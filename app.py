from flask import Flask, request, jsonify
from google_ads_api import fetch_daily_comparison_data
from send_report_email import send_daily_comparison_email, send_simple_test_email
import os
import traceback
from datetime import datetime, timedelta
import pandas as pd

app = Flask(__name__)
last_daily_data = {}
report_ready = False

def format_daily_comparison_for_web(daily_data):
    """Convert daily comparison data to HTML for web display"""
    campaigns = daily_data.get('campaigns', {})
    weeks = daily_data.get('weeks', [])
    
    if not campaigns or not weeks:
        return """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; text-align: center; padding: 40px; background: #f8d7da; border-radius: 12px;">
            <h2 style="color: #721c24;">📊 No Data Available</h2>
            <p style="color: #721c24;">No campaign data found for daily comparison.</p>
            <a href="/trigger?key=supersecret123" style="background: #dc3545; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold;">🔄 Generate Data</a>
        </div>
        """
    
    html = f"""
    <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 1400px; margin: 0 auto; background: white; min-height: 100vh;">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center;">
            <h1 style="margin: 0; font-size: 28px;">📊 Google Ads Daily Comparison</h1>
            <p style="margin: 10px 0 0 0; opacity: 0.9;">Last 4 Weeks Performance Data • {datetime.now().strftime('%B %d, %Y at %H:%M')}</p>
            <p style="margin: 5px 0 0 0; opacity: 0.8; font-size: 14px;">📈 Week-over-week comparison for all campaigns</p>
        </div>
        
        <div style="padding: 30px;">
            <!-- Week Headers -->
            <div style="margin-bottom: 20px; text-align: center;">
                <h2 style="color: #333; margin-bottom: 15px;">📅 Comparing Last 4 Weeks</h2>
                <div style="display: flex; justify-content: center; gap: 20px; flex-wrap: wrap;">
    """
    
    # Reverse the weeks list so the most recent week is actually "This Week"
    weeks_corrected = list(reversed(weeks))
    
    for i, week in enumerate(weeks_corrected):
        week_label = f"This Week" if i == 0 else f"Week {i+1}"
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
    
    # Generate one big transposed table (weeks as rows, campaigns as columns)
    html += f"""
        <div style="margin-bottom: 40px;">
            <h3 style="color: #333; margin-bottom: 15px; padding: 15px; background: #f8f9fa; border-left: 4px solid #667eea; border-radius: 0 8px 8px 0;">
                📈 All Campaigns Daily Comparison
            </h3>
            
            <div style="overflow-x: auto; box-shadow: 0 4px 15px rgba(0,0,0,0.1); border-radius: 12px;">
                <table style="width: 100%; border-collapse: collapse; background: white; min-width: 1200px;">
                    <thead>
                        <tr style="background: linear-gradient(135deg, #343a40, #495057); color: white;">
                            <th rowspan="2" style="padding: 15px; text-align: left; font-weight: 600; min-width: 120px; border-right: 2px solid #495057;">Week</th>
    """
    
    # Campaign headers
    for campaign_name in campaigns.keys():
        html += f"<th colspan='7' style='padding: 15px; text-align: center; font-weight: 600; border-right: 1px solid #495057;'>{campaign_name[:30]}{'...' if len(campaign_name) > 30 else ''}</th>"
    
    html += """
                        </tr>
                        <tr style="background: linear-gradient(135deg, #495057, #6c757d); color: white;">
    """
    
    # Metric subheaders for each campaign
    for _ in campaigns.keys():
        html += """
            <th style='padding: 8px; text-align: center; font-size: 11px; border-right: 1px solid #6c757d;'>Impr.</th>
            <th style='padding: 8px; text-align: center; font-size: 11px; border-right: 1px solid #6c757d;'>Clicks</th>
            <th style='padding: 8px; text-align: center; font-size: 11px; border-right: 1px solid #6c757d;'>CTR</th>
            <th style='padding: 8px; text-align: center; font-size: 11px; border-right: 1px solid #6c757d;'>Conv.</th>
            <th style='padding: 8px; text-align: center; font-size: 11px; border-right: 1px solid #6c757d;'>Impr.Shr</th>
            <th style='padding: 8px; text-align: center; font-size: 11px; border-right: 1px solid #6c757d;'>Cost/Conv</th>
            <th style='padding: 8px; text-align: center; font-size: 11px; border-right: 1px solid #6c757d;'>Cost Micros</th>
        """
    
    html += """
                        </tr>
                    </thead>
                    <tbody>
    """
    
    # Generate rows for each week
    for i, week in enumerate(weeks_corrected):
        bg_color = "#f8f9fa" if i % 2 == 0 else "white"
        week_label = f"This Week" if i == 0 else f"Week {i+1}"
        
        # Calculate trend class for the whole row
        trend_class = ""
        if i > 0:
            # Compare with previous week for any campaign improvements
            has_improvement = False
            has_decline = False
            for campaign_name, campaign_data in campaigns.items():
                curr_week_data = campaign_data.get(week, {})
                prev_week_data = campaign_data.get(weeks_corrected[i-1], {})
                curr_clicks = curr_week_data.get('clicks', 0)
                prev_clicks = prev_week_data.get('clicks', 0)
                if curr_clicks > prev_clicks:
                    has_improvement = True
                elif curr_clicks < prev_clicks:
                    has_decline = True
            
            if has_improvement and not has_decline:
                trend_class = "style='background: linear-gradient(90deg, #d4f3d0, #f8f9fa);'"
            elif has_decline and not has_improvement:
                trend_class = "style='background: linear-gradient(90deg, #f8d7da, #f8f9fa);'"
        
        html += f"""
                        <tr {trend_class if trend_class else f"style='background-color: {bg_color};'"}>
                            <td style="padding: 12px; font-weight: 500; border-bottom: 1px solid #e9ecef; border-right: 2px solid #e9ecef;">
                                <div style="font-weight: bold; color: #333;">{week_label}</div>
                                <div style="font-size: 11px; color: #666;">{week}</div>
                            </td>
        """
        
        # Add data for each campaign in this week
        for campaign_name, campaign_data in campaigns.items():
            week_data = campaign_data.get(week, {})
            
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
            
            cost_micros = week_data.get('cost_micros', '—')
            cost_micros_formatted = f"€{cost_micros}" if cost_micros != '—' else '—'
            
            html += f"""
                            <td style="padding: 8px; text-align: center; border-bottom: 1px solid #e9ecef; border-right: 1px solid #e9ecef; font-size: 12px;">{impressions_formatted}</td>
                            <td style="padding: 8px; text-align: center; border-bottom: 1px solid #e9ecef; border-right: 1px solid #e9ecef; font-size: 12px; color: #667eea; font-weight: bold;">{clicks_formatted}</td>
                            <td style="padding: 8px; text-align: center; border-bottom: 1px solid #e9ecef; border-right: 1px solid #e9ecef; font-size: 12px;">{ctr_formatted}</td>
                            <td style="padding: 8px; text-align: center; border-bottom: 1px solid #e9ecef; border-right: 1px solid #e9ecef; font-size: 12px;">{conversions}</td>
                            <td style="padding: 8px; text-align: center; border-bottom: 1px solid #e9ecef; border-right: 1px solid #e9ecef; font-size: 12px;">{search_share_formatted}</td>
                            <td style="padding: 8px; text-align: center; border-bottom: 1px solid #e9ecef; border-right: 1px solid #e9ecef; font-size: 12px;">{cost_conv_formatted}</td>
                            <td style="padding: 8px; text-align: center; border-bottom: 1px solid #e9ecef; border-right: 1px solid #e9ecef; font-size: 12px;">{cost_micros_formatted}</td>
            """
        
        html += """
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
                    📊 <span>Daily Comparison Summary</span>
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
                        <div style="font-size: 16px; font-weight: bold; color: #0066cc;">{weeks_corrected[0] if weeks_corrected else 'N/A'}</div>
                        <div style="font-size: 12px; color: #666;">to {weeks_corrected[-1] if weeks_corrected else 'N/A'}</div>
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
                    🔄 Refresh Daily Data
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
            <p style="margin: 0;">🤖 Automated Google Ads Daily Comparison • Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p style="margin: 5px 0 0 0;">Daily data comparison showing last 4 weeks • Green = improvement, Red = decline</p>
        </div>
    </div>
    """
    
    return html

