# Morning Coffee Project - Cursor Command Examples

This document provides practical examples of Cursor commands specifically tailored for the Morning Coffee project. These examples demonstrate how to effectively use Cursor's AI capabilities with our project's architecture and components.

## Code Generation Examples

### Generating a New API Endpoint

**Command:**
```
/generate Create a new Flask endpoint that allows users to update their preferred call time, with input validation and error handling.
```

**Expected Output:**
```python
@app.route('/update_preferred_time', methods=['POST'])
def update_preferred_time():
    """Update a user's preferred call time.
    
    Expects JSON body with:
    - phone_number: User's phone number in E.164 format
    - preferred_time: Preferred time in HH:MM format (24-hour)
    
    Returns:
        JSON response with status and message
    """
    try:
        # Parse request data
        data = request.json
        if not data or 'phone_number' not in data or 'preferred_time' not in data:
            return jsonify({
                "status": "error", 
                "message": "Missing required fields: phone_number and preferred_time"
            }), 400
        
        phone_number = data['phone_number']
        preferred_time = data['preferred_time']
        
        # Validate phone number format (E.164)
        phone_regex = r'^\+[1-9]\d{1,14}$'
        if not re.match(phone_regex, phone_number):
            return jsonify({
                "status": "error", 
                "message": "Invalid phone number format. Must be in E.164 format (e.g., +15551234567)"
            }), 400
        
        # Validate time format
        time_regex = r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$'
        if not re.match(time_regex, preferred_time):
            return jsonify({
                "status": "error", 
                "message": "Invalid time format. Must be in HH:MM format (e.g., 08:00)"
            }), 400
        
        # Get user session
        user_session = get_user_session(phone_number)
        if not user_session:
            # Create new user session if it doesn't exist
            user_session = {}
        
        # Update preferred time
        user_session['preferred_time'] = preferred_time
        user_session['last_updated'] = datetime.now().isoformat()
        
        # Store updated session
        store_user_session(phone_number, user_session)
        
        return jsonify({
            "status": "success",
            "message": f"Preferred time updated to {preferred_time}",
            "phone_number": phone_number
        })
    
    except Exception as e:
        logger.error(f"Error updating preferred time: {e}")
        return jsonify({
            "status": "error",
            "message": "Internal server error"
        }), 500
```

### Implementing a New TTS Feature

**Command:**
```
/generate Implement a function in the Spark TTS client to support emotion parameters (happy, sad, neutral) that will modify the speech output.
```

**Expected Output:**
```python
def generate_emotional_speech(self, text: str, emotion: str = 'neutral', 
                              voice_id: Optional[str] = None, speed: float = 1.0) -> Optional[bytes]:
    """
    Generate speech with emotional inflection.
    
    Args:
        text (str): The text to convert to speech
        emotion (str): Emotion to convey ('happy', 'sad', 'neutral')
        voice_id (Optional[str]): Voice ID to use, defaults to server default
        speed (float): Speech speed factor (1.0 = normal)
        
    Returns:
        Optional[bytes]: Audio data as bytes or None if generation failed
    """
    try:
        # Validate emotion parameter
        valid_emotions = ['happy', 'sad', 'neutral']
        if emotion not in valid_emotions:
            logger.warning(f"Invalid emotion: {emotion}. Using 'neutral' instead.")
            emotion = 'neutral'
        
        # Apply emotion-specific text modifications
        modified_text = self._apply_emotion_to_text(text, emotion)
        
        # Adjust speed based on emotion
        adjusted_speed = self._adjust_speed_for_emotion(speed, emotion)
        
        logger.info(f"Generating {emotion} speech for text: {text[:50]}{'...' if len(text) > 50 else ''}")
        
        # Use the standard generate_speech method with the modified parameters
        return self.generate_speech(
            text=modified_text,
            voice_id=voice_id,
            speed=adjusted_speed
        )
    
    except Exception as e:
        logger.error(f"Error generating emotional speech: {e}")
        return None
    
def _apply_emotion_to_text(self, text: str, emotion: str) -> str:
    """Apply emotion-specific modifications to the text."""
    if emotion == 'happy':
        # Add emphasis and exclamation marks for happy emotion
        return text.replace('.', '!').replace(',', ', ')
    elif emotion == 'sad':
        # Add pauses and soften language for sad emotion
        return text.replace('.', '... ').replace('!', '.')
    else:  # neutral
        return text

def _adjust_speed_for_emotion(self, base_speed: float, emotion: str) -> float:
    """Adjust speech speed based on emotion."""
    if emotion == 'happy':
        # Happy speech is slightly faster
        return base_speed * 1.15
    elif emotion == 'sad':
        # Sad speech is slightly slower
        return base_speed * 0.85
    else:  # neutral
        return base_speed
```

