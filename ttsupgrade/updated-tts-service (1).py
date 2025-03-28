#!/usr/bin/env python
# Updated TTS Service Module with OpenAI Support

import logging
import json
import hashlib
import time
from typing import Dict, Any, Optional, List, Tuple

from .provider_factory import TTSProviderFactory
from .base_provider import BaseTTSProvider

logger = logging.getLogger("tts-service")

class TTSService:
    """
    TTS service that coordinates providers and Telnyx integration.
    
    This service manages TTS providers, handles caching, and integrates
    with Telnyx for audio playback in the Morning Coffee application.
    Updated to support OpenAI's new audio models.
    """
    
    def __init__(self, redis_client=None, telnyx_handler=None, 
                 config: Optional[Dict[str, Any]] = None):
        """
        Initialize the TTS service.
        
        Args:
            redis_client: Redis client for caching
            telnyx_handler: Telnyx handler for audio upload
            config (Optional[Dict[str, Any]]): Service configuration
        """
        self.redis_client = redis_client
        self.telnyx_handler = telnyx_handler
        self.config = config or {}
        
        # Get default provider type from config or use kokoro
        default_provider = self.config.get("default_provider", "kokoro")
        provider_config = self.config.get("provider_config", {}).get(default_provider, {})
        
        # Create default provider
        self.provider = TTSProviderFactory.create_provider(
            default_provider, redis_client, provider_config
        )
        
        # Cache settings
        self.cache_enabled = self.config.get("cache_enabled", True)
        self.cache_ttl = self.config.get("cache_ttl", 86400)  # 24 hours default
        
        # Voice mapping
        self.voice_mapping = self.config.get("voice_mapping", {})
        
        logger.info(f"TTS Service initialized with provider: {default_provider}")
        
        # Map of capabilities for each provider type
        self.provider_capabilities = {
            "kokoro": ["basic", "local"],
            "google": ["high_quality", "cloud"],
            "murf": ["emotional", "custom_voice"],
            "telnyx": ["basic", "cloud", "call_integration"],
            "piper": ["basic", "local", "offline"],
            "elevenlabs": ["high_quality", "emotional", "cloud"],
            "azure": ["high_quality", "cloud", "enterprise"],
            "openai": ["high_quality", "emotional", "cloud", "voice_style"]
        }
        
    def generate_speech(self, text: str, voice_id: Optional[str] = None,
                        speed: float = 1.0, use_cache: bool = True) -> Optional[bytes]:
        """
        Generate speech using current provider.
        
        Args:
            text (str): Text to convert to speech
            voice_id (Optional[str]): Voice identifier
            speed (float): Speech speed factor
            use_cache (bool): Whether to use cache
            
        Returns:
            Optional[bytes]: Audio data as bytes or None if generation failed
        """
        if not text:
            logger.warning("Empty text provided, skipping TTS generation")
            return None
        
        # Map voice ID if needed
        mapped_voice_id = self._map_voice_id(voice_id)
        
        # Check cache if enabled and requested
        cache_key = None
        if self.cache_enabled and use_cache and self.redis_client:
            cache_key = self._get_cache_key(text, mapped_voice_id, speed)
            cached_audio = self.redis_client.get(cache_key)
            if cached_audio:
                logger.debug(f"Cache hit for text: {text[:30]}...")
                return cached_audio
        
        # Generate speech with provider
        try:
            audio_data = self.provider.generate_speech(text, mapped_voice_id, speed)
            
            # Cache result if successful
            if audio_data and self.cache_enabled and cache_key and self.redis_client:
                self.redis_client.setex(cache_key, self.cache_ttl, audio_data)
                logger.debug(f"Cached audio for text: {text[:30]}...")
            
            return audio_data
        except Exception as e:
            logger.error(f"Error generating speech: {e}")
            return None
    
    def generate_and_upload(self, text: str, voice_id: Optional[str] = None,
                           speed: float = 1.0, use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """
        Generate speech and upload to Telnyx storage.
        
        Args:
            text (str): Text to convert to speech
            voice_id (Optional[str]): Voice identifier
            speed (float): Speech speed factor
            use_cache (bool): Whether to use cache
            
        Returns:
            Optional[Dict[str, Any]]: Upload information or None if failed
        """
        if not self.telnyx_handler:
            logger.error("Telnyx handler not available")
            return None
        
        # Generate speech
        audio_data = self.generate_speech(text, voice_id, speed, use_cache)
        if not audio_data:
            return None
        
        # Upload to Telnyx
        try:
            upload_result = self.telnyx_handler.upload_to_storage(file_data=audio_data)
            return upload_result
        except Exception as e:
            logger.error(f"Error uploading to Telnyx: {e}")
            return None
    
    def change_provider(self, provider_type: str,
                       provider_config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Change TTS provider dynamically.
        
        Args:
            provider_type (str): Type of provider to use
            provider_config (Optional[Dict[str, Any]]): Provider configuration
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get config from main config if not provided
            if provider_config is None:
                provider_config = self.config.get("provider_config", {}).get(provider_type, {})
            
            # Create new provider
            new_provider = TTSProviderFactory.create_provider(
                provider_type, self.redis_client, provider_config
            )
            
            # Replace current provider
            self.provider = new_provider
            logger.info(f"Changed TTS provider to: {provider_type}")
            return True
        except Exception as e:
            logger.error(f"Error changing provider to {provider_type}: {e}")
            return False
    
    def get_available_providers(self) -> List[str]:
        """
        Get list of available provider types.
        
        Returns:
            List[str]: List of available provider names
        """
        return TTSProviderFactory.get_available_providers()
    
    def get_available_voices(self, provider_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Get available voices for specified provider or current provider.
        
        Args:
            provider_type (Optional[str]): Provider type to query
            
        Returns:
            Dict[str, Any]: Dictionary of available voices
        """
        if provider_type:
            try:
                # Create temporary provider to get voices
                provider_config = self.config.get("provider_config", {}).get(provider_type, {})
                temp_provider = TTSProviderFactory.create_provider(
                    provider_type, self.redis_client, provider_config
                )
                return temp_provider.get_voices()
            except Exception as e:
                logger.error(f"Error getting voices for provider {provider_type}: {e}")
                return {"voices": {}, "error": str(e)}
        else:
            # Use current provider
            return self.provider.get_voices()
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check health status of the TTS service.
        
        Returns:
            Dict[str, Any]: Health status information
        """
        result = {
            "service": "tts",
            "provider": self.provider.__class__.__name__,
            "cache_enabled": self.cache_enabled,
            "cache_ttl": self.cache_ttl
        }
        
        # Check provider health
        try:
            provider_health = self.provider.health_check()
            result["provider_health"] = provider_health
            result["status"] = provider_health.get("status", "unknown")
        except Exception as e:
            result["provider_health"] = {"error": str(e)}
            result["status"] = "error"
        
        # Check Redis if available
        if self.redis_client:
            try:
                self.redis_client.ping()
                result["cache_status"] = "connected"
            except Exception as e:
                result["cache_status"] = f"error: {str(e)}"
        else:
            result["cache_status"] = "disabled"
        
        return result
    
    def clear_cache(self) -> int:
        """
        Clear the TTS cache.
        
        Returns:
            int: Number of cache entries cleared
        """
        if not self.redis_client:
            return 0
        
        try:
            # Get all keys matching the pattern
            pattern = "tts:cache:*"
            keys = self.redis_client.keys(pattern)
            
            if not keys:
                return 0
            
            # Delete all matching keys
            count = self.redis_client.delete(*keys)
            logger.info(f"Cleared {count} entries from TTS cache")
            return count
        except Exception as e:
            logger.error(f"Error clearing TTS cache: {e}")
            return 0
    
    def get_provider_capabilities(self, provider_type: Optional[str] = None) -> List[str]:
        """
        Get capabilities of a provider.
        
        Args:
            provider_type (Optional[str]): Provider type to query, or current if None
            
        Returns:
            List[str]: List of provider capabilities
        """
        if provider_type is None:
            provider_type = self.provider.__class__.__name__.lower().replace("provider", "")
        
        return self.provider_capabilities.get(provider_type, [])
    
    def supports_capability(self, capability: str, provider_type: Optional[str] = None) -> bool:
        """
        Check if a provider supports a specific capability.
        
        Args:
            capability (str): Capability to check
            provider_type (Optional[str]): Provider type to query, or current if None
            
        Returns:
            bool: True if supported, False otherwise
        """
        capabilities = self.get_provider_capabilities(provider_type)
        return capability in capabilities
    
    def get_provider_for_capability(self, capability: str) -> Optional[str]:
        """
        Get the first provider that supports a capability.
        
        Args:
            capability (str): Capability to find a provider for
            
        Returns:
            Optional[str]: Provider name or None if no provider found
        """
        for provider, capabilities in self.provider_capabilities.items():
            if capability in capabilities:
                return provider
        return None
    
    def generate_with_style(self, text: str, style: str, speed: float = 1.0) -> Optional[bytes]:
        """
        Generate speech with a specific voice style.
        
        This method specifically targets providers that support voice styling,
        such as OpenAI's gpt-4o-mini-tts, which allows natural language
        instructions for voice characteristics.
        
        Args:
            text (str): Text to convert to speech
            style (str): Voice style description (e.g., "speak like a pirate")
            speed (float): Speech speed factor
            
        Returns:
            Optional[bytes]: Audio data as bytes or None if generation failed
        """
        # Check if current provider supports voice_style capability
        current_provider_type = self.provider.__class__.__name__.lower().replace("provider", "")
        
        if "voice_style" in self.provider_capabilities.get(current_provider_type, []):
            # Current provider supports voice styling
            return self.provider.generate_speech(text, style, speed)
        else:
            # Try to find a provider that supports voice styling
            for provider_type, capabilities in self.provider_capabilities.items():
                if "voice_style" in capabilities:
                    logger.info(f"Switching to {provider_type} provider for voice styling")
                    
                    # Temporarily switch provider
                    original_provider = self.provider
                    provider_config = self.config.get("provider_config", {}).get(provider_type, {})
                    
                    try:
                        # Create and use the new provider
                        style_provider = TTSProviderFactory.create_provider(
                            provider_type, self.redis_client, provider_config
                        )
                        self.provider = style_provider
                        
                        # Generate speech with the style
                        result = self.provider.generate_speech(text, style, speed)
                        
                        # Reset to original provider
                        self.provider = original_provider
                        
                        return result
                    except Exception as e:
                        logger.error(f"Error using {provider_type} provider for voice styling: {e}")
                        # Reset to original provider
                        self.provider = original_provider
            
            # If we get here, no provider with voice_style capability was found or worked
            logger.warning("No provider with voice styling capability available")
            # Fall back to regular voice generation
            return self.generate_speech(text, None, speed)
    
    def _get_cache_key(self, text: str, voice_id: Optional[str], speed: float) -> str:
        """
        Generate cache key for TTS request.
        
        Args:
            text (str): Text to convert to speech
            voice_id (Optional[str]): Voice identifier
            speed (float): Speech speed factor
            
        Returns:
            str: Cache key
        """
        # Create a unique key based on text, voice, and speed
        key_parts = [text, str(voice_id or "default"), str(speed)]
        key_string = ":".join(key_parts)
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        
        # Add provider name to cache key to avoid collisions
        provider_name = self.provider.__class__.__name__.lower()
        return f"tts:cache:{provider_name}:{key_hash}"
    
    def _map_voice_id(self, voice_id: Optional[str]) -> Optional[str]:
        """
        Map application voice ID to provider-specific voice ID.
        
        Args:
            voice_id (Optional[str]): Application voice ID
            
        Returns:
            Optional[str]: Provider-specific voice ID
        """
        if not voice_id:
            return None
        
        # Get the current provider name
        provider_name = self.provider.__class__.__name__.lower().replace("provider", "")
        
        # Check if we have a mapping for this voice and provider
        mapping = self.voice_mapping.get(voice_id, {}).get(provider_name)
        
        if mapping:
            logger.debug(f"Mapped voice {voice_id} to {mapping} for provider {provider_name}")
            return mapping
        
        # If no mapping found, return the original voice ID
        return voice_id