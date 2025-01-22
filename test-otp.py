import os
from twilio.rest import Client

# If using Account SID + Auth Token:
# TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
# TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
# client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# If using API Key + Secret:
TWILIO_API_KEY = os.environ.get('TWILIO_API_KEY', 'SK1c4a5375f81266d7864391697dfb8aed')
TWILIO_API_SECRET = os.environ.get('TWILIO_API_SECRET', 'VumDFvB4K9FbhoGbkWVlWwtjiKtTirMK')
client = Client(TWILIO_API_KEY, TWILIO_API_SECRET)

VERIFY_SERVICE_SID = "VAe93e0d2f14114c2063b578aaecd8ded4"

def send_otp(phone_number, channel='sms'):
    """
    phone_number must be in E.164 format (e.g. +1234567890)
    For WhatsApp: phone_number='whatsapp:+1234567890', channel='whatsapp'
    """
    verification = client.verify \
                         .services(VERIFY_SERVICE_SID) \
                         .verifications \
                         .create(to=phone_number, channel=channel)
    print("Status after sending OTP:", verification.status)

def check_otp(phone_number, code):
    """
    Check the OTP code that was sent to this phone_number
    """
    verification_check = client.verify \
                               .services(VERIFY_SERVICE_SID) \
                               .verification_checks \
                               .create(to=phone_number, code=code)
    print("Verification check status:", verification_check.status)

if __name__ == "__main__":
    # Example usage:
    # 1) Send OTP
    to_phone = "+15128277773"  # or "whatsapp:+15128277773"
    channel_type = "sms"       # or "whatsapp"
    send_otp(to_phone, channel_type)

    print("Please enter the OTP you received:")
    entered_code = input().strip()

    # 2) Check OTP
    check_otp(to_phone, entered_code)