## Code Explanation Examples

### Understanding the Call Flow

**Command:**
```
/explain How does the call flow work from when a user answers to when the conversation ends?
```

**Expected Output:**
```
The call flow in the Morning Coffee application follows these steps:

1. **Call Initiation**:
   - The application calls `telnyx_handler.make_call()` with the user's phone number
   - This creates a call control ID that's stored in Redis with initial state

2. **User Answers (call.answered event)**:
   - Telnyx sends a webhook to `/telnyx/call` with `event_type: 'call.answered'`
   - The application retrieves the call state and user session from Redis
   - It then generates a greeting with the user's affirmation using Spark TTS
   - The audio is uploaded to Telnyx Storage and played with `telnyx_handler.play_audio()`

3. **Greeting Playback Ends (call.playback.ended event)**:
   - When the greeting audio finishes, Telnyx sends another webhook
   - The application checks the `client_state` ("greeting_finished")
   - It then generates and plays instructions for the user to repeat the affirmation
   - After instructions, it starts recording with `telnyx_handler.start_recording()`

4. **Recording Saved (call.recording.saved event)**:
   - When recording completes, Telnyx provides a recording URL
   - The app sends this to AssemblyAI for transcription
   - Since AssemblyAI is asynchronous, it stores the transcription job ID in Redis
   - A background process or Windmill workflow checks for completed transcriptions

5. **Transcription Processing**:
   - When transcription completes, `process_transcription_result()` is called
   - For affirmation recordings, it gives positive reinforcement and moves to chat
   - For chat recordings, it sends the text to the LLM and plays back the response

6. **Conversation Loop**:
   - Steps 4-5 repeat for each user response
   - After each AI response, the app asks "Is there anything else on your mind?"
   - This loop continues until timeout or hangup

7. **Call End (call.hangup event)**:
   - When the call ends, the application updates the call state to "ended"
   - All conversation history is preserved in the user session for future calls

The entire flow is managed using the call state stored in Redis, allowing the stateless application to maintain conversation context across webhook events.
```

### Understanding the Spark TTS Integration

**Command:**
```
/explain How does the Spark TTS service generate speech and how is it integrated with the main application?
```

**Expected Output:**
```
The Spark TTS integration in the Morning Coffee project works as follows:

1. **Architecture**:
   - Spark TTS runs as a separate containerized service
   - It exposes a REST API on port 8020
   - The main application communicates with it via HTTP

2. **Spark TTS Service Implementation**:
   - Uses the Hugging Face Transformers library
   - Loads the SparkAudio/Spark-TTS-0.5B model
   - Provides endpoints for generating speech, listing voices, and health checks

3. **Speech Generation Process**:
   - The service receives text via a POST request to `/tts`
   - It processes the text through the TTS pipeline
   - The model generates audio as a numerical array
   - This is converted to WAV format and returned in the response

4. **Integration with Main Application**:
   - The main app uses the `SparkTTSClient` class to communicate with the TTS service
   - When speech is needed, it calls `generate_speech()` with the text
   - The resulting audio bytes are then uploaded to Telnyx Storage for playback
   - The public URL of this audio is used in Telnyx's call control API

5. **Error Handling and Reliability**:
   - The client implements retry mechanisms with exponential backoff
   - Errors in speech generation are caught and logged
   - The main application has fallback mechanisms if TTS fails

6. **Performance Optimization**:
   - GPU acceleration is used when available
   - The model is loaded once at startup and kept in memory
   - Audio is generated with a customizable sample rate

7. **Docker Configuration**:
   - The service is defined in `docker-compose.yml`
   - It mounts a volume for persistent model storage
   - Health checks ensure the service is operational

This separation of concerns allows the TTS functionality to be scaled independently of the main application and potentially reused across different projects.
```

## Code Editing Examples

### Improving Error Handling

**Command:**
```
/edit The error handling in the transcription job processing could be improved. Update the code to track failed jobs and implement a dead-letter queue for jobs that fail multiple times.
```

