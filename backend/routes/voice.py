"""
Voice AI routes for FieldOS.

This module contains the same voice route implementations that exist in server.py.
It is populated here for future use when server.py is refactored into proper modules.

NOTE: The live routes are currently served by server.py. The WebSocket endpoints
(voice_ws, voice_stream_websocket) must be registered directly on the FastAPI `app`
instance (not on a router) due to Starlette/FastAPI WebSocket routing constraints,
which is why they remain on `app` in server.py.

Usage (future):
    from routes.voice import router as voice_router
    app.include_router(voice_router, prefix="/api/v1")
"""
import os
import json
import base64
import logging
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice", tags=["voice"])


# ---------------------------------------------------------------------------
# Helper utilities (duplicated from server.py for self-contained module)
# ---------------------------------------------------------------------------

def _calculate_quote_amount(job_type: str, urgency: str = None) -> float:
    """Calculate quote amount based on job type and urgency."""
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
    base = base_prices.get(job_type, 150.00)
    multiplier = urgency_multipliers.get(urgency, 1.0)
    return round(base * multiplier, 2)


def _normalize_phone_e164(phone: str) -> str:
    """Normalize phone number to E.164 format (+1XXXXXXXXXX)."""
    if not phone:
        return ""
    digits = "".join(c for c in phone if c.isdigit())
    if phone.startswith("+1") and len(digits) == 11 and digits.startswith("1"):
        return "+" + digits
    if len(digits) == 10:
        digits = "1" + digits
    elif len(digits) == 11 and digits.startswith("1"):
        pass
    else:
        return "+" + digits if digits else ""
    return "+" + digits


# ---------------------------------------------------------------------------
# Module-level db placeholder – will be injected at startup in a future
# refactor.  For now, routes in server.py use the `db` defined there.
# ---------------------------------------------------------------------------
db = None  # type: ignore  # Will be set by app startup in future refactor


# ---------------------------------------------------------------------------
# HTTP Routes
# ---------------------------------------------------------------------------

@router.post("/inbound")
async def voice_inbound(request: Request):
    """
    Handle inbound voice call from Twilio.
    Returns TwiML with ConversationRelay for real-time WebSocket streaming.

    ConversationRelay provides:
    - Real-time speech-to-text (STT) via Deepgram
    - Text-to-speech (TTS) via ElevenLabs (default) or others
    - Low-latency bidirectional WebSocket communication
    """
    form_data = await request.form()
    call_sid = form_data.get("CallSid", "")
    from_phone = form_data.get("From", "").strip()
    to_phone = form_data.get("To", "").strip()

    if from_phone and not from_phone.startswith("+"):
        from_phone = "+" + from_phone.lstrip()
    if to_phone and not to_phone.startswith("+"):
        to_phone = "+" + to_phone.lstrip()

    logger.info(f"Inbound voice call: {call_sid} from {from_phone} to {to_phone}")

    # Find tenant by phone number
    tenant = await db.tenants.find_one({"twilio_phone_number": to_phone}, {"_id": 0})

    if not tenant:
        to_phone_digits = "".join(c for c in to_phone if c.isdigit())
        tenant = await db.tenants.find_one(
            {
                "$or": [
                    {"twilio_phone_number": to_phone},
                    {"twilio_phone_number": f"+{to_phone_digits}"},
                    {"twilio_phone_number": to_phone_digits},
                    {"twilio_phone_number": f"+1{to_phone_digits[-10:]}"}
                    if len(to_phone_digits) >= 10
                    else {"twilio_phone_number": "NOMATCH"},
                ]
            },
            {"_id": 0},
        )

    if not tenant:
        logger.warning(f"No tenant found for phone number: {to_phone}")
        twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>We're sorry, this number is not configured.</Say>
    <Hangup/>
</Response>"""
        return Response(content=twiml, media_type="application/xml")

    # Get the backend URL and construct WebSocket URL
    base_url = os.environ.get("BACKEND_URL", os.environ.get("APP_BASE_URL", ""))

    if base_url.startswith("https://"):
        ws_url = base_url.replace("https://", "wss://")
    elif base_url.startswith("http://"):
        ws_url = base_url.replace("http://", "ws://")
    else:
        ws_url = f"wss://{base_url}"

    ws_endpoint = f"{ws_url}/api/v1/voice/ws/{call_sid}"

    # Check if OpenAI key is configured (required for Voice AI)
    has_openai = os.environ.get("OPENAI_API_KEY")

    if not has_openai:
        logger.warning("No OPENAI_API_KEY environment variable set")
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">Thank you for calling {tenant.get('name', 'us')}. Please leave a message after the beep.</Say>
    <Record maxLength="120" action="{base_url}/api/v1/voice/recording-complete" />
</Response>"""
        return Response(content=twiml, media_type="application/xml")

    if not tenant.get("voice_system_prompt"):
        logger.warning(f"No voice system prompt configured for tenant {tenant.get('id')}")
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">Thank you for calling {tenant.get('name', 'us')}. Please leave a message after the beep.</Say>
    <Record maxLength="120" action="{base_url}/api/v1/voice/recording-complete" />
