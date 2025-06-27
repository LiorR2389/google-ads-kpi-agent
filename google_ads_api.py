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
    sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)
    data = sheet.get_all_records(head=2)
    df = pd.DataFrame(data)
    
    print(f"📊 Loaded {len(df)} rows from Google Sheets")
    print(f"🔍 Columns found: {list(df.columns)}")

    # Clean column names
    df.columns = [col.strip().lower().replace(' ', '_') for col in df.columns]
    
    # Map your actual columns to standard names
    column_mapping = {
        'date': 'date',
        'campaign_name': 'campaign',
        'impressions': 'impressions', 
        'clicks': 'clicks',
        'ctr': 'ctr_raw',
        'conversions': 'conversions',
        'average_target_cpa_micros': 'target_cpa_micros',
        'search_impression_share': 'impression_share'
    }
    
    # Rename columns
    for old_name, new_name in column_mapping.items():
        if old_name in df.columns:
            df = df.rename(columns={old_name: new_name})
    
    # Filter for today's date only (most recent data)
    if 'date' in df.columns:
        # Convert date column to datetime
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        # Get the most recent date's data
        latest_date = df['date'].max()
        df = df[df['date'] == latest_date]
        print(f"📅 Using data from: {latest_date.strftime('%Y-%m-%d')}")
    
    # Remove empty rows
    df = df.dropna(subset=['campaign'])
    df = df[df['campaign'].str.strip() != '']
    
    print(f"✅ Final dataset: {len(df)} campaigns")
    return df

def add_kpis(df):
    # Clean and convert numeric columns
    numeric_columns = ['clicks', 'impressions', 'conversions']
    
    for col in numeric_columns:
        if col in df.columns:
            # Convert to string first, then clean
            df[col] = df[col].astype(str).str.replace(r'[€$,]', '', regex=True)
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # Clean CTR (remove % sign if present)
    if 'ctr_raw' in df.columns:
        df['ctr_raw'] = df['ctr_raw'].astype(str).str.replace('%', '').str.replace('€', '')
        df['ctr'] = pd.to_numeric(df['ctr_raw'], errors='coerce').fillna(0)
    else:
        # Calculate CTR if not provided
        df['ctr'] = ((df['clicks'] / df['impressions']) * 100).round(2)
        df['ctr'] = df['ctr'].fillna(0)
    
    # Clean impression share
    if 'impression_share' in df.columns:
        df['impression_share'] = df['impression_share'].astype(str).str.replace('%', '')
        df['impression_share'] = pd.to_numeric(df['impression_share'], errors='coerce').fillna(0)
    else:
        df['impression_share'] = 75.0  # Default value
    
    # CALCULATE ESTIMATED SPEND based on industry averages
    # Since you don't have spend data, we'll estimate it
    print("⚠️ No spend data found - calculating estimates based on industry averages")
    
    # Estimate CPC based on campaign type and performance
    def estimate_cpc(row):
        campaign_name = str(row['campaign']).lower()
        if 'search' in campaign_name:
            return 0.25  # Search campaigns typically €0.15-0.35
        elif 'performance max' in campaign_name or 'pmax' in campaign_name:
            return 0.18  # Performance Max typically €0.12-0.25  
        elif 'demand gen' in campaign_name or 'display' in campaign_name:
            return 0.05  # Display/Demand Gen typically €0.03-0.08
        else:
            return 0.20  # Default
    
    df['cpc'] = df.apply(estimate_cpc, axis=1)
    df['spend'] = (df['clicks'] * df['cpc']).round(2)
    
    # Calculate other KPIs
    df['conversion_rate'] = ((df['conversions'] / df['clicks']) * 100).round(2)
    df['conversion_rate'] = df['conversion_rate'].replace([float('inf'), -float('inf')], 0).fillna(0)
    
    df['cost_per_conversion'] = (df['spend'] / df['conversions']).round(2)
    df['cost_per_conversion'] = df['cost_per_conversion'].replace([float('inf'), -float('inf')], 0).fillna(0)
    
    # Add quality score placeholder
    df['quality_score'] = 7.5
    
    print("💰 Spend estimates calculated based on industry benchmarks")
    return df

def get_yesterday_file(today):
    yesterday = today - datetime.timedelta(days=1)
    filename = f"{DATA_DIR}/ads_{yesterday.strftime('%Y-%m-%d')}.csv"
    return filename if os.path.exists(filename) else None

