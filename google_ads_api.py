import os
import pandas as pd
import matplotlib.pyplot as plt
import datetime
import gspread
import base64
import json
from oauth2client.service_account import ServiceAccountCredentials

DATA_DIR = "data"
SHEET_ID = "1rBjY6_AeDIG-1UEp3JvA44CKLAqn3JAGFttixkcRaKg"
SHEET_NAME = "Daily Ad Group Performance Report"
CONVERSION_SHEET_NAME = "Daily Ad Group Conversion Action Report"

def load_campaign_data():
    try:
        b64_key = os.getenv("GOOGLE_CREDENTIALS_B64")
        if not b64_key:
            raise ValueError("Missing GOOGLE_CREDENTIALS_B64 environment variable")

        key_data = base64.b64decode(b64_key).decode("utf-8")
        creds_dict = json.loads(key_data)

        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)

        sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)
        all_data = sheet.get_all_values()
        
        print(f"📊 Total rows loaded: {len(all_data)}")
        
        if len(all_data) < 3:
            print("⚠️ Not enough data rows found")
            return create_empty_dataframe()
        
        # Look for the actual data - skip header rows
        data_start_row = None
        for i, row in enumerate(all_data):
            if len(row) > 1 and any(char.isdigit() for char in str(row[0])) and str(row[1]).strip():
                data_start_row = i
                print(f"🎯 Found data starting at row {i}: {row}")
                break
        
        if data_start_row is None:
            print("⚠️ Could not find data rows")
            return create_empty_dataframe()
        
        # Use the row before data as headers, or create our own
        if data_start_row > 0:
            headers = all_data[data_start_row - 1]
        else:
            headers = ['Date', 'Campaign Name', 'Impressions', 'Clicks', 'Ctr', 'Conversions', 'Search Impression Share', 'Cost Per Conversion', 'Cost Micros', 'Phone Calls']
        
        data_rows = all_data[data_start_row:]
        
        print(f"🔍 Using headers: {headers}")
        print(f"📝 Data rows available: {len(data_rows)}")
        
        # Filter out empty rows
        valid_data_rows = []
        for row in data_rows:
            if len(row) >= 2 and str(row[0]).strip() and str(row[1]).strip():
                valid_data_rows.append(row)
        
        print(f"📝 Valid data rows after filtering: {len(valid_data_rows)}")
        
        if not valid_data_rows:
            print("⚠️ No valid data rows found after filtering")
            return create_empty_dataframe()
        
        df = pd.DataFrame(valid_data_rows, columns=headers)
        df.columns = [str(col).strip() for col in df.columns]
        
        print(f"✅ Created DataFrame with {len(df)} rows")
        print(f"📋 Columns: {list(df.columns)}")
        
        return df
        
    except Exception as e:
        print(f"❌ Error in load_campaign_data: {e}")
        import traceback
        traceback.print_exc()
        return create_empty_dataframe()

def create_empty_dataframe():
    return pd.DataFrame({
        'Date': [],
        'Campaign Name': [],
        'Impressions': [],
        'Clicks': [],
        'Ctr': [],
        'Conversions': [],
        'Search Impression Share': [],
        'Cost Per Conversion': [],
        'Cost Micros': [],
        'Phone Calls': []
    })

