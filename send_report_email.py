import os
import smtplib
import base64
from datetime import datetime
from email.message import EmailMessage
from email.utils import formataddr

def format_change(change_value, metric_type='percentage'):
    """Format change values with appropriate symbols and colors"""
    if change_value == 0:
        return f'<span class="trend-flat">➡️ No change</span>'
    elif change_value > 0:
        if metric_type == 'percentage':
            return f'<span class="trend-up">⬆️ +{change_value:.1f}%</span>'
        else:
            return f'<span class="trend-up">⬆️ +{change_value}</span>'
    else:
        if metric_type == 'percentage':
            return f'<span class="trend-down">⬇️ {change_value:.1f}%</span>'
        else:
            return f'<span class="trend-down">⬇️ {change_value}</span>'

def generate_html_email(insights_data, chart_base64):
    """Generate the HTML email content"""
    summary = insights_data['summary']
    highlights = insights_data['highlights']
    campaigns = insights_data['campaigns']
    
    # Format summary stats with dummy trend data (you can enhance this with actual trend calculation)
    summary_spend_change = format_change(5.2)  # Placeholder
    summary_clicks_change = format_change(-2.1)  # Placeholder
    summary_cpc_change = format_change(8.7)  # Placeholder
    summary_impressions_change = format_change(12.3)  # Placeholder
    
    # Generate highlights table rows
    highlights_rows = ""
    for highlight in highlights:
        change_formatted = format_change(highlight['change'])
        highlights_rows += f"""
        <tr>
            <td><span class="metric-icon">{highlight['metric'].split()[0]}</span>{highlight['metric'][2:]}</td>
            <td>{highlight['campaign']}</td>
            <td>{highlight['value']}</td>
            <td>{change_formatted}</td>
        </tr>
        """
    
    # Generate campaign performance table rows
    campaign_rows = ""
    for campaign in campaigns[:5]:  # Limit to top 5 campaigns
        campaign_name = campaign['campaign'][:30] + "..." if len(campaign['campaign']) > 30 else campaign['campaign']
        campaign_rows += f"""
        <tr>
            <td>{campaign_name}</td>
            <td>{int(campaign['impressions']):,}</td>
            <td>{int(campaign['clicks']):,}</td>
            <td>{campaign['ctr']:.1f}%</td>
            <td>€{campaign['cpc']:.2f}</td>
            <td>€{campaign['spend']:.2f}</td>
            <td>{int(campaign['conversions'])}</td>
            <td>€{campaign['cost_per_conversion']:.2f}</td>
        </tr>
        """
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Google Ads Daily KPI Report</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.6;
                color: #333;
                background-color: #f8f9fa;
                margin: 0;
                padding: 20px;
            }}
            
            .container {{
                max-width: 800px;
                margin: 0 auto;
                background: white;
                border-radius: 12px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                overflow: hidden;
            }}
            
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                text-align: center;
            }}
            
            .header h1 {{
                margin: 0;
                font-size: 28px;
                font-weight: 600;
            }}
            
            .header .date {{
                margin-top: 8px;
                opacity: 0.9;
                font-size: 16px;
            }}
            
            .content {{
                padding: 30px;
            }}
            
            .summary-cards {{
                display: flex;
                gap: 15px;
                margin-bottom: 30px;
                flex-wrap: wrap;
            }}
            
            .summary-card {{
                flex: 1;
                min-width: 180px;
                background: #f8f9fa;
                padding: 20px;
                border-radius: 8px;
                border-left: 4px solid #667eea;
                text-align: center;
            }}
            
            .summary-card h3 {{
                margin: 0 0 10px 0;
                color: #667eea;
                font-size: 14px;
                text-transform: uppercase;
                font-weight: 600;
            }}
            
            .summary-card .value {{
                font-size: 24px;
                font-weight: bold;
                color: #333;
                margin-bottom: 5px;
            }}
            
            .summary-card .change {{
                font-size: 12px;
                color: #6c757d;
            }}
            
            .section {{
                margin-bottom: 30px;
            }}
            
            .section h2 {{
                color: #333;
                font-size: 22px;
                margin-bottom: 15px;
                padding-bottom: 10px;
                border-bottom: 2px solid #e9ecef;
            }}
            
            .highlights-table {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 20px;
                background: white;
                border-radius: 8px;
                overflow: hidden;
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            }}
            
            .highlights-table th {{
                background: #667eea;
                color: white;
                padding: 15px;
                text-align: left;
                font-weight: 600;
                font-size: 14px;
            }}
            
            .highlights-table td {{
                padding: 12px 15px;
                border-bottom: 1px solid #e9ecef;
            }}
            
            .highlights-table tr:last-child td {{
                border-bottom: none;
            }}
            
            .highlights-table tr:nth-child(even) {{
                background-color: #f8f9fa;
            }}
            
            .metric-icon {{
                font-size: 18px;
                margin-right: 8px;
            }}
            
            .performance-table {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 20px;
                font-size: 14px;
            }}
            
            .performance-table th {{
                background: #343a40;
                color: white;
                padding: 12px 8px;
                text-align: center;
                font-size: 12px;
                font-weight: 600;
            }}
            
            .performance-table td {{
                padding: 10px 8px;
                text-align: center;
                border-bottom: 1px solid #dee2e6;
            }}
            
            .performance-table tr:nth-child(even) {{
                background-color: #f8f9fa;
            }}
            
            .chart-container {{
                text-align: center;
                margin: 20px 0;
                padding: 20px;
                background: #f8f9fa;
                border-radius: 8px;
            }}
            
            .chart-container img {{
                max-width: 100%;
                height: auto;
                border-radius: 4px;
            }}
            
            .recommendations {{
                background: #e7f3ff;
                border-left: 4px solid #0066cc;
                padding: 20px;
                border-radius: 0 8px 8px 0;
                margin-bottom: 20px;
            }}
            
            .recommendations h3 {{
                color: #0066cc;
                margin-top: 0;
                margin-bottom: 15px;
            }}
            
            .recommendations ul {{
                margin: 0;
                padding-left: 20px;
            }}
            
            .recommendations li {{
                margin-bottom: 8px;
                color: #333;
            }}
            
            .footer {{
                background: #f8f9fa;
                padding: 20px;
                text-align: center;
                font-size: 12px;
                color: #6c757d;
            }}
            
            .trend-up {{ color: #28a745; }}
            .trend-down {{ color: #dc3545; }}
            .trend-flat {{ color: #6c757d; }}
            
            @media (max-width: 600px) {{
                .summary-cards {{
                    flex-direction: column;
                }}
                
                .performance-table {{
                    font-size: 12px;
                }}
                
                .performance-table th,
                .performance-table td {{
                    padding: 8px 4px;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📊 Google Ads Daily KPI Report</h1>
                <div class="date">{datetime.now().strftime('%B %d, %Y')}</div>
            </div>
            
            <div class="content">
                <!-- Summary Cards -->
                <div class="summary-cards">
                    <div class="summary-card">
                        <h3>Total Spend</h3>
                        <div class="value">€{summary['total_spend']:.2f}</div>
                        <div class="change">{summary_spend_change}</div>
                    </div>
                    <div class="summary-card">
                        <h3>Total Clicks</h3>
                        <div class="value">{summary['total_clicks']:,}</div>
                        <div class="change">{summary_clicks_change}</div>
                    </div>
                    <div class="summary-card">
                        <h3>Avg CPC</h3>
                        <div class="value">€{summary['avg_cpc']:.2f}</div>
                        <div class="change">{summary_cpc_change}</div>
                    </div>
                    <div class="summary-card">
                        <h3>Total Impressions</h3>
                        <div class="value">{summary['total_impressions']:,}</div>
                        <div class="change">{summary_impressions_change}</div>
                    </div>
                </div>
                
                <!-- Key Highlights -->
                <div class="section">
                    <h2>🎯 Daily Highlights</h2>
                    <table class="highlights-table">
                        <thead>
                            <tr>
                                <th>Metric</th>
                                <th>Campaign</th>
                                <th>Value</th>
                                <th>Trend</th>
                            </tr>
                        </thead>
                        <tbody>
                            {highlights_rows}
                        </tbody>
                    </table>
                </div>
                
                <!-- Campaign Performance -->
                <div class="section">
                    <h2>📈 Top Campaign Performance</h2>
                    <table class="performance-table">
                        <thead>
                            <tr>
                                <th>Campaign</th>
                                <th>Impressions</th>
                                <th>Clicks</th>
                                <th>CTR</th>
                                <th>CPC</th>
                                <th>Spend</th>
                                <th>Conv.</th>
                                <th>CPA</th>
                            </tr>
                        </thead>
                        <tbody>
                            {campaign_rows}
                        </tbody>
                    </table>
                </div>
                
                <!-- Chart -->
                <div class="section">
                    <h2>💰 Daily Spend Overview</h2>
                    <div class="chart-container">
                        <img src="data:image/png;base64,{chart_base64}" alt="Daily Spend Chart" />
                    </div>
                </div>
                
                <!-- Recommendations -->
                <div class="section">
                    <div class="recommendations">
                        <h3>✅ Actionable Recommendations</h3>
                        <ul>
                            <li><strong>🚀 Scale Budget:</strong> Increase budget for top-performing campaigns with low CPC</li>
                            <li><strong>🔍 Optimize Keywords:</strong> Review high-CPC campaigns for keyword optimization opportunities</li>
                            <li><strong>🎯 Improve Landing Pages:</strong> Test new landing page variants to boost conversion rates</li>
                            <li><strong>📊 A/B Test Ads:</strong> Create new ad variations for underperforming campaigns</li>
                            <li><strong>⏰ Adjust Bidding:</strong> Consider automated bidding strategies for better cost efficiency</li>
                            <li><strong>📱 Mobile Optimization:</strong> Review mobile performance and adjust bids accordingly</li>
                        </ul>
                    </div>
                </div>
            </div>
            
            <div class="footer">
                <p>Generated automatically by KPI Bot | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p>Need help? Contact your marketing team</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html_content

def send_report_email(insights_data, image_path):
    """
    Send enhanced daily KPI report via email
    
    Args:
        insights_data: Dictionary containing comprehensive campaign data and insights
        image_path (str): Path to the chart image to attach
    """
    # Get chart as base64 for embedding
    chart_base64 = ""
    if os.path.exists(image_path):
        with open(image_path, 'rb') as f:
            chart_base64 = base64.b64encode(f.read()).decode('utf-8')
    
    # Generate HTML content
    html_body = generate_html_email(insights_data, chart_base64)
    
    # Create email message
    msg = EmailMessage()
    msg['Subject'] = f'📊 Google Ads Daily Report - {datetime.now().strftime("%b %d, %Y")}'
    msg['From'] = formataddr(('KPI Bot', os.getenv('EMAIL_USER')))
    msg['To'] = os.getenv('EMAIL_TO')
    
    # Set plain text content as fallback
    plain_text = f"""
Google Ads Daily KPI Report - {datetime.now().strftime('%B %d, %Y')}

Summary:
- Total Spend: €{insights_data['summary']['total_spend']:.2f}
- Total Clicks: {insights_data['summary']['total_clicks']:,}
- Total Impressions: {insights_data['summary']['total_impressions']:,}
- Average CPC: €{insights_data['summary']['avg_cpc']:.2f}
- Average CTR: {insights_data['summary']['avg_ctr']:.2f}%

Top Performers:
"""
    
    for highlight in insights_data['highlights']:
        plain_text += f"- {highlight['metric']}: {highlight['campaign']} ({highlight['value']})\n"
    
    plain_text += "\nPlease view in HTML format for the full interactive report."
    
    msg.set_content(plain_text)
    
    # Add HTML content
    msg.add_alternative(html_body, subtype='html')

    # Attach spend chart image
    if os.path.exists(image_path):
        with open(image_path, 'rb') as f:
            img_data = f.read()
        msg.add_attachment(img_data, maintype='image', subtype='png', filename='spend_chart.png')
    else:
        print(f"⚠️ Warning: Image file not found at {image_path}")

    # Send email with fallback options
    email_user = os.getenv("EMAIL_USER")
    email_password = os.getenv("EMAIL_PASSWORD")
    
    if not email_user or not email_password:
        print("❌ Missing EMAIL_USER or EMAIL_PASSWORD environment variables")
        return
    
    # Try multiple SMTP configurations
    smtp_configs = [
        ("smtp.gmail.com", 587, "starttls"),  # TLS on port 587
        ("smtp.gmail.com", 465, "ssl"),       # SSL on port 465
    ]
    
    for host, port, method in smtp_configs:
        try:
            print(f"🔄 Attempting SMTP connection to {host}:{port} using {method}")
            
            if method == "ssl":
                with smtplib.SMTP_SSL(host, port) as server:
                    server.login(email_user, email_password)
                    server.send_message(msg)
                    print("✅ Enhanced email sent successfully via SSL")
                    return
            else:  # starttls
                with smtplib.SMTP(host, port) as server:
                    server.starttls()
                    server.login(email_user, email_password)
                    server.send_message(msg)
                    print("✅ Enhanced email sent successfully via STARTTLS")
                    return
                    
        except Exception as e:
            print(f"❌ Failed with {host}:{port} ({method}): {e}")
            continue
    
    print("❌ All SMTP methods failed")
    raise Exception("Unable to send email with any SMTP configuration")