import smtplib
from email.message import EmailMessage
import os
import smtplib

def send_report_email(to, subject, body, attachment_path):
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = os.getenv("EMAIL_FROM")
    msg['To'] = to
    msg.set_content(body)

    with open(attachment_path, 'rb') as f:
        msg.add_attachment(f.read(), maintype='application', subtype='pdf', filename='weekly_report.pdf')

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(os.getenv("EMAIL_FROM"), os.getenv("EMAIL_PASSWORD"))
        smtp.send_message(msg)

