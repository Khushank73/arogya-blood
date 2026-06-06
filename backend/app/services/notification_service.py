import os
import logging
from typing import Optional

logger = logging.getLogger("app.services.notification")

class NotificationService:
    @staticmethod
    def send_sms_twilio(to_phone: str, message: str) -> Optional[str]:
        """
        Sends an SMS message using Twilio SMS API.
        Automatically falls back to a mock representation if env vars are missing or USE_LOCAL_MOCKS is enabled.
        """
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        from_phone = os.getenv("TWILIO_PHONE_NUMBER")
        use_mock = os.getenv("USE_LOCAL_MOCKS", "TRUE").upper() == "TRUE"
        
        if use_mock or not account_sid or not auth_token or not from_phone:
            logger.info(f"[Mock Twilio SMS] To: {to_phone} | Message: {message}")
            return "mock-sms-sid"

        try:
            from twilio.rest import Client
            client = Client(account_sid, auth_token)
            sent_message = client.messages.create(
                body=message,
                from_=from_phone,
                to=to_phone
            )
            logger.info(f"Twilio SMS sent to {to_phone}. Message SID: {sent_message.sid}")
            return sent_message.sid
        except Exception as e:
            logger.error(f"Failed to send Twilio SMS to {to_phone}: {str(e)}")
            raise e

    @staticmethod
    def send_whatsapp_twilio(to_phone: str, message: str) -> Optional[str]:
        """
        Sends a WhatsApp message using Twilio WhatsApp API.
        Automatically falls back to a mock representation if env vars are missing or USE_LOCAL_MOCKS is enabled.
        """
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        from_whatsapp = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")
        use_mock = os.getenv("USE_LOCAL_MOCKS", "TRUE").upper() == "TRUE"
        
        if use_mock or not account_sid or not auth_token:
            logger.info(f"[Mock Twilio WhatsApp] To: {to_phone} | Message: {message}")
            return "mock-whatsapp-sid"

        try:
            from twilio.rest import Client
            client = Client(account_sid, auth_token)
            
            # Ensure phone is prefixed with whatsapp:
            to_whatsapp = to_phone if to_phone.startswith("whatsapp:") else f"whatsapp:{to_phone}"
            
            sent_message = client.messages.create(
                body=message,
                from_=from_whatsapp,
                to=to_whatsapp
            )
            logger.info(f"Twilio WhatsApp sent to {to_phone}. Message SID: {sent_message.sid}")
            return sent_message.sid
        except Exception as e:
            logger.error(f"Failed to send Twilio WhatsApp to {to_phone}: {str(e)}")
            raise e

    @staticmethod
    def send_sms_aws_sns(to_phone: str, message: str) -> Optional[str]:
        """
        Sends an SMS message using AWS SNS.
        Automatically falls back to a mock representation if USE_LOCAL_MOCKS is enabled.
        Supports AWS IAM Roles (default credentials chain) if keys are not explicitly set in the environment.
        """
        aws_key = os.getenv("AWS_ACCESS_KEY_ID")
        aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY")
        use_mock = os.getenv("USE_LOCAL_MOCKS", "TRUE").upper() == "TRUE"

        if use_mock:
            logger.info(f"[Mock AWS SNS SMS] To: {to_phone} | Message: {message}")
            return "mock-aws-sns-sid"

        try:
            import boto3
            if aws_key and aws_secret:
                sns_client = boto3.client(
                    "sns",
                    aws_access_key_id=aws_key,
                    aws_secret_access_key=aws_secret,
                    region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1")
                )
            else:
                # Fallback to default credentials chain (e.g. ECS Task Role, Instance Profile)
                sns_client = boto3.client(
                    "sns",
                    region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1")
                )
            response = sns_client.publish(
                PhoneNumber=to_phone,
                Message=message
            )
            message_id = response.get("MessageId")
            logger.info(f"AWS SNS SMS sent to {to_phone}. Message ID: {message_id}")
            return message_id
        except Exception as e:
            logger.error(f"Failed to send AWS SNS SMS to {to_phone}: {str(e)}")
            raise e

    @classmethod
    def send_outreach(cls, to_phone: str, message: str) -> Optional[str]:
        """
        Dispatches message dynamically via SMS or WhatsApp depending on environment variables.
        """
        channel = os.getenv("NOTIFICATION_CHANNEL", "SMS").upper()
        if channel == "WHATSAPP":
            return cls.send_whatsapp_twilio(to_phone, message)
        else:
            return cls.send_sms_aws_sns(to_phone, message)

