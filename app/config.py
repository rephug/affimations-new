#!/usr/bin/env python
# Configuration module for Morning Coffee application

import os
import json
from typing import Dict, Any


class Config:
    """Configuration for the Morning Coffee application."""
    
    def __init__(self):
        """Initialize configuration from environment variables."""
        # Application settings
        self.DEBUG = os.environ.get('FLASK_ENV') == 'development'
        self.PORT = int(os.environ.get('PORT', 5000))
        self.LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
        self.MORNING_COFFEE_API_KEY = os.environ.get('MORNING_COFFEE_API_KEY')
        
        # Redis configuration
        self.REDIS_HOST = os.environ.get('REDIS_HOST', 'redis')
        self.REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
        self.REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD')
        self.REDIS_DB = int(os.environ.get('REDIS_DB', 0))
        self.REDIS_URL = self._build_redis_url()
        
        # TTS service configuration
        self.TTS_SERVICE_URL = os.environ.get('TTS_SERVICE_URL', 'http://spark-tts:5001')
        self.TTS_SERVICE_TIMEOUT = int(os.environ.get('TTS_SERVICE_TIMEOUT', 30))
        
        # TTS provider selection
        self.TTS_PROVIDER = os.environ.get('TTS_PROVIDER', 'openai')  # Default to OpenAI
        self.TTS_CACHE_ENABLED = os.environ.get('TTS_CACHE_ENABLED', 'true').lower() == 'true'
        self.TTS_CACHE_TTL = int(os.environ.get('TTS_CACHE_TTL', 86400))  # 24 hours default
        
        # Voice mapping configuration
        self.TTS_VOICE_MAPPING = self._load_voice_mapping()
        
        # Telnyx settings
        self.TELNYX_API_KEY = os.environ.get('TELNYX_API_KEY')
        self.TELNYX_APP_ID = os.environ.get('TELNYX_APP_ID')  # Connection ID
        self.TELNYX_PHONE_NUMBER = os.environ.get('TELNYX_PHONE_NUMBER')
        self.TELNYX_MESSAGING_PROFILE_ID = os.environ.get('TELNYX_MESSAGING_PROFILE_ID')
        self.TELNYX_STORAGE_BUCKET_ID = os.environ.get('TELNYX_STORAGE_BUCKET_ID')
        
        # AssemblyAI settings
        self.ASSEMBLYAI_API_KEY = os.environ.get('ASSEMBLYAI_API_KEY')
        
        # OpenAI settings for TTS and STT
        self.OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
        self.OPENAI_TTS_MODEL = os.environ.get('OPENAI_TTS_MODEL', 'gpt-4o-mini-tts')
        self.OPENAI_TRANSCRIBE_MODEL = os.environ.get('OPENAI_TRANSCRIBE_MODEL', 'gpt-4o-mini-transcribe')
        self.OPENAI_DEFAULT_VOICE_STYLE = os.environ.get('OPENAI_DEFAULT_VOICE_STYLE', 
                                                     'Speak in a natural, warm tone that is friendly and conversational')
        
        # LLM settings
        self.LLM_TYPE = os.environ.get('LLM_TYPE', 'openai')
        self.LLM_API_KEY = os.environ.get('LLM_API_KEY')
        self.LLM_MODEL = os.environ.get('LLM_MODEL', 'gpt-4o')
        self.LLM_ENDPOINT = os.environ.get('LLM_ENDPOINT', 'https://api.openai.com/v1')
        
        # Webhook settings
        self.WEBHOOK_BASE_URL = os.environ.get('WEBHOOK_BASE_URL', 'https://example.com')
    
    def _build_redis_url(self) -> str:
        """
        Build Redis URL from components.
        
        Returns:
            str: Redis URL
        """
        auth = f':{self.REDIS_PASSWORD}@' if self.REDIS_PASSWORD else ''
        return f'redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}'
    
    def _load_voice_mapping(self) -> Dict[str, Dict[str, str]]:
        """
        Load voice mapping from environment or default mapping.
        
        Returns:
            Dict[str, Dict[str, str]]: Voice mapping dictionary
        """
        try:
            mapping_json = os.environ.get('TTS_VOICE_MAPPING', '')
            if mapping_json:
                return json.loads(mapping_json)
        except Exception as e:
            print(f"Error loading voice mapping: {e}")
        
        # Default mapping - updated with OpenAI voice styles
        return {
            "default_female": {
                "openai": "Speak in a natural, warm female voice with a friendly tone"
            },
            "default_male": {
                "openai": "Speak in a natural, warm male voice with a friendly tone"
            },
            "professional": {
                "openai": "Speak in a clear, professional tone. Be concise and articulate."
            },
            "enthusiastic": {
                "openai": "Speak with enthusiasm and energy! Be excited and upbeat."
            },
            "calm": {
                "openai": "Speak in a calm, soothing voice like a mindfulness teacher. Use a serene, peaceful tone."
            },
            "customer_service": {
                "openai": "Speak like a helpful customer service representative. Be friendly, professional, and apologetic if there's an issue."
            }
        }
    
    def get_tts_provider_config(self) -> Dict[str, Dict[str, Any]]:
        """
        Get configuration for all TTS providers.
        
        Returns:
            Dict[str, Dict[str, Any]]: Provider configuration dictionary
        """
        return {
            "openai": {
                "api_key": self.OPENAI_API_KEY,
                "model": self.OPENAI_TTS_MODEL,
                "voice_style": self.OPENAI_DEFAULT_VOICE_STYLE
            },
            "google": {
                "credentials_path": os.environ.get('GOOGLE_CREDENTIALS_PATH'),
                "project_id": os.environ.get('GOOGLE_PROJECT_ID')
            },
            "azure": {
                "speech_key": os.environ.get('AZURE_SPEECH_KEY'),
                "speech_region": os.environ.get('AZURE_SPEECH_REGION')
            },
            "elevenlabs": {
                "api_key": os.environ.get('ELEVENLABS_API_KEY'),
                "model_id": os.environ.get('ELEVENLABS_MODEL_ID', 'eleven_monolingual_v1')
            },
            "murf": {
                "api_key": os.environ.get('MURF_API_KEY')
            },
            "kokoro": {
                # Kokoro doesn't require API keys, only voice settings
            }
        }
    
    def validate(self) -> Dict[str, Any]:
        """
        Validate configuration, checking for required variables.
        
        Returns:
            Dict[str, Any]: Validation result with status and missing fields
        """
        required_vars = [
            'TELNYX_API_KEY', 
            'TELNYX_APP_ID', 
            'TELNYX_PHONE_NUMBER', 
            'TELNYX_MESSAGING_PROFILE_ID',
            'MORNING_COFFEE_API_KEY'
        ]
        
        # Add required keys for selected TTS provider
        if self.TTS_PROVIDER == 'openai':
            required_vars.append('OPENAI_API_KEY')
        
        # Add required keys for transcription (OpenAI or AssemblyAI)
        if not self.OPENAI_API_KEY:
            required_vars.append('ASSEMBLYAI_API_KEY')
        
        # Add required keys for selected LLM type
        if self.LLM_TYPE == 'openai':
            required_vars.append('LLM_API_KEY')
        
        missing = [var for var in required_vars if not getattr(self, var)]
        
        return {
            'valid': len(missing) == 0,
            'missing': missing
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.
        
        Returns:
            Dict[str, Any]: Configuration as dictionary
        """
        # Sanitize sensitive information
        config_dict = {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
        
        # Mask sensitive values
        sensitive_keys = [
            'TELNYX_API_KEY',
            'REDIS_PASSWORD',
            'ASSEMBLYAI_API_KEY',
            'OPENAI_API_KEY',
            'LLM_API_KEY',
            'MORNING_COFFEE_API_KEY'
        ]
        
        for key in sensitive_keys:
            if key in config_dict and config_dict[key]:
                config_dict[key] = '****'
        
        return config_dict


class TestConfig(Config):
    """
    Test configuration for the Morning Coffee application.
    This configuration is used for running tests with pytest.
    """
    
    def __init__(self):
        """Initialize test configuration with test values."""
        super().__init__()
        
        # Test settings
        self.TESTING = True
        self.DEBUG = True
        self.LOG_LEVEL = 'INFO'
        self.MORNING_COFFEE_API_KEY = 'test_api_key'
        
        # Test Redis configuration
        self.REDIS_HOST = 'localhost'
        self.REDIS_PORT = 6379
        self.REDIS_PASSWORD = None
        self.REDIS_DB = 15  # Use DB 15 for tests
        self.REDIS_URL = self._build_redis_url()
        
        # Test TTS configuration
        self.TTS_SERVICE_URL = 'http://localhost:5001'
        self.TTS_SERVICE_TIMEOUT = 5
        self.TTS_PROVIDER = 'openai'
        
        # Test Telnyx settings
        self.TELNYX_API_KEY = 'test_telnyx_api_key'
        self.TELNYX_APP_ID = 'test_telnyx_app_id'
        self.TELNYX_PHONE_NUMBER = '+15551234567'
        self.TELNYX_MESSAGING_PROFILE_ID = 'test_profile_id'
        self.TELNYX_STORAGE_BUCKET_ID = 'test_bucket_id'
        
        # Test AssemblyAI settings
        self.ASSEMBLYAI_API_KEY = 'test_assemblyai_api_key'
        
        # Test OpenAI settings
        self.OPENAI_API_KEY = 'test_openai_api_key'
        self.OPENAI_TTS_MODEL = 'gpt-4o-mini-tts'
        self.OPENAI_TRANSCRIBE_MODEL = 'gpt-4o-mini-transcribe'
        
        # Test LLM settings
        self.LLM_TYPE = 'openai'
        self.LLM_API_KEY = 'test_llm_api_key'
        self.LLM_MODEL = 'gpt-4o'
        self.LLM_ENDPOINT = 'https://api.openai.com/v1'


# Create singleton instance
config = Config() 