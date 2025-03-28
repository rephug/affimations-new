#!/usr/bin/env python
# Kokoro TTS Provider Module for Morning Coffee application

import logging
import tempfile
import os
import time
import traceback
from typing import Dict, Any, Optional, Tuple

import pyaudio
try:
    from RealtimeTTS import TextToAudioStream, KokoroEngine
except ImportError:
    logging.warning("RealtimeTTS not installed, Kokoro TTS provider will not work")

from ..base_provider import BaseTTSProvider

logger = logging.getLogger("kokoro-provider")

class KokoroProvider(BaseTTSProvider):
    """TTS provider using Kokoro engine via RealtimeTTS."""
    
    def __init__(self, redis_client=None, **kwargs):
        """
        Initialize Kokoro provider.
        
        Args:
            redis_client: Redis client for caching (not used by this provider)
            **kwargs: Additional configuration options
        """
        try:
            self.engine = KokoroEngine()
            self.current_voice = None
            
            # Cache for available voices
            self._voices = None
            
            # Load voice mapping
            self._voice_mapping = {
                "en_female_1": "en_female",
                "en_female_2": "en_female_bright",
                "en_male_1": "en_male",
                "en_male_2": "en_male_deep",
                "en_us_amy": "en_us_amy",
                "en_us_andy": "en_us_andy",
                "en_us_ashley": "en_us_ashley",
                "en_gb_charlie": "en_gb_charlie",
                "en_gb_emma": "en_gb_emma",
                "en_gb_john": "en_gb_john"
            }
            
            logger.info("Kokoro TTS provider initialized")
        except NameError:
            logger.error("Cannot initialize Kokoro TTS provider. RealtimeTTS not installed.")
            raise ImportError("RealtimeTTS not installed. Please install with: pip install RealtimeTTS")
    
    def generate_speech(self, text: str, voice_id: Optional[str] = None, 
                       speed: float = 1.0) -> Optional[bytes]:
        """
        Generate speech using Kokoro engine.
        
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
            
            # Set voice if provided and different from current
            if voice_id and voice_id != self.current_voice:
                self.set_voice(voice_id)
            
            logger.debug(f"Generating speech for text: {text[:50]}{'...' if len(text) > 50 else ''}")
            
            # Create a temporary file to store the audio
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                output_path = temp_file.name
            
            # Create stream and generate audio
            start_time = time.time()
            
            # Create a TextToAudioStream with the engine
            stream = TextToAudioStream(self.engine, muted=True)
            stream.feed(text)
            stream.play(output_wavfile=output_path, log_synthesized_text=False)
            
            generation_time = time.time() - start_time
            logger.debug(f"Speech generation took {generation_time:.2f} seconds")
            
            # Read the generated WAV file
            with open(output_path, 'rb') as audio_file:
                audio_data = audio_file.read()
            
            # Clean up the temporary file
            os.unlink(output_path)
            
            return audio_data
            
        except Exception as e:
            logger.error(f"Error generating speech: {e}")
            logger.debug(traceback.format_exc())
            return None
    
    def get_voices(self) -> Dict[str, Any]:
        """
        Get available Kokoro voices.
        
        Returns:
            Dict[str, Any]: Dictionary containing available voices
        """
        if self._voices is None:
            # Kokoro has a fixed set of voices
            voices = {
                "en_female_1": {"name": "English Female 1", "description": "Standard female voice", "language": "en"},
                "en_female_2": {"name": "English Female 2", "description": "Bright female voice", "language": "en"},
                "en_male_1": {"name": "English Male 1", "description": "Standard male voice", "language": "en"},
                "en_male_2": {"name": "English Male 2", "description": "Deep male voice", "language": "en"},
                "en_us_amy": {"name": "Amy (US)", "description": "US female voice", "language": "en-US"},
                "en_us_andy": {"name": "Andy (US)", "description": "US male voice", "language": "en-US"},
                "en_us_ashley": {"name": "Ashley (US)", "description": "US female voice", "language": "en-US"},
                "en_gb_charlie": {"name": "Charlie (GB)", "description": "UK male voice", "language": "en-GB"},
                "en_gb_emma": {"name": "Emma (GB)", "description": "UK female voice", "language": "en-GB"},
                "en_gb_john": {"name": "John (GB)", "description": "UK male voice", "language": "en-GB"}
            }
            self._voices = voices
        
        return {"voices": self._voices}
    
    def set_voice(self, voice_id: str) -> bool:
        """
        Set voice to use for TTS.
        
        Args:
            voice_id (str): Voice identifier
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if voice_id in self._voice_mapping:
                # Map to internal voice name if needed
                self.current_voice = voice_id
                logger.debug(f"Voice set to {voice_id}")
                return True
            else:
                logger.warning(f"Voice {voice_id} not found")
                return False
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
        return voice_id in self._voice_mapping or voice_id in self.get_voices()["voices"]
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check if the TTS service is healthy.
        
        Returns:
            Dict[str, Any]: Health status information
        """
        try:
            # Test by generating a small audio sample
            _ = self.generate_speech("Test", voice_id="en_female_1")
            return {
                "status": "healthy",
                "engine": "Kokoro via RealtimeTTS",
                "message": "Engine is functioning normally"
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "engine": "Kokoro via RealtimeTTS",
                "message": str(e)
            }
    
    def get_stream_info(self) -> Tuple[int, int, int]:
        """
        Get stream configuration information for audio playback.
        
        Returns:
            Tuple[int, int, int]: Audio format, number of channels, and sample rate
        """
        return pyaudio.paInt16, 1, 24000  # 16-bit, mono, 24kHz 