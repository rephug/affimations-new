"""
Unit tests for the TTS client module.
"""

import pytest
import requests
from unittest.mock import patch, MagicMock

from app.modules.tts_client import SparkTTSClient


@pytest.fixture
def tts_client():
    """
    Create a TTS client instance for testing.
    """
    return SparkTTSClient(base_url='http://localhost:5001', timeout=5)


@pytest.fixture
def mock_requests():
    """
    Mock the requests module for testing HTTP requests.
    """
    with patch('app.modules.tts_client.requests') as mock_requests:
        # Configure a successful response for health check
        health_response = MagicMock()
        health_response.status_code = 200
        health_response.json.return_value = {
            'status': 'healthy',
            'version': '1.0.0'
        }
        
        # Configure a successful response for getting voices
        voices_response = MagicMock()
        voices_response.status_code = 200
        voices_response.json.return_value = {
            'voices': [
                {'id': 'voice1', 'name': 'Voice 1'},
                {'id': 'voice2', 'name': 'Voice 2'}
            ]
        }
        
        # Configure a successful response for generating speech
        speech_response = MagicMock()
        speech_response.status_code = 200
        speech_response.content = b'fake audio data'
        
        # Configure request responses
        mock_requests.get.side_effect = lambda url, **kwargs: (
            health_response if 'health' in url else voices_response
        )
        mock_requests.post.return_value = speech_response
        
        # Configure request exceptions
        mock_requests.exceptions = requests.exceptions
        
        yield mock_requests


def test_health_check_success(tts_client, mock_requests):
    """
    GIVEN a SparkTTSClient instance
    WHEN health_check is called and the server responds successfully
    THEN it should return the health status information
    """
    result = tts_client.health_check()
    
    # Verify the request was made correctly
    mock_requests.get.assert_called_once_with(
        'http://localhost:5001/health',
        timeout=5
    )
    
    # Verify the result
    assert result['status'] == 'healthy'
    assert result['version'] == '1.0.0'


def test_health_check_failure(tts_client, mock_requests):
    """
    GIVEN a SparkTTSClient instance
    WHEN health_check is called and the server responds with an error
    THEN it should return None
    """
    # Configure a failed response
    error_response = MagicMock()
    error_response.status_code = 500
    mock_requests.get.return_value = error_response
    
    result = tts_client.health_check()
    
    # Verify the result
    assert result is None


def test_health_check_timeout(tts_client, mock_requests):
    """
    GIVEN a SparkTTSClient instance
    WHEN health_check is called and the request times out
    THEN it should return None and log the error
    """
    # Configure a timeout exception
    mock_requests.get.side_effect = requests.exceptions.Timeout("Request timed out")
    
    result = tts_client.health_check()
    
    # Verify the result
    assert result is None


def test_get_voices_success(tts_client, mock_requests):
    """
    GIVEN a SparkTTSClient instance
    WHEN get_voices is called and the server responds successfully
    THEN it should return the list of voices
    """
    voices = tts_client.get_voices()
    
    # Verify the request was made correctly
    mock_requests.get.assert_called_with(
        'http://localhost:5001/voices',
        timeout=5
    )
    
    # Verify the result
    assert len(voices) == 2
    assert voices[0]['id'] == 'voice1'
    assert voices[1]['name'] == 'Voice 2'


def test_generate_speech_success(tts_client, mock_requests):
    """
    GIVEN a SparkTTSClient instance
    WHEN generate_speech is called with valid parameters
    THEN it should return the audio data
    """
    audio_data = tts_client.generate_speech(
        text="Hello, world!",
        voice_id="voice1"
    )
    
    # Verify the request was made correctly
    mock_requests.post.assert_called_once()
    call_args = mock_requests.post.call_args[0]
    call_kwargs = mock_requests.post.call_args[1]
    
    assert call_args[0] == 'http://localhost:5001/generate'
    assert call_kwargs['timeout'] == 5
    assert call_kwargs['json']['text'] == 'Hello, world!'
    assert call_kwargs['json']['voice_id'] == 'voice1'
    
    # Verify the result
    assert audio_data == b'fake audio data'


def test_generate_speech_failure(tts_client, mock_requests):
    """
    GIVEN a SparkTTSClient instance
    WHEN generate_speech is called and the server responds with an error
    THEN it should return None
    """
    # Configure a failed response
    error_response = MagicMock()
    error_response.status_code = 400
    error_response.json.return_value = {'error': 'Invalid parameters'}
    mock_requests.post.return_value = error_response
    
    audio_data = tts_client.generate_speech(
        text="Hello, world!",
        voice_id="invalid_voice"
    )
    
    # Verify the result
    assert audio_data is None 