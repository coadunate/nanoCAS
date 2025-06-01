import os
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger('nanocas')

def send_sms(body):
    """Send an SMS alert using Twilio."""
    account_sid = os.getenv('TWILIO_ACCOUNT_SID')
    auth_token = os.getenv('TWILIO_AUTH_TOKEN')
    twilio_phone = os.getenv('TWILIO_PHONE_NUMBER')
    recipient_phone = os.getenv('ALERT_RECIPIENT_PHONE')

    # Check if all required Twilio credentials are provided
    if not all([account_sid, auth_token, twilio_phone, recipient_phone]):
        logger.error("Twilio configuration missing in .env file. SMS not sent.")
        return

    try:
        client = Client(account_sid, auth_token)
        message = client.messages.create(
            body=body,
            from_=twilio_phone,
            to=recipient_phone
        )
        logger.info(f"SMS sent successfully: {message.sid}")
    except TwilioRestException as e:
        logger.error(f"Failed to send SMS: {e}")