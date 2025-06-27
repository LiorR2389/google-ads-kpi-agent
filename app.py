from flask import Flask, request
from google_ads_api import fetch_sheet_data
from send_report_email import send_report_email
import os
import json

app = Flask(__name__)
last_insights = {}
report_ready = False

def format_insights_for_web(insights_data):
    """Convert insights data to HTML for web display"""
    summary = insights_data['summary']
    highlights = insights_data['highlights']
    
    html = f"""
    <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 1000px; margin: 0 auto;">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 12px 12px 0 0;">
            <h1 style="margin: 0; font-size: 28px;">📊 Google Ads Dashboard</h1>
            <p style="margin: 10px 0 0 0; opacity: 0.9;">Real-time Performance Overview</p>
        </div>
        
        <div style="padding: 30px; background: white; border-radius: 0 0 12px 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            <!-- Summary Cards -->
            <div style="display: flex; gap: 15px; margin-bottom: 30px; flex-wrap: wrap;">
                <div style="flex: 1; min-width: 200px; background: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 4px solid #667eea; text-align: center;">
                    <h3 style="margin: 0 0 10px 0; color: #667eea; font-size: 14px; text-transform: uppercase;">Total Spend</h3>
                    <div style="font-size: 24px; font-weight: bold; color: #333;">€{summary['total_spend']:.2f}</div>
                </div>
                <div style="flex: 1; min-width: 200px; background: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 4px solid #28a745; text-align: center;">
                    <h3 style="margin: 0 0 10px 0; color: #28a745; font-size: 14px; text-transform: uppercase;">Total Clicks</h3>
                    <div style="font-size: 24px; font-weight: bold; color: #333;">{summary['total_clicks']:,}</div>
                </div>
                <div style="flex: 1; min-width: 200px; background: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 4px solid #ffc107; text-align: center;">
                    <h3 style="margin: 0 0 10px 0; color: #e67e22; font-size: 14px; text-transform: uppercase;">Avg CPC</h3>
                    <div style="font-size: 24px; font-weight: bold; color: #333;">€{summary['avg_cpc']:.2f}</div>
                </div>
                <div style="flex: 1; min-width: 200px; background: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 4px solid #17a2b8; text-align: center;">
                    <h3 style="margin: 0 0 10px 0; color: #17a2b8; font-size: 14px; text-transform: uppercase;">Impressions</h3>
                    <div style="font-size: 24px; font-weight: bold; color: #333;">{summary['total_impressions']:,}</div>
                </div>
            </div>
            
            <!-- Highlights Table -->
            <h2 style="color: #333; font-size: 22px; margin-bottom: 15px; padding-bottom: 10px; border-bottom: 2px solid #e9ecef;">🎯 Performance Highlights</h2>
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                <thead>
                    <tr style="background: #667eea; color: white;">
                        <th style="padding: 15px; text-align: left; font-weight: 600;">Metric</th>
                        <th style="padding: 15px; text-align: left; font-weight: 600;">Campaign</th>
                        <th style="padding: 15px; text-align: left; font-weight: 600;">Value</th>
                    </tr>
                </thead>
                <tbody>
    """
    
    for i, highlight in enumerate(highlights):
        bg_color = "#f8f9fa" if i % 2 == 0 else "white"
        html += f"""
                    <tr style="background-color: {bg_color};">
                        <td style="padding: 12px 15px; border-bottom: 1px solid #e9ecef;">{highlight['metric']}</td>
                        <td style="padding: 12px 15px; border-bottom: 1px solid #e9ecef;">{highlight['campaign']}</td>
                        <td style="padding: 12px 15px; border-bottom: 1px solid #e9ecef;">{highlight['value']}</td>
                    </tr>
        """
    
    html += """
                </tbody>
            </table>
            
            <h2 style="color: #333; font-size: 22px; margin-bottom: 15px; padding-bottom: 10px; border-bottom: 2px solid #e9ecef;">💰 Spend Chart</h2>
            <div style="text-align: center; margin: 20px 0; padding: 20px; background: #f8f9fa; border-radius: 8px;">
                <img src="/static/spend_chart.png" style="max-width: 100%; height: auto; border-radius: 4px;" alt="Spend Chart">
            </div>
            
            <div style="background: #e7f3ff; border-left: 4px solid #0066cc; padding: 20px; border-radius: 0 8px 8px 0; margin-bottom: 20px;">
                <h3 style="color: #0066cc; margin-top: 0; margin-bottom: 15px;">✅ Quick Actions</h3>
                <ul style="margin: 0; padding-left: 20px;">
                    <li style="margin-bottom: 8px; color: #333;"><strong>Scale top performers:</strong> Increase budget for campaigns with best ROI</li>
                    <li style="margin-bottom: 8px; color: #333;"><strong>Optimize keywords:</strong> Review high-CPC campaigns for better targeting</li>
                    <li style="margin-bottom: 8px; color: #333;"><strong>Test new creatives:</strong> A/B test ad variations for underperforming campaigns</li>
                </ul>
            </div>
        </div>
    </div>
    """
    
    return html

