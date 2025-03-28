#!/usr/bin/env python
# Call Quality Monitoring Module

import time
import logging
import json
import threading
from typing import Dict, Any, List, Optional, Tuple, Set
from collections import defaultdict
import statistics
import datetime
import os

logger = logging.getLogger("call-quality-monitor")

class CallQualityMetrics:
    """
    Data class for storing call quality metrics.
    
    This class stores all metrics related to a single call, including
    latency measurements, error counts, and user experience indicators.
    """
    
    def __init__(self, call_id: str):
        """
        Initialize metrics for a call.
        
        Args:
            call_id: Unique identifier for the call
        """
        self.call_id = call_id
        self.started_at = time.time()
        self.ended_at = None
        self.duration = 0
        
        # TTS Generation metrics
        self.generation_times = []
        self.generation_errors = []
        self.total_generation_time = 0
        self.avg_generation_time = 0
        
        # Streaming metrics
        self.streaming_sessions = {}
        self.first_chunk_latencies = []
        self.chunk_sizes = []
        self.total_chunks = 0
        self.total_audio_size = 0
        
        # Error tracking
        self.errors = []
        self.error_count = 0
        
        # User experience indicators
        self.user_responses = []
        self.interrupted_count = 0
        self.silence_durations = []
        
        # Call phases timing
        self.call_phases = {}
        self.current_phase = None
        self.phase_start_time = None
        
        # Status
        self.is_active = True
        self.completion_status = "active"  # active, completed, failed, interrupted
        
        # Qualitative measures
        self.quality_score = None
        self.user_feedback = None

    def end_call(self, status: str = "completed"):
        """
        Mark call as ended and calculate final metrics.
        
        Args:
            status: Completion status (completed, failed, interrupted)
        """
        self.ended_at = time.time()
        self.duration = self.ended_at - self.started_at
        self.is_active = False
        self.completion_status = status
        
        # Calculate final averages
        if self.generation_times:
            self.avg_generation_time = statistics.mean(self.generation_times)
        
        # End current phase if any
        if self.current_phase and self.phase_start_time:
            self.end_phase(self.current_phase)

    def record_generation(self, duration: float, text_length: int = 0):
        """
        Record a TTS generation event.
        
        Args:
            duration: Time taken for generation in seconds
            text_length: Length of generated text
        """
        self.generation_times.append(duration)
        self.total_generation_time += duration
        
        if self.generation_times:
            self.avg_generation_time = statistics.mean(self.generation_times)

    def record_error(self, error_type: str, error_message: str, component: str = "unknown"):
        """
        Record an error that occurred during the call.
        
        Args:
            error_type: Type/category of error
            error_message: Detailed error message
            component: Component where error occurred
        """
        error_info = {
            "timestamp": time.time(),
            "type": error_type,
            "message": error_message,
            "component": component
        }
        self.errors.append(error_info)
        self.error_count += 1

    def record_chunk(self, chunk_size: int, latency: Optional[float] = None):
        """
        Record an audio chunk delivery.
        
        Args:
            chunk_size: Size of audio chunk in bytes
            latency: Time to deliver chunk (optional)
        """
        self.chunk_sizes.append(chunk_size)
        self.total_chunks += 1
        self.total_audio_size += chunk_size
        
        if latency is not None:
            self.first_chunk_latencies.append(latency)

    def start_streaming_session(self, session_id: str):
        """
        Record the start of a streaming session.
        
        Args:
            session_id: Unique ID for the streaming session
        """
        self.streaming_sessions[session_id] = {
            "start_time": time.time(),
            "end_time": None,
            "duration": 0,
            "chunk_count": 0,
            "total_audio_size": 0,
            "first_chunk_time": None,
            "first_chunk_latency": None,
            "status": "active"
        }

    def end_streaming_session(self, session_id: str, status: str = "completed"):
        """
        Record the end of a streaming session.
        
        Args:
            session_id: Unique ID for the streaming session
            status: Completion status (completed, failed, interrupted)
        """
        if session_id in self.streaming_sessions:
            session = self.streaming_sessions[session_id]
            session["end_time"] = time.time()
            session["duration"] = session["end_time"] - session["start_time"]
            session["status"] = status

    def update_streaming_session(self, session_id: str, chunk_size: int = 0, first_chunk: bool = False):
        """
        Update metrics for an ongoing streaming session.
        
        Args:
            session_id: Unique ID for the streaming session
            chunk_size: Size of audio chunk in bytes
            first_chunk: Whether this is the first chunk of the session
        """
        if session_id in self.streaming_sessions:
            session = self.streaming_sessions[session_id]
            session["chunk_count"] += 1
            session["total_audio_size"] += chunk_size
            
            if first_chunk:
                session["first_chunk_time"] = time.time()
                session["first_chunk_latency"] = session["first_chunk_time"] - session["start_time"]
                # Also record in the main latency list
                self.first_chunk_latencies.append(session["first_chunk_latency"])

    def record_user_response(self, response_type: str, duration: float = 0):
        """
        Record a user response or interaction.
        
        Args:
            response_type: Type of response (speech, dtmf, silence)
            duration: Duration of response in seconds
        """
        self.user_responses.append({
            "timestamp": time.time(),
            "type": response_type,
            "duration": duration
        })
        
        if response_type == "interrupt":
            self.interrupted_count += 1
        elif response_type == "silence" and duration > 0:
            self.silence_durations.append(duration)

    def start_phase(self, phase_name: str):
        """
        Start timing a call phase.
        
        Args:
            phase_name: Name of the phase (e.g., greeting, main_content)
        """
        # End current phase if any
        if self.current_phase and self.phase_start_time:
            self.end_phase(self.current_phase)
        
        self.current_phase = phase_name
        self.phase_start_time = time.time()
        
        # Initialize phase if not exists
        if phase_name not in self.call_phases:
            self.call_phases[phase_name] = {
                "start_time": self.phase_start_time,
                "end_time": None,
                "duration": 0,
                "visits": 0
            }
        
        # Update start time for this visit
        phase = self.call_phases[phase_name]
        phase["visits"] += 1
        if phase["visits"] == 1:  # First visit
            phase["start_time"] = self.phase_start_time

    def end_phase(self, phase_name: str):
        """
        End timing a call phase.
        
        Args:
            phase_name: Name of the phase
        """
        if phase_name in self.call_phases:
            phase = self.call_phases[phase_name]
            phase["end_time"] = time.time()
            
            # Calculate cumulative duration
            current_duration = phase["end_time"] - self.phase_start_time
            phase["duration"] += current_duration
            
            # Reset current phase
            if self.current_phase == phase_name:
                self.current_phase = None
                self.phase_start_time = None

    def set_quality_score(self, score: float, category: str = "overall"):
        """
        Set a quality score for the call.
        
        Args:
            score: Quality score (0-100)
            category: Category of the score
        """
        if not hasattr(self, "quality_scores"):
            self.quality_scores = {}
        
        self.quality_scores[category] = score
        
        # Set overall quality score
        if category == "overall":
            self.quality_score = score


