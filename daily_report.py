from google_ads_api import fetch_daily_comparison_data, fetch_keynote_comparison_data
from send_report_email import send_daily_comparison_email, send_keynote_comparison_email
import time

def send_all_daily_reports():
    """Send both Luma and Keynote daily comparison reports"""
    print("🚀 Starting daily reports generation...")
    
    # Generate and send Luma report
    try:
        print("📊 Generating Luma daily comparison...")
        luma_data = fetch_daily_comparison_data()
        send_daily_comparison_email(luma_data)
        print("✅ Luma report sent successfully!")
    except Exception as e:
        print(f"❌ Luma report failed: {e}")
    
    # Wait a bit between emails to avoid rate limiting
    print("⏱️ Waiting 10 seconds before sending Keynote report...")
    time.sleep(10)
    
    # Generate and send Keynote report
    try:
        print("📊 Generating Keynote daily comparison...")
        keynote_data = fetch_keynote_comparison_data()
        send_keynote_comparison_email(keynote_data)
        print("✅ Keynote report sent successfully!")
    except Exception as e:
        print(f"❌ Keynote report failed: {e}")
    
    print("🎉 All daily reports processing completed!")

if __name__ == "__main__":
    send_all_daily_reports()