@app.route("/")
def index():
    global last_insights, report_ready
    if report_ready and last_insights:
        return format_insights_for_web(last_insights)
    else:
        return """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; text-align: center; padding: 40px; background: #f8f9fa; border-radius: 12px;">
            <h1 style="color: #333;">📊 Google Ads KPI Dashboard</h1>
            <p style="color: #666; font-size: 18px;">Report not yet generated.</p>
            <p style="color: #666;">Visit <a href="/trigger?key=supersecret123" style="color: #667eea; text-decoration: none; font-weight: bold;">/trigger</a> to run it manually.</p>
            <div style="margin-top: 30px; padding: 20px; background: white; border-radius: 8px; border-left: 4px solid #ffc107;">
                <p style="margin: 0; color: #856404;"><strong>💡 Tip:</strong> The report will automatically update with your latest Google Ads data when triggered.</p>
            </div>
        </div>
        """

@app.route("/trigger")
def trigger():
    key = request.args.get("key")
    if key != os.getenv("TRIGGER_KEY"):
        return """
        <div style="font-family: Arial, sans-serif; max-width: 400px; margin: 50px auto; text-align: center; padding: 40px; background: #f8d7da; border-radius: 12px; border-left: 4px solid #dc3545;">
            <h2 style="color: #721c24;">❌ Unauthorized</h2>
            <p style="color: #721c24;">Invalid trigger key provided.</p>
        </div>
        """, 403

    global last_insights, report_ready
    try:
        print("🔄 Starting report generation...")
        df, insights_data = fetch_sheet_data()
        last_insights = insights_data
        report_ready = True
        print("✅ Report data generated successfully")

        # Try to send email, but don't fail if it doesn't work
        try:
            print("📧 Attempting to send email...")
            send_report_email(insights_data, "static/spend_chart.png")
            email_status = "📧 Email sent successfully"
            print("✅ Email sent successfully")
        except Exception as email_error:
            print(f"❌ Email failed: {email_error}")
            email_status = "⚠️ Report generated but email failed"

        return f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; text-align: center; padding: 40px; background: #d4edda; border-radius: 12px; border-left: 4px solid #28a745;">
            <h2 style="color: #155724;">✅ Report Updated Successfully</h2>
            <p style="color: #155724; font-size: 18px;">{email_status}</p>
            <div style="margin-top: 20px;">
                <a href="/" style="background: #28a745; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold;">View Dashboard</a>
            </div>
            <div style="margin-top: 20px; padding: 15px; background: rgba(255,255,255,0.7); border-radius: 6px;">
                <p style="margin: 0; color: #155724; font-size: 14px;">
                    <strong>Summary:</strong> 
                    €{last_insights['summary']['total_spend']:.2f} spent | 
                    {last_insights['summary']['total_clicks']:,} clicks | 
                    {last_insights['summary']['total_impressions']:,} impressions
                </p>
            </div>
        </div>
        """
        
    except Exception as e:
        print(f"❌ Report generation failed: {e}")
        return f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; text-align: center; padding: 40px; background: #f8d7da; border-radius: 12px; border-left: 4px solid #dc3545;">
            <h2 style="color: #721c24;">❌ Report Generation Failed</h2>
            <p style="color: #721c24; font-size: 16px;">Error: {str(e)}</p>
            <div style="margin-top: 20px; padding: 15px; background: rgba(255,255,255,0.7); border-radius: 6px;">
                <p style="margin: 0; color: #721c24; font-size: 14px;">Please check your configuration and try again.</p>
            </div>
        </div>
        """, 500

@app.route("/api/data")
def api_data():
    """API endpoint to get raw data as JSON"""
    global last_insights, report_ready
    if report_ready and last_insights:
        return last_insights
    else:
        return {"error": "No data available"}, 404

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)