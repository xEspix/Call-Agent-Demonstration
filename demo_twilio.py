from twilio.rest import Client
from dotenv import load_dotenv
import os
load_dotenv()

TWILIO_ACCOUNT_SID=os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN=os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER=os.getenv("TWILIO_PHONE_NUMBER")
CUSTOMER_TEST_NUMBER=os.getenv("CUSTOMER_TEST_NUMBER")

account_sid=TWILIO_ACCOUNT_SID
auth_token=TWILIO_AUTH_TOKEN

client=Client(account_sid, auth_token)

call=client.calls.create(
    to=CUSTOMER_TEST_NUMBER,
    from_=TWILIO_PHONE_NUMBER,
    url="https://dwain-rocky-clockwise.ngrok-free.dev/voice"
)

print("Call SID:", call.sid)