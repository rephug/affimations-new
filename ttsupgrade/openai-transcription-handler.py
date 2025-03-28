#!/usr/bin/env python
# OpenAI Transcription Handler Module for Morning Coffee application

import os
import logging
import json
import time
import tempfile
from typing import Optional, Dict, Any, List, Union

import requests
from tenacity import retry, stop_after_attempt, wait_exponential
from openai import OpenAI

logger = logging.getLogger("openai-transcription-handler")

class OpenAITranscriptionHandler:
    """Handler for OpenAI's new transcription API using gpt-4o-transcribe models."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini-transcribe"):
        """
        Initialize the OpenAI transcription handler.
        
        Args:
            api_key (Optional[str]): OpenAI API key, defaults to OPENAI_API_KEY environment variable
            model (str): Transcription model to use (gpt-4o-transcribe or gpt-4o-mini-transcribe)
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        
        self.model = model
        
        # Initialize client
        self.client = OpenAI(api_key=self.api_key)
        
        logger.info(f"OpenAI transcription handler initialized with model {self.model}")
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def submit_transcription(self, audio_data: Union[bytes, str]) -> Optional[Dict[str, Any]]:
        """
        Submit audio data for transcription.
        
        Args:
            audio_data (Union[bytes, str]): Audio data as bytes or URL to audio file
            
        Returns:
            Optional[Dict[str, Any]]: Transcription result or None if failed
        """
        try:
            # Check if audio_data is a URL
            if isinstance(audio_data, str) and (audio_data.startswith('http://') or audio_data.startswith('https://')):
                # Download the audio file
                response = requests.get(audio_data, timeout=30)
                response.raise_for_status()
                audio_bytes = response.content
            else:
                # Use the provided bytes
                audio_bytes = audio_data
            
            # Save to a temporary file for the API
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file_path = temp_file.name
                if isinstance(audio_bytes, bytes):
                    temp_file.write(audio_bytes)
                else:
                    temp_file.write(audio_bytes.encode())
            
            logger.info(f"Submitting audio for transcription using {self.model}")
            
            # Transcribe using the OpenAI API
            with open(temp_file_path, "rb") as audio_file:
                transcription = self.client.audio.transcriptions.create(
                    model=self.model,
                    file=audio_file
                )
            
            # Clean up temporary file
            os.unlink(temp_file_path)
            
            result = {
                "job_id": transcription.id,  # Note: This is a simulated job ID since the API returns complete results
                "status": "completed",
                "text": transcription.text
            }
            
            logger.info(f"Transcription completed with {len(transcription.text)} characters")
            return result
            
        except Exception as e:
            logger.error(f"Error submitting transcription to OpenAI: {e}")
            # Ensure temporary file is cleaned up
            if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            return None
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def check_transcription_status(self, job_id: str) -> Dict[str, Any]:
        """
        Check the status of a transcription job.
        
        Note: For OpenAI's new transcription models, results are immediate, so this is a compatibility
        function that simulates the behavior of AssemblyAI's API.
        
        Args:
            job_id (str): The ID of the transcription job
            
        Returns:
            Dict[str, Any]: Status information with text if completed
        """
        # For OpenAI's new transcription API, the result is returned immediately
        # so we don't need to check status. This is a compatibility function.
        return {
            "status": "completed",
            "text": "Transcription completed"  # This would normally be populated with the actual transcription
        }
    
    def transcribe_sync(self, audio_data: Union[bytes, str]) -> Optional[str]:
        """
        Transcribe audio synchronously (convenience method).
        
        Args:
            audio_data (Union[bytes, str]): Audio data as bytes or URL to audio file
            
        Returns:
            Optional[str]: Transcribed text or None if transcription failed
        """
        result = self.submit_transcription(audio_data)
        if result and result["status"] == "completed":
            return result["text"]
        return None
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the OpenAI transcription API.
        
        Returns:
            Dict[str, Any]: Health status
        """
        try:
            # Create a small test audio file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file_path = temp_file.name
                # Write a very short audio file (essentially empty)
                temp_file.write(b'RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x00\x04\x00\x00\x00\x04\x00\x00\x01\x00\x08\x00data\x00\x00\x00\x00')
            
            # Test with the API
            with open(temp_file_path, "rb") as audio_file:
                try:
                    # Just check if the API endpoint is accessible, don't worry about the result
                    self.client.audio.transcriptions.create(
                        model=self.model,
                        file=audio_file,
                        max_tokens=1
                    )
                    status = "healthy"
                except Exception as e:
                    status = "unhealthy"
                    logger.error(f"API health check failed: {e}")
            
            # Clean up temporary file
            os.unlink(temp_file_path)
            
            return {
                "status": status,
                "model": self.model,
                "message": "API connection is functioning normally" if status == "healthy" else "API connection failed"
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            # Ensure temporary file is cleaned up
            if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            return {
                "status": "unhealthy",
                "model": self.model,
                "message": f"Health check error: {str(e)}"
            }
