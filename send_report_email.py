import os
import smtplib
from email.message import EmailMessage
from email.utils import formataddr

def send_report_email(html_body, image_path):
    msg = EmailMessage()
    msg['Subject'] = '📊 Google Ads Daily KPI Report'
    msg['From'] = formataddr(('KPI Bot', os.getenv('EMAIL_USER')))
    msg['To'] = os.getenv('EMAIL_TO')
    msg.set_content("Your daily KPI report is attached.")
    msg.add_alternative(html_body, subtype='html')

    # Attach spend_chart.png
    if os.path.exists(image_path):
        with open(image_path, 'rb') as f:
            img_data = f.read()
        msg.add_attachment(img_data, maintype='image', subtype='png', filename='spend_chart.png')

    with smtplib.SMTP('smtp.gmail.com', 465) as server:
        server.starttls()
        server.login(os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASSWORD"))
        server.send_message(msg)
        print("✅ Email sent successfully.")
