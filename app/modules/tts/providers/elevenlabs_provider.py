#!/usr/bin/env python
# ElevenLabs TTS Provider Module for Morning Coffee application

import logging
import time
import traceback
from typing import Dict, Any, Optional, Tuple
import requests

import pyaudio

from ..base_provider import BaseTTSProvider

logger = logging.getLogger("elevenlabs-provider")

class ElevenlabsProvider(BaseTTSProvider):
    """TTS provider using ElevenLabs API."""
    
    def __init__(self, redis_client=None, **kwargs):
        """
        Initialize ElevenLabs provider.
        
        Args:
            redis_client: Redis client for caching (not used by this provider)
            **kwargs: Additional configuration options including:
                - api_key: ElevenLabs API key
                - model_id: Model ID to use (default: 'eleven_monolingual_v1')
        """
        self.api_key = kwargs.get("api_key")
        if not self.api_key:
            raise ValueError("ElevenLabs API key is required")
        
        self.api_url = "https://api.elevenlabs.io/v1"
        self.current_voice = None
        self.model_id = kwargs.get("model_id", "eleven_monolingual_v1")
        
        # Default voice configuration
        self.voice_config = {
            "voice_id": "21m00Tcm4TlvDq8ikWAM",  # Rachel voice
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.0,
            "use_speaker_boost": True
        }
        
        # Cache for available voices
        self._voices = None
        
        logger.info("ElevenLabs TTS provider initialized")
    
    def generate_speech(self, text: str, voice_id: Optional[str] = None, 
                       speed: float = 1.0) -> Optional[bytes]:
        """
        Generate speech using ElevenLabs API.
        
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
                "xi-api-key": self.api_key,
                "Content-Type": "application/json",
                "Accept": "audio/wav"
            }
            
            # Use the configured voice_id
            voice_id = self.voice_config["voice_id"]
            
            # Voice settings
            voice_settings = {
                "stability": self.voice_config["stability"],
                "similarity_boost": self.voice_config["similarity_boost"],
                "style": self.voice_config["style"],
                "use_speaker_boost": self.voice_config["use_speaker_boost"]
            }
            
            # Model settings (including speed)
            model_settings = {
                "model_id": self.model_id,
                "speed": speed
            }
            
            payload = {
                "text": text,
                "voice_settings": voice_settings,
                "model_id": self.model_id
            }
            
            # Make API request
            start_time = time.time()
            response = requests.post(
                f"{self.api_url}/text-to-speech/{voice_id}",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            
            generation_time = time.time() - start_time
            logger.debug(f"Speech generation took {generation_time:.2f} seconds")
            
            return response.content
            
        except requests.exceptions.RequestException as req_err:
            logger.error(f"API request error: {req_err}")
            return None
        except Exception as e:
            logger.error(f"Error generating speech: {e}")
            logger.debug(traceback.format_exc())
            return None
    
    def get_voices(self) -> Dict[str, Any]:
        """
        Get available ElevenLabs voices.
        
        Returns:
            Dict[str, Any]: Dictionary containing available voices
        """
        if self._voices is None:
            try:
                headers = {
                    "xi-api-key": self.api_key,
                    "Accept": "application/json"
                }
                
                response = requests.get(
                    f"{self.api_url}/voices",
                    headers=headers
                )
                response.raise_for_status()
                
                voices_data = response.json().get("voices", [])
                
                # Process voice data
                voice_dict = {}
                for voice in voices_data:
                    voice_id = voice.get("voice_id")
                    if not voice_id:
                        continue
                    
                    voice_dict[voice_id] = {
                        "name": voice.get("name", voice_id),
                        "category": voice.get("category", "unknown"),
                        "description": voice.get("description", ""),
                        "gender": "male" if voice.get("labels", {}).get("gender") == "male" else "female",
                        "preview_url": voice.get("preview_url", "")
                    }
                
                self._voices = voice_dict
                
            except Exception as e:
                logger.error(f"Error fetching ElevenLabs voices: {e}")
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
            # Parse voice ID format (can include style params): "voice_id:stability:similarity"
            parts = voice_id.split(":")
            base_voice_id = parts[0]
            
            # Load voices if not already loaded
            if self._voices is None:
                self.get_voices()
            
            # Check if the voice exists
            if base_voice_id not in self._voices:
                logger.warning(f"Voice {base_voice_id} not found in available voices")
                return False
            
            # Update voice configuration
            self.voice_config["voice_id"] = base_voice_id
            
            # Update additional settings if provided
            if len(parts) > 1 and parts[1]:
                self.voice_config["stability"] = float(parts[1])
            if len(parts) > 2 and parts[2]:
                self.voice_config["similarity_boost"] = float(parts[2])
            if len(parts) > 3 and parts[3]:
                self.voice_config["style"] = float(parts[3])
            
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
        Check if the ElevenLabs service is healthy.
        
        Returns:
            Dict[str, Any]: Health status information
        """
        try:
            # Try to get user info to check API connectivity
            headers = {
                "xi-api-key": self.api_key,
                "Accept": "application/json"
            }
            
            response = requests.get(
                f"{self.api_url}/user",
                headers=headers
            )
            response.raise_for_status()
            
            # Check subscription
            user_data = response.json()
            subscription = user_data.get("subscription", {})
            tier = subscription.get("tier", "free")
            remaining_chars = subscription.get("character_count", 0)
            
            return {
                "status": "healthy",
                "engine": "ElevenLabs",
                "message": "API connection is functioning normally",
                "tier": tier,
                "remaining_characters": remaining_chars
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "engine": "ElevenLabs",
                "message": str(e)
            }
    
    def get_stream_info(self) -> Tuple[int, int, int]:
        """
        Get stream configuration information for audio playback.
        
        Returns:
            Tuple[int, int, int]: Audio format, number of channels, and sample rate
        """
        return pyaudio.paInt16, 1, 24000  # 16-bit, mono, 24kHz 