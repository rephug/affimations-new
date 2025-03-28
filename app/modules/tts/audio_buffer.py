#!/usr/bin/env python
# Audio buffer for streaming TTS playback

import logging
import threading
import time
from typing import Callable, Dict, List, Optional, Any, Tuple, Set, Union
from collections import deque
import numpy as np
from enum import Enum
import io
import wave

from .events import TTSEventEmitter, TTSEventType

logger = logging.getLogger("tts-audio-buffer")


class BufferThreshold(Enum):
    """Threshold levels for buffer state monitoring."""
    EMPTY = "empty"          # Buffer has no data
    CRITICAL = "critical"    # Buffer is critically low
    LOW = "low"              # Buffer is running low
    NORMAL = "normal"        # Buffer has adequate data
    HIGH = "high"            # Buffer has plenty of data
    OVERFLOW = "overflow"    # Buffer has too much data


class BufferState:
    """Current state and statistics of the audio buffer."""
    
    def __init__(self):
        """Initialize buffer state tracking."""
        self.chunks = 0               # Current number of chunks in buffer
        self.bytes = 0                # Current size in bytes
        self.duration_ms = 0          # Estimated playback duration in milliseconds
        self.threshold = BufferThreshold.EMPTY  # Current threshold level
        
        # Statistics
        self.total_chunks_added = 0
        self.total_chunks_retrieved = 0
        self.overflow_count = 0
        self.underflow_count = 0
        self.peak_chunks = 0
        self.peak_bytes = 0
        self.peak_duration_ms = 0
        
        # Timing
        self.last_add_time = None
        self.last_get_time = None
        self.creation_time = time.time()
    
    def update_on_add(self, chunk_size: int, duration_ms: float) -> None:
        """
        Update state when a chunk is added.
        
        Args:
            chunk_size: Size of chunk in bytes
            duration_ms: Duration of chunk in milliseconds
        """
        self.chunks += 1
        self.bytes += chunk_size
        self.duration_ms += duration_ms
        self.total_chunks_added += 1
        self.last_add_time = time.time()
        
        # Update peaks
        self.peak_chunks = max(self.peak_chunks, self.chunks)
        self.peak_bytes = max(self.peak_bytes, self.bytes)
        self.peak_duration_ms = max(self.peak_duration_ms, self.duration_ms)
    
    def update_on_get(self, chunk_size: int, duration_ms: float) -> None:
        """
        Update state when a chunk is retrieved.
        
        Args:
            chunk_size: Size of chunk in bytes
            duration_ms: Duration of chunk in milliseconds
        """
        self.chunks -= 1
        self.bytes -= chunk_size
        self.duration_ms -= duration_ms
        self.total_chunks_retrieved += 1
        self.last_get_time = time.time()
    
    def update_threshold(self, thresholds: Dict[BufferThreshold, float]) -> BufferThreshold:
        """
        Update the current threshold level based on buffer duration.
        
        Args:
            thresholds: Dictionary mapping threshold levels to durations in ms
            
        Returns:
            Current threshold level
        """
        prev_threshold = self.threshold
        
        # Determine new threshold
        if self.chunks == 0:
            self.threshold = BufferThreshold.EMPTY
        elif self.duration_ms <= thresholds[BufferThreshold.CRITICAL]:
            self.threshold = BufferThreshold.CRITICAL
        elif self.duration_ms <= thresholds[BufferThreshold.LOW]:
            self.threshold = BufferThreshold.LOW
        elif self.duration_ms <= thresholds[BufferThreshold.NORMAL]:
            self.threshold = BufferThreshold.NORMAL
        elif self.duration_ms <= thresholds[BufferThreshold.HIGH]:
            self.threshold = BufferThreshold.HIGH
        else:
            self.threshold = BufferThreshold.OVERFLOW
            if prev_threshold != BufferThreshold.OVERFLOW:
                self.overflow_count += 1
        
        # Check for underflow
        if prev_threshold != BufferThreshold.EMPTY and self.threshold == BufferThreshold.EMPTY:
            self.underflow_count += 1
        
        return self.threshold
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get buffer statistics.
        
        Returns:
            Dictionary of statistics
        """
        now = time.time()
        stats = {
            "current": {
                "chunks": self.chunks,
                "bytes": self.bytes,
                "duration_ms": self.duration_ms,
                "threshold": self.threshold.value if self.threshold else None
            },
            "totals": {
                "chunks_added": self.total_chunks_added,
                "chunks_retrieved": self.total_chunks_retrieved,
                "overflow_count": self.overflow_count,
                "underflow_count": self.underflow_count
            },
            "peaks": {
                "chunks": self.peak_chunks,
                "bytes": self.peak_bytes,
                "duration_ms": self.peak_duration_ms
            },
            "timing": {
                "buffer_age_seconds": now - self.creation_time,
                "seconds_since_last_add": now - self.last_add_time if self.last_add_time else None,
                "seconds_since_last_get": now - self.last_get_time if self.last_get_time else None
            }
        }
        return stats


class AudioChunk:
    """Represents a chunk of audio data with metadata."""
    
    def __init__(self, 
                 data: bytes, 
                 duration_ms: float, 
                 sample_rate: int = 24000, 
                 sample_width: int = 2, 
                 channels: int = 1,
                 metadata: Optional[Dict[str, Any]] = None):
        """
        Initialize an audio chunk.
        
        Args:
            data: Raw audio data (bytes)
            duration_ms: Duration of audio in milliseconds
            sample_rate: Sample rate of audio in Hz
            sample_width: Sample width in bytes
            channels: Number of audio channels
            metadata: Additional metadata for the chunk
        """
        self.data = data
        self.duration_ms = duration_ms
        self.sample_rate = sample_rate
        self.sample_width = sample_width
        self.channels = channels
        self.metadata = metadata or {}
        self.timestamp = time.time()
        self.size = len(data)
    
    def get_numpy_array(self) -> np.ndarray:
        """
        Convert audio data to numpy array.
        
        Returns:
            Numpy array of audio samples
        """
        if self.sample_width == 2:
            return np.frombuffer(self.data, dtype=np.int16)
        elif self.sample_width == 4:
            return np.frombuffer(self.data, dtype=np.int32)
        elif self.sample_width == 1:
            return np.frombuffer(self.data, dtype=np.int8)
        else:
            # Default to 16-bit samples
            return np.frombuffer(self.data, dtype=np.int16)
    
    def to_wav_bytes(self) -> bytes:
        """
        Convert audio chunk to WAV format.
        
        Returns:
            WAV-formatted audio data
        """
        with io.BytesIO() as wav_io:
            with wave.open(wav_io, 'wb') as wav_file:
                wav_file.setnchannels(self.channels)
                wav_file.setsampwidth(self.sample_width)
                wav_file.setframerate(self.sample_rate)
                wav_file.writeframes(self.data)
            return wav_io.getvalue()
    
    @classmethod
    def from_wav_bytes(cls, wav_data: bytes, metadata: Optional[Dict[str, Any]] = None) -> 'AudioChunk':
        """
        Create an AudioChunk from WAV data.
        
        Args:
            wav_data: WAV-formatted audio data
            metadata: Additional metadata
            
        Returns:
            AudioChunk instance
        """
        with io.BytesIO(wav_data) as wav_io:
            with wave.open(wav_io, 'rb') as wav_file:
                channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()
                sample_rate = wav_file.getframerate()
                data = wav_file.readframes(wav_file.getnframes())
                
                # Calculate duration in milliseconds
                frames = wav_file.getnframes()
                duration_ms = (frames / sample_rate) * 1000
                
                return cls(
                    data=data,
                    duration_ms=duration_ms,
                    sample_rate=sample_rate,
                    sample_width=sample_width,
                    channels=channels,
                    metadata=metadata
                )


class AudioBuffer:
    """
    Thread-safe audio buffer for streaming playback.
    
    Features:
    - Thread-safe add/get operations
    - Threshold-based buffer state monitoring
    - Callback notifications for buffer state changes
    - Overflow protection
    - Statistics tracking
    """
    
    def __init__(self,
                 max_size: int = 100,
                 ready_threshold_ms: float = 500,
                 critical_threshold_ms: float = 200,
                 low_threshold_ms: float = 500,
                 normal_threshold_ms: float = 2000,
                 high_threshold_ms: float = 5000,
                 overflow_threshold_ms: float = 10000,
                 event_emitter: Optional[TTSEventEmitter] = None):
        """
        Initialize the audio buffer.
        
        Args:
            max_size: Maximum number of chunks in buffer
            ready_threshold_ms: Minimum buffer duration to be considered ready (ms)
            critical_threshold_ms: Critical threshold for buffer duration (ms)
            low_threshold_ms: Low threshold for buffer duration (ms)
            normal_threshold_ms: Normal threshold for buffer duration (ms)
            high_threshold_ms: High threshold for buffer duration (ms)
            overflow_threshold_ms: Overflow threshold for buffer duration (ms)
            event_emitter: Event emitter for notification events
        """
        # Buffer configuration
        self.max_size = max_size
        self.ready_threshold_ms = ready_threshold_ms
        
        # Thresholds based on buffer duration (milliseconds)
        self.thresholds = {
            BufferThreshold.CRITICAL: critical_threshold_ms,
            BufferThreshold.LOW: low_threshold_ms,
            BufferThreshold.NORMAL: normal_threshold_ms,
            BufferThreshold.HIGH: high_threshold_ms,
            BufferThreshold.OVERFLOW: overflow_threshold_ms
        }
        
        # Buffer state
        self.state = BufferState()
        
        # Thread synchronization
        self.lock = threading.RLock()
        self.buffer = deque()
        self.ready_event = threading.Event()
        self.empty_event = threading.Event()
        self.empty_event.set()  # Start as empty
        
        # Callbacks for threshold crossings
        self.threshold_callbacks: Dict[BufferThreshold, List[Callable]] = {
            threshold: [] for threshold in BufferThreshold
        }
        
        # Event emission
        self.event_emitter = event_emitter
        
        # Session identifier
        self.session_id = None
        
        logger.debug("AudioBuffer initialized")
    
    def add_chunk(self, chunk: AudioChunk) -> bool:
        """
        Add an audio chunk to the buffer.
        
        Args:
            chunk: Audio chunk to add
            
        Returns:
            Success status (False if overflow prevented adding)
        """
        with self.lock:
            # Check for overflow
            if len(self.buffer) >= self.max_size:
                logger.warning(f"Buffer overflow prevented (size={len(self.buffer)})")
                self._notify_threshold_change(BufferThreshold.OVERFLOW)
                return False
            
            # Add chunk to buffer
            self.buffer.append(chunk)
            
            # Update buffer state
            self.state.update_on_add(chunk.size, chunk.duration_ms)
            prev_threshold = self.state.threshold
            current_threshold = self.state.update_threshold(self.thresholds)
            
            # Check if buffer is now ready
            if self.state.duration_ms >= self.ready_threshold_ms:
                if not self.ready_event.is_set():
                    logger.debug(f"Buffer is now ready: {self.state.duration_ms}ms")
                    self.ready_event.set()
                    if self.event_emitter:
                        self.event_emitter.emit(
                            TTSEventType.BUFFER_READY,
                            {"buffer_id": id(self), "duration_ms": self.state.duration_ms}
                        )
            
            # Clear empty state
            if self.empty_event.is_set():
                self.empty_event.clear()
            
            # Notify threshold change if needed
            if current_threshold != prev_threshold:
                self._notify_threshold_change(current_threshold)
            
            return True
    
    def get_chunk(self) -> Optional[AudioChunk]:
        """
        Get the next audio chunk from the buffer.
        
        Returns:
            Audio chunk or None if buffer is empty
        """
        with self.lock:
            if not self.buffer:
                if not self.empty_event.is_set():
                    logger.debug("Buffer is now empty")
                    self.empty_event.set()
                    self.ready_event.clear()
                    self._notify_threshold_change(BufferThreshold.EMPTY)
                    if self.event_emitter:
                        self.event_emitter.emit(
                            TTSEventType.BUFFER_EMPTY,
                            {"buffer_id": id(self)}
                        )
                return None
            
            # Get chunk from buffer
            chunk = self.buffer.popleft()
            
            # Update buffer state
            self.state.update_on_get(chunk.size, chunk.duration_ms)
            prev_threshold = self.state.threshold
            current_threshold = self.state.update_threshold(self.thresholds)
            
            # Check if buffer is no longer ready
            if self.state.duration_ms < self.ready_threshold_ms:
                self.ready_event.clear()
            
            # Check if buffer is empty
            if not self.buffer:
                self.empty_event.set()
                self._notify_threshold_change(BufferThreshold.EMPTY)
                if self.event_emitter:
                    self.event_emitter.emit(
                        TTSEventType.BUFFER_EMPTY,
                        {"buffer_id": id(self)}
                    )
            elif current_threshold != prev_threshold:
                # Notify threshold change
                self._notify_threshold_change(current_threshold)
            
            return chunk
    
    def peek_chunk(self) -> Optional[AudioChunk]:
        """
        Peek at the next audio chunk without removing it.
        
        Returns:
            Audio chunk or None if buffer is empty
        """
        with self.lock:
            if not self.buffer:
                return None
            return self.buffer[0]
    
    def wait_until_ready(self, timeout: Optional[float] = None) -> bool:
        """
        Wait until the buffer has enough data to start playback.
        
        Args:
            timeout: Maximum time to wait in seconds (None for no timeout)
            
        Returns:
            True if buffer is ready, False if timed out
        """
        return self.ready_event.wait(timeout)
    
    def wait_until_empty(self, timeout: Optional[float] = None) -> bool:
        """
        Wait until the buffer is empty.
        
        Args:
            timeout: Maximum time to wait in seconds (None for no timeout)
            
        Returns:
            True if buffer is empty, False if timed out
        """
        return self.empty_event.wait(timeout)
    
    def register_threshold_callback(self, threshold: BufferThreshold, callback: Callable) -> None:
        """
        Register a callback to be called when a threshold is crossed.
        
        Args:
            threshold: Buffer threshold
            callback: Function to call when threshold is crossed
        """
        with self.lock:
            self.threshold_callbacks[threshold].append(callback)
    
    def _notify_threshold_change(self, threshold: BufferThreshold) -> None:
        """
        Notify callbacks of a threshold change.
        
        Args:
            threshold: New buffer threshold
        """
        # Notify specific callbacks
        for callback in self.threshold_callbacks[threshold]:
            try:
                callback(self.state)
            except Exception as e:
                logger.error(f"Error in threshold callback: {e}")
        
        # Emit event if available
        if self.event_emitter:
            self.event_emitter.emit(
                TTSEventType.BUFFER_THRESHOLD_CHANGE,
                {
                    "buffer_id": id(self),
                    "threshold": threshold.value,
                    "duration_ms": self.state.duration_ms
                }
            )
    
    def clear(self) -> None:
        """Clear all audio chunks from the buffer."""
        with self.lock:
            self.buffer.clear()
            self.state = BufferState()
            self.ready_event.clear()
            self.empty_event.set()
            
            if self.event_emitter:
                self.event_emitter.emit(
                    TTSEventType.BUFFER_CLEARED,
                    {"buffer_id": id(self)}
                )
            
            logger.debug("Buffer cleared")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current buffer status.
        
        Returns:
            Dictionary of buffer status information
        """
        with self.lock:
            status = {
                "ready": self.ready_event.is_set(),
                "empty": self.empty_event.is_set(),
                "current_threshold": self.state.threshold.value if self.state.threshold else None,
                "size": len(self.buffer),
                "duration_ms": self.state.duration_ms,
                "session_id": self.session_id,
                "thresholds": {k.value: v for k, v in self.thresholds.items()},
                "stats": self.state.get_stats()
            }
            return status
    
    def set_session_id(self, session_id: str) -> None:
        """
        Set a session identifier for this buffer.
        
        Args:
            session_id: Session identifier
        """
        with self.lock:
            self.session_id = session_id
            
            if self.event_emitter:
                self.event_emitter.emit(
                    TTSEventType.BUFFER_SESSION_CHANGED,
                    {"buffer_id": id(self), "session_id": session_id}
                )
    
    def add_raw_audio(self, 
                      audio_data: bytes, 
                      duration_ms: float,
                      sample_rate: int = 24000,
                      sample_width: int = 2,
                      channels: int = 1,
                      metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Add raw audio data to the buffer.
        
        Args:
            audio_data: Raw audio data
            duration_ms: Duration in milliseconds
            sample_rate: Sample rate in Hz
            sample_width: Sample width in bytes
            channels: Number of channels
            metadata: Additional metadata
            
        Returns:
            Success status
        """
        chunk = AudioChunk(
            data=audio_data,
            duration_ms=duration_ms,
            sample_rate=sample_rate,
            sample_width=sample_width,
            channels=channels,
            metadata=metadata
        )
        return self.add_chunk(chunk)
    
    def add_wav_audio(self, wav_data: bytes, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Add WAV audio data to the buffer.
        
        Args:
            wav_data: WAV-formatted audio data
            metadata: Additional metadata
            
        Returns:
            Success status
        """
        chunk = AudioChunk.from_wav_bytes(wav_data, metadata)
        return self.add_chunk(chunk)
    
    def is_ready(self) -> bool:
        """
        Check if buffer is ready for playback.
        
        Returns:
            Ready status
        """
        return self.ready_event.is_set()
    
    def is_empty(self) -> bool:
        """
        Check if buffer is empty.
        
        Returns:
            Empty status
        """
        return self.empty_event.is_set()
    
    def get_duration_ms(self) -> float:
        """
        Get current buffer duration in milliseconds.
        
        Returns:
            Buffer duration
        """
        with self.lock:
            return self.state.duration_ms
    
    def set_threshold(self, threshold_type: BufferThreshold, value_ms: float) -> None:
        """
        Update a threshold value.
        
        Args:
            threshold_type: Threshold type to update
            value_ms: New value in milliseconds
        """
        with self.lock:
            self.thresholds[threshold_type] = value_ms
            
            # Recompute current threshold
            self.state.update_threshold(self.thresholds)
    
    def get_all_chunks(self) -> List[AudioChunk]:
        """
        Get all chunks in the buffer (for testing/debugging).
        
        Returns:
            List of all audio chunks
        """
        with self.lock:
            return list(self.buffer) 