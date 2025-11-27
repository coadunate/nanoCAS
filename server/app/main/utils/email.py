import smtplib
from email.message import EmailMessage
from email.mime.text import MIMEText
import logging
import ssl

logger = logging.getLogger("nanocas")

def send_email(subject, body, config):
    try:
        sender = config["sender"]
        password = config["password"]
        recipient = config["recipient"]
        smtp_server = config["smtpServer"]
        smtp_port = config["smtpPort"]

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = recipient
        msg.set_content(body)

        context = ssl.create_default_context()

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            print("Email server connected")
            server.starttls(context=context)
            server.login(sender, password)
            server.send_message(msg)
        logger.info(f"Email sent to {recipient}")
    
    except Exception as e:
        print(f"Failed to send email: {e}")
        logger.error(f"Failed to send email: {e}")