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
        
        if len(all_data) < 3:
            print("⚠️ Not enough data rows found")
            return create_empty_dataframe()
        
        # Find the header row - look for "Date" in the first column
        header_row_idx = None
        for i, row in enumerate(all_data):
            if row and len(row) > 0 and 'Date' in str(row[0]):
                header_row_idx = i
                break
        
        if header_row_idx is None:
            print("⚠️ Could not find header row with 'Date'")
            return create_empty_dataframe()
        
        headers = all_data[header_row_idx]
        data_rows = all_data[header_row_idx + 1:]
        
        print(f"🔍 Found headers at row {header_row_idx}: {headers}")
        print(f"📝 Data rows available: {len(data_rows)}")
        
        # Filter out empty rows
        data_rows = [row for row in data_rows if any(cell.strip() for cell in row if cell)]
        
        if not data_rows:
            print("⚠️ No data rows found after filtering")
            return create_empty_dataframe()
        
        df = pd.DataFrame(data_rows, columns=headers)
        df.columns = [str(col).strip() for col in df.columns]
        
        print(f"✅ Created DataFrame with {len(df)} rows and columns: {list(df.columns)}")
        return df
        
    except Exception as e:
        print(f"❌ Error in load_campaign_data: {e}")
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
    
    column_mapping = {}
    for col in df.columns:
        col_lower = str(col).lower().strip()
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
    
    df_mapped = df.rename(columns=column_mapping)
    print(f"🗺️ Column mapping applied: {column_mapping}")
    return df_mapped

def get_date_data(df, target_date):
    """Get data for a specific date"""
    if df.empty or 'date' not in df.columns:
        return create_processed_empty_dataframe()
    
    df_copy = df.copy()
    df_copy = df_copy[df_copy['date'].notna() & (df_copy['date'] != '')]
    
    if len(df_copy) == 0:
        return create_processed_empty_dataframe()
    
    df_copy['date'] = pd.to_datetime(df_copy['date'], errors='coerce')
    df_copy = df_copy.dropna(subset=['date'])
    
    if len(df_copy) == 0:
        return create_processed_empty_dataframe()
    
    # Filter for target date
    df_filtered = df_copy[df_copy['date'].dt.date == target_date]
    
    # Filter for valid campaigns
    if 'campaign' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['campaign'].notna() & (df_filtered['campaign'] != '')]
    
    return df_filtered

def add_kpis(df):
    if df.empty:
        return create_processed_empty_dataframe()
    
    # Clean numeric columns
    numeric_columns = ['impressions', 'clicks', 'conversions']
    for col in numeric_columns:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(r'[€$,%]', '', regex=True)
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
    if 'impression_share' in df.columns:
        df['impression_share'] = df['impression_share'].astype(str).str.replace('%', '')
        df['impression_share'] = pd.to_numeric(df['impression_share'], errors='coerce').fillna(75.0)
    else:
        df['impression_share'] = 75.0
    
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
        'impression_share': [],
        'quality_score': []
    })

def calculate_trends(today_df, yesterday_df):
    """Calculate trends between today and yesterday"""
    if today_df.empty:
        return today_df
    
    if yesterday_df.empty:
        # No yesterday data, add empty trend columns
        for col in ['clicks', 'impressions', 'spend', 'ctr', 'conversions']:
            today_df[f'{col}_trend'] = '🆕'
            today_df[f'{col}_change'] = 0
        return today_df
    
    # Merge today and yesterday data
    merged = today_df.merge(yesterday_df, on='campaign', suffixes=('', '_prev'), how='left')
    
    # Calculate trends for key metrics
    trend_columns = ['clicks', 'impressions', 'spend', 'ctr', 'conversions']
    
    for col in trend_columns:
        trend_col = f'{col}_trend'
        change_col = f'{col}_change'
        
        today_df[trend_col] = ''
        today_df[change_col] = 0
        
        for idx, row in merged.iterrows():
            today_val = row[col] if pd.notna(row[col]) else 0
            yesterday_val = row[f'{col}_prev'] if pd.notna(row[f'{col}_prev']) else 0
            
            if yesterday_val == 0:
                if today_val > 0:
                    arrow = '🆕'
                    change = 0
                else:
                    arrow = ''
                    change = 0
            else:
                change_pct = ((today_val - yesterday_val) / yesterday_val) * 100
                
                if change_pct > 5:
                    arrow = '⬆️'
                elif change_pct < -5:
                    arrow = '⬇️'
                else:
                    arrow = '➡️'
                
                change = round(change_pct, 1)
            
            campaign_mask = today_df['campaign'] == row['campaign']
            today_df.loc[campaign_mask, trend_col] = arrow
            today_df.loc[campaign_mask, change_col] = change
    
    return today_df

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

