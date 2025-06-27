import os
import smtplib
import base64
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

def send_weekly_comparison_email(weekly_data):
    """Send weekly comparison email with campaign data in table format"""
    
    # Check environment variables
    email_user = os.getenv("EMAIL_USER")
    email_password = os.getenv("EMAIL_PASSWORD") 
    email_to = os.getenv("EMAIL_TO")
    
    if not all([email_user, email_password, email_to]):
        print("❌ Missing email configuration:")
        print(f"   EMAIL_USER: {'✓' if email_user else '✗'}")
        print(f"   EMAIL_PASSWORD: {'✓' if email_password else '✗'}")  
        print(f"   EMAIL_TO: {'✓' if email_to else '✗'}")
        return
    
    try:
        campaigns = weekly_data.get('campaigns', {})
        weeks = weekly_data.get('weeks', [])
        
        if not campaigns or not weeks:
            print("❌ No campaign data to send")
            return
        
        # Create HTML email
        html_content = generate_weekly_comparison_html(weekly_data)
        
        # Create plain text version
        plain_text = generate_weekly_comparison_text(weekly_data)
        
        # Create email message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"📊 Google Ads Weekly Comparison - {datetime.now().strftime('%b %d, %Y')}"
        msg['From'] = email_user
        msg['To'] = email_to
        
        # Add text and HTML parts
        text_part = MIMEText(plain_text, 'plain')
        html_part = MIMEText(html_content, 'html')
        
        msg.attach(text_part)
        msg.attach(html_part)
        
        # Try different SMTP configurations
        smtp_configs = [
            {"host": "smtp.gmail.com", "port": 587, "use_tls": True},
            {"host": "smtp.gmail.com", "port": 465, "use_ssl": True}
        ]
        
        for config in smtp_configs:
            try:
                print(f"🔄 Trying SMTP: {config['host']}:{config['port']}")
                
                if config.get("use_ssl"):
                    server = smtplib.SMTP_SSL(config["host"], config["port"])
                    print("✓ SSL connection established")
                else:
                    server = smtplib.SMTP(config["host"], config["port"])
                    if config.get("use_tls"):
                        server.starttls()
                        print("✓ TLS connection established")
                
                server.login(email_user, email_password)
                print("✓ Login successful")
                
                server.send_message(msg)
                server.quit()
                
                print("✅ Weekly comparison email sent successfully!")
                return
                
            except smtplib.SMTPAuthenticationError as e:
                print(f"❌ Authentication failed: {e}")
                print("💡 Tip: Make sure you're using an App Password, not your regular Gmail password")
                break
                
            except smtplib.SMTPServerDisconnected as e:
                print(f"❌ Server disconnected: {e}")
                continue
                
            except Exception as e:
                print(f"❌ Failed with {config['host']}:{config['port']} - {e}")
                continue
        
        print("❌ All SMTP configurations failed")
        
    except Exception as e:
        print(f"❌ Email preparation failed: {e}")
        raise

