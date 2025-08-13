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

def load_campaign_data(sheet_name=None):
    try:
        b64_key = os.getenv("GOOGLE_CREDENTIALS_B64")
        if not b64_key:
            raise ValueError("Missing GOOGLE_CREDENTIALS_B64 environment variable")

        key_data = base64.b64decode(b64_key).decode("utf-8")
        creds_dict = json.loads(key_data)

        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)

        target_sheet_name = sheet_name if sheet_name else SHEET_NAME
        print(f"📊 Loading data from sheet: {target_sheet_name}")
        sheet = client.open_by_key(SHEET_ID).worksheet(target_sheet_name)
        all_data = sheet.get_all_values()

        print(f"📊 Total rows loaded: {len(all_data)}")

        if len(all_data) < 3:
            print("⚠️ Not enough data rows found")
            return create_empty_dataframe()

        # Find the header row (first non-empty row)
        header_row_idx = 0
        for i, row in enumerate(all_data):
            if any(cell.strip() for cell in row):
                if 'Date' in row or 'Campaign' in str(row):
                    header_row_idx = i
                    break

        # Extract headers and data
        headers = [col.strip() for col in all_data[header_row_idx]]
        data_rows = all_data[header_row_idx + 1:]
        
        print(f"🎯 Found data starting at row {header_row_idx + 1}: {data_rows[0][:4] if data_rows else 'No data'}")
        print(f"🔍 Using headers: {headers[:10]}")

        # Filter out empty rows
        valid_rows = []
        for row in data_rows:
            if len(row) >= len(headers):
                row_padded = row[:len(headers)]
            else:
                row_padded = row + [''] * (len(headers) - len(row))
            
            if any(cell.strip() for cell in row_padded):
                valid_rows.append(row_padded)

        print(f"📝 Data rows available: {len(data_rows)}")
        print(f"📝 Valid data rows after filtering: {len(valid_rows)}")

        if not valid_rows:
            print("❌ No valid data rows found")
            return create_empty_dataframe()

        # Create DataFrame
        df = pd.DataFrame(valid_rows, columns=headers)
        print(f"✅ Created DataFrame with {len(df)} rows")
        print(f"📋 Columns: {list(df.columns)}")

        # Clean the DataFrame
        df = clean_and_map_columns(df)
        
        return df

    except Exception as e:
        print(f"❌ Error in load_campaign_data: {e}")
        import traceback
        traceback.print_exc()
        raise

def create_empty_dataframe():
    """Create an empty DataFrame with expected columns"""
    columns = [
        'Date', 'Campaign Name', 'Impressions', 'Clicks', 'Ctr', 'Conversions',
        'Search Impression Share', 'Cost Per Conversion', 'Cost Micros', 'Phone Calls'
    ]
    return pd.DataFrame(columns=columns)

def clean_and_map_columns(df):
    """Clean and standardize column names"""
    try:
        # Column mapping for different possible names
        column_mapping = {
            'Date': 'Date',
            'Campaign name': 'Campaign Name',
            'Campaign Name': 'Campaign Name',
            'Impressions': 'Impressions',
            'Clicks': 'Clicks',
            'Ctr': 'Ctr',
            'CTR': 'Ctr',
            'Click-through rate': 'Ctr',
            'Conversions': 'Conversions',
            'Conv.': 'Conversions',
            'Search impression share': 'Search Impression Share',
            'Search Impression Share': 'Search Impression Share',
            'Impr. share': 'Search Impression Share',
            'Cost per conversion': 'Cost Per Conversion',
            'Cost Per Conversion': 'Cost Per Conversion',
            'Cost/conv.': 'Cost Per Conversion',
            'Cost micros': 'Cost Micros',
            'Cost Micros': 'Cost Micros',
            'Phone calls': 'Phone Calls',
            'Phone Calls': 'Phone Calls'
        }
        
        # Rename columns based on mapping
        df.columns = [column_mapping.get(col, col) for col in df.columns]
        
        # Ensure required columns exist with default values
        required_columns = ['Date', 'Campaign Name', 'Impressions', 'Clicks', 'Ctr', 'Conversions', 
                          'Search Impression Share', 'Cost Per Conversion', 'Cost Micros', 'Phone Calls']
        
        for col in required_columns:
            if col not in df.columns:
                df[col] = 0 if col != 'Date' and col != 'Campaign Name' else ''
        
        return df
        
    except Exception as e:
        print(f"❌ Error in clean_and_map_columns: {e}")
        return df

