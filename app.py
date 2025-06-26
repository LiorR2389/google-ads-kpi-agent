from flask import Flask, render_template, send_file
from google_ads_api import fetch_sheet_data
import os

app = Flask(__name__)

# Cache for insights
last_insights = ""
report_ready = False

@app.route("/")
def index():
    global last_insights, report_ready
    if report_ready:
        return f"""
        <html>
        <head><title>Google Ads KPI Report</title></head>
        <body>
            <h1>Google Ads KPI Report</h1>
            {last_insights}
            <h2>Spend Chart</h2>
            <img src="/static/spend_chart.png" width="600">
        </body>
        </html>
        """
    else:
        return "<h1>Report not yet generated. Visit /trigger to run it manually.</h1>"

@app.route("/trigger")
def trigger():
    key = request.args.get("key")
    if key != os.getenv("TRIGGER_KEY"):
        return "❌ Unauthorized", 403

    global last_insights, report_ready
    df, insights = fetch_sheet_data()
    last_insights = insights
    report_ready = True
    return "✅ Report updated successfully"


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
