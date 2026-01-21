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


def get_system_prompt(company_name: str, caller_phone: str, collected_info: Dict, state: str) -> str:
    """Generate the AI system prompt based on current conversation state"""
    
    # Format phone for display in prompt (for speech)
    phone_display = format_phone_for_speech(caller_phone)
    
    # Get the updated phone if different from caller ID
    current_phone = collected_info.get("phone", caller_phone)
    phone_to_confirm = format_phone_for_speech(current_phone)
    
    return f"""## Identity & Purpose

You are the receptionist for {company_name}. Capture caller details, classify urgency, and book appointments.

## Voice Style

- Friendly, calm, professional
- SHORT responses - one sentence max
- Use natural contractions
- NEVER say you are AI
- When saying phone numbers, say each digit separately with pauses

## Current Call

CALLER ID: {phone_display}
COLLECTED: {json.dumps(collected_info)}
STATE: {state}

## Call Flow - ONE question at a time

1. **Name** (if not collected):
   → "Can I get your name please?"

2. **Phone** (after name):
   → If phone not confirmed: "Is {phone_to_confirm} the best number to reach you?"
   → If they say NO or give new number: capture it, then confirm: "Got it, [new number]. Is that correct?"

3. **Address** (after phone confirmed):
   → "What's the service address?"
   → After they give it: "Got it, [address]. Is that correct?"

4. **Issue** (after address confirmed):
   → "What's going on with your system?"

5. **Urgency** (after issue):
   → "Is this an emergency, urgent in the next day or two, or more routine?"

6. **Day preference** (after urgency):
   → "What day works best - today, tomorrow, or another day this week?"

7. **Time slot** (after day):
   → Based on their day choice, offer: "I have morning 9 to 12, or afternoon 1 to 5. Which works better?"

8. **Confirm booking** (when all collected):
   → "Perfect, I'll book you for [day] [time slot] at [address]. Sound good?"
   → When they confirm: action="book_job"

## Response Format

IMPORTANT: Return phone numbers WITHOUT spaces in collected_data. Only use spaces when SPEAKING the number.

Return ONLY this JSON:
{{
    "response_text": "One short sentence",
    "next_state": "collecting_name|confirming_phone|collecting_new_phone|collecting_address|confirming_address|collecting_issue|collecting_urgency|offering_times|confirming_time|booking_complete",
    "collected_data": {{
        "name": "FirstName LastName or null",
        "phone": "1234567890 (digits only, NO SPACES) or null",
        "phone_confirmed": true/false,
        "address": "Full street address or null",
        "address_confirmed": true/false,
        "issue": "Brief issue description or null",
        "urgency": "EMERGENCY|URGENT|ROUTINE or null",
        "preferred_day": "today|tomorrow|specific day or null",
        "preferred_time": "morning|afternoon or null"
    }},
    "action": null or "book_job"
}}

## Rules

1. ONE sentence responses only
2. Follow exact order
3. If they give a NEW phone number, update phone field (DIGITS ONLY) and set phone_confirmed=false, then confirm it
4. Say phone numbers digit by digit: "2 1 5, 8 0 5, 0 5 9 4" but STORE as "2158050594"
5. Set action="book_job" ONLY when they confirm the final booking
6. Extract the caller's ACTUAL name - never leave as null if they provided it"""


