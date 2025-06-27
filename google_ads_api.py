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
        
        # Print first 10 rows to debug
        print("🔍 First 10 rows of raw data:")
        for i, row in enumerate(all_data[:10]):
            print(f"Row {i}: {row}")
        
        if len(all_data) < 3:
            print("⚠️ Not enough data rows found")
            return create_empty_dataframe()
        
        # Look for the actual data - skip header rows
        data_start_row = None
        for i, row in enumerate(all_data):
            # Look for a row that has a date-like pattern and campaign name
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
            headers = ['Date', 'Campaign Name', 'Impressions', 'Clicks', 'Ctr', 'Conversions', 'Average Target Cpa Micros', 'Search Impression Share']
        
        data_rows = all_data[data_start_row:]
        
        print(f"🔍 Using headers: {headers}")
        print(f"📝 Data rows available: {len(data_rows)}")
        print(f"📝 First 3 data rows:")
        for i, row in enumerate(data_rows[:3]):
            print(f"  {i}: {row}")
        
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
        print(f"📊 Sample data:")
        print(df.head())
        
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
        'Average Target Cpa Micros': [],
        'Search Impression Share': []
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
        elif 'conversion' in col_lower and 'micros' not in col_lower:
            column_mapping[col] = 'conversions'
        elif 'impression' in col_lower and 'share' in col_lower:
            column_mapping[col] = 'impression_share'
    
    print(f"🗺️ Column mapping: {column_mapping}")
    
    df_mapped = df.rename(columns=column_mapping)
    print(f"📋 Mapped columns: {list(df_mapped.columns)}")
    
    return df_mapped

def filter_for_date(df, target_date):
    """Filter data for a specific date"""
    if df.empty or 'date' not in df.columns:
        print(f"⚠️ Cannot filter by date - empty df or no date column")
        return df
    
    print(f"📅 Filtering for date: {target_date}")
    print(f"📊 Before filtering: {len(df)} rows")
    
    # Clean and parse dates
    df_copy = df.copy()
    df_copy = df_copy[df_copy['date'].notna() & (df_copy['date'] != '')]
    
    print(f"📊 After removing empty dates: {len(df_copy)} rows")
    
    if len(df_copy) == 0:
        return df_copy
    
    # Show sample dates
    print(f"📅 Sample date values: {df_copy['date'].head(5).tolist()}")
    
    # Parse dates
    df_copy['date_parsed'] = pd.to_datetime(df_copy['date'], errors='coerce')
    df_copy = df_copy.dropna(subset=['date_parsed'])
    
    print(f"📊 After parsing dates: {len(df_copy)} rows")
    
    if len(df_copy) == 0:
        return df_copy
    
    # Show parsed dates
    print(f"📅 Sample parsed dates: {df_copy['date_parsed'].head(5).tolist()}")
    
    # Filter for target date
    df_filtered = df_copy[df_copy['date_parsed'].dt.date == target_date]
    
    print(f"📊 After filtering for {target_date}: {len(df_filtered)} rows")
    
    if len(df_filtered) > 0:
        print(f"✅ Found data for {target_date}")
        print(f"📊 Sample filtered data:")
        print(df_filtered[['date', 'campaign', 'impressions', 'clicks']].head())
    
    return df_filtered.drop('date_parsed', axis=1)

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
            print(f"🔢 Processing {col}: {df[col].head(3).tolist()}")
            df[col] = df[col].astype(str).str.replace(r'[€$,%]', '', regex=True)
            df[col] = df[col].str.replace(',', '')
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            print(f"✅ Cleaned {col}: {df[col].head(3).tolist()}")
        else:
            print(f"⚠️ Column {col} not found, setting to 0")
            df[col] = 0
    
    # Handle CTR
    if 'ctr_raw' in df.columns:
        print(f"🎯 Processing CTR: {df['ctr_raw'].head(3).tolist()}")
        df['ctr_raw'] = df['ctr_raw'].astype(str).str.replace('%', '').str.replace('€', '')
        df['ctr'] = pd.to_numeric(df['ctr_raw'], errors='coerce').fillna(0)
        print(f"✅ Cleaned CTR: {df['ctr'].head(3).tolist()}")
    else:
        print("🧮 Calculating CTR from impressions and clicks")
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
    if 'impression_share' in df.columns:
        df['impression_share'] = df['impression_share'].astype(str).str.replace('%', '')
        df['impression_share'] = pd.to_numeric(df['impression_share'], errors='coerce').fillna(75.0)
    else:
        df['impression_share'] = 75.0
    
    df['quality_score'] = 7.5
    
    print(f"✅ KPIs added successfully")
    print(f"📊 Final summary:")
    print(f"   Campaigns: {len(df)}")
    print(f"   Total impressions: {df['impressions'].sum():,.0f}")
    print(f"   Total clicks: {df['clicks'].sum():,.0f}")
    print(f"   Total spend (est): €{df['spend'].sum():.2f}")
    
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
        'impression_share': [],
        'quality_score': []
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
        'avg_impression_share': round(df['impression_share'].mean(), 1)
    }