</Response>"""
        return Response(content=twiml, media_type="application/xml")

    # Store call context for conversation
    await db.voice_calls.update_one(
        {"call_sid": call_sid},
        {
            "$set": {
                "call_sid": call_sid,
                "tenant_id": tenant["id"],
                "from_phone": from_phone,
                "to_phone": to_phone,
                "tenant_name": tenant.get("name", "our company"),
                "conversation_state": "greeting",
                "collected_info": {},
                "conversation_history": [],
                "started_at": datetime.now(timezone.utc).isoformat(),
            }
        },
        upsert=True,
    )

    # Get welcome greeting
    welcome = (
        tenant.get("voice_greeting")
        or f"Hi, thanks for calling {tenant.get('name', 'us')}. How can I help you today?"
    )

    # Escape XML special characters in welcome message
    welcome = (
        welcome.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )

    # Get voice provider settings
    voice_provider = tenant.get("voice_provider", "elevenlabs").lower()

    if voice_provider == "elevenlabs":
        tts_provider = "ElevenLabs"
        voice = tenant.get("elevenlabs_voice_id") or "UgBBYS2sOqTuMpoF3BR0"
    elif voice_provider == "amazon":
        tts_provider = "Amazon"
        voice = tenant.get("voice_name") or "Joanna-Neural"
    else:
        tts_provider = "Google"
        voice = tenant.get("voice_name") or "en-US-Journey-O"

    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect action="{base_url}/api/v1/voice/connect-complete">
        <ConversationRelay
            url="{ws_endpoint}"
            welcomeGreeting="{welcome}"
            welcomeGreetingInterruptible="any"
            language="en-US"
            ttsProvider="{tts_provider}"
            voice="{voice}"
            transcriptionProvider="Deepgram"
            speechModel="nova-3-general"
            interruptible="any"
            dtmfDetection="true"
        >
            <Parameter name="tenant_id" value="{tenant['id']}"/>
            <Parameter name="tenant_name" value="{tenant.get('name', 'Company')}"/>
            <Parameter name="caller_phone" value="{from_phone}"/>
        </ConversationRelay>
    </Connect>
</Response>"""

    logger.info(f"Voice AI (ConversationRelay) started for tenant {tenant['id']}, call {call_sid}")
    logger.info(f"WebSocket endpoint: {ws_endpoint}")
    return Response(content=twiml, media_type="application/xml")


@router.post("/connect-complete")
async def voice_connect_complete(request: Request):
    """
    Called by Twilio when the <Connect> verb completes (ConversationRelay session ends).
    This is the action URL for the Connect verb.
    """
    form_data = await request.form()
    call_sid = form_data.get("CallSid", "")
    session_id = form_data.get("SessionId", "")
    session_status = form_data.get("SessionStatus", "")
    session_duration = form_data.get("SessionDuration", "0")
    handoff_data = form_data.get("HandoffData", "")
    error_code = form_data.get("ErrorCode", "")
    error_message = form_data.get("ErrorMessage", "")

    logger.info(f"ConversationRelay session ended: {call_sid}")
    logger.info(f"  Session: {session_id}, Status: {session_status}, Duration: {session_duration}s")

    if error_code:
        logger.error(f"  Error: {error_code} - {error_message}")

    if handoff_data:
        logger.info(f"  Handoff data: {handoff_data}")

    await db.voice_calls.update_one(
        {"call_sid": call_sid},
        {
            "$set": {
                "session_id": session_id,
                "session_status": session_status,
                "session_duration_seconds": int(session_duration) if session_duration else 0,
                "handoff_data": handoff_data,
                "error_code": error_code if error_code else None,
                "error_message": error_message if error_message else None,
                "ended_at": datetime.now(timezone.utc).isoformat(),
            }
        },
    )

    twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">Thank you for calling. Goodbye!</Say>
    <Hangup/>