def clean_numeric_value(value):
    """Clean and convert numeric values"""
    if pd.isna(value) or value == '' or value == '--' or value == '—':
        return 0
    
    try:
        # Convert to string and handle concatenated values
        str_value = str(value)
        
        # If it contains multiple percentage signs, it's concatenated data
        if str_value.count('%') > 1:
            # Split by % and take the first valid number
            parts = str_value.split('%')
            for part in parts:
                part = part.strip()
                if part and part != '':
                    try:
                        return float(part)
                    except ValueError:
                        continue
            return 0
        
        # Remove common formatting
        cleaned = str_value.replace(',', '').replace('%', '').replace('€', '').replace('$', '').strip()
        if cleaned == '' or cleaned == '--' or cleaned == '—':
            return 0
        return float(cleaned)
    except (ValueError, TypeError):
        return 0

def get_last_4_weeks():
    """Get the date range for the last 4 weeks"""
    from datetime import datetime, timedelta
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=28)  # 4 weeks
    
    return start_date, end_date

def safe_numeric_mean(series):
    """Safely calculate mean of potentially malformed data"""
    try:
        # Convert each value individually
        numeric_values = []
        for val in series:
            cleaned = clean_numeric_value(val)
            if cleaned > 0:
                numeric_values.append(cleaned)
        return sum(numeric_values) / len(numeric_values) if numeric_values else 0
    except:
        return 0

def safe_numeric_sum(series):
    """Safely calculate sum of potentially malformed data"""
    try:
        total = 0
        for val in series:
            cleaned = clean_numeric_value(val)
            total += cleaned
        return total
    except:
        return 0

def fetch_daily_comparison_data():
    """Fetch and process daily comparison data for Luma campaigns"""
    try:
        print("🚀 Starting daily comparison data fetch...")
        
        # Load campaign data
        df = load_campaign_data()
        
        if df is None or df.empty:
            print("❌ No data loaded from sheet")
            return {"campaigns": {}, "weeks": []}
        
        # Process dates and filter for last 4 weeks
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df.dropna(subset=['Date'])
        
        start_date, end_date = get_last_4_weeks()
        recent_df = df[df['Date'] >= start_date].copy()
        
        if recent_df.empty:
            print("❌ No recent data found in last 4 weeks")
            return {"campaigns": {}, "weeks": []}
        
        # Group by week
        recent_df['Week_Start'] = recent_df['Date'].dt.to_period('W').dt.start_time
        weeks = sorted(recent_df['Week_Start'].dt.strftime('%Y-%m-%d').unique())
        
        # Process campaigns
        campaigns = {}
        for campaign in recent_df['Campaign Name'].unique():
            if not campaign or pd.isna(campaign):
                continue
                
            campaign_data = recent_df[recent_df['Campaign Name'] == campaign]
            campaigns[campaign] = {}
            
            for week in weeks:
                week_data = campaign_data[campaign_data['Week_Start'].dt.strftime('%Y-%m-%d') == week]
                if not week_data.empty:
                    campaigns[campaign][week] = {
                        'impressions': int(safe_numeric_sum(week_data['Impressions'])),
                        'clicks': int(safe_numeric_sum(week_data['Clicks'])),
                        'ctr': round(safe_numeric_mean(week_data['Ctr']), 2),
                        'conversions': int(safe_numeric_sum(week_data['Conversions'])),
                        'search_impression_share': round(safe_numeric_mean(week_data['Search Impression Share']), 2),
                        'cost_per_conversion': round(safe_numeric_mean(week_data['Cost Per Conversion']), 2),
                        'cost_micros': round(safe_numeric_sum(week_data['Cost Micros']), 2),
                        'phone_calls': int(safe_numeric_sum(week_data['Phone Calls']))
                    }
        
        print(f"✅ Daily comparison data ready: {len(campaigns)} campaigns, {len(weeks)} weeks")
        return {"campaigns": campaigns, "weeks": weeks}
        
    except Exception as e:
        print(f"❌ Error in fetch_daily_comparison_data: {e}")
        import traceback
        traceback.print_exc()
        return {"campaigns": {}, "weeks": []}

