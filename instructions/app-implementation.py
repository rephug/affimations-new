#!/usr/bin/env python
# Morning Coffee Main Application
# Handles Telnyx integration, call flow, and service coordination

import os
import time
import json
import uuid
import logging
import threading
import tempfile
from datetime import datetime
from typing import Optional, Dict, Any, List, Union
from pathlib import Path

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import redis
import telnyx
import assemblyai as aai
from tenacity import retry, stop_after_attempt, wait_exponential

# Import configuration
from config import Config

# Import modules
from modules.telnyx_handler import TelnyxHandler
from modules.assemblyai_handler import AssemblyAIHandler
from modules.llm_handler import LLMHandler
from modules.tts_client import SparkTTSClient
from modules.models import CallState, Message, UserSession

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join('logs', 'app.log'))
    ]
)
logger = logging.getLogger("morning-coffee")

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Load configuration
config = Config()

# Initialize Redis
redis_client = redis.Redis.from_url(config.REDIS_URL)

# Initialize service handlers
tts_client = SparkTTSClient(config.SPARK_TTS_URL)
assemblyai_handler = AssemblyAIHandler(config.ASSEMBLYAI_API_KEY)
llm_handler = LLMHandler(
    llm_type=config.LLM_TYPE,
    api_key=config.LLM_API_KEY,
    model=config.LLM_MODEL,
    endpoint=config.LLM_ENDPOINT
)
telnyx_handler = TelnyxHandler(
    api_key=config.TELNYX_API_KEY,
    phone_number=config.TELNYX_PHONE_NUMBER,
    messaging_profile_id=config.TELNYX_MESSAGING_PROFILE_ID,
    app_id=config.TELNYX_APP_ID
)

# Sample affirmations
AFFIRMATIONS = [
    "I am capable of achieving my goals and dreams.",
    "I embrace the day with positivity and purpose.",
    "I trust my intuition and make wise decisions.",
    "I am grateful for the abundance in my life.",
    "I radiate confidence, energy, and positivity.",
    "Today I choose joy and gratitude.",
    "I am worthy of success and happiness.",
    "I transform challenges into opportunities for growth.",
    "My potential is limitless, and I can achieve anything.",
    "I am becoming the best version of myself each day."
]

# Helper functions
def get_random_affirmation():
    """Return a random affirmation from the list."""
    import random
    return random.choice(AFFIRMATIONS)

def store_call_state(call_control_id: str, state: Dict[str, Any]):
    """Store call state in Redis."""
    key = f"call:{call_control_id}"
    redis_client.set(key, json.dumps(state), ex=3600)  # Expire after 1 hour

def get_call_state(call_control_id: str) -> Optional[Dict[str, Any]]:
    """Get call state from Redis."""
    key = f"call:{call_control_id}"
    data = redis_client.get(key)
    if data:
        return json.loads(data)
    return None

def update_call_state(call_control_id: str, updates: Dict[str, Any]):
    """Update specific fields in call state."""
    state = get_call_state(call_control_id)
    if state:
        state.update(updates)
        store_call_state(call_control_id, state)

def store_user_session(user_number: str, session: Dict[str, Any]):
    """Store user session in Redis."""
    key = f"user:{user_number}"
    redis_client.set(key, json.dumps(session), ex=86400)  # Expire after 24 hours

def get_user_session(user_number: str) -> Optional[Dict[str, Any]]:
    """Get user session from Redis."""
    key = f"user:{user_number}"
    data = redis_client.get(key)
    if data:
        return json.loads(data)
    return None

def update_user_session(user_number: str, updates: Dict[str, Any]):
    """Update specific fields in user session."""
    session = get_user_session(user_number)
    if session:
        session.update(updates)
        store_user_session(user_number, session)

def store_transcription_job(job_id: str, data: Dict[str, Any]):
    """Store transcription job information in Redis."""
    key = f"transcription:{job_id}"
    redis_client.set(key, json.dumps(data), ex=3600)  # Expire after 1 hour

