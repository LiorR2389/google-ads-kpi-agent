import os
import smtplib
import base64
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

def generate_trend_card(title, current, previous, trend, icon="📊"):
    """Generate HTML for a trend comparison card"""
    # Determine trend color
    if "📈" in trend:
        trend_color = "#28a745"  # Green for positive
        bg_color = "#d4f3d0"
    elif "📉" in trend:
        trend_color = "#dc3545"  # Red for negative
        bg_color = "#f8d7da"
    else:
        trend_color = "#6c757d"  # Gray for no change
        bg_color = "#f8f9fa"
    
    return f"""
    <div style="flex: 1; min-width: 180px; background: {bg_color}; padding: 20px; border-radius: 8px; text-align: center; border-left: 4px solid {trend_color}; margin: 5px;">
        <div style="font-size: 12px; color: {trend_color}; font-weight: bold; margin-bottom: 5px; text-transform: uppercase;">{title}</div>
        <div style="font-size: 24px; font-weight: bold; color: #333; margin-bottom: 5px;">{current}</div>
        <div style="font-size: 12px; color: {trend_color}; font-weight: bold;">{trend}</div>
        <div style="font-size: 10px; color: #666; margin-top: 3px;">vs. last week: {previous}</div>
    </div>
    """

def generate_simple_html_email_with_trends(insights_data, chart_base64):
    """Generate a clean, simple HTML email with trend comparisons"""
    summary = insights_data['summary']
    trends = insights_data.get('summary_trends', {})
    highlights = insights_data['highlights']
    campaigns = insights_data['campaigns'][:5]  # Top 5 campaigns
    comparison_available = insights_data.get('comparison_available', False)
    
    # Generate summary cards with trends
    summary_cards = ""
    
    # Total Spend
    spend_trend = trends.get('total_spend', {})
    summary_cards += generate_trend_card(
        "Total Spend",
        f"€{summary['total_spend']:.2f}",
        f"€{spend_trend.get('previous', 0):.2f}",
        spend_trend.get('trend', '➡️ No data'),
        "💰"
    )
    
    # Total Clicks
    clicks_trend = trends.get('total_clicks', {})
    summary_cards += generate_trend_card(
        "Total Clicks",
        f"{summary['total_clicks']:,}",
        f"{clicks_trend.get('previous', 0):,}",
        clicks_trend.get('trend', '➡️ No data'),
        "👆"
    )
    
    # Average CPC
    cpc_trend = trends.get('avg_cpc', {})
    summary_cards += generate_trend_card(
        "Avg CPC",
        f"€{summary['avg_cpc']:.2f}",
        f"€{cpc_trend.get('previous', 0):.2f}",
        cpc_trend.get('trend', '➡️ No data'),
        "💲"
    )
    
    # Impressions
    imp_trend = trends.get('total_impressions', {})
    summary_cards += generate_trend_card(
        "Impressions",
        f"{summary['total_impressions']:,}",
        f"{imp_trend.get('previous', 0):,}",
        imp_trend.get('trend', '➡️ No data'),
        "👁️"
    )
    
    # Generate highlights rows with trends
    highlights_html = ""
    for highlight in highlights:
        trend_cell = f"<td style='padding: 10px; text-align: center; font-weight: bold; color: #28a745;'>{highlight['trend']}</td>" if highlight['trend'] else "<td style='padding: 10px; text-align: center; color: #999;'>-</td>"
        highlights_html += f"""
        <tr style="border-bottom: 1px solid #eee;">
            <td style="padding: 10px; font-weight: bold;">{highlight['metric']}</td>
            <td style="padding: 10px;">{highlight['campaign']}</td>
            <td style="padding: 10px; color: #667eea; font-weight: bold;">{highlight['value']}</td>
            {trend_cell}
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
    
    # Comparison note
    comparison_note = ""
    if comparison_available:
        comparison_note = f"""
        <div style="background: #e7f3ff; border-left: 4px solid #0066cc; padding: 15px; margin: 20px 0; border-radius: 0 6px 6px 0;">
            <h4 style="color: #0066cc; margin: 0 0 10px 0; font-size: 14px;">📊 Week-over-Week Comparison</h4>
            <p style="margin: 0; color: #0066cc; font-size: 12px;">
                Trends shown compare today's data with the same day last week ({(datetime.now() - timedelta(days=7)).strftime('%B %d, %Y')}).
                Green arrows (📈) indicate improvement, red arrows (📉) indicate decline.
            </p>
        </div>
        """
    else:
        comparison_note = f"""
        <div style="background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; border-radius: 0 6px 6px 0;">
            <p style="margin: 0; color: #856404; font-size: 12px;">
                ⚠️ No comparison data available for last week. Trends will appear once we have historical data.
            </p>
        </div>
        """
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 20px; font-family: Arial, sans-serif; background-color: #f5f5f5;">
        <div style="max-width: 900px; margin: 0 auto; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center;">
                <h1 style="margin: 0; font-size: 24px;">📊 Google Ads Daily Report</h1>
                <p style="margin: 10px 0 0 0; opacity: 0.9;">{datetime.now().strftime('%B %d, %Y')}</p>
            </div>
            
            <!-- Summary with Trends -->
            <div style="padding: 30px;">
                <h2 style="color: #333; margin-bottom: 20px; display: flex; align-items: center; gap: 10px;">
                    📈 <span>Performance Overview</span>
                </h2>
                
                {comparison_note}
                
                <div style="display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 30px;">
                    {summary_cards}
                </div>
                
                <!-- Highlights Table with Trends -->
                <h2 style="color: #333; font-size: 20px; margin-bottom: 15px; display: flex; align-items: center; gap: 10px;">
                    🎯 <span>Performance Highlights</span>
                </h2>
                <div style="background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1); margin-bottom: 30px;">
                    <table style="width: 100%; border-collapse: collapse;">
                        <thead>
                            <tr style="background: linear-gradient(135deg, #343a40, #495057); color: white;">
                                <th style="padding: 15px; text-align: left; font-weight: 600; font-size: 13px;">Metric</th>
                                <th style="padding: 15px; text-align: left; font-weight: 600; font-size: 13px;">Campaign</th>
                                <th style="padding: 15px; text-align: left; font-weight: 600; font-size: 13px;">Value</th>
                                <th style="padding: 15px; text-align: center; font-weight: 600; font-size: 13px;">Trend</th>
                            </tr>
                        </thead>
                        <tbody>
                            {highlights_html}
                        </tbody>
                    </table>
                </div>
                
                <!-- Top Campaigns -->
                <h2 style="color: #333; font-size: 20px; margin-bottom: 15px; display: flex; align-items: center; gap: 10px;">
                    🏆 <span>Top Campaign Performance</span>
                </h2>
                <div style="background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1); margin-bottom: 30px;">
                    <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                        <thead>
                            <tr style="background: linear-gradient(135deg, #343a40, #495057); color: white;">
                                <th style="padding: 12px; text-align: left; font-weight: 600; font-size: 13px;">Campaign</th>
                                <th style="padding: 12px; text-align: center; font-weight: 600; font-size: 13px;">Impressions</th>
                                <th style="padding: 12px; text-align: center; font-weight: 600; font-size: 13px;">Clicks</th>
                                <th style="padding: 12px; text-align: center; font-weight: 600; font-size: 13px;">CTR</th>
                                <th style="padding: 12px; text-align: center; font-weight: 600; font-size: 13px;">Est. Spend</th>
                            </tr>
                        </thead>
                        <tbody>
                            {campaigns_html}
                        </tbody>
                    </table>
                </div>
                
                <!-- Chart -->
                <h2 style="color: #333; font-size: 20px; margin-bottom: 15px; display: flex; align-items: center; gap: 10px;">
                    💰 <span>Spend Overview</span>
                </h2>
                <div style="text-align: center; padding: 20px; background: #f8f9fa; border-radius: 8px; margin-bottom: 30px;">
                    <img src="data:image/png;base64,{chart_base64}" style="max-width: 100%; height: auto; border-radius: 6px;" alt="Spend Chart" />
                </div>
                
                <!-- Key Insights with Trends -->
                <div style="background: #e7f3ff; border-left: 4px solid #0066cc; padding: 20px; margin: 20px 0; border-radius: 0 8px 8px 0;">
                    <h3 style="color: #0066cc; margin-top: 0; margin-bottom: 15px; display: flex; align-items: center; gap: 8px;">
                        💡 <span>Key Insights & Trends</span>
                    </h3>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 15px;">
                        <div style="text-align: center;">
                            <div style="font-size: 14px; color: #666; margin-bottom: 5px;">Average CTR</div>
                            <div style="font-size: 18px; font-weight: bold; color: #0066cc;">{summary['avg_ctr']:.2f}%</div>
                            <div style="font-size: 11px; color: #0066cc;">{trends.get('avg_ctr', {}).get('trend', '➡️ No data')}</div>
                        </div>
                        <div style="text-align: center;">
                            <div style="font-size: 14px; color: #666; margin-bottom: 5px;">Total Conversions</div>
                            <div style="font-size: 18px; font-weight: bold; color: #0066cc;">{summary['total_conversions']}</div>
                            <div style="font-size: 11px; color: #0066cc;">{trends.get('total_conversions', {}).get('trend', '➡️ No data')}</div>
                        </div>
                        <div style="text-align: center;">
                            <div style="font-size: 14px; color: #666; margin-bottom: 5px;">Avg Conv. Rate</div>
                            <div style="font-size: 18px; font-weight: bold; color: #0066cc;">{summary['avg_conversion_rate']:.1f}%</div>
                            <div style="font-size: 11px; color: #0066cc;">{trends.get('avg_conversion_rate', {}).get('trend', '➡️ No data')}</div>
                        </div>
                    </div>
                    <div style="border-top: 1px solid #cce7ff; padding-top: 15px; margin-top: 15px;">
                        <p style="margin: 0; color: #0066cc; font-weight: 500;">
                            💡 Your Demand Gen campaign continues to show strong performance with excellent CTR!
                            {"Monitor spending trends to optimize ROI." if comparison_available else "Historical trend data will be available after a week of data collection."}
                        </p>
                    </div>
                </div>
                
                <!-- Recommendations -->
                <div style="background: #f8f9fa; border-left: 4px solid #28a745; padding: 20px; margin: 20px 0; border-radius: 0 8px 8px 0;">
                    <h3 style="color: #28a745; margin-top: 0; margin-bottom: 15px;">✅ Smart Recommendations</h3>
                    <ul style="margin: 0; padding-left: 20px; color: #333;">
                        <li style="margin-bottom: 8px;">🚀 <strong>Demand Gen campaign</strong> shows excellent CTR - consider increasing budget {f"(trending {trends.get('total_clicks', {}).get('trend', '')})" if comparison_available else ""}</li>
                        <li style="margin-bottom: 8px;">🔍 <strong>Performance Max</strong> has good conversion potential - optimize targeting</li>
                        <li style="margin-bottom: 8px;">📊 <strong>Search campaigns</strong> may need keyword review for better efficiency</li>
                        {"<li style='margin-bottom: 8px;'>📈 <strong>Overall trends</strong> looking positive - maintain current strategy</li>" if comparison_available and any("📈" in trend.get('trend', '') for trend in trends.values()) else ""}
                    </ul>
                </div>
            </div>
            
            <!-- Footer -->
            <div style="background: #f8f9fa; padding: 20px; text-align: center; font-size: 12px; color: #666; border-top: 1px solid #e9ecef;">
                <p style="margin: 0;">🤖 Automated Google Ads Reporting with Trend Analysis • Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p style="margin: 5px 0 0 0;">* Spend values are estimates based on industry benchmarks • Trends compare week-over-week performance</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html

def send_report_email(insights_data, image_path):
    """Send report with trend comparisons and multiple fallback methods"""
    
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
        
        # Create HTML email with trends
        html_content = generate_simple_html_email_with_trends(insights_data, chart_base64)
        
        # Create plain text version with trends
        summary = insights_data['summary']
        trends = insights_data.get('summary_trends', {})
        comparison_available = insights_data.get('comparison_available', False)
        
        plain_text = f"""
