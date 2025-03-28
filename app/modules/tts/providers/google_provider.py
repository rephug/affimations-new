#!/usr/bin/env python
# Google Cloud TTS Provider with Chirp3 voice support

import logging
import os
import tempfile
import time
import uuid
from typing import Dict, Any, Optional, Generator, List, Tuple

from ..base_provider import StreamingTTSProvider
from ..text_processing import TextFragmenter
from ..events import TTSEventType

logger = logging.getLogger("tts-google")

class EnhancedGoogleProvider(StreamingTTSProvider):
    """
    Enhanced Google Cloud TTS provider with streaming and Chirp3 support.
    
    This provider integrates with Google Cloud Text-to-Speech API to support
    high-quality Chirp3 voices with streaming capabilities for minimal latency.
    """
    
    def __init__(self, 
                config: Optional[Dict[str, Any]] = None,
                event_emitter = None,
                **kwargs):
        """
        Initialize the Google Cloud TTS provider.
        
        Args:
            config (Optional[Dict[str, Any]]): Provider configuration
            event_emitter: Optional event emitter for monitoring
            **kwargs: Additional parameters
        """
        self.config = config or {}
        self.event_emitter = event_emitter
        
        # Credentials setup
        self.credentials_path = self.config.get("credentials_path")
        if self.credentials_path:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.credentials_path
        
        # Initialize Google Cloud TTS client
        try:
            from google.cloud import texttospeech
            self.client = texttospeech.TextToSpeechClient()
            self.texttospeech = texttospeech  # Store reference to module
            self.tts_available = True
        except ImportError:
            logger.error("Google Cloud TTS not installed. Please install with 'pip install google-cloud-texttospeech'")
            self.tts_available = False
        except Exception as e:
            logger.error(f"Error initializing Google Cloud TTS client: {e}")
            self.tts_available = False
        
        # Voice configuration
        self.voice_config = {
            "language_code": self.config.get("language_code", "en-US"),
            "name": self.config.get("voice_name", "en-US-Chirp3-Standard-F"),
            "ssml_gender": self.config.get("gender", "FEMALE")
        }
        
        # Chirp3 configuration
        self.use_chirp3 = self.config.get("use_chirp3", True)
        if self.use_chirp3:
            self.chirp3_voices = [
                "en-US-Chirp3-Standard-F",
                "en-US-Chirp3-Standard-M",
                "en-US-Chirp3-Polyglot",
                "en-US-Chirp3-Studio"
            ]
            # Default to first Chirp3 voice if not specified or not a Chirp3 voice
            if not self.voice_config["name"] in self.chirp3_voices:
                self.voice_config["name"] = self.chirp3_voices[0]
        
        # Stream configuration
        self.chunk_size = self.config.get("chunk_size", 4096)
        self.buffer_threshold = self.config.get("buffer_threshold", 0.2)  # seconds
        self.max_sentence_length = self.config.get("max_sentence_length", 100)
        
        # Text processor for sentence splitting
        self.text_processor = TextFragmenter(
            min_fragment_size=self.config.get("min_fragment_size", 5),
            max_fragment_size=self.config.get("max_fragment_size", 100),
            fast_first_response=self.config.get("fast_first_response", True)
        )
        
        # Active streaming sessions
        self.active_sessions = {}
        
        logger.info("EnhancedGoogleProvider initialized")
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check if the Google Cloud TTS service is healthy.
        
        Returns:
            Dict[str, Any]: Health status information
        """
        status = {
            "service": "google",
            "status": "healthy" if self.tts_available else "unavailable", 
            "timestamp": time.time()
        }
        
        if not self.tts_available:
            status["error"] = "Google Cloud TTS client not available"
            return status
        
        # Try a simple TTS request to verify the service is working
        try:
            text = "Test"
            input_text = self.texttospeech.SynthesisInput(text=text)
            
            voice = self.texttospeech.VoiceSelectionParams(
                language_code=self.voice_config["language_code"],
                name=self.voice_config["name"]
            )
            
            audio_config = self.texttospeech.AudioConfig(
                audio_encoding=self.texttospeech.AudioEncoding.LINEAR16,
                sample_rate_hertz=24000
            )
            
            self.client.synthesize_speech(
                input=input_text,
                voice=voice,
                audio_config=audio_config
            )
            
            status["detail"] = "API connection successful"
        except Exception as e:
            status["status"] = "unhealthy"
            status["error"] = str(e)
        
        return status
    
    def get_voices(self) -> Dict[str, Any]:
        """
        Get available voices.
        
        Returns:
            Dict[str, Any]: Dictionary containing available voices
        """
        if not self.tts_available:
            return {"voices": []}
        
        try:
            # Request the list of voices from Google Cloud TTS
            response = self.client.list_voices()
            
            voices = []
            for voice in response.voices:
                voice_data = {
                    "id": voice.name,
                    "name": voice.name,
                    "gender": voice.ssml_gender.name,
                    "language": voice.language_codes[0]
                }
                # Highlight Chirp3 voices
                if self.use_chirp3 and any(chirp_voice in voice.name for chirp_voice in self.chirp3_voices):
                    voice_data["is_chirp3"] = True
                
                voices.append(voice_data)
            
            return {"voices": voices}
        except Exception as e:
            logger.error(f"Error getting Google voices: {e}")
            return {"voices": []}
    
    def set_voice(self, voice_id: str) -> bool:
        """
        Set voice to use for TTS.
        
        Args:
            voice_id (str): Voice identifier
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.tts_available:
            return False
        
        try:
            # If using Chirp3, ensure it's a valid Chirp3 voice if specified
            if self.use_chirp3 and not any(chirp_voice in voice_id for chirp_voice in self.chirp3_voices):
                logger.warning(f"Voice {voice_id} is not a Chirp3 voice, using anyway")
            
            # Extract language code from voice name (e.g., en-US-Chirp3-Standard-F -> en-US)
            parts = voice_id.split('-')
            if len(parts) >= 2:
                language_code = f"{parts[0]}-{parts[1]}"
                self.voice_config["language_code"] = language_code
            
            self.voice_config["name"] = voice_id
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
        if not self.tts_available:
            return False
        
        try:
            voices = self.get_voices()
            return any(voice["id"] == voice_id for voice in voices.get("voices", []))
        except Exception as e:
            logger.error(f"Error checking if voice exists: {e}")
            return False
    
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
        if not self.tts_available:
            logger.error("Google Cloud TTS client not available")
            return None
        
        if not text:
            logger.warning("Empty text provided to Google TTS")
            return None
        
        try:
            # Set voice if provided
            if voice_id:
                self.set_voice(voice_id)
            
            # Emit event if available
            if self.event_emitter:
                self.event_emitter.create_and_emit(
                    TTSEventType.GENERATION_START,
                    provider_type="google",
                    text_length=len(text),
                    voice_id=voice_id or self.voice_config["name"]
                )
            
            start_time = time.time()
            
            # Prepare input
            input_text = self.texttospeech.SynthesisInput(text=text)
            
            # Configure voice
            voice = self.texttospeech.VoiceSelectionParams(
                language_code=self.voice_config["language_code"],
                name=self.voice_config["name"]
            )
            
            # Configure audio output
            audio_config = self.texttospeech.AudioConfig(
                audio_encoding=self.texttospeech.AudioEncoding.LINEAR16,
                speaking_rate=speed,
                sample_rate_hertz=24000
            )
            
            # Make API request
            response = self.client.synthesize_speech(
                input=input_text,
                voice=voice,
                audio_config=audio_config
            )
            
            # Get audio content
            audio_data = response.audio_content
            
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Emit event if available
            if self.event_emitter:
                self.event_emitter.create_and_emit(
                    TTSEventType.GENERATION_END,
                    provider_type="google",
                    text_length=len(text),
                    duration_ms=duration_ms,
                    voice_id=voice_id or self.voice_config["name"]
                )
            
            return audio_data
            
        except Exception as e:
            logger.error(f"Error generating speech with Google TTS: {e}")
            
            # Emit error event if available
            if self.event_emitter:
                self.event_emitter.create_and_emit(
                    TTSEventType.GENERATION_ERROR,
                    provider_type="google",
                    text_length=len(text),
                    error_message=str(e),
                    voice_id=voice_id or self.voice_config["name"]
                )
            
            return None
    
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
        if not self.tts_available:
            logger.error("Google Cloud TTS client not available")
            return
        
        if not text:
            logger.warning("Empty text provided to Google TTS streaming")
            return
        
        try:
            # Set voice if provided
            if voice_id:
                self.set_voice(voice_id)
            
            # Emit event if available
            if self.event_emitter:
                self.event_emitter.create_and_emit(
                    TTSEventType.STREAMING_START,
                    provider_type="google",
                    text_length=len(text),
                    voice_id=voice_id or self.voice_config["name"]
                )
            
            # Get the initial fragment for immediate playback
            initial_fragment = self.text_processor.get_initial_fragment(text)
            
            if initial_fragment:
                # Generate initial fragment immediately for low latency
                input_text = self.texttospeech.SynthesisInput(text=initial_fragment)
                
                voice = self.texttospeech.VoiceSelectionParams(
                    language_code=self.voice_config["language_code"],
                    name=self.voice_config["name"]
                )
                
                audio_config = self.texttospeech.AudioConfig(
                    audio_encoding=self.texttospeech.AudioEncoding.LINEAR16,
                    speaking_rate=speed,
                    sample_rate_hertz=24000
                )
                
                response = self.client.synthesize_speech(
                    input=input_text,
                    voice=voice,
                    audio_config=audio_config
                )
                
                # Stream the audio in chunks
                audio_data = response.audio_content
                for i in range(0, len(audio_data), self.chunk_size):
                    chunk = audio_data[i:i+self.chunk_size]
                    # Emit chunk event if available
                    if self.event_emitter:
                        self.event_emitter.create_and_emit(
                            TTSEventType.STREAMING_CHUNK,
                            provider_type="google",
                            additional_data={"chunk_size": len(chunk)}
                        )
                    yield chunk
            
            # Process remaining text by sentences
            sentences = self.text_processor.split_into_sentences(text)
            if initial_fragment and sentences:
                # Skip first sentence if we already processed the initial fragment
                if sentences[0].startswith(initial_fragment):
                    remaining_part = sentences[0][len(initial_fragment):].strip()
                    if remaining_part:
                        sentences[0] = remaining_part
                    else:
                        sentences = sentences[1:]
            
            for sentence in sentences:
                # Skip empty sentences
                if not sentence.strip():
                    continue
                    
                # Process in smaller chunks if sentence is too long
                if len(sentence) > self.max_sentence_length:
                    chunks = [sentence[i:i+self.max_sentence_length] 
                            for i in range(0, len(sentence), self.max_sentence_length)]
                else:
                    chunks = [sentence]
                
                for chunk in chunks:
                    # Generate speech for the chunk
                    input_text = self.texttospeech.SynthesisInput(text=chunk)
                    
                    voice = self.texttospeech.VoiceSelectionParams(
                        language_code=self.voice_config["language_code"],
                        name=self.voice_config["name"]
                    )
                    
                    audio_config = self.texttospeech.AudioConfig(
                        audio_encoding=self.texttospeech.AudioEncoding.LINEAR16,
                        speaking_rate=speed,
                        sample_rate_hertz=24000
                    )
                    
                    response = self.client.synthesize_speech(
                        input=input_text,
                        voice=voice,
                        audio_config=audio_config
                    )
                    
                    # Stream the audio in chunks
                    audio_data = response.audio_content
                    for i in range(0, len(audio_data), self.chunk_size):
                        audio_chunk = audio_data[i:i+self.chunk_size]
                        # Emit chunk event if available
                        if self.event_emitter:
                            self.event_emitter.create_and_emit(
                                TTSEventType.STREAMING_CHUNK,
                                provider_type="google",
                                additional_data={"chunk_size": len(audio_chunk)}
                            )
                        yield audio_chunk
            
            # Emit end event if available
            if self.event_emitter:
                self.event_emitter.create_and_emit(
                    TTSEventType.STREAMING_END,
                    provider_type="google",
                    text_length=len(text),
                    voice_id=voice_id or self.voice_config["name"]
                )
            
        except Exception as e:
            logger.error(f"Error in Google speech streaming: {e}")
            
            # Emit error event if available
            if self.event_emitter:
                self.event_emitter.create_and_emit(
                    TTSEventType.STREAMING_ERROR,
                    provider_type="google",
                    text_length=len(text),
                    error_message=str(e),
                    voice_id=voice_id or self.voice_config["name"]
                )
    
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
        if not self.tts_available:
            logger.error("Google Cloud TTS client not available")
            return False
        
        try:
            if session_id in self.active_sessions:
                logger.warning(f"Session {session_id} already exists, ending previous session")
                self.end_streaming_session(session_id)
            
            # Set voice if provided
            if voice_id:
                self.set_voice(voice_id)
            
            # Store session data
            self.active_sessions[session_id] = {
                "voice_id": voice_id or self.voice_config["name"],
                "speed": speed,
                "created_at": time.time(),
                "last_activity": time.time(),
                "text_buffer": "",
                "audio_buffer": bytearray(),
                "processed_sentences": []
            }
            
            # Emit event if available
            if self.event_emitter:
                self.event_emitter.create_and_emit(
                    TTSEventType.SESSION_START,
                    provider_type="google",
                    session_id=session_id,
                    voice_id=voice_id or self.voice_config["name"]
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Error starting Google streaming session: {e}")
            
            # Emit error event if available
            if self.event_emitter:
                self.event_emitter.create_and_emit(
                    TTSEventType.SESSION_ERROR,
                    provider_type="google",
                    session_id=session_id,
                    error_message=str(e),
                    voice_id=voice_id or self.voice_config["name"]
                )
            
            return False
    
    def add_text_to_stream(self, session_id: str, text: str) -> bool:
        """
        Add text to an existing streaming session.
        
        Args:
            session_id (str): Session identifier
            text (str): Text to add to the stream
            
        Returns:
            bool: True if text was added successfully
        """
        if not self.tts_available:
            logger.error("Google Cloud TTS client not available")
            return False
        
        if not session_id in self.active_sessions:
            logger.error(f"Session {session_id} not found")
            return False
        
        try:
            # Get session data
            session = self.active_sessions[session_id]
            session["last_activity"] = time.time()
            
            # Add text to buffer
            session["text_buffer"] += text
            
            # Process buffer if it contains complete sentences
            sentences = self.text_processor.split_into_sentences(session["text_buffer"])
            
            if len(sentences) > 1:
                # Process all but the last sentence (which may be incomplete)
                for sentence in sentences[:-1]:
                    # Skip if we've already processed this sentence
                    if sentence in session["processed_sentences"]:
                        continue
                    
                    # Generate speech for the sentence
                    input_text = self.texttospeech.SynthesisInput(text=sentence)
                    
                    voice = self.texttospeech.VoiceSelectionParams(
                        language_code=self.voice_config["language_code"],
                        name=self.voice_config["name"]
                    )
                    
                    audio_config = self.texttospeech.AudioConfig(
                        audio_encoding=self.texttospeech.AudioEncoding.LINEAR16,
                        speaking_rate=session["speed"],
                        sample_rate_hertz=24000
                    )
                    
                    # Make API request
                    response = self.client.synthesize_speech(
                        input=input_text,
                        voice=voice,
                        audio_config=audio_config
                    )
                    
                    # Store the audio in the session buffer
                    session["audio_buffer"].extend(response.audio_content)
                    
                    # Add to processed sentences
                    session["processed_sentences"].append(sentence)
                
                # Keep the last sentence in buffer (may be incomplete)
                session["text_buffer"] = sentences[-1]
            
            # Emit event if available
            if self.event_emitter:
                self.event_emitter.create_and_emit(
                    TTSEventType.SESSION_TEXT_ADDED,
                    provider_type="google",
                    session_id=session_id,
                    text_length=len(text),
                    voice_id=session["voice_id"]
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding text to Google streaming session: {e}")
            
            # Emit error event if available
            if self.event_emitter:
                self.event_emitter.create_and_emit(
                    TTSEventType.SESSION_ERROR,
                    provider_type="google",
                    session_id=session_id,
                    error_message=str(e),
                    voice_id=self.active_sessions.get(session_id, {}).get("voice_id")
                )
            
            return False
    
    def end_streaming_session(self, session_id: str) -> bool:
        """
        End a streaming session and clean up resources.
        
        Args:
            session_id (str): Session identifier
            
        Returns:
            bool: True if session was ended successfully
        """
        if not session_id in self.active_sessions:
            logger.warning(f"Session {session_id} not found")
            return False
        
        try:
            # Get session data
            session = self.active_sessions[session_id]
            
            # Process any remaining text in buffer
            if session["text_buffer"]:
                if session["text_buffer"] not in session["processed_sentences"]:
                    # Generate speech for the remaining text
                    input_text = self.texttospeech.SynthesisInput(text=session["text_buffer"])
                    
                    voice = self.texttospeech.VoiceSelectionParams(
                        language_code=self.voice_config["language_code"],
                        name=self.voice_config["name"]
                    )
                    
                    audio_config = self.texttospeech.AudioConfig(
                        audio_encoding=self.texttospeech.AudioEncoding.LINEAR16,
                        speaking_rate=session["speed"],
                        sample_rate_hertz=24000
                    )
                    
                    # Make API request
                    response = self.client.synthesize_speech(
                        input=input_text,
                        voice=voice,
                        audio_config=audio_config
                    )
                    
                    # Add to audio buffer
                    session["audio_buffer"].extend(response.audio_content)
            
            # Remove session
            del self.active_sessions[session_id]
            
            # Emit event if available
            if self.event_emitter:
                self.event_emitter.create_and_emit(
                    TTSEventType.SESSION_END,
                    provider_type="google",
                    session_id=session_id,
                    voice_id=session["voice_id"]
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Error ending Google streaming session: {e}")
            
            # Try to remove session even if there was an error
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
            
            # Emit error event if available
            if self.event_emitter:
                self.event_emitter.create_and_emit(
                    TTSEventType.SESSION_ERROR,
                    provider_type="google",
                    session_id=session_id,
                    error_message=str(e)
                )
            
            return False 