def get_transcription_job(job_id: str) -> Optional[Dict[str, Any]]:
    """Get transcription job information from Redis."""
    key = f"transcription:{job_id}"
    data = redis_client.get(key)
    if data:
        return json.loads(data)
    return None

def get_all_pending_transcriptions() -> List[str]:
    """Get all pending transcription job IDs."""
    keys = redis_client.keys("transcription:*")
    return [key.decode("utf-8").split(":", 1)[1] for key in keys]

def generate_and_upload_tts(text, voice_id=None):
    """
    Generate speech using SparkTTS and upload to Telnyx Storage.
    
    Args:
        text (str): The text to convert to speech
        voice_id (str, optional): Voice ID to use
        
    Returns:
        str: URL of the uploaded audio file
    """
    try:
        # Generate speech with SparkTTS
        audio_data = tts_client.generate_speech(text, voice_id)
        
        if not audio_data:
            logger.error("Failed to generate speech")
            return None
            
        # Upload to Telnyx Storage
        file_id = f"tts_{uuid.uuid4()}.wav"
        upload_result = telnyx_handler.upload_to_storage(audio_data, file_id)
        
        if upload_result and "url" in upload_result:
            logger.info(f"Audio uploaded to Telnyx Storage: {upload_result['url']}")
            return upload_result["url"]
        else:
            logger.error(f"Failed to upload audio to Telnyx Storage: {upload_result}")
            return None
            
    except Exception as e:
        logger.error(f"Error generating and uploading TTS: {e}")
        return None

# Flask routes
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    services_status = {
        "app": "healthy",
        "tts": "unknown",
        "telnyx": "unknown",
        "assemblyai": "configured",
        "llm": "unknown",
        "redis": "unknown"
    }
    
    # Check TTS health
    try:
        tts_health = tts_client.health_check()
        services_status["tts"] = "healthy" if tts_health.get("status") == "healthy" else "unhealthy"
    except Exception:
        services_status["tts"] = "unhealthy"
    
    # Check Redis health
    try:
        if redis_client.ping():
            services_status["redis"] = "healthy"
        else:
            services_status["redis"] = "unhealthy"
    except Exception:
        services_status["redis"] = "unhealthy"
    
    # Check LLM health
    try:
        llm_health = llm_handler.health_check()
        services_status["llm"] = "healthy" if llm_health else "unhealthy"
    except Exception:
        services_status["llm"] = "unhealthy"
    
    # Determine overall status
    overall_status = "healthy"
    if services_status["tts"] == "unhealthy" or services_status["redis"] == "unhealthy":
        overall_status = "degraded"
    
    return jsonify({
        "status": overall_status,
        "services": services_status,
        "timestamp": datetime.now().isoformat()
    })

@app.route('/schedule_morning_coffee', methods=['POST'])
def schedule_morning_coffee():
    """Endpoint to schedule the morning coffee routine."""
    data = request.json
    to_number = data.get('phone_number')
    
    if not to_number:
        return {'status': 'error', 'message': 'Phone number is required'}, 400
    
    # Get or create user session
    user_session = get_user_session(to_number) or {}
    
    # Get a random affirmation
    affirmation = get_random_affirmation()
    
    # Update user session with the new affirmation
    user_session['affirmation'] = affirmation
    user_session['last_updated'] = datetime.now().isoformat()
    if 'conversation_history' not in user_session:
        user_session['conversation_history'] = []
    
    # Store the updated session
    store_user_session(to_number, user_session)
    
    # Send affirmation SMS
    sms_result = telnyx_handler.send_sms(
        to=to_number,
        text=f"Good morning! Your affirmation for today: {affirmation}"
    )
    
    if not sms_result:
        return {'status': 'error', 'message': 'Failed to send SMS'}, 500
    
    # Make the morning call
    call_result = telnyx_handler.make_call(
        to=to_number,
        webhook_url=f"{config.BASE_URL}/telnyx/call",
        user_number=to_number
    )
    
    if not call_result or 'call_control_id' not in call_result:
        return {'status': 'error', 'message': 'Failed to initiate call'}, 500
    
    # Store initial call state
    call_state = {
        'user_number': to_number,
        'stage': 'init',
        'affirmation': affirmation,
        'created_at': datetime.now().isoformat()
    }
    store_call_state(call_result['call_control_id'], call_state)
    
    return {
        'status': 'success',
        'message': 'Morning coffee routine initiated',
        'affirmation': affirmation,
        'call_control_id': call_result['call_control_id']
    }