@app.route("/")
def index():
    global last_daily_data, report_ready
    if report_ready and last_daily_data:
        return format_daily_comparison_for_web(last_daily_data)
    else:
        return """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; text-align: center; padding: 40px; background: linear-gradient(135deg, #f8f9fa, #e9ecef); border-radius: 12px;">
            <h1 style="color: #333; margin-bottom: 20px;">📊 Google Ads Daily Comparison</h1>
            <div style="font-size: 64px; margin-bottom: 20px;">📅</div>
            <p style="color: #666; font-size: 18px; margin-bottom: 30px;">Welcome! Your daily comparison dashboard is ready to show the last 4 weeks of campaign data.</p>
            <div style="margin: 30px 0; padding: 20px; background: white; border-radius: 8px; border-left: 4px solid #ffc107;">
                <p style="margin: 0; color: #856404;"><strong>📈 Features:</strong></p>
                <p style="margin: 10px 0 0 0; color: #856404;">
                    • Side-by-side daily comparison<br>
                    • All key metrics in one view<br>
                    • Week-over-week trend indicators<br>
                    • Performance highlighting
                </p>
            </div>
            <a href="/trigger?key=supersecret123" style="background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 15px 30px; text-decoration: none; border-radius: 25px; font-weight: bold; display: inline-block; box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);">
                📊 Generate Daily Comparison
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

    global last_daily_data, report_ready
    
    try:
        print("🚀 Starting Google Ads daily comparison generation...")
        
        # Generate daily comparison data
        daily_data = fetch_daily_comparison_data()
        last_daily_data = daily_data
        report_ready = True
        
        print("✅ Daily comparison data generated successfully")
        print(f"📊 Found {len(daily_data.get('campaigns', {}))} campaigns across {len(daily_data.get('weeks', []))} weeks")

        # Try to send email
        email_status = "⚠️ Report generated but email not attempted"
        try:
            print("📧 Attempting to send daily comparison email...")
            send_daily_comparison_email(daily_data)
            email_status = "📧 Daily comparison email sent successfully"
            print("✅ Email sent successfully")
        except Exception as email_error:
            print(f"❌ Email failed: {email_error}")
            email_status = f"⚠️ Report generated but email failed: {str(email_error)[:50]}..."

        return f"""
        <div style="font-family: Arial, sans-serif; max-width: 700px; margin: 50px auto; text-align: center; padding: 40px; background: #d4edda; border-radius: 12px; border-left: 4px solid #28a745;">
            <h2 style="color: #155724;">✅ Daily Comparison Generated Successfully!</h2>
            <div style="font-size: 48px; margin: 20px 0;">📅</div>
            <p style="color: #155724; font-size: 16px; margin-bottom: 20px;">{email_status}</p>
            
            <div style="background: rgba(255,255,255,0.8); padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="color: #155724; margin-top: 0;">📊 Daily Summary</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 15px; text-align: center;">
                    <div>
                        <div style="font-size: 20px; font-weight: bold; color: #155724;">{len(daily_data.get('campaigns', {}))}</div>
                        <div style="font-size: 12px; color: #155724;">Campaigns</div>
                    </div>
                    <div>
                        <div style="font-size: 20px; font-weight: bold; color: #155724;">{len(daily_data.get('weeks', []))}</div>
                        <div style="font-size: 12px; color: #155724;">Weeks</div>
                    </div>
                    <div>
                        <div style="font-size: 16px; font-weight: bold; color: #155724;">{daily_data.get('weeks', ['N/A'])[-1] if daily_data.get('weeks') else 'N/A'}</div>
                        <div style="font-size: 12px; color: #155724;">Start Date</div>
                    </div>
                    <div>
                        <div style="font-size: 16px; font-weight: bold; color: #155724;">{daily_data.get('weeks', ['N/A'])[0] if daily_data.get('weeks') else 'N/A'}</div>
                        <div style="font-size: 12px; color: #155724;">End Date</div>
                    </div>
                </div>
            </div>
            
            <div style="margin-top: 25px;">
                <a href="/" style="background: #28a745; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 0 10px;">📊 View Daily Comparison</a>
                <a href="/trigger?key={key}" style="background: #17a2b8; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 0 10px;">🔄 Refresh Again</a>
            </div>
        </div>
        """
        
    except Exception as e:
        error_details = str(e)
        traceback_str = traceback.format_exc()
        print(f"❌ Daily comparison generation failed: {error_details}")
        print(f"🔍 Full traceback: {traceback_str}")
        
        return f"""
        <div style="font-family: Arial, sans-serif; max-width: 700px; margin: 50px auto; text-align: center; padding: 40px; background: #f8d7da; border-radius: 12px; border-left: 4px solid #dc3545;">
            <h2 style="color: #721c24;">❌ Daily Comparison Generation Failed</h2>
            <div style="font-size: 48px; margin: 20px 0;">⚠️</div>
            <p style="color: #721c24; font-size: 16px; margin-bottom: 20px;"><strong>Error:</strong> {error_details}</p>
            
            <div style="background: rgba(255,255,255,0.7); padding: 20px; border-radius: 6px; margin: 20px 0; text-align: left;">
                <h4 style="color: #721c24; margin-top: 0;">🔍 Troubleshooting Steps:</h4>
                <ol style="color: #721c24; padding-left: 20px;">
                    <li>Check that your Google Sheets has data for the last 4 weeks</li>
                    <li>Verify your GOOGLE_CREDENTIALS_B64 environment variable is set</li>
                    <li>Make sure your sheet has the required columns: Date, Campaign Name, Impressions, Clicks, CTR, Conversions, Search Impression Share, Cost Per Conversion, Cost Micros</li>
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
                <p style="color: #155724; font-size: 14px; margin-top: 15px;">Daily comparison emails will include all campaign data in a table format.</p>
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

@app.route("/api/daily-data")
def api_daily_data():
    """API endpoint to get raw daily comparison data as JSON"""
    global last_daily_data, report_ready
    if report_ready and last_daily_data:
        return jsonify(last_daily_data)
    else:
        return jsonify({"error": "No daily data available"}), 404

@app.route("/health")
def health():
    """Health check endpoint"""
    global last_daily_data, report_ready
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "report_ready": report_ready,
        "data_available": bool(last_daily_data),
        "campaigns_count": len(last_daily_data.get('campaigns', {})) if last_daily_data else 0,
        "weeks_count": len(last_daily_data.get('weeks', [])) if last_daily_data else 0,
        "version": "daily_comparison"
    })

print("🚀 Starting Google Ads Daily Comparison Dashboard...")
print(f"📊 Dashboard will be available at: http://localhost:{os.environ.get('PORT', 5000)}")
print(f"🔑 Trigger key: {os.getenv('TRIGGER_KEY', 'supersecret123')}")
print("📅 New features: 4-week comparison, side-by-side campaign data, trend indicators")

port = int(os.environ.get('PORT', 5000))
app.run(host='0.0.0.0', port=port, debug=False)