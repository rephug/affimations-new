"""
Unit tests for the Redis store module.
"""

import pytest
from unittest.mock import patch, MagicMock
import redis

from app.modules.redis_store import RedisStore


@pytest.fixture
def mock_redis_connection():
    """
    Create a mock Redis connection for testing.
    """
    with patch('redis.Redis') as mock_redis:
        mock_instance = MagicMock()
        mock_redis.return_value = mock_instance
        
        # Configure default behaviors
        mock_instance.ping.return_value = True
        mock_instance.get.return_value = None
        mock_instance.set.return_value = True
        mock_instance.delete.return_value = True
        mock_instance.hset.return_value = True
        mock_instance.hgetall.return_value = {}
        mock_instance.keys.return_value = []
        mock_instance.exists.return_value = 0
        
        yield mock_instance


def test_redis_store_initialization():
    """
    GIVEN RedisStore class
    WHEN a new instance is created
    THEN it should initialize with the correct parameters
    """
    store = RedisStore(
        host='localhost',
        port=6379,
        password='password',
        db=0
    )
    
    assert store.host == 'localhost'
    assert store.port == 6379
    assert store.password == 'password'
    assert store.db == 0


def test_redis_store_connect_success(mock_redis_connection):
    """
    GIVEN a RedisStore instance
    WHEN connect is called
    THEN it should connect to Redis successfully
    """
    store = RedisStore(host='localhost')
    
    # Test connection
    assert store.connect() is True
    assert store.client is not None


@patch('redis.Redis')
def test_redis_store_connect_failure(mock_redis):
    """
    GIVEN a RedisStore instance
    WHEN connect is called and Redis connection fails
    THEN it should return False
    """
    # Configure the mock to raise an exception
    mock_redis.side_effect = redis.ConnectionError("Connection refused")
    
    store = RedisStore(host='localhost')
    
    # Test connection
    assert store.connect() is False
    assert store.client is None


def test_redis_store_ping_success(mock_redis_connection):
    """
    GIVEN a RedisStore instance with a connected client
    WHEN ping is called
    THEN it should return True if the ping succeeds
    """
    store = RedisStore(host='localhost')
    store.connect()
    
    assert store.ping() is True


def test_redis_store_ping_failure(mock_redis_connection):
    """
    GIVEN a RedisStore instance with a connected client
    WHEN ping is called and Redis ping fails
    THEN it should return False
    """
    # Configure the mock to raise an exception for ping
    mock_redis_connection.ping.side_effect = redis.ConnectionError("Connection refused")
    
    store = RedisStore(host='localhost')
    store.connect()
    
    assert store.ping() is False


def test_redis_store_get_success(mock_redis_connection):
    """
    GIVEN a RedisStore instance with a connected client
    WHEN get is called with a valid key
    THEN it should return the value for that key
    """
    # Configure the mock to return a value
    mock_redis_connection.get.return_value = b'test value'
    
    store = RedisStore(host='localhost')
    store.connect()
    
    assert store.get('test_key') == 'test value'


def test_redis_store_get_not_found(mock_redis_connection):
    """
    GIVEN a RedisStore instance with a connected client
    WHEN get is called with a key that doesn't exist
    THEN it should return None
    """
    # Configure the mock to return None (key not found)
    mock_redis_connection.get.return_value = None
    
    store = RedisStore(host='localhost')
    store.connect()
    
    assert store.get('nonexistent_key') is None


def test_redis_store_set_success(mock_redis_connection):
    """
    GIVEN a RedisStore instance with a connected client
    WHEN set is called with a key and value
    THEN it should store the value in Redis
    """
    store = RedisStore(host='localhost')
    store.connect()
    
    assert store.set('test_key', 'test value') is True
    mock_redis_connection.set.assert_called_once_with('test_key', 'test value', ex=None)


def test_redis_store_delete_success(mock_redis_connection):
    """
    GIVEN a RedisStore instance with a connected client
    WHEN delete is called with a key
    THEN it should delete the key from Redis
    """
    # Configure the mock to return 1 (key deleted)
    mock_redis_connection.delete.return_value = 1
    
    store = RedisStore(host='localhost')
    store.connect()
    
    assert store.delete('test_key') is True
    mock_redis_connection.delete.assert_called_once_with('test_key')


def test_redis_store_hset_success(mock_redis_connection):
    """
    GIVEN a RedisStore instance with a connected client
    WHEN hset is called with a key, field, and value
    THEN it should store the value in the hash
    """
    store = RedisStore(host='localhost')
    store.connect()
    
    assert store.hset('test_hash', 'test_field', 'test value') is True
    mock_redis_connection.hset.assert_called_once_with('test_hash', 'test_field', 'test value')


def test_redis_store_hget_success(mock_redis_connection):
    """
    GIVEN a RedisStore instance with a connected client
    WHEN hget is called with a key and field
    THEN it should return the value for that field
    """
    # Configure the mock to return a value
    mock_redis_connection.hget.return_value = b'test value'
    
    store = RedisStore(host='localhost')
    store.connect()
    
    assert store.hget('test_hash', 'test_field') == 'test value'
    mock_redis_connection.hget.assert_called_once_with('test_hash', 'test_field')


def test_redis_store_hgetall_success(mock_redis_connection):
    """
    GIVEN a RedisStore instance with a connected client
    WHEN hgetall is called with a key
    THEN it should return all fields and values in the hash
    """
    # Configure the mock to return a hash
    mock_redis_connection.hgetall.return_value = {
        b'field1': b'value1',
        b'field2': b'value2'
    }
    
    store = RedisStore(host='localhost')
    store.connect()
    
    result = store.hgetall('test_hash')
    assert result == {'field1': 'value1', 'field2': 'value2'}
    mock_redis_connection.hgetall.assert_called_once_with('test_hash')


def test_redis_store_keys_pattern(mock_redis_connection):
    """
    GIVEN a RedisStore instance with a connected client
    WHEN keys is called with a pattern
    THEN it should return keys matching the pattern
    """
    # Configure the mock to return keys
    mock_redis_connection.keys.return_value = [b'prefix:key1', b'prefix:key2']
    
    store = RedisStore(host='localhost')
    store.connect()
    
    result = store.keys('prefix:*')
    assert result == ['prefix:key1', 'prefix:key2']
    mock_redis_connection.keys.assert_called_once_with('prefix:*') 