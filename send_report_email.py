import os
import smtplib
import base64
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

def generate_simple_html_email(insights_data, chart_base64):
    """Generate a clean, simple HTML email"""
    summary = insights_data['summary']
    highlights = insights_data['highlights']
    campaigns = insights_data['campaigns'][:5]  # Top 5 campaigns
    
    # Generate highlights rows
    highlights_html = ""
    for highlight in highlights:
        highlights_html += f"""
        <tr style="border-bottom: 1px solid #eee;">
            <td style="padding: 10px; font-weight: bold;">{highlight['metric']}</td>
            <td style="padding: 10px;">{highlight['campaign']}</td>
            <td style="padding: 10px; color: #667eea; font-weight: bold;">{highlight['value']}</td>
        </tr>
        """
    
    # Generate campaign rows
    campaigns_html = ""
    for campaign in campaigns:
        campaigns_html += f"""
        <tr style="border-bottom: 1px solid #eee;">
            <td style="padding: 8px; font-size: 12px;">{campaign['campaign'][:25]}...</td>
            <td style="padding: 8px; text-align: center;">{int(campaign['impressions']):,}</td>
            <td style="padding: 8px; text-align: center;">{int(campaign['clicks']):,}</td>
            <td style="padding: 8px; text-align: center;">{campaign['ctr']:.1f}%</td>
            <td style="padding: 8px; text-align: center;">€{campaign['spend']:.2f}</td>
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
        <div style="max-width: 800px; margin: 0 auto; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center;">
                <h1 style="margin: 0; font-size: 24px;">📊 Google Ads Daily Report</h1>
                <p style="margin: 10px 0 0 0; opacity: 0.9;">{datetime.now().strftime('%B %d, %Y')}</p>
            </div>
            
            <!-- Summary -->
            <div style="padding: 30px;">
                <div style="display: flex; flex-wrap: wrap; gap: 15px; margin-bottom: 30px;">
                    <div style="flex: 1; min-width: 150px; background: #f8f9fa; padding: 20px; border-radius: 6px; text-align: center; border-left: 4px solid #667eea;">
                        <div style="font-size: 12px; color: #667eea; font-weight: bold; margin-bottom: 5px;">TOTAL SPEND</div>
                        <div style="font-size: 20px; font-weight: bold;">€{summary['total_spend']:.2f}</div>
                    </div>
                    <div style="flex: 1; min-width: 150px; background: #f8f9fa; padding: 20px; border-radius: 6px; text-align: center; border-left: 4px solid #28a745;">
                        <div style="font-size: 12px; color: #28a745; font-weight: bold; margin-bottom: 5px;">TOTAL CLICKS</div>
                        <div style="font-size: 20px; font-weight: bold;">{summary['total_clicks']:,}</div>
                    </div>
                    <div style="flex: 1; min-width: 150px; background: #f8f9fa; padding: 20px; border-radius: 6px; text-align: center; border-left: 4px solid #ffc107;">
                        <div style="font-size: 12px; color: #e67e22; font-weight: bold; margin-bottom: 5px;">AVG CPC</div>
                        <div style="font-size: 20px; font-weight: bold;">€{summary['avg_cpc']:.2f}</div>
                    </div>
                    <div style="flex: 1; min-width: 150px; background: #f8f9fa; padding: 20px; border-radius: 6px; text-align: center; border-left: 4px solid #17a2b8;">
                        <div style="font-size: 12px; color: #17a2b8; font-weight: bold; margin-bottom: 5px;">IMPRESSIONS</div>
                        <div style="font-size: 20px; font-weight: bold;">{summary['total_impressions']:,}</div>
                    </div>
                </div>
                
                <!-- Highlights -->
                <h2 style="color: #333; margin-bottom: 15px; border-bottom: 2px solid #eee; padding-bottom: 10px;">🎯 Performance Highlights</h2>
                <table style="width: 100%; border-collapse: collapse; margin-bottom: 30px;">
                    <thead>
                        <tr style="background: #667eea; color: white;">
                            <th style="padding: 12px; text-align: left;">Metric</th>
                            <th style="padding: 12px; text-align: left;">Campaign</th>
                            <th style="padding: 12px; text-align: left;">Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        {highlights_html}
                    </tbody>
                </table>
                
                <!-- Top Campaigns -->
                <h2 style="color: #333; margin-bottom: 15px; border-bottom: 2px solid #eee; padding-bottom: 10px;">📈 Top Campaign Performance</h2>
                <table style="width: 100%; border-collapse: collapse; margin-bottom: 30px; font-size: 14px;">
                    <thead>
                        <tr style="background: #343a40; color: white;">
                            <th style="padding: 10px; text-align: left;">Campaign</th>
                            <th style="padding: 10px; text-align: center;">Impressions</th>
                            <th style="padding: 10px; text-align: center;">Clicks</th>
                            <th style="padding: 10px; text-align: center;">CTR</th>
                            <th style="padding: 10px; text-align: center;">Est. Spend</th>
                        </tr>
                    </thead>
                    <tbody>
                        {campaigns_html}
                    </tbody>
                </table>
                
                <!-- Chart -->
                <h2 style="color: #333; margin-bottom: 15px; border-bottom: 2px solid #eee; padding-bottom: 10px;">💰 Spend Overview</h2>
                <div style="text-align: center; padding: 20px; background: #f8f9fa; border-radius: 6px;">
                    <img src="data:image/png;base64,{chart_base64}" style="max-width: 100%; height: auto;" alt="Spend Chart" />
                </div>
                
                <!-- Recommendations -->
                <div style="background: #e7f3ff; border-left: 4px solid #0066cc; padding: 20px; margin: 20px 0; border-radius: 0 6px 6px 0;">
                    <h3 style="color: #0066cc; margin-top: 0;">✅ Quick Recommendations</h3>
                    <ul style="margin: 0; padding-left: 20px; color: #333;">
                        <li style="margin-bottom: 5px;">🚀 <strong>Demand Gen campaign</strong> shows excellent CTR - consider increasing budget</li>
                        <li style="margin-bottom: 5px;">🔍 <strong>Performance Max</strong> has good conversion potential - optimize targeting</li>
                        <li style="margin-bottom: 5px;">📊 <strong>Search campaigns</strong> may need keyword review for better efficiency</li>
                    </ul>
                </div>
            </div>
            
            <!-- Footer -->
            <div style="background: #f8f9fa; padding: 20px; text-align: center; font-size: 12px; color: #666;">
                <p style="margin: 0;">Generated by KPI Bot | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p style="margin: 5px 0 0 0;">* Spend values are estimates based on industry benchmarks</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html

def send_report_email(insights_data, image_path):
    """Send report with multiple fallback methods"""
    
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
        # Get chart as base64
        chart_base64 = ""
        if os.path.exists(image_path):
            with open(image_path, 'rb') as f:
                chart_base64 = base64.b64encode(f.read()).decode('utf-8')
        else:
            print(f"⚠️ Chart image not found: {image_path}")
        
        # Create HTML email
        html_content = generate_simple_html_email(insights_data, chart_base64)
        
        # Create plain text version
        summary = insights_data['summary']
        plain_text = f"""