</Response>"""
    return Response(content=twiml, media_type="application/xml")


@router.get("/audio/{audio_id}")
async def get_voice_audio(audio_id: str):
    """
    Serve ElevenLabs-generated audio for Twilio to play.
    Generates audio on-demand and streams it.
    """
    from starlette.responses import StreamingResponse  # noqa: F401
    from services.elevenlabs_service import elevenlabs_service

    audio_doc = await db.voice_audio.find_one({"audio_id": audio_id}, {"_id": 0})

    if not audio_doc or not audio_doc.get("text"):
        logger.error(f"No audio text found for ID: {audio_id}")
        return Response(content=b"", media_type="audio/mpeg")

    text = audio_doc["text"]

    audio_data = elevenlabs_service.text_to_speech(
        text=text,
        voice="roger",
        stability=0.5,
        similarity_boost=0.75,
    )

    if not audio_data:
        logger.error(f"Failed to generate audio for: {text}")
        return Response(content=b"", media_type="audio/mpeg")

    logger.info(f"Serving {len(audio_data)} bytes of ElevenLabs audio for: {text[:50]}...")

    return Response(
        content=audio_data,
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": f"inline; filename={audio_id}.mp3",
            "Cache-Control": "public, max-age=3600",
        },
    )


@router.post("/recording-complete")
async def voice_recording_complete(request: Request):
    """Handle completed voice recording (fallback when self-hosted not enabled)."""
    form_data = await request.form()
    recording_url = form_data.get("RecordingUrl", "")
    call_sid = form_data.get("CallSid", "")
    from_phone = form_data.get("From", "")
    to_phone = form_data.get("To", "")

    logger.info(f"Voice recording complete: {call_sid}, recording: {recording_url}")

    tenant = await db.tenants.find_one(
        {
            "$or": [
                {"twilio_phone_number": to_phone},
                {"twilio_phone_number": to_phone.replace("+", "")},
            ]
        },
        {"_id": 0},
    )

    if tenant and recording_url:
        from_phone_normalized = _normalize_phone_e164(from_phone)

        lead = {
            "id": str(uuid4()),
            "tenant_id": tenant["id"],
            "source": "MISSED_CALL_SMS",
            "channel": "VOICE",
            "status": "NEW",
            "caller_phone": from_phone_normalized,
            "description": f"Voicemail recording: {recording_url}",
            "urgency": "ROUTINE",
            "tags": ["voicemail"],
            "first_contact_at": datetime.now(timezone.utc).isoformat(),
            "last_activity_at": datetime.now(timezone.utc).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.leads.insert_one(lead)

        from services.twilio_service import twilio_service

        sms_msg = (
            f"Hi! Thanks for calling {tenant.get('name')}. "
            f"We received your voicemail and will call you back shortly."
        )
        await twilio_service.send_sms(to_phone=from_phone_normalized, body=sms_msg)

    twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Thank you for your message. We will call you back shortly. Goodbye!</Say>
    <Hangup/>
</Response>"""
    return Response(content=twiml, media_type="application/xml")


@router.post("/process-speech")
async def voice_process_speech(request: Request):
    """
    Process speech input from caller and generate AI response.
    Uses the professional receptionist prompt for natural conversation.
    """
    form_data = await request.form()
    call_sid = form_data.get("CallSid", "")
    speech_result = form_data.get("SpeechResult", "")
    from_phone = form_data.get("From", "").strip()

    if from_phone and not from_phone.startswith("+"):
        from_phone = "+" + from_phone.lstrip()

    logger.info(f"Voice AI processing: '{speech_result}' from {from_phone}")

    base_url = os.environ.get("BACKEND_URL", os.environ.get("APP_BASE_URL", ""))

    call_context = await db.voice_calls.find_one({"call_sid": call_sid}, {"_id": 0})

    if not call_context:
        logger.error(f"No call context for {call_sid}")
        twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Matthew-Neural">I'm sorry, there was an error. Please call back.</Say>
    <Hangup/>
