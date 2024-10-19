import os
from twilio.rest import Client
from twilio.base.exceptions import TwilioException, TwilioRestException
import re
import logging

TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_MESSAGING_SERVICE_SID = os.environ.get("TWILIO_MESSAGING_SERVICE_SID")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_twilio_credentials():
    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_MESSAGING_SERVICE_SID]):
        raise ValueError("Twilio credentials are missing. Please make sure TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_MESSAGING_SERVICE_SID are set in the environment.")

def is_valid_phone_number(phone_number):
    pattern = r'^\+[1-9]\d{1,14}$'
    return re.match(pattern, phone_number) is not None

try:
    check_twilio_credentials()
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
except (ValueError, TwilioException) as e:
    logger.error(f"Error initializing Twilio client: {str(e)}")
    client = None

def schedule_twilio_message(scheduled_blast):
    if client is None:
        logger.error("Twilio client is not initialized. Cannot schedule messages.")
        return None

    recipients = scheduled_blast.recipients.all()
    message_sids = []
    for recipient in recipients:
        personalized_message = scheduled_blast.message_template.format(**recipient.custom_fields)
        
        if not is_valid_phone_number(recipient.phone_number):
            logger.warning(f"Invalid phone number format: {recipient.phone_number}")
            continue

        try:
            message = client.messages.create(
                messaging_service_sid=TWILIO_MESSAGING_SERVICE_SID,
                body=personalized_message,
                schedule_type="fixed",
                send_at=scheduled_blast.scheduled_time.isoformat(),
                to=recipient.phone_number
            )
            message_sids.append(message.sid)
            logger.info(f"Scheduled message for {recipient.phone_number}: SID {message.sid}")
        except TwilioRestException as e:
            logger.error(f"Twilio API error for {recipient.phone_number}: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error scheduling message for {recipient.phone_number}: {str(e)}")

    return ','.join(message_sids) if message_sids else None

def cancel_twilio_message(message_sids):
    if client is None:
        logger.error("Twilio client is not initialized. Cannot cancel messages.")
        return False

    success = True
    for message_sid in message_sids.split(','):
        try:
            message = client.messages(message_sid).update(status="canceled")
            if message.status != "canceled":
                logger.warning(f"Failed to cancel message {message_sid}: status is {message.status}")
                success = False
            else:
                logger.info(f"Successfully canceled message {message_sid}")
        except TwilioRestException as e:
            logger.error(f"Twilio API error canceling message {message_sid}: {str(e)}")
            success = False
        except Exception as e:
            logger.error(f"Unexpected error canceling message {message_sid}: {str(e)}")
            success = False

    return success
