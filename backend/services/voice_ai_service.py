"""
Self-Hosted Voice AI Service

Replaces Vapi with a custom solution using:
- Twilio Voice for call handling
- OpenAI Whisper for speech-to-text
- OpenAI TTS for text-to-speech
- OpenAI GPT-4o for conversation logic

Cost comparison (per 3000 minutes/month):
- Vapi: ~$450/month
- Self-hosted: ~$150/month (70% savings)
"""
import os
import json
import base64
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from io import BytesIO

logger = logging.getLogger(__name__)

# Voice AI System Prompt
VOICE_AI_SYSTEM_PROMPT = """You are a friendly and professional AI phone receptionist for {company_name}.

CONTEXT:
- Company: {company_name}
- Caller Phone: {caller_phone}
- Current Time: {current_time}
- Known Customer: {is_known_customer}
{customer_context}

YOUR GOALS:
1. Greet the caller warmly
2. Understand their service needs
3. Collect necessary information (name, phone, address if needed)
4. Determine urgency level
5. Book a service appointment OR take a message

CONVERSATION RULES:
- Keep responses SHORT (1-2 sentences max) - this is a phone call
- Be conversational and natural
- Speak clearly and at a moderate pace
- Confirm important details by repeating them back
- Ask ONE question at a time

AVAILABLE SERVICES:
{service_types}

BUSINESS HOURS: {business_hours}

SERVICE WINDOWS:
- Morning: 8 AM - 12 PM
- Afternoon: 12 PM - 4 PM
- Evening: 4 PM - 7 PM

TOOL CALLING:
When you have collected enough information, call the appropriate function:
- create_lead: When you have name, phone, issue description
- check_availability: When customer asks about appointment times
- book_job: When customer confirms a time slot
- end_call: When conversation is complete

Be helpful, efficient, and professional. If the customer is frustrated, be empathetic."""


class VoiceAIService:
    """
    Self-hosted Voice AI service using OpenAI APIs.
    
    Flow:
    1. Twilio receives inbound call
    2. Twilio streams audio via WebSocket
    3. This service processes audio chunks through Whisper (STT)
    4. GPT-4o generates responses with tool calling
    5. TTS converts response to speech
    6. Audio sent back to Twilio/caller
    """
    
    def __init__(self, db_client=None):
        self.api_key = os.environ.get('OPENAI_API_KEY')
        self.db = db_client
        self.conversation_history: List[Dict] = []
        self.tenant: Optional[Dict] = None
        self.customer: Optional[Dict] = None
        self.lead: Optional[Dict] = None
        self.call_sid: Optional[str] = None
        self.audio_buffer = b""
        self.stream_sid: Optional[str] = None
        self.is_processing = False
        self.silence_threshold = 0.5  # seconds of silence to detect end of speech
        self.last_audio_time = datetime.now(timezone.utc)
        
    async def initialize(self, tenant_id: str, from_phone: str, call_sid: str, db):
        """Initialize conversation context for a new call"""
        self.db = db
        self.call_sid = call_sid
        
        # Load tenant
        self.tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
        if not self.tenant:
            logger.error(f"Tenant not found: {tenant_id}")
            return False
        
        # Normalize phone number
        from_phone = self._normalize_phone(from_phone)
        
        # Try to find existing customer
        self.customer = await db.customers.find_one(
            {"phone": from_phone, "tenant_id": tenant_id},
            {"_id": 0}
        )
        
        # Build conversation context
        self.conversation_history = []
        
        logger.info(f"Voice AI initialized for tenant {tenant_id}, call {call_sid}")
        return True
    
    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone to E.164 format"""
        if not phone:
            return ""
        digits = ''.join(c for c in phone if c.isdigit())
        if phone.startswith('+1') and len(digits) == 11 and digits.startswith('1'):
            return '+' + digits
        if len(digits) == 10:
            digits = '1' + digits
        elif len(digits) == 11 and digits.startswith('1'):
            pass
        return '+' + digits if digits else ""
    
    def _get_system_prompt(self) -> str:
        """Build system prompt with context"""
        import pytz
        tenant_tz = pytz.timezone(self.tenant.get("timezone", "America/New_York"))
        current_time = datetime.now(tenant_tz).strftime("%A, %B %d, %Y at %I:%M %p")
        
        customer_context = ""
        if self.customer:
            customer_context = f"""
