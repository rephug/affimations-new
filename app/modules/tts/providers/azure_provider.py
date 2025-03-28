#!/usr/bin/env python
# Azure TTS Provider Module for Morning Coffee application

import logging
import time
import traceback
from typing import Dict, Any, Optional, Tuple
import requests
import xml.etree.ElementTree as ET
import uuid

import pyaudio

from ..base_provider import BaseTTSProvider

logger = logging.getLogger("azure-provider")

class AzureProvider(BaseTTSProvider):
    """TTS provider using Microsoft Azure Cognitive Services Speech API."""
    
    def __init__(self, redis_client=None, **kwargs):
        """
        Initialize Azure TTS provider.
        
        Args:
            redis_client: Redis client for caching (not used by this provider)
            **kwargs: Additional configuration options including:
                - speech_key: Azure Speech service key (required)
                - speech_region: Azure Speech service region (required)
        """
        self.speech_key = kwargs.get("speech_key")
        self.speech_region = kwargs.get("speech_region")
        
        if not self.speech_key or not self.speech_region:
            raise ValueError("Azure Speech API key and region are required")
        
        self.api_url = f"https://{self.speech_region}.tts.speech.microsoft.com/cognitiveservices/v1"
        self.current_voice = None
        
        # Default voice configuration
        self.voice_config = {
            "name": "en-US-JennyNeural",
            "language": "en-US",
            "gender": "Female",
            "style": "friendly"
        }
        
        # Cache for available voices
        self._voices = None
        
        logger.info("Azure TTS provider initialized")
    
    def generate_speech(self, text: str, voice_id: Optional[str] = None, 
                       speed: float = 1.0) -> Optional[bytes]:
        """
        Generate speech using Azure Speech API.
        
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
            
            # Create SSML document
            ssml = self._create_ssml(text, speed)
            
            # Prepare API request
            headers = {
                "Ocp-Apim-Subscription-Key": self.speech_key,
                "Content-Type": "application/ssml+xml",
                "X-Microsoft-OutputFormat": "riff-24khz-16bit-mono-pcm",
                "User-Agent": "MorningCoffeeApplication"
            }
            
            # Make API request
            start_time = time.time()
            response = requests.post(
                self.api_url,
                headers=headers,
                data=ssml.encode('utf-8')
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
    
    def _create_ssml(self, text: str, speed: float) -> str:
        """
        Create SSML document for Azure TTS.
        
        Args:
            text (str): Text to convert to speech
            speed (float): Speech speed factor
            
        Returns:
            str: SSML document
        """
        voice_name = self.voice_config["name"]
        style = self.voice_config.get("style", "")
        
        # Format rate attribute based on speed
        rate_str = ""
        if speed != 1.0:
            # Convert to percentage string (1.1 -> +10%, 0.9 -> -10%)
            percentage = int((speed - 1.0) * 100)
            if percentage > 0:
                rate_str = f' rate="+{percentage}%"'
            else:
                rate_str = f' rate="{percentage}%"'
        
        # Add style if available and not empty
        style_opening = f'<mstts:express-as style="{style}">' if style else ""
        style_closing = "</mstts:express-as>" if style else ""
        
        # Create SSML document
        ssml = f"""<?xml version="1.0" encoding="UTF-8"?>
<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" 
       xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="en-US">
    <voice name="{voice_name}">
        <prosody{rate_str}>
            {style_opening}{text}{style_closing}
        </prosody>
    </voice>
</speak>"""
        
        return ssml
    
    def get_voices(self) -> Dict[str, Any]:
        """
        Get available Azure voices.
        
        Returns:
            Dict[str, Any]: Dictionary containing available voices
        """
        if self._voices is None:
            try:
                token_url = f"https://{self.speech_region}.api.cognitive.microsoft.com/sts/v1.0/issuetoken"
                token_headers = {
                    "Ocp-Apim-Subscription-Key": self.speech_key
                }
                
                # Get authentication token
                token_response = requests.post(token_url, headers=token_headers)
                token_response.raise_for_status()
                access_token = token_response.text
                
                # Get voices list
                voices_url = f"https://{self.speech_region}.tts.speech.microsoft.com/cognitiveservices/voices/list"
                voices_headers = {
                    "Authorization": f"Bearer {access_token}"
                }
                
                response = requests.get(voices_url, headers=voices_headers)
                response.raise_for_status()
                
                voices_data = response.json()
                
                # Process voice data
                voice_dict = {}
                for voice in voices_data:
                    voice_name = voice.get("ShortName")
                    if not voice_name:
                        continue
                    
                    # Get voice ID
                    voice_id = voice_name  # Use ShortName as voice ID
                    
                    # Get style list if any
                    style_list = voice.get("StyleList", [])
                    
                    voice_dict[voice_id] = {
                        "name": voice.get("DisplayName", voice_name),
                        "language": voice.get("Locale", "unknown"),
                        "gender": voice.get("Gender", "unknown"),
                        "voice_type": voice.get("VoiceType", "unknown"),
                        "styles": style_list
                    }
                
                self._voices = voice_dict
                
            except Exception as e:
                logger.error(f"Error fetching Azure voices: {e}")
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
            # Parse voice ID format (can include style): "en-US-JennyNeural:cheerful"
            parts = voice_id.split(":")
            base_voice_id = parts[0]
            style = parts[1] if len(parts) > 1 else ""
            
            # Load voices if not already loaded
            if self._voices is None:
                self.get_voices()
            
            # Check if the voice exists
            if base_voice_id not in self._voices:
                logger.warning(f"Voice {base_voice_id} not found in available voices")
                return False
            
            # Check if the style is valid
            if style:
                voice_info = self._voices[base_voice_id]
                styles = voice_info.get("styles", [])
                
                if style not in styles:
                    logger.warning(f"Style {style} not available for voice {base_voice_id}")
                    style = ""  # Reset style if not available
            
            # Update voice configuration
            voice_info = self._voices[base_voice_id]
            self.voice_config = {
                "name": base_voice_id,
                "language": voice_info["language"],
                "gender": voice_info["gender"],
                "style": style
            }
            
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
        Check if the Azure Speech service is healthy.
        
        Returns:
            Dict[str, Any]: Health status information
        """
        try:
            # Try to get token to check API connectivity
            token_url = f"https://{self.speech_region}.api.cognitive.microsoft.com/sts/v1.0/issuetoken"
            token_headers = {
                "Ocp-Apim-Subscription-Key": self.speech_key
            }
            
            token_response = requests.post(token_url, headers=token_headers)
            token_response.raise_for_status()
            
            return {
                "status": "healthy",
                "engine": "Azure Cognitive Services Speech",
                "message": "API connection is functioning normally",
                "region": self.speech_region
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "engine": "Azure Cognitive Services Speech",
                "message": str(e)
            }
    
    def get_stream_info(self) -> Tuple[int, int, int]:
        """
        Get stream configuration information for audio playback.
        
        Returns:
            Tuple[int, int, int]: Audio format, number of channels, and sample rate
        """
        return pyaudio.paInt16, 1, 24000  # 16-bit, mono, 24kHz 