def fetch_conversion_action_data(sheet_name=None):
    """Fetch conversion action data from the specified sheet"""
    try:
        print("🔄 Loading conversion action data...")
        
        b64_key = os.getenv("GOOGLE_CREDENTIALS_B64")
        if not b64_key:
            print("❌ Missing GOOGLE_CREDENTIALS_B64 environment variable")
            return pd.DataFrame()

        key_data = base64.b64decode(b64_key).decode("utf-8")
        creds_dict = json.loads(key_data)

        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)

        # Use provided sheet_name or default
        target_sheet_name = sheet_name if sheet_name else CONVERSION_SHEET_NAME
        print(f"📊 Loading conversion data from sheet: {target_sheet_name}")
        
        try:
            sheet = client.open_by_key(SHEET_ID).worksheet(target_sheet_name)
            all_data = sheet.get_all_values()
        except gspread.WorksheetNotFound:
            print(f"❌ Sheet '{target_sheet_name}' not found")
            return pd.DataFrame()

        print(f"📊 Conversion data rows loaded: {len(all_data)}")

        if len(all_data) < 2:
            print("⚠️ Not enough conversion data rows")
            return pd.DataFrame()

        # Find header row
        header_row_idx = 0
        for i, row in enumerate(all_data):
            if any('Date' in str(cell) for cell in row):
                header_row_idx = i
                break

        headers = [col.strip() for col in all_data[header_row_idx]]
        data_rows = all_data[header_row_idx + 1:]
        
        print(f"🎯 Found conversion data starting at row {header_row_idx + 1}: {data_rows[0] if data_rows else 'No data'}")

        # Filter valid rows
        valid_rows = []
        for row in data_rows:
            if len(row) >= len(headers):
                row_padded = row[:len(headers)]
            else:
                row_padded = row + [''] * (len(headers) - len(row))
            
            if any(cell.strip() for cell in row_padded[:4]):  # Check first 4 columns
                valid_rows.append(row_padded)

        print(f"📝 Valid conversion data rows after filtering: {len(valid_rows)}")

        if not valid_rows:
            print("❌ No valid conversion data found")
            return pd.DataFrame()

        df = pd.DataFrame(valid_rows, columns=headers)
        print(f"✅ Created conversion DataFrame with {len(df)} rows")

        # Filter for last 7 days
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            df = df.dropna(subset=['Date'])
            
            from datetime import datetime, timedelta
            week_ago = datetime.now() - timedelta(days=7)
            recent_conversions = df[df['Date'] >= week_ago]
            
            print(f"✅ Processed {len(recent_conversions)} conversion rows from last 7 days")
            return recent_conversions
        
        return df

    except Exception as e:
        print(f"❌ Error fetching conversion data: {e}")
        return pd.DataFrame()

