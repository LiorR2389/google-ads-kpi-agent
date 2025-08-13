import os
import smtplib
import base64
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

def send_daily_comparison_email(daily_data):
    """Send daily comparison email with Luma campaign data in table format"""
    
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
        campaigns = daily_data.get('campaigns', {})
        weeks = daily_data.get('weeks', [])
        
        if not campaigns or not weeks:
            print("❌ No Luma campaign data to send")
            return
        
        # DEBUG: Check Luma conversion data
        conversion_actions = daily_data.get('conversion_actions', [])
        print(f"🔍 DEBUG LUMA: Conversion actions count: {len(conversion_actions)}")
        if conversion_actions:
            print(f"🔍 DEBUG LUMA: First conversion keys: {list(conversion_actions[0].keys())}")
            print(f"🔍 DEBUG LUMA: First conversion data: {conversion_actions[0]}")
        
        # Create HTML email
        html_content = generate_daily_comparison_html(daily_data, "Luma")
        
        # Create plain text version
        plain_text = generate_daily_comparison_text(daily_data, "Luma")
        
        # Create email message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"gads luma campaign - {datetime.now().strftime('%b %d, %Y')}"
        msg['From'] = email_user
        msg['To'] = email_to
        
        # Add text and HTML parts
        text_part = MIMEText(plain_text, 'plain')
        html_part = MIMEText(html_content, 'html')
        
        msg.attach(text_part)
        msg.attach(html_part)
        
        # Send email
        _send_email(msg, email_user, email_password)
        print("✅ Luma daily comparison email sent successfully!")
        
    except Exception as e:
        print(f"❌ Luma email preparation failed: {e}")
        raise

def send_keynote_comparison_email(keynote_data):
    """Send daily comparison email with Keynote campaign data in table format"""
    
    # Check environment variables
    email_user = os.getenv("EMAIL_USER")
    email_password = os.getenv("EMAIL_PASSWORD") 
    email_to = os.getenv("EMAIL_TO")
    
    if not all([email_user, email_password, email_to]):
        print("❌ Missing email configuration for Keynote")
        return
    
    try:
        campaigns = keynote_data.get('campaigns', {})
        weeks = keynote_data.get('weeks', [])
        
        if not campaigns or not weeks:
            print("❌ No Keynote campaign data to send")
            return
        
        # DEBUG: Check Keynote conversion data
        conversion_actions = keynote_data.get('conversions', [])  # FIXED: Use 'conversions' key instead of 'conversion_actions'
        print(f"🔍 DEBUG KEYNOTE: Conversion actions count: {len(conversion_actions)}")
        if conversion_actions:
            print(f"🔍 DEBUG KEYNOTE: First conversion keys: {list(conversion_actions[0].keys())}")
            print(f"🔍 DEBUG KEYNOTE: First conversion data: {conversion_actions[0]}")
            print(f"🔍 DEBUG KEYNOTE: All conversion data: {conversion_actions}")
        else:
            print(f"🔍 DEBUG KEYNOTE: No conversion actions found in data")
            print(f"🔍 DEBUG KEYNOTE: Available keynote_data keys: {list(keynote_data.keys())}")
        
        # Create HTML email - explicitly pass conversion data with correct key
        keynote_data_with_conversions = keynote_data.copy()
        keynote_data_with_conversions['conversion_actions'] = conversion_actions  # FIXED: Ensure HTML function gets data under expected key
        html_content = generate_daily_comparison_html(keynote_data_with_conversions, "Keynote")
        
        # Create plain text version
        keynote_data_with_conversions['conversion_actions'] = conversion_actions  # Also fix for text version
        plain_text = generate_daily_comparison_text(keynote_data_with_conversions, "Keynote")
        
        # Create email message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"gads keynote campaign - {datetime.now().strftime('%b %d, %Y')}"
        msg['From'] = email_user
        msg['To'] = email_to
        
        # Add text and HTML parts
        text_part = MIMEText(plain_text, 'plain')
        html_part = MIMEText(html_content, 'html')
        
        msg.attach(text_part)
        msg.attach(html_part)
        
        # Send email
        _send_email(msg, email_user, email_password)
        print("✅ Keynote daily comparison email sent successfully!")
        
    except Exception as e:
        print(f"❌ Keynote email preparation failed: {e}")
        raise


    
def _send_email(msg, email_user, email_password):
    """Helper function to send email with different SMTP configurations"""
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

