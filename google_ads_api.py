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
        # Load service account from base64 environment variable
        b64_key = os.getenv("GOOGLE_CREDENTIALS_B64")
        if not b64_key:
            raise ValueError("Missing GOOGLE_CREDENTIALS_B64 environment variable")

        key_data = base64.b64decode(b64_key).decode("utf-8")
        creds_dict = json.loads(key_data)

        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)

        # Load sheet data
        print(f"📋 Connecting to Google Sheets: {SHEET_ID}")
        sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)
        
        # Get all data starting from row 2 (skip header row 1)
        all_data = sheet.get_all_values()
        print(f"📊 Raw data loaded: {len(all_data)} rows")
        
        if len(all_data) < 2:
            raise ValueError("No data found in sheet (need at least header + 1 data row)")
        
        # Use row 2 as headers (your actual headers)
        headers = all_data[1]  # Row 2 contains the real headers
        data_rows = all_data[2:]  # Data starts from row 3
        
        print(f"🔍 Headers found: {headers}")
        print(f"📝 Data rows: {len(data_rows)}")
        
        # Create DataFrame
        df = pd.DataFrame(data_rows, columns=headers)
        
        # Remove completely empty rows
        df = df.dropna(how='all')
        
        # Clean column names - remove extra spaces and normalize
        df.columns = [str(col).strip() for col in df.columns]
        print(f"📋 Cleaned columns: {list(df.columns)}")
        
        # Show first few rows for debugging
        print(f"🔍 First 3 rows of data:")
        for i, row in df.head(3).iterrows():
            print(f"   Row {i}: {dict(row)}")
        
        return df
        
    except Exception as e:
        print(f"❌ Error in load_campaign_data: {e}")
        print(f"🔍 Full error details: {str(e)}")
        raise

def clean_and_map_columns(df):
    """Clean and map columns to standard names with extensive debugging"""
    print(f"🔧 Starting column mapping...")
    print(f"📋 Original columns: {list(df.columns)}")
    
    # Create a mapping dictionary - be very flexible with column names
    column_mapping = {}
    
    for col in df.columns:
        col_lower = str(col).lower().strip()
        
        # Map to standard names
        if 'date' in col_lower:
            column_mapping[col] = 'date'
        elif 'campaign' in col_lower and 'name' in col_lower:
            column_mapping[col] = 'campaign'
        elif col_lower == 'impressions':
            column_mapping[col] = 'impressions'
        elif col_lower == 'clicks':
            column_mapping[col] = 'clicks'
        elif 'ctr' in col_lower:
            column_mapping[col] = 'ctr_raw'
        elif 'conversion' in col_lower and 'micros' not in col_lower:
            column_mapping[col] = 'conversions'
        elif 'impression' in col_lower and 'share' in col_lower:
            column_mapping[col] = 'impression_share'
        elif 'cost' in col_lower or 'spend' in col_lower:
            column_mapping[col] = 'spend'
    
    print(f"🗺️ Column mapping: {column_mapping}")
    
    # Apply mapping
    df_mapped = df.rename(columns=column_mapping)
    
    # Ensure we have required columns
    required_cols = ['campaign', 'impressions', 'clicks']
    missing_cols = [col for col in required_cols if col not in df_mapped.columns]
    
    if missing_cols:
        print(f"❌ Missing required columns: {missing_cols}")
        print(f"📋 Available columns after mapping: {list(df_mapped.columns)}")
        
        # Try to find columns with similar names
        for missing_col in missing_cols:
            for orig_col in df.columns:
                if missing_col.lower() in str(orig_col).lower():
                    print(f"💡 Found similar column '{orig_col}' for '{missing_col}'")
                    df_mapped[missing_col] = df[orig_col]
                    break
    
    print(f"✅ Final columns: {list(df_mapped.columns)}")
    return df_mapped