@app.route('/telnyx/call', methods=['POST'])
def telnyx_call_webhook():
    """
    Webhook for handling Telnyx call control events.
    
    This handles the full call lifecycle including:
    - call.initiated: Initial call setup
    - call.answered: When the user answers
    - call.playback.ended: When audio playback finishes
    - call.recording.saved: When a recording is available
    - call.hangup: When the call ends
    """
    data = request.json
    
    # Extract event details
    event_type = data.get('data', {}).get('event_type')
    call_control_id = data.get('data', {}).get('payload', {}).get('call_control_id')
    
    logger.info(f"Received Telnyx event: {event_type} for call: {call_control_id}")
    
    # Handle different event types
    if event_type == 'call.initiated':
        # Call is being initiated, nothing to do yet
        return jsonify({"status": "ok"})
        
    elif event_type == 'call.answered':
        # User has answered the call, start the conversation
        call_state = get_call_state(call_control_id)
        if not call_state:
            logger.error(f"No call state found for call: {call_control_id}")
            return jsonify({"status": "error", "message": "Call state not found"}), 404
        
        user_number = call_state.get('user_number')
        user_session = get_user_session(user_number)
        if not user_session:
            logger.error(f"No user session found for user: {user_number}")
            return jsonify({"status": "error", "message": "User session not found"}), 404
        
        affirmation = user_session.get('affirmation')
        if not affirmation:
            logger.error(f"No affirmation found for user: {user_number}")
            return jsonify({"status": "error", "message": "Affirmation not found"}), 404
        
        # Generate greeting with SparkTTS and upload to Telnyx Storage
        greeting_text = f"Good morning! Welcome to your Morning Coffee. Today's affirmation is: {affirmation}"
        greeting_audio_url = generate_and_upload_tts(greeting_text)
        
        if greeting_audio_url:
            # Play the audio using Telnyx Call Control API
            play_result = telnyx_handler.play_audio(
                call_control_id=call_control_id,
                audio_url=greeting_audio_url,
                client_state="greeting_finished"
            )
            
            if play_result:
                # Update call state
                update_call_state(call_control_id, {
                    'stage': 'greeting',
                    'last_updated': datetime.now().isoformat()
                })
            else:
                # Failed to play audio, end the call
                telnyx_handler.hangup_call(call_control_id)
        else:
            # Failed to generate audio, end the call
            telnyx_handler.hangup_call(call_control_id)
        
        return jsonify({"status": "ok"})
        
    elif event_type == 'call.playback.ended':
        # An audio playback has finished, determine next action
        call_state = get_call_state(call_control_id)
        if not call_state:
            logger.error(f"No call state found for call: {call_control_id}")
            return jsonify({"status": "error", "message": "Call state not found"}), 404
        
        client_state = data.get('data', {}).get('payload', {}).get('client_state', '')
        
        if client_state == 'greeting_finished':
            # Greeting audio finished, ask user to repeat affirmation
            instruction_text = "Please repeat the affirmation out loud."
            instruction_audio_url = generate_and_upload_tts(instruction_text)
            
            if instruction_audio_url:
                # Play the instruction audio
                play_result = telnyx_handler.play_audio(
                    call_control_id=call_control_id,
                    audio_url=instruction_audio_url,
                    client_state="instruction_finished"
                )
                
                if not play_result:
                    # Failed to play audio, try to move to next stage
                    record_result = telnyx_handler.start_recording(
                        call_control_id=call_control_id,
                        client_state="record_affirmation"
                    )
                    
                    if record_result:
                        update_call_state(call_control_id, {
                            'stage': 'recording_affirmation',
                            'last_updated': datetime.now().isoformat()
                        })
                    else:
                        # Failed to start recording, end the call
                        telnyx_handler.hangup_call(call_control_id)
            else:
                # Failed to generate audio, move to next stage
                record_result = telnyx_handler.start_recording(
                    call_control_id=call_control_id,
                    client_state="record_affirmation"
                )
                
                if record_result:
                    update_call_state(call_control_id, {
                        'stage': 'recording_affirmation',
                        'last_updated': datetime.now().isoformat()
                    })
                else:
                    # Failed to start recording, end the call
                    telnyx_handler.hangup_call(call_control_id)
        
        elif client_state == 'instruction_finished':
            # Instruction finished, start recording
            record_result = telnyx_handler.start_recording(
                call_control_id=call_control_id,
                client_state="record_affirmation"
            )
            
            if record_result:
                update_call_state(call_control_id, {
                    'stage': 'recording_affirmation',
                    'last_updated': datetime.now().isoformat()
                })
            else:
                # Failed to start recording, end the call
                telnyx_handler.hangup_call(call_control_id)
        
        elif client_state == 'response_finished':
            # AI response finished, ask followup question
            followup_text = "Is there anything else on your mind this morning?"
            followup_audio_url = generate_and_upload_tts(followup_text)
            
            if followup_audio_url:
                # Play the followup question
                play_result = telnyx_handler.play_audio(
                    call_control_id=call_control_id,
                    audio_url=followup_audio_url,
                    client_state="followup_finished"
                )
                
                if not play_result:
                    # Failed to play audio, start recording anyway
                    record_result = telnyx_handler.start_recording(
                        call_control_id=call_control_id,
                        client_state="record_chat"
                    )
                    
                    if record_result:
                        update_call_state(call_control_id, {
                            'stage': 'recording_chat',
                            'last_updated': datetime.now().isoformat()
                        })
                    else:
                        # Failed to start recording, end the call
                        telnyx_handler.hangup_call(call_control_id)
            else:
                # Failed to generate audio, start recording anyway
                record_result = telnyx_handler.start_recording(
                    call_control_id=call_control_id,
                    client_state="record_chat"
                )
                
                if record_result:
                    update_call_state(call_control_id, {
                        'stage': 'recording_chat',
                        'last_updated': datetime.now().isoformat()
                    })
                else:
                    # Failed to start recording, end the call
                    telnyx_handler.hangup_call(call_control_id)
        
        elif client_state == 'followup_finished' or client_state == 'reinforcement_finished':
            # Followup/reinforcement question finished, start recording
            record_result = telnyx_handler.start_recording(
                call_control_id=call_control_id,
                client_state="record_chat"
            )
            
            if record_result:
                update_call_state(call_control_id, {
                    'stage': 'recording_chat',
                    'last_updated': datetime.now().isoformat()
                })
            else:
                # Failed to start recording, end the call
                telnyx_handler.hangup_call(call_control_id)
        
        elif client_state == 'goodbye_finished':
            # Goodbye message finished, hang up
            telnyx_handler.hangup_call(call_control_id)
        
        return jsonify({"status": "ok"})
        
    elif event_type == 'call.recording.saved':
        # A recording is available, process it
        call_state = get_call_state(call_control_id)
        if not call_state:
            logger.error(f"No call state found for call: {call_control_id}")
            return jsonify({"status": "error", "message": "Call state not found"}), 404
        
        client_state = data.get('data', {}).get('payload', {}).get('client_state', '')
        recording_url = data.get('data', {}).get('payload', {}).get('recording_urls', {}).get('wav')
        
        # Stop recording to ensure we don't get multiple recordings
        telnyx_handler.stop_recording(call_control_id)
        
        if recording_url:
            # Start AssemblyAI transcription
            transcription_result = assemblyai_handler.submit_transcription(recording_url)
            
            if transcription_result and 'job_id' in transcription_result:
                job_id = transcription_result['job_id']
                
                # Store information about this transcription job
                transcription_data = {
                    'call_control_id': call_control_id,
                    'client_state': client_state,
                    'start_time': datetime.now().timestamp(),
                    'status': 'pending'
                }
                store_transcription_job(job_id, transcription_data)
                
                logger.info(f"AssemblyAI transcription job started: {job_id}")
                
                # Update call state
                update_call_state(call_control_id, {
                    'pending_transcription': job_id,
                    'last_updated': datetime.now().isoformat()
                })
                
                # Trigger background check for transcription (in production, use a task queue)
                threading.Thread(target=check_transcription_periodically, args=(job_id,)).start()
            else:
                # Failed to start transcription, try to continue anyway
                if client_state == 'record_affirmation':
                    # Just move to the chat phase
                    reinforce_text = "Let's move on to our morning chat. How are you feeling today?"
                    reinforce_audio_url = generate_and_upload_tts(reinforce_text)
                    
                    if reinforce_audio_url:
                        play_result = telnyx_handler.play_audio(
                            call_control_id=call_control_id,
                            audio_url=reinforce_audio_url,
                            client_state="reinforcement_finished"
                        )
                        
                        if not play_result:
                            telnyx_handler.hangup_call(call_control_id)
                    else:
                        telnyx_handler.hangup_call(call_control_id)
                else:
                    # End the call
                    telnyx_handler.hangup_call(call_control_id)
        else:
            # No recording URL, end the call
            telnyx_handler.hangup_call(call_control_id)
        
        return jsonify({"status": "ok"})
        
    elif event_type == 'call.hangup':
        # Call has ended, clean up
        # We could delete the call state here, but keeping it for logging purposes
        # Just mark it as ended
        call_state = get_call_state(call_control_id)
        if call_state:
            update_call_state(call_control_id, {
                'stage': 'ended',
                'end_time': datetime.now().isoformat(),
                'last_updated': datetime.now().isoformat()
            })
            
        return jsonify({"status": "ok"})
    
    # For any other event types
    return jsonify({"status": "ok"})

