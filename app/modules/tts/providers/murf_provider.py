#!/usr/bin/env python
# Murf.ai TTS Provider Module for Morning Coffee application

import logging
import time
import traceback
import json
from typing import Dict, Any, Optional, Tuple
import requests

import pyaudio

from ..base_provider import BaseTTSProvider

logger = logging.getLogger("murf-provider")

class MurfProvider(BaseTTSProvider):
    """TTS provider using Murf.ai API."""
    
    def __init__(self, redis_client=None, **kwargs):
        """
        Initialize Murf.ai provider.
        
        Args:
            redis_client: Redis client for caching (not used by this provider)
            **kwargs: Additional configuration options including:
                - api_key: Murf.ai API key
                - api_url: Custom API URL (optional)
        """
        self.api_key = kwargs.get("api_key")
        if not self.api_key:
            raise ValueError("Murf.ai API key is required")
        
        self.api_url = kwargs.get("api_url", "https://api.murf.ai/v1")
        self.current_voice = None
        
        # Default voice configuration
        self.voice_config = {
            "voice_id": "en-US-ryan",
            "style": "neutral",
            "speed": 1.0,
            "pitch": 0
        }
        
        # Cache for available voices
        self._voices = None
        
        logger.info("Murf.ai TTS provider initialized")
    
    def generate_speech(self, text: str, voice_id: Optional[str] = None, 
                       speed: float = 1.0) -> Optional[bytes]:
        """
        Generate speech using Murf.ai API.
        
        Args:
            text (str): Text to convert to speech
            voice_id (Optional[str]): Voice identifier
            speed (float): Speech speed factor
            
        Returns:
            Optional[bytes]: Audio data as bytes or None if generation failed
        """
        try:
            if not text:
                return None
            
            # Set voice if provided
            if voice_id:
                self.set_voice(voice_id)
            
            logger.debug(f"Generating speech for text: {text[:50]}{'...' if len(text) > 50 else ''}")
            
            # Prepare API request
            headers = {
                "accept": "application/json",
                "content-type": "application/json",
                "x-api-key": self.api_key
            }
            
            payload = {
                "text": text,
                "voiceId": self.voice_config["voice_id"],
                "style": self.voice_config["style"],
                "rate": speed * self.voice_config["speed"],
                "pitch": self.voice_config["pitch"],
                "sampleRate": 24000,
                "format": "WAV"
            }
            
            # Make API request
            start_time = time.time()
            response = requests.post(
                f"{self.api_url}/speech",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            
            # Parse response
            result = response.json()
            if result.get("status") != "success":
                logger.error(f"Murf.ai API error: {result.get('message', 'Unknown error')}")
                return None
            
            # Download audio file
            audio_url = result.get("data", {}).get("audioUrl")
            if not audio_url:
                logger.error("No audio URL in response")
                return None
            
            audio_response = requests.get(audio_url)
            audio_response.raise_for_status()
            
            generation_time = time.time() - start_time
            logger.debug(f"Speech generation took {generation_time:.2f} seconds")
            
            return audio_response.content
            
        except requests.exceptions.RequestException as req_err:
            logger.error(f"API request error: {req_err}")
            return None
        except Exception as e:
            logger.error(f"Error generating speech: {e}")
            logger.debug(traceback.format_exc())
            return None
    
    def get_voices(self) -> Dict[str, Any]:
        """
        Get available Murf.ai voices.
        
        Returns:
            Dict[str, Any]: Dictionary containing available voices
        """
        if self._voices is None:
            try:
                headers = {
                    "accept": "application/json",
                    "x-api-key": self.api_key
                }
                
                response = requests.get(
                    f"{self.api_url}/voices",
                    headers=headers
                )
                response.raise_for_status()
                
                result = response.json()
                if result.get("status") != "success":
                    logger.error(f"Murf.ai API error: {result.get('message', 'Unknown error')}")
                    return {"voices": {}}
                
                voices_data = result.get("data", {}).get("voices", [])
                
                # Process voice data
                voice_dict = {}
                for voice in voices_data:
                    voice_id = voice.get("voiceId")
                    if not voice_id:
                        continue
                    
                    voice_dict[voice_id] = {
                        "name": voice.get("name", voice_id),
                        "language": voice.get("language", "unknown"),
                        "gender": voice.get("gender", "unknown"),
                        "accent": voice.get("accent", "unknown"),
                        "styles": voice.get("styles", [])
                    }
                
                self._voices = voice_dict
                
            except Exception as e:
                logger.error(f"Error fetching Murf.ai voices: {e}")
                self._voices = {}
        
        return {"voices": self._voices}
    
    def set_voice(self, voice_id: str) -> bool:
        """
        Set the voice to use for TTS.
        
        Args:
            voice_id (str): Voice identifier
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Parse voice ID format (can include style): "en-US-ryan:excited"
            parts = voice_id.split(":")
            base_voice_id = parts[0]
            style = parts[1] if len(parts) > 1 else "neutral"
            
            # Load voices if not already loaded
            if self._voices is None:
                self.get_voices()
            
            # Check if the voice exists
            if base_voice_id not in self._voices:
                logger.warning(f"Voice {base_voice_id} not found in available voices")
                return False
            
            # Check if the style is valid
            voice_info = self._voices[base_voice_id]
            styles = voice_info.get("styles", ["neutral"])
            
            if style not in styles:
                logger.warning(f"Style {style} not available for voice {base_voice_id}")
                style = "neutral"  # Default to neutral
            
            # Update voice configuration
            self.voice_config["voice_id"] = base_voice_id
            self.voice_config["style"] = style
            
            self.current_voice = voice_id
            logger.debug(f"Voice set to {voice_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting voice: {e}")
            return False
    
    def voice_exists(self, voice_id: str) -> bool:
        """
        Check if voice exists.
        
        Args:
            voice_id (str): Voice identifier
            
        Returns:
            bool: True if voice exists, False otherwise
        """
        # Parse voice ID to get base voice ID
        parts = voice_id.split(":")
        base_voice_id = parts[0]
        
        # Check if voice exists
        if self._voices is None:
            self.get_voices()
        
        return base_voice_id in self._voices
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check if the Murf.ai service is healthy.
        
        Returns:
            Dict[str, Any]: Health status information
        """
        try:
            # Try to get voices list to check API connectivity
            headers = {
                "accept": "application/json",
                "x-api-key": self.api_key
            }
            
            response = requests.get(
                f"{self.api_url}/voices",
                headers=headers
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get("status") != "success":
                return {
                    "status": "unhealthy",
                    "engine": "Murf.ai",
                    "message": result.get("message", "API returned error status")
                }
            
            return {
                "status": "healthy",
                "engine": "Murf.ai",
                "message": "API connection is functioning normally"
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "engine": "Murf.ai",
                "message": str(e)
            }
    
    def get_stream_info(self) -> Tuple[int, int, int]:
        """
        Get stream configuration information for audio playback.
        
        Returns:
            Tuple[int, int, int]: Audio format, number of channels, and sample rate
        """
        return pyaudio.paInt16, 1, 24000  # 16-bit, mono, 24kHz 