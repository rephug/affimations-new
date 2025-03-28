#!/usr/bin/env python
# API Blueprint for Morning Coffee application

from functools import wraps
import logging
import uuid

from flask import Blueprint, request, jsonify, current_app
from werkzeug.exceptions import BadRequest, Unauthorized, NotFound

from config import config
from modules.models import User, CallSession

# Configure logging
logger = logging.getLogger('api')

# Create blueprint
api = Blueprint('api', __name__, url_prefix='/api')

# Utility functions
def api_key_required(f):
    """Decorator to require API key for API endpoints."""
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if api_key != config.MORNING_COFFEE_API_KEY:
            logger.warning(f"Unauthorized API access attempt")
            raise Unauthorized("Invalid API key")
        return f(*args, **kwargs)
    return decorated

def validate_json_body():
    """Validate that the request has a JSON body."""
    if not request.json:
        raise BadRequest("Request must contain a JSON body")

# User routes
@api.route('/users', methods=['POST'])
@api_key_required
def create_user():
    """Create a new user."""
    validate_json_body()
    
    data = request.json
    required_fields = ['phone_number', 'name']
    if not all(field in data for field in required_fields):
        raise BadRequest(f"Missing required fields: {required_fields}")
    
    try:
        redis_store = current_app.config['REDIS_STORE']
        user = redis_store.create_user(
            phone_number=data['phone_number'],
            name=data['name'],
            affirmation_preferences=data.get('affirmation_preferences', [])
        )
        
        logger.info(f"Created user: {user.id}")
        return jsonify(user.to_dict()), 201
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        return jsonify({"error": str(e)}), 500

@api.route('/users/<user_id>', methods=['GET'])
@api_key_required
def get_user(user_id):
    """Get user by ID."""
    redis_store = current_app.config['REDIS_STORE']
    user = redis_store.get_user_by_id(user_id)
    if not user:
        raise NotFound("User not found")
    
    return jsonify(user.to_dict())

@api.route('/users/phone/<phone_number>', methods=['GET'])
@api_key_required
def get_user_by_phone(phone_number):
    """Get user by phone number."""
    redis_store = current_app.config['REDIS_STORE']
    user = redis_store.get_user_by_phone(phone_number)
    if not user:
        raise NotFound("User not found")
    
    return jsonify(user.to_dict())

@api.route('/users/<user_id>', methods=['PUT'])
@api_key_required
def update_user(user_id):
    """Update user data."""
    validate_json_body()
    
    redis_store = current_app.config['REDIS_STORE']
    user = redis_store.get_user_by_id(user_id)
    if not user:
        raise NotFound("User not found")
    
    data = request.json
    
    # Update user fields
    if 'name' in data:
        user.name = data['name']
    if 'phone_number' in data:
        user.phone_number = data['phone_number']
    if 'affirmation_preferences' in data:
        user.affirmation_preferences = data['affirmation_preferences']
    if 'active' in data:
        user.active = data['active']
    
    # Save updated user
    success = redis_store.update_user(user)
    if not success:
        return jsonify({"error": "Failed to update user"}), 500
    
    logger.info(f"Updated user: {user.id}")
    return jsonify(user.to_dict())

