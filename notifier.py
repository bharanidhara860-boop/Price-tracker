import smtplib
from email.mime.text import MIMEText

import config


def send_email_alert(subject, body):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = config.SMTP_USERNAME
    msg["To"] = config.NOTIFY_EMAIL_TO
    with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as server:
        server.starttls()
        server.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
        server.sendmail(config.SMTP_USERNAME, [config.NOTIFY_EMAIL_TO], msg.as_string())


def send_telegram_alert(text):
    import requests

    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": config.TELEGRAM_CHAT_ID, "text": text}, timeout=10)


def notify_price_drop(title, old_price, new_price, url):
    text = (
        f"Price drop! \U0001F4C9\n\n"
        f"{title}\n"
        f"Old price: Rs.{old_price}\n"
        f"New price: Rs.{new_price}\n"
        f"Link: {url}"
    )
    channel = getattr(config, "NOTIFY_CHANNEL", "email")
    if channel == "email":
        send_email_alert("Price Drop Alert", text)
    elif channel == "telegram":
        send_telegram_alert(text)
    else:
        print(text)
