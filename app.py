from flask import Flask, render_template, send_file
from google_ads_api import fetch_sheet_data
from report_generator import generate_report
from email_sender import send_email
import os
from dotenv import load_dotenv
from google_ads_api import fetch_sheet_data

app = Flask(__name__)

load_dotenv()

if __name__ == '__main__':
    df, insights = fetch_sheet_data()
    pdf_path = generate_report(df, insights)
    send_email(
        to=os.getenv("EMAIL_TO"),
        subject="Weekly Google Ads KPI Report",
        body="Attached is your weekly Google Ads report.",
        attachment_path=pdf_path
    )
    print("Report sent!")

    @app.route("/")
    def index():
        df, insights = fetch_sheet_data()
        return f"""
        <html>
        <head><title>Google Ads Daily Report</title></head>
        <body>
            <h1>Google Ads KPI Report</h1>
            {insights}
            <h2>Spend Chart</h2>
            <img src="/static/spend_chart.png" width="600">
        </body>
        </html>
        """

if __name__ == "__main__":
    app.run(debug=True)