KNOWN CUSTOMER INFO:
- Name: {self.customer.get('first_name', '')} {self.customer.get('last_name', '')}
- Phone: {self.customer.get('phone', '')}
- Previous customer: Yes
"""
        
        service_types = """
- DIAGNOSTIC ($89): Initial inspection to diagnose the problem
- REPAIR ($250): Fix a known issue
- MAINTENANCE ($149): Regular maintenance/tune-up
- INSTALL ($1500): New equipment installation
"""
        
        business_hours = "Monday-Saturday 8 AM - 7 PM"
        
        return VOICE_AI_SYSTEM_PROMPT.format(
            company_name=self.tenant.get("name", "Our Company"),
            caller_phone=self.customer.get("phone", "Unknown") if self.customer else "New Caller",
            current_time=current_time,
            is_known_customer="Yes" if self.customer else "No",
            customer_context=customer_context,
            service_types=service_types,
            business_hours=business_hours
        )
    
    async def get_greeting(self) -> str:
        """Generate initial greeting for caller"""
        if self.customer:
            greeting = f"Hi {self.customer.get('first_name', 'there')}! Thanks for calling {self.tenant.get('name')}. How can I help you today?"
        else:
            greeting = f"Thank you for calling {self.tenant.get('name')}. How can I help you today?"
        
        return await self._text_to_speech(greeting)
    
    async def process_audio(self, audio_chunk: bytes) -> Optional[str]:
        """
        Process incoming audio chunk.
        Accumulates audio and detects end of speech.
        Returns transcript when speech ends, None otherwise.
        """
        self.audio_buffer += audio_chunk
        self.last_audio_time = datetime.now(timezone.utc)
        
        # Simple silence detection based on buffer size and time
        # In production, use VAD (Voice Activity Detection)
        if len(self.audio_buffer) > 16000:  # ~1 second of audio at 16kHz
            # Check if we should process
            if await self._detect_end_of_speech():
                transcript = await self._transcribe_audio()
                self.audio_buffer = b""
                return transcript
        
        return None
    
    async def _detect_end_of_speech(self) -> bool:
        """
        Detect if the speaker has finished talking.
        Uses a simple time-based approach. In production, use WebRTC VAD.
        """
        # For now, process after accumulating enough audio
        # This is a simplified version - real implementation would use VAD
        return len(self.audio_buffer) >= 32000  # ~2 seconds
    
    async def _transcribe_audio(self) -> Optional[str]:
        """Transcribe audio buffer using OpenAI Whisper"""
        if not self.audio_buffer:
            return None
        
        try:
            # Use OpenAI directly
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=self.api_key)
            
            audio_file = BytesIO(self.audio_buffer)
            audio_file.name = "audio.wav"
            
            transcript = await client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
            return transcript.text
                
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return None
    
    async def generate_response(self, user_message: str) -> tuple[str, Optional[Dict]]:
        """
        Generate AI response to user message.
        Returns tuple of (audio_base64, action_data).
        """
        if not user_message:
            return await self._text_to_speech("I'm sorry, I didn't catch that. Could you repeat?"), None
        
        # Add to conversation history
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        try:
            # Get available tools
            tools = self._get_available_tools()
            response_text, action_data = await self._generate_with_openai(tools)
            
            # Add response to history
            self.conversation_history.append({
                "role": "assistant",
                "content": response_text
            })
            
            # Convert to speech
            audio = await self._text_to_speech(response_text)
            
            return audio, action_data
            
        except Exception as e:
            logger.error(f"Response generation error: {e}")
            fallback = "I apologize, I'm having technical difficulties. Let me transfer you to a team member."
            return await self._text_to_speech(fallback), {"action": "transfer"}
    
    async def _generate_with_openai(self, tools: List[Dict]) -> tuple[str, Optional[Dict]]:
        """Generate response using OpenAI directly with function calling"""
        import openai
        client = openai.AsyncOpenAI(api_key=self.api_key)
        
        messages = [
            {"role": "system", "content": self._get_system_prompt()},
            *self.conversation_history
        ]
        
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=tools,
            tool_choice="auto",
            max_tokens=150
        )
        
        assistant_message = response.choices[0].message
        
        # Handle tool calls
        action_data = None
        if assistant_message.tool_calls:
            action_data = await self._execute_tools(assistant_message.tool_calls)
            
            # Get follow-up response after tool execution
            messages.append(assistant_message.model_dump())
            for tool_call in assistant_message.tool_calls:
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(action_data or {})
                })
            
            follow_up = await client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                max_tokens=150
            )
            return follow_up.choices[0].message.content, action_data
        
        return assistant_message.content, action_data
    
    def _parse_action(self, response: str) -> Optional[Dict]:
        """Parse action from AI response"""
        # Check for JSON in response
        if "{" in response and "}" in response:
            try:
                start = response.index("{")
                end = response.rindex("}") + 1
                json_str = response[start:end]
                data = json.loads(json_str)
                if "action" in data:
                    return data
            except (json.JSONDecodeError, ValueError):
                pass
        return None
    
    async def _execute_tools(self, tool_calls) -> Optional[Dict]:
        """Execute tool calls from the AI"""
        results = {}
        
        for tool_call in tool_calls:
            func_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            
            if func_name == "create_lead":
                result = await self._create_lead(args)
                results["action"] = "lead_created"
                results["lead_id"] = result.get("id")
                
            elif func_name == "check_availability":
                result = await self._check_availability(args)
                results["action"] = "availability_checked"
                results["slots"] = result
                
            elif func_name == "book_job":
                result = await self._book_job(args)
                results["action"] = "job_booked"
                results["job_id"] = result.get("id")
                
            elif func_name == "end_call":
                results["action"] = "end_call"
                results["reason"] = args.get("reason", "completed")
        
        return results if results else None
    
    async def _create_lead(self, args: Dict) -> Dict:
        """Create a lead from call data"""
        from uuid import uuid4
        
        lead_data = {
            "id": str(uuid4()),
            "tenant_id": self.tenant["id"],
            "source": "SELF_HOSTED_VOICE",
            "channel": "VOICE",
            "status": "NEW",
            "caller_name": args.get("name", ""),
            "caller_phone": args.get("phone", self.customer.get("phone") if self.customer else ""),
            "issue_type": args.get("issue_type", ""),
            "description": args.get("description", ""),
            "urgency": args.get("urgency", "ROUTINE"),
            "tags": ["voice_ai"],
            "first_contact_at": datetime.now(timezone.utc).isoformat(),
            "last_activity_at": datetime.now(timezone.utc).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Create customer if new
        if not self.customer and args.get("name"):
            customer_data = {
                "id": str(uuid4()),
                "tenant_id": self.tenant["id"],
                "first_name": args.get("name", "").split()[0] if args.get("name") else "",
                "last_name": " ".join(args.get("name", "").split()[1:]) if args.get("name") else "",
                "phone": self._normalize_phone(args.get("phone", "")),
                "preferred_channel": "CALL",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            await self.db.customers.insert_one(customer_data)
            self.customer = customer_data
            lead_data["customer_id"] = customer_data["id"]
        elif self.customer:
            lead_data["customer_id"] = self.customer["id"]
        
        await self.db.leads.insert_one(lead_data)
        self.lead = lead_data
        
        return lead_data
    
    async def _check_availability(self, args: Dict) -> List[Dict]:
        """Check available appointment slots"""
        import pytz
        
        date_str = args.get("date")
        tenant_tz = pytz.timezone(self.tenant.get("timezone", "America/New_York"))
        
        if not date_str:
            # Default to tomorrow
            tomorrow = datetime.now(tenant_tz) + timedelta(days=1)
            date_str = tomorrow.strftime("%Y-%m-%d")
        
        # Get existing jobs for the date
        start_of_day = f"{date_str}T00:00:00"
        end_of_day = f"{date_str}T23:59:59"
        
        existing_jobs = await self.db.jobs.find({
            "tenant_id": self.tenant["id"],
            "status": {"$in": ["BOOKED", "EN_ROUTE", "ON_SITE"]},
            "service_window_start": {"$gte": start_of_day, "$lte": end_of_day}
        }, {"_id": 0, "service_window_start": 1, "service_window_end": 1}).to_list(100)
        
        # Define time slots
        slots = [
            {"slot": "morning", "start": "08:00", "end": "12:00", "available": True},
            {"slot": "afternoon", "start": "12:00", "end": "16:00", "available": True},
            {"slot": "evening", "start": "16:00", "end": "19:00", "available": True}
        ]
        
        # Mark unavailable slots (simplified - in production, check capacity)
        for job in existing_jobs:
            job_start = job.get("service_window_start", "")
            if "T08" in job_start or "T09" in job_start or "T10" in job_start or "T11" in job_start:
                slots[0]["available"] = False
            elif "T12" in job_start or "T13" in job_start or "T14" in job_start or "T15" in job_start:
                slots[1]["available"] = False
            elif "T16" in job_start or "T17" in job_start or "T18" in job_start:
                slots[2]["available"] = False
        
        return [s for s in slots if s["available"]]
    
    async def _book_job(self, args: Dict) -> Dict:
        """Book a service appointment"""
        from uuid import uuid4
        import pytz
        
        tenant_tz = pytz.timezone(self.tenant.get("timezone", "America/New_York"))
        
        date_str = args.get("date")
        time_slot = args.get("time_slot", "morning")
        job_type = args.get("job_type", "DIAGNOSTIC").upper()
        
        if not date_str:
            tomorrow = datetime.now(tenant_tz) + timedelta(days=1)
            date_str = tomorrow.strftime("%Y-%m-%d")
        
        # Determine time window
        slot_times = {
            "morning": ("08:00", "12:00"),
            "afternoon": ("12:00", "16:00"),
            "evening": ("16:00", "19:00")
        }
        start_time, end_time = slot_times.get(time_slot, ("08:00", "12:00"))
        
        service_window_start = tenant_tz.localize(
            datetime.strptime(f"{date_str} {start_time}", "%Y-%m-%d %H:%M")
        )
        service_window_end = tenant_tz.localize(
            datetime.strptime(f"{date_str} {end_time}", "%Y-%m-%d %H:%M")
        )
        
        # Get or create property
        property_id = None
        if self.customer:
            prop = await self.db.properties.find_one(
                {"customer_id": self.customer["id"]},
                {"_id": 0, "id": 1}
            )
            if prop:
                property_id = prop["id"]
            elif args.get("address"):
                # Create property
                prop_data = {
                    "id": str(uuid4()),
                    "tenant_id": self.tenant["id"],
                    "customer_id": self.customer["id"],
                    "address_line1": args.get("address", ""),
                    "city": args.get("city", ""),
                    "state": args.get("state", ""),
                    "postal_code": args.get("zip", ""),
                    "property_type": "RESIDENTIAL",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                await self.db.properties.insert_one(prop_data)
                property_id = prop_data["id"]
        
        # Calculate quote
        urgency = self.lead.get("urgency", "ROUTINE") if self.lead else "ROUTINE"
        base_prices = {"DIAGNOSTIC": 89, "REPAIR": 250, "MAINTENANCE": 149, "INSTALL": 1500, "INSTALLATION": 1500}
        urgency_mult = {"EMERGENCY": 1.5, "URGENT": 1.25, "ROUTINE": 1.0}
        quote_amount = base_prices.get(job_type, 150) * urgency_mult.get(urgency, 1.0)
        
        job_data = {
            "id": str(uuid4()),
            "tenant_id": self.tenant["id"],
            "customer_id": self.customer["id"] if self.customer else None,
            "property_id": property_id,
            "lead_id": self.lead["id"] if self.lead else None,
            "job_type": job_type,
            "priority": "EMERGENCY" if urgency == "EMERGENCY" else ("HIGH" if urgency == "URGENT" else "NORMAL"),
            "service_window_start": service_window_start.isoformat(),
            "service_window_end": service_window_end.isoformat(),
            "status": "BOOKED",
            "created_by": "AI",
            "notes": args.get("notes", ""),
            "quote_amount": round(quote_amount, 2),
            "reminder_day_before_sent": False,
            "reminder_morning_of_sent": False,
            "en_route_sms_sent": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        await self.db.jobs.insert_one(job_data)
        
        # Update lead status
        if self.lead:
            await self.db.leads.update_one(
                {"id": self.lead["id"]},
                {"$set": {"status": "JOB_BOOKED", "updated_at": datetime.now(timezone.utc).isoformat()}}
            )
        
        return job_data
    
    async def _text_to_speech(self, text: str) -> str:
        """Convert text to speech using OpenAI TTS"""
        if not text:
            return ""
        
        try:
            if self.use_emergent:
                # Use emergent integrations
                from emergentintegrations.llm.tts import text_to_speech
                
                audio_bytes = await text_to_speech(
                    api_key=self.api_key,
                    text=text,
                    model="tts-1",
                    voice="alloy"
                )
                return base64.b64encode(audio_bytes).decode()
            else:
                # Use OpenAI directly
                import openai
                client = openai.AsyncOpenAI(api_key=self.api_key)
                
                response = await client.audio.speech.create(
                    model="tts-1",
                    voice="alloy",
                    input=text,
                    response_format="pcm"  # Raw PCM for Twilio
                )
                
                audio_bytes = response.content
                return base64.b64encode(audio_bytes).decode()
                
        except Exception as e:
            logger.error(f"TTS error: {e}")
            return ""
    
    def _get_available_tools(self) -> List[Dict]:
        """Define available function tools for GPT"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "create_lead",
                    "description": "Create a new lead/customer in the system when you have collected their information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Customer's full name"},
                            "phone": {"type": "string", "description": "Customer's phone number"},
                            "issue_type": {"type": "string", "description": "Brief description of the issue"},
                            "description": {"type": "string", "description": "Detailed description of the problem"},
                            "urgency": {
                                "type": "string",
                                "enum": ["EMERGENCY", "URGENT", "ROUTINE"],
                                "description": "How urgent is the service needed"
                            }
                        },
                        "required": ["name", "issue_type", "urgency"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "check_availability",
                    "description": "Check available appointment slots for a specific date",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "date": {
                                "type": "string",
                                "description": "Date to check in YYYY-MM-DD format"
                            }
                        },
                        "required": ["date"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "book_job",
                    "description": "Book a service appointment when customer confirms a time",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "date": {"type": "string", "description": "Appointment date YYYY-MM-DD"},
                            "time_slot": {
                                "type": "string",
                                "enum": ["morning", "afternoon", "evening"],
                                "description": "Preferred time slot"
                            },
                            "job_type": {
                                "type": "string",
                                "enum": ["DIAGNOSTIC", "REPAIR", "MAINTENANCE", "INSTALL"],
                                "description": "Type of service needed"
                            },
                            "address": {"type": "string", "description": "Service address if new customer"},
                            "notes": {"type": "string", "description": "Any additional notes"}
                        },
                        "required": ["date", "time_slot", "job_type"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "end_call",
                    "description": "End the call when conversation is complete",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "reason": {
                                "type": "string",
                                "enum": ["completed", "customer_request", "no_response", "transfer"],
                                "description": "Reason for ending the call"
                            },
                            "summary": {"type": "string", "description": "Brief summary of the call"}
                        },
                        "required": ["reason"]
                    }
                }
            }
        ]
    
    async def end_conversation(self):
        """Clean up after call ends"""
        # Store call summary
        if self.lead and self.conversation_history:
            summary = " | ".join([
                f"{msg['role']}: {msg['content'][:100]}"
                for msg in self.conversation_history[-5:]
            ])
            
            await self.db.leads.update_one(
                {"id": self.lead["id"]},
                {"$set": {
                    "description": f"Voice AI Call Summary: {summary}",
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }}
            )
        
        logger.info(f"Voice AI conversation ended for call {self.call_sid}")


# Singleton-style factory
def create_voice_ai_service(db_client=None):
    """Create a new VoiceAIService instance"""
    return VoiceAIService(db_client)
