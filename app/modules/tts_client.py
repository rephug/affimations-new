#!/usr/bin/env python
# Spark TTS Client Module for Morning Coffee application

import logging
import requests
from typing import Optional, Dict, Any, Union, Tuple
from tenacity import retry, stop_after_attempt, wait_exponential

# Configure logging
logger = logging.getLogger("tts-client")

class SparkTTSClient:
    """Client for interacting with the Spark TTS service."""
    
    def __init__(self, base_url: str, timeout: int = 30):
        """
        Initialize the Spark TTS client.
        
        Args:
            base_url (str): Base URL of the Spark TTS service
            timeout (int): Default timeout in seconds for API calls
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the Spark TTS service.
        
        Returns:
            Dict[str, Any]: Health status information
        """
        try:
            response = requests.get(f"{self.base_url}/health", timeout=self.timeout)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Health check failed with status {response.status_code}: {response.text}")
                return {"status": "unhealthy", "message": response.text}
        except Exception as e:
            logger.error(f"Error checking Spark TTS health: {e}")
            return {"status": "unhealthy", "message": str(e)}
    
    # Add an alias for health_check to maintain compatibility with app.py
    def health(self) -> Dict[str, Any]:
        """
        Alias for health_check() method to maintain API compatibility.
        
        Returns:
            Dict[str, Any]: Health status information
        """
        return self.health_check()
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_voices(self) -> Dict[str, Any]:
        """
        Get available voices from the Spark TTS service.
        
        Returns:
            Dict[str, Any]: Available voices information
        """
        try:
            response = requests.get(f"{self.base_url}/voices", timeout=self.timeout)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Get voices failed with status {response.status_code}: {response.text}")
                return {"voices": []}
        except Exception as e:
            logger.error(f"Error getting voices from Spark TTS: {e}")
            return {"voices": []}
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def generate_speech(self, text: str, voice_id: Optional[str] = None, 
                         speed: float = 1.0, seed: Optional[int] = None) -> Optional[bytes]:
        """
        Generate speech from text.
        
        Args:
            text (str): The text to convert to speech
            voice_id (Optional[str]): Voice ID to use, defaults to server default
            speed (float): Speech speed factor (1.0 = normal)
            seed (Optional[int]): Random seed for reproducibility
            
        Returns:
            Optional[bytes]: Audio data as bytes or None if generation failed
        """
        try:
            # Prepare the request payload
            payload = {
                "text": text,
                "speed": speed
            }
            
            # Add optional parameters if provided
            if voice_id:
                payload["voice_id"] = voice_id
            
            if seed is not None:
                payload["seed"] = seed
            
            logger.info(f"Generating speech for text: {text[:50]}{'...' if len(text) > 50 else ''}")
            
            # Send request to the Spark TTS service
            response = requests.post(
                f"{self.base_url}/generate",
                json=payload,
                timeout=self.timeout  # Use class-level timeout
            )
            
            if response.status_code == 200:
                return response.content
            else:
                logger.error(f"Speech generation failed with status {response.status_code}: {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error generating speech with Spark TTS: {e}")
            return None
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_service_info(self) -> Dict[str, Any]:
        """
        Get information about the Spark TTS service.
        
        Returns:
            Dict[str, Any]: Service information
        """
        try:
            response = requests.get(f"{self.base_url}/info", timeout=self.timeout)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Get info failed with status {response.status_code}: {response.text}")
                return {}
        except Exception as e:
            logger.error(f"Error getting Spark TTS service info: {e}")
            return {} 