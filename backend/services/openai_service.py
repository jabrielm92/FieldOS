"""
OpenAI Service - Handles AI-powered SMS generation
"""
import os
import logging
from typing import List, Dict, Optional
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class OpenAIService:
    def __init__(self):
        self.api_key = os.environ.get('OPENAI_API_KEY')
        self.model = "gpt-4o-mini"
        self.client = None
        
        if self.api_key:
            try:
                self.client = OpenAI(api_key=self.api_key)
                logger.info("OpenAI client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
    
    def is_configured(self) -> bool:
        """Check if OpenAI is properly configured"""
        return self.client is not None
    
    async def generate_sms_reply(
        self,
        tenant_name: str,
        tenant_timezone: str,
        tone_profile: str,
        customer_name: str,
        conversation_history: List[Dict],
        current_message: str,
        context_type: str = "GENERAL"
    ) -> str:
        """
        Generate an AI-powered SMS reply
        
        Args:
            tenant_name: Name of the field service company
            tenant_timezone: Timezone for scheduling context
            tone_profile: PROFESSIONAL, FRIENDLY, or BLUE_COLLAR_DIRECT
            customer_name: Customer's name for personalization
            conversation_history: List of previous messages
            current_message: The inbound message to respond to
            context_type: INBOUND_LEAD, RESCHEDULE_REQUEST, GENERAL, etc.
        
        Returns:
            Generated SMS text (max 320 chars)
        """
        if not self.is_configured():
            logger.warning("OpenAI not configured - returning fallback message")
            return self._get_fallback_message(context_type)
        
        try:
            system_prompt = self._build_system_prompt(
                tenant_name, tenant_timezone, tone_profile, context_type
            )
            
            # Build conversation context
            context_text = self._format_conversation_history(conversation_history)
            
            user_message = f"""Previous conversation:
{context_text}

Latest customer message: "{current_message}"

Generate a helpful SMS reply (max 320 characters). Be direct and action-oriented."""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=150,
                temperature=0.7
            )
            
            reply = response.choices[0].message.content.strip()
            
            # Ensure response is within character limit
            if len(reply) > 320:
                reply = reply[:317] + "..."
            
            logger.info(f"AI SMS generated successfully for {customer_name}")
            return reply
            
        except Exception as e:
            logger.error(f"Error generating AI SMS: {e}")
            return self._get_fallback_message(context_type)
    
    def _build_system_prompt(
        self,
        tenant_name: str,
        timezone: str,
        tone_profile: str,
        context_type: str
    ) -> str:
        """Build the system prompt for SMS generation"""
        
        tone_instructions = {
            "PROFESSIONAL": "Use formal, courteous language. Be respectful and thorough.",
            "FRIENDLY": "Be warm and conversational. Use friendly but professional language.",
            "BLUE_COLLAR_DIRECT": "Be straightforward and no-nonsense. Cut to the chase. Use simple language."
        }
        
        tone = tone_instructions.get(tone_profile, tone_instructions["PROFESSIONAL"])
        
        context_instructions = {
            "INBOUND_LEAD": "This is a new potential customer. Collect key info: issue type, urgency, and offer to schedule a visit.",
            "RESCHEDULE_REQUEST": "The customer wants to reschedule. Be helpful and offer alternative times.",
            "GENERAL": "Respond helpfully to their question or request.",
            "FOLLOW_UP": "This is a follow-up. Check if they need any further assistance."
        }
        
        context = context_instructions.get(context_type, context_instructions["GENERAL"])
        
        return f"""You are an SMS coordinator for {tenant_name}, a field service company.

TONE: {tone}

CONTEXT: {context}

RULES:
1. Keep messages under 320 characters
2. Never mention you are AI
3. Never give technical repair instructions or safety-critical advice
4. For emergencies: tell them to contact 911 if life/safety is at risk, then collect info
5. Steer toward booking a service visit when appropriate
6. Use timezone {timezone} for any time references
7. Be concise - every word counts in SMS
8. End with a clear next step or question when appropriate"""
    
    def _format_conversation_history(self, history: List[Dict]) -> str:
        """Format conversation history for the prompt"""
        if not history:
            return "(No previous messages)"
        
        formatted = []
        for msg in history[-10:]:  # Last 10 messages
            sender = "Customer" if msg.get("sender_type") == "CUSTOMER" else "Assistant"
            content = msg.get("content", "")
            formatted.append(f"{sender}: {content}")
        
        return "\n".join(formatted)
    
    def _get_fallback_message(self, context_type: str) -> str:
        """Return a fallback message when AI is unavailable"""
        fallbacks = {
            "INBOUND_LEAD": "Thanks for reaching out! A team member will contact you shortly to discuss your service needs.",
            "RESCHEDULE_REQUEST": "We received your request. A team member will reach out soon to help reschedule.",
            "GENERAL": "Thanks for your message. A team member will review and respond shortly.",
            "FOLLOW_UP": "Thanks for getting back to us. We'll follow up with you soon."
        }
        return fallbacks.get(context_type, fallbacks["GENERAL"])


# Singleton instance
openai_service = OpenAIService()
