"""
ElevenLabs Text-to-Speech Service
Provides natural, human-like voice for phone AI
"""
import os
import logging
import base64
import hashlib
from typing import Optional
from elevenlabs import ElevenLabs, VoiceSettings

logger = logging.getLogger(__name__)

# Voice options - these are the most natural for phone conversations
VOICE_OPTIONS = {
    "roger": "CwhRBWXzGAHq8TQ4Fs17",     # Male, laid-back, conversational, American
    "sarah": "EXAVITQu4vr4xnSDxMaL",     # Female, professional, American
    "charlie": "IKne3meq5aSn9XLyUdCD",   # Male, confident, energetic, Australian
    "river": "SAz9YHcvj6GT2YYXdXww",     # Neutral, calm, informative, American
    "liam": "TX3LPaxmHKxFdv7VOQHJ",      # Male, confident, young, American
}

# Default voice for phone receptionist
DEFAULT_VOICE = "roger"


class ElevenLabsService:
    """ElevenLabs TTS service for natural voice generation"""
    
    def __init__(self):
        self.api_key = os.environ.get('ELEVENLABS_API_KEY')
        self.client = None
        self.audio_cache = {}  # Simple in-memory cache for repeated phrases
        
        if self.api_key:
            try:
                self.client = ElevenLabs(api_key=self.api_key)
                logger.info("ElevenLabs client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize ElevenLabs client: {e}")
    
    def is_configured(self) -> bool:
        """Check if ElevenLabs is properly configured"""
        return self.client is not None
    
    def _get_cache_key(self, text: str, voice_id: str) -> str:
        """Generate a cache key for text+voice combination"""
        return hashlib.md5(f"{text}:{voice_id}".encode()).hexdigest()
    
    def text_to_speech(
        self,
        text: str,
        voice: str = DEFAULT_VOICE,
        stability: float = 0.5,
        similarity_boost: float = 0.75,
        style: float = 0.0,
        use_speaker_boost: bool = True
    ) -> Optional[bytes]:
        """
        Convert text to speech using ElevenLabs.
        
        Args:
            text: Text to convert to speech
            voice: Voice name or ID (default: roger)
            stability: Voice stability (0-1), lower = more expressive
            similarity_boost: How closely to match the voice (0-1)
            style: Style exaggeration (0-1)
            use_speaker_boost: Enhance speaker clarity
            
        Returns:
            Audio bytes (MP3 format) or None if failed
        """
        if not self.is_configured():
            logger.error("ElevenLabs not configured")
            return None
        
        # Get voice ID
        voice_id = VOICE_OPTIONS.get(voice.lower(), voice)
        
        # Check cache first
        cache_key = self._get_cache_key(text, voice_id)
        if cache_key in self.audio_cache:
            logger.debug(f"Cache hit for text: {text[:50]}...")
            return self.audio_cache[cache_key]
        
        try:
            # Configure voice settings for natural phone conversation
            voice_settings = VoiceSettings(
                stability=stability,
                similarity_boost=similarity_boost,
                style=style,
                use_speaker_boost=use_speaker_boost
            )
            
            # Generate audio
            audio_generator = self.client.text_to_speech.convert(
                text=text,
                voice_id=voice_id,
                model_id="eleven_turbo_v2_5",  # Fast model for real-time
                voice_settings=voice_settings,
                output_format="mp3_44100_128"  # Good quality for phone
            )
            
            # Collect audio data
            audio_data = b""
            for chunk in audio_generator:
                audio_data += chunk
            
            # Cache the result (limit cache size)
            if len(self.audio_cache) < 100:
                self.audio_cache[cache_key] = audio_data
            
            logger.info(f"Generated {len(audio_data)} bytes of audio for: {text[:50]}...")
            return audio_data
            
        except Exception as e:
            logger.error(f"ElevenLabs TTS error: {e}")
            return None
    
    def text_to_speech_base64(
        self,
        text: str,
        voice: str = DEFAULT_VOICE,
        **kwargs
    ) -> Optional[str]:
        """
        Convert text to speech and return as base64-encoded string.
        Useful for embedding in responses or data URLs.
        """
        audio_data = self.text_to_speech(text, voice, **kwargs)
        if audio_data:
            return base64.b64encode(audio_data).decode('utf-8')
        return None
    
    def get_available_voices(self) -> list:
        """Get list of available voices"""
        if not self.is_configured():
            return []
        
        try:
            voices = self.client.voices.get_all()
            return [
                {
                    "id": v.voice_id,
                    "name": v.name,
                    "labels": v.labels
                }
                for v in voices.voices
            ]
        except Exception as e:
            logger.error(f"Error fetching voices: {e}")
            return []


# Singleton instance
elevenlabs_service = ElevenLabsService()
