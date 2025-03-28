#!/usr/bin/env python
# Configuration module for Morning Coffee application

import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()

class Config:
    """Configuration class for the application."""
    
    def __init__(self):
        # Telnyx credentials
        self.TELNYX_API_KEY = os.getenv('TELNYX_API_KEY')
        self.TELNYX_PHONE_NUMBER = os.getenv('TELNYX_PHONE_NUMBER')
        self.TELNYX_MESSAGING_PROFILE_ID = os.getenv('TELNYX_MESSAGING_PROFILE_ID')
        self.TELNYX_APP_ID = os.getenv('TELNYX_APP_ID')
        self.TELNYX_STORAGE_BUCKET_ID = os.getenv('TELNYX_STORAGE_BUCKET_ID')
        
        # AssemblyAI configuration
        self.ASSEMBLYAI_API_KEY = os.getenv('ASSEMBLYAI_API_KEY')
        
        # Spark TTS configuration
        self.SPARK_TTS_URL = os.getenv('SPARK_TTS_URL', 'http://spark-tts:8020')
        
        # LLM configuration
        self.LLM_TYPE = os.getenv('LLM_TYPE', 'openai')
        self.LLM_API_KEY = os.getenv('LLM_API_KEY')
        self.LLM_MODEL = os.getenv('LLM_MODEL', 'gpt-3.5-turbo')
        self.LLM_ENDPOINT = os.getenv('LLM_ENDPOINT', None)
        
        # Redis configuration
        self.REDIS_URL = os.getenv('REDIS_URL', 'redis://redis:6379/0')
        
        # Application configuration
        self.BASE_URL = os.getenv('BASE_URL')
        self.DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
        
        # Validate required configuration
        self._validate_config()
    
    def _validate_config(self):
        """Validate that required configuration variables are set."""
        required_vars = [
            ('TELNYX_API_KEY', self.TELNYX_API_KEY),
            ('TELNYX_PHONE_NUMBER', self.TELNYX_PHONE_NUMBER),
            ('TELNYX_MESSAGING_PROFILE_ID', self.TELNYX_MESSAGING_PROFILE_ID),
            ('TELNYX_APP_ID', self.TELNYX_APP_ID),
            ('TELNYX_STORAGE_BUCKET_ID', self.TELNYX_STORAGE_BUCKET_ID),
            ('ASSEMBLYAI_API_KEY', self.ASSEMBLYAI_API_KEY),
            ('BASE_URL', self.BASE_URL),
        ]
        
        # Check LLM configuration based on type
        if self.LLM_TYPE == 'openai':
            required_vars.append(('LLM_API_KEY', self.LLM_API_KEY))
        elif self.LLM_TYPE == 'claude':
            required_vars.append(('LLM_API_KEY', self.LLM_API_KEY))
        elif self.LLM_TYPE == 'llama':
            if not self.LLM_ENDPOINT:
                required_vars.append(('LLM_ENDPOINT', self.LLM_ENDPOINT))
        
        missing_vars = [var_name for var_name, var_value in required_vars if not var_value]
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
