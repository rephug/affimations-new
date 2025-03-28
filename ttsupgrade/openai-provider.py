#!/usr/bin/env python
# OpenAI TTS Provider Module for Morning Coffee application

import logging
import time
import traceback
import os
from typing import Dict, Any, Optional, Tuple

import pyaudio
import requests
from openai import OpenAI

from ..base_provider import BaseTTSProvider

logger = logging.getLogger("openai-provider")

class OpenAITTSProvider(BaseTTSProvider):
    """TTS provider using OpenAI's gpt-4o-mini-tts API."""
    
    def __init__(self, redis_client=None, **kwargs):
        """
        Initialize OpenAI TTS provider.
        
        Args:
            redis_client: Redis client for caching (not used by this provider)
            **kwargs: Additional configuration options including:
                - api_key: OpenAI API key
                - model: TTS model to use (default: gpt-4o-mini-tts)
                - voice_style: Style instructions for the voice
        """
        self.api_key = kwargs.get("api_key", os.environ.get("OPENAI_API_KEY"))
        self.model = kwargs.get("model", "gpt-4o-mini-tts")
        self.voice_style = kwargs.get("voice_style", "Speak in a natural, warm, and friendly tone")
        
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        
        # Initialize OpenAI client
        self.client = OpenAI(api_key=self.api_key)
        self.current_voice = None
        
        # Sample rate for the OpenAI TTS model
        self.sample_rate = 24000
        
        # Cache for available voices
        self._voices = None
        
        # Voice styling options (can be customized through natural language)
        self.voice_styles = {
            "default_female": "Speak in a natural, warm female voice",
            "default_male": "Speak in a natural, warm male voice",
            "professional": "Speak in a clear, professional tone",
            "friendly": "Speak in a friendly, approachable manner",
            "calm": "Speak in a calm, soothing voice like a mindfulness guide",
            "excited": "Speak with enthusiasm and energy",
            "sad": "Speak with a somber, melancholic tone",
            "serene": "Speak with a peaceful, zen-like quality",
            "formal": "Speak in a formal, slightly authoritative manner",
            "customer_service": "Speak like a helpful customer service representative"
        }
        
        logger.info("OpenAI TTS provider initialized")
    
    def generate_speech(self, text: str, voice_id: Optional[str] = None, 
                       speed: float = 1.0) -> Optional[bytes]:
        """
        Generate speech using OpenAI's TTS API.
        
        Args:
            text (str): Text to convert to speech
            voice_id (Optional[str]): Voice identifier or style
            speed (float): Speech speed factor
            
        Returns:
            Optional[bytes]: Audio data as bytes or None if generation failed
        """
        try:
            if not text:
                return None
            
            # Set voice style if provided
            voice_style = self.voice_style
            if voice_id:
                if voice_id in self.voice_styles:
                    voice_style = self.voice_styles[voice_id]
                elif self.voice_exists(voice_id):
                    voice_style = voice_id  # Use directly if it's a custom style instruction
                self.current_voice = voice_id
            
            # Prepare the input for the TTS model
            logger.debug(f"Generating speech for text: {text[:50]}{'...' if len(text) > 50 else ''}")
            logger.debug(f"Using voice style: {voice_style}")
            
            # For the new OpenAI TTS model, we use a special format that includes voice style instructions
            full_prompt = f"{voice_style}. {text}"
            
            # Start time measurement
            start_time = time.time()
            
            # Use the OpenAI client to generate speech
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a text-to-speech service."},
                    {"role": "user", "content": full_prompt}
                ],
                audio={"voice": "alloy", "format": "wav"},
                max_tokens=1024
            )
            
            # Get audio content from response
            audio_data = response.audio_content
            
            generation_time = time.time() - start_time
            logger.debug(f"Speech generation took {generation_time:.2f} seconds")
            
            return audio_data
            
        except Exception as e:
            logger.error(f"Error generating speech with OpenAI TTS: {e}")
            logger.debug(traceback.format_exc())
            return None
    
    def get_voices(self) -> Dict[str, Any]:
        """
        Get available voice styles for OpenAI TTS.
        
        Returns:
            Dict[str, Any]: Dictionary containing available voice styles
        """
        if self._voices is None:
            # Create a dictionary of available voice styles
            voices_dict = {}
            
            for style_id, style_desc in self.voice_styles.items():
                voices_dict[style_id] = {
                    "name": style_id.replace('_', ' ').title(),
                    "description": style_desc,
                    "category": "voice_style"
                }
            
            self._voices = voices_dict
        
        return {"voices": self._voices}
    
    def set_voice(self, voice_id: str) -> bool:
        """
        Set the voice style to use for TTS.
        
        Args:
            voice_id (str): Voice identifier or style
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if voice_id in self.voice_styles:
                self.voice_style = self.voice_styles[voice_id]
                self.current_voice = voice_id
                logger.debug(f"Voice set to {voice_id}: {self.voice_style}")
                return True
            elif voice_id and isinstance(voice_id, str):
                # Allow for custom voice style instructions
                self.voice_style = voice_id
                self.current_voice = voice_id
                logger.debug(f"Custom voice style set: {voice_id}")
                return True
            else:
                logger.warning(f"Voice {voice_id} not found in available voices")
                return False
        except Exception as e:
            logger.error(f"Error setting voice: {e}")
            return False
    
    def voice_exists(self, voice_id: str) -> bool:
        """
        Check if a voice style exists.
        
        Args:
            voice_id (str): Voice identifier or style
            
        Returns:
            bool: True if voice exists, False otherwise
        """
        return voice_id in self.voice_styles or (isinstance(voice_id, str) and len(voice_id) > 0)
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check if the OpenAI TTS service is healthy.
        
        Returns:
            Dict[str, Any]: Health status information
        """
        try:
            # Test the API with a small request
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a text-to-speech service."},
                    {"role": "user", "content": "Hello"}
                ],
                audio={"voice": "alloy", "format": "wav"},
                max_tokens=10
            )
            
            return {
                "status": "healthy",
                "engine": f"OpenAI {self.model}",
                "message": "API connection is functioning normally"
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "engine": f"OpenAI {self.model}",
                "message": str(e)
            }
    
    def get_stream_info(self) -> Tuple[int, int, int]:
        """
        Get stream configuration information for audio playback.
        
        Returns:
            Tuple[int, int, int]: Audio format, number of channels, and sample rate
        """
        return pyaudio.paInt16, 1, self.sample_rate  # 16-bit, mono, 24kHz