def generate_daily_comparison_html(daily_data, campaign_type="Luma"):
    """Generate HTML email for daily comparison"""
    campaigns = daily_data.get('campaigns', {})
    weeks = daily_data.get('weeks', [])
    conversion_actions = daily_data.get('conversion_actions', [])
    
    # DEBUG: Check what we receive
    print(f"🔍 DEBUG HTML {campaign_type}: conversion_actions type: {type(conversion_actions)}")
    print(f"🔍 DEBUG HTML {campaign_type}: conversion_actions length: {len(conversion_actions) if conversion_actions else 0}")
    if conversion_actions:
        print(f"🔍 DEBUG HTML {campaign_type}: First item: {conversion_actions[0]}")
        print(f"🔍 DEBUG HTML {campaign_type}: First item keys: {list(conversion_actions[0].keys()) if isinstance(conversion_actions[0], dict) else 'Not a dict'}")
    
    # Reverse the weeks list so the most recent week is actually "This Week"
    weeks_corrected = list(reversed(weeks))
    
    # Week headers
    week_headers = ""
    for i, week in enumerate(weeks_corrected):
        week_label = f"This Week" if i == 0 else f"Week {i+1}"
        week_headers += f"<th colspan='8' style='padding: 15px; text-align: center; background: #667eea; color: white; font-weight: 600;'>{week_label}<br><span style='font-size: 11px; opacity: 0.8;'>{week}</span></th>"
    
    # Subheaders for metrics
    metric_headers = ""
    for _ in weeks_corrected:
        metric_headers += """
            <th style='padding: 8px; text-align: center; background: #495057; color: white; font-size: 11px;'>Impr.</th>
            <th style='padding: 8px; text-align: center; background: #495057; color: white; font-size: 11px;'>Clicks</th>
            <th style='padding: 8px; text-align: center; background: #495057; color: white; font-size: 11px;'>CTR</th>
            <th style='padding: 8px; text-align: center; background: #495057; color: white; font-size: 11px;'>Conv.</th>
            <th style='padding: 8px; text-align: center; background: #495057; color: white; font-size: 11px;'>Impr.Share</th>
            <th style='padding: 8px; text-align: center; background: #495057; color: white; font-size: 11px;'>Cost/Conv</th>
            <th style='padding: 8px; text-align: center; background: #495057; color: white; font-size: 11px;'>Cost Micros</th>
            <th style='padding: 8px; text-align: center; background: #495057; color: white; font-size: 11px;'>Phone Calls</th>
        """
    
    # Campaign rows
    campaign_rows = ""
    for i, (campaign_name, campaign_data) in enumerate(campaigns.items()):
        bg_color = "#f8f9fa" if i % 2 == 0 else "white"
        
        week_cells = ""
        for week in weeks_corrected:
            week_data = campaign_data.get(week, {})
            
            impressions = week_data.get('impressions', '—')
            clicks = week_data.get('clicks', '—')
            ctr = week_data.get('ctr', '—')
            conversions = week_data.get('conversions', '—')
            search_share = week_data.get('search_impression_share', '—')
            cost_conv = week_data.get('cost_per_conversion', '—')
            cost_micros = week_data.get('cost_micros', '—')
            phone_calls = week_data.get('phone_calls', '—')
            
            # Format numbers properly
            impressions_formatted = f"{impressions:,}" if isinstance(impressions, (int, float)) else str(impressions)
            clicks_formatted = f"{clicks:,}" if isinstance(clicks, (int, float)) else str(clicks)
            ctr_formatted = f"{ctr}%" if ctr != '—' else '—'
            search_share_formatted = f"{search_share}%" if search_share != '—' else '—'
            cost_conv_formatted = f"€{cost_conv}" if cost_conv != '—' else '—'
            cost_micros_formatted = f"€{cost_micros}" if cost_micros != '—' else '—'
            phone_calls_formatted = f"€{phone_calls}" if phone_calls != '—' else '—'
            
            week_cells += f"""
                <td style='padding: 8px; text-align: center; border-bottom: 1px solid #e9ecef; font-size: 12px;'>{impressions_formatted}</td>
                <td style='padding: 8px; text-align: center; border-bottom: 1px solid #e9ecef; font-size: 12px; color: #667eea; font-weight: bold;'>{clicks_formatted}</td>
                <td style='padding: 8px; text-align: center; border-bottom: 1px solid #e9ecef; font-size: 12px;'>{ctr_formatted}</td>
                <td style='padding: 8px; text-align: center; border-bottom: 1px solid #e9ecef; font-size: 12px;'>{conversions}</td>
                <td style='padding: 8px; text-align: center; border-bottom: 1px solid #e9ecef; font-size: 12px;'>{search_share_formatted}</td>
                <td style='padding: 8px; text-align: center; border-bottom: 1px solid #e9ecef; font-size: 12px;'>{cost_conv_formatted}</td>
                <td style='padding: 8px; text-align: center; border-bottom: 1px solid #e9ecef; font-size: 12px;'>{cost_micros_formatted}</td>
                <td style='padding: 8px; text-align: center; border-bottom: 1px solid #e9ecef; font-size: 12px;'>{phone_calls_formatted}</td>
            """
        
        campaign_rows += f"""
            <tr style='background-color: {bg_color};'>
                <td style='padding: 12px; border-bottom: 1px solid #e9ecef; font-weight: 500; font-size: 13px; max-width: 200px; word-wrap: break-word;'>{campaign_name}</td>
                {week_cells}
            </tr>
        """
    
    # Set colors based on campaign type
    if campaign_type == "Keynote":
        primary_color = "#dc3545"  # Red theme for Keynote
        gradient = "linear-gradient(135deg, #dc3545 0%, #c82333 100%)"
        accent_color = "#f8d7da"
    else:
        primary_color = "#667eea"  # Blue theme for Luma
        gradient = "linear-gradient(135deg, #667eea 0%, #764ba2 100%)"
        accent_color = "#e7f3ff"
    
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
            <div style="background: {gradient}; color: white; padding: 30px; text-align: center;">
                <h1 style="margin: 0; font-size: 24px;">📊 Google Ads {campaign_type} Daily Comparison</h1>
                <p style="margin: 10px 0 0 0; opacity: 0.9;">Last 4 Weeks Performance • {datetime.now().strftime('%B %d, %Y')}</p>
            </div>
            
            <!-- Daily Comparison Table -->
            <div style="padding: 30px;">
                <h2 style="color: #333; margin-bottom: 20px; display: flex; align-items: center; gap: 10px;">
                    📅 <span>{campaign_type} Campaign Performance by Week</span>
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
                <div style="background: {accent_color}; border-left: 4px solid {primary_color}; padding: 20px; margin: 30px 0; border-radius: 0 8px 8px 0;">
                    <h3 style="color: {primary_color}; margin-top: 0; margin-bottom: 15px;">📊 {campaign_type} Summary</h3>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px;">
                        <div style="text-align: center; background: white; padding: 15px; border-radius: 6px;">
                            <div style="font-size: 14px; color: #666; margin-bottom: 5px;">Campaigns</div>
                            <div style="font-size: 20px; font-weight: bold; color: {primary_color};">{len(campaigns)}</div>
                        </div>
                        <div style="text-align: center; background: white; padding: 15px; border-radius: 6px;">
                            <div style="font-size: 14px; color: #666; margin-bottom: 5px;">Weeks</div>
                            <div style="font-size: 20px; font-weight: bold; color: {primary_color};">{len(weeks_corrected)}</div>
                        </div>
                        <div style="text-align: center; background: white; padding: 15px; border-radius: 6px;">
                            <div style="font-size: 14px; color: #666; margin-bottom: 5px;">Date Range</div>
                            <div style="font-size: 12px; font-weight: bold; color: {primary_color};">{weeks_corrected[0] if weeks_corrected else 'N/A'}</div>
                            <div style="font-size: 12px; color: #666;">to {weeks_corrected[-1] if weeks_corrected else 'N/A'}</div>
                        </div>
                    </div>
                    <div style="border-top: 1px solid #cce7ff; padding-top: 15px; margin-top: 15px;">
                        <p style="margin: 0; color: {primary_color}; font-weight: 500; font-size: 14px;">
                            💡 Use this {campaign_type.lower()} daily comparison to identify trends and optimize your campaigns. 
                            Look for consistent performers and investigate any significant drops or spikes.
                        </p>
                    </div>
                </div>
                
                <!-- Conversion Actions Table -->
                <div style="margin-top: 40px;">
                    <h2 style="color: #333; margin-bottom: 20px; display: flex; align-items: center; gap: 10px;">
                        🎯 <span>{campaign_type} Conversion Actions (Last 7 Days)</span>
                    </h2>
                    
                    <div style="overflow-x: auto; box-shadow: 0 2px 8px rgba(0,0,0,0.1); border-radius: 8px;">
                        <table style="width: 100%; border-collapse: collapse; background: white;">
                            <thead>
                                <tr style="background: linear-gradient(135deg, #28a745, #20c997);">
                                    <th style="padding: 15px; text-align: left; color: white; font-weight: 600;">Date</th>
                                    <th style="padding: 15px; text-align: left; color: white; font-weight: 600;">Campaign Name</th>
                                    <th style="padding: 15px; text-align: center; color: white; font-weight: 600;">Conversions</th>
                                    <th style="padding: 15px; text-align: left; color: white; font-weight: 600;">Conversion Action</th>
                                </tr>
                            </thead>
                            <tbody>"""
    
    # Add conversion action rows - FIXED VERSION WITH ENHANCED DEBUG
    if conversion_actions:
        print(f"🔍 DEBUG HTML {campaign_type}: Processing {len(conversion_actions)} conversion actions")
        for i, row in enumerate(conversion_actions):
            bg_color = "#f8f9fa" if i % 2 == 0 else "white"
            
            print(f"🔍 DEBUG HTML {campaign_type}: Row {i}: {row}")
            print(f"🔍 DEBUG HTML {campaign_type}: Row {i} type: {type(row)}")
            
            if isinstance(row, dict):
                print(f"🔍 DEBUG HTML {campaign_type}: Row {i} keys: {list(row.keys())}")
                
                # Try all possible field name combinations
                date = (row.get('Date') or 
                       row.get('date_parsed') or 
                       row.get('date') or 
                       str(list(row.values())[0]) if row else '')
                
                campaign = (row.get('Campaign Name') or 
                           row.get('campaign') or 
                           row.get('Campaign') or
                           str(list(row.values())[1]) if len(row.values()) > 1 else '')
                
                conversions = (row.get('Conversions') or 
                              row.get('conversions') or 
                              str(list(row.values())[2]) if len(row.values()) > 2 else '')
                
                action_name = (row.get('Conversion Action Name') or 
                              row.get('Conversion Action') or 
                              row.get('action_name') or
                              str(list(row.values())[3]) if len(row.values()) > 3 else '')
                
                # Handle datetime objects
                if hasattr(date, 'strftime'):
                    date = date.strftime('%Y-%m-%d')
                elif hasattr(date, 'date'):
                    date = date.date().strftime('%Y-%m-%d')
                
                print(f"🔍 DEBUG HTML {campaign_type}: Extracted - Date: {date}, Campaign: {campaign}, Conversions: {conversions}, Action: {action_name}")
                
                html += f"""
                                    <tr style="background-color: {bg_color};">
                                        <td style="padding: 12px; border-bottom: 1px solid #e9ecef; font-size: 13px;">{date}</td>
                                        <td style="padding: 12px; border-bottom: 1px solid #e9ecef; font-size: 13px;">{campaign}</td>
                                        <td style="padding: 12px; border-bottom: 1px solid #e9ecef; font-size: 13px; text-align: center; font-weight: bold; color: #28a745;">{conversions}</td>
                                        <td style="padding: 12px; border-bottom: 1px solid #e9ecef; font-size: 13px;">{action_name}</td>
                                    </tr>
                """
            else:
                print(f"🔍 DEBUG HTML {campaign_type}: Row {i} is not a dict: {row}")
    else:
        print(f"🔍 DEBUG HTML {campaign_type}: No conversion actions to process")
        html += """
                                <tr>
                                    <td colspan="4" style="padding: 20px; text-align: center; color: #666; font-style: italic;">No conversion data available</td>
                                </tr>
        """
    
    html += f"""
                            </tbody>
                        </table>
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
                        <div><strong>Cost Micros:</strong> Cost in micros (€)</div>
                        <div><strong>Phone Calls:</strong> Phone calls (€)</div>
                    </div>
                </div>
            </div>
            
            <!-- Footer -->
            <div style="background: #f8f9fa; padding: 20px; text-align: center; font-size: 12px; color: #666; border-top: 1px solid #e9ecef;">
                <p style="margin: 0;">🤖 Automated Google Ads {campaign_type} Daily Comparison • Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p style="margin: 5px 0 0 0;">{campaign_type} daily performance data for the last 4 weeks • Monitor trends to optimize campaign performance</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html

