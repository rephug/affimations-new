#!/usr/bin/env python
# Telnyx streaming manager for TTS audio streaming

import logging
import threading
import time
import uuid
import os
import json
import requests
import queue
from typing import Dict, List, Optional, Any, Set, Tuple, Union, Callable
from enum import Enum
import io
import wave
import traceback
from datetime import datetime, timedelta

# Local imports
from .audio_buffer import AudioBuffer, AudioChunk, BufferThreshold
from .events import TTSEventEmitter, TTSEventType

# Optional backoff library for retries
try:
    from backoff import on_exception, expo
    BACKOFF_AVAILABLE = True
except ImportError:
    BACKOFF_AVAILABLE = False
    logging.warning("backoff library not installed. Retries will use simple logic.")

logger = logging.getLogger("tts-telnyx-streaming")


class StreamingSessionState(Enum):
    """State of a Telnyx streaming session."""
    INITIALIZING = "initializing"  # Session is being initialized
    READY = "ready"                # Session is ready for streaming
    STREAMING = "streaming"        # Session is actively streaming
    PAUSED = "paused"              # Session is paused
    COMPLETED = "completed"        # Session has completed successfully
    ERROR = "error"                # Session encountered an error
    TERMINATED = "terminated"      # Session was terminated


class AudioFormat(Enum):
    """Supported audio formats for Telnyx streaming."""
    WAV = "wav"
    RAW = "raw"
    MP3 = "mp3"