**Expected Output:**
```diff
 def process_transcription_result(job_id, job_info, transcribed_text):
     """
     Process a completed transcription and continue the call flow.
     
     Args:
         job_id (str): The transcription job ID
         job_info (dict): Information about the transcription job
         transcribed_text (str): The transcribed text
     """
     try:
         call_control_id = job_info.get('call_control_id')
         client_state = job_info.get('client_state')
         
         # Get call state
         call_state = get_call_state(call_control_id)
         if not call_state:
             logger.error(f"No call state found for call: {call_control_id}")
+            # Add to dead-letter queue
+            add_to_dead_letter_queue(job_id, job_info, "Call state not found")
             return
 
         user_number = call_state.get('user_number')
 
         # Mark transcription as processed
         job_info['status'] = 'processed'
         job_info['text'] = transcribed_text
         job_info['processed_at'] = datetime.now().timestamp()
         store_transcription_job(job_id, job_info)
 
         # Update call state with transcription result
         update_call_state(call_control_id, {
             'last_transcription': transcribed_text,
             'last_updated': datetime.now().isoformat()
         })
 
         # Process based on the client state
         if client_state == 'record_affirmation':
             # ...existing code...
 
     except Exception as e:
         logger.error(f"Error processing transcription result: {e}")
+        # Track failure and retry if under threshold
+        failure_count = job_info.get('failures', 0) + 1
+        job_info['failures'] = failure_count
+        job_info['last_error'] = str(e)
+        job_info['last_failure_time'] = datetime.now().timestamp()
+        
+        if failure_count <= 3:  # Retry up to 3 times
+            logger.info(f"Scheduling retry {failure_count} for job {job_id}")
+            job_info['status'] = 'retry_pending'
+            store_transcription_job(job_id, job_info)
+            
+            # Schedule retry with exponential backoff
+            retry_delay = 5 * (2 ** (failure_count - 1))  # 5, 10, 20 seconds
+            threading.Timer(retry_delay, retry_transcription_processing, args=[job_id]).start()
+        else:
+            # Add to dead-letter queue after exceeding retry limit
+            logger.warning(f"Job {job_id} failed {failure_count} times, moving to dead-letter queue")
+            add_to_dead_letter_queue(job_id, job_info, str(e))
+            
         # Try to handle the failure gracefully
         call_control_id = job_info.get('call_control_id')
         client_state = job_info.get('client_state')
         
         if call_control_id and client_state:
             handle_transcription_failure(call_control_id, client_state)

+def retry_transcription_processing(job_id):
+    """Retry processing a transcription job."""
+    job_info = get_transcription_job(job_id)
+    if not job_info or job_info.get('status') != 'retry_pending':
+        return  # Job was already processed or removed
+    
+    # Get the transcription text
+    transcribed_text = job_info.get('text')
+    
+    # Process the transcription again
+    process_transcription_result(job_id, job_info, transcribed_text)
+
+def add_to_dead_letter_queue(job_id, job_info, reason):
+    """
+    Add a failed job to the dead-letter queue.
+    
+    Args:
+        job_id (str): The job ID
+        job_info (dict): Job information
+        reason (str): Failure reason
+    """
+    dlq_key = f"dlq:transcription:{job_id}"
+    
+    # Add failure reason and timestamp
+    job_info['dlq_reason'] = reason
+    job_info['dlq_time'] = datetime.now().timestamp()
+    
+    # Store in Redis with a longer expiration (7 days)
+    redis_client.set(dlq_key, json.dumps(job_info), ex=604800)
+    
+    # Add to the list of dead-letter jobs
+    redis_client.sadd("dlq:transcription:jobs", job_id)
+    
+    # Log the DLQ addition
+    logger.warning(f"Added job {job_id} to dead-letter queue: {reason}")
```

### Adding a New Feature

**Command:**
```
/edit Add a caching mechanism to the Spark TTS client to avoid regenerating the same phrases repeatedly.
```