def clean_and_map_columns(df):
    if df.empty:
        return df
    
    print(f"🔧 Starting column mapping for: {list(df.columns)}")
    
    column_mapping = {}
    for col in df.columns:
        col_lower = str(col).lower().strip()
        if 'date' in col_lower:
            column_mapping[col] = 'date'
        elif 'campaign' in col_lower:
            column_mapping[col] = 'campaign'
        elif 'impression' in col_lower and 'share' not in col_lower:
            column_mapping[col] = 'impressions'
        elif 'click' in col_lower:
            column_mapping[col] = 'clicks'
        elif 'ctr' in col_lower:
            column_mapping[col] = 'ctr_raw'
        elif 'conversion' in col_lower and ('cost' in col_lower or 'per' in col_lower):
            column_mapping[col] = 'cost_per_conversion'
        elif 'conversion' in col_lower:
            column_mapping[col] = 'conversions'
        elif 'impression' in col_lower and 'share' in col_lower:
            column_mapping[col] = 'search_impression_share'
        elif 'cost' in col_lower and 'micro' in col_lower:
            column_mapping[col] = 'cost_micros'
        elif 'phone' in col_lower and 'call' in col_lower:
            column_mapping[col] = 'phone_calls'
    
    print(f"🗺️ Column mapping: {column_mapping}")
    
    df_mapped = df.rename(columns=column_mapping)
    print(f"📋 Mapped columns: {list(df_mapped.columns)}")
    
    return df_mapped

def clean_numeric_value(value):
    """Clean numeric values from strings, percentages, currency symbols"""
    if pd.isna(value) or value == '':
        return 0
    
    # Convert to string and clean
    str_val = str(value).strip()
    
    # Remove currency symbols, commas, and other non-numeric characters
    str_val = str_val.replace('€', '').replace('$', '').replace(',', '').replace('%', '')
    
    # Try to convert to float
    try:
        return float(str_val)
    except (ValueError, TypeError):
        return 0

def get_last_4_weeks():
    """Get the last 4 weeks date ranges (Monday to Sunday)"""
    today = datetime.date.today()
    
    # Find the most recent Monday
    days_since_monday = today.weekday()
    last_monday = today - datetime.timedelta(days=days_since_monday)
    
    weeks = []
    for i in range(4):
        week_start = last_monday - datetime.timedelta(weeks=i)
        week_end = week_start + datetime.timedelta(days=6)
        weeks.append((week_start, week_end))
    
    return weeks

