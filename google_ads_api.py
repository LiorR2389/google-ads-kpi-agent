import os
import pandas as pd
import matplotlib.pyplot as plt
import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

DATA_DIR = "data"
SHEET_ID = "1rBjY6_AeDIG-1UEp3JvA44CKLAqn3JAGFttixkcRaKg"
SHEET_NAME = "Daily Ad Group Performance Report"  # updated to match the correct worksheet name

def load_campaign_data():
    # Authenticate using the service account
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("bots-464109-66b37fe69997.json", scope)
    client = gspread.authorize(creds)

    # Open the sheet and load data
    sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)
    data = sheet.get_all_records(head=2)  # skip first row, real headers start at row 2
    df = pd.DataFrame(data)

    # Normalize and rename columns
    df.columns = [col.strip().lower() for col in df.columns]
    rename_map = {
        'ad group name': 'Campaign',
        'clicks': 'clicks',
        'average cost': 'spend'
    }
    df = df.rename(columns=rename_map)

    # Keep only needed columns (skipping conversions)
    df = df[['Campaign', 'clicks', 'spend']]

    return df

def add_kpis(df):
    # Clean and convert columns
    df['spend'] = df['spend'].replace('[€$,]', '', regex=True)
    df['spend'] = pd.to_numeric(df['spend'], errors='coerce')
    df['clicks'] = pd.to_numeric(df['clicks'], errors='coerce')

    # Fill NaNs with 0 to avoid crash
    df[['spend', 'clicks']] = df[['spend', 'clicks']].fillna(0)

    # Add calculated KPIs
    df['ctr'] = (df['clicks'] / 100000) * 100
    df['cpc'] = df['spend'] / df['clicks']
    df['conversion_rate'] = 0
    df['cost_per_conversion'] = 0
    return df


def get_yesterday_file(today):
    yesterday = today - datetime.timedelta(days=1)
    filename = f"{DATA_DIR}/ads_{yesterday.strftime('%Y-%m-%d')}.csv"
    return filename if os.path.exists(filename) else None

def add_trend_arrows(df, prev_df):
    merged = df.merge(prev_df, on="Campaign", suffixes=("", "_prev"))
    for col in ['clicks', 'cpc', 'conversion_rate', 'cost_per_conversion']:
        trend_col = f"{col}_trend"
        df[trend_col] = ""
        for idx, row in merged.iterrows():
            today_val = row[col]
            yest_val = row[f"{col}_prev"]
            if pd.isna(yest_val):
                arrow = ""
            elif today_val > yest_val:
                arrow = "⬆️"
            elif today_val < yest_val:
                arrow = "⬇️"
            else:
                arrow = "➡️"
            df.loc[df['Campaign'] == row['Campaign'], trend_col] = arrow
    return df

def generate_insights(df):
    most_clicks = df.loc[df['clicks'].idxmax()]
    best_cpc = df.loc[df['cpc'].idxmin()]
    worst_cpc = df.loc[df['cpc'].idxmax()]

    summary_table = f"""
    <table class="highlight-table">
        <thead>
            <tr><th>Metric</th><th>Campaign</th><th>Value</th></tr>
        </thead>
        <tbody>
            <tr><td>🥇 Most Clicks</td><td>{most_clicks['Campaign']}</td><td>{most_clicks['clicks']} {most_clicks.get('clicks_trend', '')}</td></tr>
            <tr><td>💰 Lowest CPC</td><td>{best_cpc['Campaign']}</td><td>€{best_cpc['cpc']:.2f} {best_cpc.get('cpc_trend', '')}</td></tr>
            <tr><td>💸 Highest CPC</td><td>{worst_cpc['Campaign']}</td><td>€{worst_cpc['cpc']:.2f} {worst_cpc.get('cpc_trend', '')}</td></tr>
        </tbody>
    </table>
    """

    recommendations = """
    <ul class="recommendations">
        <li>🚀 Shift budget to high-performing campaigns like Demand Gen</li>
        <li>🔍 Improve ad copy and targeting on high-CPC campaigns</li>
        <li>🎯 Test new landing pages to improve CVR</li>
        <li>📉 Reduce cost-per-conversion with better bidding or creatives</li>
    </ul>
    """

    return f"<strong>📊 Daily Highlights</strong><br>{summary_table}<br><strong>✅ Recommendations</strong>{recommendations}"

def fetch_sheet_data():
    today = datetime.date.today()
    df = load_campaign_data()
    df = add_kpis(df)

    os.makedirs(DATA_DIR, exist_ok=True)
    yesterday_file = get_yesterday_file(today)
    if yesterday_file:
        prev_df = pd.read_csv(yesterday_file)
        prev_df = add_kpis(prev_df)
        df = add_trend_arrows(df, prev_df)

    df.to_csv(f"{DATA_DIR}/ads_{today.strftime('%Y-%m-%d')}.csv", index=False)

    os.makedirs("static", exist_ok=True)
    plt.figure(figsize=(8, 5))
    plt.bar(df['Campaign'], df['spend'])
    plt.title("Daily Spend per Campaign")
    plt.ylabel("Spend (€)")
    plt.xticks(rotation=15, ha='right')
    plt.tight_layout()
    plt.savefig("static/spend_chart.png")
    plt.close()

    insights = generate_insights(df)
    return df, insights