</Response>"""
        return Response(content=twiml, media_type="application/xml")

    tenant_id = call_context.get("tenant_id")
    tenant_name = call_context.get("tenant_name", "our company")
    conversation_state = call_context.get("conversation_state", "greeting")
    collected_info = call_context.get("collected_info", {})

    if not from_phone:
        from_phone = call_context.get("from_phone", "")

    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})

    customer = None
    if from_phone:
        customer = await db.customers.find_one(
            {"phone": from_phone, "tenant_id": tenant_id},
            {"_id": 0},
        )

    try:
        from openai import AsyncOpenAI
        from services.voice_ai_prompt import get_voice_ai_prompt

        openai_key = tenant.get("openai_api_key") if tenant else None
        if not openai_key:
            logger.error("No OpenAI API key configured for tenant")
            return Response(content="Error: API not configured", media_type="text/plain")

        client = AsyncOpenAI(api_key=openai_key)

        conversation_history = call_context.get("conversation_history", [])
        conversation_history.append({"role": "user", "content": speech_result})

        system_prompt = get_voice_ai_prompt(
            company_name=tenant_name,
            caller_phone=from_phone,
            collected_info=collected_info,
            conversation_state=conversation_state,
        )

        messages = [{"role": "system", "content": system_prompt}]
        for msg in conversation_history[-6:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append(
            {
                "role": "user",
                "content": "Respond to the caller. Follow the order: Name → Phone → Address → Issue → Urgency → Book",
            }
        )

        response_obj = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=300,
        )

        response = response_obj.choices[0].message.content

        # Parse AI response
        try:
            response_text = response.strip()
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]
            ai_response = json.loads(response_text)
        except json.JSONDecodeError:
            ai_response = {
                "response_text": response[:150]
                if len(response) < 150
                else "Got it. What else can you tell me?",
                "next_state": conversation_state,
                "collected_data": {},
                "action": None,
            }

        if ai_response.get("collected_data"):
            collected_info.update(
                {k: v for k, v in ai_response["collected_data"].items() if v}
            )

        next_state = ai_response.get("next_state", conversation_state)
        action = ai_response.get("action")
        response_text = ai_response.get("response_text", "Got it.")

        # Auto-detect booking trigger
        has_name = bool(collected_info.get("name"))
        has_phone = collected_info.get("phone_confirmed", False) or bool(
            collected_info.get("phone")
        )
        has_address = collected_info.get("address_confirmed", False) or bool(
            collected_info.get("address")
        )
        has_issue = bool(collected_info.get("issue"))
        has_urgency = bool(collected_info.get("urgency"))

        all_info_collected = has_name and has_phone and has_address and has_issue and has_urgency
        user_confirmed = any(
            word in speech_result.lower()
            for word in ["yes", "yeah", "works", "good", "okay", "ok", "sure", "fine", "correct", "right"]
        )

        if all_info_collected and user_confirmed and action != "book_job":
            logger.info("Auto-triggering booking - all info collected and user confirmed")
            action = "book_job"
            next_state = "booking_complete"

        if not collected_info.get("phone"):
            collected_info["phone"] = from_phone

        conversation_history.append({"role": "assistant", "content": response_text})

        await db.voice_calls.update_one(
            {"call_sid": call_sid},
            {
                "$set": {
                    "conversation_state": next_state,
                    "collected_info": collected_info,
                    "conversation_history": conversation_history,
                    "last_speech": speech_result,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            },
        )

        if action == "book_job" or next_state == "booking_complete":
            confirmed_phone = collected_info.get("phone") or from_phone

            result = await _voice_ai_book_job(
                tenant_id=tenant_id,
                from_phone=confirmed_phone,
                collected_info=collected_info,
                customer=customer,
            )

            if result.get("success"):
                job = result.get("job", {})
                quote_amount = job.get("quote_amount", 89)
                customer_name = (
                    collected_info.get("name", "").split()[0]
                    if collected_info.get("name")
                    else ""
                )
                address = collected_info.get("address", "your location")

                from services.twilio_service import twilio_service

                sms_body = (
                    f"Hi {customer_name}! Your appointment with {tenant_name} is confirmed "
                    f"for tomorrow morning at {address}. Quote: ${quote_amount:.2f}. "
                    f"We'll text when the tech is on the way."
                )
                await twilio_service.send_sms(to_phone=confirmed_phone, body=sms_body)

                final_text = (
                    f"Perfect, you're all set for tomorrow morning at {address}. "
                    f"You'll get a text confirmation shortly. Thanks for calling {tenant_name}!"
                )
                audio_id = f"final_{call_sid}"
                await db.voice_audio.update_one(
                    {"audio_id": audio_id},
                    {"$set": {"text": final_text}},
                    upsert=True,
                )

                twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Play>{base_url}/api/v1/voice/audio/{audio_id}</Play>
    <Hangup/>
</Response>"""
            else:
                twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Matthew-Neural">I apologize, I couldn't complete your booking. Someone will call you back shortly.</Say>
    <Hangup/>
