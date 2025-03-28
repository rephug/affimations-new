#!/usr/bin/env python
# Updated Provider Factory Module for Morning Coffee TTS

import logging
from typing import Dict, Any, Optional, Type, List

from .base_provider import BaseTTSProvider
from .providers.kokoro_provider import KokoroProvider
from .providers.google_provider import GoogleProvider
from .providers.murf_provider import MurfProvider
from .providers.telnyx_provider import TelnyxProvider
from .providers.piper_provider import PiperProvider
from .providers.elevenlabs_provider import ElevenlabsProvider
from .providers.azure_provider import AzureProvider
from .providers.openai_provider import OpenAITTSProvider

logger = logging.getLogger("tts-factory")

class TTSProviderFactory:
    """Factory class for creating TTS provider instances."""
    
    # Registry of available providers
    _providers = {
        "kokoro": KokoroProvider,
        "google": GoogleProvider,
        "murf": MurfProvider,
        "telnyx": TelnyxProvider,
        "piper": PiperProvider,
        "elevenlabs": ElevenlabsProvider,
        "azure": AzureProvider,
        "openai": OpenAITTSProvider  # Add the new OpenAI provider
    }
    
    @classmethod
    def register_provider(cls, name: str, provider_class: Type[BaseTTSProvider]) -> None:
        """
        Register a new provider class.
        
        Args:
            name (str): Provider name
            provider_class (Type[BaseTTSProvider]): Provider class
        """
        cls._providers[name.lower()] = provider_class
        logger.info(f"Registered TTS provider: {name}")
    
    @classmethod
    def create_provider(cls, provider_type: str, redis_client=None, 
                        config: Optional[Dict[str, Any]] = None) -> BaseTTSProvider:
        """
        Create and return a TTS provider based on type.
        
        Args:
            provider_type (str): Type of provider to create
            redis_client: Redis client for caching (optional)
            config (Optional[Dict[str, Any]]): Provider configuration
            
        Returns:
            BaseTTSProvider: Instantiated provider
            
        Raises:
            ValueError: If provider type is unknown
        """
        config = config or {}
        provider_type = provider_type.lower()
        
        if provider_type not in cls._providers:
            available = ", ".join(cls._providers.keys())
            raise ValueError(f"Unknown provider type: {provider_type}. Available providers: {available}")
        
        provider_class = cls._providers[provider_type]
        
        # Pass redis_client if the provider supports it
        if "redis_client" in provider_class.__init__.__code__.co_varnames:
            provider = provider_class(redis_client=redis_client, **config)
        else:
            provider = provider_class(**config)
        
        logger.info(f"Created TTS provider: {provider_type}")
        return provider
    
    @classmethod
    def get_available_providers(cls) -> List[str]:
        """
        Get list of available provider types.
        
        Returns:
            List[str]: List of available provider names
        """
        return list(cls._providers.keys())