def fetch_keynote_comparison_data():
    """
    Fetch Keynote campaign data for daily comparison from the Keynote sheet tab
    """
    try:
        print("🚀 Starting Keynote daily comparison data fetch...")
        
        # Use the Keynote-specific sheet name
        keynote_sheet_name = "Daily Ad Group Performance Report Keynote"
        
        # Load data from the Keynote sheet
        df = load_campaign_data(sheet_name=keynote_sheet_name)
        
        if df is None or df.empty:
            print(f"❌ No data found in {keynote_sheet_name} sheet")
            return {"campaigns": {}, "weeks": []}
        
        print(f"✅ Loaded {len(df)} rows from Keynote sheet")
        print(f"📋 Available columns: {list(df.columns)}")
        
        # Process the data using similar logic to fetch_daily_comparison_data
        from datetime import datetime, timedelta
        
        # Convert Date column to datetime
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df.dropna(subset=['Date'])
        
        if df.empty:
            print("❌ No valid dates in Keynote data")
            return {"campaigns": {}, "weeks": []}
        
        # Get last 4 weeks of data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=28)
        recent_df = df[df['Date'] >= start_date].copy()
        
        if recent_df.empty:
            print("❌ No recent Keynote data found in last 4 weeks")
            return {"campaigns": {}, "weeks": []}
        
        # Group by week
        recent_df['Week_Start'] = recent_df['Date'].dt.to_period('W').dt.start_time
        weeks = sorted(recent_df['Week_Start'].dt.strftime('%Y-%m-%d').unique())
        
        # Take only last 4 weeks
        weeks = weeks[-4:] if len(weeks) > 4 else weeks
        
        print(f"📅 Processing {len(weeks)} weeks: {weeks}")
        
        # Process campaigns
        campaigns = {}
        for campaign in recent_df['Campaign Name'].unique():
            if not campaign or pd.isna(campaign):
                continue
                
            campaign_data = recent_df[recent_df['Campaign Name'] == campaign]
            campaigns[campaign] = {}
            
            for week in weeks:
                week_data = campaign_data[campaign_data['Week_Start'].dt.strftime('%Y-%m-%d') == week]
                if not week_data.empty:
                    campaigns[campaign][week] = {
                        'impressions': int(safe_numeric_sum(week_data['Impressions'])),
                        'clicks': int(safe_numeric_sum(week_data['Clicks'])),
                        'ctr': round(safe_numeric_mean(week_data['Ctr']), 2),
                        'conversions': int(safe_numeric_sum(week_data['Conversions'])),
                        'search_impression_share': round(safe_numeric_mean(week_data['Search Impression Share']), 2),
                        'cost_per_conversion': round(safe_numeric_mean(week_data['Cost Per Conversion']), 2),
                        'cost_micros': round(safe_numeric_sum(week_data['Cost Micros']), 2),
                        'phone_calls': int(safe_numeric_sum(week_data['Phone Calls']))
                    }
        
        result = {"campaigns": campaigns, "weeks": weeks}
        print(f"✅ Keynote comparison data ready: {len(campaigns)} campaigns, {len(weeks)} weeks")
        return result
        
    except Exception as e:
        print(f"❌ Error in fetch_keynote_comparison_data: {e}")
        import traceback
        traceback.print_exc()
        return {"campaigns": {}, "weeks": []}

def fetch_keynote_conversion_data():
    """Fetch conversion data specifically for Keynote campaigns"""
    try:
        keynote_conversion_sheet = "Daily Ad Group Conversion Action Report Keynote"
        conversion_df = fetch_conversion_action_data(sheet_name=keynote_conversion_sheet)
        
        if conversion_df.empty:
            print("❌ No Keynote conversion data available")
            return pd.DataFrame()
        
        print(f"✅ Loaded {len(conversion_df)} Keynote conversion rows")
        return conversion_df
        
    except Exception as e:
        print(f"❌ Error fetching Keynote conversion data: {e}")
        return pd.DataFrame()

# Additional utility functions
def get_date_range_data(df_all, target_date, days_back=7):
    """Get data for a specific date range"""
    try:
        if df_all.empty:
            return pd.DataFrame()
        
        from datetime import datetime, timedelta
        
        end_date = pd.to_datetime(target_date)
        start_date = end_date - timedelta(days=days_back)
        
        df_all['Date'] = pd.to_datetime(df_all['Date'], errors='coerce')
        filtered_df = df_all[(df_all['Date'] >= start_date) & (df_all['Date'] <= end_date)]
        
        return filtered_df
        
    except Exception as e:
        print(f"❌ Error in get_date_range_data: {e}")
        return pd.DataFrame()