# Call and SMS routes
@api.route('/send_affirmation', methods=['POST'])
@api_key_required
def send_affirmation():
    """Send an affirmation SMS to a user."""
    validate_json_body()
    
    data = request.json
    if 'user_id' not in data:
        raise BadRequest("User ID is required")
    
    telnyx_handler = current_app.config['TELNYX_HANDLER']
    if not telnyx_handler:
        return jsonify({"error": "Telnyx integration not available"}), 503
    
    redis_store = current_app.config['REDIS_STORE']
    user = redis_store.get_user_by_id(data['user_id'])
    if not user:
        raise NotFound("User not found")
    
    # Generate or use provided affirmation
    llm_handler = current_app.config['LLM_HANDLER']
    affirmation = data.get('affirmation')
    
    if not affirmation:
        # Generate an affirmation
        if not llm_handler:
            affirmation = f"I am worthy of love and respect. I am enough just as I am."
        else:
            # Prepare a prompt for the LLM
            prompt = [
                {"role": "system", "content": "You are an AI that creates personalized affirmations for users."},
                {"role": "user", "content": f"Create a short, positive affirmation for {user.name}."}
            ]
            
            # Add preference context if available
            if user.affirmation_preferences:
                preferences = ", ".join(user.affirmation_preferences)
                prompt[1]["content"] += f" Their preferred affirmation themes are: {preferences}."
            
            # Get response from LLM
            try:
                affirmation = llm_handler.get_response(prompt, temperature=0.7)
            except Exception as e:
                logger.error(f"Error generating affirmation: {e}")
                affirmation = f"I am worthy of love and respect. I am enough just as I am."
    
    # Send SMS via Telnyx
    result = telnyx_handler.send_sms(to=user.phone_number, text=affirmation)
    if not result:
        return jsonify({"error": "Failed to send SMS"}), 500
    
    logger.info(f"Sent affirmation SMS to user: {user.id}")
    return jsonify({
        "status": "sent",
        "affirmation": affirmation,
        "user_id": user.id,
        "message_id": result.get("id")
    })

@api.route('/make_call', methods=['POST'])
@api_key_required
def make_call():
    """Initiate a call to a user."""
    validate_json_body()
    
    data = request.json
    if 'user_id' not in data:
        raise BadRequest("User ID is required")
    
    telnyx_handler = current_app.config['TELNYX_HANDLER']
    if not telnyx_handler:
        return jsonify({"error": "Telnyx integration not available"}), 503
    
    redis_store = current_app.config['REDIS_STORE']
    user = redis_store.get_user_by_id(data['user_id'])
    if not user:
        raise NotFound("User not found")
    
    # Generate or use provided affirmation
    llm_handler = current_app.config['LLM_HANDLER']
    affirmation = data.get('affirmation')
    
    if not affirmation:
        # Generate an affirmation
        if not llm_handler:
            affirmation = f"I am worthy of love and respect. I am enough just as I am."
        else:
            # Prepare a prompt for the LLM
            prompt = [
                {"role": "system", "content": "You are an AI that creates personalized affirmations for users."},
                {"role": "user", "content": f"Create a short, positive affirmation for {user.name}."}
            ]
            
            # Add preference context if available
            if user.affirmation_preferences:
                preferences = ", ".join(user.affirmation_preferences)
                prompt[1]["content"] += f" Their preferred affirmation themes are: {preferences}."
            
            # Get response from LLM
            try:
                affirmation = llm_handler.get_response(prompt, temperature=0.7)
            except Exception as e:
                logger.error(f"Error generating affirmation: {e}")
                affirmation = f"I am worthy of love and respect. I am enough just as I am."
    
    # Create webhook URL for call events
    webhook_url = f"{config.WEBHOOK_BASE_URL}/webhooks/telnyx/call"
    
    # Initiate call via Telnyx
    result = telnyx_handler.make_call(
        to=user.phone_number,
        webhook_url=webhook_url,
        user_number=user.phone_number
    )
    
    if not result:
        return jsonify({"error": "Failed to initiate call"}), 500
    
    # Create a call session for tracking
    call_session = redis_store.create_call_session(
        user_id=user.id,
        call_control_id=result['call_control_id'],
        affirmation=affirmation
    )
    
    logger.info(f"Initiated call to user: {user.id}, call_id: {call_session.id}")
    return jsonify({
        "status": "initiated",
        "call_id": call_session.id,
        "user_id": user.id,
        "call_control_id": result['call_control_id'],
        "affirmation": affirmation
    })

@api.route('/call_status/<call_id>', methods=['GET'])
@api_key_required
def get_call_status(call_id):
    """Get the status of a call."""
    redis_store = current_app.config['REDIS_STORE']
    call_session = redis_store.get_call_session(call_id)
    if not call_session:
        raise NotFound("Call session not found")
    
    return jsonify(call_session.to_dict())

@api.route('/active_calls/<user_id>', methods=['GET'])
@api_key_required
def get_active_calls(user_id):
    """Get all active calls for a user."""
    redis_store = current_app.config['REDIS_STORE']
    # Check if user exists
    user = redis_store.get_user_by_id(user_id)
    if not user:
        raise NotFound("User not found")
        
    active_calls = redis_store.get_active_calls_for_user(user_id)
    return jsonify({
        "user_id": user_id,
        "active_calls": [call.to_dict() for call in active_calls]
    })

