from google_ads_api import fetch_daily_comparison_data
from send_report_email import send_daily_comparison_email

# Get the data and send the email
data = fetch_daily_comparison_data()
send_daily_comparison_email(data)