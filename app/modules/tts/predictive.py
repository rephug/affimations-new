#!/usr/bin/env python
# Predictive TTS Generation

import logging
import threading
import time
import uuid
import json
from typing import Dict, List, Set, Optional, Callable, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import queue
import os
from pathlib import Path
import concurrent.futures

# Local imports
from .cache_manager import TTSCacheManager, TTSCacheKey
from .events import TTSEventEmitter, TTSEventType, TTSEvent

logger = logging.getLogger("tts-predictive")

class PredictionPriority(Enum):
    """Priority levels for predictive generation tasks."""
    HIGH = 0    # Immediate next phrases in call flow
    MEDIUM = 1  # Likely but not immediate phrases
    LOW = 2     # Possible but less likely phrases


@dataclass
class CallFlow:
    """Represents a defined conversation flow with step transitions."""
    name: str
    description: str = ""
    steps: Dict[str, "CallFlowStep"] = field(default_factory=dict)
    entry_point: str = "start"
    
    def add_step(self, step: "CallFlowStep") -> None:
        """Add a step to the call flow."""
        self.steps[step.id] = step
    
    def get_step(self, step_id: str) -> Optional["CallFlowStep"]:
        """Get a step by ID."""
        return self.steps.get(step_id)
    
    def get_entry_step(self) -> Optional["CallFlowStep"]:
        """Get the entry point step."""
        return self.steps.get(self.entry_point)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CallFlow":
        """Create a CallFlow from a dictionary representation."""
        flow = cls(
            name=data.get("name", "Unnamed Flow"),
            description=data.get("description", ""),
            entry_point=data.get("entry_point", "start")
        )
        
        # Process steps
        for step_id, step_data in data.get("steps", {}).items():
            step = CallFlowStep(
                id=step_id,
                phrases=step_data.get("phrases", []),
                transitions=step_data.get("transitions", {}),
                metadata=step_data.get("metadata", {})
            )
            flow.add_step(step)
        
        return flow
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation for serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "entry_point": self.entry_point,
            "steps": {
                step_id: {
                    "phrases": step.phrases,
                    "transitions": step.transitions,
                    "metadata": step.metadata
                }
                for step_id, step in self.steps.items()
            }
        }


@dataclass
class CallFlowStep:
    """A step in a call flow with possible phrases and transitions."""
    id: str
    phrases: List[str] = field(default_factory=list)
    transitions: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_next_step_id(self, condition: str = "default") -> Optional[str]:
        """Get the ID of the next step based on a condition."""
        return self.transitions.get(condition, self.transitions.get("default"))
    
    def get_all_possible_next_steps(self) -> List[str]:
        """Get all possible next step IDs."""
        return list(self.transitions.values())


@dataclass
class CallState:
    """Represents the current state of a call for prediction purposes."""
    call_id: str
    flow_id: str
    current_step_id: str
    history: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def update_step(self, new_step_id: str) -> None:
        """Update the current step and add to history."""
        self.history.append(self.current_step_id)
        self.current_step_id = new_step_id
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "call_id": self.call_id,
            "flow_id": self.flow_id,
            "current_step_id": self.current_step_id,
            "history": self.history,
            "metadata": self.metadata
        }


@dataclass
class PredictionTask:
    """A task for generating a predicted phrase."""
    task_id: str
    call_id: str 
    phrase: str
    provider_type: str
    voice_id: str
    priority: PredictionPriority
    step_id: str
    speed: float = 1.0
    created_at: float = field(default_factory=time.time)
    params: Dict[str, Any] = field(default_factory=dict)
    
    def get_cache_key(self) -> str:
        """Get cache key for this prediction task."""
        return TTSCacheKey.generate(
            self.phrase, 
            self.provider_type, 
            self.voice_id, 
            self.speed, 
            **self.params
        )


