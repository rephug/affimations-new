"""
Functional tests for the API endpoints.
"""

import json
import pytest
from unittest.mock import patch


def test_health_endpoint(client, mock_redis, mock_tts_client):
    """
    GIVEN a Flask application
    WHEN the '/health' endpoint is requested (GET)
    THEN check the response is valid and contains health status for Redis and TTS
    """
    # Configure the mock responses
    mock_redis.ping.return_value = True
    mock_tts_client.health_check.return_value = {'status': 'healthy'}
    
    response = client.get('/health')
    data = json.loads(response.data)
    
    assert response.status_code == 200
    assert data['status'] == 'healthy'
    assert 'timestamp' in data
    assert data['services']['redis']['status'] == 'healthy'
    assert data['services']['tts']['status'] == 'healthy'


def test_health_endpoint_with_service_failure(client, mock_redis, mock_tts_client):
    """
    GIVEN a Flask application
    WHEN the '/health' endpoint is requested (GET) and a service is down
    THEN check the response shows the service as unhealthy
    """
    # Configure the mock responses
    mock_redis.ping.return_value = False
    mock_tts_client.health_check.return_value = None
    
    response = client.get('/health')
    data = json.loads(response.data)
    
    assert response.status_code == 200
    assert data['status'] == 'unhealthy'
    assert 'timestamp' in data
    assert data['services']['redis']['status'] == 'unhealthy'
    assert data['services']['tts']['status'] == 'unhealthy'


def test_api_send_sms_endpoint(client, mock_telnyx):
    """
    GIVEN a Flask application
    WHEN the '/api/send_sms' endpoint is requested (POST)
    THEN check that the SMS is sent successfully
    """
    # Set up the request data
    request_data = {
        'phone_number': '+15551234567',
        'message': 'Test message'
    }
    
    # Configure the mock response
    mock_telnyx.Message.create.return_value = {'id': 'msg_123'}
    
    response = client.post(
        '/api/send_sms',
        data=json.dumps(request_data),
        content_type='application/json',
        headers={'X-API-Key': 'test_api_key'}
    )
    data = json.loads(response.data)
    
    assert response.status_code == 200
    assert data['success'] is True
    assert 'message_id' in data


def test_api_send_sms_endpoint_invalid_auth(client):
    """
    GIVEN a Flask application
    WHEN the '/api/send_sms' endpoint is requested (POST) with invalid auth
    THEN check that the response is a 401 Unauthorized
    """
    # Set up the request data
    request_data = {
        'phone_number': '+15551234567',
        'message': 'Test message'
    }
    
    response = client.post(
        '/api/send_sms',
        data=json.dumps(request_data),
        content_type='application/json'
    )
    
    assert response.status_code == 401


def test_api_make_call_endpoint(client, mock_telnyx):
    """
    GIVEN a Flask application
    WHEN the '/api/make_call' endpoint is requested (POST)
    THEN check that the call is initiated successfully
    """
    # Set up the request data
    request_data = {
        'phone_number': '+15551234567'
    }
    
    # Configure the mock response
    mock_telnyx.Call.create.return_value = {'call_control_id': 'call_123'}
    
    response = client.post(
        '/api/make_call',
        data=json.dumps(request_data),
        content_type='application/json',
        headers={'X-API-Key': 'test_api_key'}
    )
    data = json.loads(response.data)
    
    assert response.status_code == 200
    assert data['success'] is True
    assert 'call_id' in data


def test_api_check_transcriptions_endpoint(client, mock_redis):
    """
    GIVEN a Flask application
    WHEN the '/api/check_transcriptions' endpoint is requested (GET)
    THEN check that pending transcriptions are returned
    """
    # Configure the mock Redis response
    mock_redis.keys.return_value = [b'transcription:123', b'transcription:456']
    mock_redis.hgetall.side_effect = [
        {b'status': b'pending', b'call_id': b'call_123'},
        {b'status': b'completed', b'call_id': b'call_456', b'text': b'Hello world'}
    ]
    
    response = client.get(
        '/api/check_transcriptions',
        headers={'X-API-Key': 'test_api_key'}
    )
    data = json.loads(response.data)
    
    assert response.status_code == 200
    assert data['pending_count'] == 2
    assert len(data['results']) == 2
    assert data['results'][0]['job_id'] == '123'
    assert data['results'][0]['status'] == 'pending'
    assert data['results'][1]['job_id'] == '456'
    assert data['results'][1]['status'] == 'completed'


def test_api_transcription_status_endpoint(client, mock_redis):
    """
    GIVEN a Flask application
    WHEN the '/api/transcription/{job_id}/status' endpoint is requested (GET)
    THEN check that the transcription status is returned
    """
    # Configure the mock Redis response
    job_id = '123'
    mock_redis.hgetall.return_value = {
        b'status': b'completed',
        b'call_id': b'call_123',
        b'text': b'This is a test transcription.'
    }
    
    response = client.get(
        f'/api/transcription/{job_id}/status',
        headers={'X-API-Key': 'test_api_key'}
    )
    data = json.loads(response.data)
    
    assert response.status_code == 200
    assert data['job_id'] == job_id
    assert data['status'] == 'completed'
    assert data['text'] == 'This is a test transcription.' 