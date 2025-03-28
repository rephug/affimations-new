#!/usr/bin/env python
# Updated Configuration module for Morning Coffee application with OpenAI TTS support

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
        self.TTS_PROVIDER = os.environ.get('TTS_PROVIDER', 'kokoro')
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
        
        # Google TTS configuration
        self.GOOGLE_CREDENTIALS_PATH = os.environ.get('GOOGLE_CREDENTIALS_PATH', '')
        self.GOOGLE_PROJECT_ID = os.environ.get('GOOGLE_PROJECT_ID', '')
        
        # Murf.ai configuration
        self.MURF_API_KEY = os.environ.get('MURF_API_KEY', '')
        
        # ElevenLabs configuration
        self.ELEVENLABS_API_KEY = os.environ.get('ELEVENLABS_API_KEY', '')
        self.ELEVENLABS_MODEL_ID = os.environ.get('ELEVENLABS_MODEL_ID', 'eleven_multilingual_v2')
        
        # Azure Speech Services configuration
        self.AZURE_SPEECH_KEY = os.environ.get('AZURE_SPEECH_KEY', '')
        self.AZURE_SPEECH_REGION = os.environ.get('AZURE_SPEECH_REGION', '')
        
        # Piper configuration
        self.PIPER_PATH = os.environ.get('PIPER_PATH', '/usr/local/bin/piper')
        self.PIPER_MODELS_DIR = os.environ.get('PIPER_MODELS_DIR', '/app/piper_models')
        self.PIPER_DEFAULT_MODEL = os.environ.get('PIPER_DEFAULT_MODEL', 'en_US-lessac-medium')
        
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
                "kokoro": "en_female_1",
                "google": "en-US-Neural2-F",
                "elevenlabs": "21m00Tcm4TlvDq8ikWAM",  # Rachel
                "murf": "en-US-madison",
                "azure": "en-US-JennyNeural",
                "piper": "en_US-lessac-medium",
                "openai": "Speak in a natural, warm female voice with a friendly tone"
            },
            "default_male": {
                "kokoro": "en_male_1",
                "google": "en-US-Neural2-J",
                "elevenlabs": "pNInz6obpgDQGcFmaJgB",  # Adam
                "murf": "en-US-daniel",
                "azure": "en-US-GuyNeural",
                "piper": "en_US-ljspeech-medium",
                "openai": "Speak in a natural, warm male voice with a friendly tone"
            },
            "professional": {
                "kokoro": "en_female_2",
                "google": "en-US-Neural2-F",
                "elevenlabs": "21m00Tcm4TlvDq8ikWAM",  # Rachel
                "murf": "en-US-madison",
                "azure": "en-US-JennyNeural",
                "piper": "en_US-lessac-medium",
                "openai": "Speak in a clear, professional tone. Be concise and articulate."
            },
            "enthusiastic": {
                "kokoro": "en_female_1",
                "google": "en-US-Neural2-F",
                "elevenlabs": "g9IGB5x0zCEXQUXG8j2O",  # Bella
                "murf": "en-US-madison",
                "azure": "en-US-AriaNeural",
                "piper": "en_US-lessac-medium",
                "openai": "Speak with enthusiasm and energy! Be excited and upbeat."
            },
            "calm": {
                "kokoro": "en_male_2",
                "google": "en-US-Neural2-D",
                "elevenlabs": "ErXwobaYiN019PkySvjV",  # Antoni
                "murf": "en-US-daniel",
                "azure": "en-US-DavisNeural",
                "piper": "en_US-ljspeech-medium",
                "openai": "Speak in a calm, soothing voice like a mindfulness teacher. Use a serene, peaceful tone."
            },
            "customer_service": {
                "kokoro": "en_female_2",
                "google": "en-US-Neural2-F",
                "elevenlabs": "EXAVITQu4vr4xnSDxMaL",  # Bella
                "murf": "en-US-madison",
                "azure": "en-US-JennyNeural",
                "piper": "en_US-lessac-medium",
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
            "kokoro": {},
            "google": {
                "credentials_path": self.GOOGLE_CREDENTIALS_PATH,
                "project_id": self.GOOGLE_PROJECT_ID
            },
            "murf": {
                "api_key": self.MURF_API_KEY
            },
            "telnyx": {
                "api_key": self.TELNYX_API_KEY,
                "base_provider": "kokoro",
                "bucket_id": self.TELNYX_STORAGE_BUCKET_ID
            },
            "piper": {
                "piper_path": self.PIPER_PATH,
                "models_dir": self.PIPER_MODELS_DIR,
                "default_model": self.PIPER_DEFAULT_MODEL
            },
            "elevenlabs": {
                "api_key": self.ELEVENLABS_API_KEY,
                "model_id": self.ELEVENLABS_MODEL_ID
            },
            "azure": {
                "speech_key": self.AZURE_SPEECH_KEY,
                "service_region": self.AZURE_SPEECH_REGION
            },
            "openai": {
                "api_key": self.OPENAI_API_KEY,
                "model": self.OPENAI_TTS_MODEL,
                "voice_style": self.OPENAI_DEFAULT_VOICE_STYLE
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
        elif self.TTS_PROVIDER == 'elevenlabs':
            required_vars.append('ELEVENLABS_API_KEY')
        elif self.TTS_PROVIDER == 'murf':
            required_vars.append('MURF_API_KEY')
        elif self.TTS_PROVIDER == 'azure':
            required_vars.append('AZURE_SPEECH_KEY')
            required_vars.append('AZURE_SPEECH_REGION')
        
        # Add required keys for selected LLM type
        if self.LLM_TYPE == 'openai':
            required_vars.append('OPENAI_API_KEY')
        
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
            'ELEVENLABS_API_KEY',
            'MURF_API_KEY',
            'AZURE_SPEECH_KEY',
            'LLM_API_KEY',
            'MORNING_COFFEE_API_KEY'
        ]
        
        for key in sensitive_keys:
            if key in config_dict and config_dict[key]:
                config_dict[key] = '****'
        
        return config_dict


# Create singleton instance
config = Config()