def generate_weekly_comparison_html(weekly_data):
    """Generate HTML email for weekly comparison"""
    campaigns = weekly_data.get('campaigns', {})
    weeks = weekly_data.get('weeks', [])
    
    # Week headers
    week_headers = ""
    for i, week in enumerate(weeks):
        week_label = f"Week {i+1}" if i > 0 else "This Week"
        week_headers += f"<th colspan='6' style='padding: 15px; text-align: center; background: #667eea; color: white; font-weight: 600;'>{week_label}<br><span style='font-size: 11px; opacity: 0.8;'>{week}</span></th>"
    
    # Subheaders for metrics
    metric_headers = ""
    for _ in weeks:
        metric_headers += """
            <th style='padding: 8px; text-align: center; background: #495057; color: white; font-size: 11px;'>Impr.</th>
            <th style='padding: 8px; text-align: center; background: #495057; color: white; font-size: 11px;'>Clicks</th>
            <th style='padding: 8px; text-align: center; background: #495057; color: white; font-size: 11px;'>CTR</th>
            <th style='padding: 8px; text-align: center; background: #495057; color: white; font-size: 11px;'>Conv.</th>
            <th style='padding: 8px; text-align: center; background: #495057; color: white; font-size: 11px;'>Impr.Share</th>
            <th style='padding: 8px; text-align: center; background: #495057; color: white; font-size: 11px;'>Cost/Conv</th>
        """
    
    # Campaign rows
    campaign_rows = ""
    for i, (campaign_name, campaign_data) in enumerate(campaigns.items()):
        bg_color = "#f8f9fa" if i % 2 == 0 else "white"
        
        week_cells = ""
        for week in weeks:
            week_data = campaign_data.get(week, {})
            
            impressions = week_data.get('impressions', '—')
            clicks = week_data.get('clicks', '—')
            ctr = week_data.get('ctr', '—')
            conversions = week_data.get('conversions', '—')
            search_share = week_data.get('search_impression_share', '—')
            cost_conv = week_data.get('cost_per_conversion', '—')
            
            # Format numbers properly
            impressions_formatted = f"{impressions:,}" if isinstance(impressions, (int, float)) else str(impressions)
            clicks_formatted = f"{clicks:,}" if isinstance(clicks, (int, float)) else str(clicks)
            ctr_formatted = f"{ctr}%" if ctr != '—' else '—'
            search_share_formatted = f"{search_share}%" if search_share != '—' else '—'
            cost_conv_formatted = f"€{cost_conv}" if cost_conv != '—' else '—'
            
            week_cells += f"""
                <td style='padding: 8px; text-align: center; border-bottom: 1px solid #e9ecef; font-size: 12px;'>{impressions_formatted}</td>
                <td style='padding: 8px; text-align: center; border-bottom: 1px solid #e9ecef; font-size: 12px; color: #667eea; font-weight: bold;'>{clicks_formatted}</td>
                <td style='padding: 8px; text-align: center; border-bottom: 1px solid #e9ecef; font-size: 12px;'>{ctr_formatted}</td>
                <td style='padding: 8px; text-align: center; border-bottom: 1px solid #e9ecef; font-size: 12px;'>{conversions}</td>
                <td style='padding: 8px; text-align: center; border-bottom: 1px solid #e9ecef; font-size: 12px;'>{search_share_formatted}</td>
                <td style='padding: 8px; text-align: center; border-bottom: 1px solid #e9ecef; font-size: 12px;'>{cost_conv_formatted}</td>
            """
        
        campaign_rows += f"""
            <tr style='background-color: {bg_color};'>
                <td style='padding: 12px; border-bottom: 1px solid #e9ecef; font-weight: 500; font-size: 13px; max-width: 200px; word-wrap: break-word;'>{campaign_name}</td>
                {week_cells}
            </tr>
        """
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 20px; font-family: Arial, sans-serif; background-color: #f5f5f5;">
        <div style="max-width: 1200px; margin: 0 auto; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center;">
                <h1 style="margin: 0; font-size: 24px;">📊 Google Ads Weekly Comparison</h1>
                <p style="margin: 10px 0 0 0; opacity: 0.9;">Last 4 Weeks Performance • {datetime.now().strftime('%B %d, %Y')}</p>
            </div>
            
            <!-- Weekly Comparison Table -->
            <div style="padding: 30px;">
                <h2 style="color: #333; margin-bottom: 20px; display: flex; align-items: center; gap: 10px;">
                    📅 <span>Campaign Performance by Week</span>
                </h2>
                
                <div style="overflow-x: auto; box-shadow: 0 2px 8px rgba(0,0,0,0.1); border-radius: 8px;">
                    <table style="width: 100%; border-collapse: collapse; background: white; min-width: 1000px;">
                        <thead>
                            <tr style="background: linear-gradient(135deg, #343a40, #495057);">
                                <th rowspan="2" style="padding: 15px; text-align: left; color: white; font-weight: 600; border-right: 2px solid #495057;">Campaign</th>
                                {week_headers}
                            </tr>
                            <tr>
                                {metric_headers}
                            </tr>
                        </thead>
                        <tbody>
                            {campaign_rows}
                        </tbody>
                    </table>
                </div>
                
                <!-- Summary Stats -->
                <div style="background: #e7f3ff; border-left: 4px solid #0066cc; padding: 20px; margin: 30px 0; border-radius: 0 8px 8px 0;">
                    <h3 style="color: #0066cc; margin-top: 0; margin-bottom: 15px;">📊 Summary</h3>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px;">
                        <div style="text-align: center; background: white; padding: 15px; border-radius: 6px;">
                            <div style="font-size: 14px; color: #666; margin-bottom: 5px;">Campaigns</div>
                            <div style="font-size: 20px; font-weight: bold; color: #0066cc;">{len(campaigns)}</div>
                        </div>
                        <div style="text-align: center; background: white; padding: 15px; border-radius: 6px;">
                            <div style="font-size: 14px; color: #666; margin-bottom: 5px;">Weeks</div>
                            <div style="font-size: 20px; font-weight: bold; color: #0066cc;">{len(weeks)}</div>
                        </div>
                        <div style="text-align: center; background: white; padding: 15px; border-radius: 6px;">
                            <div style="font-size: 14px; color: #666; margin-bottom: 5px;">Date Range</div>
                            <div style="font-size: 12px; font-weight: bold; color: #0066cc;">{weeks[-1] if weeks else 'N/A'}</div>
                            <div style="font-size: 12px; color: #666;">to {weeks[0] if weeks else 'N/A'}</div>
                        </div>
                    </div>
                    <div style="border-top: 1px solid #cce7ff; padding-top: 15px; margin-top: 15px;">
                        <p style="margin: 0; color: #0066cc; font-weight: 500; font-size: 14px;">
                            💡 Use this weekly comparison to identify trends and optimize your campaigns. 
                            Look for consistent performers and investigate any significant drops or spikes.
                        </p>
                    </div>
                </div>
                
                <!-- Legend -->
                <div style="background: #f8f9fa; padding: 15px; border-radius: 6px; margin-top: 20px;">
                    <h4 style="color: #333; margin-top: 0; margin-bottom: 10px; font-size: 14px;">📋 Column Definitions</h4>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; font-size: 12px; color: #666;">
                        <div><strong>Impr.:</strong> Impressions</div>
                        <div><strong>Clicks:</strong> Total clicks</div>
                        <div><strong>CTR:</strong> Click-through rate (%)</div>
                        <div><strong>Conv.:</strong> Conversions</div>
                        <div><strong>Impr.Share:</strong> Search impression share (%)</div>
                        <div><strong>Cost/Conv:</strong> Cost per conversion (€)</div>
                    </div>
                </div>
            </div>
            
            <!-- Footer -->
            <div style="background: #f8f9fa; padding: 20px; text-align: center; font-size: 12px; color: #666; border-top: 1px solid #e9ecef;">
                <p style="margin: 0;">🤖 Automated Google Ads Weekly Comparison • Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p style="margin: 5px 0 0 0;">Weekly performance data for the last 4 weeks • Monitor trends to optimize campaign performance</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html