async def get_ai_response(
    user_input: str,
    company_name: str,
    caller_phone: str,
    collected_info: Dict,
    state: str,
    conversation_history: list
) -> Dict[str, Any]:
    """
    Get AI response using OpenAI directly.
    Returns structured response with text and state updates.
    """
    from openai import AsyncOpenAI
    
    client = AsyncOpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
    system_prompt = get_system_prompt(company_name, caller_phone, collected_info, state)
    
    # Build messages
    messages = [{"role": "system", "content": system_prompt}]
    
    # Add conversation history (last 10 exchanges max)
    for msg in conversation_history[-20:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    
    # Add current user input
    messages.append({"role": "user", "content": user_input})
    
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=300
        )
        
        response_text = response.choices[0].message.content.strip()
        logger.info(f"AI raw response: {response_text}")
        
        # Parse JSON response
        try:
            # Handle potential markdown code blocks
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            parsed = json.loads(response_text)
            
            # Clean the collected data to normalize phone numbers and other fields
            collected_data = parsed.get("collected_data", collected_info)
            cleaned_data = clean_collected_data(collected_data)
            
            return {
                "response_text": parsed.get("response_text", "I'm sorry, could you repeat that?"),
                "next_state": parsed.get("next_state", state),
                "collected_data": cleaned_data,
                "action": parsed.get("action")
            }
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse AI JSON: {e}. Raw: {response_text}")
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
        
        # Get AI response
        ai_result = await get_ai_response(
            user_input=voice_prompt,
            company_name=self.company_name,
            caller_phone=self.caller_phone,
            collected_info=self.collected_info,
            state=self.state,
            conversation_history=self.conversation_history
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
        """Handle call end - save summary and create lead/message"""
        logger.info(f"Call ended: {self.call_sid}")
        
        # Generate call summary
        summary = self._generate_summary()
        
        await self.db.voice_calls.update_one(
            {"call_sid": self.call_sid},
            {"$set": {
                "state": STATE_ENDED,
                "ended_at": datetime.now(timezone.utc).isoformat(),
                "summary": summary,
                "duration_seconds": (datetime.now(timezone.utc) - self.call_started_at).total_seconds()
            }}
        )
        
        # Create lead if we have useful info
        if self.collected_info.get("name") or self.collected_info.get("issue"):
            await self._create_lead()
        
        # Create a message record for the inbox
        await self._create_inbox_message()
    
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
    
    async def _create_inbox_message(self) -> None:
        """Create a message in the inbox for this call"""
        # Find or create customer
        phone = self.collected_info.get("phone") or self.caller_phone
        customer = await self.db.customers.find_one({
            "tenant_id": self.tenant["id"],
            "phone": phone
        }, {"_id": 0})
        
        if not customer:
            return
        
        # Find or create conversation
        conversation = await self.db.conversations.find_one({
            "tenant_id": self.tenant["id"],
            "customer_id": customer["id"]
        }, {"_id": 0})
        
        if not conversation:
            conversation_id = str(uuid4())
            conversation = {
                "id": conversation_id,
                "tenant_id": self.tenant["id"],
                "customer_id": customer["id"],
                "status": "ACTIVE",
                "preferred_channel": "CALL",
                "last_message_from": "CUSTOMER",
                "last_message_at": datetime.now(timezone.utc).isoformat(),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            await self.db.conversations.insert_one(conversation)
        else:
            conversation_id = conversation["id"]
            # Update conversation
            await self.db.conversations.update_one(
                {"id": conversation_id},
                {"$set": {
                    "last_message_from": "CUSTOMER",
                    "last_message_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }}
            )
        
        # Create message for the voice call
        call_summary = self._generate_summary()
        transcript = "\n".join([
            f"{'Caller' if m['role'] == 'user' else 'AI'}: {m['content']}"
            for m in self.conversation_history
        ])
        
        message = {
            "id": str(uuid4()),
            "tenant_id": self.tenant["id"],
            "conversation_id": conversation_id,
            "customer_id": customer["id"],
            "direction": "INBOUND",
            "sender_type": "CUSTOMER",
            "channel": "VOICE",
            "content": f"📞 Voice Call\n\n{call_summary}\n\n--- Transcript ---\n{transcript}",
            "metadata": {
                "call_sid": self.call_sid,
                "duration_seconds": (datetime.now(timezone.utc) - self.call_started_at).total_seconds(),
                "collected_info": self.collected_info
            },
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        await self.db.messages.insert_one(message)
        logger.info(f"Created inbox message for call {self.call_sid}")
    
    async def _create_lead(self) -> Optional[str]:
        """Create a lead from call information"""
        lead_id = str(uuid4())
        
        # Use the confirmed phone, not caller ID
        phone = self.collected_info.get("phone") or self.caller_phone
        
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
    
    async def _create_booking(self) -> None:
        """Create a job booking from collected information"""
        from services.twilio_service import twilio_service
        
        # Use the confirmed phone number
        phone = self.collected_info.get("phone") or self.caller_phone
        
        # First create/find customer
        customer = await self._find_or_create_customer()
        if not customer:
            return
        
        # Create property if we have address
        property_id = None
        if self.collected_info.get("address") and self.collected_info.get("address_confirmed"):
            property_id = await self._create_property(customer["id"])
        
        # Create the job
        job_id = str(uuid4())
        
        # Determine the booking time based on collected preferences
        preferred_day = self.collected_info.get("preferred_day", "").lower()
        preferred_time = self.collected_info.get("preferred_time", "morning").lower()
        
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
        
        job = {
            "id": job_id,
            "tenant_id": self.tenant["id"],
            "customer_id": customer["id"],
            "property_id": property_id,
            "job_type": "DIAGNOSTIC",
            "priority": self._map_urgency_to_priority(self.collected_info.get("urgency")),
            "status": "SCHEDULED",
            "created_by": "AI_PHONE",
            "description": self.collected_info.get("issue", "Service call scheduled via phone"),
            "notes": f"Booked via AI phone. Urgency: {self.collected_info.get('urgency', 'ROUTINE')}",
            "service_window_start": window_start.isoformat(),
            "service_window_end": window_end.isoformat(),
            "tags": ["voice_ai_booking"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        await self.db.jobs.insert_one(job)
        logger.info(f"Created job {job_id} from voice booking")
        
        # Send SMS confirmation to the CONFIRMED phone number
        if phone:
            date_str = window_start.strftime("%A, %B %d")
            address = self.collected_info.get('address', 'your location')
            name = self.collected_info.get('name', '').split()[0] if self.collected_info.get('name') else 'there'
            
            sms_msg = f"Hi {name}! Your appointment with {self.company_name} is confirmed for {date_str}, {time_label} at {address}. We'll text you when our tech is on the way!"
            
            try:
                await twilio_service.send_sms(to_phone=phone, body=sms_msg)
                logger.info(f"Sent booking confirmation SMS to {phone}")
                
                # Also create a message record for the SMS
                await self._create_sms_message(customer["id"], sms_msg)
            except Exception as e:
                logger.error(f"Failed to send SMS confirmation: {e}")
    
    async def _create_sms_message(self, customer_id: str, content: str) -> None:
        """Create a message record for the SMS confirmation"""
        # Find conversation
        conversation = await self.db.conversations.find_one({
            "tenant_id": self.tenant["id"],
            "customer_id": customer_id
        }, {"_id": 0})
        
        if not conversation:
            return
        
        message = {
            "id": str(uuid4()),
            "tenant_id": self.tenant["id"],
            "conversation_id": conversation["id"],
            "customer_id": customer_id,
            "direction": "OUTBOUND",
            "sender_type": "SYSTEM",
            "channel": "SMS",
            "content": content,
            "metadata": {"source": "voice_ai_booking_confirmation"},
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        await self.db.messages.insert_one(message)
        
        # Update conversation
        await self.db.conversations.update_one(
            {"id": conversation["id"]},
            {"$set": {
                "last_message_from": "SYSTEM",
                "last_message_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
    
    async def _find_or_create_customer(self) -> Optional[Dict]:
        """Find existing customer or create new one using CONFIRMED phone"""
        # Use the confirmed phone, not caller ID
        phone = self.collected_info.get("phone") or self.caller_phone
        
        # Try to find by phone
        customer = await self.db.customers.find_one({
            "tenant_id": self.tenant["id"],
            "phone": phone
        }, {"_id": 0})
        
        if customer:
            # Update name if we have a new one
            if self.collected_info.get("name") and not customer.get("first_name"):
                name_parts = self.collected_info["name"].split(" ", 1)
                await self.db.customers.update_one(
                    {"id": customer["id"]},
                    {"$set": {
                        "first_name": name_parts[0],
                        "last_name": name_parts[1] if len(name_parts) > 1 else "",
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }}
                )
            return customer
        
        # Create new customer with confirmed phone
        customer_id = str(uuid4())
        name_parts = (self.collected_info.get("name") or "").split(" ", 1)
        
        new_customer = {
            "id": customer_id,
            "tenant_id": self.tenant["id"],
            "first_name": name_parts[0] if name_parts[0] else "Unknown",
            "last_name": name_parts[1] if len(name_parts) > 1 else "",
            "phone": phone,
            "source": "AI_PHONE",
            "tags": ["voice_ai"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        await self.db.customers.insert_one(new_customer)
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
