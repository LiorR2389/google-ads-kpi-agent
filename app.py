from flask import Flask, request, jsonify
from google_ads_api import fetch_weekly_comparison_data
from send_report_email import send_weekly_comparison_email, send_simple_test_email
import os
import traceback
from datetime import datetime, timedelta
import pandas as pd

app = Flask(__name__)
last_weekly_data = {}
report_ready = False

def format_weekly_comparison_for_web(weekly_data):
    """Convert weekly comparison data to HTML for web display"""
    campaigns = weekly_data.get('campaigns', {})
    weeks = weekly_data.get('weeks', [])
    
    if not campaigns or not weeks:
        return """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; text-align: center; padding: 40px; background: #f8d7da; border-radius: 12px;">
            <h2 style="color: #721c24;">📊 No Data Available</h2>
            <p style="color: #721c24;">No campaign data found for weekly comparison.</p>
            <a href="/trigger?key=supersecret123" style="background: #dc3545; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold;">🔄 Generate Data</a>
        </div>
        """
    
    html = f"""
    <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 1400px; margin: 0 auto; background: white; min-height: 100vh;">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center;">
            <h1 style="margin: 0; font-size: 28px;">📊 Google Ads Weekly Comparison</h1>
            <p style="margin: 10px 0 0 0; opacity: 0.9;">Last 4 Weeks Performance Data • {datetime.now().strftime('%B %d, %Y at %H:%M')}</p>
            <p style="margin: 5px 0 0 0; opacity: 0.8; font-size: 14px;">📈 Week-over-week comparison for all campaigns</p>
        </div>
        
        <div style="padding: 30px;">
            <!-- Week Headers -->
            <div style="margin-bottom: 20px; text-align: center;">
                <h2 style="color: #333; margin-bottom: 15px;">📅 Comparing Last 4 Weeks</h2>
                <div style="display: flex; justify-content: center; gap: 20px; flex-wrap: wrap;">
    """
    
    for i, week in enumerate(weeks):
        week_label = f"Week {i+1}" if i > 0 else "This Week"
        html += f"""
                    <div style="background: #e7f3ff; padding: 10px 20px; border-radius: 8px; border-left: 4px solid #0066cc;">
                        <div style="font-weight: bold; color: #0066cc;">{week_label}</div>
                        <div style="font-size: 12px; color: #666;">{week}</div>
                    </div>
        """
    
    html += """
                </div>
            </div>
    """
    
    # Generate table for each campaign
    for campaign_name, campaign_data in campaigns.items():
        html += f"""
            <div style="margin-bottom: 40px;">
                <h3 style="color: #333; margin-bottom: 15px; padding: 15px; background: #f8f9fa; border-left: 4px solid #667eea; border-radius: 0 8px 8px 0;">
                    📈 {campaign_name}
                </h3>
                
                <div style="overflow-x: auto; box-shadow: 0 4px 15px rgba(0,0,0,0.1); border-radius: 12px;">
                    <table style="width: 100%; border-collapse: collapse; background: white;">
                        <thead>
                            <tr style="background: linear-gradient(135deg, #343a40, #495057); color: white;">
                                <th style="padding: 15px; text-align: left; font-weight: 600; min-width: 100px;">Week</th>
                                <th style="padding: 15px; text-align: center; font-weight: 600; min-width: 100px;">Impressions</th>
                                <th style="padding: 15px; text-align: center; font-weight: 600; min-width: 80px;">Clicks</th>
                                <th style="padding: 15px; text-align: center; font-weight: 600; min-width: 80px;">CTR</th>
                                <th style="padding: 15px; text-align: center; font-weight: 600; min-width: 100px;">Conversions</th>
                                <th style="padding: 15px; text-align: center; font-weight: 600; min-width: 120px;">Search Impr. Share</th>
                                <th style="padding: 15px; text-align: center; font-weight: 600; min-width: 120px;">Cost/Conversion</th>
                            </tr>
                        </thead>
                        <tbody>
        """
        
        for i, week in enumerate(weeks):
            week_data = campaign_data.get(week, {})
            bg_color = "#f8f9fa" if i % 2 == 0 else "white"
            week_label = f"Week {i+1}" if i > 0 else "This Week"
            
            # Calculate trend indicators
            trend_class = ""
            if i > 0 and week in campaign_data and weeks[i-1] in campaign_data:
                prev_clicks = campaign_data[weeks[i-1]].get('clicks', 0)
                curr_clicks = week_data.get('clicks', 0)
                if curr_clicks > prev_clicks:
                    trend_class = "style='background: linear-gradient(90deg, #d4f3d0, #f8f9fa);'"
                elif curr_clicks < prev_clicks:
                    trend_class = "style='background: linear-gradient(90deg, #f8d7da, #f8f9fa);'"
            
            # Format numbers properly
            impressions = week_data.get('impressions', '—')
            impressions_formatted = f"{impressions:,}" if isinstance(impressions, (int, float)) else str(impressions)
            
            clicks = week_data.get('clicks', '—')
            clicks_formatted = f"{clicks:,}" if isinstance(clicks, (int, float)) else str(clicks)
            
            ctr = week_data.get('ctr', '—')
            ctr_formatted = f"{ctr}%" if ctr != '—' else '—'
            
            conversions = week_data.get('conversions', '—')
            
            search_share = week_data.get('search_impression_share', '—')
            search_share_formatted = f"{search_share}%" if search_share != '—' else '—'
            
            cost_conv = week_data.get('cost_per_conversion', '—')
            cost_conv_formatted = f"€{cost_conv}" if cost_conv != '—' else '—'

            html += f"""
                            <tr {trend_class if trend_class else f"style='background-color: {bg_color};'"}>
                                <td style="padding: 12px; font-weight: 500; border-bottom: 1px solid #e9ecef;">
                                    <div style="font-weight: bold; color: #333;">{week_label}</div>
                                    <div style="font-size: 11px; color: #666;">{week}</div>
                                </td>
                                <td style="padding: 12px; text-align: center; border-bottom: 1px solid #e9ecef; font-weight: 500;">
                                    {impressions_formatted}
                                </td>
                                <td style="padding: 12px; text-align: center; border-bottom: 1px solid #e9ecef; font-weight: 500; color: #667eea;">
                                    {clicks_formatted}
                                </td>
                                <td style="padding: 12px; text-align: center; border-bottom: 1px solid #e9ecef; font-weight: 500;">
                                    {ctr_formatted}
                                </td>
                                <td style="padding: 12px; text-align: center; border-bottom: 1px solid #e9ecef; font-weight: 500;">
                                    {conversions}
                                </td>
                                <td style="padding: 12px; text-align: center; border-bottom: 1px solid #e9ecef; font-weight: 500;">
                                    {search_share_formatted}
                                </td>
                                <td style="padding: 12px; text-align: center; border-bottom: 1px solid #e9ecef; font-weight: 500;">
                                    {cost_conv_formatted}
                                </td>
                            </tr>
            """
        
        html += """
                        </tbody>
                    </table>
                </div>
            </div>
        """
    
    html += f"""
            <!-- Summary Section -->
            <div style="background: #e7f3ff; border-left: 4px solid #0066cc; padding: 25px; margin: 30px 0; border-radius: 0 12px 12px 0;">
                <h3 style="color: #0066cc; margin-top: 0; margin-bottom: 15px; display: flex; align-items: center; gap: 8px;">
                    📊 <span>Weekly Comparison Summary</span>
                </h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
                    <div style="text-align: center; background: white; padding: 15px; border-radius: 8px;">
                        <div style="font-size: 14px; color: #666; margin-bottom: 5px;">Total Campaigns</div>
                        <div style="font-size: 24px; font-weight: bold; color: #0066cc;">{len(campaigns)}</div>
                    </div>
                    <div style="text-align: center; background: white; padding: 15px; border-radius: 8px;">
                        <div style="font-size: 14px; color: #666; margin-bottom: 5px;">Weeks Compared</div>
                        <div style="font-size: 24px; font-weight: bold; color: #0066cc;">{len(weeks)}</div>
                    </div>
                    <div style="text-align: center; background: white; padding: 15px; border-radius: 8px;">
                        <div style="font-size: 14px; color: #666; margin-bottom: 5px;">Data Period</div>
                        <div style="font-size: 16px; font-weight: bold; color: #0066cc;">{weeks[-1] if weeks else 'N/A'}</div>
                        <div style="font-size: 12px; color: #666;">to {weeks[0] if weeks else 'N/A'}</div>
                    </div>
                </div>
                <div style="border-top: 1px solid #cce7ff; padding-top: 15px; margin-top: 15px;">
                    <p style="margin: 0; color: #0066cc; font-weight: 500;">
                        💡 Green highlighting indicates week-over-week improvement in clicks. 
                        Red highlighting indicates decline. Use this data to identify trends and optimize campaigns.
                    </p>
                </div>
            </div>
            
            <!-- Action Buttons -->
            <div style="text-align: center; margin-top: 30px;">
                <a href="/trigger?key={os.getenv('TRIGGER_KEY', 'supersecret123')}" 
                   style="background: linear-gradient(135deg, #28a745, #20c997); color: white; padding: 12px 25px; text-decoration: none; border-radius: 25px; font-weight: bold; margin: 0 10px; display: inline-block; box-shadow: 0 4px 15px rgba(40, 167, 69, 0.3); transition: transform 0.2s;" 
                   onmouseover="this.style.transform='translateY(-2px)'" 
                   onmouseout="this.style.transform='translateY(0)'">
                    🔄 Refresh Weekly Data
                </a>
                <a href="/test-email" 
                   style="background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 12px 25px; text-decoration: none; border-radius: 25px; font-weight: bold; margin: 0 10px; display: inline-block; box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3); transition: transform 0.2s;" 
                   onmouseover="this.style.transform='translateY(-2px)'" 
                   onmouseout="this.style.transform='translateY(0)'">
                    📧 Email Report
                </a>
            </div>
        </div>
        
        <!-- Footer -->
        <div style="background: #f8f9fa; padding: 20px; text-align: center; font-size: 12px; color: #6c757d; border-top: 1px solid #e9ecef;">
            <p style="margin: 0;">🤖 Automated Google Ads Weekly Comparison • Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p style="margin: 5px 0 0 0;">Weekly data comparison showing last 4 weeks • Green = improvement, Red = decline</p>
        </div>
    </div>
    """
    
    return html

