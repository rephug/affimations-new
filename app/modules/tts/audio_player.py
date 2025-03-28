#!/usr/bin/env python
# Audio player for streaming TTS playback

import logging
import threading
import time
import queue
from typing import Dict, List, Optional, Any, Tuple, Callable, Union
from enum import Enum
import io
import wave
import traceback
import numpy as np

try:
    import pyaudio
except ImportError:
    logging.error("PyAudio not installed. Install with 'pip install pyaudio'")
    raise

from .audio_buffer import AudioBuffer, AudioChunk, BufferThreshold
from .events import TTSEventEmitter, TTSEventType

logger = logging.getLogger("tts-audio-player")


class PlayerState(Enum):
    """State of the audio player."""
    STOPPED = "stopped"      # Player is stopped
    STARTING = "starting"    # Player is starting up
    PLAYING = "playing"      # Player is actively playing
    PAUSED = "paused"        # Player is paused
    STOPPING = "stopping"    # Player is in the process of stopping
    ERROR = "error"          # Player encountered an error


class PlayerEvent(Enum):
    """Events emitted by the audio player."""
    STARTED = "started"              # Playback started
    STOPPED = "stopped"              # Playback stopped
    PAUSED = "paused"                # Playback paused
    RESUMED = "resumed"              # Playback resumed
    BUFFER_LOW = "buffer_low"        # Buffer is running low
    BUFFER_EMPTY = "buffer_empty"    # Buffer is empty
    PLAYBACK_COMPLETE = "complete"   # Playback completed
    ERROR = "error"                  # Error occurred


