"""
AI-powered SMS Booking Service

Handles automated SMS conversations to book service appointments.
Uses OpenAI to understand customer responses and guide them through booking.
"""
import os
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

logger = logging.getLogger(__name__)

# System prompt for the AI booking assistant
SMS_BOOKING_SYSTEM_PROMPT = """You are a friendly and professional AI assistant for {company_name}, a field service company. You're having an SMS conversation to help a customer book a service appointment.

CONTEXT:
- Customer Name: {customer_name}
- Their Issue: {issue_description}
- Urgency: {urgency}
- Their Address: {address}

YOUR GOALS:
1. Confirm their service needs
2. Determine the appropriate job type (DIAGNOSTIC, REPAIR, MAINTENANCE, or INSTALL)
3. Find out their availability for an appointment
4. Book the appointment

AVAILABLE JOB TYPES:
- DIAGNOSTIC ($89): Initial inspection to diagnose the problem
- REPAIR ($250): Fix a known issue
- MAINTENANCE ($149): Regular maintenance/tune-up
- INSTALL ($1500): New equipment installation

CONVERSATION RULES:
- Keep messages SHORT (under 160 chars ideally for SMS)
- Be warm but professional
- Ask ONE question at a time
- When you have enough info, output a JSON booking command

BOOKING COMMAND FORMAT:
When ready to book, output ONLY this JSON (no other text):
{{"action": "book_job", "job_type": "DIAGNOSTIC|REPAIR|MAINTENANCE|INSTALL", "date": "YYYY-MM-DD", "time_slot": "morning|afternoon|evening", "confirmed": true}}

TIME SLOTS:
- morning: 8 AM - 12 PM
- afternoon: 12 PM - 4 PM  
- evening: 4 PM - 7 PM

If customer confirms, output the booking JSON. If they need to reschedule or have questions, continue the conversation.

Current date/time: {current_datetime}
Business hours: Monday-Saturday, 8 AM - 7 PM"""


class AiSmsService:
    """Service for AI-powered SMS conversations"""
    
    def __init__(self):
        self.api_key = os.environ.get('OPENAI_API_KEY')
        if not self.api_key:
            logger.warning("OPENAI_API_KEY not found in environment")
    
    async def process_sms_reply(
        self,
        customer_message: str,
        conversation_context: Dict[str, Any],
        tenant_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process an inbound SMS and generate AI response.
        
        Returns:
            {
                "response_text": str,  # Text to send back to customer
                "action": str or None,  # "book_job" if ready to book
                "booking_data": dict or None  # Job booking details if action is book_job
            }
        """
        if not self.api_key:
            return {
                "response_text": "Thanks for your message! A team member will reach out shortly.",
                "action": None,
                "booking_data": None
            }
        
        client = AsyncOpenAI(api_key=self.api_key)
        
        # Build system prompt with context
        import pytz
        tenant_tz = pytz.timezone(tenant_info.get("timezone", "America/New_York"))
        current_time = datetime.now(tenant_tz)
        
        system_prompt = SMS_BOOKING_SYSTEM_PROMPT.format(
            company_name=tenant_info.get("name", "Our company"),
            customer_name=conversation_context.get("customer_name", "Customer"),
            issue_description=conversation_context.get("issue_description", "service needed"),
            urgency=conversation_context.get("urgency", "ROUTINE"),
            address=conversation_context.get("address", ""),
            current_datetime=current_time.strftime("%A, %B %d, %Y at %I:%M %p")
        )
        
        # Build conversation history
        history = conversation_context.get("message_history", [])
        messages = [{"role": "system", "content": system_prompt}]
        
        for msg in history[-8:]:
            role = "user" if msg.get("direction") == "INBOUND" else "assistant"
            messages.append({"role": role, "content": msg.get("content", "")})
        
        messages.append({"role": "user", "content": customer_message})
        
        try:
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.7,
                max_tokens=200
            )
            
            response_text = response.choices[0].message.content.strip()
            action = None
            booking_data = None
            
            # Try to parse as JSON booking command
            if response_text.startswith("{") and "book_job" in response_text:
                try:
                    booking_data = json.loads(response_text)
                    if booking_data.get("action") == "book_job" and booking_data.get("confirmed"):
                        action = "book_job"
                        response_text = f"Perfect! I've booked your {booking_data.get('job_type', 'service').lower()} appointment for {booking_data.get('date')} in the {booking_data.get('time_slot', 'morning')}. You'll receive a confirmation shortly!"
                except json.JSONDecodeError:
                    pass
            
            return {
                "response_text": response_text,
                "action": action,
                "booking_data": booking_data
            }
            
        except Exception as e:
            logger.error(f"AI SMS processing error: {e}")
            return {
                "response_text": "Thanks for your message! A team member will follow up shortly.",
                "action": None,
                "booking_data": None
            }
    
    async def generate_initial_message(
        self,
        customer_name: str,
        issue_description: str,
        company_name: str
    ) -> str:
        """Generate the initial AI greeting message for webform leads"""
        if not self.api_key:
            return f"Hi {customer_name}! Thanks for reaching out to {company_name} about: {issue_description[:50]}. When would be a good time for us to come take a look?"
        
        try:
            client = AsyncOpenAI(api_key=self.api_key)
            
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": f"""Generate a SHORT (under 160 chars) SMS greeting for {company_name}. Be warm but professional. Ask about availability.
Customer: {customer_name}
Issue: {issue_description}
Output ONLY the SMS text."""},
                    {"role": "user", "content": "Generate the greeting"}
                ],
                temperature=0.7,
                max_tokens=100
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating initial message: {e}")
            return f"Hi {customer_name}! Thanks for contacting {company_name}. When works best for an appointment - morning, afternoon, or evening?"


# Singleton instance
ai_sms_service = AiSmsService()