**Expected Output:**
```diff
 class SparkTTSClient:
     """Client for interacting with the Spark TTS service."""
     
     def __init__(self, base_url: str):
         """
         Initialize the Spark TTS client.
         
         Args:
             base_url (str): Base URL of the Spark TTS service
         """
         self.base_url = base_url.rstrip('/')
+        self.cache = {}
+        self.cache_hit_count = 0
+        self.cache_miss_count = 0
+        self.max_cache_size = 100  # Maximum number of items to store in cache
 
     @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
     def health_check(self) -> Dict[str, Any]:
         # ...existing code...
 
     @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
     def get_voices(self) -> Dict[str, Any]:
         # ...existing code...
 
     @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
     def generate_speech(self, text: str, voice_id: Optional[str] = None, 
                          speed: float = 1.0, seed: Optional[int] = None) -> Optional[bytes]:
         """
         Generate speech from text.
         
         Args:
             text (str): The text to convert to speech
             voice_id (Optional[str]): Voice ID to use, defaults to server default
             speed (float): Speech speed factor (1.0 = normal)
             seed (Optional[int]): Random seed for reproducibility
             
         Returns:
             Optional[bytes]: Audio data as bytes or None if generation failed
         """
+        # Generate cache key
+        cache_key = f"{text}:{voice_id or 'default'}:{speed}:{seed or 0}"
+        
+        # Check cache first
+        if cache_key in self.cache:
+            logger.info(f"Cache hit for text: {text[:30]}...")
+            self.cache_hit_count += 1
+            return self.cache[cache_key]
+        
         try:
             # Prepare the request payload
             payload = {
                 "text": text,
                 "speed": speed
             }
             
             # Add optional parameters if provided
             if voice_id:
                 payload["voice_id"] = voice_id
             
             if seed is not None:
                 payload["seed"] = seed
             
             logger.info(f"Generating speech for text: {text[:50]}{'...' if len(text) > 50 else ''}")
+            self.cache_miss_count += 1
             
             # Send request to the Spark TTS service
             response = requests.post(
                 f"{self.base_url}/tts",
                 json=payload,
                 timeout=30  # Longer timeout for speech generation
             )
             
             if response.status_code == 200:
+                # Cache the result
+                audio_data = response.content
+                self._update_cache(cache_key, audio_data)
+                return audio_data
+            else:
+                logger.error(f"Speech generation failed with status {response.status_code}: {response.text}")
+                return None
+        except Exception as e:
+            logger.error(f"Error generating speech with Spark TTS: {e}")
+            return None
+    
+    def _update_cache(self, key: str, value: bytes) -> None:
+        """
+        Update the cache with a new item, removing oldest if cache is full.
+        
+        Args:
+            key (str): Cache key
+            value (bytes): Audio data to cache
+        """
+        # If cache is full, remove the oldest item (first in, first out)
+        if len(self.cache) >= self.max_cache_size:
+            oldest_key = next(iter(self.cache))
+            del self.cache[oldest_key]
+            
+        # Add new item to cache
+        self.cache[key] = value
+        
+        # Log cache statistics
+        if (self.cache_hit_count + self.cache_miss_count) % 100 == 0:
+            total_requests = self.cache_hit_count + self.cache_miss_count
+            hit_ratio = (self.cache_hit_count / total_requests) * 100 if total_requests > 0 else 0
+            logger.info(f"TTS cache stats: {len(self.cache)} items, {hit_ratio:.1f}% hit ratio")
+    
+    def get_cache_stats(self) -> Dict[str, Any]:
+        """
+        Get statistics about the TTS cache.
+        
+        Returns:
+            Dict[str, Any]: Cache statistics
+        """
+        total_requests = self.cache_hit_count + self.cache_miss_count
+        hit_ratio = (self.cache_hit_count / total_requests) * 100 if total_requests > 0 else 0
+        
+        return {
+            "cache_size": len(self.cache),
+            "max_cache_size": self.max_cache_size,
+            "hit_count": self.cache_hit_count,
+            "miss_count": self.cache_miss_count,
+            "hit_ratio": hit_ratio,
+            "cache_keys": list(self.cache.keys())[:10]  # Show first 10 keys for debugging
+        }
+    
+    def clear_cache(self) -> None:
+        """Clear the TTS cache."""
+        self.cache.clear()
+        logger.info("TTS cache cleared")
 
     @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
     def get_service_info(self) -> Dict[str, Any]:
         # ...existing code...
```

## Best Practices with Cursor

### Effective Keyboard Shortcuts

1. Use `Alt+G` to quickly generate code
2. Use `Alt+X` to explain selected code
3. Use `Alt+E` to edit and improve selected code
4. Use `Alt+C` to start a chat about the current file

### Project Navigation

1. Use the file tree to explore the project structure
2. Use `Cmd/Ctrl + P` to quickly open files
3. Use `Cmd/Ctrl + Shift + F` to search across the entire project

### Improving AI Responses

1. Be specific about which component you're working with
2. Reference project-specific terminology from `.cursorrules`
3. Include context about the desired outcome
4. Break complex tasks into smaller, focused requests

### Working with the Codebase

1. Let Cursor help you understand unfamiliar parts
2. Use the AI to explain complex logic
3. Ask for diagrams when dealing with complex flows
4. Generate tests to validate your changes

By following these examples and best practices, you'll be able to work more effectively with the Morning Coffee codebase using Cursor's AI capabilities.