</Response>"""

            return Response(content=twiml, media_type="application/xml")

        elif next_state == "end_call":
            await _voice_ai_create_lead(
                tenant_id=tenant_id,
                from_phone=collected_info.get("phone") or from_phone,
                collected_info=collected_info,
                customer=customer,
                speech_transcript=speech_result,
            )

            goodbye_text = f"{response_text} Thanks for calling {tenant_name}!"
            audio_id = f"goodbye_{call_sid}"
            await db.voice_audio.update_one(
                {"audio_id": audio_id},
                {"$set": {"text": goodbye_text}},
                upsert=True,
            )

            twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Play>{base_url}/api/v1/voice/audio/{audio_id}</Play>
    <Hangup/>
</Response>"""
            return Response(content=twiml, media_type="application/xml")

        else:
            audio_id = f"resp_{call_sid}_{hash(response_text) % 10000}"
            await db.voice_audio.update_one(
                {"audio_id": audio_id},
                {"$set": {"text": response_text}},
                upsert=True,
            )

            twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Gather input="speech" action="{base_url}/api/v1/voice/process-speech" method="POST" speechTimeout="auto" language="en-US" enhanced="true">
        <Play>{base_url}/api/v1/voice/audio/{audio_id}</Play>
    </Gather>
    <Say voice="Polly.Matthew-Neural">I didn't catch that.</Say>
    <Gather input="speech" action="{base_url}/api/v1/voice/process-speech" method="POST" speechTimeout="auto" language="en-US" enhanced="true">
        <Say voice="Polly.Matthew-Neural">Are you still there?</Say>
    </Gather>
    <Say voice="Polly.Matthew-Neural">I'll have someone call you back. Goodbye.</Say>
    <Hangup/>
</Response>"""
            return Response(content=twiml, media_type="application/xml")

    except Exception as e:
        logger.error(f"Voice AI error: {e}")
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Matthew-Neural">I apologize for the technical difficulty. Let me transfer you.</Say>
    <Record maxLength="120" action="{base_url}/api/v1/voice/recording-complete" />
</Response>"""
        return Response(content=twiml, media_type="application/xml")


@router.post("/status")
async def voice_call_status(request: Request):
    """Handle Twilio call status callbacks."""
    form_data = await request.form()
    call_sid = form_data.get("CallSid", "")
    call_status = form_data.get("CallStatus", "")

    logger.info(f"Voice call status: {call_sid} -> {call_status}")

    return {"received": True}


# ---------------------------------------------------------------------------
# WebSocket handlers
#
# These CANNOT be on an APIRouter; they must be registered directly on the
# FastAPI `app` instance.  They are documented here so the full voice module
# is understandable in one place, but the live registrations remain in
# server.py.
#
# Future refactor pattern (in main app startup):
#
#   from routes.voice import register_websocket_routes
#   register_websocket_routes(app, db)
# ---------------------------------------------------------------------------

