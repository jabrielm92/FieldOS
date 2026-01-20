"""
Twilio ConversationRelay Voice AI Service
Real-time WebSocket streaming for natural voice conversations
"""
import os
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from uuid import uuid4

logger = logging.getLogger(__name__)

# Conversation states
STATE_GREETING = "greeting"
STATE_COLLECTING_NAME = "collecting_name"
STATE_CONFIRMING_PHONE = "confirming_phone"
STATE_COLLECTING_ADDRESS = "collecting_address"
STATE_CONFIRMING_ADDRESS = "confirming_address"
STATE_COLLECTING_ISSUE = "collecting_issue"
STATE_COLLECTING_URGENCY = "collecting_urgency"
STATE_OFFERING_TIMES = "offering_times"
STATE_BOOKING_COMPLETE = "booking_complete"
STATE_ENDED = "ended"


def get_system_prompt(company_name: str, caller_phone: str, collected_info: Dict, state: str) -> str:
    """Generate the AI system prompt based on current conversation state"""
    return f"""## Identity & Purpose

You are the receptionist and scheduling assistant for {company_name}. You answer inbound calls, capture caller details, classify urgency, and book service appointments.

You do NOT diagnose equipment or quote detailed prices. You are the front door to the schedule.

## Voice & Persona

- **Tone**: friendly, calm, blue-collar professional, competent and organized
- Be patient with stressed callers (no heat / no cooling)
- Use clear, simple language with natural contractions
- Use short practical phrases like:
  - "Let me grab a few details from you."
  - "One moment while I check the schedule."
  - "Got it."
  - "Perfect."
- NEVER say you are AI. You are "the scheduling assistant" or "front desk"
- Keep responses SHORT - this is a phone call, not a chat. One or two sentences max.

## Current Call Context

CALLER PHONE: {caller_phone}
INFO COLLECTED: {json.dumps(collected_info)}
CURRENT STATE: {state}

## REQUIRED Call Flow - FOLLOW THIS EXACT ORDER

Collect information in this order. Do not skip steps. Ask ONE question at a time.

1. **Get Name FIRST** - If no name collected:
   → "Can I get your name please?"

2. **Confirm Phone** - After you have name:
   → "Is {caller_phone} the best number to reach you?"
   → If they say yes: mark phone_confirmed=true
   → If they give a different number: capture it and confirm

3. **Get Address** - After phone confirmed:
   → "And what's the service address?"
   → After they give it, repeat back to confirm: "Got it, [address]. Is that correct?"

4. **Get Issue** - After address confirmed:
   → "What's going on with your system?"

5. **Get Urgency** - After issue collected:
   → "Is this an emergency for today, something that needs attention in a day or two, or more routine?"
   → Map to: EMERGENCY, URGENT, or ROUTINE

6. **Book Appointment** - When ALL info collected:
   → "We'll get you on the schedule. I have tomorrow morning available, does that work?"
   → When they confirm, complete the booking

## Response Rules

1. Respond with ONE short sentence - this is a phone call
2. Follow the exact order: Name → Phone → Address → Issue → Urgency → Book
3. If caller gives info for a future step, acknowledge it but still collect missing earlier steps
4. Be natural and conversational
5. If caller seems confused, reassure them: "No problem, let me help you with that."

## JSON Response Format

Return ONLY valid JSON:
{{
    "response_text": "Your response (one short sentence)",
    "next_state": "{STATE_COLLECTING_NAME}|{STATE_CONFIRMING_PHONE}|{STATE_COLLECTING_ADDRESS}|{STATE_CONFIRMING_ADDRESS}|{STATE_COLLECTING_ISSUE}|{STATE_COLLECTING_URGENCY}|{STATE_OFFERING_TIMES}|{STATE_BOOKING_COMPLETE}",
    "collected_data": {{
        "name": "string or null",
        "phone": "string or null", 
        "phone_confirmed": true/false,
        "address": "string or null",
        "address_confirmed": true/false,
        "issue": "string or null",
        "urgency": "EMERGENCY|URGENT|ROUTINE or null"
    }},
    "action": null or "book_job"
}}"""