def fetch_daily_comparison_data():
    """Fetch and organize data for daily comparison view"""
    try:
        print("🚀 Starting daily comparison data fetch...")
        
        # Load all data from sheet
        df_all = load_campaign_data()
        
        if df_all.empty:
            print("❌ No data loaded from sheet")
            return {"campaigns": {}, "weeks": [], "conversion_actions": []}
        
        df_all_mapped = clean_and_map_columns(df_all)
        
        # Clean and parse dates
        if 'date' not in df_all_mapped.columns:
            print("❌ No date column found")
            return {"campaigns": {}, "weeks": [], "conversion_actions": []}
        
        df_copy = df_all_mapped.copy()
        df_copy = df_copy[df_copy['date'].notna() & (df_copy['date'] != '')]
        df_copy['date_parsed'] = pd.to_datetime(df_copy['date'], errors='coerce')
        df_copy = df_copy.dropna(subset=['date_parsed'])
        
        if len(df_copy) == 0:
            print("❌ No valid dates found")
            return {"campaigns": {}, "weeks": [], "conversion_actions": []}
        
        # Get last 4 weeks
        weeks = get_last_4_weeks()
        print(f"📅 Analyzing weeks: {[f'{w[0]} to {w[1]}' for w in weeks]}")
        
        # Group data by campaign and week
        campaigns_data = {}
        week_labels = []
        
        for week_start, week_end in weeks:
            week_label = f"{week_start} to {week_end}"
            week_labels.append(week_label)
            
            # Filter data for this week
            week_data = df_copy[
                (df_copy['date_parsed'].dt.date >= week_start) & 
                (df_copy['date_parsed'].dt.date <= week_end)
            ]
            
            print(f"📊 Week {week_label}: {len(week_data)} rows")
            
            if not week_data.empty:
                # Group by campaign and aggregate
                for campaign in week_data['campaign'].unique():
                    if pd.isna(campaign) or campaign == '':
                        continue
                        
                    campaign_week_data = week_data[week_data['campaign'] == campaign]
                    
                    if campaign not in campaigns_data:
                        campaigns_data[campaign] = {}
                    
                    # Aggregate the week's data for this campaign
                    total_impressions = sum(clean_numeric_value(x) for x in campaign_week_data.get('impressions', []))
                    total_clicks = sum(clean_numeric_value(x) for x in campaign_week_data.get('clicks', []))
                    
                    # Calculate CTR
                    ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
                    
                    # Get other metrics (take average or sum as appropriate)
                    conversions = sum(clean_numeric_value(x) for x in campaign_week_data.get('conversions', []))
                    
                    # For percentages, take average
                    search_imp_share_values = [clean_numeric_value(x) for x in campaign_week_data.get('search_impression_share', []) if clean_numeric_value(x) > 0]
                    search_imp_share = sum(search_imp_share_values) / len(search_imp_share_values) if search_imp_share_values else 0
                    
                    cost_per_conv_values = [clean_numeric_value(x) for x in campaign_week_data.get('cost_per_conversion', []) if clean_numeric_value(x) > 0]
                    cost_per_conversion = sum(cost_per_conv_values) / len(cost_per_conv_values) if cost_per_conv_values else 0
                    
                    # Handle cost micros
                    cost_micros_values = [clean_numeric_value(x) for x in campaign_week_data.get('cost_micros', []) if clean_numeric_value(x) > 0]
                    cost_micros = sum(cost_micros_values) / len(cost_micros_values) if cost_micros_values else 0
                    
                    # Handle phone calls
                    phone_calls_values = [clean_numeric_value(x) for x in campaign_week_data.get('phone_calls', [])]
                    phone_calls = sum(phone_calls_values)
                    
                    campaigns_data[campaign][week_label] = {
                        'impressions': int(total_impressions),
                        'clicks': int(total_clicks),
                        'ctr': round(ctr, 2),
                        'conversions': conversions,
                        'search_impression_share': round(search_imp_share, 2) if search_imp_share > 0 else '—',
                        'cost_per_conversion': round(cost_per_conversion, 2) if cost_per_conversion > 0 else '—',
                        'cost_micros': round(cost_micros, 2) if cost_micros > 0 else '—',
                        'phone_calls': round(phone_calls, 2) if phone_calls > 0 else '—'
                    }
        
        print(f"✅ Processed {len(campaigns_data)} campaigns across {len(week_labels)} weeks")
        
        # Sort weeks chronologically (most recent first)
        week_labels.reverse()
        
        return {
            "campaigns": campaigns_data,
            "weeks": week_labels,
            "conversion_actions": fetch_conversion_action_data()
        }
        
    except Exception as e:
        print(f"❌ Error in fetch_daily_comparison_data: {e}")
        import traceback
        traceback.print_exc()
        return {"campaigns": {}, "weeks": [], "conversion_actions": []}