def register_websocket_routes(app, database):
    """
    Register WebSocket routes on the given FastAPI app instance.
    Call this from the main application startup after `db` is available.

    Example:
        from routes.voice import register_websocket_routes
        register_websocket_routes(app, db)
    """
    global db
    db = database

    @app.websocket("/api/v1/voice/ws/{call_sid}")
    async def voice_ws(websocket: WebSocket, call_sid: str):
        """
        WebSocket endpoint for Twilio ConversationRelay.

        Handles real-time bidirectional communication:
        - Receives: setup, prompt (transcribed speech), interrupt, dtmf, error
        - Sends: text tokens for TTS synthesis
        """
        logger.info(f"ConversationRelay WebSocket connection attempt for call: {call_sid}")

        try:
            await websocket.accept()
            logger.info(f"ConversationRelay WebSocket CONNECTED: {call_sid}")
        except Exception as e:
            logger.error(f"WebSocket accept failed: {e}")
            return

        from services.conversation_relay import ConversationRelayHandler

        handler = None
        tenant = None
        caller_phone = ""

        try:
            call_context = await database.voice_calls.find_one(
                {"call_sid": call_sid}, {"_id": 0}
            )

            if call_context:
                tenant = await database.tenants.find_one(
                    {"id": call_context.get("tenant_id")}, {"_id": 0}
                )
                caller_phone = call_context.get("from_phone", "")

            while True:
                data = await websocket.receive_text()
                message = json.loads(data)
                event_type = message.get("type")

                logger.info(f"ConversationRelay event: {event_type}")
                logger.debug(f"Message payload: {json.dumps(message)[:500]}")

                if event_type == "setup":
                    session_id = message.get("sessionId", "")
                    custom_params = message.get("customParameters", {})

                    logger.info(f"ConversationRelay setup - SessionID: {session_id}")
                    logger.info(f"Custom parameters: {custom_params}")

                    if not tenant and custom_params.get("tenant_id"):
                        tenant = await database.tenants.find_one(
                            {"id": custom_params["tenant_id"]}, {"_id": 0}
                        )
                        caller_phone = custom_params.get("caller_phone", "")
                        logger.info(
                            f"Got tenant from custom_params: "
                            f"{tenant.get('name') if tenant else 'None'}"
                        )

                    if tenant:
                        logger.info(
                            f"Creating handler for tenant: {tenant.get('name')}, "
                            f"has prompt: {bool(tenant.get('voice_system_prompt'))}"
                        )
                        handler = ConversationRelayHandler(
                            db=database,
                            call_sid=call_sid,
                            tenant=tenant,
                            caller_phone=caller_phone,
                        )
                        await handler.handle_setup(message)
                        logger.info("Handler created successfully")
                    else:
                        logger.error(f"No tenant found for call {call_sid}")
                        await websocket.send_text(
                            json.dumps(
                                {
                                    "type": "end",
                                    "handoffData": json.dumps(
                                        {"reason": "No tenant configured"}
                                    ),
                                }
                            )
                        )
                        break

                elif event_type == "prompt":
                    voice_prompt = message.get("voicePrompt", "")
                    is_last = message.get("last", True)
                    lang = message.get("lang", "en-US")

                    logger.info(
                        f"Caller said: '{voice_prompt}' (lang={lang}, last={is_last})"
                    )

                    if handler and voice_prompt.strip():
                        try:
                            response = await handler.handle_prompt(message)
                            logger.info(f"Handler returned response: '{response}'")

                            if response:
                                await websocket.send_text(
                                    json.dumps(
                                        {
                                            "type": "text",
                                            "token": response,
                                            "last": True,
                                        }
                                    )
                                )
                                logger.info(f"Sent response to Twilio: '{response}'")
                            else:
                                logger.warning("Handler returned empty response")
                        except Exception as e:
                            logger.error(f"Error in handle_prompt: {e}", exc_info=True)
                            await websocket.send_text(
                                json.dumps(
                                    {
                                        "type": "text",
                                        "token": "I'm sorry, I'm having trouble. Could you repeat that?",
                                        "last": True,
                                    }
                                )
                            )
                    else:
                        if not handler:
                            logger.error("No handler available for prompt event")
                        elif not voice_prompt.strip():
                            logger.warning("Empty voice prompt received")

                elif event_type == "interrupt":
                    utterance = message.get("utteranceUntilInterrupt", "")
                    duration_ms = message.get("durationUntilInterruptMs", 0)
                    logger.info(
                        f"Caller interrupted after {duration_ms}ms. Partial: '{utterance}'"
                    )
                    if handler:
                        await handler.handle_interrupt(message)

                elif event_type == "dtmf":
                    digit = message.get("digit", "")
                    logger.info(f"DTMF digit pressed: {digit}")
                    if handler:
                        response = await handler.handle_dtmf(message)
                        if response:
                            await websocket.send_text(
                                json.dumps(
                                    {"type": "text", "token": response, "last": True}
                                )
                            )

                elif event_type == "error":
                    description = message.get("description", "Unknown error")
                    logger.error(f"ConversationRelay error: {description}")
                    if handler:
                        await handler.handle_error(message)

                elif event_type == "end":
                    logger.info(f"ConversationRelay session ending for call {call_sid}")
                    break

        except WebSocketDisconnect:
            logger.info(f"ConversationRelay WebSocket disconnected: {call_sid}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
        except Exception as e:
            logger.error(f"ConversationRelay WebSocket error: {e}", exc_info=True)
        finally:
            if handler:
                await handler.handle_end()

    @app.websocket("/api/v1/voice/stream/{call_sid}")
    async def voice_stream_websocket(websocket: WebSocket, call_sid: str):
        """
        WebSocket endpoint for Twilio Media Streams.
        Handles real-time audio streaming for voice AI.
        """
        await websocket.accept()

        from services.voice_ai_service import create_voice_ai_service

        voice_ai = create_voice_ai_service()

        tenant_id = None
        from_phone = None
        stream_sid = None
        greeting_sent = False

        try:
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)
                event_type = message.get("event")

                if event_type == "connected":
                    logger.info(f"WebSocket connected for call {call_sid}")

                elif event_type == "start":
                    start_data = message.get("start", {})
                    stream_sid = start_data.get("streamSid")
                    custom_params = start_data.get("customParameters", {})

                    tenant_id = custom_params.get("tenant_id")
                    from_phone = custom_params.get("from_phone")

                    logger.info(f"Stream started: {stream_sid}, tenant: {tenant_id}")

                    if tenant_id:
                        await voice_ai.initialize(
                            tenant_id, from_phone, call_sid, database
                        )

                        if not greeting_sent:
                            greeting_audio = await voice_ai.get_greeting()
                            if greeting_audio:
                                await websocket.send_json(
                                    {
                                        "event": "media",
                                        "streamSid": stream_sid,
                                        "media": {"payload": greeting_audio},
                                    }
                                )
                                greeting_sent = True

                elif event_type == "media":
                    media_data = message.get("media", {})
                    audio_payload = media_data.get("payload", "")

                    if audio_payload:
                        audio_chunk = base64.b64decode(audio_payload)
                        transcript = await voice_ai.process_audio(audio_chunk)

                        if transcript:
                            logger.info(f"Transcript: {transcript}")
                            response_audio, action_data = await voice_ai.generate_response(
                                transcript
                            )

                            if response_audio:
                                await websocket.send_json(
                                    {
                                        "event": "media",
                                        "streamSid": stream_sid,
                                        "media": {"payload": response_audio},
                                    }
                                )

                            if action_data and action_data.get("action") == "end_call":
                                logger.info(f"Ending call {call_sid}")
                                break

                elif event_type == "stop":
                    logger.info(f"Stream stopped for call {call_sid}")
                    break

        except WebSocketDisconnect:
            logger.info(f"Media stream WebSocket disconnected: {call_sid}")
        except Exception as e:
            logger.error(f"Media stream WebSocket error: {e}", exc_info=True)
        finally:
            await voice_ai.end_conversation()