Google Ads Daily Report - {datetime.now().strftime('%B %d, %Y')}

SUMMARY:
• Total Spend: €{summary['total_spend']:.2f}
• Total Clicks: {summary['total_clicks']:,}
• Total Impressions: {summary['total_impressions']:,}
• Average CPC: €{summary['avg_cpc']:.2f}
• Average CTR: {summary['avg_ctr']:.2f}%

TOP PERFORMERS:
"""
        for highlight in insights_data['highlights']:
            plain_text += f"• {highlight['metric']}: {highlight['campaign']} ({highlight['value']})\n"
        
        plain_text += "\n* Spend values are estimates based on industry benchmarks"
        plain_text += "\nPlease view HTML version for charts and full details."
        
        # Create email message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"📊 Google Ads Report - {datetime.now().strftime('%b %d, %Y')}"
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
                
                print("✅ Email sent successfully!")
                return
                
            except smtplib.SMTPAuthenticationError as e:
                print(f"❌ Authentication failed: {e}")
                print("💡 Tip: Make sure you're using an App Password, not your regular Gmail password")
                break  # Don't try other configs for auth errors
                
            except smtplib.SMTPServerDisconnected as e:
                print(f"❌ Server disconnected: {e}")
                continue  # Try next config
                
            except Exception as e:
                print(f"❌ Failed with {config['host']}:{config['port']} - {e}")
                continue
        
        print("❌ All SMTP configurations failed")
        
    except Exception as e:
        print(f"❌ Email preparation failed: {e}")
        raise

# Alternative: Simple email without attachments for testing
def send_simple_test_email():
    """Send a simple test email to verify SMTP works"""
    email_user = os.getenv("EMAIL_USER")
    email_password = os.getenv("EMAIL_PASSWORD")
    email_to = os.getenv("EMAIL_TO")
    
    if not all([email_user, email_password, email_to]):
        print("❌ Missing email configuration")
        return False
    
    try:
        # Simple HTML message
        html = f"""
        <html>
        <body>
            <h2>🧪 Google Ads Bot Test</h2>
            <p>This is a test email from your Google Ads reporting bot.</p>
            <p><strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>If you receive this, your email configuration is working! ✅</p>
        </body>
        </html>
        """
        
        msg = MIMEMultipart()
        msg['Subject'] = "🧪 Google Ads Bot Test"
        msg['From'] = email_user
        msg['To'] = email_to
        msg.attach(MIMEText(html, 'html'))
        
        # Try Gmail SMTP
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(email_user, email_password)
            server.send_message(msg)
            print("✅ Test email sent successfully!")
            return True
            
    except Exception as e:
        print(f"❌ Test email failed: {e}")
        return False