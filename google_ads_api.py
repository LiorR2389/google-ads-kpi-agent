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

    # Normalize column names
    df.columns = [col.strip().lower().replace(' ', '_') for col in df.columns]
    
    # Map columns to standard names - update these based on your actual sheet columns
    column_mapping = {
        'campaign_name': 'campaign',
        'campaign': 'campaign',
        'clicks': 'clicks',
        'average_cost': 'spend',
        'cost': 'spend',
        'impressions': 'impressions',
        'impr.': 'impressions',
        'ctr': 'ctr_raw',
        'click-through_rate': 'ctr_raw',
        'conversions': 'conversions',
        'conv.': 'conversions',
        'cost_/_conv.': 'cost_per_conversion',
        'cost_per_conversion': 'cost_per_conversion',
        'avg._cpc': 'avg_cpc',
        'average_cpc': 'avg_cpc'
    }
    
    # Rename columns based on mapping
    for old_name, new_name in column_mapping.items():
        if old_name in df.columns:
            df = df.rename(columns={old_name: new_name})
    
    # Ensure we have required columns, create with defaults if missing
    required_columns = ['campaign', 'clicks', 'spend', 'impressions', 'conversions']
    for col in required_columns:
        if col not in df.columns:
            df[col] = 0
    
    return df

def add_kpis(df):
    # Clean and convert numeric columns
    numeric_columns = ['spend', 'clicks', 'impressions', 'conversions']
    
    for col in numeric_columns:
        if col in df.columns:
            # Remove currency symbols and convert to numeric
            df[col] = df[col].astype(str).str.replace(r'[€$,]', '', regex=True)
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # Calculate KPIs
    df['ctr'] = ((df['clicks'] / df['impressions']) * 100).round(2)
    df['ctr'] = df['ctr'].fillna(0)
    
    df['cpc'] = (df['spend'] / df['clicks']).round(2)
    df['cpc'] = df['cpc'].replace([float('inf'), -float('inf')], 0).fillna(0)
    
    df['conversion_rate'] = ((df['conversions'] / df['clicks']) * 100).round(2)
    df['conversion_rate'] = df['conversion_rate'].replace([float('inf'), -float('inf')], 0).fillna(0)
    
    df['cost_per_conversion'] = (df['spend'] / df['conversions']).round(2)
    df['cost_per_conversion'] = df['cost_per_conversion'].replace([float('inf'), -float('inf')], 0).fillna(0)
    
    # Calculate impression share (placeholder - would need actual data from Google Ads)
    df['impression_share'] = 75.0  # Placeholder
    
    # Calculate quality score (placeholder - would need actual data from Google Ads)
    df['quality_score'] = 7.5  # Placeholder
    
    return df

def get_yesterday_file(today):
    yesterday = today - datetime.timedelta(days=1)
    filename = f"{DATA_DIR}/ads_{yesterday.strftime('%Y-%m-%d')}.csv"
    return filename if os.path.exists(filename) else None

def add_trend_arrows(df, prev_df):
    merged = df.merge(prev_df, on="campaign", suffixes=("", "_prev"))
    
    trend_columns = ['clicks', 'spend', 'impressions', 'ctr', 'cpc', 'conversions', 'conversion_rate', 'cost_per_conversion']
    
    for col in trend_columns:
        if col in df.columns and f"{col}_prev" in merged.columns:
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
        'total_spend': df['spend'].sum(),
        'total_clicks': int(df['clicks'].sum()),
        'total_impressions': int(df['impressions'].sum()),
        'total_conversions': int(df['conversions'].sum()),
        'avg_ctr': round(df['ctr'].mean(), 2),
        'avg_cpc': round(df['cpc'].mean(), 2),
        'avg_conversion_rate': round(df['conversion_rate'].mean(), 2)
    }
    return summary