async def get_ai_response(
    user_input: str,
    company_name: str,
    caller_phone: str,
    collected_info: Dict,
    state: str,
    conversation_history: list
) -> Dict[str, Any]:
    """
    Get AI response using OpenAI via Emergent LLM Key.
    Returns structured response with text and state updates.
    """
    from emergentintegrations.llm.chat import chat, Message, Model
    
    system_prompt = get_system_prompt(company_name, caller_phone, collected_info, state)
    
    # Build messages
    messages = [Message(role="system", content=system_prompt)]
    
    # Add conversation history (last 10 exchanges max)
    for msg in conversation_history[-20:]:
        messages.append(Message(role=msg["role"], content=msg["content"]))
    
    # Add current user input
    messages.append(Message(role="user", content=user_input))
    
    try:
        emergent_key = os.environ.get('EMERGENT_LLM_KEY')
        
        response = await chat(
            api_key=emergent_key,
            model=Model.OPENAI_GPT4O_MINI,
            messages=messages,
            temperature=0.7,
            max_tokens=300
        )
        
        response_text = response.message.content.strip()
        logger.info(f"AI raw response: {response_text}")
        
        # Parse JSON response
        try:
            # Handle potential markdown code blocks
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            parsed = json.loads(response_text)
            return {
                "response_text": parsed.get("response_text", "I'm sorry, could you repeat that?"),
                "next_state": parsed.get("next_state", state),
                "collected_data": parsed.get("collected_data", collected_info),
                "action": parsed.get("action")
            }
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse AI JSON: {e}. Raw: {response_text}")
            # Return raw text as response if JSON parsing fails
            return {
                "response_text": response_text if len(response_text) < 200 else "I'm sorry, could you repeat that?",
                "next_state": state,
                "collected_data": collected_info,
                "action": None
            }
            
    except Exception as e:
        logger.error(f"AI response error: {e}")
        return {
            "response_text": "I'm sorry, I'm having trouble understanding. Could you repeat that?",
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
        self.state = STATE_GREETING
        self.collected_info = {
            "name": None,
            "phone": caller_phone,
            "phone_confirmed": False,
            "address": None,
            "address_confirmed": False,
            "issue": None,
            "urgency": None
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
    
    async def handle_interrupt(self, message: Dict) -> None:
        """Handle interruption (caller spoke during TTS)"""
        utterance = message.get("utteranceUntilInterrupt", "")
        duration_ms = message.get("durationUntilInterruptMs", 0)
        logger.info(f"Caller interrupted after {duration_ms}ms. Partial: '{utterance}'")
    
    async def handle_dtmf(self, message: Dict) -> str:
        """Handle DTMF key press"""
        digit = message.get("digit", "")
        logger.info(f"DTMF digit pressed: {digit}")
        
        # Map common DTMF usage
        if digit == "0":
            return "Let me connect you to a live representative. One moment please."
        elif digit == "1":
            return "You pressed one. How can I help you today?"
        
        return None
    
    async def handle_error(self, message: Dict) -> None:
        """Handle error from ConversationRelay"""
        description = message.get("description", "Unknown error")
        logger.error(f"ConversationRelay error: {description}")
    
    async def handle_end(self) -> None:
        """Handle call end - save summary"""
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
        
        lead = {
            "id": lead_id,
            "tenant_id": self.tenant["id"],
            "source": "AI_PHONE",
            "channel": "VOICE",
            "status": "NEW",
            "caller_name": self.collected_info.get("name"),
            "caller_phone": self.collected_info.get("phone") or self.caller_phone,
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
        
        # Default to tomorrow morning 9-12
        from datetime import timedelta
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        window_start = tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
        window_end = tomorrow.replace(hour=12, minute=0, second=0, microsecond=0)
        
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
            "notes": f"Booked via AI phone assistant. Urgency: {self.collected_info.get('urgency', 'ROUTINE')}",
            "service_window_start": window_start.isoformat(),
            "service_window_end": window_end.isoformat(),
            "tags": ["voice_ai_booking"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        await self.db.jobs.insert_one(job)
        logger.info(f"Created job {job_id} from voice booking")
        
        # Send SMS confirmation
        phone = self.collected_info.get("phone") or self.caller_phone
        if phone:
            date_str = window_start.strftime("%A, %B %d")
            time_str = "9 AM - 12 PM"
            
            sms_msg = f"Hi {self.collected_info.get('name', 'there')}! Your appointment with {self.company_name} is confirmed for {date_str}, {time_str}. We'll text you when our tech is on the way!"
            
            try:
                await twilio_service.send_sms(to_phone=phone, body=sms_msg)
                logger.info(f"Sent booking confirmation SMS to {phone}")
            except Exception as e:
                logger.error(f"Failed to send SMS confirmation: {e}")
    
    async def _find_or_create_customer(self) -> Optional[Dict]:
        """Find existing customer or create new one"""
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
        
        # Create new customer
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