class AudioPlayer:
    """
    Audio player for streaming TTS playback using PyAudio.
    
    Features:
    - Streaming playback from AudioBuffer
    - Automatic buffer management
    - Playback controls (start, stop, pause, resume)
    - Event notifications
    - Clean resource handling
    """
    
    def __init__(self, 
                 buffer: Optional[AudioBuffer] = None,
                 sample_rate: int = 24000,
                 sample_width: int = 2,
                 channels: int = 1,
                 buffer_size: int = 1024,
                 event_emitter: Optional[TTSEventEmitter] = None):
        """
        Initialize the audio player.
        
        Args:
            buffer: Audio buffer to play from (or create new if None)
            sample_rate: Sample rate in Hz
            sample_width: Sample width in bytes
            channels: Number of audio channels
            buffer_size: PyAudio buffer size in frames
            event_emitter: Event emitter for notifications
        """
        # Audio format
        self.sample_rate = sample_rate
        self.sample_width = sample_width
        self.channels = channels
        self.buffer_size = buffer_size
        
        # Format for PyAudio
        if sample_width == 1:
            self.format = pyaudio.paInt8
        elif sample_width == 2:
            self.format = pyaudio.paInt16
        elif sample_width == 4:
            self.format = pyaudio.paInt32
        else:
            self.format = pyaudio.paInt16
            self.sample_width = 2
            logger.warning(f"Unsupported sample width: {sample_width}, using 16-bit")
        
        # Audio buffer
        self.buffer = buffer or AudioBuffer()
        
        # PyAudio objects
        self._pyaudio = None
        self._stream = None
        
        # Playback state
        self.state = PlayerState.STOPPED
        self.total_played_samples = 0
        self.total_played_chunks = 0
        self.playback_start_time = None
        self.current_chunk = None
        
        # Stream stats
        self.underflows = 0
        self.last_timestamp = None
        
        # Playback thread
        self._playback_thread = None
        self._stop_event = threading.Event()
        self._thread_exception = None
        
        # Stream lock
        self.lock = threading.RLock()
        
        # Event emission
        self.event_emitter = event_emitter
        self.event_callbacks = {event: [] for event in PlayerEvent}
        
        # Register buffer callbacks
        self.buffer.register_threshold_callback(
            BufferThreshold.EMPTY, self._on_buffer_empty)
        self.buffer.register_threshold_callback(
            BufferThreshold.CRITICAL, self._on_buffer_critical)
        
        logger.debug("AudioPlayer initialized")
    
    def _initialize_pyaudio(self) -> None:
        """Initialize PyAudio if not already initialized."""
        with self.lock:
            if self._pyaudio is None:
                try:
                    self._pyaudio = pyaudio.PyAudio()
                    logger.debug("PyAudio initialized")
                except Exception as e:
                    logger.error(f"Error initializing PyAudio: {e}")
                    self.state = PlayerState.ERROR
                    self._emit_event(PlayerEvent.ERROR, {"error": str(e)})
                    raise
    
    def _audio_callback(self, in_data, frame_count, time_info, status) -> Tuple[bytes, int]:
        """
        Callback function for PyAudio stream.
        
        Args:
            in_data: Input data (not used)
            frame_count: Number of frames to get
            time_info: Timing info
            status: Status flag
            
        Returns:
            Tuple of (audio_data, stream_status)
        """
        try:
            # Check if playback is active
            if self.state != PlayerState.PLAYING or self._stop_event.is_set():
                return (b'\x00' * frame_count * self.channels * self.sample_width, pyaudio.paComplete)
            
            # Calculate bytes needed for the requested frames
            bytes_per_frame = self.channels * self.sample_width
            bytes_needed = frame_count * bytes_per_frame
            
            # Try to get data from current chunk first
            if self.current_chunk is not None:
                remaining_bytes = len(self.current_chunk.data) - self.current_position
                if remaining_bytes >= bytes_needed:
                    # We have enough data in the current chunk
                    data = self.current_chunk.data[self.current_position:self.current_position+bytes_needed]
                    self.current_position += bytes_needed
                    
                    # Update stats
                    self.total_played_samples += frame_count
                    self.last_timestamp = time.time()
                    
                    return (data, pyaudio.paContinue)
                else:
                    # Use remaining data from current chunk
                    data = bytearray(self.current_chunk.data[self.current_position:])
                    self.current_chunk = None
                    self.current_position = 0
                    bytes_needed -= len(data)
            else:
                data = bytearray()
            
            # Get more chunks from buffer if needed
            while bytes_needed > 0:
                chunk = self.buffer.get_chunk()
                if chunk is None:
                    # Buffer is empty, pad with silence
                    data.extend(b'\x00' * bytes_needed)
                    
                    # Log underflow and stats
                    self.underflows += 1
                    logger.debug(f"Buffer underflow during playback (underflows={self.underflows})")
                    
                    # Emit buffer empty event
                    self._emit_event(PlayerEvent.BUFFER_EMPTY, {})
                    
                    # Check if we should stop because playback is complete
                    if self.playback_complete():
                        logger.info("Playback complete, stopping")
                        self._emit_event(PlayerEvent.PLAYBACK_COMPLETE, {})
                        return (bytes(data), pyaudio.paComplete)
                    
                    # Continue playback and wait for more data
                    return (bytes(data), pyaudio.paContinue)
                
                # Add chunk to total
                self.total_played_chunks += 1
                
                if len(chunk.data) <= bytes_needed:
                    # Use entire chunk
                    data.extend(chunk.data)
                    bytes_needed -= len(chunk.data)
                else:
                    # Use part of the chunk and save the rest
                    data.extend(chunk.data[:bytes_needed])
                    self.current_chunk = chunk
                    self.current_position = bytes_needed
                    bytes_needed = 0
            
            # Update stats
            self.total_played_samples += frame_count
            self.last_timestamp = time.time()
            
            return (bytes(data), pyaudio.paContinue)
        
        except Exception as e:
            # Log any errors in the callback
            logger.error(f"Error in audio callback: {e}")
            traceback.print_exc()
            self._thread_exception = e
            
            # Stop playback on error
            self.state = PlayerState.ERROR
            self._emit_event(PlayerEvent.ERROR, {"error": str(e)})
            
            return (b'\x00' * frame_count * self.channels * self.sample_width, pyaudio.paComplete)
    
    def start(self) -> bool:
        """
        Start audio playback.
        
        Returns:
            Success status
        """
        with self.lock:
            # Check if already playing
            if self.state in [PlayerState.PLAYING, PlayerState.STARTING]:
                logger.warning("Playback already active")
                return False
            
            # Mark as starting
            self.state = PlayerState.STARTING
            self._stop_event.clear()
            self._thread_exception = None
            
            try:
                # Initialize PyAudio if needed
                self._initialize_pyaudio()
                
                # Start a new playback thread (avoids blocking the main thread)
                self._playback_thread = threading.Thread(
                    target=self._playback_thread_func,
                    name="audio-playback",
                    daemon=True
                )
                self._playback_thread.start()
                
                logger.info("Audio playback starting")
                return True
            
            except Exception as e:
                logger.error(f"Error starting playback: {e}")
                self.state = PlayerState.ERROR
                self._emit_event(PlayerEvent.ERROR, {"error": str(e)})
                return False
    
    def _playback_thread_func(self) -> None:
        """Background thread function for audio playback."""
        try:
            # Wait for buffer to be ready
            if not self.buffer.is_ready():
                logger.debug("Waiting for buffer to be ready")
                ready = self.buffer.wait_until_ready(timeout=3.0)
                if not ready:
                    logger.warning("Buffer not ready after timeout, continuing anyway")
            
            # Initialize playback stats
            self.playback_start_time = time.time()
            self.total_played_samples = 0
            self.total_played_chunks = 0
            self.underflows = 0
            self.current_chunk = None
            self.current_position = 0
            
            # Open stream
            self._stream = self._pyaudio.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                output=True,
                frames_per_buffer=self.buffer_size,
                stream_callback=self._audio_callback
            )
            
            # Mark as playing
            self.state = PlayerState.PLAYING
            self._emit_event(PlayerEvent.STARTED, {})
            
            # Wait for playback to complete or stop event
            while not self._stop_event.is_set() and self._stream.is_active():
                time.sleep(0.1)
                
                # Check for thread exception
                if self._thread_exception:
                    raise self._thread_exception
            
            # Clean up
            self._cleanup_stream()
            
            # Emit stop event if not already in error state
            if self.state != PlayerState.ERROR:
                self.state = PlayerState.STOPPED
                self._emit_event(PlayerEvent.STOPPED, {})
        
        except Exception as e:
            logger.error(f"Error in playback thread: {e}")
            traceback.print_exc()
            
            # Clean up
            self._cleanup_stream()
            
            # Update state and emit error
            self.state = PlayerState.ERROR
            self._emit_event(PlayerEvent.ERROR, {"error": str(e)})
    
    def stop(self) -> bool:
        """
        Stop audio playback.
        
        Returns:
            Success status
        """
        with self.lock:
            # Check if already stopped
            if self.state in [PlayerState.STOPPED, PlayerState.STOPPING]:
                return True
            
            logger.info("Stopping audio playback")
            
            # Set state to stopping
            prev_state = self.state
            self.state = PlayerState.STOPPING
            
            # Signal thread to stop
            self._stop_event.set()
            
            # Clean up stream (if we're not in the playback thread)
            if threading.current_thread() != self._playback_thread:
                self._cleanup_stream()
                
                # Wait for playback thread to complete
                if self._playback_thread is not None and self._playback_thread.is_alive():
                    self._playback_thread.join(timeout=2.0)
                
                # Update state
                self.state = PlayerState.STOPPED
                
                # If we were previously paused, emit the stop event here
                # (since the playback thread isn't running to emit it)
                if prev_state == PlayerState.PAUSED:
                    self._emit_event(PlayerEvent.STOPPED, {})
            
            return True
    
    def pause(self) -> bool:
        """
        Pause audio playback.
        
        Returns:
            Success status
        """
        with self.lock:
            # Check if playing
            if self.state != PlayerState.PLAYING:
                return False
            
            # Pause stream
            if self._stream is not None:
                self._stream.stop_stream()
            
            # Update state
            self.state = PlayerState.PAUSED
            self._emit_event(PlayerEvent.PAUSED, {})
            
            logger.info("Audio playback paused")
            return True
    
    def resume(self) -> bool:
        """
        Resume paused audio playback.
        
        Returns:
            Success status
        """
        with self.lock:
            # Check if paused
            if self.state != PlayerState.PAUSED:
                return False
            
            # Resume stream
            if self._stream is not None:
                self._stream.start_stream()
            
            # Update state
            self.state = PlayerState.PLAYING
            self._emit_event(PlayerEvent.RESUMED, {})
            
            logger.info("Audio playback resumed")
            return True
    
    def _cleanup_stream(self) -> None:
        """Clean up the audio stream."""
        with self.lock:
            if self._stream is not None:
                try:
                    if self._stream.is_active():
                        self._stream.stop_stream()
                    self._stream.close()
                except Exception as e:
                    logger.error(f"Error closing stream: {e}")
                finally:
                    self._stream = None
    
    def _cleanup_pyaudio(self) -> None:
        """Clean up PyAudio resources."""
        with self.lock:
            if self._pyaudio is not None:
                try:
                    self._pyaudio.terminate()
                except Exception as e:
                    logger.error(f"Error terminating PyAudio: {e}")
                finally:
                    self._pyaudio = None
    
    def is_playing(self) -> bool:
        """
        Check if audio is currently playing.
        
        Returns:
            Playback status
        """
        return self.state == PlayerState.PLAYING
    
    def is_paused(self) -> bool:
        """
        Check if audio is currently paused.
        
        Returns:
            Pause status
        """
        return self.state == PlayerState.PAUSED
    
    def is_stopped(self) -> bool:
        """
        Check if audio is currently stopped.
        
        Returns:
            Stop status
        """
        return self.state == PlayerState.STOPPED
    
    def is_active(self) -> bool:
        """
        Check if audio player is active (playing or paused).
        
        Returns:
            Active status
        """
        return self.state in [PlayerState.PLAYING, PlayerState.PAUSED]
    
    def playback_complete(self) -> bool:
        """
        Check if playback is complete (buffer empty and no more data expected).
        
        Returns:
            Completion status
        """
        return (self.buffer.is_empty() and self.current_chunk is None and 
                time.time() - (self.last_timestamp or time.time()) > 1.0)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get playback statistics.
        
        Returns:
            Dictionary of statistics
        """
        with self.lock:
            stats = {
                "state": self.state.value,
                "format": {
                    "sample_rate": self.sample_rate,
                    "sample_width": self.sample_width,
                    "channels": self.channels,
                    "buffer_size": self.buffer_size
                },
                "playback": {
                    "total_played_samples": self.total_played_samples,
                    "total_played_chunks": self.total_played_chunks,
                    "underflows": self.underflows
                },
                "buffer": self.buffer.get_status() if self.buffer else None
            }
            
            # Add playback duration if available
            if self.playback_start_time is not None:
                duration = time.time() - self.playback_start_time
                stats["playback"]["duration_seconds"] = duration
                
                # Add average playback rate
                if duration > 0:
                    samples_per_second = self.total_played_samples / duration
                    stats["playback"]["avg_samples_per_second"] = samples_per_second
            
            return stats
    
    def cleanup(self) -> None:
        """Clean up all resources."""
        self.stop()
        self._cleanup_stream()
        self._cleanup_pyaudio()
        logger.debug("AudioPlayer resources cleaned up")
    
    def __del__(self) -> None:
        """Destructor to ensure resources are cleaned up."""
        self.cleanup()
    
    def register_event_callback(self, event: PlayerEvent, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Register a callback for a player event.
        
        Args:
            event: Player event
            callback: Function to call when event occurs
        """
        with self.lock:
            self.event_callbacks[event].append(callback)
    
    def _emit_event(self, event: PlayerEvent, data: Dict[str, Any]) -> None:
        """
        Emit a player event.
        
        Args:
            event: Player event
            data: Event data
        """
        # Add player ID to data
        data["player_id"] = id(self)
        
        # Call registered callbacks
        for callback in self.event_callbacks[event]:
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Error in event callback: {e}")
        
        # Emit through event emitter if available
        if self.event_emitter:
            try:
                # Map player events to TTS events
                event_map = {
                    PlayerEvent.STARTED: TTSEventType.PLAYBACK_STARTED,
                    PlayerEvent.STOPPED: TTSEventType.PLAYBACK_STOPPED,
                    PlayerEvent.PAUSED: TTSEventType.PLAYBACK_PAUSED,
                    PlayerEvent.RESUMED: TTSEventType.PLAYBACK_RESUMED,
                    PlayerEvent.BUFFER_LOW: TTSEventType.BUFFER_LOW,
                    PlayerEvent.BUFFER_EMPTY: TTSEventType.BUFFER_EMPTY,
                    PlayerEvent.PLAYBACK_COMPLETE: TTSEventType.PLAYBACK_COMPLETE,
                    PlayerEvent.ERROR: TTSEventType.ERROR
                }
                
                if event in event_map:
                    self.event_emitter.emit(event_map[event], data)
            except Exception as e:
                logger.error(f"Error emitting event: {e}")
    
    def _on_buffer_empty(self, state) -> None:
        """
        Callback for buffer empty threshold.
        
        Args:
            state: Buffer state
        """
        if self.is_playing():
            self._emit_event(PlayerEvent.BUFFER_EMPTY, {"buffer_state": state.get_stats()})
    
    def _on_buffer_critical(self, state) -> None:
        """
        Callback for buffer critical threshold.
        
        Args:
            state: Buffer state
        """
        if self.is_playing():
            self._emit_event(PlayerEvent.BUFFER_LOW, {"buffer_state": state.get_stats()})
    
    @staticmethod
    def play_wav_file(file_path: str, block: bool = True) -> Optional['AudioPlayer']:
        """
        Static method to play a WAV file.
        
        Args:
            file_path: Path to WAV file
            block: Whether to block until playback completes
            
        Returns:
            AudioPlayer instance or None if error
        """
        try:
            # Read WAV file
            with wave.open(file_path, 'rb') as wav_file:
                channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()
                sample_rate = wav_file.getframerate()
                data = wav_file.readframes(wav_file.getnframes())
                frames = wav_file.getnframes()
                duration_ms = (frames / sample_rate) * 1000
            
            # Create buffer and player
            buffer = AudioBuffer()
            buffer.add_raw_audio(
                audio_data=data,
                duration_ms=duration_ms,
                sample_rate=sample_rate,
                sample_width=sample_width,
                channels=channels
            )
            
            player = AudioPlayer(
                buffer=buffer,
                sample_rate=sample_rate,
                sample_width=sample_width,
                channels=channels
            )
            
            # Start playback
            player.start()
            
            # Wait for completion if blocking
            if block:
                while player.is_active() and not buffer.is_empty():
                    time.sleep(0.1)
                player.stop()
                player.cleanup()
                return None
            else:
                return player
        
        except Exception as e:
            logger.error(f"Error playing WAV file: {e}")
            return None 