class PredictiveGenerator:
    """
    Generates audio for likely next phrases in advance.
    
    This class predicts and pre-generates speech for phrases that are likely
    to be needed next in a conversation flow, speeding up response times by
    having audio ready before it's requested.
    
    Features:
    - Call flow definition and tracking
    - Pattern-based prediction of next phrases
    - Background generation with prioritization
    - Integration with the caching system
    """
    
    def __init__(self, 
                 cache_manager: TTSCacheManager,
                 tts_generator: Callable,
                 max_workers: int = 2,
                 prediction_depth: int = 2,
                 enabled: bool = True):
        """
        Initialize the predictive generator.
        
        Args:
            cache_manager: The TTSCacheManager for storing generated audio
            tts_generator: Function that generates TTS audio (phrase, voice_id, etc) -> bytes
            max_workers: Maximum number of background generation threads
            prediction_depth: How many steps ahead to predict
            enabled: Whether predictive generation is enabled
        """
        self.cache_manager = cache_manager
        self.tts_generator = tts_generator
        self.max_workers = max_workers
        self.prediction_depth = prediction_depth
        self.enabled = enabled
        
        # Call flows by ID
        self.call_flows: Dict[str, CallFlow] = {}
        
        # Active call states by call ID
        self.call_states: Dict[str, CallState] = {}
        
        # Task queue for background generation
        self.task_queue: "queue.PriorityQueue[Tuple[int, PredictionTask]]" = queue.PriorityQueue()
        
        # Track currently processing tasks to avoid duplicates
        self.processing_tasks: Set[str] = set()
        self.processing_lock = threading.RLock()
        
        # Thread pool for generation tasks
        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="tts-predict-"
        )
        
        # Event emitter for monitoring
        self.event_emitter = TTSEventEmitter()
        
        # Stats tracking
        self.stats = {
            "tasks_generated": 0,
            "cache_hits": 0,
            "successful_predictions": 0,
            "total_predictions": 0,
            "generation_times": []
        }
        self.stats_lock = threading.RLock()
        
        # Start worker thread
        self._stop_event = threading.Event()
        self._worker_thread = threading.Thread(
            target=self._process_queue,
            daemon=True,
            name="tts-predict-worker"
        )
        self._worker_thread.start()
        
        logger.info(f"PredictiveGenerator initialized with {max_workers} workers, "
                   f"prediction depth {prediction_depth}")
    
    def register_call_flow(self, flow: Union[CallFlow, Dict[str, Any]]) -> str:
        """
        Register a call flow for prediction.
        
        Args:
            flow: CallFlow object or dictionary representation
            
        Returns:
            The flow ID
        """
        if isinstance(flow, dict):
            flow = CallFlow.from_dict(flow)
        
        flow_id = flow.name.lower().replace(" ", "_")
        self.call_flows[flow_id] = flow
        
        logger.info(f"Registered call flow '{flow.name}' with {len(flow.steps)} steps")
        return flow_id
    
    def register_call_flow_from_file(self, file_path: str) -> str:
        """
        Register a call flow from a JSON file.
        
        Args:
            file_path: Path to JSON file with flow definition
            
        Returns:
            The flow ID
        """
        with open(file_path, 'r') as f:
            flow_data = json.load(f)
        
        return self.register_call_flow(flow_data)
    
    def start_call(self, call_id: str, flow_id: str) -> bool:
        """
        Start tracking a new call with a particular flow.
        
        Args:
            call_id: Unique call identifier
            flow_id: ID of the call flow to use
            
        Returns:
            Success status
        """
        if flow_id not in self.call_flows:
            logger.error(f"Cannot start call with unknown flow: {flow_id}")
            return False
        
        flow = self.call_flows[flow_id]
        entry_step = flow.get_entry_step()
        
        if not entry_step:
            logger.error(f"Call flow {flow_id} has no valid entry point")
            return False
        
        # Create call state and start predictions
        state = CallState(
            call_id=call_id,
            flow_id=flow_id,
            current_step_id=entry_step.id
        )
        self.call_states[call_id] = state
        
        # Begin prediction for this call
        if self.enabled:
            self.predict_next_phrases(call_id)
        
        logger.info(f"Started call {call_id} with flow {flow_id}")
        self.event_emitter.emit(TTSEventType.INFO, f"Call {call_id} started with flow {flow_id}")
        return True
    
    def update_call_step(self, call_id: str, step_id: str) -> bool:
        """
        Update a call's current step and trigger new predictions.
        
        Args:
            call_id: The call identifier
            step_id: The new step ID
            
        Returns:
            Success status
        """
        if call_id not in self.call_states:
            logger.warning(f"Attempted to update unknown call: {call_id}")
            return False
        
        state = self.call_states[call_id]
        flow = self.call_flows.get(state.flow_id)
        
        if not flow or step_id not in flow.steps:
            logger.error(f"Invalid step ID: {step_id} for call {call_id}")
            return False
        
        # Update the call state
        state.update_step(step_id)
        
        # Generate new predictions based on updated state
        if self.enabled:
            self.predict_next_phrases(call_id)
        
        logger.debug(f"Updated call {call_id} to step {step_id}")
        return True
    
    def end_call(self, call_id: str) -> None:
        """
        End tracking for a call.
        
        Args:
            call_id: The call identifier
        """
        if call_id in self.call_states:
            # Record final state for learning (could be implemented later)
            del self.call_states[call_id]
            logger.info(f"Ended call {call_id}")
            self.event_emitter.emit(TTSEventType.INFO, f"Call {call_id} ended")
    
    def predict_next_phrases(self, call_id: str) -> List[str]:
        """
        Predict and queue generation for the next likely phrases.
        
        Args:
            call_id: The call identifier
            
        Returns:
            List of phrases queued for generation
        """
        if not self.enabled or call_id not in self.call_states:
            return []
        
        state = self.call_states[call_id]
        flow = self.call_flows.get(state.flow_id)
        
        if not flow:
            return []
        
        # Get current step
        current_step = flow.get_step(state.current_step_id)
        if not current_step:
            return []
        
        queued_phrases = []
        
        # Use prediction depth to determine how far ahead to look
        self._predict_ahead(
            flow=flow,
            call_id=call_id,
            start_step=current_step,
            depth=0,
            max_depth=self.prediction_depth,
            queued_phrases=queued_phrases,
            visited=set()
        )
        
        return queued_phrases
    
    def _predict_ahead(self, flow: CallFlow, call_id: str, start_step: CallFlowStep, 
                      depth: int, max_depth: int, queued_phrases: List[str], 
                      visited: Set[str]) -> None:
        """
        Recursively predict and queue phrases ahead in the call flow.
        
        Args:
            flow: The call flow
            call_id: The call identifier
            start_step: The starting step for prediction
            depth: Current recursion depth
            max_depth: Maximum recursion depth
            queued_phrases: List to collect queued phrases
            visited: Set of visited step IDs to prevent cycles
        """
        if depth > max_depth or start_step.id in visited:
            return
        
        visited.add(start_step.id)
        
        # Queue all phrases in this step with priority based on depth
        priority = PredictionPriority.HIGH if depth == 0 else (
            PredictionPriority.MEDIUM if depth == 1 else PredictionPriority.LOW
        )
        
        for phrase in start_step.phrases:
            # Get default provider and voice from call state metadata
            state = self.call_states.get(call_id)
            if not state:
                continue
                
            provider_type = state.metadata.get("provider_type", "default")
            voice_id = state.metadata.get("voice_id", "default")
            speed = state.metadata.get("speed", 1.0)
            
            # Skip if already in cache
            cache_key = TTSCacheKey.generate(phrase, provider_type, voice_id, speed)
            if self.cache_manager.get(cache_key):
                with self.stats_lock:
                    self.stats["cache_hits"] += 1
                continue
            
            # Queue for generation
            self._queue_prediction_task(
                call_id=call_id,
                phrase=phrase,
                provider_type=provider_type,
                voice_id=voice_id,
                speed=speed,
                priority=priority,
                step_id=start_step.id
            )
            queued_phrases.append(phrase)
        
        # Recursively process next steps
        next_step_ids = start_step.get_all_possible_next_steps()
        for next_id in next_step_ids:
            next_step = flow.get_step(next_id)
            if next_step:
                self._predict_ahead(
                    flow=flow,
                    call_id=call_id, 
                    start_step=next_step,
                    depth=depth + 1,
                    max_depth=max_depth,
                    queued_phrases=queued_phrases,
                    visited=visited.copy()  # Copy to allow different recursion paths
                )
    
    def _queue_prediction_task(self, call_id: str, phrase: str, 
                              provider_type: str, voice_id: str,
                              speed: float, priority: PredictionPriority,
                              step_id: str, params: Dict[str, Any] = None) -> str:
        """
        Queue a prediction task for background processing.
        
        Args:
            call_id: The call identifier
            phrase: Text to synthesize
            provider_type: TTS provider type
            voice_id: Voice identifier
            speed: Speech rate
            priority: Task priority
            step_id: Source step ID
            params: Additional parameters
            
        Returns:
            Task ID
        """
        if params is None:
            params = {}
        
        task_id = str(uuid.uuid4())
        task = PredictionTask(
            task_id=task_id,
            call_id=call_id,
            phrase=phrase,
            provider_type=provider_type,
            voice_id=voice_id,
            speed=speed,
            priority=priority,
            step_id=step_id,
            params=params
        )
        
        # Queue task with priority
        self.task_queue.put((priority.value, task))
        
        with self.stats_lock:
            self.stats["total_predictions"] += 1
        
        logger.debug(f"Queued prediction for '{phrase[:30]}...' with {priority.name} priority")
        return task_id
    
    def _process_queue(self) -> None:
        """Worker thread to process the prediction queue."""
        while not self._stop_event.is_set():
            try:
                # Try to get a task with timeout
                try:
                    _, task = self.task_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                # Skip if call no longer exists
                if task.call_id not in self.call_states:
                    self.task_queue.task_done()
                    continue
                
                # Check if already in cache (could have been added since queueing)
                cache_key = task.get_cache_key()
                if self.cache_manager.get(cache_key):
                    with self.stats_lock:
                        self.stats["cache_hits"] += 1
                    self.task_queue.task_done()
                    continue
                
                # Check if already processing
                with self.processing_lock:
                    if cache_key in self.processing_tasks:
                        self.task_queue.task_done()
                        continue
                    self.processing_tasks.add(cache_key)
                
                # Submit to thread pool
                self.executor.submit(
                    self._generate_audio, 
                    task
                )
                
                self.task_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error in prediction worker: {e}")
    
    def _generate_audio(self, task: PredictionTask) -> None:
        """
        Generate TTS audio for a prediction task.
        
        Args:
            task: The prediction task
        """
        try:
            start_time = time.time()
            
            # Generate TTS audio
            self.event_emitter.emit(
                TTSEventType.GENERATION_START, 
                f"Predictive generation for: {task.phrase[:50]}...",
                extra={"call_id": task.call_id, "predictive": True}
            )
            
            audio_data = self.tts_generator(
                task.phrase, 
                task.voice_id, 
                task.speed,
                **task.params
            )
            
            if audio_data:
                # Store in cache
                self.cache_manager.set(task.get_cache_key(), audio_data)
                
                generation_time = time.time() - start_time
                with self.stats_lock:
                    self.stats["tasks_generated"] += 1
                    self.stats["successful_predictions"] += 1
                    # Keep only the last 100 generation times for stats
                    self.stats["generation_times"].append(generation_time)
                    if len(self.stats["generation_times"]) > 100:
                        self.stats["generation_times"].pop(0)
                
                self.event_emitter.emit(
                    TTSEventType.GENERATION_COMPLETE, 
                    f"Predictive generation complete: {len(audio_data)} bytes in {generation_time:.2f}s",
                    extra={
                        "call_id": task.call_id, 
                        "predictive": True,
                        "audio_size": len(audio_data),
                        "generation_time": generation_time
                    }
                )
                
                logger.debug(
                    f"Generated prediction for '{task.phrase[:30]}...' "
                    f"({len(audio_data)} bytes) in {generation_time:.2f}s"
                )
            else:
                logger.warning(f"Failed to generate prediction for: {task.phrase[:50]}...")
                self.event_emitter.emit(
                    TTSEventType.ERROR, 
                    f"Predictive generation failed for: {task.phrase[:50]}...",
                    extra={"call_id": task.call_id, "predictive": True}
                )
        
        except Exception as e:
            logger.error(f"Error in predictive generation: {e}")
            self.event_emitter.emit(
                TTSEventType.ERROR, 
                f"Error in predictive generation: {str(e)}",
                extra={"call_id": task.call_id, "predictive": True}
            )
        
        finally:
            # Remove from processing set
            with self.processing_lock:
                self.processing_tasks.discard(task.get_cache_key())
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about predictive generation.
        
        Returns:
            Dictionary of statistics
        """
        with self.stats_lock:
            stats = dict(self.stats)
            
            # Calculate additional metrics
            total_preds = stats["total_predictions"]
            if total_preds > 0:
                stats["success_rate"] = stats["successful_predictions"] / total_preds
                stats["cache_hit_rate"] = stats["cache_hits"] / total_preds
            else:
                stats["success_rate"] = 0
                stats["cache_hit_rate"] = 0
            
            if stats["generation_times"]:
                stats["avg_generation_time"] = sum(stats["generation_times"]) / len(stats["generation_times"])
            else:
                stats["avg_generation_time"] = 0
            
            # Replace full list with summary stats for generation times
            if stats["generation_times"]:
                times = sorted(stats["generation_times"])
                stats["generation_time_stats"] = {
                    "min": min(times),
                    "max": max(times),
                    "avg": sum(times) / len(times),
                    "median": times[len(times) // 2],
                    "count": len(times)
                }
            else:
                stats["generation_time_stats"] = {
                    "min": 0,
                    "max": 0,
                    "avg": 0,
                    "median": 0,
                    "count": 0
                }
            del stats["generation_times"]
        
        return stats
    
    def set_call_metadata(self, call_id: str, key: str, value: Any) -> bool:
        """
        Set metadata for a call that can affect prediction behavior.
        
        Args:
            call_id: The call identifier
            key: Metadata key
            value: Metadata value
            
        Returns:
            Success status
        """
        if call_id not in self.call_states:
            return False
        
        self.call_states[call_id].metadata[key] = value
        return True
    
    def set_prediction_depth(self, depth: int) -> None:
        """
        Set how many steps ahead to predict.
        
        Args:
            depth: Number of steps ahead to predict (1-5)
        """
        self.prediction_depth = max(1, min(5, depth))
        logger.info(f"Prediction depth set to {self.prediction_depth}")
    
    def enable(self) -> None:
        """Enable predictive generation."""
        self.enabled = True
        logger.info("Predictive generation enabled")
    
    def disable(self) -> None:
        """Disable predictive generation."""
        self.enabled = False
        logger.info("Predictive generation disabled")
    
    def shutdown(self) -> None:
        """Shutdown the predictive generator."""
        self._stop_event.set()
        self.executor.shutdown(wait=False)
        logger.info("Predictive generator shutdown") 