class TelnyxStreamingSession:
    """
    Represents a streaming session for a Telnyx call.
    
    Manages the state and resources associated with a streaming 
    session to a Telnyx call.
    """
    
    def __init__(self, 
                 call_control_id: str,
                 client_state: Optional[str] = None,
                 buffer: Optional[AudioBuffer] = None,
                 format: AudioFormat = AudioFormat.WAV,
                 sample_rate: int = 8000, 
                 sample_width: int = 2,
                 channels: int = 1,
                 command_id: Optional[str] = None,
                 buffer_size_ms: int = 5000,
                 event_emitter: Optional[TTSEventEmitter] = None):
        """
        Initialize a streaming session.
        
        Args:
            call_control_id: Telnyx call control ID
            client_state: Client state for tracking
            buffer: Audio buffer (creates new if None)
            format: Audio format for streaming
            sample_rate: Sample rate in Hz
            sample_width: Sample width in bytes
            channels: Number of audio channels
            command_id: Command ID for the streaming session
            buffer_size_ms: Size of buffer in milliseconds
            event_emitter: Event emitter for notifications
        """
        # Call information
        self.call_control_id = call_control_id
        self.client_state = client_state
        self.command_id = command_id or str(uuid.uuid4())
        self.stream_id = None
        
        # Session state
        self.state = StreamingSessionState.INITIALIZING
        self.created_at = time.time()
        self.started_at = None
        self.last_activity = time.time()
        self.completed_at = None
        self.error = None
        
        # Audio format
        self.format = format
        self.sample_rate = sample_rate
        self.sample_width = sample_width
        self.channels = channels
        
        # Streaming buffer
        self.buffer = buffer or AudioBuffer(
            ready_threshold_ms=500,  # Start playback with 500ms
            critical_threshold_ms=200,
            low_threshold_ms=500,
            normal_threshold_ms=2000,
            high_threshold_ms=buffer_size_ms
        )
        
        # Register buffer callbacks
        self.buffer.register_threshold_callback(
            BufferThreshold.EMPTY, self._on_buffer_empty)
        self.buffer.register_threshold_callback(
            BufferThreshold.CRITICAL, self._on_buffer_critical)
        
        # Streaming statistics
        self.total_chunks_sent = 0
        self.total_bytes_sent = 0
        self.upload_errors = 0
        self.consecutive_errors = 0
        self.max_consecutive_errors = 3
        self.upload_latencies = []  # ms
        
        # Thread synchronization
        self.lock = threading.RLock()
        self.upload_queue = queue.Queue()
        self.upload_thread = None
        self.stop_event = threading.Event()
        
        # Event emitter
        self.event_emitter = event_emitter
        
        logger.debug(f"Streaming session created for call {call_control_id}")
    
    def start(self) -> bool:
        """
        Start the streaming session.
        
        Returns:
            Success status
        """
        with self.lock:
            # Check if already started
            if self.state in [StreamingSessionState.STREAMING, 
                             StreamingSessionState.PAUSED]:
                return True
            
            # Update state
            self.state = StreamingSessionState.READY
            self.started_at = time.time()
            self.last_activity = time.time()
            
            # Start upload thread
            self.stop_event.clear()
            self.upload_thread = threading.Thread(
                target=self._upload_worker,
                name=f"telnyx-upload-{self.call_control_id[:8]}",
                daemon=True
            )
            self.upload_thread.start()
            
            # Mark as streaming
            self.state = StreamingSessionState.STREAMING
            
            logger.info(f"Started streaming session for call {self.call_control_id}")
            return True
    
    def add_audio(self, 
                 audio_data: bytes, 
                 duration_ms: float,
                 metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Add audio data to the buffer.
        
        Args:
            audio_data: Raw audio data
            duration_ms: Duration in milliseconds
            metadata: Additional metadata
            
        Returns:
            Success status
        """
        with self.lock:
            # Check if session is active
            if self.state not in [StreamingSessionState.READY, 
                                StreamingSessionState.STREAMING]:
                logger.warning(f"Cannot add audio to inactive session for call {self.call_control_id}")
                return False
            
            # Add to buffer
            result = self.buffer.add_raw_audio(
                audio_data=audio_data,
                duration_ms=duration_ms,
                sample_rate=self.sample_rate,
                sample_width=self.sample_width,
                channels=self.channels,
                metadata=metadata
            )
            
            # Update activity timestamp
            self.last_activity = time.time()
            
            return result
    
    def add_wav_audio(self, wav_data: bytes, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Add WAV audio data to the buffer.
        
        Args:
            wav_data: WAV-formatted audio data
            metadata: Additional metadata
            
        Returns:
            Success status
        """
        with self.lock:
            # Check if session is active
            if self.state not in [StreamingSessionState.READY, 
                                StreamingSessionState.STREAMING]:
                logger.warning(f"Cannot add audio to inactive session for call {self.call_control_id}")
                return False
            
            # Add to buffer
            result = self.buffer.add_wav_audio(wav_data, metadata)
            
            # Update activity timestamp
            self.last_activity = time.time()
            
            return result
    
    def pause(self) -> bool:
        """
        Pause the streaming session.
        
        Returns:
            Success status
        """
        with self.lock:
            # Check if streaming
            if self.state != StreamingSessionState.STREAMING:
                return False
            
            # Update state
            self.state = StreamingSessionState.PAUSED
            
            logger.info(f"Paused streaming session for call {self.call_control_id}")
            return True
    
    def resume(self) -> bool:
        """
        Resume the streaming session.
        
        Returns:
            Success status
        """
        with self.lock:
            # Check if paused
            if self.state != StreamingSessionState.PAUSED:
                return False
            
            # Update state
            self.state = StreamingSessionState.STREAMING
            self.last_activity = time.time()
            
            logger.info(f"Resumed streaming session for call {self.call_control_id}")
            return True
    
    def complete(self) -> bool:
        """
        Mark the streaming session as complete.
        
        Returns:
            Success status
        """
        with self.lock:
            # Check if active
            if self.state in [StreamingSessionState.COMPLETED, 
                             StreamingSessionState.TERMINATED]:
                return True
            
            # Update state
            prev_state = self.state
            self.state = StreamingSessionState.COMPLETED
            self.completed_at = time.time()
            
            # Stop upload thread
            self.stop_event.set()
            
            logger.info(f"Completed streaming session for call {self.call_control_id}")
            
            # If not streaming, manually clean up
            if prev_state != StreamingSessionState.STREAMING:
                self._cleanup()
            
            return True
    
    def terminate(self, error: Optional[str] = None) -> None:
        """
        Terminate the streaming session due to an error.
        
        Args:
            error: Error message
        """
        with self.lock:
            # Update state
            self.state = StreamingSessionState.TERMINATED
            self.completed_at = time.time()
            self.error = error
            
            # Stop upload thread
            self.stop_event.set()
            
            # Log error
            if error:
                logger.error(f"Terminated streaming session for call {self.call_control_id}: {error}")
            else:
                logger.info(f"Terminated streaming session for call {self.call_control_id}")
            
            # Clean up
            self._cleanup()
    
    def _cleanup(self) -> None:
        """Clean up resources associated with the session."""
        # Clear buffer
        self.buffer.clear()
        
        # Wait for upload thread to finish
        if (self.upload_thread is not None and 
            self.upload_thread.is_alive() and 
            threading.current_thread() != self.upload_thread):
            self.upload_thread.join(timeout=2.0)
    
    def _on_buffer_empty(self, state) -> None:
        """
        Callback for empty buffer.
        
        Args:
            state: Buffer state
        """
        if self.state == StreamingSessionState.STREAMING:
            # End streaming if no more data expected
            if self.buffer.is_empty():
                # Wait for a moment to see if more data arrives
                pass
    
    def _on_buffer_critical(self, state) -> None:
        """
        Callback for critically low buffer.
        
        Args:
            state: Buffer state
        """
        # Log warning
        if self.state == StreamingSessionState.STREAMING:
            logger.warning(f"Buffer critically low for call {self.call_control_id}")
    
    def _upload_worker(self) -> None:
        """Worker thread for uploading audio chunks."""
        logger.debug(f"Upload worker started for call {self.call_control_id}")
        
        try:
            # Process chunks until stopped
            while not self.stop_event.is_set():
                # Check if we're streaming
                if self.state != StreamingSessionState.STREAMING:
                    time.sleep(0.1)
                    continue
                
                # Get next chunk
                chunk = self.buffer.get_chunk()
                if chunk is None:
                    time.sleep(0.05)  # Small sleep to avoid CPU spin
                    continue
                
                # Upload chunk
                start_time = time.time()
                success = self._upload_chunk(chunk.data)
                end_time = time.time()
                
                # Calculate latency
                latency_ms = (end_time - start_time) * 1000
                
                # Update statistics
                if success:
                    with self.lock:
                        self.total_chunks_sent += 1
                        self.total_bytes_sent += len(chunk.data)
                        self.consecutive_errors = 0
                        self.upload_latencies.append(latency_ms)
                        
                        # Keep only the last 100 latencies
                        if len(self.upload_latencies) > 100:
                            self.upload_latencies = self.upload_latencies[-100:]
                else:
                    with self.lock:
                        self.upload_errors += 1
                        self.consecutive_errors += 1
                        
                        # Check for too many consecutive errors
                        if self.consecutive_errors >= self.max_consecutive_errors:
                            logger.error(f"Too many consecutive upload errors for call {self.call_control_id}")
                            self.terminate(error="Too many consecutive upload errors")
                            break
            
            # End of streaming
            logger.debug(f"Upload worker completed for call {self.call_control_id}")
            
            # Mark as completed if still streaming
            with self.lock:
                if self.state == StreamingSessionState.STREAMING:
                    self.state = StreamingSessionState.COMPLETED
                    self.completed_at = time.time()
                    logger.info(f"Streaming completed for call {self.call_control_id}")
        
        except Exception as e:
            # Log error
            logger.error(f"Error in upload worker for call {self.call_control_id}: {e}")
            traceback.print_exc()
            
            # Terminate session
            self.terminate(error=str(e))
    
    def _upload_chunk(self, chunk_data: bytes) -> bool:
        """
        Upload a chunk of audio data to Telnyx.
        
        Args:
            chunk_data: Audio chunk data
            
        Returns:
            Success status
        """
        # This method should be implemented to make the actual Telnyx API call
        # to upload the chunk data. For now, we'll return True to simulate success.
        # In a real implementation, this would call the TelnyxStreamingManager's
        # method to upload the chunk.
        
        # Placeholder for actual API call
        logger.debug(f"Would upload {len(chunk_data)} bytes to Telnyx for call {self.call_control_id}")
        
        # Simulated success
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get streaming statistics.
        
        Returns:
            Dictionary of statistics
        """
        with self.lock:
            duration = 0
            if self.started_at is not None:
                end_time = self.completed_at or time.time()
                duration = end_time - self.started_at
            
            avg_latency = 0
            if self.upload_latencies:
                avg_latency = sum(self.upload_latencies) / len(self.upload_latencies)
            
            stats = {
                "call_control_id": self.call_control_id,
                "command_id": self.command_id,
                "stream_id": self.stream_id,
                "state": self.state.value,
                "duration_seconds": duration,
                "format": {
                    "type": self.format.value,
                    "sample_rate": self.sample_rate,
                    "sample_width": self.sample_width,
                    "channels": self.channels
                },
                "streaming": {
                    "total_chunks_sent": self.total_chunks_sent,
                    "total_bytes_sent": self.total_bytes_sent,
                    "upload_errors": self.upload_errors,
                    "consecutive_errors": self.consecutive_errors,
                    "avg_upload_latency_ms": avg_latency
                },
                "buffer": self.buffer.get_status() if self.buffer else None,
                "timestamps": {
                    "created_at": datetime.fromtimestamp(self.created_at).isoformat(),
                    "started_at": datetime.fromtimestamp(self.started_at).isoformat() if self.started_at else None,
                    "last_activity": datetime.fromtimestamp(self.last_activity).isoformat() if self.last_activity else None,
                    "completed_at": datetime.fromtimestamp(self.completed_at).isoformat() if self.completed_at else None
                }
            }
            
            # Add error info if present
            if self.error:
                stats["error"] = self.error
            
            return stats


class TelnyxStreamingManager:
    """
    Manager for Telnyx streaming audio sessions.
    
    Handles creating, tracking, and managing streaming sessions to Telnyx calls.
    Provides error recovery and statistics tracking across all sessions.
    """
    
    def __init__(self, 
                 api_key: Optional[str] = None,
                 api_base_url: str = "https://api.telnyx.com/v2",
                 max_concurrent_sessions: int = 50,
                 session_timeout_seconds: int = 300,
                 retry_attempts: int = 3,
                 retry_backoff_factor: float = 2.0,
                 default_format: AudioFormat = AudioFormat.WAV,
                 default_sample_rate: int = 8000,
                 default_sample_width: int = 2,
                 default_channels: int = 1,
                 event_emitter: Optional[TTSEventEmitter] = None):
        """
        Initialize the Telnyx streaming manager.
        
        Args:
            api_key: Telnyx API key (defaults to TELNYX_API_KEY env var)
            api_base_url: Telnyx API base URL
            max_concurrent_sessions: Maximum concurrent streaming sessions
            session_timeout_seconds: Session timeout in seconds
            retry_attempts: Maximum retry attempts for API calls
            retry_backoff_factor: Backoff factor for retries
            default_format: Default audio format
            default_sample_rate: Default sample rate in Hz
            default_sample_width: Default sample width in bytes
            default_channels: Default number of audio channels
            event_emitter: Event emitter for notifications
        """
        # API configuration
        self.api_key = api_key or os.environ.get("TELNYX_API_KEY")
        if not self.api_key:
            logger.warning("No Telnyx API key provided. Set TELNYX_API_KEY env var or pass api_key.")
        
        self.api_base_url = api_base_url
        self.retry_attempts = retry_attempts
        self.retry_backoff_factor = retry_backoff_factor
        
        # Streaming sessions
        self.sessions: Dict[str, TelnyxStreamingSession] = {}
        self.max_concurrent_sessions = max_concurrent_sessions
        self.session_timeout_seconds = session_timeout_seconds
        
        # Default audio format
        self.default_format = default_format
        self.default_sample_rate = default_sample_rate
        self.default_sample_width = default_sample_width
        self.default_channels = default_channels
        
        # Thread safety
        self.lock = threading.RLock()
        
        # Maintenance thread
        self._shutdown = threading.Event()
        self._maintenance_thread = threading.Thread(
            target=self._maintenance_loop,
            name="telnyx-streaming-maintenance",
            daemon=True
        )
        self._maintenance_thread.start()
        
        # Statistics
        self.total_sessions_created = 0
        self.total_sessions_completed = 0
        self.total_sessions_error = 0
        self.total_bytes_sent = 0
        self.api_errors = 0
        
        # Event emitter
        self.event_emitter = event_emitter
        
        logger.info("TelnyxStreamingManager initialized")
        
        # Set up HTTP session with connection pooling
        self.http_session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=100,
            max_retries=retry_attempts
        )
        self.http_session.mount("https://", adapter)
        self.http_session.mount("http://", adapter)
        
        # Headers for API calls
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    def create_streaming_session(self,
                                call_control_id: str,
                                client_state: Optional[str] = None,
                                format: Optional[AudioFormat] = None,
                                sample_rate: Optional[int] = None,
                                sample_width: Optional[int] = None,
                                channels: Optional[int] = None,
                                buffer: Optional[AudioBuffer] = None,
                                command_id: Optional[str] = None) -> Optional[str]:
        """
        Create a new streaming session for a call.
        
        Args:
            call_control_id: Telnyx call control ID
            client_state: Client state for tracking
            format: Audio format (defaults to manager default)
            sample_rate: Sample rate in Hz (defaults to manager default)
            sample_width: Sample width in bytes (defaults to manager default)
            channels: Number of audio channels (defaults to manager default)
            buffer: Audio buffer (creates new if None)
            command_id: Command ID for the streaming session
            
        Returns:
            Session ID or None if creation failed
        """
        with self.lock:
            # Check if session already exists
            if call_control_id in self.sessions:
                logger.warning(f"Streaming session already exists for call {call_control_id}")
                return call_control_id
            
            # Check if too many sessions
            if len(self.sessions) >= self.max_concurrent_sessions:
                logger.error(f"Too many concurrent sessions (max={self.max_concurrent_sessions})")
                return None
            
            try:
                # Create session
                session = TelnyxStreamingSession(
                    call_control_id=call_control_id,
                    client_state=client_state,
                    buffer=buffer,
                    format=format or self.default_format,
                    sample_rate=sample_rate or self.default_sample_rate,
                    sample_width=sample_width or self.default_sample_width,
                    channels=channels or self.default_channels,
                    command_id=command_id,
                    event_emitter=self.event_emitter
                )
                
                # Store session
                self.sessions[call_control_id] = session
                self.total_sessions_created += 1
                
                logger.info(f"Created streaming session for call {call_control_id}")
                
                # Emit event if available
                if self.event_emitter:
                    self.event_emitter.emit(
                        TTSEventType.SESSION_CREATED,
                        {
                            "call_control_id": call_control_id,
                            "command_id": session.command_id
                        }
                    )
                
                return call_control_id
            
            except Exception as e:
                logger.error(f"Error creating streaming session: {e}")
                return None
    
    def start_streaming(self, call_control_id: str) -> bool:
        """
        Start streaming for a call.
        
        Args:
            call_control_id: Telnyx call control ID
            
        Returns:
            Success status
        """
        with self.lock:
            # Check if session exists
            if call_control_id not in self.sessions:
                logger.warning(f"No streaming session for call {call_control_id}")
                return False
            
            # Get session
            session = self.sessions[call_control_id]
            
            # Start API call
            if not self._start_streaming_call(session):
                return False
            
            # Patch session with upload method
            self._patch_session_upload(session)
            
            # Start session
            result = session.start()
            
            # Emit event if available
            if result and self.event_emitter:
                self.event_emitter.emit(
                    TTSEventType.STREAMING_STARTED,
                    {
                        "call_control_id": call_control_id,
                        "command_id": session.command_id,
                        "stream_id": session.stream_id
                    }
                )
            
            return result
    
    def add_audio(self, 
                 call_control_id: str, 
                 audio_data: bytes, 
                 duration_ms: float,
                 metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Add audio data to a streaming session.
        
        Args:
            call_control_id: Telnyx call control ID
            audio_data: Raw audio data
            duration_ms: Duration in milliseconds
            metadata: Additional metadata
            
        Returns:
            Success status
        """
        # Check if session exists
        if call_control_id not in self.sessions:
            logger.warning(f"No streaming session for call {call_control_id}")
            return False
        
        # Add audio to session
        session = self.sessions[call_control_id]
        return session.add_audio(audio_data, duration_ms, metadata)
    
    def add_wav_audio(self, 
                     call_control_id: str, 
                     wav_data: bytes,
                     metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Add WAV audio data to a streaming session.
        
        Args:
            call_control_id: Telnyx call control ID
            wav_data: WAV-formatted audio data
            metadata: Additional metadata
            
        Returns:
            Success status
        """
        # Check if session exists
        if call_control_id not in self.sessions:
            logger.warning(f"No streaming session for call {call_control_id}")
            return False
        
        # Add audio to session
        session = self.sessions[call_control_id]
        return session.add_wav_audio(wav_data, metadata)
    
    def pause_streaming(self, call_control_id: str) -> bool:
        """
        Pause streaming for a call.
        
        Args:
            call_control_id: Telnyx call control ID
            
        Returns:
            Success status
        """
        # Check if session exists
        if call_control_id not in self.sessions:
            logger.warning(f"No streaming session for call {call_control_id}")
            return False
        
        # Pause streaming
        session = self.sessions[call_control_id]
        result = session.pause()
        
        # Emit event if available
        if result and self.event_emitter:
            self.event_emitter.emit(
                TTSEventType.STREAMING_PAUSED,
                {
                    "call_control_id": call_control_id,
                    "command_id": session.command_id
                }
            )
        
        return result
    
    def resume_streaming(self, call_control_id: str) -> bool:
        """
        Resume streaming for a call.
        
        Args:
            call_control_id: Telnyx call control ID
            
        Returns:
            Success status
        """
        # Check if session exists
        if call_control_id not in self.sessions:
            logger.warning(f"No streaming session for call {call_control_id}")
            return False
        
        # Resume streaming
        session = self.sessions[call_control_id]
        result = session.resume()
        
        # Emit event if available
        if result and self.event_emitter:
            self.event_emitter.emit(
                TTSEventType.STREAMING_RESUMED,
                {
                    "call_control_id": call_control_id,
                    "command_id": session.command_id
                }
            )
        
        return result
    
    def complete_streaming(self, call_control_id: str) -> bool:
        """
        Complete streaming for a call.
        
        Args:
            call_control_id: Telnyx call control ID
            
        Returns:
            Success status
        """
        with self.lock:
            # Check if session exists
            if call_control_id not in self.sessions:
                logger.warning(f"No streaming session for call {call_control_id}")
                return False
            
            # Complete streaming
            session = self.sessions[call_control_id]
            result = session.complete()
            
            # Stop API call
            self._stop_streaming_call(call_control_id)
            
            # Update statistics
            if result:
                self.total_sessions_completed += 1
                self.total_bytes_sent += session.total_bytes_sent
            
            # Emit event if available
            if result and self.event_emitter:
                self.event_emitter.emit(
                    TTSEventType.STREAMING_COMPLETED,
                    {
                        "call_control_id": call_control_id,
                        "command_id": session.command_id,
                        "bytes_sent": session.total_bytes_sent,
                        "stream_id": session.stream_id
                    }
                )
            
            # Remove from sessions
            self._remove_session(call_control_id)
            
            return result
    
    def terminate_streaming(self, call_control_id: str, error: Optional[str] = None) -> None:
        """
        Terminate streaming for a call due to an error.
        
        Args:
            call_control_id: Telnyx call control ID
            error: Error message
        """
        with self.lock:
            # Check if session exists
            if call_control_id not in self.sessions:
                logger.warning(f"No streaming session for call {call_control_id}")
                return
            
            # Terminate streaming
            session = self.sessions[call_control_id]
            session.terminate(error)
            
            # Update statistics
            self.total_sessions_error += 1
            self.total_bytes_sent += session.total_bytes_sent
            
            # Emit event if available
            if self.event_emitter:
                self.event_emitter.emit(
                    TTSEventType.STREAMING_ERROR,
                    {
                        "call_control_id": call_control_id,
                        "command_id": session.command_id,
                        "error": error
                    }
                )
            
            # Remove from sessions
            self._remove_session(call_control_id)
    
    def get_session_stats(self, call_control_id: str) -> Optional[Dict[str, Any]]:
        """
        Get statistics for a streaming session.
        
        Args:
            call_control_id: Telnyx call control ID
            
        Returns:
            Dictionary of statistics or None if session not found
        """
        # Check if session exists
        if call_control_id not in self.sessions:
            logger.warning(f"No streaming session for call {call_control_id}")
            return None
        
        # Get stats
        session = self.sessions[call_control_id]
        return session.get_stats()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics for all streaming sessions.
        
        Returns:
            Dictionary of statistics
        """
        with self.lock:
            stats = {
                "total_sessions_created": self.total_sessions_created,
                "total_sessions_completed": self.total_sessions_completed,
                "total_sessions_error": self.total_sessions_error,
                "total_bytes_sent": self.total_bytes_sent,
                "api_errors": self.api_errors,
                "active_sessions": len(self.sessions),
                "sessions": [
                    session.get_stats()
                    for session in self.sessions.values()
                ]
            }
            
            return stats
    
    def _remove_session(self, call_control_id: str) -> None:
        """
        Remove a session from tracking.
        
        Args:
            call_control_id: Telnyx call control ID
        """
        with self.lock:
            if call_control_id in self.sessions:
                del self.sessions[call_control_id]
    
    def _maintenance_loop(self) -> None:
        """Maintenance thread for cleaning up idle sessions."""
        while not self._shutdown.is_set():
            try:
                with self.lock:
                    # Find timed out sessions
                    current_time = time.time()
                    timed_out_sessions = []
                    
                    for call_control_id, session in self.sessions.items():
                        # Check if session is idle
                        if (current_time - session.last_activity) > self.session_timeout_seconds:
                            # Session has timed out
                            timed_out_sessions.append(call_control_id)
                    
                    # Terminate timed out sessions
                    for call_control_id in timed_out_sessions:
                        logger.warning(f"Session timeout for call {call_control_id}")
                        session = self.sessions[call_control_id]
                        session.terminate(error="Session timeout")
                        self.total_sessions_error += 1
                        self._remove_session(call_control_id)
                
                # Sleep for a while
                time.sleep(10)
            
            except Exception as e:
                logger.error(f"Error in maintenance loop: {e}")
                time.sleep(30)  # Longer sleep on error
    
    def shutdown(self) -> None:
        """Shutdown the manager and clean up resources."""
        logger.info("Shutting down TelnyxStreamingManager...")
        self._shutdown.set()
        
        with self.lock:
            # Terminate all sessions
            for call_control_id, session in list(self.sessions.items()):
                session.terminate()
                self._remove_session(call_control_id)
            
            # Close HTTP session
            self.http_session.close()
        
        logger.info("TelnyxStreamingManager shutdown complete")
    
    def __del__(self) -> None:
        """Destructor to ensure resources are cleaned up."""
        self.shutdown()
    
    def _make_api_call(self, 
                       method: str, 
                       path: str, 
                       json_data: Optional[Dict] = None, 
                       binary_data: Optional[bytes] = None,
                       content_type: Optional[str] = None) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        Make an API call to Telnyx.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            path: API path
            json_data: JSON data for request
            binary_data: Binary data for request
            content_type: Content type for binary data
            
        Returns:
            Tuple of (success, response_data, error_message)
        """
        url = f"{self.api_base_url}/{path.lstrip('/')}"
        
        headers = self.headers.copy()
        
        if content_type and binary_data:
            headers["Content-Type"] = content_type
        
        try:
            # Make API call with retries
            response = None
            
            if BACKOFF_AVAILABLE:
                retry_decorator = on_exception(
                    expo, 
                    (requests.exceptions.RequestException,),
                    max_tries=self.retry_attempts,
                    factor=self.retry_backoff_factor
                )
                
                @retry_decorator
                def make_request():
                    if method.upper() == "GET":
                        return self.http_session.get(url, headers=headers)
                    elif method.upper() == "POST":
                        if json_data:
                            return self.http_session.post(url, json=json_data, headers=headers)
                        elif binary_data:
                            return self.http_session.post(url, data=binary_data, headers=headers)
                        else:
                            return self.http_session.post(url, headers=headers)
                    elif method.upper() == "PUT":
                        if json_data:
                            return self.http_session.put(url, json=json_data, headers=headers)
                        elif binary_data:
                            return self.http_session.put(url, data=binary_data, headers=headers)
                        else:
                            return self.http_session.put(url, headers=headers)
                    else:
                        raise ValueError(f"Unsupported HTTP method: {method}")
                
                response = make_request()
            else:
                # Simple retry logic
                for attempt in range(self.retry_attempts):
                    try:
                        if method.upper() == "GET":
                            response = self.http_session.get(url, headers=headers)
                        elif method.upper() == "POST":
                            if json_data:
                                response = self.http_session.post(url, json=json_data, headers=headers)
                            elif binary_data:
                                response = self.http_session.post(url, data=binary_data, headers=headers)
                            else:
                                response = self.http_session.post(url, headers=headers)
                        elif method.upper() == "PUT":
                            if json_data:
                                response = self.http_session.put(url, json=json_data, headers=headers)
                            elif binary_data:
                                response = self.http_session.put(url, data=binary_data, headers=headers)
                            else:
                                response = self.http_session.put(url, headers=headers)
                        else:
                            raise ValueError(f"Unsupported HTTP method: {method}")
                        
                        break  # Success, exit retry loop
                    
                    except requests.exceptions.RequestException as e:
                        if attempt < self.retry_attempts - 1:
                            # Calculate backoff time
                            backoff_time = self.retry_backoff_factor * (2 ** attempt)
                            logger.warning(f"API call failed, retrying in {backoff_time:.2f}s: {e}")
                            time.sleep(backoff_time)
                        else:
                            # Last attempt failed
                            raise
            
            # Check response
            if response.status_code >= 200 and response.status_code < 300:
                # Success
                try:
                    if response.content:
                        return True, response.json(), None
                    else:
                        return True, {}, None
                except ValueError:
                    # Not JSON
                    return True, None, None
            else:
                # Error
                error_message = f"API call failed: {response.status_code}"
                try:
                    error_data = response.json()
                    if "errors" in error_data:
                        error_message = f"API error: {error_data['errors'][0]['title']}"
                except Exception:
                    error_message = f"API error: {response.content.decode('utf-8', errors='ignore')[:100]}"
                
                # Update error count
                self.api_errors += 1
                
                return False, None, error_message
        
        except Exception as e:
            # Error
            error_message = f"API call exception: {e}"
            
            # Update error count
            self.api_errors += 1
            
            return False, None, error_message
    
    def _start_streaming_call(self, session: TelnyxStreamingSession) -> bool:
        """
        Start streaming for a call using Telnyx API.
        
        Args:
            session: TelnyxStreamingSession to start
            
        Returns:
            Success status
        """
        # Build request
        call_control_id = session.call_control_id
        path = f"calls/{call_control_id}/actions/streaming_start"
        
        # Get audio format
        content_type = "audio/wav"
        if session.format == AudioFormat.MP3:
            content_type = "audio/mp3"
        elif session.format == AudioFormat.RAW:
            content_type = "audio/raw"
        
        # Build JSON payload
        payload = {
            "client_state": session.client_state,
            "command_id": session.command_id,
            "audio_stream": {
                "content_type": content_type,
                "sample_rate": session.sample_rate,
                "channels": session.channels
            }
        }
        
        # Make API call
        success, response, error = self._make_api_call("POST", path, json_data=payload)
        
        if success:
            logger.info(f"Started streaming for call {call_control_id}")
            
            # Update session with stream ID if available
            if response and "data" in response and "stream_id" in response["data"]:
                session.stream_id = response["data"]["stream_id"]
            
            return True
        else:
            logger.error(f"Failed to start streaming for call {call_control_id}: {error}")
            return False
    
    def _upload_chunk_to_call(self, 
                             call_control_id: str, 
                             chunk_data: bytes, 
                             content_type: str = "audio/wav") -> bool:
        """
        Upload a chunk of audio data to a call.
        
        Args:
            call_control_id: Telnyx call control ID
            chunk_data: Audio chunk data
            content_type: Content type for audio data
            
        Returns:
            Success status
        """
        # Build request
        path = f"calls/{call_control_id}/actions/streaming"
        
        # Make API call
        success, _, error = self._make_api_call(
            "POST", 
            path, 
            binary_data=chunk_data, 
            content_type=content_type
        )
        
        if not success:
            logger.warning(f"Failed to upload chunk to call {call_control_id}: {error}")
        
        return success
    
    def _stop_streaming_call(self, call_control_id: str) -> bool:
        """
        Stop streaming for a call.
        
        Args:
            call_control_id: Telnyx call control ID
            
        Returns:
            Success status
        """
        # Build request
        path = f"calls/{call_control_id}/actions/streaming_stop"
        
        # Make API call
        success, _, error = self._make_api_call("POST", path)
        
        if success:
            logger.info(f"Stopped streaming for call {call_control_id}")
            return True
        else:
            logger.error(f"Failed to stop streaming for call {call_control_id}: {error}")
            return False

    # Additional method to patch the session's _upload_chunk method with actual implementation
    def _patch_session_upload(self, session: TelnyxStreamingSession) -> None:
        """
        Patch a session with the manager's upload method.
        
        Args:
            session: TelnyxStreamingSession to patch
        """
        def upload_chunk(chunk_data: bytes) -> bool:
            """
            Upload a chunk of audio data to Telnyx.
            
            Args:
                chunk_data: Audio chunk data
                
            Returns:
                Success status
            """
            # Get content type based on format
            content_type = "audio/wav"
            if session.format == AudioFormat.MP3:
                content_type = "audio/mp3"
            elif session.format == AudioFormat.RAW:
                content_type = "audio/raw"
            
            # Upload chunk
            return self._upload_chunk_to_call(
                call_control_id=session.call_control_id,
                chunk_data=chunk_data,
                content_type=content_type
            )
        
        # Patch the session's upload method
        session._upload_chunk = upload_chunk 