def add_kpis(df):
    """Add KPIs with extensive error handling and debugging"""
    print(f"🧮 Starting KPI calculations...")
    print(f"📊 DataFrame shape: {df.shape}")
    
    # Filter for most recent date and valid campaigns
    if 'date' in df.columns:
        # Remove empty dates
        df = df[df['date'].notna() & (df['date'] != '')]
        
        if len(df) == 0:
            print("⚠️ No rows with valid dates found")
            return create_empty_dataframe()
        
        # Convert date and get latest
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df = df.dropna(subset=['date'])
        
        if len(df) == 0:
            print("⚠️ No rows with valid date formats found")
            return create_empty_dataframe()
        
        latest_date = df['date'].max()
        df = df[df['date'] == latest_date]
        print(f"📅 Using data from: {latest_date.strftime('%Y-%m-%d')}")
    
    # Filter for valid campaigns
    if 'campaign' in df.columns:
        df = df[df['campaign'].notna() & (df['campaign'] != '')]
        
    if len(df) == 0:
        print("⚠️ No valid campaign data found")
        return create_empty_dataframe()
    
    print(f"📊 Working with {len(df)} campaigns")
    
    # Clean numeric columns with extensive debugging
    numeric_columns = ['impressions', 'clicks', 'conversions']
    
    for col in numeric_columns:
        if col in df.columns:
            print(f"🔢 Processing column '{col}'...")
            original_values = df[col].head(3).tolist()
            print(f"   Original values: {original_values}")
            
            # Convert to string, remove common characters, then to numeric
            df[col] = df[col].astype(str)
            df[col] = df[col].str.replace(r'[€$,%]', '', regex=True)
            df[col] = df[col].str.replace(',', '')  # Remove thousands separators
            df[col] = pd.to_numeric(df[col], errors='coerce')
            df[col] = df[col].fillna(0)
            
            cleaned_values = df[col].head(3).tolist()
            print(f"   Cleaned values: {cleaned_values}")
        else:
            print(f"⚠️ Column '{col}' not found, setting to 0")
            df[col] = 0
    
    # Handle CTR specifically
    if 'ctr_raw' in df.columns:
        print(f"🎯 Processing CTR...")
        df['ctr_raw'] = df['ctr_raw'].astype(str).str.replace('%', '').str.replace('€', '')
        df['ctr'] = pd.to_numeric(df['ctr_raw'], errors='coerce').fillna(0)
        print(f"   CTR values: {df['ctr'].head(3).tolist()}")
    else:
        print(f"🧮 Calculating CTR from impressions and clicks...")
        df['ctr'] = ((df['clicks'] / df['impressions']) * 100).round(2)
        df['ctr'] = df['ctr'].replace([float('inf'), -float('inf')], 0).fillna(0)
    
    # Estimate spend (since you don't have real spend data)
    print(f"💰 Estimating spend based on campaign types...")
    def estimate_cpc(campaign_name):
        campaign_lower = str(campaign_name).lower()
        if 'search' in campaign_lower:
            return 0.25
        elif 'performance max' in campaign_lower or 'pmax' in campaign_lower:
            return 0.18
        elif 'demand gen' in campaign_lower or 'display' in campaign_lower:
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
    
    df['quality_score'] = 7.5  # Placeholder
    
    print(f"✅ KPI calculations completed")
    print(f"📊 Final data summary:")
    print(f"   Total impressions: {df['impressions'].sum():,.0f}")
    print(f"   Total clicks: {df['clicks'].sum():,.0f}")
    print(f"   Estimated spend: €{df['spend'].sum():.2f}")
    print(f"   Average CTR: {df['ctr'].mean():.2f}%")
    
    return df

def create_empty_dataframe():
    """Create an empty dataframe with required columns"""
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
    """Generate summary stats with safety checks"""
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