def fetch_conversion_action_data():
    """Fetch conversion action data from the second sheet"""
    try:
        print("🚀 Starting conversion action data fetch...")
        
        b64_key = os.getenv("GOOGLE_CREDENTIALS_B64")
        if not b64_key:
            raise ValueError("Missing GOOGLE_CREDENTIALS_B64 environment variable")

        key_data = base64.b64decode(b64_key).decode("utf-8")
        creds_dict = json.loads(key_data)

        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)

        sheet = client.open_by_key(SHEET_ID).worksheet(CONVERSION_SHEET_NAME)
        all_data = sheet.get_all_values()
        
        print(f"📊 Conversion data rows loaded: {len(all_data)}")
        
        if len(all_data) < 3:
            print("⚠️ Not enough conversion data rows found")
            return []
        
        # Look for the actual data - skip header rows
        data_start_row = None
        for i, row in enumerate(all_data):
            if len(row) > 1 and any(char.isdigit() for char in str(row[0])) and str(row[1]).strip():
                data_start_row = i
                print(f"🎯 Found conversion data starting at row {i}: {row}")
                break
        
        if data_start_row is None:
            print("⚠️ Could not find conversion data rows")
            return []
        
        # Use the row before data as headers
        if data_start_row > 0:
            headers = all_data[data_start_row - 1]
        else:
            headers = ['Date', 'Campaign Name', 'Conversions', 'Conversion Action Name']
        
        data_rows = all_data[data_start_row:]
        
        # Filter out empty rows
        valid_data_rows = []
        for row in data_rows:
            if len(row) >= 2 and str(row[0]).strip() and str(row[1]).strip():
                valid_data_rows.append(row)
        
        print(f"📝 Valid conversion data rows after filtering: {len(valid_data_rows)}")
        
        if not valid_data_rows:
            print("⚠️ No valid conversion data rows found after filtering")
            return []
        
        df = pd.DataFrame(valid_data_rows, columns=headers)
        df.columns = [str(col).strip() for col in df.columns]
        
        print(f"✅ Created conversion DataFrame with {len(df)} rows")
        
        # Get last 7 days of conversion data
        df_copy = df.copy()
        df_copy = df_copy[df_copy.iloc[:, 0].notna() & (df_copy.iloc[:, 0] != '')]
        df_copy['date_parsed'] = pd.to_datetime(df_copy.iloc[:, 0], errors='coerce')
        df_copy = df_copy.dropna(subset=['date_parsed'])
        
        if len(df_copy) == 0:
            print("❌ No valid conversion dates found")
            return []
        
        # Get last 7 days
        today = datetime.date.today()
        seven_days_ago = today - datetime.timedelta(days=7)
        
        recent_data = df_copy[df_copy['date_parsed'].dt.date >= seven_days_ago]
        
        print(f"✅ Processed {len(recent_data)} conversion rows from last 7 days")
        
        return recent_data.to_dict('records')
        
    except Exception as e:
        print(f"❌ Error in fetch_conversion_action_data: {e}")
        import traceback
        traceback.print_exc()
        return []
        
        df_all_mapped = clean_and_map_columns(df_all)
        
        # Clean and parse dates
        if 'date' not in df_all_mapped.columns:
            print("❌ No date column found")
            return {"campaigns": {}, "weeks": []}
        
        df_copy = df_all_mapped.copy()
        df_copy = df_copy[df_copy['date'].notna() & (df_copy['date'] != '')]
        df_copy['date_parsed'] = pd.to_datetime(df_copy['date'], errors='coerce')
        df_copy = df_copy.dropna(subset=['date_parsed'])
        
        if len(df_copy) == 0:
            print("❌ No valid dates found")
            return {"campaigns": {}, "weeks": []}
        
        # Get last 4 weeks
        weeks = get_last_4_weeks()
        print(f"📅 Analyzing weeks: {[f'{w[0]} to {w[1]}' for w in weeks]}")
        
        # Group data by campaign and week
        campaigns_data = {}
        week_labels = []
        
        for week_start, week_end in weeks:
            week_label = f"{week_start} to {week_end}"
            week_labels.append(week_label)
            
            # Filter data for this week
            week_data = df_copy[
                (df_copy['date_parsed'].dt.date >= week_start) & 
                (df_copy['date_parsed'].dt.date <= week_end)
            ]
            
            print(f"📊 Week {week_label}: {len(week_data)} rows")
            
            if not week_data.empty:
                # Group by campaign and aggregate
                for campaign in week_data['campaign'].unique():
                    if pd.isna(campaign) or campaign == '':
                        continue
                        
                    campaign_week_data = week_data[week_data['campaign'] == campaign]
                    
                    if campaign not in campaigns_data:
                        campaigns_data[campaign] = {}
                    
                    # Aggregate the week's data for this campaign
                    total_impressions = sum(clean_numeric_value(x) for x in campaign_week_data.get('impressions', []))
                    total_clicks = sum(clean_numeric_value(x) for x in campaign_week_data.get('clicks', []))
                    
                    # Calculate CTR
                    ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
                    
                    # Get other metrics (take average or sum as appropriate)
                    conversions = sum(clean_numeric_value(x) for x in campaign_week_data.get('conversions', []))
                    
                    # For percentages, take average
                    search_imp_share_values = [clean_numeric_value(x) for x in campaign_week_data.get('search_impression_share', []) if clean_numeric_value(x) > 0]
                    search_imp_share = sum(search_imp_share_values) / len(search_imp_share_values) if search_imp_share_values else 0
                    
                    cost_per_conv_values = [clean_numeric_value(x) for x in campaign_week_data.get('cost_per_conversion', []) if clean_numeric_value(x) > 0]
                    cost_per_conversion = sum(cost_per_conv_values) / len(cost_per_conv_values) if cost_per_conv_values else 0
                    
                    # Handle cost micros
                    cost_micros_values = [clean_numeric_value(x) for x in campaign_week_data.get('cost_micros', []) if clean_numeric_value(x) > 0]
                    cost_micros = sum(cost_micros_values) / len(cost_micros_values) if cost_micros_values else 0
                    
                    # Handle phone calls
                    phone_calls_values = [clean_numeric_value(x) for x in campaign_week_data.get('phone_calls', [])]
                    phone_calls = sum(phone_calls_values)
                    
                    campaigns_data[campaign][week_label] = {
                        'impressions': int(total_impressions),
                        'clicks': int(total_clicks),
                        'ctr': round(ctr, 2),
                        'conversions': conversions,
                        'search_impression_share': round(search_imp_share, 2) if search_imp_share > 0 else '—',
                        'cost_per_conversion': round(cost_per_conversion, 2) if cost_per_conversion > 0 else '—',
                        'cost_micros': round(cost_micros, 2) if cost_micros > 0 else '—',
                        'phone_calls': round(phone_calls, 2) if phone_calls > 0 else '—'
                    }
        
        print(f"✅ Processed {len(campaigns_data)} campaigns across {len(week_labels)} weeks")
        
        # Sort weeks chronologically (most recent first)
        week_labels.reverse()
        
        return {
            "campaigns": campaigns_data,
            "weeks": week_labels,
            "conversion_actions": fetch_conversion_action_data()
        }
        
    except Exception as e:
        print(f"❌ Error in fetch_daily_comparison_data: {e}")
        import traceback
        traceback.print_exc()
        return {"campaigns": {}, "weeks": []}

