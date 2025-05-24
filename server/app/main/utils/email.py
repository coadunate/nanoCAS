import smtplib
from email.mime.text import MIMEText
import logging

logger = logging.getLogger("nanocas")

def send_email(subject, body, config):
    try:
        sender = config["sender"]
        password = config["password"]
        recipient = config["recipient"]
        smtp_server = config["smtp_server"]
        smtp_port = config["smtp_port"]

        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = recipient

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            print("Email server connected")
            server.starttls()
            server.login(sender, password)
            server.sendmail(sender, recipient, msg.as_string())
        logger.info(f"Email sent to {recipient}")
    
    except Exception as e:
        print(f"Failed to send email: {e}")
        logger.error(f"Failed to send email: {e}")