def generate_insights(df):
    """Generate insights with safety checks"""
    print(f"🔍 Generating insights...")
    
    if df.empty:
        print("⚠️ No data available for insights")
        return {
            'summary': generate_summary_stats(df),
            'highlights': [
                {'metric': '📊 Status', 'campaign': 'No Data', 'value': 'No campaigns found', 'trend': '', 'change': 0}
            ],
            'campaigns': []
        }
    
    # Generate summary
    summary = generate_summary_stats(df)
    
    # Find top performers safely
    highlights = []
    
    if df['clicks'].sum() > 0:
        most_clicks_idx = df['clicks'].idxmax()
        most_clicks = df.iloc[most_clicks_idx]
        highlights.append({
            'metric': '🥇 Most Clicks',
            'campaign': str(most_clicks['campaign'])[:30],
            'value': f"{int(most_clicks['clicks']):,}",
            'trend': '',
            'change': 0
        })
    
    if df['impressions'].sum() > 0:
        most_impressions_idx = df['impressions'].idxmax()
        most_impressions = df.iloc[most_impressions_idx]
        highlights.append({
            'metric': '👁️ Most Impressions',
            'campaign': str(most_impressions['campaign'])[:30],
            'value': f"{int(most_impressions['impressions']):,}",
            'trend': '',
            'change': 0
        })
    
    if df['ctr'].sum() > 0:
        best_ctr_idx = df['ctr'].idxmax()
        best_ctr = df.iloc[best_ctr_idx]
        highlights.append({
            'metric': '🎯 Best CTR',
            'campaign': str(best_ctr['campaign'])[:30],
            'value': f"{best_ctr['ctr']:.2f}%",
            'trend': '',
            'change': 0
        })
    
    if df['conversions'].sum() > 0:
        best_conv_idx = df['conversion_rate'].idxmax()
        best_conv = df.iloc[best_conv_idx]
        highlights.append({
            'metric': '🔄 Best Conv. Rate',
            'campaign': str(best_conv['campaign'])[:30],
            'value': f"{best_conv['conversion_rate']:.2f}%",
            'trend': '',
            'change': 0
        })
    
    # Add impression share highlight
    if len(highlights) < 5:
        best_imp_share_idx = df['impression_share'].idxmax()
        best_imp_share = df.iloc[best_imp_share_idx]
        highlights.append({
            'metric': '📊 Best Imp. Share',
            'campaign': str(best_imp_share['campaign'])[:30],
            'value': f"{best_imp_share['impression_share']:.1f}%",
            'trend': '',
            'change': 0
        })
    
    if not highlights:
        highlights = [
            {'metric': '📊 Status', 'campaign': 'Data Available', 'value': f'{len(df)} campaigns', 'trend': '', 'change': 0}
        ]
    
    print(f"✅ Generated {len(highlights)} highlights")
    
    return {
        'summary': summary,
        'highlights': highlights,
        'campaigns': df.to_dict('records')
    }

def create_enhanced_charts(df):
    """Create charts with safety checks"""
    print(f"📊 Creating charts...")
    os.makedirs("static", exist_ok=True)
    
    if df.empty:
        # Create placeholder chart
        plt.figure(figsize=(10, 6))
        plt.text(0.5, 0.5, 'No data available\nCheck your Google Sheets connection', 
                ha='center', va='center', fontsize=16, 
                bbox=dict(boxstyle="round,pad=0.5", facecolor="lightgray"))
        plt.xlim(0, 1)
        plt.ylim(0, 1)
        plt.axis('off')
        plt.title("Google Ads Spend Overview", fontsize=14, fontweight='bold')
        plt.savefig("static/spend_chart.png", dpi=150, bbox_inches='tight')
        plt.close()
        print("📊 Created placeholder chart")
        return
    
    # Create spend chart
    campaigns = [str(name)[:15] + "..." if len(str(name)) > 15 else str(name) for name in df['campaign']]
    
    plt.figure(figsize=(12, 6))
    bars = plt.bar(campaigns, df['spend'], color='#667eea', alpha=0.8)
    plt.title("Estimated Daily Spend by Campaign", fontsize=14, fontweight='bold', pad=20)
    plt.ylabel("Spend (€)")
    plt.xticks(rotation=45, ha='right')
    
    # Add value labels on bars
    for bar, spend in zip(bars, df['spend']):
        if spend > 0:
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                    f'€{spend:.1f}', ha='center', va='bottom', fontsize=10)
    
    plt.tight_layout()
    plt.savefig("static/spend_chart.png", dpi=150, bbox_inches='tight')
    plt.close()
    print("📊 Created spend chart successfully")

def fetch_sheet_data():
    """Main function with comprehensive error handling"""
    try:
        print(f"🚀 Starting Google Ads data fetch...")
        
        # Load and process data
        df_raw = load_campaign_data()
        df_mapped = clean_and_map_columns(df_raw)
        df_final = add_kpis(df_mapped)
        
        # Save data for trend analysis
        today = datetime.date.today()
        os.makedirs(DATA_DIR, exist_ok=True)
        df_final.to_csv(f"{DATA_DIR}/ads_{today.strftime('%Y-%m-%d')}.csv", index=False)
        print(f"💾 Data saved for future trend analysis")
        
        # Create charts
        create_enhanced_charts(df_final)
        
        # Generate insights
        insights = generate_insights(df_final)
        
        print(f"✅ Data fetch completed successfully!")
        print(f"📊 Processed {len(df_final)} campaigns with {insights['summary']['total_clicks']} total clicks")
        
        return df_final, insights
        
    except Exception as e:
        print(f"❌ Critical error in fetch_sheet_data: {e}")
        import traceback
        print(f"🔍 Full traceback:")
        traceback.print_exc()
        raise