# Keep the original functions for backward compatibility
def get_date_range_data(df_all, target_date, days_back=7):
    """Get data for target date and comparison period (e.g., previous week)"""
    if df_all.empty or 'date' not in df_all.columns:
        return pd.DataFrame(), pd.DataFrame()
    
    print(f"📅 Getting data for {target_date} and {days_back} days back")
    
    # Clean and parse dates
    df_copy = df_all.copy()
    df_copy = df_copy[df_copy['date'].notna() & (df_copy['date'] != '')]
    df_copy['date_parsed'] = pd.to_datetime(df_copy['date'], errors='coerce')
    df_copy = df_copy.dropna(subset=['date_parsed'])
    
    if len(df_copy) == 0:
        return pd.DataFrame(), pd.DataFrame()
    
    # Get current period data (target date)
    current_df = df_copy[df_copy['date_parsed'].dt.date == target_date]
    
    # Get comparison period data (same day previous week)
    comparison_date = target_date - datetime.timedelta(days=days_back)
    comparison_df = df_copy[df_copy['date_parsed'].dt.date == comparison_date]
    
    print(f"📊 Current data ({target_date}): {len(current_df)} rows")
    print(f"📊 Comparison data ({comparison_date}): {len(comparison_df)} rows")
    
    return current_df.drop('date_parsed', axis=1), comparison_df.drop('date_parsed', axis=1)

