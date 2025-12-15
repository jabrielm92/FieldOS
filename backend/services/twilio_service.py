"""
Twilio SMS Service - Handles all SMS operations
"""
import os
import logging
from typing import Optional
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

logger = logging.getLogger(__name__)


class TwilioService:
    def __init__(self):
        self.account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
        self.auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
        self.default_messaging_service_sid = os.environ.get('TWILIO_MESSAGING_SERVICE_SID')
        self.client = None
        
        if self.account_sid and self.auth_token:
            try:
                self.client = Client(self.account_sid, self.auth_token)
                logger.info("Twilio client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Twilio client: {e}")
    
    def is_configured(self) -> bool:
        """Check if Twilio is properly configured"""
        return self.client is not None
    
    async def send_sms(
        self,
        to_phone: str,
        body: str,
        from_phone: Optional[str] = None,
        messaging_service_sid: Optional[str] = None
    ) -> dict:
        """
        Send SMS via Twilio
        
        Args:
            to_phone: Recipient phone number
            body: Message content
            from_phone: Sender phone number (optional if using messaging service)
            messaging_service_sid: Twilio Messaging Service SID (optional)
        
        Returns:
            dict with success status, provider_message_id, and error if any
        """
        if not self.is_configured():
            logger.warning("Twilio not configured - SMS not sent")
            return {
                "success": False,
                "error": "Twilio not configured",
                "provider_message_id": None
            }
        
        try:
            # Clean phone number
            to_phone = self._format_phone(to_phone)
            
            message_params = {
                "body": body,
                "to": to_phone
            }
            
            # Use messaging service if provided or default, otherwise use from number
            service_sid = messaging_service_sid or self.default_messaging_service_sid
            if service_sid:
                message_params["messaging_service_sid"] = service_sid
                logger.info(f"Sending SMS via Messaging Service: {service_sid}")
            elif from_phone:
                message_params["from_"] = self._format_phone(from_phone)
                logger.info(f"Sending SMS from: {from_phone}")
            else:
                logger.error("No from_phone or messaging_service_sid provided")
                return {
                    "success": False,
                    "provider_message_id": None,
                    "error": "No sender configured"
                }
            
            message = self.client.messages.create(**message_params)
            
            logger.info(f"SMS sent successfully: {message.sid} to {to_phone}")
            return {
                "success": True,
                "provider_message_id": message.sid,
                "error": None
            }
            
        except TwilioRestException as e:
            logger.error(f"Twilio error sending SMS: {e.msg}")
            return {
                "success": False,
                "provider_message_id": None,
                "error": str(e.msg)
            }
        except Exception as e:
            logger.error(f"Error sending SMS: {e}")
            return {
                "success": False,
                "provider_message_id": None,
                "error": str(e)
            }
    
    def _format_phone(self, phone: str) -> str:
        """Format phone number to E.164 format"""
        if not phone:
            return phone
        # Remove any non-digit characters except +
        cleaned = ''.join(c for c in phone if c.isdigit() or c == '+')
        
        # Add + if not present and starts with country code
        if not cleaned.startswith('+'):
            # Assume US number if 10 digits
            if len(cleaned) == 10:
                cleaned = '+1' + cleaned
            elif len(cleaned) == 11 and cleaned.startswith('1'):
                cleaned = '+' + cleaned
            else:
                cleaned = '+' + cleaned
        
        return cleaned


# Singleton instance
twilio_service = TwilioService()