# ---------------------------------------------------------------------------
# Private helper functions
# ---------------------------------------------------------------------------

async def _voice_ai_book_job(
    tenant_id: str,
    from_phone: str,
    collected_info: dict,
    customer: dict = None,
):
    """Helper: create lead, customer, property, and job from voice AI conversation."""
    try:
        import pytz

        tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
        if not tenant:
            logger.error(f"Tenant not found: {tenant_id}")
            return {"success": False, "error": "Tenant not found"}

        tenant_tz = pytz.timezone(tenant.get("timezone", "America/New_York"))

        # Create or get customer
        customer_id = None
        if customer:
            customer_id = customer["id"]
        else:
            name_parts = (
                collected_info.get("name", "").split()
                if collected_info.get("name")
                else [""]
            )
            first_name = name_parts[0] if name_parts else ""
            last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

            new_customer = {
                "id": str(uuid4()),
                "tenant_id": tenant_id,
                "first_name": first_name,
                "last_name": last_name,
                "phone": from_phone,
                "preferred_channel": "CALL",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            await db.customers.insert_one(new_customer)
            customer_id = new_customer["id"]
            customer = new_customer

        urgency = collected_info.get("urgency", "ROUTINE").upper()
        if urgency not in ["EMERGENCY", "URGENT", "ROUTINE"]:
            urgency = "ROUTINE"

        lead = {
            "id": str(uuid4()),
            "tenant_id": tenant_id,
            "customer_id": customer_id,
            "source": "SELF_HOSTED_VOICE",
            "channel": "VOICE",
            "status": "JOB_BOOKED",
            "caller_name": collected_info.get("name", ""),
            "caller_phone": from_phone,
            "issue_type": collected_info.get("issue", "General Inquiry")[:100],
            "description": collected_info.get("issue", ""),
            "urgency": urgency,
            "tags": ["voice_ai", "self_hosted"],
            "first_contact_at": datetime.now(timezone.utc).isoformat(),
            "last_activity_at": datetime.now(timezone.utc).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.leads.insert_one(lead)

        # Determine job schedule
        tomorrow = datetime.now(tenant_tz) + timedelta(days=1)
        if urgency == "EMERGENCY":
            now = datetime.now(tenant_tz)
            if now.hour < 16:
                service_date = now
                start_hour, end_hour = 14, 18
            else:
                service_date = tomorrow
                start_hour, end_hour = 8, 12
        else:
            service_date = tomorrow
            start_hour, end_hour = 8, 12

        service_window_start = tenant_tz.localize(
            datetime(
                service_date.year,
                service_date.month,
                service_date.day,
                start_hour,
                0,
            )
        )
        service_window_end = tenant_tz.localize(
            datetime(
                service_date.year,
                service_date.month,
                service_date.day,
                end_hour,
                0,
            )
        )

        job_type = "DIAGNOSTIC"
        quote_amount = _calculate_quote_amount(job_type, urgency)

        # Get or create property
        property_id = None
        existing_prop = await db.properties.find_one(
            {"customer_id": customer_id}, {"_id": 0}
        )

        if existing_prop:
            property_id = existing_prop["id"]
            if collected_info.get("address"):
                await db.properties.update_one(
                    {"id": property_id},
                    {
                        "$set": {
                            "address_line1": collected_info["address"],
                            "updated_at": datetime.now(timezone.utc).isoformat(),
                        }
                    },
                )
        elif collected_info.get("address"):
            new_property = {
                "id": str(uuid4()),
                "tenant_id": tenant_id,
                "customer_id": customer_id,
                "address_line1": collected_info["address"],
                "property_type": "RESIDENTIAL",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            await db.properties.insert_one(new_property)
            property_id = new_property["id"]
            logger.info(
                f"Created property {property_id} with address: {collected_info['address']}"
            )

        job = {
            "id": str(uuid4()),
            "tenant_id": tenant_id,
            "customer_id": customer_id,
            "property_id": property_id,
            "lead_id": lead["id"],
            "job_type": job_type,
            "priority": (
                "EMERGENCY"
                if urgency == "EMERGENCY"
                else ("HIGH" if urgency == "URGENT" else "NORMAL")
            ),
            "service_window_start": service_window_start.isoformat(),
            "service_window_end": service_window_end.isoformat(),
            "status": "BOOKED",
            "created_by": "AI",
            "notes": collected_info.get("issue", ""),
            "quote_amount": quote_amount,
            "reminder_day_before_sent": False,
            "reminder_morning_of_sent": False,
            "en_route_sms_sent": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.jobs.insert_one(job)

        quote = {
            "id": str(uuid4()),
            "tenant_id": tenant_id,
            "customer_id": customer_id,
            "property_id": property_id,
            "job_id": job["id"],
            "amount": quote_amount,
            "currency": "USD",
            "description": (
                f"{job_type} service - "
                f"{collected_info.get('issue', 'General service')[:100]}"
            ),
            "status": "SENT",
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.quotes.insert_one(quote)

        await db.jobs.update_one(
            {"id": job["id"]}, {"$set": {"quote_id": quote["id"]}}
        )

        logger.info(f"Voice AI booked job {job['id']} for customer {customer_id}")

        return {
            "success": True,
            "job": job,
            "quote": quote,
            "lead": lead,
            "customer_id": customer_id,
        }

    except Exception as e:
        logger.error(f"Voice AI booking error: {e}")
        return {"success": False, "error": str(e)}


async def _voice_ai_create_lead(
    tenant_id: str,
    from_phone: str,
    collected_info: dict,
    customer: dict = None,
    speech_transcript: str = "",
):
    """Helper: create just a lead from voice AI conversation (without booking)."""
    try:
        customer_id = customer["id"] if customer else None

        urgency = collected_info.get("urgency", "ROUTINE").upper()
        if urgency not in ["EMERGENCY", "URGENT", "ROUTINE"]:
            urgency = "ROUTINE"

        lead = {
            "id": str(uuid4()),
            "tenant_id": tenant_id,
            "customer_id": customer_id,
            "source": "SELF_HOSTED_VOICE",
            "channel": "VOICE",
            "status": "NEW",
            "caller_name": collected_info.get("name", ""),
            "caller_phone": from_phone,
            "issue_type": (
                collected_info.get("issue", "General Inquiry")[:100]
                if collected_info.get("issue")
                else "Voice Inquiry"
            ),
            "description": (
                f"Voice AI transcript: {speech_transcript}\n\n"
                f"Collected info: {json.dumps(collected_info)}"
            ),
            "urgency": urgency,
            "tags": ["voice_ai", "self_hosted", "needs_followup"],
            "first_contact_at": datetime.now(timezone.utc).isoformat(),
            "last_activity_at": datetime.now(timezone.utc).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.leads.insert_one(lead)

        logger.info(f"Voice AI created lead {lead['id']}")
        return {"success": True, "lead": lead}

    except Exception as e:
        logger.error(f"Voice AI lead creation error: {e}")
        return {"success": False, "error": str(e)}