Google Ads Daily Report with Trends - {datetime.now().strftime('%B %d, %Y')}

PERFORMANCE OVERVIEW {"(vs. last week)" if comparison_available else "(no comparison data yet)"}:
• Total Spend: €{summary['total_spend']:.2f} {trends.get('total_spend', {}).get('trend', '')}
• Total Clicks: {summary['total_clicks']:,} {trends.get('total_clicks', {}).get('trend', '')}
• Total Impressions: {summary['total_impressions']:,} {trends.get('total_impressions', {}).get('trend', '')}
• Average CPC: €{summary['avg_cpc']:.2f} {trends.get('avg_cpc', {}).get('trend', '')}
• Average CTR: {summary['avg_ctr']:.2f}% {trends.get('avg_ctr', {}).get('trend', '')}

TOP PERFORMERS:
"""
        for highlight in insights_data['highlights']:
            trend_text = f" {highlight['trend']}" if highlight['trend'] else ""
            plain_text += f"• {highlight['metric']}: {highlight['campaign']} ({highlight['value']}){trend_text}\n"
        
        if comparison_available:
            plain_text += f"\nTrends compare with {(datetime.now() - timedelta(days=7)).strftime('%B %d, %Y')}"
        else:
            plain_text += "\nHistorical trend data will be available after a week of data collection."
            
        plain_text += "\n\n* Spend values are estimates based on industry benchmarks"
        plain_text += "\nPlease view HTML version for full trend analysis and charts."
        
        # Create email message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"📊 Google Ads Report with Trends - {datetime.now().strftime('%b %d, %Y')}"
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
                
                print("✅ Email with trends sent successfully!")
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
            <p>This is a test email from your enhanced Google Ads reporting bot with trend analysis.</p>
            <p><strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>If you receive this, your email configuration is working! ✅</p>
            <p><em>Next report will include week-over-week trend comparisons.</em></p>
        </body>
        </html>
        """
        
        msg = MIMEMultipart()
        msg['Subject'] = "🧪 Google Ads Bot Test - Enhanced with Trends"
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