# Development/testing endpoints
@api.route('/dev/clear_test_data', methods=['POST'])
@api_key_required
def clear_test_data():
    """Clear test data from Redis (development only)."""
    if not config.DEBUG:
        return jsonify({"error": "This endpoint is only available in development mode"}), 403
        
    redis_store = current_app.config['REDIS_STORE']
    redis_store.clear_test_data()
    logger.info("Cleared test data from Redis")
    return jsonify({"status": "Test data cleared"})

@api.route('/test/voice_call', methods=['POST'])
@api_key_required
def test_voice_call():
    """Test voice call with custom voice settings"""
    validate_json_body()
    
    data = request.json
    if 'phone_number' not in data or 'affirmation' not in data:
        raise BadRequest("Phone number and affirmation are required")
    
    # Get the services
    telnyx_handler = current_app.config['TELNYX_HANDLER']
    tts_service = current_app.config['TTS_SERVICE']
    
    if not telnyx_handler:
        return jsonify({"error": "Telnyx integration not available"}), 503
    
    if not tts_service:
        return jsonify({"error": "TTS service not available"}), 503
    
    # Extract voice settings
    provider = data.get('provider', 'openai')  # Default to OpenAI
    voice_id = data.get('voice', None)  # Voice ID or style
    speed = float(data.get('speed', 1.0))
    
    # If provider specified, try to change provider
    if provider and provider != 'openai':
        try:
            success = tts_service.change_provider(provider)
            if not success:
                logger.warning(f"Failed to change provider to {provider}, using default")
        except Exception as e:
            logger.error(f"Error changing TTS provider: {e}")
            return jsonify({"error": f"Error changing TTS provider: {str(e)}"}), 500
    
    # Generate speech for the affirmation
    try:
        affirmation = data['affirmation']
        audio_data = tts_service.generate_speech(
            text=affirmation,
            voice_id=voice_id,
            speed=speed
        )
        
        if not audio_data:
            logger.error("Failed to generate speech")
            return jsonify({"error": "Failed to generate speech"}), 500
        
        # Upload to Telnyx
        upload_result = tts_service.generate_and_upload(
            text=affirmation,
            voice_id=voice_id,
            speed=speed
        )
        
        if not upload_result:
            logger.error("Failed to upload audio to Telnyx")
            return jsonify({"error": "Failed to upload audio to Telnyx"}), 500
        
        # Create webhook URL for call events
        webhook_url = f"{config.WEBHOOK_BASE_URL}/webhooks/telnyx/call"
        
        # Initiate call
        call_result = telnyx_handler.make_call(
            to=data['phone_number'],
            webhook_url=webhook_url,
            user_number=data['phone_number']
        )
        
        if not call_result:
            logger.error("Failed to initiate call")
            return jsonify({"error": "Failed to initiate call"}), 500
        
        # Create a call session to track the call
        redis_store = current_app.config['REDIS_STORE']
        call_session = redis_store.create_call_session(
            user_id="test_user",  # Test user ID
            call_control_id=call_result['call_control_id'],
            affirmation=affirmation,
            metadata={
                "test_call": True,
                "provider": provider,
                "voice": voice_id,
                "speed": speed,
                "audio_url": upload_result.get('url')
            }
        )
        
        logger.info(f"Initiated test call with voice settings. Call control ID: {call_result['call_control_id']}")
        
        return jsonify({
            "status": "initiated",
            "call_id": call_session.id,
            "call_control_id": call_result['call_control_id'],
            "audio_url": upload_result.get('url'),
            "provider": provider,
            "voice": voice_id,
            "speed": speed
        })
        
    except Exception as e:
        logger.error(f"Error in test voice call: {str(e)}")
        return jsonify({"error": str(e)}), 500

@api.errorhandler(BadRequest)
@api.errorhandler(Unauthorized)
@api.errorhandler(NotFound)
def handle_error(error):
    """Handle errors with proper JSON responses."""
    response = jsonify({"error": str(error)})
    response.status_code = error.code
    return response 