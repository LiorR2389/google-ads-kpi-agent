from flask import Flask, request, jsonify
from google_ads_api import fetch_sheet_data
from send_report_email import send_report_email, send_simple_test_email
import os
import traceback
from datetime import datetime

app = Flask(__name__)
last_insights = {}
report_ready = False

def format_insights_for_web(insights_data):
    """Convert insights data to HTML for web display"""
    summary = insights_data['summary']
    highlights = insights_data['highlights']
    
    html = f"""
    <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 1000px; margin: 0 auto; background: white; min-height: 100vh;">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center;">
            <h1 style="margin: 0; font-size: 28px;">📊 Google Ads Dashboard</h1>
            <p style="margin: 10px 0 0 0; opacity: 0.9;">Live Performance Data • {datetime.now().strftime('%B %d, %Y at %H:%M')}</p>
        </div>
        
        <div style="padding: 30px;">
            <!-- Summary Cards -->
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px;">
                <div style="background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 25px; border-radius: 12px; text-align: center; box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);">
                    <h3 style="margin: 0 0 10px 0; font-size: 14px; opacity: 0.9; text-transform: uppercase; letter-spacing: 1px;">Total Spend</h3>
                    <div style="font-size: 28px; font-weight: bold;">€{summary['total_spend']:.2f}</div>
                    <div style="font-size: 12px; opacity: 0.8; margin-top: 5px;">*Estimated</div>
                </div>
                <div style="background: linear-gradient(135deg, #28a745, #20c997); color: white; padding: 25px; border-radius: 12px; text-align: center; box-shadow: 0 4px 15px rgba(40, 167, 69, 0.3);">
                    <h3 style="margin: 0 0 10px 0; font-size: 14px; opacity: 0.9; text-transform: uppercase; letter-spacing: 1px;">Total Clicks</h3>
                    <div style="font-size: 28px; font-weight: bold;">{summary['total_clicks']:,}</div>
                    <div style="font-size: 12px; opacity: 0.8; margin-top: 5px;">Real Data</div>
                </div>
                <div style="background: linear-gradient(135deg, #ffc107, #fd7e14); color: white; padding: 25px; border-radius: 12px; text-align: center; box-shadow: 0 4px 15px rgba(255, 193, 7, 0.3);">
                    <h3 style="margin: 0 0 10px 0; font-size: 14px; opacity: 0.9; text-transform: uppercase; letter-spacing: 1px;">Avg CPC</h3>
                    <div style="font-size: 28px; font-weight: bold;">€{summary['avg_cpc']:.2f}</div>
                    <div style="font-size: 12px; opacity: 0.8; margin-top: 5px;">*Estimated</div>
                </div>
                <div style="background: linear-gradient(135deg, #17a2b8, #6f42c1); color: white; padding: 25px; border-radius: 12px; text-align: center; box-shadow: 0 4px 15px rgba(23, 162, 184, 0.3);">
                    <h3 style="margin: 0 0 10px 0; font-size: 14px; opacity: 0.9; text-transform: uppercase; letter-spacing: 1px;">Impressions</h3>
                    <div style="font-size: 28px; font-weight: bold;">{summary['total_impressions']:,}</div>
                    <div style="font-size: 12px; opacity: 0.8; margin-top: 5px;">Real Data</div>
                </div>
            </div>
            
            <!-- Highlights Table -->
            <h2 style="color: #333; font-size: 24px; margin-bottom: 20px; display: flex; align-items: center; gap: 10px;">
                🎯 <span>Performance Highlights</span>
            </h2>
            <div style="background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.1); margin-bottom: 30px;">
                <table style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr style="background: linear-gradient(135deg, #343a40, #495057); color: white;">
                            <th style="padding: 20px; text-align: left; font-weight: 600; font-size: 14px;">Metric</th>
                            <th style="padding: 20px; text-align: left; font-weight: 600; font-size: 14px;">Campaign</th>
                            <th style="padding: 20px; text-align: left; font-weight: 600; font-size: 14px;">Value</th>
                        </tr>
                    </thead>
                    <tbody>
    """
    
    for i, highlight in enumerate(highlights):
        bg_color = "#f8f9fa" if i % 2 == 0 else "white"
        html += f"""
                        <tr style="background-color: {bg_color}; transition: background-color 0.2s;">
                            <td style="padding: 15px; border-bottom: 1px solid #e9ecef; font-weight: 500;">{highlight['metric']}</td>
                            <td style="padding: 15px; border-bottom: 1px solid #e9ecef; color: #495057;">{highlight['campaign']}</td>
                            <td style="padding: 15px; border-bottom: 1px solid #e9ecef; color: #667eea; font-weight: bold; font-size: 16px;">{highlight['value']}</td>
                        </tr>
        """
    
    html += f"""
                    </tbody>
                </table>
            </div>
            
            <!-- Chart Section -->
            <h2 style="color: #333; font-size: 24px; margin-bottom: 20px; display: flex; align-items: center; gap: 10px;">
                💰 <span>Spend Overview</span>
            </h2>
            <div style="background: white; border-radius: 12px; padding: 30px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); text-align: center; margin-bottom: 30px;">
                <img src="/static/spend_chart.png" style="max-width: 100%; height: auto; border-radius: 8px;" alt="Spend Chart">
            </div>
            
            <!-- Quick Stats -->
            <div style="background: linear-gradient(135deg, #e7f3ff, #f0f8ff); border-left: 5px solid #0066cc; padding: 25px; border-radius: 0 12px 12px 0; margin-bottom: 30px;">
                <h3 style="color: #0066cc; margin-top: 0; margin-bottom: 15px; display: flex; align-items: center; gap: 8px;">
                    📊 <span>Key Insights</span>
                </h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin-bottom: 15px;">
                    <div style="text-align: center;">
                        <div style="font-size: 14px; color: #666; margin-bottom: 5px;">Average CTR</div>
                        <div style="font-size: 20px; font-weight: bold; color: #0066cc;">{summary['avg_ctr']:.2f}%</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 14px; color: #666; margin-bottom: 5px;">Total Conversions</div>
                        <div style="font-size: 20px; font-weight: bold; color: #0066cc;">{summary['total_conversions']}</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 14px; color: #666; margin-bottom: 5px;">Avg Conv. Rate</div>
                        <div style="font-size: 20px; font-weight: bold; color: #0066cc;">{summary['avg_conversion_rate']:.1f}%</div>
                    </div>
                </div>
                <div style="border-top: 1px solid #cce7ff; padding-top: 15px; margin-top: 15px;">
                    <p style="margin: 0; color: #0066cc; font-weight: 500;">💡 Your Demand Gen campaign is performing exceptionally well with strong CTR!</p>
                </div>
            </div>
            
            <!-- Action Buttons -->
            <div style="text-align: center; margin-top: 30px;">
                <a href="/trigger?key={os.getenv('TRIGGER_KEY', 'supersecret123')}" 
                   style="background: linear-gradient(135deg, #28a745, #20c997); color: white; padding: 12px 25px; text-decoration: none; border-radius: 25px; font-weight: bold; margin: 0 10px; display: inline-block; box-shadow: 0 4px 15px rgba(40, 167, 69, 0.3); transition: transform 0.2s;" 
                   onmouseover="this.style.transform='translateY(-2px)'" 
                   onmouseout="this.style.transform='translateY(0)'">
                    🔄 Refresh Data
                </a>
                <a href="/test-email" 
                   style="background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 12px 25px; text-decoration: none; border-radius: 25px; font-weight: bold; margin: 0 10px; display: inline-block; box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3); transition: transform 0.2s;" 
                   onmouseover="this.style.transform='translateY(-2px)'" 
                   onmouseout="this.style.transform='translateY(0)'">
                    📧 Test Email
                </a>
            </div>
        </div>
        
        <!-- Footer -->
        <div style="background: #f8f9fa; padding: 20px; text-align: center; font-size: 12px; color: #6c757d; border-top: 1px solid #e9ecef;">
            <p style="margin: 0;">🤖 Automated Google Ads Reporting • Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p style="margin: 5px 0 0 0;">* Spend estimates based on industry benchmarks • Real data: Impressions, Clicks, CTR</p>
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
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; text-align: center; padding: 40px; background: linear-gradient(135deg, #f8f9fa, #e9ecef); border-radius: 12px;">
            <h1 style="color: #333; margin-bottom: 20px;">📊 Google Ads KPI Dashboard</h1>
            <div style="font-size: 64px; margin-bottom: 20px;">🚀</div>
            <p style="color: #666; font-size: 18px; margin-bottom: 30px;">Welcome! Your dashboard is ready to go.</p>
            <div style="margin: 30px 0; padding: 20px; background: white; border-radius: 8px; border-left: 4px solid #ffc107;">
                <p style="margin: 0; color: #856404;"><strong>💡 Getting Started:</strong></p>
                <p style="margin: 10px 0 0 0; color: #856404;">Click the button below to fetch your latest Google Ads data and generate your first report!</p>
            </div>
            <a href="/trigger?key=supersecret123" style="background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 15px 30px; text-decoration: none; border-radius: 25px; font-weight: bold; display: inline-block; box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);">
                🚀 Generate Report
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

    global last_insights, report_ready
    
    try:
        print("🚀 Starting Google Ads report generation...")
        
        # Generate report data
        df, insights_data = fetch_sheet_data()
        last_insights = insights_data
        report_ready = True
        
        print("✅ Report data generated successfully")
        print(f"📊 Summary: €{insights_data['summary']['total_spend']:.2f} spend, {insights_data['summary']['total_clicks']:,} clicks")

        # Try to send email
        email_status = "⚠️ Report generated but email not attempted"
        try:
            print("📧 Attempting to send email...")
            send_report_email(insights_data, "static/spend_chart.png")
            email_status = "📧 Email sent successfully"
            print("✅ Email sent successfully")
        except Exception as email_error:
            print(f"❌ Email failed: {email_error}")
            email_status = f"⚠️ Report generated but email failed: {str(email_error)[:50]}..."

        return f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; text-align: center; padding: 40px; background: #d4edda; border-radius: 12px; border-left: 4px solid #28a745;">
            <h2 style="color: #155724;">✅ Report Generated Successfully!</h2>
            <div style="font-size: 48px; margin: 20px 0;">🎉</div>
            <p style="color: #155724; font-size: 16px; margin-bottom: 20px;">{email_status}</p>
            
            <div style="background: rgba(255,255,255,0.8); padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="color: #155724; margin-top: 0;">📊 Quick Summary</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 15px; text-align: center;">
                    <div>
                        <div style="font-size: 20px; font-weight: bold; color: #155724;">€{last_insights['summary']['total_spend']:.2f}</div>
                        <div style="font-size: 12px; color: #155724;">Est. Spend</div>
                    </div>
                    <div>
                        <div style="font-size: 20px; font-weight: bold; color: #155724;">{last_insights['summary']['total_clicks']:,}</div>
                        <div style="font-size: 12px; color: #155724;">Clicks</div>
                    </div>
                    <div>
                        <div style="font-size: 20px; font-weight: bold; color: #155724;">{last_insights['summary']['total_impressions']:,}</div>
                        <div style="font-size: 12px; color: #155724;">Impressions</div>
                    </div>
                    <div>
                        <div style="font-size: 20px; font-weight: bold; color: #155724;">{last_insights['summary']['avg_ctr']:.1f}%</div>
                        <div style="font-size: 12px; color: #155724;">Avg CTR</div>
                    </div>
                </div>
            </div>
            
            <div style="margin-top: 25px;">
                <a href="/" style="background: #28a745; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 0 10px;">📊 View Dashboard</a>
                <a href="/trigger?key={key}" style="background: #17a2b8; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 0 10px;">🔄 Refresh Again</a>
            </div>
        </div>
        """
        
    except Exception as e:
        error_details = str(e)
        traceback_str = traceback.format_exc()
        print(f"❌ Report generation failed: {error_details}")
        print(f"🔍 Full traceback: {traceback_str}")
        
        return f"""
        <div style="font-family: Arial, sans-serif; max-width: 700px; margin: 50px auto; text-align: center; padding: 40px; background: #f8d7da; border-radius: 12px; border-left: 4px solid #dc3545;">
            <h2 style="color: #721c24;">❌ Report Generation Failed</h2>
            <div style="font-size: 48px; margin: 20px 0;">⚠️</div>
            <p style="color: #721c24; font-size: 16px; margin-bottom: 20px;"><strong>Error:</strong> {error_details}</p>
            
            <div style="background: rgba(255,255,255,0.7); padding: 20px; border-radius: 6px; margin: 20px 0; text-align: left;">
                <h4 style="color: #721c24; margin-top: 0;">🔍 Troubleshooting Steps:</h4>
                <ol style="color: #721c24; padding-left: 20px;">
                    <li>Check that your Google Sheets is accessible and has data</li>
                    <li>Verify your GOOGLE_CREDENTIALS_B64 environment variable is set</li>
                    <li>Make sure your sheet has the columns: Date, Campaign Name, Impressions, Clicks, CTR</li>
                    <li>Try the test email to verify your email configuration</li>
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

@app.route("/api/data")
def api_data():
    """API endpoint to get raw data as JSON"""
    global last_insights, report_ready
    if report_ready and last_insights:
        return jsonify(last_insights)
    else:
        return jsonify({"error": "No data available"}), 404

@app.route("/health")
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "report_ready": report_ready,
        "data_available": bool(last_insights)
    })

if __name__ == '__main__':
    print("🚀 Starting Google Ads KPI Dashboard...")
    print(f"📊 Dashboard will be available at: http://localhost:{os.environ.get('PORT', 5000)}")
    print(f"🔑 Trigger key: {os.getenv('TRIGGER_KEY', 'supersecret123')}")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)