@app.route("/")
def index():
    global last_weekly_data, report_ready
    if report_ready and last_weekly_data:
        return format_weekly_comparison_for_web(last_weekly_data)
    else:
        return """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; text-align: center; padding: 40px; background: linear-gradient(135deg, #f8f9fa, #e9ecef); border-radius: 12px;">
            <h1 style="color: #333; margin-bottom: 20px;">📊 Google Ads Weekly Comparison</h1>
            <div style="font-size: 64px; margin-bottom: 20px;">📅</div>
            <p style="color: #666; font-size: 18px; margin-bottom: 30px;">Welcome! Your weekly comparison dashboard is ready to show the last 4 weeks of campaign data.</p>
            <div style="margin: 30px 0; padding: 20px; background: white; border-radius: 8px; border-left: 4px solid #ffc107;">
                <p style="margin: 0; color: #856404;"><strong>📈 Features:</strong></p>
                <p style="margin: 10px 0 0 0; color: #856404;">
                    • Side-by-side weekly comparison<br>
                    • All key metrics in one view<br>
                    • Week-over-week trend indicators<br>
                    • Performance highlighting
                </p>
            </div>
            <a href="/trigger?key=supersecret123" style="background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 15px 30px; text-decoration: none; border-radius: 25px; font-weight: bold; display: inline-block; box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);">
                📊 Generate Weekly Comparison
            </a>
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

    global last_weekly_data, report_ready
    
    try:
        print("🚀 Starting Google Ads weekly comparison generation...")
        
        # Generate weekly comparison data
        weekly_data = fetch_weekly_comparison_data()
        last_weekly_data = weekly_data
        report_ready = True
        
        print("✅ Weekly comparison data generated successfully")
        print(f"📊 Found {len(weekly_data.get('campaigns', {}))} campaigns across {len(weekly_data.get('weeks', []))} weeks")

        # Try to send email
        email_status = "⚠️ Report generated but email not attempted"
        try:
            print("📧 Attempting to send weekly comparison email...")
            send_weekly_comparison_email(weekly_data)
            email_status = "📧 Weekly comparison email sent successfully"
            print("✅ Email sent successfully")
        except Exception as email_error:
            print(f"❌ Email failed: {email_error}")
            email_status = f"⚠️ Report generated but email failed: {str(email_error)[:50]}..."

        return f"""
        <div style="font-family: Arial, sans-serif; max-width: 700px; margin: 50px auto; text-align: center; padding: 40px; background: #d4edda; border-radius: 12px; border-left: 4px solid #28a745;">
            <h2 style="color: #155724;">✅ Weekly Comparison Generated Successfully!</h2>
            <div style="font-size: 48px; margin: 20px 0;">📅</div>
            <p style="color: #155724; font-size: 16px; margin-bottom: 20px;">{email_status}</p>
            
            <div style="background: rgba(255,255,255,0.8); padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="color: #155724; margin-top: 0;">📊 Weekly Summary</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 15px; text-align: center;">
                    <div>
                        <div style="font-size: 20px; font-weight: bold; color: #155724;">{len(weekly_data.get('campaigns', {}))}</div>
                        <div style="font-size: 12px; color: #155724;">Campaigns</div>
                    </div>
                    <div>
                        <div style="font-size: 20px; font-weight: bold; color: #155724;">{len(weekly_data.get('weeks', []))}</div>
                        <div style="font-size: 12px; color: #155724;">Weeks</div>
                    </div>
                    <div>
                        <div style="font-size: 16px; font-weight: bold; color: #155724;">{weekly_data.get('weeks', ['N/A'])[-1] if weekly_data.get('weeks') else 'N/A'}</div>
                        <div style="font-size: 12px; color: #155724;">Start Date</div>
                    </div>
                    <div>
                        <div style="font-size: 16px; font-weight: bold; color: #155724;">{weekly_data.get('weeks', ['N/A'])[0] if weekly_data.get('weeks') else 'N/A'}</div>
                        <div style="font-size: 12px; color: #155724;">End Date</div>
                    </div>
                </div>
            </div>
            
            <div style="margin-top: 25px;">
                <a href="/" style="background: #28a745; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 0 10px;">📊 View Weekly Comparison</a>
                <a href="/trigger?key={key}" style="background: #17a2b8; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 0 10px;">🔄 Refresh Again</a>
            </div>
        </div>
        """
        
    except Exception as e:
        error_details = str(e)
        traceback_str = traceback.format_exc()
        print(f"❌ Weekly comparison generation failed: {error_details}")
        print(f"🔍 Full traceback: {traceback_str}")
        
        return f"""
        <div style="font-family: Arial, sans-serif; max-width: 700px; margin: 50px auto; text-align: center; padding: 40px; background: #f8d7da; border-radius: 12px; border-left: 4px solid #dc3545;">
            <h2 style="color: #721c24;">❌ Weekly Comparison Generation Failed</h2>
            <div style="font-size: 48px; margin: 20px 0;">⚠️</div>
            <p style="color: #721c24; font-size: 16px; margin-bottom: 20px;"><strong>Error:</strong> {error_details}</p>
            
            <div style="background: rgba(255,255,255,0.7); padding: 20px; border-radius: 6px; margin: 20px 0; text-align: left;">
                <h4 style="color: #721c24; margin-top: 0;">🔍 Troubleshooting Steps:</h4>
                <ol style="color: #721c24; padding-left: 20px;">
                    <li>Check that your Google Sheets has data for the last 4 weeks</li>
                    <li>Verify your GOOGLE_CREDENTIALS_B64 environment variable is set</li>
                    <li>Make sure your sheet has the required columns: Date, Campaign Name, Impressions, Clicks, CTR, Conversions, Search Impression Share, Cost Per Conversion</li>
                    <li>Ensure dates are in YYYY-MM-DD format</li>
                    <li>Check that there's data for multiple weeks</li>
                </ol>
            </div>
            
            <div style="margin-top: 25px;">
                <a href="/test-email" style="background: #dc3545; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 0 10px;">📧 Test Email</a>
                <a href="/" style="background: #6c757d; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 0 10px;">🏠 Home</a>
            </div>
        </div>
        """, 500

@app.route("/test-email")
def test_email():
    """Test email configuration"""
    try:
        success = send_simple_test_email()
        if success:
            return """
            <div style="font-family: Arial, sans-serif; max-width: 500px; margin: 50px auto; text-align: center; padding: 40px; background: #d4edda; border-radius: 12px; border-left: 4px solid #28a745;">
                <h2 style="color: #155724;">✅ Email Test Successful!</h2>
                <p style="color: #155724;">Check your inbox - you should receive a test email shortly.</p>
                <p style="color: #155724; font-size: 14px; margin-top: 15px;">Weekly comparison emails will include all campaign data in a table format.</p>
                <a href="/" style="background: #28a745; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold;">Back to Dashboard</a>
            </div>
            """
        else:
            return """
            <div style="font-family: Arial, sans-serif; max-width: 500px; margin: 50px auto; text-align: center; padding: 40px; background: #f8d7da; border-radius: 12px; border-left: 4px solid #dc3545;">
                <h2 style="color: #721c24;">❌ Email Test Failed</h2>
                <p style="color: #721c24;">Please check your email configuration in the environment variables.</p>
                <a href="/" style="background: #6c757d; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold;">Back to Dashboard</a>
            </div>
            """
    except Exception as e:
        return f"""
        <div style="font-family: Arial, sans-serif; max-width: 500px; margin: 50px auto; text-align: center; padding: 40px; background: #f8d7da; border-radius: 12px; border-left: 4px solid #dc3545;">
            <h2 style="color: #721c24;">❌ Email Test Error</h2>
            <p style="color: #721c24;">Error: {str(e)}</p>
            <a href="/" style="background: #6c757d; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold;">Back to Dashboard</a>
        </div>
        """

@app.route("/api/weekly-data")
def api_weekly_data():
    """API endpoint to get raw weekly comparison data as JSON"""
    global last_weekly_data, report_ready
    if report_ready and last_weekly_data:
        return jsonify(last_weekly_data)
    else:
        return jsonify({"error": "No weekly data available"}), 404

@app.route("/health")
def health():
    """Health check endpoint"""
    global last_weekly_data, report_ready
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "report_ready": report_ready,
        "data_available": bool(last_weekly_data),
        "campaigns_count": len(last_weekly_data.get('campaigns', {})) if last_weekly_data else 0,
        "weeks_count": len(last_weekly_data.get('weeks', [])) if last_weekly_data else 0,
        "version": "weekly_comparison"
    })

if __name__ == '__main__':
    print("🚀 Starting Google Ads Weekly Comparison Dashboard...")
    print(f"📊 Dashboard will be available at: http://localhost:{os.environ.get('PORT', 5000)}")
    print(f"🔑 Trigger key: {os.getenv('TRIGGER_KEY', 'supersecret123')}")
    print("📅 New features: 4-week comparison, side-by-side campaign data, trend indicators")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)