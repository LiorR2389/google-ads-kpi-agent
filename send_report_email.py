import os
import smtplib
from email.message import EmailMessage
from email.utils import formataddr

def send_report_email(html_body, image_path):
    """
    Send daily KPI report via email
    
    Args:
        html_body (str): HTML content for the email body
        image_path (str): Path to the chart image to attach
    """
    # Create email message
    msg = EmailMessage()
    msg['Subject'] = '📊 Google Ads Daily KPI Report'
    msg['From'] = formataddr(('KPI Bot', os.getenv('EMAIL_USER')))
    msg['To'] = os.getenv('EMAIL_TO')
    
    # Set plain text content as fallback
    msg.set_content("Your daily KPI report is attached. Please view in HTML format for best experience.")
    
    # Add HTML content
    msg.add_alternative(html_body, subtype='html')

    # Attach spend chart image if it exists
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
                    print("✅ Email sent successfully via SSL")
                    return
            else:  # starttls
                with smtplib.SMTP(host, port) as server:
                    server.starttls()
                    server.login(email_user, email_password)
                    server.send_message(msg)
                    print("✅ Email sent successfully via STARTTLS")
                    return
                    
        except Exception as e:
            print(f"❌ Failed with {host}:{port} ({method}): {e}")
            continue
    
    print("❌ All SMTP methods failed")
    raise Exception("Unable to send email with any SMTP configuration")