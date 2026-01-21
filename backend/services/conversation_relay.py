"""
Twilio ConversationRelay Voice AI Service
Real-time WebSocket streaming for natural voice conversations
"""
import os
import json
import logging
import re
from typing import Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from uuid import uuid4

logger = logging.getLogger(__name__)

# Conversation states
STATE_GREETING = "greeting"
STATE_COLLECTING_NAME = "collecting_name"
STATE_CONFIRMING_PHONE = "confirming_phone"
STATE_COLLECTING_NEW_PHONE = "collecting_new_phone"
STATE_COLLECTING_ADDRESS = "collecting_address"
STATE_CONFIRMING_ADDRESS = "confirming_address"
STATE_COLLECTING_ISSUE = "collecting_issue"
STATE_COLLECTING_URGENCY = "collecting_urgency"
STATE_OFFERING_TIMES = "offering_times"
STATE_CONFIRMING_TIME = "confirming_time"
STATE_BOOKING_COMPLETE = "booking_complete"
STATE_ENDED = "ended"


def normalize_phone_number(phone: str) -> str:
    """
    Normalize phone number to clean E.164 format.
    Removes spaces, commas, and other formatting characters.
    Returns: +1XXXXXXXXXX format
    """
    if not phone:
        return ""
    # Remove ALL non-digit characters
    digits = re.sub(r'\D', '', phone)
    
    # Handle various lengths
    if len(digits) == 10:
        return f"+1{digits}"
    elif len(digits) == 11 and digits.startswith('1'):
        return f"+{digits}"
    elif len(digits) > 11:
        # Take last 10 digits and add +1
        return f"+1{digits[-10:]}"
    else:
        # Return as-is with + prefix
        return f"+{digits}" if digits else ""


def format_phone_for_speech(phone: str) -> str:
    """Format phone number for natural speech with pauses"""
    if not phone:
        return ""
    # First normalize to get clean digits
    normalized = normalize_phone_number(phone)
    digits = re.sub(r'\D', '', normalized)
    
    if len(digits) == 11 and digits.startswith('1'):
        digits = digits[1:]  # Remove country code for speech
    
    if len(digits) == 10:
        # Format as: 2 1 5, 8 0 5, 0 5 9 4 (with pauses)
        return f"{digits[0]} {digits[1]} {digits[2]}, {digits[3]} {digits[4]} {digits[5]}, {digits[6]} {digits[7]} {digits[8]} {digits[9]}"
    return phone


def clean_collected_data(data: Dict) -> Dict:
    """
    Clean and normalize collected data from AI responses.
    - Removes spaces from phone numbers
    - Normalizes addresses
    - Cleans up names
    """
    cleaned = data.copy()
    
    # Clean phone number - remove spaces, commas, etc.
    if cleaned.get("phone"):
        cleaned["phone"] = normalize_phone_number(cleaned["phone"])
    
    # Clean name - capitalize properly
    if cleaned.get("name"):
        name = cleaned["name"].strip()
        # Remove any weird characters
        name = re.sub(r'[^\w\s\'-]', '', name)
        # Capitalize each word
        name = ' '.join(word.capitalize() for word in name.split())
        cleaned["name"] = name
    
    # Clean address - normalize whitespace
    if cleaned.get("address"):
        address = cleaned["address"].strip()
        # Normalize multiple spaces to single space
        address = re.sub(r'\s+', ' ', address)
        cleaned["address"] = address
    
    return cleaned


# Default system prompt template - can be overridden per tenant
DEFAULT_VOICE_PROMPT = """You are a friendly receptionist for {company_name}. Your job is to collect information from callers and book service appointments.

CURRENT CALL STATE:
- Caller phone: {caller_phone}
- Data collected so far: {collected_info}
- Current step: {state}

CONVERSATION FLOW (follow this order):
1. Get caller's name
2. Confirm their phone number (or get a new one if they prefer)
3. Get service address
4. Ask what's wrong with their system
5. Ask urgency: emergency, urgent (1-2 days), or routine
6. Ask preferred day: today, tomorrow, or later this week
7. Ask preferred time: morning (9-12) or afternoon (1-5)
8. Confirm the booking and set action to "book_job"

RULES:
- Keep responses SHORT (1 sentence max)
- Be warm and professional
- Say phone numbers digit by digit when speaking
- Store phone numbers as digits only (no spaces)
- Set action="book_job" ONLY when customer confirms final booking"""