def add_kpis(df):
    if df.empty:
        print("⚠️ Empty dataframe in add_kpis")
        return create_processed_empty_dataframe()
    
    print(f"🧮 Adding KPIs to {len(df)} rows")
    
    # Filter for valid campaigns
    if 'campaign' in df.columns:
        df = df[df['campaign'].notna() & (df['campaign'] != '')]
        print(f"📊 After filtering valid campaigns: {len(df)} rows")
    
    if len(df) == 0:
        print("⚠️ No valid campaigns found")
        return create_processed_empty_dataframe()
    
    # Clean numeric columns
    numeric_columns = ['impressions', 'clicks', 'conversions']
    for col in numeric_columns:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(r'[€$,%]', '', regex=True)
            df[col] = df[col].str.replace(',', '')
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        else:
            df[col] = 0
    
    # Handle CTR
    if 'ctr_raw' in df.columns:
        df['ctr_raw'] = df['ctr_raw'].astype(str).str.replace('%', '').str.replace('€', '')
        df['ctr'] = pd.to_numeric(df['ctr_raw'], errors='coerce').fillna(0)
    else:
        df['ctr'] = ((df['clicks'] / df['impressions']) * 100).round(2)
        df['ctr'] = df['ctr'].replace([float('inf'), -float('inf')], 0).fillna(0)
    
    # Estimate spend
    def estimate_cpc(campaign_name):
        campaign_lower = str(campaign_name).lower()
        if 'search' in campaign_lower:
            return 0.25
        elif 'performance max' in campaign_lower:
            return 0.18
        elif 'demand gen' in campaign_lower:
            return 0.05
        else:
            return 0.20
    
    df['cpc'] = df['campaign'].apply(estimate_cpc)
    df['spend'] = (df['clicks'] * df['cpc']).round(2)
    
    # Calculate other KPIs
    df['conversion_rate'] = ((df['conversions'] / df['clicks']) * 100).round(2)
    df['conversion_rate'] = df['conversion_rate'].replace([float('inf'), -float('inf')], 0).fillna(0)
    
    df['cost_per_conversion'] = (df['spend'] / df['conversions']).round(2)
    df['cost_per_conversion'] = df['cost_per_conversion'].replace([float('inf'), -float('inf')], 0).fillna(0)
    
    # Handle impression share
    if 'search_impression_share' in df.columns:
        df['search_impression_share'] = df['search_impression_share'].astype(str).str.replace('%', '')
        df['search_impression_share'] = pd.to_numeric(df['search_impression_share'], errors='coerce').fillna(75.0)
    else:
        df['search_impression_share'] = 75.0
    
    df['quality_score'] = 7.5
    
    return df

def create_processed_empty_dataframe():
    return pd.DataFrame({
        'campaign': [],
        'impressions': [],
        'clicks': [],
        'ctr': [],
        'spend': [],
        'cpc': [],
        'conversions': [],
        'conversion_rate': [],
        'cost_per_conversion': [],
        'search_impression_share': [],
        'quality_score': [],
        'cost_micros': []
    })

def generate_summary_stats(df):
    if df.empty:
        return {
            'total_spend': 0,
            'total_clicks': 0,
            'total_impressions': 0,
            'total_conversions': 0,
            'avg_ctr': 0,
            'avg_cpc': 0,
            'avg_conversion_rate': 0,
            'avg_impression_share': 0
        }
    
    return {
        'total_spend': round(df['spend'].sum(), 2),
        'total_clicks': int(df['clicks'].sum()),
        'total_impressions': int(df['impressions'].sum()),
        'total_conversions': int(df['conversions'].sum()),
        'avg_ctr': round(df['ctr'].mean(), 2),
        'avg_cpc': round(df['cpc'].mean(), 2),
        'avg_conversion_rate': round(df['conversion_rate'].mean(), 2),
        'avg_impression_share': round(df['search_impression_share'].mean(), 1)
    }

def calculate_percentage_change(current, previous):
    """Calculate percentage change between current and previous values"""
    if previous == 0:
        return 100 if current > 0 else 0
    return round(((current - previous) / previous) * 100, 1)

def format_trend_indicator(change_pct):
    """Format trend indicator with emoji and color"""
    if change_pct > 0:
        return f"📈 +{change_pct}%"
    elif change_pct < 0:
        return f"📉 {change_pct}%"
    else:
        return "➡️ 0%"