def generate_insights(df):
    """Generate insights with enhanced metrics"""
    # Find best/worst performers
    most_clicks = df.loc[df['clicks'].idxmax()] if df['clicks'].sum() > 0 else df.iloc[0]
    best_ctr = df.loc[df['ctr'].idxmax()] if df['ctr'].sum() > 0 else df.iloc[0]
    worst_ctr = df.loc[df['ctr'].idxmin()] if df['ctr'].sum() > 0 else df.iloc[0]
    best_cpc = df.loc[df['cpc'].idxmin()] if df['cpc'].sum() > 0 else df.iloc[0]
    worst_cpc = df.loc[df['cpc'].idxmax()] if df['cpc'].sum() > 0 else df.iloc[0]
    most_impressions = df.loc[df['impressions'].idxmax()] if df['impressions'].sum() > 0 else df.iloc[0]
    
    # Generate summary stats
    summary = generate_summary_stats(df)
    
    # Create enhanced insights
    insights_data = {
        'summary': summary,
        'highlights': [
            {
                'metric': '🥇 Most Clicks',
                'campaign': most_clicks['campaign'],
                'value': f"{int(most_clicks['clicks']):,}",
                'trend': most_clicks.get('clicks_trend', ''),
                'change': most_clicks.get('clicks_change', 0)
            },
            {
                'metric': '👁️ Most Impressions', 
                'campaign': most_impressions['campaign'],
                'value': f"{int(most_impressions['impressions']):,}",
                'trend': most_impressions.get('impressions_trend', ''),
                'change': most_impressions.get('impressions_change', 0)
            },
            {
                'metric': '🎯 Best CTR',
                'campaign': best_ctr['campaign'],
                'value': f"{best_ctr['ctr']:.2f}%",
                'trend': best_ctr.get('ctr_trend', ''),
                'change': best_ctr.get('ctr_change', 0)
            },
            {
                'metric': '💰 Lowest CPC',
                'campaign': best_cpc['campaign'],
                'value': f"€{best_cpc['cpc']:.2f}",
                'trend': best_cpc.get('cpc_trend', ''),
                'change': best_cpc.get('cpc_change', 0)
            },
            {
                'metric': '💸 Highest CPC',
                'campaign': worst_cpc['campaign'],
                'value': f"€{worst_cpc['cpc']:.2f}",
                'trend': worst_cpc.get('cpc_trend', ''),
                'change': worst_cpc.get('cpc_change', 0)
            }
        ],
        'campaigns': df.to_dict('records')
    }
    
    return insights_data

def create_enhanced_charts(df):
    """Create multiple charts for better visualization"""
    os.makedirs("static", exist_ok=True)
    
    # Create a figure with multiple subplots
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle('Google Ads Performance Dashboard', fontsize=16, fontweight='bold')
    
    # 1. Spend by Campaign (Bar Chart)
    campaigns = df['campaign'].str[:20]  # Truncate long names
    ax1.bar(campaigns, df['spend'], color='#667eea', alpha=0.8)
    ax1.set_title('Daily Spend by Campaign', fontweight='bold')
    ax1.set_ylabel('Spend (€)')
    ax1.tick_params(axis='x', rotation=45)
    
    # 2. Clicks vs Impressions (Scatter Plot)
    ax2.scatter(df['impressions'], df['clicks'], 
               s=df['spend']*10, alpha=0.7, color='#764ba2')
    ax2.set_title('Clicks vs Impressions', fontweight='bold')
    ax2.set_xlabel('Impressions')
    ax2.set_ylabel('Clicks')
    
    # 3. CTR by Campaign (Horizontal Bar)
    ax3.barh(campaigns, df['ctr'], color='#28a745', alpha=0.8)
    ax3.set_title('Click-Through Rate by Campaign', fontweight='bold')
    ax3.set_xlabel('CTR (%)')
    
    # 4. CPC vs Conversion Rate
    ax4.scatter(df['cpc'], df['conversion_rate'], 
               s=df['clicks']/10, alpha=0.7, color='#dc3545')
    ax4.set_title('CPC vs Conversion Rate', fontweight='bold')
    ax4.set_xlabel('CPC (€)')
    ax4.set_ylabel('Conversion Rate (%)')
    
    plt.tight_layout()
    plt.savefig("static/dashboard.png", dpi=150, bbox_inches='tight')
    plt.close()
    
    # Create simple spend chart for email
    plt.figure(figsize=(10, 6))
    plt.bar(campaigns, df['spend'], color='#667eea', alpha=0.8)
    plt.title("Daily Spend per Campaign", fontsize=14, fontweight='bold')
    plt.ylabel("Spend (€)")
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig("static/spend_chart.png", dpi=150, bbox_inches='tight')
    plt.close()

def fetch_sheet_data():
    today = datetime.date.today()
    df = load_campaign_data()
    df = add_kpis(df)

    os.makedirs(DATA_DIR, exist_ok=True)
    
    # Load previous day's data for trend analysis
    yesterday_file = get_yesterday_file(today)
    if yesterday_file:
        prev_df = pd.read_csv(yesterday_file)
        prev_df = add_kpis(prev_df)
        df = add_trend_arrows(df, prev_df)

    # Save current data
    df.to_csv(f"{DATA_DIR}/ads_{today.strftime('%Y-%m-%d')}.csv", index=False)

    # Create enhanced charts
    create_enhanced_charts(df)
    
    # Generate comprehensive insights
    insights = generate_insights(df)
    
    return df, insights