def add_trend_arrows(df, prev_df):
    if prev_df.empty:
        return df
        
    merged = df.merge(prev_df, on="campaign", suffixes=("", "_prev"))
    
    trend_columns = ['clicks', 'spend', 'impressions', 'ctr', 'cpc', 'conversions', 'conversion_rate']
    
    for col in trend_columns:
        if col in df.columns:
            trend_col = f"{col}_trend"
            df[trend_col] = ""
            df[f"{col}_change"] = 0
            
            for idx, row in merged.iterrows():
                today_val = row[col] if not pd.isna(row[col]) else 0
                yest_val = row[f"{col}_prev"] if not pd.isna(row[f"{col}_prev"]) else 0
                
                if yest_val == 0:
                    arrow = "🆕" if today_val > 0 else ""
                    change = 0
                elif today_val > yest_val:
                    arrow = "⬆️"
                    change = round(((today_val - yest_val) / yest_val) * 100, 1)
                elif today_val < yest_val:
                    arrow = "⬇️"
                    change = round(((today_val - yest_val) / yest_val) * 100, 1)
                else:
                    arrow = "➡️"
                    change = 0
                
                campaign_mask = df['campaign'] == row['campaign']
                df.loc[campaign_mask, trend_col] = arrow
                df.loc[campaign_mask, f"{col}_change"] = change
    
    return df

def generate_summary_stats(df):
    """Generate overall summary statistics"""
    summary = {
        'total_spend': round(df['spend'].sum(), 2),
        'total_clicks': int(df['clicks'].sum()),
        'total_impressions': int(df['impressions'].sum()),
        'total_conversions': int(df['conversions'].sum()),
        'avg_ctr': round(df['ctr'].mean(), 2),
        'avg_cpc': round(df['cpc'].mean(), 2),
        'avg_conversion_rate': round(df['conversion_rate'].mean(), 2),
        'avg_impression_share': round(df['impression_share'].mean(), 1)
    }
    return summary

def generate_insights(df):
    """Generate insights with your actual data structure"""
    if df.empty:
        print("⚠️ No data to generate insights")
        return {
            'summary': {'total_spend': 0, 'total_clicks': 0, 'total_impressions': 0, 'total_conversions': 0, 'avg_ctr': 0, 'avg_cpc': 0, 'avg_conversion_rate': 0},
            'highlights': [],
            'campaigns': []
        }
    
    # Find best performers
    most_clicks_idx = df['clicks'].idxmax() if df['clicks'].sum() > 0 else 0
    most_impressions_idx = df['impressions'].idxmax() if df['impressions'].sum() > 0 else 0
    best_ctr_idx = df['ctr'].idxmax() if df['ctr'].sum() > 0 else 0
    best_conversion_rate_idx = df['conversion_rate'].idxmax() if df['conversion_rate'].sum() > 0 else 0
    highest_impression_share_idx = df['impression_share'].idxmax() if df['impression_share'].sum() > 0 else 0
    
    most_clicks = df.iloc[most_clicks_idx]
    most_impressions = df.iloc[most_impressions_idx] 
    best_ctr = df.iloc[best_ctr_idx]
    best_conversion_rate = df.iloc[best_conversion_rate_idx]
    highest_impression_share = df.iloc[highest_impression_share_idx]
    
    # Generate summary stats
    summary = generate_summary_stats(df)
    
    # Create insights
    insights_data = {
        'summary': summary,
        'highlights': [
            {
                'metric': '🥇 Most Clicks',
                'campaign': most_clicks['campaign'][:30],
                'value': f"{int(most_clicks['clicks']):,}",
                'trend': most_clicks.get('clicks_trend', ''),
                'change': most_clicks.get('clicks_change', 0)
            },
            {
                'metric': '👁️ Most Impressions', 
                'campaign': most_impressions['campaign'][:30],
                'value': f"{int(most_impressions['impressions']):,}",
                'trend': most_impressions.get('impressions_trend', ''),
                'change': most_impressions.get('impressions_change', 0)
            },
            {
                'metric': '🎯 Best CTR',
                'campaign': best_ctr['campaign'][:30],
                'value': f"{best_ctr['ctr']:.2f}%",
                'trend': best_ctr.get('ctr_trend', ''),
                'change': best_ctr.get('ctr_change', 0)
            },
            {
                'metric': '🔄 Best Conv. Rate',
                'campaign': best_conversion_rate['campaign'][:30],
                'value': f"{best_conversion_rate['conversion_rate']:.2f}%",
                'trend': best_conversion_rate.get('conversion_rate_trend', ''),
                'change': best_conversion_rate.get('conversion_rate_change', 0)
            },
            {
                'metric': '📊 Best Imp. Share',
                'campaign': highest_impression_share['campaign'][:30],
                'value': f"{highest_impression_share['impression_share']:.1f}%",
                'trend': '',
                'change': 0
            }
        ],
        'campaigns': df.to_dict('records')
    }
    
    return insights_data