def get_system_prompt(company_name: str, caller_phone: str, collected_info: Dict, state: str, custom_prompt: str = None) -> str:
    """
    Generate the AI system prompt.
    Uses custom prompt from tenant if provided, otherwise uses default.
    """
    # Format phone for speech
    phone_display = format_phone_for_speech(caller_phone)
    
    # Use custom prompt or default
    base_prompt = custom_prompt if custom_prompt else DEFAULT_VOICE_PROMPT
    
    # Replace placeholders
    prompt = base_prompt.format(
        company_name=company_name,
        caller_phone=phone_display,
        collected_info=json.dumps(collected_info),
        state=state
    )
    
    # Add JSON response format instructions (always required)
    json_instructions = """

RESPONSE FORMAT (REQUIRED - always respond with this exact JSON structure):
{
    "response_text": "Your spoken response here (keep it short)",
    "next_state": "collecting_name|confirming_phone|collecting_address|collecting_issue|collecting_urgency|offering_times|confirming_time|booking_complete",
    "collected_data": {
        "name": "Customer name or null if not yet collected",
        "phone": "10 digit phone number with no spaces or null",
        "phone_confirmed": true or false,
        "address": "Full address or null",
        "address_confirmed": true or false,
        "issue": "Issue description or null",
        "urgency": "EMERGENCY or URGENT or ROUTINE or null",
        "preferred_day": "today/tomorrow/specific day or null",
        "preferred_time": "morning or afternoon or null"
    },
    "action": null or "book_job"
}

IMPORTANT:
- Store phone as digits only: "2158050594" not "2 1 5 8 0 5 0 5 9 4"
- Only set action="book_job" when customer confirms the final booking
- Always preserve previously collected data in collected_data"""

    return prompt + json_instructions


async def get_ai_response(
    user_input: str,
    company_name: str,
    caller_phone: str,
    collected_info: Dict,
    state: str,
    conversation_history: list,
    custom_prompt: str = None
) -> Dict[str, Any]:
    """
    Get AI response using OpenAI directly with JSON mode.
    Returns structured response with text and state updates.
    
    Args:
        custom_prompt: Optional custom system prompt from tenant configuration
    """
    from openai import AsyncOpenAI
    
    client = AsyncOpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
    system_prompt = get_system_prompt(company_name, caller_phone, collected_info, state, custom_prompt)
    
    # Build messages
    messages = [{"role": "system", "content": system_prompt}]
    
    # Add conversation history (last 10 exchanges max)
    for msg in conversation_history[-20:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    
    # Add current user input
    messages.append({"role": "user", "content": user_input})
    
    try:
        # Use JSON mode to ensure structured response
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=400,
            response_format={"type": "json_object"}  # Force JSON response
        )
        
        response_text = response.choices[0].message.content.strip()
        logger.info(f"AI raw response: {response_text[:200]}...")
        
        # Parse JSON response
        try:
            parsed = json.loads(response_text)
            
            # Clean the collected data to normalize phone numbers and other fields
            collected_data = parsed.get("collected_data", {})
            # Merge with existing collected_info (don't lose previously collected data)
            merged_data = collected_info.copy()
            for key, value in collected_data.items():
                if value is not None:
                    merged_data[key] = value
            
            cleaned_data = clean_collected_data(merged_data)
            
            return {
                "response_text": parsed.get("response_text", "I'm sorry, could you repeat that?"),
                "next_state": parsed.get("next_state", state),
                "collected_data": cleaned_data,
                "action": parsed.get("action")
            }
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse AI JSON: {e}. Raw: {response_text}")
            # Return the raw text as response but keep existing data
            return {
                "response_text": response_text if len(response_text) < 200 else "I'm sorry, could you repeat that?",
                "next_state": state,
                "collected_data": collected_info,
                "action": None
            }
            
    except Exception as e:
        logger.error(f"AI response error: {e}")
        return {
            "response_text": "I'm sorry, I'm having trouble. Could you repeat that?",
            "next_state": state,
            "collected_data": collected_info,
            "action": None
        }


