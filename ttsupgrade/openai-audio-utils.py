#!/usr/bin/env python
# OpenAI Audio Utilities for Morning Coffee application

import os
import base64
import tempfile
import logging
from typing import Optional, Dict, Any, Union, Tuple

import requests
from openai import OpenAI

logger = logging.getLogger("openai-audio-utils")

class OpenAIAudioUtils:
    """Utility functions for working with OpenAI's audio APIs."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize OpenAI audio utilities.
        
        Args:
            api_key (Optional[str]): OpenAI API key, defaults to OPENAI_API_KEY environment variable
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        
        # Initialize client
        self.client = OpenAI(api_key=self.api_key)
        
        logger.info("OpenAI audio utilities initialized")
    
    def transcribe_audio(self, audio_data: bytes, model: str = "gpt-4o-transcribe") -> Optional[str]:
        """
        Transcribe audio data using OpenAI's transcription API.
        
        Args:
            audio_data (bytes): Audio data to transcribe
            model (str): Model to use for transcription (gpt-4o-transcribe or gpt-4o-mini-transcribe)
            
        Returns:
            Optional[str]: Transcribed text or None if transcription failed
        """
        try:
            # Save audio data to a temporary file for the API
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file_path = temp_file.name
                temp_file.write(audio_data)
            
            logger.info(f"Transcribing audio using {model}")
            
            # Use the file with OpenAI's API
            with open(temp_file_path, "rb") as audio_file:
                transcription = self.client.audio.transcriptions.create(
                    model=model,
                    file=audio_file
                )
            
            # Clean up temporary file
            os.unlink(temp_file_path)
            
            return transcription.text
            
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            # Make sure to clean up even if there's an error
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            return None
    
    def text_to_speech(self, 
                       text: str, 
                       voice_style: str = "Speak in a natural, warm tone", 
                       model: str = "gpt-4o-mini-tts") -> Optional[bytes]:
        """
        Convert text to speech using OpenAI's text-to-speech API.
        
        Args:
            text (str): Text to convert to speech
            voice_style (str): Voice style instruction
            model (str): Model to use (gpt-4o-mini-tts)
            
        Returns:
            Optional[bytes]: Audio data as bytes or None if generation failed
        """
        try:
            # Prepare the prompt with voice style
            prompt = f"{voice_style}. {text}"
            
            # Use the client to generate audio
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a text-to-speech service."},
                    {"role": "user", "content": prompt}
                ],
                audio={"voice": "alloy", "format": "wav"},
                max_tokens=1024
            )
            
            return response.audio_content
            
        except Exception as e:
            logger.error(f"Error generating speech: {e}")
            return None
    
    def download_audio_url(self, url: str) -> Optional[bytes]:
        """
        Download audio from URL.
        
        Args:
            url (str): URL of audio file
            
        Returns:
            Optional[bytes]: Audio data as bytes or None if download failed
        """
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.content
        except Exception as e:
            logger.error(f"Error downloading audio: {e}")
            return None
    
    def encode_audio_base64(self, audio_data: bytes) -> str:
        """
        Encode audio data as base64.
        
        Args:
            audio_data (bytes): Audio data to encode
            
        Returns:
            str: Base64-encoded audio data
        """
        return base64.b64encode(audio_data).decode("utf-8")
    
    def decode_audio_base64(self, base64_data: str) -> bytes:
        """
        Decode base64 audio data.
        
        Args:
            base64_data (str): Base64-encoded audio data
            
        Returns:
            bytes: Decoded audio data
        """
        return base64.b64decode(base64_data)
    
    def get_estimated_cost(self, audio_length_seconds: float, is_tts: bool = True) -> float:
        """
        Calculate estimated cost for audio processing.
        
        Args:
            audio_length_seconds (float): Length of audio in seconds
            is_tts (bool): Whether this is for TTS (True) or transcription (False)
            
        Returns:
            float: Estimated cost in USD
        """
        # Pricing as of March 2025
        if is_tts:
            # gpt-4o-mini-tts: $0.015 per minute
            return (audio_length_seconds / 60) * 0.015
        else:
            # gpt-4o-mini-transcribe: $0.003 per minute
            # gpt-4o-transcribe: $0.006 per minute (using the more expensive one)
            return (audio_length_seconds / 60) * 0.006
