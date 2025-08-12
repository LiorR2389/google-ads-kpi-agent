from flask import Flask, request, jsonify
from google_ads_api import fetch_daily_comparison_data, fetch_keynote_comparison_data
from send_report_email import send_daily_comparison_email, send_keynote_comparison_email, send_simple_test_email
import os
import traceback
from datetime import datetime, timedelta
import pandas as pd

app = Flask(__name__)
last_daily_data = {}
last_keynote_data = {}
luma_report_ready = False
keynote_report_ready = False

def format_daily_comparison_for_web(daily_data, campaign_type="Luma"):
    """Convert daily comparison data to HTML for web display"""
    campaigns = daily_data.get('campaigns', {})
    weeks = daily_data.get('weeks', [])
    
    # Set theme colors based on campaign type
    if campaign_type == "Keynote":
        primary_color = "#dc3545"
        gradient = "linear-gradient(135deg, #dc3545 0%, #c82333 100%)"
        accent_color = "#f8d7da"
        trigger_url = "/trigger-keynote"
    else:
        primary_color = "#667eea"
        gradient = "linear-gradient(135deg, #667eea 0%, #764ba2 100%)"
        accent_color = "#e7f3ff"
        trigger_url = "/trigger"
    
    if not campaigns or not weeks:
        return f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; text-align: center; padding: 40px; background: #f8d7da; border-radius: 12px;">
            <h2 style="color: #721c24;">📊 No {campaign_type} Data Available</h2>
            <p style="color: #721c24;">No {campaign_type.lower()} campaign data found for daily comparison.</p>
            <a href="{trigger_url}?key=supersecret123" style="background: {primary_color}; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold;">🔄 Generate {campaign_type} Data</a>
        </div>
        """
    
    html = f"""
    <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 1400px; margin: 0 auto; background: white; min-height: 100vh;">
        <div style="background: {gradient}; color: white; padding: 30px; text-align: center;">
            <h1 style="margin: 0; font-size: 28px;">📊 Google Ads {campaign_type} Daily Comparison</h1>
            <p style="margin: 10px 0 0 0; opacity: 0.9;">Last 4 Weeks Performance Data • {datetime.now().strftime('%B %d, %Y at %H:%M')}</p>
            <p style="margin: 5px 0 0 0; opacity: 0.8; font-size: 14px;">📈 Week-over-week comparison for all {campaign_type.lower()} campaigns</p>
        </div>
        
        <div style="padding: 30px;">
            <!-- Week Headers -->
            <div style="margin-bottom: 20px; text-align: center;">
                <h2 style="color: #333; margin-bottom: 15px;">📅 Comparing Last 4 Weeks - {campaign_type}</h2>
                <div style="display: flex; justify-content: center; gap: 20px; flex-wrap: wrap;">
    """
    
    # Reverse the weeks list so the most recent week is actually "This Week"
    weeks_corrected = list(reversed(weeks))
    
    for i, week in enumerate(weeks_corrected):
        week_label = f"This Week" if i == 0 else f"Week {i+1}"
        html += f"""
                    <div style="background: {accent_color}; padding: 10px 20px; border-radius: 8px; border-left: 4px solid {primary_color};">
                        <div style="font-weight: bold; color: {primary_color};">{week_label}</div>
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
            <h3 style="color: #333; margin-bottom: 15px; padding: 15px; background: #f8f9fa; border-left: 4px solid {primary_color}; border-radius: 0 8px 8px 0;">
                📈 All {campaign_type} Campaigns Daily Comparison
            </h3>
            
            <div style="overflow-x: auto; box-shadow: 0 4px 15px rgba(0,0,0,0.1); border-radius: 12px;">
                <table style="width: 100%; border-collapse: collapse; background: white; min-width: 1200px;">
                    <thead>
                        <tr style="background: linear-gradient(135deg, #343a40, #495057); color: white;">
                            <th rowspan="2" style="padding: 15px; text-align: left; font-weight: 600; min-width: 120px; border-right: 2px solid #495057;">Week</th>
    """
    
    # Campaign headers
    for campaign_name in campaigns.keys():
        html += f"<th colspan='8' style='padding: 15px; text-align: center; font-weight: 600; border-right: 1px solid #495057;'>{campaign_name[:30]}{'...' if len(campaign_name) > 30 else ''}</th>"
    
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
            <th style='padding: 8px; text-align: center; font-size: 11px; border-right: 1px solid #6c757d;'>Phone Calls</th>
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
            
            phone_calls = week_data.get('phone_calls', '—')
            phone_calls_formatted = f"€{phone_calls}" if phone_calls != '—' else '—'
            
            html += f"""
                            <td style="padding: 8px; text-align: center; border-bottom: 1px solid #e9ecef; border-right: 1px solid #e9ecef; font-size: 12px;">{impressions_formatted}</td>
                            <td style="padding: 8px; text-align: center; border-bottom: 1px solid #e9ecef; border-right: 1px solid #e9ecef; font-size: 12px; color: {primary_color}; font-weight: bold;">{clicks_formatted}</td>
                            <td style="padding: 8px; text-align: center; border-bottom: 1px solid #e9ecef; border-right: 1px solid #e9ecef; font-size: 12px;">{ctr_formatted}</td>
                            <td style="padding: 8px; text-align: center; border-bottom: 1px solid #e9ecef; border-right: 1px solid #e9ecef; font-size: 12px;">{conversions}</td>
                            <td style="padding: 8px; text-align: center; border-bottom: 1px solid #e9ecef; border-right: 1px solid #e9ecef; font-size: 12px;">{search_share_formatted}</td>
                            <td style="padding: 8px; text-align: center; border-bottom: 1px solid #e9ecef; border-right: 1px solid #e9ecef; font-size: 12px;">{cost_conv_formatted}</td>
                            <td style="padding: 8px; text-align: center; border-bottom: 1px solid #e9ecef; border-right: 1px solid #e9ecef; font-size: 12px;">{cost_micros_formatted}</td>
                            <td style="padding: 8px; text-align: center; border-bottom: 1px solid #e9ecef; border-right: 1px solid #e9ecef; font-size: 12px;">{phone_calls_formatted}</td>
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
            <div style="background: {accent_color}; border-left: 4px solid {primary_color}; padding: 25px; margin: 30px 0; border-radius: 0 12px 12px 0;">
                <h3 style="color: {primary_color}; margin-top: 0; margin-bottom: 15px; display: flex; align-items: center; gap: 8px;">
                    📊 <span>{campaign_type} Daily Comparison Summary</span>
                </h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
                    <div style="text-align: center; background: white; padding: 15px; border-radius: 8px;">
                        <div style="font-size: 14px; color: #666; margin-bottom: 5px;">Total Campaigns</div>
                        <div style="font-size: 24px; font-weight: bold; color: {primary_color};">{len(campaigns)}</div>
                    </div>
                    <div style="text-align: center; background: white; padding: 15px; border-radius: 8px;">
                        <div style="font-size: 14px; color: #666; margin-bottom: 5px;">Weeks Compared</div>
                        <div style="font-size: 24px; font-weight: bold; color: {primary_color};">{len(weeks)}</div>
                    </div>
                    <div style="text-align: center; background: white; padding: 15px; border-radius: 8px;">
                        <div style="font-size: 14px; color: #666; margin-bottom: 5px;">Data Period</div>
                        <div style="font-size: 16px; font-weight: bold; color: {primary_color};">{weeks_corrected[0] if weeks_corrected else 'N/A'}</div>
                        <div style="font-size: 12px; color: #666;">to {weeks_corrected[-1] if weeks_corrected else 'N/A'}</div>
                    </div>
                </div>
                <div style="border-top: 1px solid #cce7ff; padding-top: 15px; margin-top: 15px;">
                    <p style="margin: 0; color: {primary_color}; font-weight: 500;">
                        💡 Green highlighting indicates week-over-week improvement in clicks. 
                        Red highlighting indicates decline. Use this data to identify trends and optimize campaigns.
                    </p>
                </div>
            </div>
            
            <!-- Action Buttons -->
            <div style="text-align: center; margin-top: 30px;">
                <a href="{trigger_url}?key={os.getenv('TRIGGER_KEY', 'supersecret123')}" 
                   style="background: linear-gradient(135deg, #28a745, #20c997); color: white; padding: 12px 25px; text-decoration: none; border-radius: 25px; font-weight: bold; margin: 0 10px; display: inline-block; box-shadow: 0 4px 15px rgba(40, 167, 69, 0.3); transition: transform 0.2s;" 
                   onmouseover="this.style.transform='translateY(-2px)'" 
                   onmouseout="this.style.transform='translateY(0)'">
                    🔄 Refresh {campaign_type} Data
                </a>
                <a href="/test-email" 
                   style="background: {gradient}; color: white; padding: 12px 25px; text-decoration: none; border-radius: 25px; font-weight: bold; margin: 0 10px; display: inline-block; box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3); transition: transform 0.2s;" 
                   onmouseover="this.style.transform='translateY(-2px)'" 
                   onmouseout="this.style.transform='translateY(0)'">
                    📧 Email Report
                </a>
                <a href="/test-email" style="background: #dc3545; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 0 10px;">📧 Test Email</a>
                <a href="/" style="background: #6c757d; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 0 10px;">🏠 Home</a>
            </div>
        </div>
        
        <!-- Footer -->
        <div style="background: #f8f9fa; padding: 20px; text-align: center; font-size: 12px; color: #6c757d; border-top: 1px solid #e9ecef;">
            <p style="margin: 0;">🤖 Automated Google Ads {campaign_type} Daily Comparison • Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p style="margin: 5px 0 0 0;">Daily data comparison showing last 4 weeks • Green = improvement, Red = decline</p>
        </div>
    </div>
    """
    
    return html

@app.route("/trigger-keynote")
def trigger_keynote():
    key = request.args.get("key")
    if key != os.getenv("TRIGGER_KEY"):
        return """
        <div style="font-family: Arial, sans-serif; max-width: 400px; margin: 50px auto; text-align: center; padding: 40px; background: #f8d7da; border-radius: 12px; border-left: 4px solid #dc3545;">
            <h2 style="color: #721c24;">❌ Unauthorized</h2>
            <p style="color: #721c24;">Invalid trigger key provided.</p>
        </div>
        """, 403

    global last_keynote_data, keynote_report_ready
    
    try:
        print("🚀 Starting Google Ads Keynote daily comparison generation...")
        
        # Generate Keynote daily comparison data
        keynote_data = fetch_keynote_comparison_data()
        last_keynote_data = keynote_data
        keynote_report_ready = True
        
        print("✅ Keynote daily comparison data generated successfully")
        print(f"📊 Found {len(keynote_data.get('campaigns', {}))} campaigns across {len(keynote_data.get('weeks', []))} weeks")

        # Try to send email
        email_status = "⚠️ Keynote report generated but email not attempted"
        try:
            print("📧 Attempting to send Keynote daily comparison email...")
            send_keynote_comparison_email(keynote_data)
            email_status = "📧 Keynote daily comparison email sent successfully"
            print("✅ Keynote email sent successfully")
        except Exception as email_error:
            print(f"❌ Keynote email failed: {email_error}")
            email_status = f"⚠️ Keynote report generated but email failed: {str(email_error)[:50]}..."

        return f"""
        <div style="font-family: Arial, sans-serif; max-width: 700px; margin: 50px auto; text-align: center; padding: 40px; background: #d4edda; border-radius: 12px; border-left: 4px solid #28a745;">
            <h2 style="color: #155724;">✅ Keynote Daily Comparison Generated Successfully!</h2>
            <div style="font-size: 48px; margin: 20px 0;">📅</div>
            <p style="color: #155724; font-size: 16px; margin-bottom: 20px;">{email_status}</p>
            
            <div style="background: rgba(255,255,255,0.8); padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="color: #155724; margin-top: 0;">📊 Keynote Daily Summary</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 15px; text-align: center;">
                    <div>
                        <div style="font-size: 20px; font-weight: bold; color: #155724;">{len(keynote_data.get('campaigns', {}))}</div>
                        <div style="font-size: 12px; color: #155724;">Campaigns</div>
                    </div>
                    <div>
                        <div style="font-size: 20px; font-weight: bold; color: #155724;">{len(keynote_data.get('weeks', []))}</div>
                        <div style="font-size: 12px; color: #155724;">Weeks</div>
                    </div>
                    <div>
                        <div style="font-size: 16px; font-weight: bold; color: #155724;">{keynote_data.get('weeks', ['N/A'])[-1] if keynote_data.get('weeks') else 'N/A'}</div>
                        <div style="font-size: 12px; color: #155724;">Start Date</div>
                    </div>
                    <div>
                        <div style="font-size: 16px; font-weight: bold; color: #155724;">{keynote_data.get('weeks', ['N/A'])[0] if keynote_data.get('weeks') else 'N/A'}</div>
                        <div style="font-size: 12px; color: #155724;">End Date</div>
                    </div>
                </div>
            </div>
            
            <div style="margin-top: 25px;">
                <a href="/keynote" style="background: #dc3545; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 0 10px;">📊 View Keynote Comparison</a>
                <a href="/trigger-keynote?key={key}" style="background: #17a2b8; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 0 10px;">🔄 Refresh Again</a>
                <a href="/" style="background: #667eea; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 0 10px;">🔵 View Luma</a>
            </div>
        </div>
        """
        
    except Exception as e:
        error_details = str(e)
        traceback_str = traceback.format_exc()
        print(f"❌ Keynote daily comparison generation failed: {error_details}")
        print(f"🔍 Full traceback: {traceback_str}")
        
        return f"""
        <div style="font-family: Arial, sans-serif; max-width: 700px; margin: 50px auto; text-align: center; padding: 40px; background: #f8d7da; border-radius: 12px; border-left: 4px solid #dc3545;">
            <h2 style="color: #721c24;">❌ Keynote Daily Comparison Generation Failed</h2>
            <div style="font-size: 48px; margin: 20px 0;">⚠️</div>
            <p style="color: #721c24; font-size: 16px; margin-bottom: 20px;"><strong>Error:</strong> {error_details}</p>
            
            <div style="background: rgba(255,255,255,0.7); padding: 20px; border-radius: 6px; margin: 20px 0; text-align: left;">
                <h4 style="color: #721c24; margin-top: 0;">🔍 Troubleshooting Steps:</h4>
                <ol style="color: #721c24; padding-left: 20px;">
                    <li>Check that your Google Sheets has Keynote data for the last 4 weeks</li>
                    <li>Verify your GOOGLE_CREDENTIALS_B64 environment variable is set</li>
                    <li>Make sure your Keynote sheet has the required columns</li>
                    <li>Ensure dates are in YYYY-MM-DD format</li>
                    <li>Check that there's data for multiple weeks</li>
                </ol>
            </div>
            
            <div style="margin-top: 25px;">
                <a href="/test-email" style="background: #dc3545; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 0 10px;">📧 Test Email</a>
                <a href="/keynote" style="background: #6c757d; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 0 10px;">🏠 Keynote Home</a>
            </div>
        </div>
        """

@app.route("/trigger-both")
def trigger_both():
    """Trigger both Luma and Keynote reports"""
    key = request.args.get("key")
    if key != os.getenv("TRIGGER_KEY"):
        return """
        <div style="font-family: Arial, sans-serif; max-width: 400px; margin: 50px auto; text-align: center; padding: 40px; background: #f8d7da; border-radius: 12px; border-left: 4px solid #dc3545;">
            <h2 style="color: #721c24;">❌ Unauthorized</h2>
            <p style="color: #721c24;">Invalid trigger key provided.</p>
        </div>
        """, 403

    global last_daily_data, last_keynote_data, luma_report_ready, keynote_report_ready
    
    luma_status = ""
    keynote_status = ""
    
    # Generate Luma report
    try:
        print("🚀 Starting Luma daily comparison generation...")
        luma_data = fetch_daily_comparison_data()
        last_daily_data = luma_data
        luma_report_ready = True
        
        try:
            send_daily_comparison_email(luma_data)
            luma_status = "✅ Luma report generated and sent successfully"
        except:
            luma_status = "⚠️ Luma report generated but email failed"
            
    except Exception as e:
        luma_status = f"❌ Luma report failed: {str(e)[:50]}..."
    
    # Wait between reports
    import time
    time.sleep(5)
    
    # Generate Keynote report
    try:
        print("🚀 Starting Keynote daily comparison generation...")
        keynote_data = fetch_keynote_comparison_data()
        last_keynote_data = keynote_data
        keynote_report_ready = True
        
        try:
            send_keynote_comparison_email(keynote_data)
            keynote_status = "✅ Keynote report generated and sent successfully"
        except:
            keynote_status = "⚠️ Keynote report generated but email failed"
            
    except Exception as e:
        keynote_status = f"❌ Keynote report failed: {str(e)[:50]}..."

    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 700px; margin: 50px auto; text-align: center; padding: 40px; background: #d4edda; border-radius: 12px; border-left: 4px solid #28a745;">
        <h2 style="color: #155724;">📊 Both Reports Processing Complete</h2>
        <div style="font-size: 48px; margin: 20px 0;">📈📊</div>
        
        <div style="background: rgba(255,255,255,0.8); padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3 style="color: #155724; margin-top: 0;">Report Status</h3>
            <div style="text-align: left; padding: 10px;">
                <p style="color: #155724; font-size: 14px;">🔵 <strong>Luma:</strong> {luma_status}</p>
                <p style="color: #155724; font-size: 14px;">🔴 <strong>Keynote:</strong> {keynote_status}</p>
            </div>
        </div>
        
        <div style="margin-top: 25px;">
            <a href="/" style="background: #667eea; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 0 10px;">📊 View Luma</a>
            <a href="/keynote" style="background: #dc3545; color: white; padding: 12