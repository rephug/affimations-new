#!/usr/bin/env python
# Text processing utilities for TTS

import logging
import re
import nltk
from typing import List, Generator, Optional, Tuple

logger = logging.getLogger("tts-text-processing")

class TextFragmenter:
    """
    Handles text fragmentation for optimal streaming TTS.
    
    This class provides methods to break text into fragments for streaming
    with support for quick response and proper sentence boundaries.
    """
    
    def __init__(self, 
                min_fragment_size: int = 5, 
                max_fragment_size: int = 100,
                fast_first_response: bool = True,
                force_nltk_download: bool = False):
        """
        Initialize the text fragmenter.
        
        Args:
            min_fragment_size (int): Minimum fragment size in characters
            max_fragment_size (int): Maximum fragment size in characters
            fast_first_response (bool): Enable quick first response
            force_nltk_download (bool): Force download of NLTK data
        """
        self.min_fragment_size = min_fragment_size
        self.max_fragment_size = max_fragment_size
        self.fast_first_response = fast_first_response
        
        # Download NLTK data if needed
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            logger.info("Downloading NLTK punkt tokenizer...")
            nltk.download('punkt')
        
        # Initialize custom punctuation regex
        self.punctuation_regex = re.compile(r'([.!?])\s+')
    
    def get_initial_fragment(self, text: str) -> Optional[str]:
        """
        Get an initial fragment for fast first response.
        
        Args:
            text (str): Input text
            
        Returns:
            Optional[str]: Initial fragment or None if not applicable
        """
        if not self.fast_first_response or len(text) <= self.min_fragment_size:
            return None
        
        # Look for punctuation after minimum size
        for i in range(self.min_fragment_size, min(len(text), 30)):
            if text[i] in '.,:;!? ':
                # Found a good break point
                return text[:i+1].strip()
        
        # No good break point, use first few words
        words = text.split()
        if len(words) > 2:
            return ' '.join(words[:2]) + ' '
        
        return None
    
    def split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences using NLTK.
        
        Args:
            text (str): Input text
            
        Returns:
            List[str]: List of sentences
        """
        try:
            return nltk.sent_tokenize(text)
        except Exception as e:
            logger.error(f"Error in NLTK sentence tokenization: {e}")
            # Fallback to simple regex-based splitting
            return self._regex_split_sentences(text)
    
    def _regex_split_sentences(self, text: str) -> List[str]:
        """
        Split text using regex (fallback method).
        
        Args:
            text (str): Input text
            
        Returns:
            List[str]: List of sentences
        """
        # Split on common sentence terminators
        sentences = self.punctuation_regex.split(text)
        
        # Combine punctuation with preceding text
        result = []
        for i in range(0, len(sentences)-1, 2):
            if i+1 < len(sentences):
                result.append(sentences[i] + sentences[i+1])
            else:
                result.append(sentences[i])
        
        # Add the last item if there's an odd number
        if len(sentences) % 2 == 1:
            result.append(sentences[-1])
        
        return [s.strip() for s in result if s.strip()]
    
    def process_stream(self, text_stream: Generator[str, None, None]) -> Generator[str, None, None]:
        """
        Process a stream of text into optimal fragments.
        
        Args:
            text_stream (Generator[str, None, None]): Stream of text chunks
            
        Returns:
            Generator[str, None, None]: Stream of optimized fragments
        """
        buffer = ""
        
        for chunk in text_stream:
            buffer += chunk
            
            # Process complete sentences from buffer
            sentences = self.split_into_sentences(buffer)
            
            # Keep the last (potentially incomplete) sentence in buffer
            if sentences:
                # Yield all but the last sentence
                for sentence in sentences[:-1]:
                    yield sentence
                
                # Check if the last sentence appears complete
                last_sentence = sentences[-1]
                if buffer.strip().endswith(last_sentence.strip()) and last_sentence.strip()[-1] in '.!?':
                    yield last_sentence
                    buffer = ""
                else:
                    # Keep last sentence in buffer as it may be incomplete
                    buffer = last_sentence
            
            # Handle very long buffers by force-breaking
            if len(buffer) > self.max_fragment_size:
                # Find the last good break point
                break_point = buffer.rfind(' ', self.min_fragment_size, self.max_fragment_size)
                if break_point == -1:
                    break_point = self.max_fragment_size
                
                yield buffer[:break_point].strip()
                buffer = buffer[break_point:].strip()
        
        # Yield any remaining text in buffer
        if buffer:
            yield buffer
    
    def fragment_text(self, text: str) -> Tuple[Optional[str], Generator[str, None, None]]:
        """
        Fragment text for optimal streaming, returning initial fragment and a generator.
        
        Args:
            text (str): Input text
            
        Returns:
            Tuple[Optional[str], Generator[str, None, None]]: Initial fragment and sentence generator
        """
        initial_fragment = self.get_initial_fragment(text)
        
        # Process the remaining text
        remaining_text = text
        if initial_fragment:
            # Remove initial fragment from the text to avoid duplication
            if text.startswith(initial_fragment):
                remaining_text = text[len(initial_fragment):].strip()
        
        # Create generator for remaining sentences
        def sentence_generator():
            for sentence in self.split_into_sentences(remaining_text):
                yield sentence
        
        return initial_fragment, sentence_generator() 