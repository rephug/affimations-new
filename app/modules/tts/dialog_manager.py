#!/usr/bin/env python
# Dialog Manager Module for TTS Conversation Flow

import logging
import re
import time
import threading
from typing import List, Dict, Any, Optional, Tuple, Generator, Callable
from enum import Enum

# Try to import nltk for sentence tokenization
try:
    import nltk
    from nltk.tokenize import sent_tokenize
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False

logger = logging.getLogger('dialog-manager')

class DialogTurnState(Enum):
    """Enum for dialog turn states."""
    IDLE = 'idle'
    SPEAKING = 'speaking'
    LISTENING = 'listening'
    PROCESSING = 'processing'
    INTERRUPTED = 'interrupted'

class DialogManager:
    """
    Manages conversation flow, sentence processing, and turn-taking for natural dialog.
    
    Features:
    - Natural sentence processing with NLTK integration
    - Fragment generation for low-latency initial responses
    - Turn-taking management with state tracking
    - Natural pauses between sentences and turns
    - Support for interruptions and backchanneling
    """
    
    def __init__(self, 
                 min_fragment_size: int = 5,
                 inter_sentence_pause_ms: int = 300,
                 initial_fragment_length: int = 15,
                 end_of_turn_pause_ms: int = 800,
                 punctuation_pause_ms: Dict[str, int] = None):
        """
        Initialize the dialog manager.
        
        Args:
            min_fragment_size: Minimum fragment size for processing
            inter_sentence_pause_ms: Pause between sentences in milliseconds
            initial_fragment_length: Minimum length of initial fragment for quick response
            end_of_turn_pause_ms: Pause at the end of a dialog turn in milliseconds
            punctuation_pause_ms: Dictionary mapping punctuation to pause duration
        """
        self.min_fragment_size = min_fragment_size
        self.inter_sentence_pause_ms = inter_sentence_pause_ms
        self.initial_fragment_length = initial_fragment_length
        self.end_of_turn_pause_ms = end_of_turn_pause_ms
        
        # Default punctuation pause mapping if not provided
        self.punctuation_pause_ms = punctuation_pause_ms or {
            '.': 300,
            ',': 150,
            ';': 200,
            ':': 200,
            '?': 350,
            '!': 350,
            '-': 100,
            '...': 400
        }
        
        # State tracking
        self.current_state = DialogTurnState.IDLE
        self.state_lock = threading.Lock()
        self.conversation_history = []
        self.current_turn_id = None
        
        # Initialize NLTK if available
        if NLTK_AVAILABLE:
            try:
                # Check if punkt tokenizer is downloaded
                nltk.data.find('tokenizers/punkt')
            except LookupError:
                logger.info("Downloading NLTK punkt tokenizer")
                nltk.download('punkt', quiet=True)
        else:
            logger.warning("NLTK not available, falling back to basic sentence splitting")
    
    def process_text(self, text: str, urgency: float = 0.0) -> Generator[Tuple[str, int], None, None]:
        """
        Process text into fragments with timing information.
        
        Args:
            text: Input text to process
            urgency: Urgency factor (0.0-1.0) that reduces pauses for urgent messages
            
        Returns:
            Generator yielding tuples of (text_fragment, pause_duration_ms)
        """
        if not text:
            logger.warning("Empty text provided to dialog manager")
            return
        
        # Update state
        with self.state_lock:
            self.current_state = DialogTurnState.SPEAKING
        
        # Extract initial fragment for rapid response if text is long enough
        if len(text) > self.initial_fragment_length and urgency < 0.8:
            first_fragment = self._get_initial_fragment(text)
            if first_fragment:
                yield (first_fragment, 0)  # No pause after initial fragment
                
                # Remove the fragment from the text
                text = text[len(first_fragment):].lstrip()
        
        # Tokenize the remaining text into sentences
        sentences = self._tokenize_sentences(text)
        
        # Process each sentence
        for i, sentence in enumerate(sentences):
            if not sentence.strip():
                continue
                
            # Calculate pause after this sentence
            pause_ms = 0
            if i < len(sentences) - 1:
                # Inter-sentence pause
                pause_ms = self.inter_sentence_pause_ms
            elif i == len(sentences) - 1:
                # End-of-turn pause
                pause_ms = self.end_of_turn_pause_ms
            
            # Adjust pause based on urgency
            if urgency > 0:
                pause_ms = int(pause_ms * (1 - urgency))
                
            # Check for specific punctuation pauses
            last_char = sentence.strip()[-1] if sentence.strip() else ''
            if last_char in self.punctuation_pause_ms:
                pause_ms = max(pause_ms, self.punctuation_pause_ms[last_char])
            
            # Process longer sentences into speaking fragments
            if len(sentence) > 100:
                fragments = self._split_long_sentence(sentence)
                for j, fragment in enumerate(fragments):
                    # Use the calculated pause only for the last fragment
                    frag_pause = pause_ms if j == len(fragments) - 1 else self.punctuation_pause_ms.get(',', 100)
                    yield (fragment, frag_pause)
            else:
                yield (sentence, pause_ms)
    
    def process_dialog_turn(self, 
                           text: str, 
                           turn_id: Optional[str] = None,
                           context: Optional[Dict[str, Any]] = None,
                           urgency: float = 0.0) -> Generator[Dict[str, Any], None, None]:
        """
        Process a complete dialog turn with additional metadata.
        
        Args:
            text: Dialog turn text
            turn_id: Unique ID for this turn
            context: Additional context for this turn
            urgency: Urgency factor (0.0-1.0)
            
        Returns:
            Generator yielding fragment info dictionaries
        """
        # Generate turn ID if not provided
        if not turn_id:
            turn_id = f"turn_{int(time.time())}_{len(self.conversation_history)}"
        
        # Store current turn ID
        self.current_turn_id = turn_id
        
        # Start timing
        start_time = time.time()
        
        # Create turn context
        turn_context = {
            "turn_id": turn_id,
            "text": text,
            "start_time": start_time,
            "additional_context": context or {},
            "fragments": []
        }
        
        # Update state
        with self.state_lock:
            prev_state = self.current_state
            self.current_state = DialogTurnState.SPEAKING
        
        # Process the text into fragments
        fragment_index = 0
        for fragment, pause_ms in self.process_text(text, urgency):
            # Calculate timing
            current_time = time.time()
            time_since_start = current_time - start_time
            
            # Create fragment info
            fragment_info = {
                "fragment": fragment,
                "index": fragment_index,
                "turn_id": turn_id,
                "pause_after_ms": pause_ms,
                "time_since_turn_start": time_since_start,
                "is_last_fragment": False
            }
            
            # Add to turn context
            turn_context["fragments"].append({
                "text": fragment,
                "time": time_since_start,
                "pause": pause_ms
            })
            
            # Yield the fragment info
            yield fragment_info
            
            # Apply the pause if specified
            if pause_ms > 0:
                time.sleep(pause_ms / 1000.0)
                
            fragment_index += 1
        
        # Mark last fragment
        if turn_context["fragments"]:
            turn_context["fragments"][-1]["is_last_fragment"] = True
        
        # Update turn context with completion information
        turn_context["end_time"] = time.time()
        turn_context["duration"] = turn_context["end_time"] - turn_context["start_time"]
        turn_context["fragment_count"] = fragment_index
        
        # Add to conversation history
        self.conversation_history.append(turn_context)
        
        # Update state
        with self.state_lock:
            self.current_state = DialogTurnState.IDLE
            
        # Yield final marker with complete turn info
        yield {
            "is_last_fragment": True,
            "turn_complete": True,
            "turn_id": turn_id,
            "turn_duration": turn_context["duration"],
            "fragment_count": fragment_index
        }
    
    def start_listening(self) -> None:
        """
        Indicate that the system is now listening to user input.
        Updates the dialog state to LISTENING.
        """
        with self.state_lock:
            self.current_state = DialogTurnState.LISTENING
    
    def start_processing(self) -> None:
        """
        Indicate that the system is processing user input.
        Updates the dialog state to PROCESSING.
        """
        with self.state_lock:
            self.current_state = DialogTurnState.PROCESSING
    
    def interrupt_speaking(self) -> bool:
        """
        Interrupt the current speaking turn.
        
        Returns:
            bool: True if successfully interrupted, False if not speaking
        """
        with self.state_lock:
            if self.current_state == DialogTurnState.SPEAKING:
                self.current_state = DialogTurnState.INTERRUPTED
                return True
            return False
    
    def get_state(self) -> DialogTurnState:
        """
        Get the current dialog state.
        
        Returns:
            DialogTurnState: Current state of the dialog
        """
        with self.state_lock:
            return self.current_state
    
    def get_conversation_history(self, max_turns: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get the conversation history.
        
        Args:
            max_turns: Maximum number of turns to return (most recent)
            
        Returns:
            List of turn information dictionaries
        """
        if max_turns is not None:
            return self.conversation_history[-max_turns:]
        return self.conversation_history
    
    def _get_initial_fragment(self, text: str) -> Optional[str]:
        """
        Get an initial fragment for rapid response.
        
        Args:
            text: Input text
            
        Returns:
            Initial fragment or None if not appropriate
        """
        # Look for natural breakpoints first (comma, period, etc.)
        match = re.search(r'^([^.!?;:]+[,.!?;:])', text)
        if match and len(match.group(1)) >= self.min_fragment_size:
            return match.group(1)
        
        # If no punctuation, look for a good stopping point around initial_fragment_length
        target_length = min(len(text), max(self.initial_fragment_length, 30))
        
        # Try to find a word boundary around the target length
        for i in range(target_length, self.min_fragment_size, -1):
            if i < len(text) and text[i] == ' ':
                return text[:i]
        
        # If text is too short or no good breaking point found
        if len(text) <= self.initial_fragment_length:
            return None
            
        # Fallback to initial fragment length
        return text[:self.initial_fragment_length]
    
    def _tokenize_sentences(self, text: str) -> List[str]:
        """
        Tokenize text into sentences using NLTK if available.
        
        Args:
            text: Input text
            
        Returns:
            List of sentences
        """
        if not text:
            return []
            
        if NLTK_AVAILABLE:
            try:
                return sent_tokenize(text)
            except Exception as e:
                logger.error(f"Error tokenizing text with NLTK: {e}")
        
        # Fallback to basic sentence splitting
        basic_splits = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in basic_splits if s.strip()]
    
    def _split_long_sentence(self, sentence: str) -> List[str]:
        """
        Split a long sentence into smaller fragments.
        
        Args:
            sentence: Long sentence to split
            
        Returns:
            List of sentence fragments
        """
        # Split on commas, semicolons, and other natural pauses
        fragments = re.split(r'(?<=[,;:])\s+', sentence)
        
        # Further split overly long fragments
        result = []
        for fragment in fragments:
            if len(fragment) > 100:
                # Split based on phrase structure using prepositions and conjunctions
                sub_fragments = re.split(r'(?<= (?:and|but|or|because|when|if|that|with|by|for|to|in|on|at))\s+', fragment)
                result.extend(sub_fragments)
            else:
                result.append(fragment)
                
        return result
    
    def register_backchannel(self, 
                           backchannel_text: str, 
                           source: str = "user") -> None:
        """
        Register a backchannel from the user or system.
        Backchannels are brief responses like "uh-huh", "right", "I see".
        
        Args:
            backchannel_text: The backchannel text
            source: Source of the backchannel ("user" or "system")
        """
        # Create backchannel event
        backchannel_event = {
            "type": "backchannel",
            "text": backchannel_text,
            "source": source,
            "timestamp": time.time(),
            "current_turn_id": self.current_turn_id,
            "current_state": self.current_state.value
        }
        
        # Add to conversation history as a special event
        if self.conversation_history:
            # Add to the most recent turn
            if "events" not in self.conversation_history[-1]:
                self.conversation_history[-1]["events"] = []
            self.conversation_history[-1]["events"].append(backchannel_event)
            
    def get_optimal_response_time(self) -> float:
        """
        Calculate the optimal response time based on conversation history.
        
        Returns:
            Optimal response time in seconds
        """
        # Default response time
        default_time = 0.8  # 800ms
        
        # If not enough history, return default
        if len(self.conversation_history) < 2:
            return default_time
            
        # Calculate average gap between turns
        gaps = []
        for i in range(1, len(self.conversation_history)):
            prev_turn = self.conversation_history[i-1]
            curr_turn = self.conversation_history[i]
            
            # Calculate gap
            if "end_time" in prev_turn and "start_time" in curr_turn:
                gap = curr_turn["start_time"] - prev_turn["end_time"]
                # Only use reasonable gaps (0.3s to 2.5s)
                if 0.3 <= gap <= 2.5:
                    gaps.append(gap)
        
        # If no valid gaps, return default
        if not gaps:
            return default_time
            
        # Calculate average gap
        avg_gap = sum(gaps) / len(gaps)
        
        # Adjust slightly to sound natural (slightly faster than human)
        return max(0.3, min(2.0, avg_gap * 0.9)) 