class CallQualityMonitor:
    """
    Monitor and collect call quality metrics.
    
    This class integrates with TTS service and Telnyx streaming manager
    to collect and analyze metrics about call quality, including latency,
    errors, and user experience indicators.
    """
    
    def __init__(self, tts_service, telnyx_streaming_manager):
        """
        Initialize the call quality monitor.
        
        Args:
            tts_service: TTSService instance
            telnyx_streaming_manager: TelnyxStreamingManager instance
        """
        self.tts_service = tts_service
        self.streaming_manager = telnyx_streaming_manager
        
        # Store call metrics by call ID
        self.call_metrics = {}
        
        # Track active calls
        self.active_calls = set()
        
        # Current call context for event handlers
        self._current_call_id = None
        
        # Lock for thread safety
        self.metrics_lock = threading.RLock()
        
        # Register event handlers with TTS service and streaming manager
        self._register_event_handlers()
        
        # For persistence
        self.metrics_dir = os.path.join(os.getcwd(), 'logs', 'call_metrics')
        os.makedirs(self.metrics_dir, exist_ok=True)
        
        logger.info("Call quality monitoring initialized")

    def _register_event_handlers(self):
        """Register event handlers with TTS service and streaming manager."""
        # Register TTS service event handlers
        events = self.tts_service.events
        events.on("synthesis_start", self._on_synthesis_start)
        events.on("synthesis_end", self._on_synthesis_end)
        events.on("audio_chunk_generated", self._on_audio_chunk)
        events.on("error", self._on_tts_error)
        events.on("fragment_processed", self._on_fragment_processed)
        events.on("first_response_latency", self._on_first_response_latency)
        
        # Register streaming manager event handlers if available
        if hasattr(self.streaming_manager, 'events'):
            streaming_events = self.streaming_manager.events
            streaming_events.on("streaming_started", self._on_streaming_started)
            streaming_events.on("streaming_ended", self._on_streaming_ended)
            streaming_events.on("chunk_uploaded", self._on_chunk_uploaded)
            streaming_events.on("error", self._on_streaming_error)

    def start_call_monitoring(self, call_id: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Start monitoring a call.
        
        Args:
            call_id: Call ID to monitor
            metadata: Optional metadata about the call
        """
        with self.metrics_lock:
            # Create metrics for this call
            self.call_metrics[call_id] = CallQualityMetrics(call_id)
            
            # Add metadata if provided
            if metadata:
                self.call_metrics[call_id].metadata = metadata
            
            # Mark as active
            self.active_calls.add(call_id)
            
            # Set as current context
            self._current_call_id = call_id
            
            logger.info(f"Started monitoring call: {call_id}")

    def end_call_monitoring(self, call_id: str, status: str = "completed") -> None:
        """
        End monitoring a call.
        
        Args:
            call_id: Call ID
            status: Call completion status
        """
        with self.metrics_lock:
            if call_id in self.call_metrics:
                # Update call metrics
                self.call_metrics[call_id].end_call(status)
                
                # Remove from active calls
                if call_id in self.active_calls:
                    self.active_calls.remove(call_id)
                
                # Clear current context if this was the current call
                if self._current_call_id == call_id:
                    self._current_call_id = None
                
                # Persist metrics
                self._persist_call_metrics(call_id)
                
                logger.info(f"Ended monitoring call: {call_id} with status: {status}")
            else:
                logger.warning(f"Attempted to end monitoring for unknown call: {call_id}")

    def set_current_call(self, call_id: Optional[str]) -> None:
        """
        Set the current call context for event handlers.
        
        Args:
            call_id: Call ID or None to clear context
        """
        with self.metrics_lock:
            if call_id is None or call_id in self.call_metrics:
                self._current_call_id = call_id
            else:
                logger.warning(f"Attempted to set unknown call as current: {call_id}")

    def start_streaming_session(self, call_id: str, stream_id: str) -> None:
        """
        Start monitoring a streaming session.
        
        Args:
            call_id: Call ID
            stream_id: Stream ID
        """
        with self.metrics_lock:
            if call_id in self.call_metrics:
                self.call_metrics[call_id].start_streaming_session(stream_id)
                logger.debug(f"Started monitoring streaming session: {stream_id} for call: {call_id}")
            else:
                logger.warning(f"Attempted to start streaming session for unknown call: {call_id}")

    def end_streaming_session(self, call_id: str, stream_id: str, status: str = "completed") -> None:
        """
        End monitoring a streaming session.
        
        Args:
            call_id: Call ID
            stream_id: Stream ID
            status: Session completion status
        """
        with self.metrics_lock:
            if call_id in self.call_metrics:
                self.call_metrics[call_id].end_streaming_session(stream_id, status)
                logger.debug(f"Ended monitoring streaming session: {stream_id} for call: {call_id}")
            else:
                logger.warning(f"Attempted to end streaming session for unknown call: {call_id}")

    def record_error(self, call_id: str, error_type: str, error_message: str, component: str = "unknown") -> None:
        """
        Record an error for a call.
        
        Args:
            call_id: Call ID
            error_type: Type of error
            error_message: Error message
            component: Component where error occurred
        """
        with self.metrics_lock:
            if call_id in self.call_metrics:
                self.call_metrics[call_id].record_error(error_type, error_message, component)
                logger.debug(f"Recorded error for call {call_id}: {error_type} - {error_message}")
            else:
                logger.warning(f"Attempted to record error for unknown call: {call_id}")

    def record_user_response(self, call_id: str, response_type: str, duration: float = 0) -> None:
        """
        Record a user response.
        
        Args:
            call_id: Call ID
            response_type: Type of response
            duration: Duration of response
        """
        with self.metrics_lock:
            if call_id in self.call_metrics:
                self.call_metrics[call_id].record_user_response(response_type, duration)
                logger.debug(f"Recorded user response for call {call_id}: {response_type}")
            else:
                logger.warning(f"Attempted to record user response for unknown call: {call_id}")

    def start_call_phase(self, call_id: str, phase_name: str) -> None:
        """
        Start a call phase.
        
        Args:
            call_id: Call ID
            phase_name: Name of the phase
        """
        with self.metrics_lock:
            if call_id in self.call_metrics:
                self.call_metrics[call_id].start_phase(phase_name)
                logger.debug(f"Started phase {phase_name} for call {call_id}")
            else:
                logger.warning(f"Attempted to start phase for unknown call: {call_id}")

    def end_call_phase(self, call_id: str, phase_name: str) -> None:
        """
        End a call phase.
        
        Args:
            call_id: Call ID
            phase_name: Name of the phase
        """
        with self.metrics_lock:
            if call_id in self.call_metrics:
                self.call_metrics[call_id].end_phase(phase_name)
                logger.debug(f"Ended phase {phase_name} for call {call_id}")
            else:
                logger.warning(f"Attempted to end phase for unknown call: {call_id}")

    def set_quality_score(self, call_id: str, score: float, category: str = "overall") -> None:
        """
        Set a quality score for a call.
        
        Args:
            call_id: Call ID
            score: Quality score (0-100)
            category: Category of the score
        """
        with self.metrics_lock:
            if call_id in self.call_metrics:
                self.call_metrics[call_id].set_quality_score(score, category)
                logger.debug(f"Set quality score for call {call_id}: {score} ({category})")
            else:
                logger.warning(f"Attempted to set quality score for unknown call: {call_id}")

    def get_call_metrics(self, call_id: str) -> Optional[Dict[str, Any]]:
        """
        Get metrics for a specific call.
        
        Args:
            call_id: Call ID
            
        Returns:
            Dictionary of metrics or None if call not found
        """
        with self.metrics_lock:
            if call_id in self.call_metrics:
                metrics = self.call_metrics[call_id]
                return self._format_call_metrics(metrics)
            return None

    def get_aggregated_metrics(self, time_period: str = "today") -> Dict[str, Any]:
        """
        Get aggregated metrics across all calls.
        
        Args:
            time_period: Time period for aggregation (today, week, month, all)
            
        Returns:
            Dictionary of aggregated metrics
        """
        with self.metrics_lock:
            # Filter calls based on time period
            calls = self._filter_calls_by_time_period(time_period)
            
            if not calls:
                return {"error": "No calls found for the specified time period"}
            
            # Initialize aggregated metrics
            aggregated = {
                "total_calls": len(calls),
                "active_calls": sum(1 for m in calls if m.is_active),
                "completed_calls": sum(1 for m in calls if m.completion_status == "completed"),
                "failed_calls": sum(1 for m in calls if m.completion_status == "failed"),
                "interrupted_calls": sum(1 for m in calls if m.completion_status == "interrupted"),
                "avg_call_duration": 0,
                "avg_generation_time": 0,
                "avg_first_chunk_latency": 0,
                "total_errors": sum(m.error_count for m in calls),
                "error_rate": 0,
                "avg_quality_score": 0
            }
            
            # Calculate averages
            durations = [m.duration for m in calls if m.ended_at is not None]
            if durations:
                aggregated["avg_call_duration"] = statistics.mean(durations)
            
            gen_times = []
            for m in calls:
                gen_times.extend(m.generation_times)
            if gen_times:
                aggregated["avg_generation_time"] = statistics.mean(gen_times)
            
            first_chunk_latencies = []
            for m in calls:
                first_chunk_latencies.extend(m.first_chunk_latencies)
            if first_chunk_latencies:
                aggregated["avg_first_chunk_latency"] = statistics.mean(first_chunk_latencies)
            
            # Calculate error rate
            if aggregated["total_calls"] > 0:
                aggregated["error_rate"] = aggregated["total_errors"] / aggregated["total_calls"]
            
            # Calculate quality score if available
            quality_scores = [m.quality_score for m in calls if m.quality_score is not None]
            if quality_scores:
                aggregated["avg_quality_score"] = statistics.mean(quality_scores)
            
            return aggregated

    def get_quality_trends(self, time_period: str = "week") -> Dict[str, Any]:
        """
        Get quality trends over time.
        
        Args:
            time_period: Time period for analysis (day, week, month)
            
        Returns:
            Dictionary of quality trends
        """
        with self.metrics_lock:
            # This would analyze stored/persisted metrics over time
            # For now, provide a simplified version based on in-memory metrics
            
            # Filter calls based on time period
            calls = self._filter_calls_by_time_period(time_period)
            
            if not calls:
                return {"error": "No calls found for the specified time period"}
            
            # Group by time buckets (hour, day, week depending on time_period)
            buckets = self._group_calls_by_time_buckets(calls, time_period)
            
            trends = {
                "time_buckets": list(buckets.keys()),
                "call_counts": [len(bucket) for bucket in buckets.values()],
                "avg_durations": [],
                "error_rates": [],
                "latency_trends": []
            }
            
            # Calculate metrics for each bucket
            for bucket_calls in buckets.values():
                # Average duration
                durations = [m.duration for m in bucket_calls if m.ended_at is not None]
                avg_duration = statistics.mean(durations) if durations else 0
                trends["avg_durations"].append(avg_duration)
                
                # Error rate
                total_errors = sum(m.error_count for m in bucket_calls)
                error_rate = total_errors / len(bucket_calls) if bucket_calls else 0
                trends["error_rates"].append(error_rate)
                
                # Latency
                first_chunk_latencies = []
                for m in bucket_calls:
                    first_chunk_latencies.extend(m.first_chunk_latencies)
                avg_latency = statistics.mean(first_chunk_latencies) if first_chunk_latencies else 0
                trends["latency_trends"].append(avg_latency)
            
            return trends

    def _on_synthesis_start(self, event_data):
        """Handle synthesis start event."""
        call_id = self._get_current_call_id(event_data)
        if not call_id:
            return
        
        with self.metrics_lock:
            if call_id in self.call_metrics:
                # Start tracking synthesis time
                self.call_metrics[call_id].synthesis_start_time = time.time()
                
                # Start synthesis phase if phases are being tracked
                self.call_metrics[call_id].start_phase("synthesis")

    def _on_synthesis_end(self, event_data):
        """Handle synthesis end event."""
        call_id = self._get_current_call_id(event_data)
        if not call_id:
            return
        
        with self.metrics_lock:
            if call_id in self.call_metrics:
                metrics = self.call_metrics[call_id]
                
                # Calculate synthesis time
                if hasattr(metrics, "synthesis_start_time"):
                    synthesis_time = time.time() - metrics.synthesis_start_time
                    
                    # Record generation time
                    text_length = len(event_data.get("text", "")) if event_data.get("text") else 0
                    metrics.record_generation(synthesis_time, text_length)
                    
                    # End synthesis phase if phases are being tracked
                    metrics.end_phase("synthesis")
                    
                    # Clear start time
                    delattr(metrics, "synthesis_start_time")

    def _on_audio_chunk(self, event_data):
        """Handle audio chunk generated event."""
        call_id = self._get_current_call_id(event_data)
        if not call_id:
            return
        
        with self.metrics_lock:
            if call_id in self.call_metrics:
                # Record chunk
                chunk_size = event_data.get("chunk_size", 0)
                stream_id = event_data.get("stream_id")
                
                self.call_metrics[call_id].record_chunk(chunk_size)
                
                # If this is part of a streaming session, update that too
                if stream_id:
                    first_chunk = event_data.get("is_first_chunk", False)
                    self.call_metrics[call_id].update_streaming_session(stream_id, chunk_size, first_chunk)

    def _on_tts_error(self, event_data):
        """Handle TTS error event."""
        call_id = self._get_current_call_id(event_data)
        if not call_id:
            return
        
        with self.metrics_lock:
            if call_id in self.call_metrics:
                error_message = event_data.get("error", "Unknown error")
                self.call_metrics[call_id].record_error("tts", error_message, "tts_service")

    def _on_fragment_processed(self, event_data):
        """Handle fragment processed event."""
        call_id = self._get_current_call_id(event_data)
        if not call_id:
            return
        
        # This is mainly for logging/tracking purposes
        fragment = event_data.get("fragment", "")
        position = event_data.get("position", 0)
        
        logger.debug(f"Fragment {position} processed for call {call_id}: {fragment[:30]}...")

    def _on_first_response_latency(self, event_data):
        """Handle first response latency event."""
        call_id = self._get_current_call_id(event_data)
        if not call_id:
            return
        
        with self.metrics_lock:
            if call_id in self.call_metrics:
                latency = event_data.get("latency_sec", 0)
                self.call_metrics[call_id].first_chunk_latencies.append(latency)

    def _on_streaming_started(self, event_data):
        """Handle streaming started event."""
        call_id = self._get_current_call_id(event_data)
        if not call_id:
            return
        
        stream_id = event_data.get("stream_id")
        if stream_id:
            with self.metrics_lock:
                if call_id in self.call_metrics:
                    self.call_metrics[call_id].start_streaming_session(stream_id)
                    self.call_metrics[call_id].start_phase("streaming")

    def _on_streaming_ended(self, event_data):
        """Handle streaming ended event."""
        call_id = self._get_current_call_id(event_data)
        if not call_id:
            return
        
        stream_id = event_data.get("stream_id")
        status = event_data.get("status", "completed")
        
        if stream_id:
            with self.metrics_lock:
                if call_id in self.call_metrics:
                    self.call_metrics[call_id].end_streaming_session(stream_id, status)
                    self.call_metrics[call_id].end_phase("streaming")

    def _on_chunk_uploaded(self, event_data):
        """Handle chunk uploaded event."""
        call_id = self._get_current_call_id(event_data)
        if not call_id:
            return
        
        with self.metrics_lock:
            if call_id in self.call_metrics:
                chunk_size = event_data.get("size", 0)
                stream_id = event_data.get("stream_id")
                is_first = event_data.get("is_first", False)
                
                if stream_id:
                    self.call_metrics[call_id].update_streaming_session(stream_id, chunk_size, is_first)

    def _on_streaming_error(self, event_data):
        """Handle streaming error event."""
        call_id = self._get_current_call_id(event_data)
        if not call_id:
            return
        
        with self.metrics_lock:
            if call_id in self.call_metrics:
                error_message = event_data.get("error", "Unknown streaming error")
                self.call_metrics[call_id].record_error("streaming", error_message, "streaming_manager")

    def _get_current_call_id(self, event_data):
        """Extract call ID from event data or use current context."""
        # Try to get from event data first
        call_id = event_data.get("call_id")
        
        # Fallback to current context
        if not call_id:
            call_id = self._current_call_id
        
        return call_id

    def _format_call_metrics(self, metrics):
        """Format call metrics for API response."""
        # Convert CallQualityMetrics object to dictionary
        result = {
            "call_id": metrics.call_id,
            "started_at": metrics.started_at,
            "ended_at": metrics.ended_at,
            "duration": metrics.duration,
            "status": metrics.completion_status,
            "is_active": metrics.is_active,
            
            "tts_metrics": {
                "generation_count": len(metrics.generation_times),
                "avg_generation_time": metrics.avg_generation_time,
                "total_generation_time": metrics.total_generation_time
            },
            
            "streaming_metrics": {
                "session_count": len(metrics.streaming_sessions),
                "total_chunks": metrics.total_chunks,
                "total_audio_size": metrics.total_audio_size,
                "avg_first_chunk_latency": statistics.mean(metrics.first_chunk_latencies) if metrics.first_chunk_latencies else 0
            },
            
            "error_metrics": {
                "error_count": metrics.error_count,
                "errors": metrics.errors[:10]  # Limit to first 10 errors
            },
            
            "user_experience": {
                "response_count": len(metrics.user_responses),
                "interrupted_count": metrics.interrupted_count,
                "avg_silence_duration": statistics.mean(metrics.silence_durations) if metrics.silence_durations else 0
            },
            
            "phases": {name: {
                "duration": phase["duration"],
                "visits": phase["visits"]
            } for name, phase in metrics.call_phases.items()},
            
            "quality_score": metrics.quality_score
        }
        
        # Add any metadata if present
        if hasattr(metrics, "metadata"):
            result["metadata"] = metrics.metadata
        
        return result

    def _filter_calls_by_time_period(self, time_period):
        """Filter calls by time period."""
        now = time.time()
        
        if time_period == "today":
            # Start of today
            start_time = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
            return [m for m in self.call_metrics.values() if m.started_at >= start_time]
        
        elif time_period == "week":
            # 7 days ago
            start_time = now - (7 * 24 * 60 * 60)
            return [m for m in self.call_metrics.values() if m.started_at >= start_time]
        
        elif time_period == "month":
            # 30 days ago
            start_time = now - (30 * 24 * 60 * 60)
            return [m for m in self.call_metrics.values() if m.started_at >= start_time]
        
        else:  # "all"
            return list(self.call_metrics.values())

    def _group_calls_by_time_buckets(self, calls, time_period):
        """Group calls by time buckets for trend analysis."""
        buckets = defaultdict(list)
        
        for call in calls:
            bucket_key = self._get_bucket_key(call.started_at, time_period)
            buckets[bucket_key].append(call)
        
        return buckets

    def _get_bucket_key(self, timestamp, time_period):
        """Get bucket key for a timestamp based on time period."""
        dt = datetime.datetime.fromtimestamp(timestamp)
        
        if time_period == "day":
            # Hourly buckets
            return dt.strftime("%Y-%m-%d %H:00")
        
        elif time_period == "week":
            # Daily buckets
            return dt.strftime("%Y-%m-%d")
        
        elif time_period == "month":
            # Daily buckets
            return dt.strftime("%Y-%m-%d")
        
        else:
            # Weekly buckets
            return f"Week {dt.isocalendar()[1]}, {dt.year}"

    def _persist_call_metrics(self, call_id):
        """Persist call metrics to disk."""
        if call_id not in self.call_metrics:
            return
        
        metrics = self.call_metrics[call_id]
        
        # Only persist completed calls
        if metrics.is_active:
            return
        
        # Format metrics for persistence
        metrics_data = self._format_call_metrics(metrics)
        
        # Create filename with timestamp and call ID
        timestamp = datetime.datetime.fromtimestamp(metrics.started_at).strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{call_id}.json"
        filepath = os.path.join(self.metrics_dir, filename)
        
        try:
            with open(filepath, 'w') as f:
                json.dump(metrics_data, f, indent=2)
            logger.debug(f"Persisted call metrics to {filepath}")
        except Exception as e:
            logger.error(f"Error persisting call metrics: {e}")

    def load_historical_metrics(self, days_ago: int = 30) -> int:
        """
        Load historical metrics from disk.
        
        Args:
            days_ago: Number of days to load metrics for
            
        Returns:
            Number of call metrics loaded
        """
        # Calculate timestamp cutoff
        cutoff_time = time.time() - (days_ago * 24 * 60 * 60)
        count = 0
        
        try:
            # List all metric files
            files = os.listdir(self.metrics_dir)
            
            for filename in files:
                if not filename.endswith('.json'):
                    continue
                
                # Extract timestamp from filename
                parts = filename.split('_')
                if len(parts) < 2:
                    continue
                
                try:
                    # Parse timestamp from filename
                    file_date = datetime.datetime.strptime(parts[0], "%Y%m%d")
                    
                    # Skip if older than cutoff
                    if file_date.timestamp() < cutoff_time:
                        continue
                    
                    # Load metrics
                    filepath = os.path.join(self.metrics_dir, filename)
                    with open(filepath, 'r') as f:
                        metrics_data = json.load(f)
                    
                    # Skip if already loaded
                    call_id = metrics_data.get("call_id")
                    if call_id in self.call_metrics:
                        continue
                    
                    # Create metrics object
                    metrics = CallQualityMetrics(call_id)
                    
                    # Set basic properties
                    metrics.started_at = metrics_data.get("started_at")
                    metrics.ended_at = metrics_data.get("ended_at")
                    metrics.duration = metrics_data.get("duration")
                    metrics.completion_status = metrics_data.get("status")
                    metrics.is_active = False
                    
                    # Store in call metrics
                    self.call_metrics[call_id] = metrics
                    count += 1
                    
                except Exception as e:
                    logger.error(f"Error loading metrics from {filename}: {e}")
            
            logger.info(f"Loaded {count} historical call metrics")
            return count
            
        except Exception as e:
            logger.error(f"Error loading historical metrics: {e}")
            return 0 