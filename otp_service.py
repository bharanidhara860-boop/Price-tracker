import random
import smtplib
import time
from email.mime.text import MIMEText

import config

_otp_store = {}
OTP_TTL_SECONDS = 300


def generate_otp(mobile_number):
    otp = f"{random.randint(100000, 999999)}"
    _otp_store[mobile_number] = (otp, time.time() + OTP_TTL_SECONDS)
    _deliver_otp(mobile_number, otp)
    return True


def _deliver_otp(mobile_number, otp):
    mode = getattr(config, "OTP_MODE", "console")

    if mode == "console":
        print(f"[OTP] For {mobile_number}: {otp}  (valid {OTP_TTL_SECONDS//60} min)")

    elif mode == "email":
        msg = MIMEText(f"Your login OTP is: {otp}")
        msg["Subject"] = "Your Price Tracker OTP"
        msg["From"] = config.SMTP_USERNAME
        msg["To"] = config.NOTIFY_EMAIL_TO
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as server:
            server.starttls()
            server.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
            server.sendmail(config.SMTP_USERNAME, [config.NOTIFY_EMAIL_TO], msg.as_string())

    elif mode == "sms":
        from twilio.rest import Client

        client = Client(config.TWILIO_SID, config.TWILIO_AUTH_TOKEN)
        client.messages.create(
            body=f"Your login OTP is: {otp}",
            from_=config.TWILIO_FROM_NUMBER,
            to=mobile_number,
        )
    else:
        raise ValueError(f"Unknown OTP_MODE: {mode}")


def verify_otp(mobile_number, submitted_otp):
    record = _otp_store.get(mobile_number)
    if not record:
        return False
    otp, expiry = record
    if time.time() > expiry:
        del _otp_store[mobile_number]
        return False
    if submitted_otp.strip() == otp:
        del _otp_store[mobile_number]
        return True
    return False