def generate_insights_with_comparison(current_df, comparison_df):
    current_summary = generate_summary_stats(current_df)
    comparison_summary = generate_summary_stats(comparison_df)
    
    # Calculate trends
    trends = {}
    for key in current_summary:
        if key in comparison_summary:
            change_pct = calculate_percentage_change(current_summary[key], comparison_summary[key])
            trends[key] = {
                'current': current_summary[key],
                'previous': comparison_summary[key],
                'change_pct': change_pct,
                'trend': format_trend_indicator(change_pct)
            }
    
    if current_df.empty:
        return {
            'summary': current_summary,
            'summary_trends': trends,
            'highlights': [
                {'metric': '📊 Status', 'campaign': 'No Data', 'value': 'No campaigns found', 'trend': '', 'change': 0}
            ],
            'campaigns': [],
            'comparison_available': not comparison_df.empty
        }
    
    highlights = []
    
    # Most clicks with comparison
    if current_df['clicks'].sum() > 0:
        most_clicks_idx = current_df['clicks'].idxmax()
        most_clicks = current_df.loc[most_clicks_idx]
        campaign_name = str(most_clicks['campaign'])[:30]
        
        # Find same campaign in comparison data
        trend = ""
        if not comparison_df.empty:
            comp_campaign = comparison_df[comparison_df['campaign'] == most_clicks['campaign']]
            if not comp_campaign.empty:
                prev_clicks = comp_campaign['clicks'].iloc[0]
                change_pct = calculate_percentage_change(most_clicks['clicks'], prev_clicks)
                trend = format_trend_indicator(change_pct)
        
        highlights.append({
            'metric': '🥇 Most Clicks',
            'campaign': campaign_name,
            'value': f"{int(most_clicks['clicks']):,}",
            'trend': trend,
            'change': 0
        })
    
    # Most impressions with comparison
    if current_df['impressions'].sum() > 0:
        most_impressions_idx = current_df['impressions'].idxmax()
        most_impressions = current_df.loc[most_impressions_idx]
        campaign_name = str(most_impressions['campaign'])[:30]
        
        trend = ""
        if not comparison_df.empty:
            comp_campaign = comparison_df[comparison_df['campaign'] == most_impressions['campaign']]
            if not comp_campaign.empty:
                prev_impressions = comp_campaign['impressions'].iloc[0]
                change_pct = calculate_percentage_change(most_impressions['impressions'], prev_impressions)
                trend = format_trend_indicator(change_pct)
        
        highlights.append({
            'metric': '👁️ Most Impressions',
            'campaign': campaign_name,
            'value': f"{int(most_impressions['impressions']):,}",
            'trend': trend,
            'change': 0
        })
    
    # Best CTR with comparison
    if current_df['ctr'].sum() > 0:
        best_ctr_idx = current_df['ctr'].idxmax()
        best_ctr = current_df.loc[best_ctr_idx]
        campaign_name = str(best_ctr['campaign'])[:30]
        
        trend = ""
        if not comparison_df.empty:
            comp_campaign = comparison_df[comparison_df['campaign'] == best_ctr['campaign']]
            if not comp_campaign.empty:
                prev_ctr = comp_campaign['ctr'].iloc[0]
                change_pct = calculate_percentage_change(best_ctr['ctr'], prev_ctr)
                trend = format_trend_indicator(change_pct)
        
        highlights.append({
            'metric': '🎯 Best CTR',
            'campaign': campaign_name,
            'value': f"{best_ctr['ctr']:.2f}%",
            'trend': trend,
            'change': 0
        })
    
    if not highlights:
        highlights = [
            {'metric': '📊 Status', 'campaign': 'Data Available', 'value': f'{len(current_df)} campaigns', 'trend': '', 'change': 0}
        ]
    
    return {
        'summary': current_summary,
        'summary_trends': trends,
        'highlights': highlights,
        'campaigns': current_df.to_dict('records'),
        'comparison_available': not comparison_df.empty
    }

