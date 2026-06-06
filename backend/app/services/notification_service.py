import os
import logging
from typing import Optional

logger = logging.getLogger("app.services.notification")

class NotificationService:
    @staticmethod
    def _clean_phone(phone: str) -> str:
        if not phone:
            return ""
        # Remove spaces, dashes, parentheses, keeping digits and +
        cleaned = "".join(c for c in phone if c.isdigit() or c == "+")
        # If it doesn't start with '+', add country code
        if not cleaned.startswith("+"):
            # If it starts with '91' and is 12 digits, prepend '+'
            if len(cleaned) == 12 and cleaned.startswith("91"):
                cleaned = "+" + cleaned
            # If it is 10 digits, prepend '+91'
            elif len(cleaned) == 10:
                cleaned = "+91" + cleaned
            # Otherwise prepend '+'
            else:
                cleaned = "+" + cleaned
        return cleaned

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
        
        to_phone = NotificationService._clean_phone(to_phone)
        is_placeholder = not account_sid or not auth_token or "your_" in account_sid.lower() or "your_" in auth_token.lower()
        
        if use_mock or is_placeholder or not from_phone:
            logger.info(f"[Mock Twilio SMS] To: {to_phone} | Message: {message}")
            return "mock-sms-sid"

        try:
            from twilio.rest import Client
            client = Client(account_sid, auth_token)
            
            # Clean from_phone too
            from_phone_cleaned = NotificationService._clean_phone(from_phone)
            sent_message = client.messages.create(
                body=message,
                from_=from_phone_cleaned,
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
        
        to_phone = NotificationService._clean_phone(to_phone)
        is_placeholder = not account_sid or not auth_token or "your_" in account_sid.lower() or "your_" in auth_token.lower()
        
        if use_mock or is_placeholder:
            logger.info(f"[Mock Twilio WhatsApp] To: {to_phone} | Message: {message}")
            return "mock-whatsapp-sid"

        try:
            from twilio.rest import Client
            client = Client(account_sid, auth_token)
            
            # Ensure phone is prefixed with whatsapp:
            to_whatsapp = to_phone if to_phone.startswith("whatsapp:") else f"whatsapp:{to_phone}"
            
            # Safely clean from_whatsapp number while preserving whatsapp: prefix
            from_whatsapp_num = from_whatsapp.replace("whatsapp:", "").strip()
            from_whatsapp_cleaned = "whatsapp:" + NotificationService._clean_phone(from_whatsapp_num)
            
            sent_message = client.messages.create(
                body=message,
                from_=from_whatsapp_cleaned,
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

        to_phone = NotificationService._clean_phone(to_phone)
        is_placeholder = (aws_key and "your_" in aws_key.lower()) or (aws_secret and "your_" in aws_secret.lower())

        if use_mock or is_placeholder:
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
        Dispatches message dynamically via SMS, WhatsApp, or both depending on environment variables.
        """
        channel = os.getenv("NOTIFICATION_CHANNEL", "SMS").upper()
        sms_provider = os.getenv("SMS_PROVIDER", "").upper()
        
        if not sms_provider:
            # Auto-detect SMS provider based on credentials
            aws_key = os.getenv("AWS_ACCESS_KEY_ID")
            aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY")
            aws_active = aws_key and aws_secret and "your_" not in aws_key.lower() and "your_" not in aws_secret.lower()
            
            twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
            twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
            twilio_active = twilio_sid and twilio_token and "your_" not in twilio_sid.lower() and "your_" not in twilio_token.lower()
            
            if aws_active:
                sms_provider = "AWS_SNS"
            elif twilio_active:
                sms_provider = "TWILIO"
            else:
                sms_provider = "TWILIO"  # Default fallback
                
        result_sid = None
        
        # If channel is WHATSAPP, BOTH, or contains WHATSAPP
        if "WHATSAPP" in channel or channel == "BOTH":
            try:
                result_sid = cls.send_whatsapp_twilio(to_phone, message)
            except Exception as e:
                logger.error(f"Failed to send WhatsApp in send_outreach: {e}")
                
        # If channel is SMS, BOTH, or contains SMS
        if "SMS" in channel or channel == "BOTH":
            try:
                if sms_provider == "AWS_SNS":
                    result_sid = cls.send_sms_aws_sns(to_phone, message)
                else:
                    result_sid = cls.send_sms_twilio(to_phone, message)
            except Exception as e:
                logger.error(f"Failed to send SMS in send_outreach (provider={sms_provider}): {e}")
                
        return result_sid