def generate_daily_comparison_text(daily_data, campaign_type="Luma"):
    """Generate plain text version of daily comparison"""
    campaigns = daily_data.get('campaigns', {})
    weeks = daily_data.get('weeks', [])
    conversion_actions = daily_data.get('conversion_actions', [])
    
    # DEBUG: Check text conversion data
    print(f"🔍 DEBUG TEXT {campaign_type}: conversion_actions length: {len(conversion_actions) if conversion_actions else 0}")
    
    # Reverse the weeks list so the most recent week is actually "This Week"
    weeks_corrected = list(reversed(weeks))
    
    text = f"""
Google Ads {campaign_type} Daily Comparison - {datetime.now().strftime('%B %d, %Y')}

{campaign_type.upper()} PERFORMANCE OVERVIEW:
Campaigns analyzed: {len(campaigns)}
Weeks compared: {len(weeks_corrected)}
Date range: {weeks_corrected[0] if weeks_corrected else 'N/A'} to {weeks_corrected[-1] if weeks_corrected else 'N/A'}

{campaign_type.upper()} CAMPAIGN DATA:
"""
    
    for campaign_name, campaign_data in campaigns.items():
        text += f"\n{campaign_name}:\n"
        text += "-" * 50 + "\n"
        
        for i, week in enumerate(weeks_corrected):
            week_label = f"This Week" if i == 0 else f"Week {i+1}"
            week_data = campaign_data.get(week, {})
            
            impressions = week_data.get('impressions', '—')
            clicks = week_data.get('clicks', '—')
            ctr = week_data.get('ctr', '—')
            conversions = week_data.get('conversions', '—')
            cost_micros = week_data.get('cost_micros', '—')
            phone_calls = week_data.get('phone_calls', '—')
            
            # Format numbers properly
            impressions_formatted = f"{impressions:,}" if isinstance(impressions, (int, float)) else str(impressions)
            clicks_formatted = f"{clicks:,}" if isinstance(clicks, (int, float)) else str(clicks)
            ctr_formatted = f"{ctr}%" if ctr != '—' else '—'
            cost_micros_formatted = f"€{cost_micros}" if cost_micros != '—' else '—'
            phone_calls_formatted = f"€{phone_calls}" if phone_calls != '—' else '—'
            
            text += f"{week_label} ({week}):\n"
            text += f"  Impressions: {impressions_formatted}\n"
            text += f"  Clicks: {clicks_formatted}\n"
            text += f"  CTR: {ctr_formatted}\n"
            text += f"  Conversions: {conversions}\n"
            text += f"  Cost Micros: {cost_micros_formatted}\n"
            text += f"  Phone Calls: {phone_calls_formatted}\n"
            text += "\n"
    
    text += f"""
Please view the HTML version for the complete table format with all metrics.

{campaign_type.upper()} CONVERSION ACTIONS (Last 7 Days):
"""
    
    if conversion_actions:
        text += "-" * 80 + "\n"
        text += f"{'Date':<12} {'Campaign':<30} {'Conversions':<12} {'Action':<20}\n"
        text += "-" * 80 + "\n"
        
        # FIXED conversion data extraction for text version with debug
        for i, row in enumerate(conversion_actions):
            print(f"🔍 DEBUG TEXT {campaign_type}: Processing row {i}: {row}")
            
            if isinstance(row, dict):
                date = str(row.get('Date', row.get('date_parsed', '')))[:10]
                campaign = str(row.get('Campaign Name', ''))[:28]
                conversions = str(row.get('Conversions', ''))
                action_name = str(row.get('Conversion Action Name', ''))[:18]
                
                # Handle datetime objects
                if hasattr(row.get('date_parsed'), 'strftime'):
                    date = row.get('date_parsed').strftime('%Y-%m-%d')
                
                print(f"🔍 DEBUG TEXT {campaign_type}: Extracted - Date: {date}, Campaign: {campaign}, Conversions: {conversions}, Action: {action_name}")
                
                text += f"{date:<12} {campaign:<30} {conversions:<12} {action_name:<20}\n"
    else:
        text += "No conversion action data available.\n"

    text += f"""
{campaign_type} Column Definitions:
- Impr.: Impressions
- Clicks: Total clicks
- CTR: Click-through rate (%)
- Conv.: Conversions
- Impr.Share: Search impression share (%)
- Cost/Conv: Cost per conversion (€)
- Cost Micros: Cost in micros (€)
- Phone Calls: Phone calls (€)
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
            <p>This is a test email from your enhanced Google Ads reporting bot with daily comparison.</p>
            <p><strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>If you receive this, your email configuration is working! ✅</p>
            <p><em>Next reports will include both Luma and Keynote 4-week campaign comparison tables.</em></p>
        </body>
        </html>
        """
        
        msg = MIMEMultipart()
        msg['Subject'] = "gads campaign test - luma & keynote"
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