def create_enhanced_charts(df):
    os.makedirs("static", exist_ok=True)
    
    if df.empty:
        plt.figure(figsize=(10, 6))
        plt.text(0.5, 0.5, 'No data available\nCheck Google Sheets connection', ha='center', va='center', fontsize=16)
        plt.xlim(0, 1)
        plt.ylim(0, 1)
        plt.axis('off')
        plt.title("Google Ads Spend Overview", fontsize=14, fontweight='bold')
        plt.savefig("static/spend_chart.png", dpi=150, bbox_inches='tight')
        plt.close()
        return
    
    campaigns = [str(name)[:15] + "..." if len(str(name)) > 15 else str(name) for name in df['campaign']]
    
    plt.figure(figsize=(12, 6))
    bars = plt.bar(campaigns, df['spend'], color='#667eea', alpha=0.8)
    plt.title("Estimated Daily Spend by Campaign", fontsize=14, fontweight='bold', pad=20)
    plt.ylabel("Spend (€)")
    plt.xticks(rotation=45, ha='right')
    
    for bar, spend in zip(bars, df['spend']):
        if spend > 0:
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                    f'€{spend:.1f}', ha='center', va='bottom', fontsize=10)
    
    plt.tight_layout()
    plt.savefig("static/spend_chart.png", dpi=150, bbox_inches='tight')
    plt.close()

def fetch_sheet_data():
    try:
        today = datetime.date.today()
        print(f"🚀 Starting fetch for {today}")
        
        # Load all data from sheet
        df_all = load_campaign_data()
        
        if df_all.empty:
            print("❌ No data loaded from sheet")
            return create_processed_empty_dataframe(), generate_insights_with_comparison(create_processed_empty_dataframe(), create_processed_empty_dataframe())
        
        df_all_mapped = clean_and_map_columns(df_all)
        
        # Get current and comparison data
        current_df, comparison_df = get_date_range_data(df_all_mapped, today, days_back=7)
        
        # If no data for today, try yesterday
        if current_df.empty:
            print(f"⚠️ No data for today ({today}), trying yesterday")
            yesterday = today - datetime.timedelta(days=1)
            current_df, comparison_df = get_date_range_data(df_all_mapped, yesterday, days_back=7)
            
            if current_df.empty:
                print(f"⚠️ No data for yesterday ({yesterday}) either, using latest available")
                # Use the most recent data available
                if 'date' in df_all_mapped.columns:
                    df_all_mapped['date_parsed'] = pd.to_datetime(df_all_mapped['date'], errors='coerce')
                    df_all_mapped = df_all_mapped.dropna(subset=['date_parsed'])
                    if not df_all_mapped.empty:
                        latest_date = df_all_mapped['date_parsed'].max().date()
                        current_df, comparison_df = get_date_range_data(df_all_mapped, latest_date, days_back=7)
                        print(f"📅 Using latest available date: {latest_date}")
        
        if current_df.empty:
            print("❌ Still no data found")
            return create_processed_empty_dataframe(), generate_insights_with_comparison(create_processed_empty_dataframe(), create_processed_empty_dataframe())
        
        # Process the data
        current_df = add_kpis(current_df)
        comparison_df = add_kpis(comparison_df) if not comparison_df.empty else comparison_df
        
        # Save data
        os.makedirs(DATA_DIR, exist_ok=True)
        current_df.to_csv(f"{DATA_DIR}/ads_{today.strftime('%Y-%m-%d')}.csv", index=False)
        
        # Create charts
        create_enhanced_charts(current_df)
        
        # Generate insights with comparison
        insights = generate_insights_with_comparison(current_df, comparison_df)
        
        print(f"✅ Successfully processed {len(current_df)} campaigns")
        if not comparison_df.empty:
            print(f"📊 Comparison data available for {len(comparison_df)} campaigns")
        
        return current_df, insights
        
    except Exception as e:
        print(f"❌ Error in fetch_sheet_data: {e}")
        import traceback
        traceback.print_exc()
        raise