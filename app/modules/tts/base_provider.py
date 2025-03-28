#!/usr/bin/env python
# Base TTS Provider for Morning Coffee application

import logging
from typing import Dict, Any, Optional, Tuple, Generator
from abc import ABC, abstractmethod

logger = logging.getLogger("tts-base")

class BaseTTSProvider(ABC):
    """Base abstract class for TTS providers."""
    
    @abstractmethod
    def generate_speech(self, text: str, voice_id: Optional[str] = None, 
                       speed: float = 1.0) -> Optional[bytes]:
        """
        Generate speech from text.
        
        Args:
            text (str): Text to convert to speech
            voice_id (Optional[str]): Voice identifier
            speed (float): Speech speed factor
            
        Returns:
            Optional[bytes]: Audio data as bytes or None if generation failed
        """
        pass
    
    @abstractmethod
    def get_voices(self) -> Dict[str, Any]:
        """
        Get available voices.
        
        Returns:
            Dict[str, Any]: Dictionary containing available voices
        """
        pass
    
    @abstractmethod
    def set_voice(self, voice_id: str) -> bool:
        """
        Set voice to use for TTS.
        
        Args:
            voice_id (str): Voice identifier
            
        Returns:
            bool: True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def voice_exists(self, voice_id: str) -> bool:
        """
        Check if voice exists.
        
        Args:
            voice_id (str): Voice identifier
            
        Returns:
            bool: True if voice exists, False otherwise
        """
        pass
    
    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """
        Check if the TTS service is healthy.
        
        Returns:
            Dict[str, Any]: Health status information
        """
        pass
    
    def get_stream_info(self) -> Tuple[int, int, int]:
        """
        Get stream configuration information for audio playback.
        Must be implemented by providers that need custom audio format.
        
        Returns:
            Tuple[int, int, int]: Audio format, number of channels, and sample rate
        """
        # Default implementation (typically 16-bit signed PCM, mono, 16kHz)
        import pyaudio
        return pyaudio.paInt16, 1, 16000 

class StreamingTTSProvider(BaseTTSProvider):
    """Base abstract class for streaming-capable TTS providers."""
    
    @abstractmethod
    def generate_speech_stream(self, text: str, voice_id: Optional[str] = None, 
                             speed: float = 1.0) -> Generator[bytes, None, None]:
        """
        Generate speech as a stream of audio chunks.
        
        Args:
            text (str): Text to convert to speech
            voice_id (Optional[str]): Voice identifier
            speed (float): Speech speed factor
            
        Returns:
            Generator[bytes, None, None]: Generator of audio chunks
        """
        pass
    
    @abstractmethod
    def begin_streaming_session(self, session_id: str, voice_id: Optional[str] = None, 
                             speed: float = 1.0) -> bool:
        """
        Begin a streaming session for incremental speech generation.
        
        Args:
            session_id (str): Unique session identifier
            voice_id (Optional[str]): Voice identifier
            speed (float): Speech speed factor
            
        Returns:
            bool: True if session was started successfully
        """
        pass
    
    @abstractmethod
    def add_text_to_stream(self, session_id: str, text: str) -> bool:
        """
        Add text to an existing streaming session.
        
        Args:
            session_id (str): Session identifier
            text (str): Text to add to the stream
            
        Returns:
            bool: True if text was added successfully
        """
        pass
    
    @abstractmethod
    def end_streaming_session(self, session_id: str) -> bool:
        """
        End a streaming session and clean up resources.
        
        Args:
            session_id (str): Session identifier
            
        Returns:
            bool: True if session was ended successfully
        """
        pass 