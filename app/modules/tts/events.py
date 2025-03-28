#!/usr/bin/env python
# TTS Event System for monitoring operations

import logging
import time
import threading
from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Callable, Any, Optional

logger = logging.getLogger("tts-events")

class TTSEventType(Enum):
    """Enumeration of TTS event types."""
    GENERATION_START = "generation_start"
    GENERATION_END = "generation_end"
    GENERATION_ERROR = "generation_error"
    
    STREAMING_START = "streaming_start"
    STREAMING_CHUNK = "streaming_chunk"
    STREAMING_END = "streaming_end"
    STREAMING_ERROR = "streaming_error"
    
    SESSION_START = "session_start"
    SESSION_TEXT_ADDED = "session_text_added"
    SESSION_END = "session_end"
    SESSION_ERROR = "session_error"
    
    PROVIDER_CHANGED = "provider_changed"
    PROVIDER_ERROR = "provider_error"
    
    CACHE_HIT = "cache_hit"
    CACHE_MISS = "cache_miss"
    CACHE_ERROR = "cache_error"
    
    FALLBACK_ACTIVATED = "fallback_activated"
    
    LATENCY_MEASURED = "latency_measured"

@dataclass
class TTSEvent:
    """Data class containing event information."""
    event_type: TTSEventType
    timestamp: float
    provider_type: Optional[str] = None
    duration_ms: Optional[float] = None
    text_length: Optional[int] = None
    error_message: Optional[str] = None
    voice_id: Optional[str] = None
    session_id: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None

class TTSEventEmitter:
    """
    Event emitter for TTS operations.
    
    This class provides a thread-safe event system for monitoring
    TTS operations with callbacks for different event types.
    """
    
    def __init__(self):
        """Initialize the event emitter."""
        self._event_handlers: Dict[TTSEventType, List[Callable[[TTSEvent], None]]] = {}
        self._lock = threading.RLock()
        self._event_history: List[TTSEvent] = []
        self._max_history = 100  # Maximum number of events to keep in history
    
    def on(self, event_type: TTSEventType, 
           handler: Callable[[TTSEvent], None]) -> None:
        """
        Register a handler for a specific event type.
        
        Args:
            event_type (TTSEventType): Type of event to listen for
            handler (Callable[[TTSEvent], None]): Function to call when event occurs
        """
        with self._lock:
            if event_type not in self._event_handlers:
                self._event_handlers[event_type] = []
            self._event_handlers[event_type].append(handler)
    
    def off(self, event_type: TTSEventType, 
            handler: Callable[[TTSEvent], None]) -> None:
        """
        Remove a handler for a specific event type.
        
        Args:
            event_type (TTSEventType): Type of event
            handler (Callable[[TTSEvent], None]): Handler to remove
        """
        with self._lock:
            if event_type in self._event_handlers:
                if handler in self._event_handlers[event_type]:
                    self._event_handlers[event_type].remove(handler)
    
    def emit(self, event: TTSEvent) -> None:
        """
        Emit an event to all registered handlers.
        
        Args:
            event (TTSEvent): Event to emit
        """
        with self._lock:
            # Add to history
            self._event_history.append(event)
            # Trim history if needed
            while len(self._event_history) > self._max_history:
                self._event_history.pop(0)
            
            # Get handlers for this event type
            handlers = self._event_handlers.get(event.event_type, [])
        
        # Call handlers outside of lock to prevent deadlocks
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Error in event handler for {event.event_type}: {e}")
    
    def create_and_emit(self, event_type: TTSEventType, **kwargs) -> TTSEvent:
        """
        Create and emit an event in one operation.
        
        Args:
            event_type (TTSEventType): Type of event
            **kwargs: Additional event data
            
        Returns:
            TTSEvent: The created and emitted event
        """
        # Set timestamp if not provided
        if 'timestamp' not in kwargs:
            kwargs['timestamp'] = time.time()
        
        event = TTSEvent(event_type=event_type, **kwargs)
        self.emit(event)
        return event
    
    def get_recent_events(self, 
                         event_type: Optional[TTSEventType] = None,
                         limit: int = 10) -> List[TTSEvent]:
        """
        Get recent events from history.
        
        Args:
            event_type (Optional[TTSEventType]): Filter by event type
            limit (int): Maximum number of events to return
            
        Returns:
            List[TTSEvent]: List of recent events
        """
        with self._lock:
            if event_type:
                events = [e for e in self._event_history if e.event_type == event_type]
            else:
                events = self._event_history.copy()
            
            # Return most recent events first, limited to requested count
            return sorted(events, key=lambda e: e.timestamp, reverse=True)[:limit]
    
    def clear_history(self) -> int:
        """
        Clear event history.
        
        Returns:
            int: Number of events cleared
        """
        with self._lock:
            count = len(self._event_history)
            self._event_history.clear()
            return count 