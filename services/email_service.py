import smtplib
import os
from email.mime.text import MIMEText

def send_email(to, link):

    msg = MIMEText(f"Reset password:\n{link}")
    msg["Subject"] = "Reset Password"
    msg["From"] = os.getenv("EMAIL_USER")
    msg["To"] = to

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASS"))
        server.send_message(msg)