def generate_weekly_comparison_text(weekly_data):
    """Generate plain text version of weekly comparison"""
    campaigns = weekly_data.get('campaigns', {})
    weeks = weekly_data.get('weeks', [])
    
    text = f"""
Google Ads Weekly Comparison - {datetime.now().strftime('%B %d, %Y')}

WEEKLY PERFORMANCE OVERVIEW:
Campaigns analyzed: {len(campaigns)}
Weeks compared: {len(weeks)}
Date range: {weeks[-1] if weeks else 'N/A'} to {weeks[0] if weeks else 'N/A'}

CAMPAIGN DATA:
"""
    
    for campaign_name, campaign_data in campaigns.items():
        text += f"\n{campaign_name}:\n"
        text += "-" * 50 + "\n"
        
        for i, week in enumerate(weeks):
            week_label = f"Week {i+1}" if i > 0 else "This Week"
            week_data = campaign_data.get(week, {})
            
            impressions = week_data.get('impressions', '—')
            clicks = week_data.get('clicks', '—')
            ctr = week_data.get('ctr', '—')
            conversions = week_data.get('conversions', '—')
            
            # Format numbers properly
            impressions_formatted = f"{impressions:,}" if isinstance(impressions, (int, float)) else str(impressions)
            clicks_formatted = f"{clicks:,}" if isinstance(clicks, (int, float)) else str(clicks)
            ctr_formatted = f"{ctr}%" if ctr != '—' else '—'
            
            text += f"{week_label} ({week}):\n"
            text += f"  Impressions: {impressions_formatted}\n"
            text += f"  Clicks: {clicks_formatted}\n"
            text += f"  CTR: {ctr_formatted}\n"
            text += f"  Conversions: {conversions}\n"
            text += "\n"
    
    text += """
Please view the HTML version for the complete table format with all metrics.

Column Definitions:
- Impr.: Impressions
- Clicks: Total clicks
- CTR: Click-through rate (%)
- Conv.: Conversions
- Impr.Share: Search impression share (%)
- Cost/Conv: Cost per conversion (€)
"""
    
    return text

def send_simple_test_email():
    """Send a simple test email to verify SMTP works"""
    email_user = os.getenv("EMAIL_USER")
    email_password = os.getenv("EMAIL_PASSWORD")
    email_to = os.getenv("EMAIL_TO")
    
    if not all([email_user, email_password, email_to]):
        print("❌ Missing email configuration")
        return False
    
    try:
        html = f"""
        <html>
        <body>
            <h2>🧪 Google Ads Bot Test</h2>
            <p>This is a test email from your enhanced Google Ads reporting bot with weekly comparison.</p>
            <p><strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>If you receive this, your email configuration is working! ✅</p>
            <p><em>Next report will include 4-week campaign comparison tables.</em></p>
        </body>
        </html>
        """
        
        msg = MIMEMultipart()
        msg['Subject'] = "🧪 Google Ads Bot Test - Weekly Comparison Ready"
        msg['From'] = email_user
        msg['To'] = email_to
        msg.attach(MIMEText(html, 'html'))
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(email_user, email_password)
            server.send_message(msg)
            print("✅ Test email sent successfully!")
            return True
            
    except Exception as e:
        print(f"❌ Test email failed: {e}")
        return False