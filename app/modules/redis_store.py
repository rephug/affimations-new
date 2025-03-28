#!/usr/bin/env python
# Redis Storage Module for Morning Coffee application

import json
import logging
import uuid
from typing import Optional, Dict, Any, List, Union

import redis

from .models import User, CallSession

# Configure logging
logger = logging.getLogger('redis-store')

class RedisStore:
    """Redis storage interface for Morning Coffee application."""
    
    # Key prefixes for different data types
    USER_PREFIX = 'user:'
    CALL_PREFIX = 'call:'
    USER_PHONE_INDEX = 'user_phone_index'
    
    def __init__(self, host: str = 'redis', port: int = 6379, db: int = 0, password: Optional[str] = None):
        """
        Initialize Redis connection.
        
        Args:
            host (str): Redis host
            port (int): Redis port
            db (int): Redis database index
            password (Optional[str]): Redis password
        """
        self.redis = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=True,  # Automatically decode responses to strings
            socket_timeout=5,  # Set socket timeout
            socket_connect_timeout=5  # Set socket connect timeout
        )
        logger.info(f'Redis store initialized: {host}:{port}/{db}')
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check Redis connection health.
        
        Returns:
            Dict[str, Any]: Health status
        """
        try:
            # Try a ping to check connection
            self.redis.ping()
            return {
                'status': 'ok',
                'message': 'Redis connection is healthy'
            }
        except redis.RedisError as e:
            logger.error(f'Redis health check failed: {str(e)}')
            return {
                'status': 'error',
                'message': f'Redis connection error: {str(e)}'
            }
    
    # User operations
    def create_user(self, phone_number: str, name: str, 
                    affirmation_preferences: Optional[List[str]] = None) -> User:
        """
        Create a new user.
        
        Args:
            phone_number (str): User's phone number
            name (str): User's name
            affirmation_preferences (Optional[List[str]]): Affirmation preferences
            
        Returns:
            User: Created user object
        """
        # Check if user with this phone number already exists
        existing_user_id = self.redis.hget(self.USER_PHONE_INDEX, phone_number)
        if existing_user_id:
            user = self.get_user_by_id(existing_user_id)
            if user:
                logger.info(f'User with phone {phone_number} already exists, returning existing user')
                return user
        
        # Create new user
        user_id = str(uuid.uuid4())
        user = User(
            id=user_id,
            phone_number=phone_number,
            name=name,
            affirmation_preferences=affirmation_preferences or []
        )
        
        # Save user
        user_key = f'{self.USER_PREFIX}{user_id}'
        self.redis.hset(user_key, mapping=user.to_dict())
        
        # Update phone index
        self.redis.hset(self.USER_PHONE_INDEX, phone_number, user_id)
        
        logger.info(f'Created new user with ID {user_id} for phone {phone_number}')
        return user
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """
        Get user by ID.
        
        Args:
            user_id (str): User ID
            
        Returns:
            Optional[User]: User object if found, None otherwise
        """
        user_key = f'{self.USER_PREFIX}{user_id}'
        user_data = self.redis.hgetall(user_key)
        
        if not user_data:
            logger.warning(f'User with ID {user_id} not found')
            return None
        
        return User.from_dict(user_data)
    
    def get_user_by_phone(self, phone_number: str) -> Optional[User]:
        """
        Get user by phone number.
        
        Args:
            phone_number (str): User's phone number
            
        Returns:
            Optional[User]: User object if found, None otherwise
        """
        user_id = self.redis.hget(self.USER_PHONE_INDEX, phone_number)
        if not user_id:
            logger.warning(f'No user found for phone number {phone_number}')
            return None
        
        return self.get_user_by_id(user_id)
    
    def update_user(self, user: User) -> bool:
        """
        Update user data.
        
        Args:
            user (User): User object to update
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            user_key = f'{self.USER_PREFIX}{user.id}'
            # Check if user exists
            if not self.redis.exists(user_key):
                logger.warning(f'Cannot update user {user.id} - does not exist')
                return False
            
            # Update user data
            self.redis.hset(user_key, mapping=user.to_dict())
            
            # Update phone index if phone number changed
            existing_id = self.redis.hget(self.USER_PHONE_INDEX, user.phone_number)
            if existing_id != user.id:
                # If there was a previous phone number, we'd need to handle that
                # This is simplified for now
                self.redis.hset(self.USER_PHONE_INDEX, user.phone_number, user.id)
            
            logger.info(f'Updated user {user.id}')
            return True
            
        except Exception as e:
            logger.error(f'Error updating user {user.id}: {str(e)}')
            return False
    
    # Call session operations
    def create_call_session(self, user_id: str, call_control_id: str, 
                            affirmation: Optional[str] = None) -> CallSession:
        """
        Create a new call session.
        
        Args:
            user_id (str): User ID
            call_control_id (str): Telnyx call control ID
            affirmation (Optional[str]): Affirmation for this call
            
        Returns:
            CallSession: Created call session
        """
        call_id = str(uuid.uuid4())
        call_session = CallSession(
            id=call_id,
            user_id=user_id,
            call_control_id=call_control_id,
            affirmation=affirmation
        )
        
        # Save call session
        call_key = f'{self.CALL_PREFIX}{call_id}'
        self.redis.hset(call_key, mapping=call_session.to_dict())
        
        # Create an index by call control ID for quick lookup
        self.redis.set(f'call_control:{call_control_id}', call_id, ex=86400)  # Expire after 24 hours
        
        logger.info(f'Created call session {call_id} for user {user_id}')
        return call_session
    
    def get_call_session(self, call_id: str) -> Optional[CallSession]:
        """
        Get call session by ID.
        
        Args:
            call_id (str): Call session ID
            
        Returns:
            Optional[CallSession]: Call session if found, None otherwise
        """
        call_key = f'{self.CALL_PREFIX}{call_id}'
        call_data = self.redis.hgetall(call_key)
        
        if not call_data:
            logger.warning(f'Call session {call_id} not found')
            return None
        
        return CallSession.from_dict(call_data)
    
    def get_call_by_control_id(self, call_control_id: str) -> Optional[CallSession]:
        """
        Get call session by Telnyx call control ID.
        
        Args:
            call_control_id (str): Telnyx call control ID
            
        Returns:
            Optional[CallSession]: Call session if found, None otherwise
        """
        call_id = self.redis.get(f'call_control:{call_control_id}')
        if not call_id:
            logger.warning(f'No call session found for control ID {call_control_id}')
            return None
        
        return self.get_call_session(call_id)
    
    def update_call_session(self, call_session: CallSession) -> bool:
        """
        Update call session data.
        
        Args:
            call_session (CallSession): Call session to update
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            call_key = f'{self.CALL_PREFIX}{call_session.id}'
            
            # Check if call session exists
            if not self.redis.exists(call_key):
                logger.warning(f'Cannot update call session {call_session.id} - does not exist')
                return False
            
            # Update call session data
            self.redis.hset(call_key, mapping=call_session.to_dict())
            
            logger.info(f'Updated call session {call_session.id}')
            return True
            
        except Exception as e:
            logger.error(f'Error updating call session {call_session.id}: {str(e)}')
            return False
            
    def get_active_calls_for_user(self, user_id: str) -> List[CallSession]:
        """
        Get all active calls for a user.
        
        Args:
            user_id (str): User ID
            
        Returns:
            List[CallSession]: List of active call sessions
        """
        # This is an inefficient implementation that scans all calls
        # In a production system, we would maintain indexes or use Redis Streams
        active_calls = []
        
        # Scan for all call keys
        cursor = 0
        while True:
            cursor, keys = self.redis.scan(cursor, f'{self.CALL_PREFIX}*', 100)
            
            for key in keys:
                call_data = self.redis.hgetall(key)
                if not call_data:
                    continue
                    
                # Check if this call belongs to the user and is not completed
                if (call_data.get('user_id') == user_id and 
                    call_data.get('state') not in ['completed', 'failed']):
                    active_calls.append(CallSession.from_dict(call_data))
            
            # Exit the loop when we've scanned all keys
            if cursor == 0:
                break
        
        logger.info(f'Found {len(active_calls)} active calls for user {user_id}')
        return active_calls
    
    def clear_test_data(self) -> None:
        """Clear all test data from Redis (for development only)."""
        # This should only be used in development/testing
        try:
            # Clear all keys with our prefixes
            cursor = 0
            while True:
                cursor, keys = self.redis.scan(cursor, f'{self.USER_PREFIX}*', 100)
                if keys:
                    self.redis.delete(*keys)
                if cursor == 0:
                    break
            
            cursor = 0
            while True:
                cursor, keys = self.redis.scan(cursor, f'{self.CALL_PREFIX}*', 100)
                if keys:
                    self.redis.delete(*keys)
                if cursor == 0:
                    break
                    
            # Clear the phone index
            self.redis.delete(self.USER_PHONE_INDEX)
            
            # Clear call control index
            cursor = 0
            while True:
                cursor, keys = self.redis.scan(cursor, 'call_control:*', 100)
                if keys:
                    self.redis.delete(*keys)
                if cursor == 0:
                    break
                    
            logger.info('Cleared all test data from Redis')
            
        except Exception as e:
            logger.error(f'Error clearing test data: {str(e)}') 