def create_enhanced_charts(df):
    """Create charts with your actual data"""
    os.makedirs("static", exist_ok=True)
    
    if df.empty:
        # Create placeholder chart
        plt.figure(figsize=(10, 6))
        plt.text(0.5, 0.5, 'No data available', ha='center', va='center', fontsize=16)
        plt.xlim(0, 1)
        plt.ylim(0, 1)
        plt.axis('off')
        plt.savefig("static/spend_chart.png", dpi=150, bbox_inches='tight')
        plt.close()
        return
    
    # Truncate campaign names for display
    campaigns = [name[:20] + "..." if len(name) > 20 else name for name in df['campaign']]
    
    # Create spend chart
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
    
    # Create performance overview chart
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle('Google Ads Performance Dashboard', fontsize=16, fontweight='bold')
    
    # 1. Clicks by Campaign
    ax1.bar(campaigns, df['clicks'], color='#28a745', alpha=0.8)
    ax1.set_title('Clicks by Campaign', fontweight='bold')
    ax1.set_ylabel('Clicks')
    ax1.tick_params(axis='x', rotation=45)
    
    # 2. CTR by Campaign  
    ax2.barh(campaigns, df['ctr'], color='#ffc107', alpha=0.8)
    ax2.set_title('Click-Through Rate by Campaign', fontweight='bold')
    ax2.set_xlabel('CTR (%)')
    
    # 3. Impressions vs Clicks
    ax3.scatter(df['impressions'], df['clicks'], s=100, alpha=0.7, color='#dc3545')
    ax3.set_title('Impressions vs Clicks', fontweight='bold')
    ax3.set_xlabel('Impressions')
    ax3.set_ylabel('Clicks')
    
    # 4. Conversion Rate by Campaign
    if df['conversions'].sum() > 0:
        ax4.bar(campaigns, df['conversion_rate'], color='#17a2b8', alpha=0.8)
        ax4.set_title('Conversion Rate by Campaign', fontweight='bold')
        ax4.set_ylabel('Conversion Rate (%)')
        ax4.tick_params(axis='x', rotation=45)
    else:
        ax4.text(0.5, 0.5, 'No conversions data', ha='center', va='center', transform=ax4.transAxes)
        ax4.set_title('Conversion Rate by Campaign', fontweight='bold')
    
    plt.tight_layout()
    plt.savefig("static/dashboard.png", dpi=150, bbox_inches='tight')
    plt.close()
    
    print("📊 Charts created successfully")

def fetch_sheet_data():
    try:
        today = datetime.date.today()
        print(f"🚀 Starting data fetch for {today}")
        
        df = load_campaign_data()
        df = add_kpis(df)

        os.makedirs(DATA_DIR, exist_ok=True)
        
        # Load previous day's data for trend analysis
        yesterday_file = get_yesterday_file(today)
        if yesterday_file and os.path.exists(yesterday_file):
            print("📈 Loading previous day data for trends")
            prev_df = pd.read_csv(yesterday_file)
            prev_df = add_kpis(prev_df)
            df = add_trend_arrows(df, prev_df)
        else:
            print("ℹ️ No previous day data found - skipping trend analysis")

        # Save current data
        df.to_csv(f"{DATA_DIR}/ads_{today.strftime('%Y-%m-%d')}.csv", index=False)
        print(f"💾 Data saved to {DATA_DIR}/ads_{today.strftime('%Y-%m-%d')}.csv")

        # Create charts
        create_enhanced_charts(df)
        
        # Generate insights
        insights = generate_insights(df)
        
        print("✅ Data processing completed successfully")
        return df, insights
        
    except Exception as e:
        print(f"❌ Error in fetch_sheet_data: {e}")
        raise