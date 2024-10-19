import os
from twilio.rest import Client
from twilio.base.exceptions import TwilioException

TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_MESSAGING_SERVICE_SID = os.environ.get("TWILIO_MESSAGING_SERVICE_SID")

def check_twilio_credentials():
    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_MESSAGING_SERVICE_SID]):
        raise ValueError("Twilio credentials are missing. Please make sure TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_MESSAGING_SERVICE_SID are set in the environment.")

try:
    check_twilio_credentials()
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
except (ValueError, TwilioException) as e:
    print(f"Error initializing Twilio client: {str(e)}")
    client = None

def schedule_twilio_message(scheduled_blast):
    if client is None:
        print("Twilio client is not initialized. Cannot schedule messages.")
        return None

    recipients = scheduled_blast.recipients.all()
    message_sids = []
    for recipient in recipients:
        personalized_message = scheduled_blast.message_template.format(**recipient.custom_fields)
        
        try:
            message = client.messages.create(
                messaging_service_sid=TWILIO_MESSAGING_SERVICE_SID,
                body=personalized_message,
                schedule_type="fixed",
                send_at=scheduled_blast.scheduled_time.isoformat(),
                to=recipient.phone_number
            )
            message_sids.append(message.sid)
        except TwilioException as e:
            print(f"Error scheduling Twilio message: {str(e)}")
            return None

    return ','.join(message_sids)

def cancel_twilio_message(message_sids):
    if client is None:
        print("Twilio client is not initialized. Cannot cancel messages.")
        return False

    success = True
    for message_sid in message_sids.split(','):
        try:
            message = client.messages(message_sid).update(status="canceled")
            if message.status != "canceled":
                success = False
        except TwilioException as e:
            print(f"Error canceling Twilio message: {str(e)}")
            success = False

    return success