def generate_insights(df, yesterday_df=None):
    summary = generate_summary_stats(df)
    
    if df.empty:
        return {
            'summary': summary,
            'summary_trends': {},
            'highlights': [
                {'metric': '📊 Status', 'campaign': 'No Data', 'value': 'No campaigns found', 'trend': '', 'change': 0}
            ],
            'campaigns': []
        }
    
    highlights = []
    
    if df['clicks'].sum() > 0:
        most_clicks_idx = df['clicks'].idxmax()
        most_clicks = df.loc[most_clicks_idx]
        highlights.append({
            'metric': '🥇 Most Clicks',
            'campaign': str(most_clicks['campaign'])[:30],
            'value': f"{int(most_clicks['clicks']):,}",
            'trend': '',
            'change': 0
        })
    
    if df['impressions'].sum() > 0:
        most_impressions_idx = df['impressions'].idxmax()
        most_impressions = df.loc[most_impressions_idx]
        highlights.append({
            'metric': '👁️ Most Impressions',
            'campaign': str(most_impressions['campaign'])[:30],
            'value': f"{int(most_impressions['impressions']):,}",
            'trend': '',
            'change': 0
        })
    
    if df['ctr'].sum() > 0:
        best_ctr_idx = df['ctr'].idxmax()
        best_ctr = df.loc[best_ctr_idx]
        highlights.append({
            'metric': '🎯 Best CTR',
            'campaign': str(best_ctr['campaign'])[:30],
            'value': f"{best_ctr['ctr']:.2f}%",
            'trend': '',
            'change': 0
        })
    
    if not highlights:
        highlights = [
            {'metric': '📊 Status', 'campaign': 'Data Available', 'value': f'{len(df)} campaigns', 'trend': '', 'change': 0}
        ]
    
    return {
        'summary': summary,
        'summary_trends': {},
        'highlights': highlights,
        'campaigns': df.to_dict('records')
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
            return create_processed_empty_dataframe(), generate_insights(create_processed_empty_dataframe())
        
        df_all_mapped = clean_and_map_columns(df_all)
        
        # Try today first, then yesterday if no today data
        today_df = filter_for_date(df_all_mapped, today)
        
        if today_df.empty:
            print(f"⚠️ No data for today ({today}), trying yesterday")
            yesterday = today - datetime.timedelta(days=1)
            today_df = filter_for_date(df_all_mapped, yesterday)
            
            if today_df.empty:
                print(f"⚠️ No data for yesterday ({yesterday}) either, using latest available")
                # Use the most recent data available
                if 'date' in df_all_mapped.columns:
                    df_all_mapped['date_parsed'] = pd.to_datetime(df_all_mapped['date'], errors='coerce')
                    df_all_mapped = df_all_mapped.dropna(subset=['date_parsed'])
                    if not df_all_mapped.empty:
                        latest_date = df_all_mapped['date_parsed'].max().date()
                        today_df = filter_for_date(df_all_mapped, latest_date)
                        print(f"📅 Using latest available date: {latest_date}")
        
        if today_df.empty:
            print("❌ Still no data found")
            return create_processed_empty_dataframe(), generate_insights(create_processed_empty_dataframe())
        
        # Process the data
        today_df = add_kpis(today_df)
        
        # Save data
        os.makedirs(DATA_DIR, exist_ok=True)
        today_df.to_csv(f"{DATA_DIR}/ads_{today.strftime('%Y-%m-%d')}.csv", index=False)
        
        # Create charts
        create_enhanced_charts(today_df)
        
        # Generate insights
        insights = generate_insights(today_df)
        
        print(f"✅ Successfully processed {len(today_df)} campaigns")
        return today_df, insights
        
    except Exception as e:
        print(f"❌ Error in fetch_sheet_data: {e}")
        import traceback
        traceback.print_exc()
        raise