def calculate_summary_trends(today_summary, yesterday_summary):
    """Calculate trends for summary statistics"""
    trends = {}
    
    metrics = ['total_spend', 'total_clicks', 'total_impressions', 'avg_ctr', 'avg_cpc']
    
    for metric in metrics:
        today_val = today_summary[metric]
        yesterday_val = yesterday_summary[metric]
        
        if yesterday_val == 0:
            if today_val > 0:
                trends[f'{metric}_trend'] = '🆕'
                trends[f'{metric}_change'] = 0
            else:
                trends[f'{metric}_trend'] = ''
                trends[f'{metric}_change'] = 0
        else:
            change_pct = ((today_val - yesterday_val) / yesterday_val) * 100
            
            if change_pct > 5:
                trends[f'{metric}_trend'] = '⬆️'
            elif change_pct < -5:
                trends[f'{metric}_trend'] = '⬇️'
            else:
                trends[f'{metric}_trend'] = '➡️'
            
            trends[f'{metric}_change'] = round(change_pct, 1)
    
    return trends

def generate_insights(df, yesterday_df=None):
    summary = generate_summary_stats(df)
    
    # Calculate summary trends if yesterday data exists
    summary_trends = {}
    if yesterday_df is not None and not yesterday_df.empty:
        yesterday_summary = generate_summary_stats(yesterday_df)
        summary_trends = calculate_summary_trends(summary, yesterday_summary)
    
    if df.empty:
        return {
            'summary': summary,
            'summary_trends': summary_trends,
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
            'trend': most_clicks.get('clicks_trend', ''),
            'change': most_clicks.get('clicks_change', 0)
        })
    
    if df['impressions'].sum() > 0:
        most_impressions_idx = df['impressions'].idxmax()
        most_impressions = df.loc[most_impressions_idx]
        highlights.append({
            'metric': '👁️ Most Impressions',
            'campaign': str(most_impressions['campaign'])[:30],
            'value': f"{int(most_impressions['impressions']):,}",
            'trend': most_impressions.get('impressions_trend', ''),
            'change': most_impressions.get('impressions_change', 0)
        })
    
    if df['ctr'].sum() > 0:
        best_ctr_idx = df['ctr'].idxmax()
        best_ctr = df.loc[best_ctr_idx]
        highlights.append({
            'metric': '🎯 Best CTR',
            'campaign': str(best_ctr['campaign'])[:30],
            'value': f"{best_ctr['ctr']:.2f}%",
            'trend': best_ctr.get('ctr_trend', ''),
            'change': best_ctr.get('ctr_change', 0)
        })
    
    if df['conversions'].sum() > 0:
        best_conv_idx = df['conversion_rate'].idxmax()
        best_conv = df.loc[best_conv_idx]
        highlights.append({
            'metric': '🔄 Best Conv. Rate',
            'campaign': str(best_conv['campaign'])[:30],
            'value': f"{best_conv['conversion_rate']:.2f}%",
            'trend': best_conv.get('conversion_rate_trend', ''),
            'change': best_conv.get('conversion_rate_change', 0)
        })
    
    if len(highlights) < 5:
        best_imp_share_idx = df['impression_share'].idxmax()
        best_imp_share = df.loc[best_imp_share_idx]
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
    
    return {
        'summary': summary,
        'summary_trends': summary_trends,
        'highlights': highlights,
        'campaigns': df.to_dict('records')
    }

def create_enhanced_charts(df):
    os.makedirs("static", exist_ok=True)
    
    if df.empty:
        plt.figure(figsize=(10, 6))
        plt.text(0.5, 0.5, 'No data available', ha='center', va='center', fontsize=16)
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
        yesterday = today - datetime.timedelta(days=1)
        
        print(f"📅 Fetching data for today: {today}")
        print(f"📅 Looking for yesterday data: {yesterday}")
        
        # Load all data from sheet
        df_all = load_campaign_data()
        df_all_mapped = clean_and_map_columns(df_all)
        
        # Get today's data
        today_df = get_date_data(df_all_mapped, today)
        today_df = add_kpis(today_df)
        
        # Get yesterday's data
        yesterday_df = get_date_data(df_all_mapped, yesterday)
        yesterday_df = add_kpis(yesterday_df)
        
        print(f"📊 Today: {len(today_df)} campaigns")
        print(f"📊 Yesterday: {len(yesterday_df)} campaigns")
        
        # Calculate trends
        if not yesterday_df.empty:
            today_df = calculate_trends(today_df, yesterday_df)
            print("📈 Trends calculated successfully")
        else:
            print("⚠️ No yesterday data found - skipping trends")
        
        # Save data
        os.makedirs(DATA_DIR, exist_ok=True)
        today_df.to_csv(f"{DATA_DIR}/ads_{today.strftime('%Y-%m-%d')}.csv", index=False)
        
        # Create charts
        create_enhanced_charts(today_df)
        
        # Generate insights with trends
        insights = generate_insights(today_df, yesterday_df)
        
        print(f"✅ Successfully processed with trends")
        return today_df, insights
        
    except Exception as e:
        print(f"❌ Error in fetch_sheet_data: {e}")
        import traceback
        traceback.print_exc()
        raise