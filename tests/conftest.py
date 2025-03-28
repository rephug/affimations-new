"""
Pytest configuration file for Morning Coffee application testing.
Contains fixtures that can be reused across test modules.
"""

import os
import sys
import pytest
from unittest.mock import MagicMock, patch

# Add the parent directory to sys.path to allow importing from the app directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the Flask app
from app.app import create_app
from app.config import TestConfig


@pytest.fixture
def app():
    """
    Create a Flask app configured for testing.
    """
    app = create_app(TestConfig)
    
    # Configure the app for testing
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    # Return the app instance
    yield app


@pytest.fixture
def client(app):
    """
    Create a test client for the Flask app.
    """
    with app.test_client() as client:
        with app.app_context():
            yield client


@pytest.fixture
def mock_redis():
    """
    Mock the Redis client for testing.
    """
    with patch('app.modules.redis_store.redis.Redis') as mock_redis:
        # Setup mock Redis behaviors
        mock_instance = MagicMock()
        mock_redis.return_value = mock_instance
        
        # Configure mock Redis methods
        mock_instance.get.return_value = None
        mock_instance.set.return_value = True
        mock_instance.delete.return_value = True
        mock_instance.hset.return_value = True
        mock_instance.hgetall.return_value = {}
        mock_instance.ping.return_value = True
        
        yield mock_instance


@pytest.fixture
def mock_telnyx():
    """
    Mock the Telnyx client for testing.
    """
    with patch('app.modules.telnyx_handler.telnyx') as mock_telnyx:
        # Configure mocked methods
        mock_telnyx.Message.create.return_value = MagicMock(id='msg_123')
        mock_telnyx.Call.create.return_value = MagicMock(call_control_id='call_123')
        
        yield mock_telnyx


@pytest.fixture
def mock_assemblyai():
    """
    Mock the AssemblyAI client for testing.
    """
    with patch('app.modules.assemblyai_handler.assemblyai') as mock_assemblyai:
        # Mock transcriber instance
        mock_transcriber = MagicMock()
        mock_assemblyai.Transcriber.return_value = mock_transcriber
        
        # Configure mock responses
        mock_transcriber.submit.return_value = MagicMock(id='transcription_123')
        mock_transcriber.get_by_id.return_value = MagicMock(
            status='completed',
            text='This is a test transcription.'
        )
        
        yield mock_assemblyai


@pytest.fixture
def mock_tts_client():
    """
    Mock the TTS client for testing.
    """
    with patch('app.modules.tts_client.SparkTTSClient') as mock_tts:
        # Configure mock instance
        mock_instance = MagicMock()
        mock_tts.return_value = mock_instance
        
        # Setup mock methods
        mock_instance.health_check.return_value = {'status': 'healthy'}
        mock_instance.get_voices.return_value = [{'id': 'voice1', 'name': 'Voice 1'}]
        mock_instance.generate_speech.return_value = b'fake audio data'
        
        yield mock_instance


@pytest.fixture
def mock_llm():
    """
    Mock the LLM handler for testing.
    """
    with patch('app.modules.llm_handler.LLMHandler') as mock_llm:
        # Configure mock instance
        mock_instance = MagicMock()
        mock_llm.return_value = mock_instance
        
        # Setup mock responses
        mock_instance.get_response.return_value = 'This is a mock LLM response.'
        mock_instance.health_check.return_value = True
        
        yield mock_instance 