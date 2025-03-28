#!/usr/bin/env python
# OpenAI Transcription Handler for Morning Coffee application

import logging
import os
import tempfile
from typing import Optional, Dict, Any, List

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger("openai-transcription")

class OpenAITranscriptionHandler:
    """Handler for OpenAI's speech-to-text transcription service."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini-transcribe"):
        """
        Initialize the OpenAI transcription handler.
        
        Args:
            api_key (Optional[str]): OpenAI API key
            model (str): Model to use for transcription
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        
        self.model = model
        self.client = OpenAI(api_key=self.api_key)
        
        # Configuration
        self.default_prompt = "This is a phone call with short responses."
        self.language = "en"  # Default language
        
        logger.info(f"OpenAI transcription handler initialized with model: {model}")
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def transcribe_audio_data(self, audio_data: bytes, prompt: Optional[str] = None) -> Optional[str]:
        """
        Transcribe audio data using OpenAI's API.
        
        Args:
            audio_data (bytes): Audio data to transcribe
            prompt (Optional[str]): Optional prompt to guide transcription
            
        Returns:
            Optional[str]: Transcribed text or None if failed
        """
        try:
            if not audio_data:
                logger.warning("Empty audio data provided")
                return None
            
            # Create a temporary file for the audio data
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file_path = temp_file.name
                temp_file.write(audio_data)
            
            # Use a prompt if provided, otherwise use default
            transcription_prompt = prompt or self.default_prompt
            
            # Open the file and transcribe
            with open(temp_file_path, "rb") as audio_file:
                logger.debug(f"Transcribing audio with model: {self.model}")
                
                transcription = self.client.audio.transcriptions.create(
                    model=self.model,
                    file=audio_file,
                    prompt=transcription_prompt,
                    language=self.language
                )
            
            # Clean up temporary file
            os.unlink(temp_file_path)
            
            return transcription.text
            
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            
            # Make sure to clean up temporary file
            if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
            return None
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def transcribe_audio_url(self, audio_url: str, prompt: Optional[str] = None) -> Optional[str]:
        """
        Transcribe audio from a URL.
        
        Args:
            audio_url (str): URL of audio to transcribe
            prompt (Optional[str]): Optional prompt to guide transcription
            
        Returns:
            Optional[str]: Transcribed text or None if failed
        """
        try:
            import requests
            
            # Download the audio file
            response = requests.get(audio_url, timeout=30)
            response.raise_for_status()
            audio_data = response.content
            
            # Transcribe using the downloaded data
            return self.transcribe_audio_data(audio_data, prompt)
            
        except Exception as e:
            logger.error(f"Error downloading or transcribing audio from URL: {e}")
            return None
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check if the OpenAI transcription service is healthy.
        
        Returns:
            Dict[str, Any]: Health check result
        """
        try:
            # Generate a small audio sample to test
            test_response = self.client.chat.completions.create(
                model="gpt-4o-mini-tts",
                messages=[
                    {"role": "system", "content": "You are a text-to-speech service."},
                    {"role": "user", "content": "Test audio for transcription."}
                ],
                audio={"voice": "alloy", "format": "wav"},
                max_tokens=10
            )
            
            audio_data = test_response.audio_content
            
            # Try to transcribe the test audio
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file_path = temp_file.name
                temp_file.write(audio_data)
            
            with open(temp_file_path, "rb") as audio_file:
                transcription = self.client.audio.transcriptions.create(
                    model=self.model,
                    file=audio_file
                )
            
            # Clean up temporary file
            os.unlink(temp_file_path)
            
            return {
                "status": "healthy",
                "model": self.model,
                "message": "OpenAI transcription API is functioning normally",
                "test_transcription": transcription.text
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            
            # Clean up temporary file if it exists
            if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
            return {
                "status": "unhealthy",
                "model": self.model,
                "message": str(e)
            }
    
    def set_model(self, model: str) -> bool:
        """
        Change the transcription model.
        
        Args:
            model (str): New model to use
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Validate the model name
            if model not in ["gpt-4o-transcribe", "gpt-4o-mini-transcribe"]:
                logger.warning(f"Unsupported model: {model}")
                return False
                
            self.model = model
            logger.info(f"Transcription model changed to: {model}")
            return True
            
        except Exception as e:
            logger.error(f"Error changing transcription model: {e}")
            return False 