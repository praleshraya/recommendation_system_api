from smtplib import SMTP
from pyotp import TOTP
import os

def send_email(to_email: str, subject: str, body: str):
    from_email = os.getenv("EMAIL_USER")
    from_password = os.getenv("EMAIL_PASSWORD")

    with SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(from_email, from_password)
        message = f"Subject: {subject}\n\n{body}"
        server.sendmail(from_email, to_email, message)
