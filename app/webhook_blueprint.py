#!/usr/bin/env python
# Webhook Blueprint for Morning Coffee application

import logging
import time
import requests
from typing import Dict, Any, Optional

from flask import Blueprint, request, jsonify, current_app

# Additional imports for streaming
from .modules.tts.telnyx_streaming import TelnyxStreamingManager, AudioFormat
from .modules.tts.call_metrics import CallQualityMonitor

# Configure logging
logger = logging.getLogger('webhooks')

# Create blueprint
webhooks = Blueprint('webhooks', __name__, url_prefix='/webhooks')

@webhooks.route('/telnyx/call', methods=['POST'])
def telnyx_call_webhook():
    """Handle Telnyx call webhooks."""
    # Extract event data
    data = request.json
    event_type = data.get('data', {}).get('event_type')
    call_control_id = data.get('data', {}).get('payload', {}).get('call_control_id')
    
    logger.info(f"Received Telnyx webhook: {event_type} for call {call_control_id}")
    
    if not call_control_id:
        return jsonify({"error": "Missing call_control_id"}), 400
    
    # Get service instances from application config
    redis_store = current_app.config['REDIS_STORE']
    tts_service = current_app.config['TTS_SERVICE']  # Replace TTS_CLIENT with TTS_SERVICE
    telnyx_handler = current_app.config['TELNYX_HANDLER']
    assemblyai_handler = current_app.config['ASSEMBLYAI_HANDLER']
    llm_handler = current_app.config['LLM_HANDLER']
    
    # Initialize TTS streaming manager and monitoring if not already in config
    tts_streaming_manager = current_app.config.get('TTS_STREAMING_MANAGER')
    if not tts_streaming_manager and telnyx_handler:
        from .modules.tts.telnyx_streaming import TelnyxStreamingManager
        tts_streaming_manager = TelnyxStreamingManager(
            api_key=telnyx_handler.api_key,
            default_sample_rate=8000,
            default_sample_width=2,
            default_channels=1
        )
        current_app.config['TTS_STREAMING_MANAGER'] = tts_streaming_manager
    
    # Initialize call quality monitor if not already in config
    call_quality_monitor = current_app.config.get('CALL_QUALITY_MONITOR')
    if not call_quality_monitor and tts_service and tts_streaming_manager:
        from .modules.tts.call_metrics import CallQualityMonitor
        call_quality_monitor = CallQualityMonitor(tts_service, tts_streaming_manager)
        current_app.config['CALL_QUALITY_MONITOR'] = call_quality_monitor
    
    # Check required services
    if not telnyx_handler:
        logger.error("Telnyx handler not available")
        return jsonify({"error": "Telnyx integration not available"}), 503
        
    if not redis_store:
        logger.error("Redis store not available")
        return jsonify({"error": "Storage not available"}), 503
    
    if not tts_service:
        logger.error("TTS service not available")
        return jsonify({"error": "TTS service not available"}), 503
    
    # Get the call session
    call_session = redis_store.get_call_by_control_id(call_control_id)
    if not call_session:
        logger.warning(f"Call session not found for control ID {call_control_id}")
        return jsonify({"error": "Call session not found"}), 404
    
    # Handle different event types
    if event_type == 'call.initiated':
        # Call was initiated
        logger.info(f"Call initiated: {call_control_id}")
        call_session.update_state('initiated')
        redis_store.update_call_session(call_session)
        
    elif event_type == 'call.answered':
        # Call was answered, start the call flow
        logger.info(f"Call answered: {call_control_id}")
        call_session.update_state('in_progress')
        redis_store.update_call_session(call_session)
        
        # Get user information
        user = redis_store.get_user_by_id(call_session.user_id)
        if not user:
            logger.error(f"User not found for call session {call_session.id}")
            return jsonify({"error": "User not found"}), 404
            
        # Generate greeting message
        greeting = f"Hello {user.name}, this is your morning coffee. Today's affirmation is: {call_session.affirmation}"
        
        # Start call quality monitoring
        if call_quality_monitor:
            call_quality_monitor.start_call_monitoring(call_session.id)
        
        try:
            # Use streaming for better latency
            if tts_streaming_manager:
                # Create a streaming session
                session_id = tts_streaming_manager.create_streaming_session(
                    call_control_id=call_control_id,
                    client_state="greeting"
                )
                
                if not session_id:
                    raise Exception("Failed to create streaming session")
                
                # Store session ID in call session
                call_session.stream_id = session_id
                redis_store.update_call_session(call_session)
                
                # Generate audio using the dialog optimized method for better initial latency
                if hasattr(tts_service, 'generate_dialog_speech_stream'):
                    # Get streaming generator from TTS service with dialog optimization
                    audio_generator = tts_service.generate_dialog_speech_stream(
                        text=greeting, 
                        voice_id="default_female"
                    )
                else:
                    # Fall back to regular streaming
                    audio_generator = tts_service.generate_speech_stream(
                        text=greeting, 
                        voice_id="default_female"
                    )
                
                # Start call quality monitoring for the stream
                if call_quality_monitor:
                    call_quality_monitor.start_streaming_session(call_session.id, session_id)
                
                # Process audio chunks
                for audio_chunk in audio_generator:
                    # Get the WAV duration
                    # Simplified calculation - 16-bit audio at 8000Hz is 16000 bytes per second
                    duration_ms = (len(audio_chunk) / 16000) * 1000
                    
                    # Add to streaming session
                    added = tts_streaming_manager.add_wav_audio(
                        call_control_id=call_control_id,
                        wav_data=audio_chunk,
                        metadata={"type": "greeting", "duration_ms": duration_ms}
                    )
                    
                    if not added:
                        logger.warning(f"Failed to add audio chunk to streaming session for call {call_control_id}")
                
                # Start streaming
                streaming_started = tts_streaming_manager.start_streaming(call_control_id)
                
                if not streaming_started:
                    raise Exception("Failed to start streaming")
                
                return jsonify({"status": "streaming started", "stream_id": session_id})
            else:
                # Fall back to non-streaming approach
                logger.warning("Streaming manager not available, falling back to batch audio generation")
                
                # Traditional audio generation (existing code)
                audio_bytes = tts_service.generate_speech(text=greeting, voice_id="default_female")
                if not audio_bytes:
                    logger.error(f"Failed to generate speech for greeting")
                    return jsonify({"error": "TTS failed"}), 500
                    
                # Upload audio to Telnyx storage
                audio_upload = telnyx_handler.upload_to_storage(file_data=audio_bytes)
                if not audio_upload:
                    logger.error(f"Failed to upload audio to Telnyx storage")
                    return jsonify({"error": "Audio upload failed"}), 500
                    
                # Play the audio in the call
                success = telnyx_handler.play_audio(
                    call_control_id=call_control_id,
                    audio_url=audio_upload['url'],
                    client_state='greeting'
                )
                
                if not success:
                    logger.error(f"Failed to play audio in call {call_control_id}")
                    return jsonify({"error": "Failed to play audio"}), 500
                    
                return jsonify({"status": "batch audio processing completed"})
                
        except Exception as e:
            # Error handling for streaming failures
            logger.error(f"Error in streaming TTS for call {call_control_id}: {str(e)}")
            
            # Record error in call metrics
            if call_quality_monitor:
                call_quality_monitor.record_error(call_session.id, "streaming_error", str(e))
            
            # Fall back to non-streaming approach
            try:
                # Traditional audio generation (existing code)
                audio_bytes = tts_service.generate_speech(text=greeting, voice_id="default_female")
                if not audio_bytes:
                    return jsonify({"error": "TTS failed"}), 500
                    
                # Upload audio to Telnyx storage
                audio_upload = telnyx_handler.upload_to_storage(file_data=audio_bytes)
                if not audio_upload:
                    return jsonify({"error": "Audio upload failed"}), 500
                    
                # Play the audio in the call
                success = telnyx_handler.play_audio(
                    call_control_id=call_control_id,
                    audio_url=audio_upload['url'],
                    client_state='greeting'
                )
                
                if not success:
                    return jsonify({"error": "Failed to play audio"}), 500
                
                return jsonify({"status": "fallback audio processing completed"})
            except Exception as fallback_error:
                logger.error(f"Fallback TTS also failed for call {call_control_id}: {str(fallback_error)}")
                return jsonify({"error": "All TTS methods failed"}), 500

    elif event_type == 'call.playback.ended':
        # Audio playback ended
        client_state = data.get('data', {}).get('payload', {}).get('client_state')
        logger.info(f"Playback ended for call {call_control_id} with state {client_state}")
        
        if client_state == 'greeting':
            # After greeting, ask user to repeat the affirmation
            prompt = "Now, please repeat the affirmation."
            
            # Convert to speech using TTS
            audio_bytes = tts_service.generate_speech(text=prompt, voice_id="default_female")
            if not audio_bytes:
                logger.error(f"Failed to generate speech for prompt")
                return jsonify({"error": "TTS failed"}), 500
                
            # Upload audio to Telnyx storage
            audio_upload = telnyx_handler.upload_to_storage(file_data=audio_bytes)
            if not audio_upload:
                logger.error(f"Failed to upload audio to Telnyx storage")
                return jsonify({"error": "Audio upload failed"}), 500
                
            # Play the prompt
            success = telnyx_handler.play_audio(
                call_control_id=call_control_id,
                audio_url=audio_upload['url'],
                client_state='repeat_prompt'
            )
            
        elif client_state == 'repeat_prompt':
            # After prompting for repetition, start recording
            success = telnyx_handler.start_recording(
                call_control_id=call_control_id,
                client_state='recording_affirmation'
            )
            if success:
                call_session.update_state('recording')
                redis_store.update_call_session(call_session)
                
        elif client_state == 'chat_prompt':
            # After chat prompt, start recording for chat
            success = telnyx_handler.start_recording(
                call_control_id=call_control_id,
                client_state='recording_chat'
            )
            if success:
                call_session.update_state('recording')
                redis_store.update_call_session(call_session)
                
        elif client_state == 'ai_response':
            # After AI response, ask if user wants to continue chatting
            prompt = "Would you like to continue our conversation? Just say yes or no."
            
            # Convert to speech using TTS
            audio_bytes = tts_service.generate_speech(text=prompt, voice_id="default_female")
            if not audio_bytes:
                logger.error(f"Failed to generate speech for chat prompt")
                return jsonify({"error": "TTS failed"}), 500
                
            # Upload audio to Telnyx storage
            audio_upload = telnyx_handler.upload_to_storage(file_data=audio_bytes)
            if not audio_upload:
                logger.error(f"Failed to upload audio to Telnyx storage")
                return jsonify({"error": "Audio upload failed"}), 500
                
            # Play the prompt
            success = telnyx_handler.play_audio(
                call_control_id=call_control_id,
                audio_url=audio_upload['url'],
                client_state='chat_prompt'
            )
            
        elif client_state == 'goodbye':
            # After goodbye, hang up the call
            success = telnyx_handler.hangup_call(call_control_id=call_control_id)
            if success:
                call_session.update_state('completed')
                redis_store.update_call_session(call_session)
    
    elif event_type == 'call.recording.saved':
        # Recording was saved
        recording_url = data.get('data', {}).get('payload', {}).get('recording_urls', {}).get('wav')
        recording_id = data.get('data', {}).get('payload', {}).get('recording_id')
        client_state = data.get('data', {}).get('payload', {}).get('client_state')
        
        logger.info(f"Recording saved for call {call_control_id}: {recording_id}")
        
        if not recording_url or not recording_id:
            logger.error(f"Missing recording details in webhook")
            return jsonify({"error": "Missing recording details"}), 400
        
        # Check if AssemblyAI handler is available
        if not assemblyai_handler:
            logger.error(f"AssemblyAI handler not available")
            return jsonify({"error": "Speech recognition not available"}), 503
            
        # Add recording to call session
        call_session.add_recording(recording_url=recording_url, recording_id=recording_id)
        call_session.update_state('processing')
        redis_store.update_call_session(call_session)
        
        # Download the recording for transcription
        try:
            recording_response = requests.get(recording_url)
            recording_response.raise_for_status()
            recording_data = recording_response.content
            
            # Submit for transcription
            transcription_id = assemblyai_handler.submit_transcription(recording_data)
            if not transcription_id:
                logger.error(f"Failed to submit transcription for recording {recording_id}")
                return jsonify({"error": "Transcription submission failed"}), 500
                
            # Poll for transcription result (in a real app, this would be async)
            max_retries = 10
            for i in range(max_retries):
                status, text = assemblyai_handler.check_transcription_status(transcription_id)
                
                if status == "completed" and text:
                    # Transcription completed
                    call_session.add_transcription(text=text, transcription_id=transcription_id)
                    
                    if client_state == 'recording_affirmation':
                        # User repeated the affirmation, now move to chat
                        call_session.add_conversation_entry(role="user", content=text)
                        
                        # Check if LLM handler is available
                        if not llm_handler:
                            logger.error(f"LLM handler not available")
                            return jsonify({"error": "Conversation AI not available"}), 503
                        
                        # Generate a response based on their affirmation repetition
                        prompt = [
                            {"role": "system", "content": "You are a supportive AI assistant. The user has just repeated their daily affirmation. Acknowledge this positively and ask how they're feeling today. Keep your response warm but concise (2-3 sentences)."},
                            {"role": "user", "content": text}
                        ]
                        
                        ai_response = llm_handler.get_response(prompt, temperature=0.7)
                        call_session.add_conversation_entry(role="assistant", content=ai_response)
                        
                        # Convert AI response to speech using streaming
                        if tts_streaming_manager:
                            try:
                                # Create a streaming session for the AI response
                                session_id = tts_streaming_manager.create_streaming_session(
                                    call_control_id=call_control_id,
                                    client_state="ai_response"
                                )
                                
                                # Generate audio stream
                                audio_generator = tts_service.generate_speech_stream(
                                    text=ai_response, 
                                    voice_id="default_female"
                                )
                                
                                # Track streaming session
                                if call_quality_monitor:
                                    call_quality_monitor.start_streaming_session(call_session.id, session_id)
                                
                                # Process audio chunks
                                for audio_chunk in audio_generator:
                                    # Add to streaming session
                                    tts_streaming_manager.add_wav_audio(
                                        call_control_id=call_control_id,
                                        wav_data=audio_chunk
                                    )
                                
                                # Start streaming
                                tts_streaming_manager.start_streaming(call_control_id)
                                
                                redis_store.update_call_session(call_session)
                                return jsonify({"status": "ai response streaming started"})
                            except Exception as e:
                                logger.error(f"Error in streaming AI response: {str(e)}")
                                # Fall back to non-streaming approach
                        
                        # Fall back to traditional approach if streaming fails or is not available
                        audio_bytes = tts_service.generate_speech(text=ai_response, voice_id="default_female")
                        if not audio_bytes:
                            logger.error(f"Failed to generate speech for AI response")
                            return jsonify({"error": "TTS failed"}), 500
                            
                            # Play the AI response
                            success = telnyx_handler.play_audio(
                                call_control_id=call_control_id,
                                audio_url=audio_upload['url'],
                                client_state='ai_response'
                            )
                    
                    elif client_state == 'recording_chat':
                        # User is chatting, generate a response
                        call_session.add_conversation_entry(role="user", content=text)
                        
                        # Check if the user wants to end the conversation
                        if text.lower() in ["no", "no thanks", "goodbye", "bye", "end", "stop"]:
                            # User wants to end the conversation
                            goodbye = "Thank you for your time today. Remember your affirmation and have a wonderful day!"
                            
                            # Convert to speech using TTS
                            audio_bytes = tts_service.generate_speech(text=goodbye, voice_id="default_female")
                            if not audio_bytes:
                                logger.error(f"Failed to generate speech for goodbye")
                                return jsonify({"error": "TTS failed"}), 500
                                
                            # Upload audio to Telnyx storage
                            audio_upload = telnyx_handler.upload_to_storage(file_data=audio_bytes)
                            if not audio_upload:
                                logger.error(f"Failed to upload audio to Telnyx storage")
                                return jsonify({"error": "Audio upload failed"}), 500
                                
                            # Play the goodbye message
                            success = telnyx_handler.play_audio(
                                call_control_id=call_control_id,
                                audio_url=audio_upload['url'],
                                client_state='goodbye'
                            )
                            
                        else:
                            # Check if LLM handler is available
                            if not llm_handler:
                                logger.error(f"LLM handler not available")
                                return jsonify({"error": "Conversation AI not available"}), 503
                                
                            # Generate a response with the LLM
                            history = call_session.conversation_history
                            
                            # Format conversation history for the LLM
                            formatted_history = [
                                {"role": entry["role"], "content": entry["content"]}
                                for entry in history
                            ]
                            
                            # Add a system prompt at the beginning
                            if not formatted_history or formatted_history[0]["role"] != "system":
                                formatted_history.insert(0, {
                                    "role": "system", 
                                    "content": "You are a supportive AI assistant having a short voice conversation. Keep your responses concise (1-3 sentences) and supportive."
                                })
                            
                            # Get response from LLM
                            ai_response = llm_handler.get_response(formatted_history, temperature=0.7)
                            call_session.add_conversation_entry(role="assistant", content=ai_response)
                            
                            # Convert AI response to speech using streaming
                            if tts_streaming_manager:
                                try:
                                    # Create a streaming session for the AI response
                                    session_id = tts_streaming_manager.create_streaming_session(
                                        call_control_id=call_control_id,
                                        client_state="ai_response"
                                    )
                                    
                                    # Generate audio stream
                                    audio_generator = tts_service.generate_speech_stream(
                                        text=ai_response, 
                                        voice_id="default_female"
                                    )
                                    
                                    # Track streaming session
                                    if call_quality_monitor:
                                        call_quality_monitor.start_streaming_session(call_session.id, session_id)
                                    
                                    # Process audio chunks
                                    for audio_chunk in audio_generator:
                                        # Add to streaming session
                                        tts_streaming_manager.add_wav_audio(
                                            call_control_id=call_control_id,
                                            wav_data=audio_chunk
                                        )
                                    
                                    # Start streaming
                                    tts_streaming_manager.start_streaming(call_control_id)
                                    
                                    redis_store.update_call_session(call_session)
                                    return jsonify({"status": "ai response streaming started"})
                                except Exception as e:
                                    logger.error(f"Error in streaming AI response: {str(e)}")
                                    # Fall back to non-streaming approach
                        
                        # Fall back to traditional approach if streaming fails or is not available
                        audio_bytes = tts_service.generate_speech(text=ai_response, voice_id="default_female")
                        if not audio_bytes:
                            logger.error(f"Failed to generate speech for AI response")
                            return jsonify({"error": "TTS failed"}), 500
                            
                        # Upload audio to Telnyx storage
                        audio_upload = telnyx_handler.upload_to_storage(file_data=audio_bytes)
                        if not audio_upload:
                            logger.error(f"Failed to upload audio to Telnyx storage")
                            return jsonify({"error": "Audio upload failed"}), 500
                            
                            # Play the AI response
                            success = telnyx_handler.play_audio(
                                call_control_id=call_control_id,
                                audio_url=audio_upload['url'],
                                client_state='ai_response'
                            )
                    
                    # Save updated call session
                    redis_store.update_call_session(call_session)
                    break
                    
                elif status == "error":
                    # Transcription failed
                    logger.error(f"Transcription failed for recording {recording_id}")
                    return jsonify({"error": "Transcription failed"}), 500
                    
                # Wait before checking again
                time.sleep(2)
            
        except Exception as e:
            logger.error(f"Error processing recording: {str(e)}")
            return jsonify({"error": str(e)}), 500
            
    elif event_type == 'call.hangup':
        # Call ended, clean up resources
        logger.info(f"Call ended: {call_control_id}")
        call_session.update_state('ended')
        redis_store.update_call_session(call_session)
        
        # Clean up any active streaming sessions
        if tts_streaming_manager:
            tts_streaming_manager.terminate_streaming(call_control_id)
        
        # End call monitoring
        if call_quality_monitor:
            call_quality_monitor.end_call_monitoring(call_session.id)
            
            # Log call metrics for analysis
            metrics = call_quality_monitor.get_call_metrics(call_session.id)
            if metrics:
                logger.info(f"Call metrics for {call_session.id}: "
                           f"duration={metrics.get('total_time', 0):.2f}s, "
                           f"errors={metrics.get('error_count', 0)}")
        
        return jsonify({"status": "call ended"})

    elif event_type == 'call.recording.failed':
        # Recording failed
        logger.error(f"Recording failed for call {call_control_id}")
        call_session.update_state('failed')
        redis_store.update_call_session(call_session)
        
    elif event_type == 'call.media.streaming':
        # Handle streaming events
        event_payload = data.get('data', {}).get('payload', {})
        streaming_status = event_payload.get('streaming_status')
        client_state = event_payload.get('client_state')
        
        logger.info(f"Streaming event: {streaming_status} for call {call_control_id} with state {client_state}")
        
        if streaming_status == 'completed':
            # Stream completed successfully
            if client_state == 'greeting':
                # After greeting stream completes, ask user to repeat the affirmation
                prompt = "Now, please repeat the affirmation."
                
                # Stream the prompt using the streaming manager
                if tts_streaming_manager:
                    try:
                        # Create a new streaming session for the prompt
                        session_id = tts_streaming_manager.create_streaming_session(
                            call_control_id=call_control_id,
                            client_state="repeat_prompt"
                        )
                        
                        # Generate audio stream
                        audio_generator = tts_service.generate_speech_stream(
                            text=prompt, 
                            voice_id="default_female"
                        )
                        
                        # Track streaming session
                        if call_quality_monitor:
                            call_quality_monitor.start_streaming_session(call_session.id, session_id)
                        
                        # Process audio chunks
                        for audio_chunk in audio_generator:
                            # Add to streaming session
                            tts_streaming_manager.add_wav_audio(
                                call_control_id=call_control_id,
                                wav_data=audio_chunk
                            )
                        
                        # Start streaming
                        tts_streaming_manager.start_streaming(call_control_id)
                        
                        return jsonify({"status": "prompt streaming started"})
                    except Exception as e:
                        logger.error(f"Error in streaming prompt: {str(e)}")
                        # Fall back to non-streaming approach for the prompt
                
                # Fall back to traditional approach if streaming fails
                audio_bytes = tts_service.generate_speech(text=prompt, voice_id="default_female")
                if not audio_bytes:
                    logger.error(f"Failed to generate speech for prompt")
                    return jsonify({"error": "TTS failed"}), 500
                    
                # Upload audio to Telnyx storage
                audio_upload = telnyx_handler.upload_to_storage(file_data=audio_bytes)
                if not audio_upload:
                    logger.error(f"Failed to upload audio to Telnyx storage")
                    return jsonify({"error": "Audio upload failed"}), 500
                    
                # Play the prompt
                success = telnyx_handler.play_audio(
                    call_control_id=call_control_id,
                    audio_url=audio_upload['url'],
                    client_state='repeat_prompt'
                )
            
            elif client_state == 'repeat_prompt':
                # After prompting for repetition, start recording
                success = telnyx_handler.start_recording(
                    call_control_id=call_control_id,
                    client_state='recording_affirmation'
                )
                if success:
                    call_session.update_state('recording')
                    redis_store.update_call_session(call_session)
            
            # Handle other client states similarly
            
        elif streaming_status == 'error':
            # Handle streaming error
            error_message = event_payload.get('error', 'Unknown streaming error')
            logger.error(f"Streaming error for call {call_control_id}: {error_message}")
            
            # Record error in call metrics
            if call_quality_monitor:
                call_quality_monitor.record_error(call_session.id, "streaming_error", error_message)
            
            # Clean up streaming session
            if tts_streaming_manager:
                tts_streaming_manager.terminate_streaming(call_control_id, error=error_message)
            
            # Fall back to traditional approach
            # (Implement fallback logic based on client_state)

    return jsonify({"status": "webhook processed"})

@webhooks.route('/telnyx/message', methods=['POST'])
def telnyx_message_webhook():
    """Handle Telnyx messaging webhooks."""
    data = request.json
    event_type = data.get('data', {}).get('event_type')
    
    logger.info(f"Received Telnyx message webhook: {event_type}")
    
    # This would process message delivery confirmations, etc.
    # For now, just acknowledge the webhook
    
    return jsonify({"status": "webhook processed"}) 