class ConversationRelayHandler:
    """Handles WebSocket communication with Twilio ConversationRelay"""
    
    def __init__(self, db, call_sid: str, tenant: Dict, caller_phone: str):
        self.db = db
        self.call_sid = call_sid
        self.tenant = tenant
        self.caller_phone = caller_phone
        self.company_name = tenant.get("name", "our company")
        self.state = STATE_COLLECTING_NAME  # Start collecting name after greeting
        self.collected_info = {
            "name": None,
            "phone": caller_phone,  # Start with caller ID
            "phone_confirmed": False,
            "address": None,
            "address_confirmed": False,
            "issue": None,
            "urgency": None,
            "preferred_day": None,
            "preferred_time": None
        }
        self.conversation_history = []
        self.call_started_at = datetime.now(timezone.utc)
    
    async def handle_setup(self, message: Dict) -> None:
        """Handle setup message from ConversationRelay"""
        logger.info(f"ConversationRelay setup: {message}")
        # Store call metadata
        await self.db.voice_calls.update_one(
            {"call_sid": self.call_sid},
            {"$set": {
                "tenant_id": self.tenant["id"],
                "caller_phone": self.caller_phone,
                "state": self.state,
                "collected_info": self.collected_info,
                "started_at": self.call_started_at.isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }},
            upsert=True
        )
    
    async def handle_prompt(self, message: Dict) -> str:
        """
        Handle prompt (transcribed speech) from caller.
        Returns text response to be spoken back.
        """
        voice_prompt = message.get("voicePrompt", "")
        is_last = message.get("last", True)
        
        if not voice_prompt.strip():
            return None
        
        logger.info(f"Caller said: '{voice_prompt}' (last={is_last})")
        
        # Add to conversation history
        self.conversation_history.append({
            "role": "user",
            "content": voice_prompt
        })
        
        # Get custom prompt from tenant if configured
        custom_prompt = self.tenant.get("voice_system_prompt")
        
        # Get AI response
        ai_result = await get_ai_response(
            user_input=voice_prompt,
            company_name=self.company_name,
            caller_phone=self.caller_phone,
            collected_info=self.collected_info,
            state=self.state,
            conversation_history=self.conversation_history,
            custom_prompt=custom_prompt
        )
        
        # Update state and collected info
        self.state = ai_result.get("next_state", self.state)
        new_data = ai_result.get("collected_data", {})
        for key, value in new_data.items():
            if value is not None:
                self.collected_info[key] = value
        
        response_text = ai_result.get("response_text", "")
        action = ai_result.get("action")
        
        # Format phone numbers in response for natural speech
        response_text = self._format_response_for_speech(response_text)
        
        # Add assistant response to history
        self.conversation_history.append({
            "role": "assistant",
            "content": response_text
        })
        
        # Update database
        await self.db.voice_calls.update_one(
            {"call_sid": self.call_sid},
            {"$set": {
                "state": self.state,
                "collected_info": self.collected_info,
                "conversation_history": self.conversation_history,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        # Handle booking action
        if action == "book_job":
            await self._create_booking()
        
        return response_text
    
    def _format_response_for_speech(self, text: str) -> str:
        """Format text for natural speech - add pauses for numbers"""
        # Find phone numbers and format them
        phone_pattern = r'\+?1?\d{10,11}|\d{3}[-.\s]?\d{3}[-.\s]?\d{4}'
        
        def format_match(match):
            phone = match.group()
            return format_phone_for_speech(phone)
        
        text = re.sub(phone_pattern, format_match, text)
        return text
    
    async def handle_interrupt(self, message: Dict) -> None:
        """Handle interruption (caller spoke during TTS)"""
        utterance = message.get("utteranceUntilInterrupt", "")
        duration_ms = message.get("durationUntilInterruptMs", 0)
        logger.info(f"Caller interrupted after {duration_ms}ms. Partial: '{utterance}'")
    
    async def handle_dtmf(self, message: Dict) -> str:
        """Handle DTMF key press"""
        digit = message.get("digit", "")
        logger.info(f"DTMF digit pressed: {digit}")
        
        if digit == "0":
            return "Let me connect you to someone. One moment please."
        
        return None
    
    async def handle_error(self, message: Dict) -> None:
        """Handle error from ConversationRelay"""
        description = message.get("description", "Unknown error")
        logger.error(f"ConversationRelay error: {description}")
    
    async def handle_end(self) -> None:
        """Handle call end - save summary and create lead"""
        logger.info(f"Call ended: {self.call_sid}")
        
        # Generate call summary
        summary = self._generate_summary()
        
        await self.db.voice_calls.update_one(
            {"call_sid": self.call_sid},
            {"$set": {
                "state": STATE_ENDED,
                "ended_at": datetime.now(timezone.utc).isoformat(),
                "summary": summary,
                "collected_info": self.collected_info,
                "duration_seconds": (datetime.now(timezone.utc) - self.call_started_at).total_seconds()
            }}
        )
        
        # Create lead if we have useful info (but no job was booked)
        # If a job was booked via action="book_job", _create_booking already handles everything
        if (self.collected_info.get("name") or self.collected_info.get("issue")) and self.state != STATE_BOOKING_COMPLETE:
            await self._create_lead()
        
        # Note: We do NOT create inbox messages for voice calls per user request
        # Inbox should only show SMS messages
    
    def _generate_summary(self) -> str:
        """Generate a summary of the call"""
        parts = []
        if self.collected_info.get("name"):
            parts.append(f"Caller: {self.collected_info['name']}")
        if self.collected_info.get("phone"):
            parts.append(f"Phone: {self.collected_info['phone']}")
        if self.collected_info.get("address"):
            parts.append(f"Address: {self.collected_info['address']}")
        if self.collected_info.get("issue"):
            parts.append(f"Issue: {self.collected_info['issue']}")
        if self.collected_info.get("urgency"):
            parts.append(f"Urgency: {self.collected_info['urgency']}")
        
        return " | ".join(parts) if parts else "No information collected"
    
    async def _create_lead(self) -> Optional[str]:
        """Create a lead from call information"""
        lead_id = str(uuid4())
        
        # Use the confirmed phone, not caller ID - ensure it's normalized
        phone = normalize_phone_number(self.collected_info.get("phone") or self.caller_phone)
        
        lead = {
            "id": lead_id,
            "tenant_id": self.tenant["id"],
            "source": "AI_PHONE",
            "channel": "VOICE",
            "status": "NEW",
            "caller_name": self.collected_info.get("name"),
            "caller_phone": phone,
            "captured_address": self.collected_info.get("address"),
            "issue_type": self.collected_info.get("issue", "")[:100] if self.collected_info.get("issue") else None,
            "description": self.collected_info.get("issue"),
            "urgency": self.collected_info.get("urgency", "ROUTINE"),
            "tags": ["voice_ai", "conversation_relay"],
            "call_sid": self.call_sid,
            "first_contact_at": self.call_started_at.isoformat(),
            "last_activity_at": datetime.now(timezone.utc).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        await self.db.leads.insert_one(lead)
        logger.info(f"Created lead {lead_id} from voice call {self.call_sid}")
        
        return lead_id
    
    def _calculate_quote_amount(self, job_type: str, urgency: str) -> float:
        """Calculate quote amount based on job type and urgency"""
        base_prices = {
            "DIAGNOSTIC": 89.00,
            "REPAIR": 250.00,
            "MAINTENANCE": 149.00,
            "INSTALL": 1500.00,
            "INSTALLATION": 1500.00,
            "INSPECTION": 75.00,
        }
        
        urgency_multipliers = {
            "EMERGENCY": 1.5,
            "URGENT": 1.25,
            "ROUTINE": 1.0,
        }
        
        base = base_prices.get(job_type, 89.00)
        multiplier = urgency_multipliers.get(urgency, 1.0)
        
        return round(base * multiplier, 2)
    
    async def _create_booking(self) -> None:
        """Create a job booking with quote from collected information and send confirmation SMS"""
        from services.twilio_service import twilio_service
        
        # Use the confirmed phone number - ensure it's normalized
        phone = normalize_phone_number(self.collected_info.get("phone") or self.caller_phone)
        
        # First create/find customer
        customer = await self._find_or_create_customer()
        if not customer:
            logger.error("Failed to create/find customer for booking")
            return
        
        # Create property if we have address
        property_id = None
        if self.collected_info.get("address"):
            property_id = await self._create_property(customer["id"])
        
        # Create the job
        job_id = str(uuid4())
        quote_id = str(uuid4())
        
        # Determine the booking time based on collected preferences
        preferred_day = (self.collected_info.get("preferred_day") or "").lower()
        preferred_time = (self.collected_info.get("preferred_time") or "morning").lower()
        
        # Calculate the actual date
        now = datetime.now(timezone.utc)
        if "today" in preferred_day:
            job_date = now
        elif "tomorrow" in preferred_day:
            job_date = now + timedelta(days=1)
        else:
            # Default to tomorrow
            job_date = now + timedelta(days=1)
        
        # Set time window based on preference
        if "afternoon" in preferred_time or "pm" in preferred_time:
            window_start = job_date.replace(hour=13, minute=0, second=0, microsecond=0)
            window_end = job_date.replace(hour=17, minute=0, second=0, microsecond=0)
            time_label = "1 PM to 5 PM"
        else:
            window_start = job_date.replace(hour=9, minute=0, second=0, microsecond=0)
            window_end = job_date.replace(hour=12, minute=0, second=0, microsecond=0)
            time_label = "9 AM to 12 PM"
        
        # Calculate quote amount
        urgency = self.collected_info.get("urgency", "ROUTINE")
        quote_amount = self._calculate_quote_amount("DIAGNOSTIC", urgency)
        
        # Create Quote
        quote = {
            "id": quote_id,
            "tenant_id": self.tenant["id"],
            "customer_id": customer["id"],
            "property_id": property_id,
            "job_id": job_id,
            "amount": quote_amount,
            "currency": "USD",
            "description": f"Diagnostic service - {self.collected_info.get('issue', 'General service call')}",
            "status": "SENT",
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        await self.db.quotes.insert_one(quote)
        logger.info(f"Created quote {quote_id} for ${quote_amount}")
        
        # Create Job
        job = {
            "id": job_id,
            "tenant_id": self.tenant["id"],
            "customer_id": customer["id"],
            "property_id": property_id,
            "job_type": "DIAGNOSTIC",
            "priority": self._map_urgency_to_priority(urgency),
            "status": "SCHEDULED",
            "created_by": "AI_PHONE",
            "description": self.collected_info.get("issue", "Service call scheduled via phone"),
            "notes": f"Booked via AI phone. Urgency: {urgency}. Caller: {self.collected_info.get('name', 'Unknown')}",
            "service_window_start": window_start.isoformat(),
            "service_window_end": window_end.isoformat(),
            "quote_amount": quote_amount,
            "quote_id": quote_id,
            "tags": ["voice_ai_booking"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        await self.db.jobs.insert_one(job)
        logger.info(f"Created job {job_id} from voice booking")
        
        # Also create a lead record for tracking
        lead_id = await self._create_lead()
        if lead_id:
            # Update lead status to JOB_BOOKED
            await self.db.leads.update_one(
                {"id": lead_id},
                {"$set": {"status": "JOB_BOOKED", "updated_at": datetime.now(timezone.utc).isoformat()}}
            )
        
        # Update state to booking complete
        self.state = STATE_BOOKING_COMPLETE
        
        # Send SMS confirmation with quote to the CONFIRMED phone number
        if phone:
            date_str = window_start.strftime("%A, %B %d")
            address = self.collected_info.get('address', 'your location')
            name = (self.collected_info.get('name') or '').split()[0] if self.collected_info.get('name') else 'there'
            
            sms_sig = self.tenant.get('sms_signature', '').strip()
            
            # Confirmation SMS with quote
            sms_msg = f"Hi {name}! Your appointment with {self.company_name} is confirmed for {date_str}, {time_label} at {address}. Service quote: ${quote_amount:.2f}. We'll text you when our tech is on the way!{' ' + sms_sig if sms_sig else ''}"
            
            try:
                result = await twilio_service.send_sms(to_phone=phone, body=sms_msg)
                if result.get("success"):
                    logger.info(f"Sent booking confirmation SMS to {phone}")
                    # Create a message record for the SMS in inbox
                    await self._create_sms_message(customer["id"], sms_msg, result.get("provider_message_id"))
                else:
                    logger.error(f"Failed to send SMS: {result.get('error')}")
            except Exception as e:
                logger.error(f"Failed to send SMS confirmation: {e}")
    
    async def _create_sms_message(self, customer_id: str, content: str, twilio_sid: str = None) -> None:
        """Create a message record for the SMS in the inbox"""
        # Find or create conversation for this customer
        conversation = await self.db.conversations.find_one({
            "tenant_id": self.tenant["id"],
            "customer_id": customer_id
        }, {"_id": 0})
        
        if not conversation:
            # Create a new conversation
            conversation_id = str(uuid4())
            conversation = {
                "id": conversation_id,
                "tenant_id": self.tenant["id"],
                "customer_id": customer_id,
                "status": "OPEN",
                "primary_channel": "SMS",
                "last_message_from": "SYSTEM",
                "last_message_at": datetime.now(timezone.utc).isoformat(),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            await self.db.conversations.insert_one(conversation)
        else:
            conversation_id = conversation["id"]
        
        # Create the outbound SMS message
        message = {
            "id": str(uuid4()),
            "tenant_id": self.tenant["id"],
            "conversation_id": conversation_id,
            "customer_id": customer_id,
            "direction": "OUTBOUND",
            "sender_type": "SYSTEM",
            "channel": "SMS",
            "content": content,
            "metadata": {
                "source": "voice_ai_booking_confirmation",
                "twilio_sid": twilio_sid
            },
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        await self.db.messages.insert_one(message)
        
        # Update conversation
        await self.db.conversations.update_one(
            {"id": conversation_id},
            {"$set": {
                "last_message_from": "SYSTEM",
                "last_message_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        logger.info(f"Created SMS message record in inbox for customer {customer_id}")
    
    async def _find_or_create_customer(self) -> Optional[Dict]:
        """Find existing customer or create new one using CONFIRMED phone"""
        # Use the confirmed phone, not caller ID - ensure it's normalized
        phone = normalize_phone_number(self.collected_info.get("phone") or self.caller_phone)
        
        # Try to find by phone
        customer = await self.db.customers.find_one({
            "tenant_id": self.tenant["id"],
            "phone": phone
        }, {"_id": 0})
        
        if customer:
            # Update name if we have a new one and current name is Unknown
            if self.collected_info.get("name"):
                name = self.collected_info["name"]
                if customer.get("first_name") == "Unknown" or not customer.get("first_name"):
                    name_parts = name.split(" ", 1)
                    await self.db.customers.update_one(
                        {"id": customer["id"]},
                        {"$set": {
                            "first_name": name_parts[0],
                            "last_name": name_parts[1] if len(name_parts) > 1 else "",
                            "updated_at": datetime.now(timezone.utc).isoformat()
                        }}
                    )
                    # Return updated customer
                    customer = await self.db.customers.find_one({"id": customer["id"]}, {"_id": 0})
            return customer
        
        # Create new customer with confirmed phone
        customer_id = str(uuid4())
        name = self.collected_info.get("name") or ""
        name_parts = name.split(" ", 1) if name else ["Unknown", ""]
        
        new_customer = {
            "id": customer_id,
            "tenant_id": self.tenant["id"],
            "first_name": name_parts[0] if name_parts[0] else "Unknown",
            "last_name": name_parts[1] if len(name_parts) > 1 else "",
            "phone": phone,
            "preferred_channel": "SMS",
            "source": "AI_PHONE",
            "tags": ["voice_ai"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        await self.db.customers.insert_one(new_customer)
        logger.info(f"Created new customer {customer_id}: {name_parts[0]} {name_parts[1] if len(name_parts) > 1 else ''}")
        return new_customer
    
    async def _create_property(self, customer_id: str) -> Optional[str]:
        """Create property from address"""
        address = self.collected_info.get("address")
        if not address:
            return None
        
        # Check if property already exists
        existing = await self.db.properties.find_one({
            "tenant_id": self.tenant["id"],
            "customer_id": customer_id,
            "address_line1": address
        }, {"_id": 0})
        
        if existing:
            return existing["id"]
        
        property_id = str(uuid4())
        
        new_property = {
            "id": property_id,
            "tenant_id": self.tenant["id"],
            "customer_id": customer_id,
            "address_line1": address,
            "property_type": "RESIDENTIAL",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        await self.db.properties.insert_one(new_property)
        return property_id
    
    def _map_urgency_to_priority(self, urgency: str) -> str:
        """Map urgency level to job priority"""
        mapping = {
            "EMERGENCY": "EMERGENCY",
            "URGENT": "HIGH",
            "ROUTINE": "NORMAL"
        }
        return mapping.get(urgency, "NORMAL")
