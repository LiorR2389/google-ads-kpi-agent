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

    # Send email
    try:
        # Use SMTP_SSL for port 465, or SMTP with starttls() for port 587
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASSWORD"))
            server.send_message(msg)
            print("✅ Email sent successfully.")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        raise