@app.route('/check_transcriptions', methods=['GET'])
def check_transcriptions_endpoint():
    """Endpoint to manually trigger checking of pending transcriptions."""
    job_ids = get_all_pending_transcriptions()
    results = []
    
    for job_id in job_ids:
        job_info = get_transcription_job(job_id)
        if job_info and job_info.get('status') == 'pending':
            # Check the transcription status
            transcription_status = assemblyai_handler.check_transcription_status(job_id)
            results.append({
                "job_id": job_id,
                "status": transcription_status.get('status'),
                "call_control_id": job_info.get('call_control_id')
            })
            
            # If completed, process the result
            if transcription_status.get('status') == 'completed':
                transcribed_text = transcription_status.get('text')
                process_transcription_result(job_id, job_info, transcribed_text)
    
    return jsonify({
        "status": "success",
        "message": "Checked pending transcriptions",
        "pending_count": len(job_ids),
        "results": results
    })

def check_transcription_periodically(job_id, max_attempts=12, delay_seconds=5):
    """
    Check a transcription job periodically until it completes or fails.
    
    Args:
        job_id (str): The transcription job ID
        max_attempts (int): Maximum number of attempts
        delay_seconds (int): Delay between attempts
    """
    for attempt in range(max_attempts):
        # Get the job info
        job_info = get_transcription_job(job_id)
        if not job_info:
            logger.error(f"No job info found for transcription: {job_id}")
            return
        
        # Check the status
        transcription_status = assemblyai_handler.check_transcription_status(job_id)
        status = transcription_status.get('status')
        
        if status == 'completed':
            # Process the completed transcription
            transcribed_text = transcription_status.get('text')
            process_transcription_result(job_id, job_info, transcribed_text)
            return
        elif status == 'error':
            # Handle error
            logger.error(f"Transcription error for job {job_id}: {transcription_status.get('error')}")
            call_control_id = job_info.get('call_control_id')
            client_state = job_info.get('client_state')
            
            if call_control_id and client_state:
                handle_transcription_failure(call_control_id, client_state)
            return
        
        # Wait before checking again
        time.sleep(delay_seconds)
    
    # If we reach here, transcription took too long
    logger.warning(f"Transcription timeout for job {job_id} after {max_attempts} attempts")
    job_info = get_transcription_job(job_id)
    if job_info:
        call_control_id = job_info.get('call_control_id')
        client_state = job_info.get('client_state')
        
        if call_control_id and client_state:
            handle_transcription_failure(call_control_id, client_state)

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
            # User has repeated the affirmation, provide positive reinforcement
            reinforce_text = "Wonderful! Speaking affirmations out loud makes them more powerful. Now, let's have a brief morning chat. How are you feeling today?"
            reinforce_audio_url = generate_and_upload_tts(reinforce_text)
            
            if reinforce_audio_url:
                # Play the reinforcement audio
                play_result = telnyx_handler.play_audio(
                    call_control_id=call_control_id,
                    audio_url=reinforce_audio_url,
                    client_state="reinforcement_finished"
                )
                
                if play_result:
                    # Update call stage
                    update_call_state(call_control_id, {
                        'stage': 'chat_intro',
                        'last_updated': datetime.now().isoformat()
                    })
                else:
                    # Failed to play audio, start recording for chat anyway
                    record_result = telnyx_handler.start_recording(
                        call_control_id=call_control_id,
                        client_state="record_chat"
                    )
                    
                    if record_result:
                        update_call_state(call_control_id, {
                            'stage': 'recording_chat',
                            'last_updated': datetime.now().isoformat()
                        })
                    else:
                        # Failed to start recording, end the call
                        telnyx_handler.hangup_call(call_control_id)
            else:
                # Failed to generate audio, start recording for chat anyway
                record_result = telnyx_handler.start_recording(
                    call_control_id=call_control_id,
                    client_state="record_chat"
                )
                
                if record_result:
                    update_call_state(call_control_id, {
                        'stage': 'recording_chat',
                        'last_updated': datetime.now().isoformat()
                    })
                else:
                    # Failed to start recording, end the call
                    telnyx_handler.hangup_call(call_control_id)
        
        elif client_state == 'record_chat':
            if transcribed_text:
                logger.info(f"Transcribed user speech: {transcribed_text}")
                
                # Get user session
                user_session = get_user_session(user_number)
                if not user_session:
                    logger.error(f"No user session found for user: {user_number}")
                    telnyx_handler.hangup_call(call_control_id)
                    return
                
                # Add user message to conversation history
                conversation_history = user_session.get('conversation_history', [])
                conversation_history.append({
                    "role": "user",
                    "content": transcribed_text,
                    "timestamp": datetime.now().isoformat()
                })
                
                # Get AI response based on user's input
                ai_response = llm_handler.get_response(
                    user_input=transcribed_text,
                    conversation_history=conversation_history
                )
                
                if ai_response:
                    # Add AI response to conversation history
                    conversation_history.append({
                        "role": "assistant",
                        "content": ai_response,
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    # Update user session
                    user_session['conversation_history'] = conversation_history
                    user_session['last_updated'] = datetime.now().isoformat()
                    store_user_session(user_number, user_session)
                    
                    # Generate speech for AI response
                    response_audio_url = generate_and_upload_tts(ai_response)
                    
                    if response_audio_url:
                        # Play the AI response
                        play_result = telnyx_handler.play_audio(
                            call_control_id=call_control_id,
                            audio_url=response_audio_url,
                            client_state="response_finished"
                        )
                        
                        if play_result:
                            # Update call stage
                            update_call_state(call_control_id, {
                                'stage': 'ai_response',
                                'last_updated': datetime.now().isoformat()
                            })
                        else:
                            # Failed to play audio, end call
                            goodbye_text = "I'll check in with you tomorrow. Have a great day!"
                            goodbye_audio_url = generate_and_upload_tts(goodbye_text)
                            
                            if goodbye_audio_url:
                                telnyx_handler.play_audio(
                                    call_control_id=call_control_id,
                                    audio_url=goodbye_audio_url,
                                    client_state="goodbye_finished"
                                )
                            else:
                                telnyx_handler.hangup_call(call_control_id)
                    else:
                        # Failed to generate audio, end call
                        telnyx_handler.hangup_call(call_control_id)
                else:
                    # Failed to get AI response, end call
                    error_text = "I'm having trouble understanding. Let's continue this conversation another time. Have a great day!"
                    error_audio_url = generate_and_upload_tts(error_text)
                    
                    if error_audio_url:
                        telnyx_handler.play_audio(
                            call_control_id=call_control_id,
                            audio_url=error_audio_url,
                            client_state="goodbye_finished"
                        )
                    else:
                        telnyx_handler.hangup_call(call_control_id)
            else:
                # Transcription failed, try again
                error_text = "I didn't catch that. Is there something specific you'd like to discuss this morning?"
                error_audio_url = generate_and_upload_tts(error_text)
                
                if error_audio_url:
                    play_result = telnyx_handler.play_audio(
                        call_control_id=call_control_id,
                        audio_url=error_audio_url,
                        client_state="error_finished"
                    )
                    
                    if not play_result:
                        # Start recording again anyway
                        record_result = telnyx_handler.start_recording(
                            call_control_id=call_control_id,
                            client_state="record_chat"
                        )
                        
                        if record_result:
                            update_call_state(call_control_id, {
                                'stage': 'recording_chat',
                                'last_updated': datetime.now().isoformat()
                            })
                        else:
                            # Failed to start recording, end the call
                            telnyx_handler.hangup_call(call_control_id)
                else:
                    # Start recording again anyway
                    record_result = telnyx_handler.start_recording(
                        call_control_id=call_control_id,
                        client_state="record_chat"
                    )
                    
                    if record_result:
                        update_call_state(call_control_id, {
                            'stage': 'recording_chat',
                            'last_updated': datetime.now().isoformat()
                        })
                    else:
                        # Failed to start recording, end the call
                        telnyx_handler.hangup_call(call_control_id)
    except Exception as e:
        logger.error(f"Error processing transcription result: {e}")
        # Try to handle the failure gracefully
        call_control_id = job_info.get('call_control_id')
        client_state = job_info.get('client_state')
        
        if call_control_id and client_state:
            handle_transcription_failure(call_control_id, client_state)

def handle_transcription_failure(call_control_id, client_state):
    """
    Handle a failed transcription.
    
    Args:
        call_control_id (str): The call control ID
        client_state (str): The client state
    """
    try:
        # Get call state
        call_state = get_call_state(call_control_id)
        if not call_state:
            logger.error(f"No call state found for call: {call_control_id}")
            return
        
        if client_state == 'record_affirmation':
            # Move to chat phase
            reinforce_text = "Let's move on to our morning chat. How are you feeling today?"
            reinforce_audio_url = generate_and_upload_tts(reinforce_text)
            
            if reinforce_audio_url:
                telnyx_handler.play_audio(
                    call_control_id=call_control_id,
                    audio_url=reinforce_audio_url,
                    client_state="reinforcement_finished"
                )
            else:
                telnyx_handler.hangup_call(call_control_id)
        else:
            # End the call
            goodbye_text = "I'm having trouble with our connection. Let's continue this conversation another time. Have a great day!"
            goodbye_audio_url = generate_and_upload_tts(goodbye_text)
            
            if goodbye_audio_url:
                telnyx_handler.play_audio(
                    call_control_id=call_control_id,
                    audio_url=goodbye_audio_url,
                    client_state="goodbye_finished"
                )
            else:
                telnyx_handler.hangup_call(call_control_id)
    except Exception as e:
        logger.error(f"Error handling transcription failure: {e}")
        # Just try to hang up the call
        try:
            telnyx_handler.hangup_call(call_control_id)
        except Exception:
            pass

if __name__ == '__main__':
    # Get port from environment variable or use default
    port = int(os.environ.get("PORT", 5000))
    
    # Start the Flask app
    app.run(host='0.0.0.0', port=port, debug=False)