def add_kpis(df):
    """Add calculated KPIs to the dataframe"""
    try:
        if df.empty:
            return df
        
        # Add calculated columns
        df['CTR_calc'] = (df['Clicks'] / df['Impressions'] * 100).fillna(0)
        df['CPC'] = (df['Cost Micros'] / df['Clicks']).fillna(0)
        df['Conversion_Rate'] = (df['Conversions'] / df['Clicks'] * 100).fillna(0)
        
        return df
        
    except Exception as e:
        print(f"❌ Error adding KPIs: {e}")
        return df

def create_processed_empty_dataframe():
    """Create an empty processed DataFrame"""
    columns = [
        'Date', 'Campaign Name', 'Impressions', 'Clicks', 'Ctr', 'Conversions',
        'Search Impression Share', 'Cost Per Conversion', 'Cost Micros', 'Phone Calls',
        'CTR_calc', 'CPC', 'Conversion_Rate'
    ]
    return pd.DataFrame(columns=columns)

def generate_summary_stats(df):
    """Generate summary statistics"""
    try:
        if df.empty:
            return {}
        
        return {
            'total_impressions': df['Impressions'].sum(),
            'total_clicks': df['Clicks'].sum(),
            'average_ctr': df['Ctr'].mean(),
            'total_conversions': df['Conversions'].sum(),
            'total_cost': df['Cost Micros'].sum()
        }
        
    except Exception as e:
        print(f"❌ Error generating summary stats: {e}")
        return {}

def calculate_percentage_change(current, previous):
    """Calculate percentage change between two values"""
    if previous == 0:
        return 0 if current == 0 else 100
    return ((current - previous) / previous) * 100

def format_trend_indicator(change_pct):
    """Format trend indicator based on percentage change"""
    if change_pct > 5:
        return "📈 Strong Increase"
    elif change_pct > 0:
        return "↗️ Slight Increase"
    elif change_pct < -5:
        return "📉 Strong Decrease"
    elif change_pct < 0:
        return "↘️ Slight Decrease"
    else:
        return "➡️ No Change"

def generate_insights_with_comparison(current_df, comparison_df):
    """Generate insights by comparing current and previous periods"""
    try:
        insights = []
        
        if current_df.empty:
            return ["No current data available for analysis"]
        
        current_stats = generate_summary_stats(current_df)
        
        if not comparison_df.empty:
            comparison_stats = generate_summary_stats(comparison_df)
            
            # Calculate changes
            impression_change = calculate_percentage_change(
                current_stats['total_impressions'], 
                comparison_stats['total_impressions']
            )
            
            click_change = calculate_percentage_change(
                current_stats['total_clicks'], 
                comparison_stats['total_clicks']
            )
            
            insights.append(f"Impressions {format_trend_indicator(impression_change)}: {impression_change:.1f}%")
            insights.append(f"Clicks {format_trend_indicator(click_change)}: {click_change:.1f}%")
        
        return insights
        
    except Exception as e:
        print(f"❌ Error generating insights: {e}")
        return ["Error generating insights"]

def create_enhanced_charts(df):
    """Create enhanced charts for the data"""
    try:
        if df.empty:
            print("❌ No data available for charts")
            return None
        
        # This would create matplotlib charts if needed
        print("📊 Chart creation functionality available")
        return True
        
    except Exception as e:
        print(f"❌ Error creating charts: {e}")
        return None

def fetch_sheet_data():
    """Fetch sheet data with insights and comparison"""
    try:
        print("🚀 Starting sheet data fetch with insights...")
        
        # Load current data
        current_df = load_campaign_data()
        
        if current_df.empty:
            print("❌ No current data available")
            return current_df, []
        
        # Get comparison data (previous period)
        from datetime import datetime, timedelta
        
        end_date = datetime.now() - timedelta(days=7)
        start_date = end_date - timedelta(days=7)
        comparison_df = get_date_range_data(current_df, end_date, days_back=7)
        
        # Generate insights
        insights = generate_insights_with_comparison(current_df, comparison_df)
        
        if not comparison_df.empty:
            print(f"📊 Comparison data available for {len(comparison_df)} campaigns")
        
        return current_df, insights
        
    except Exception as e:
        print(f"❌ Error in fetch_sheet_data: {e}")
        import traceback
        traceback.print_exc()
        raise