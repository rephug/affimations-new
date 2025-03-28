#!/usr/bin/env python
# TTS Service Module with OpenAI Support and Fallback Support

import logging
import json
import hashlib
import time
from typing import Dict, Any, Optional, List, Tuple, Generator

from .provider_factory import TTSProviderFactory
from .base_provider import BaseTTSProvider, StreamingTTSProvider
from .fallback_manager import TTSFallbackManager
from .tasks import generate_speech_task, batch_generation_task, prewarm_task
from .events import TTSEvent, TTSEventType, TTSEventEmitter

logger = logging.getLogger("tts-service")

class TTSService:
    """
    TTS service that coordinates providers and Telnyx integration.
    
    This service manages TTS providers, handles caching, and integrates
    with Telnyx for audio playback in the Morning Coffee application.
    Updated to support OpenAI's new audio models and provider fallbacks.
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
        
        # Get default provider type from config or use openai
        default_provider = self.config.get("default_provider", "openai")
        fallback_providers = self.config.get("fallback_providers", [])
        provider_configs = self.config.get("provider_config", {})
        
        # Initialize fallback manager if fallback providers configured
        if fallback_providers:
            logger.info(f"Initializing with fallback providers: {fallback_providers}")
            self.fallback_manager = TTSFallbackManager(
                primary_provider=default_provider,
                fallback_providers=fallback_providers,
                redis_client=redis_client,
                provider_configs=provider_configs,
                health_check_interval=self.config.get("health_check_interval", 300),
                max_failures=self.config.get("max_failures", 3),
                auto_recovery=self.config.get("auto_recovery", True)
            )
            # Use provider from fallback manager
            self.provider = self.fallback_manager.get_provider()
        else:
            # No fallback, create single provider directly
            provider_config = provider_configs.get(default_provider, {})
            self.provider = TTSProviderFactory.create_provider(
                default_provider, redis_client, provider_config
            )
            self.fallback_manager = None
        
        # Cache settings
        self.cache_enabled = self.config.get("cache_enabled", True)
        self.cache_ttl = self.config.get("cache_ttl", 86400)  # 24 hours default
        
        # Voice mapping
        self.voice_mapping = self.config.get("voice_mapping", {})
        
        # Event emitter for TTS events
        self.events = TTSEventEmitter()
        
        # Initialize dialog manager if dialog config is present
        self.dialog_manager = None
        if self.config.get("dialog_enabled", True):
            self.initialize_dialog_manager()
        
        logger.info(f"TTS Service initialized with provider: {default_provider}")
        
        # Map of capabilities for each provider type
        self.provider_capabilities = {
            "openai": ["high_quality", "emotional", "cloud", "voice_style"]
        }
        
    def generate_speech(self, text: str, voice_id: Optional[str] = None,
                        speed: float = 1.0, use_cache: bool = True) -> Optional[bytes]:
        """
        Generate speech using current provider with fallback support.
        
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
        
        # Try with current provider
        try:
            # Generate speech with provider
            audio_data = self.provider.generate_speech(text, mapped_voice_id, speed)
            
            # Cache result if successful
            if audio_data and self.cache_enabled and cache_key and self.redis_client:
                self.redis_client.setex(cache_key, self.cache_ttl, audio_data)
                logger.debug(f"Cached audio for text: {text[:30]}...")
            
            return audio_data
        except Exception as e:
            logger.error(f"Error generating speech: {e}")
            
            # Try fallback if available
            if self.fallback_manager:
                logger.info("Attempting fallback to alternative provider")
                success, fallback_provider = self.fallback_manager.try_fallback(str(e))
                
                if success:
                    # Update provider reference
                    self.provider = fallback_provider
                    
                    try:
                        # Try with fallback provider
                        audio_data = self.provider.generate_speech(text, mapped_voice_id, speed)
                        
                        # Cache result if successful
                        if audio_data and self.cache_enabled and cache_key and self.redis_client:
                            self.redis_client.setex(cache_key, self.cache_ttl, audio_data)
                            logger.debug(f"Cached audio from fallback provider for text: {text[:30]}...")
                        
                        return audio_data
                    except Exception as fallback_error:
                        logger.error(f"Fallback provider also failed: {fallback_error}")
            
            return None
    
    def generate_speech_stream(self, text: str, voice_id: Optional[str] = None,
                             speed: float = 1.0) -> Generator[bytes, None, None]:
        """
        Generate speech as a stream with fallback support.
        
        Args:
            text (str): Text to convert to speech
            voice_id (Optional[str]): Voice identifier
            speed (float): Speech speed factor
            
        Returns:
            Generator[bytes, None, None]: Generator yielding audio chunks
            
        Raises:
            ValueError: If provider doesn't support streaming
        """
        # Map voice ID if needed
        mapped_voice_id = self._map_voice_id(voice_id)
        
        # Check if provider supports streaming
        if not isinstance(self.provider, StreamingTTSProvider):
            logger.error("Current provider doesn't support streaming")
            # Try to get a streaming-capable provider through fallback
            if self.fallback_manager:
                found_streaming_provider = False
                
                # Try each fallback provider to find one that supports streaming
                for provider_name in self.fallback_manager.fallback_provider_names:
                    try:
                        # Create provider
                        provider_config = self.config.get("provider_config", {}).get(provider_name, {})
                        provider = TTSProviderFactory.create_provider(
                            provider_name, self.redis_client, provider_config
                        )
                        
                        # Check if it supports streaming
                        if isinstance(provider, StreamingTTSProvider):
                            logger.info(f"Found streaming-capable provider: {provider_name}")
                            self.provider = provider
                            found_streaming_provider = True
                            break
                    except Exception as e:
                        logger.error(f"Error checking fallback provider {provider_name}: {e}")
                
                if not found_streaming_provider:
                    raise ValueError("No streaming-capable provider available")
            else:
                raise ValueError("Current provider doesn't support streaming and no fallbacks available")
        
        try:
            # Try with current provider
            for chunk in self.provider.generate_speech_stream(text, mapped_voice_id, speed):
                yield chunk
        except Exception as e:
            logger.error(f"Error in streaming speech generation: {e}")
            
            # Try fallback if available
            if self.fallback_manager:
                logger.info("Attempting fallback to alternative provider for streaming")
                success, fallback_provider = self.fallback_manager.try_fallback(str(e))
                
                if success and isinstance(fallback_provider, StreamingTTSProvider):
                    # Update provider reference
                    self.provider = fallback_provider
                    
                    try:
                        # Try with fallback provider
                        for chunk in self.provider.generate_speech_stream(text, mapped_voice_id, speed):
                            yield chunk
                        return
                    except Exception as fallback_error:
                        logger.error(f"Fallback provider also failed for streaming: {fallback_error}")
            
            # If we get here, all providers failed or none support streaming
            logger.error("All streaming providers failed")
            yield b""  # Empty chunk to avoid breaking generators
    
    def generate_with_style(self, text: str, style: str,
                          speed: float = 1.0, use_cache: bool = True) -> Optional[bytes]:
        """
        Generate speech with a specific voice style (for providers that support styling),
        with fallback support.
        
        Args:
            text (str): Text to convert to speech
            style (str): Voice style instruction (e.g., "Speak in a calm, soothing voice")
            speed (float): Speech speed factor
            use_cache (bool): Whether to use cache
            
        Returns:
            Optional[bytes]: Audio data as bytes or None if generation failed
        """
        if not self.supports_capability("voice_style"):
            logger.warning("Current provider does not support voice styling, using standard generation")
            return self.generate_speech(text, None, speed, use_cache)
        
        if not text:
            logger.warning("Empty text provided, skipping TTS generation")
            return None
        
        # Check cache if enabled and requested
        cache_key = None
        if self.cache_enabled and use_cache and self.redis_client:
            # Include style in cache key for styled voices
            cache_key = self._get_cache_key(text, style, speed)
            cached_audio = self.redis_client.get(cache_key)
            if cached_audio:
                logger.debug(f"Cache hit for styled text: {text[:30]}...")
                return cached_audio
        
        # Try with current provider
        try:
            # Use style as voice_id for OpenAI provider
            audio_data = self.provider.generate_speech(text, style, speed)
            
            # Cache result if successful
            if audio_data and self.cache_enabled and cache_key and self.redis_client:
                self.redis_client.setex(cache_key, self.cache_ttl, audio_data)
                logger.debug(f"Cached styled audio for text: {text[:30]}...")
            
            return audio_data
        except Exception as e:
            logger.error(f"Error generating styled speech: {e}")
            
            # Try fallback if available
            if self.fallback_manager:
                logger.info("Attempting fallback to alternative provider for styled speech")
                success, fallback_provider = self.fallback_manager.try_fallback(str(e))
                
                if success:
                    # Update provider reference
                    self.provider = fallback_provider
                    
                    # Check if fallback provider supports styling
                    if self.supports_capability("voice_style"):
                        try:
                            # Try with fallback provider
                            audio_data = self.provider.generate_speech(text, style, speed)
                            
                            # Cache result if successful
                            if audio_data and self.cache_enabled and cache_key and self.redis_client:
                                self.redis_client.setex(cache_key, self.cache_ttl, audio_data)
                                logger.debug(f"Cached styled audio from fallback for text: {text[:30]}...")
                            
                            return audio_data
                        except Exception as fallback_error:
                            logger.error(f"Fallback provider also failed for styled speech: {fallback_error}")
                    else:
                        logger.warning("Fallback provider doesn't support styling, using standard generation")
                        return self.generate_speech(text, None, speed, use_cache)
            
            return None
    
    def generate_and_upload(self, text: str, voice_id: Optional[str] = None,
                           speed: float = 1.0, use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """
        Generate speech and upload to Telnyx storage, with fallback support.
        
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
        
        # Generate speech with fallback support already built in
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
    
    def generate_styled_and_upload(self, text: str, style: str,
                                 speed: float = 1.0, use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """
        Generate styled speech and upload to Telnyx storage.
        
        Args:
            text (str): Text to convert to speech
            style (str): Voice style instruction
            speed (float): Speech speed factor
            use_cache (bool): Whether to use cache
            
        Returns:
            Optional[Dict[str, Any]]: Upload information or None if failed
        """
        if not self.telnyx_handler:
            logger.error("Telnyx handler not available")
            return None
        
        # Generate speech with style
        audio_data = self.generate_with_style(text, style, speed, use_cache)
        if not audio_data:
            return None
        
        # Upload to Telnyx
        try:
            upload_result = self.telnyx_handler.upload_to_storage(file_data=audio_data)
            return upload_result
        except Exception as e:
            logger.error(f"Error uploading styled speech to Telnyx: {e}")
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
            
            # Use fallback manager if available
            if self.fallback_manager:
                # Check if this is the primary provider
                if provider_type == self.fallback_manager.primary_provider_name:
                    success, provider = self.fallback_manager.reset_to_primary()
                    if success:
                        self.provider = provider
                        logger.info(f"Reset to primary provider: {provider_type}")
                        return True
                
                # Otherwise create provider directly
                new_provider = TTSProviderFactory.create_provider(
                    provider_type, self.redis_client, provider_config
                )
                
                # Replace current provider
                self.provider = new_provider
                logger.info(f"Changed TTS provider to: {provider_type}")
                return True
            else:
                # No fallback manager, create provider directly
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
        Check TTS service health.
        
        Returns:
            Dict[str, Any]: Health status
        """
        result = {
            "status": "ok",
            "timestamp": time.time(),
            "cache_enabled": self.cache_enabled
        }
        
        # Check current provider
        try:
            provider_health = self.provider.health_check()
            result["provider"] = {
                "type": self._get_provider_type(),
                "health": provider_health
            }
        except Exception as e:
            result["provider"] = {
                "type": self._get_provider_type(),
                "health": {"status": "error", "error": str(e)}
            }
            result["status"] = "degraded"
        
        # Add fallback manager status if available
        if self.fallback_manager:
            try:
                fallback_stats = self.fallback_manager.get_stats()
                result["fallback_manager"] = fallback_stats
                
                # Update overall status based on fallback health
                if fallback_stats["current_provider"] != fallback_stats["primary_provider"]:
                    result["status"] = "degraded"
            except Exception as e:
                result["fallback_manager"] = {"status": "error", "error": str(e)}
                result["status"] = "degraded"
        
        # Check cache if enabled
        if self.cache_enabled and self.redis_client:
            try:
                # Test redis connectivity
                self.redis_client.ping()
                result["cache"] = {"status": "ok"}
            except Exception as e:
                result["cache"] = {"status": "error", "error": str(e)}
                result["status"] = "degraded"
        else:
            result["cache"] = {"status": "disabled"}
        
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
            # Get pattern for TTS cache keys
            pattern = "tts:*"
            keys = self.redis_client.keys(pattern)
            
            if not keys:
                return 0
                
            # Delete all keys matching the pattern
            self.redis_client.delete(*keys)
            count = len(keys)
            
            logger.info(f"Cleared {count} TTS cache entries")
            return count
        except Exception as e:
            logger.error(f"Error clearing TTS cache: {e}")
            return 0
    
    def supports_capability(self, capability: str) -> bool:
        """
        Check if the current provider supports a specific capability.
        
        Args:
            capability (str): Capability to check
            
        Returns:
            bool: True if supported, False otherwise
        """
        provider_type = self._get_provider_type()
        capabilities = self.provider_capabilities.get(provider_type, [])
        return capability in capabilities
    
    def _get_provider_type(self) -> str:
        """
        Get the type of the current provider.
        
        Returns:
            str: Provider type
        """
        # Get provider type from class name
        provider_class = self.provider.__class__.__name__
        
        # Extract provider type from class name
        if provider_class.endswith("Provider"):
            provider_type = provider_class[:-8].lower()
        else:
            provider_type = provider_class.lower()
            
        return provider_type
    
    def _map_voice_id(self, voice_id: Optional[str]) -> Optional[str]:
        """
        Map voice ID using voice mapping configuration.
        
        Args:
            voice_id (Optional[str]): Voice identifier
            
        Returns:
            Optional[str]: Mapped voice ID
        """
        if not voice_id or not self.voice_mapping:
            return voice_id
            
        provider_type = self._get_provider_type()
        
        # Check if voice mapping exists for this voice and provider
        if voice_id in self.voice_mapping and provider_type in self.voice_mapping[voice_id]:
            mapped_voice = self.voice_mapping[voice_id][provider_type]
            logger.debug(f"Mapped voice {voice_id} to {mapped_voice} for {provider_type}")
            return mapped_voice
            
        return voice_id
    
    def _get_cache_key(self, text: str, voice_id: Optional[str], speed: float) -> str:
        """
        Generate cache key for TTS output.
        
        Args:
            text (str): Text to convert to speech
            voice_id (Optional[str]): Voice identifier or style
            speed (float): Speech speed factor
            
        Returns:
            str: Cache key
        """
        # Get provider type for cache key
        provider_type = self._get_provider_type()
        
        # Create hashable representation of params
        params = {
            "text": text,
            "voice_id": voice_id or "default",
            "speed": speed,
            "provider": provider_type
        }
        
        # Serialize params and hash
        params_str = json.dumps(params, sort_keys=True)
        hash_obj = hashlib.md5(params_str.encode())
        hash_hex = hash_obj.hexdigest()
        
        return f"tts:{hash_hex}"
    
    def get_fallback_stats(self) -> Optional[Dict[str, Any]]:
        """
        Get statistics from the fallback manager.
        
        Returns:
            Optional[Dict[str, Any]]: Fallback statistics or None if not available
        """
        if not self.fallback_manager:
            return None
        
        try:
            return self.fallback_manager.get_stats()
        except Exception as e:
            logger.error(f"Error getting fallback stats: {e}")
            return {"error": str(e)}
            
    def reset_to_primary_provider(self) -> bool:
        """
        Reset to the primary provider.
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.fallback_manager:
            logger.warning("No fallback manager available, cannot reset to primary")
            return False
        
        try:
            success, provider = self.fallback_manager.reset_to_primary()
            if success:
                self.provider = provider
                logger.info("Reset to primary provider")
            else:
                logger.warning("Failed to reset to primary provider")
            return success
        except Exception as e:
            logger.error(f"Error resetting to primary provider: {e}")
            return False
    
    def generate_speech_async(self, text: str, voice_id: Optional[str] = None,
                             speed: float = 1.0, use_cache: bool = True) -> str:
        """
        Generate speech asynchronously using Celery tasks.
        
        Args:
            text (str): Text to convert to speech
            voice_id (Optional[str]): Voice identifier
            speed (float): Speech speed factor
            use_cache (bool): Whether to use cache
            
        Returns:
            str: Task ID for tracking the async operation
        """
        if not text:
            logger.warning("Empty text provided, skipping async TTS generation")
            return None
        
        # Map voice ID if needed
        mapped_voice_id = self._map_voice_id(voice_id)
        
        # Get current provider config
        provider_type = self._get_provider_type()
        provider_config = self.config.get("provider_config", {}).get(provider_type, {})
        
        # Submit task to Celery
        task = generate_speech_task.delay(
            text=text,
            provider_type=provider_type,
            provider_config=provider_config,
            voice_id=mapped_voice_id,
            speed=speed,
            use_cache=use_cache
        )
        
        logger.debug(f"Submitted async TTS task {task.id} for text: {text[:30]}...")
        return task.id
    
    def batch_generate_async(self, texts: List[str], voice_id: Optional[str] = None,
                            speed: float = 1.0, use_cache: bool = True) -> str:
        """
        Generate speech for multiple texts asynchronously.
        
        Args:
            texts (List[str]): List of texts to convert to speech
            voice_id (Optional[str]): Voice identifier
            speed (float): Speech speed factor
            use_cache (bool): Whether to use cache
            
        Returns:
            str: Task ID for tracking the async operation
        """
        if not texts:
            logger.warning("Empty text list provided, skipping async batch generation")
            return None
        
        # Map voice ID if needed
        mapped_voice_id = self._map_voice_id(voice_id)
        
        # Get current provider config
        provider_type = self._get_provider_type()
        provider_config = self.config.get("provider_config", {}).get(provider_type, {})
        
        # Submit task to Celery
        task = batch_generation_task.delay(
            texts=texts,
            provider_type=provider_type,
            provider_config=provider_config,
            voice_id=mapped_voice_id,
            speed=speed,
            use_cache=use_cache
        )
        
        logger.debug(f"Submitted async batch TTS task {task.id} for {len(texts)} texts")
        return task.id
    
    def get_task_result(self, task_id: str, wait: bool = False, 
                       timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        Get the result of an async TTS task.
        
        Args:
            task_id (str): Task ID returned from async generation methods
            wait (bool): Whether to wait for task completion
            timeout (Optional[int]): Maximum time to wait in seconds
            
        Returns:
            Dict[str, Any]: Task result information including status and data if available
        """
        from celery.result import AsyncResult
        
        task = AsyncResult(task_id)
        
        if wait and not task.ready():
            try:
                # Wait for task to complete with timeout
                task.get(timeout=timeout)
            except Exception as e:
                logger.error(f"Error waiting for task {task_id}: {e}")
        
        result = {
            "task_id": task_id,
            "status": task.status,
            "ready": task.ready()
        }
        
        if task.failed():
            result["error"] = str(task.result)
        elif task.successful():
            result["result_available"] = True
            # Don't include actual audio data in status response for size reasons
            if isinstance(task.result, bytes):
                result["data_size"] = len(task.result)
            elif isinstance(task.result, dict):
                result["item_count"] = len(task.result)
        
        return result
    
    def get_task_audio(self, task_id: str, wait: bool = False,
                      timeout: Optional[int] = None) -> Optional[bytes]:
        """
        Get audio data from an async TTS task.
        
        Args:
            task_id (str): Task ID returned from generate_speech_async
            wait (bool): Whether to wait for task completion
            timeout (Optional[int]): Maximum time to wait in seconds
            
        Returns:
            Optional[bytes]: Audio data if available
        """
        from celery.result import AsyncResult
        
        task = AsyncResult(task_id)
        
        if wait and not task.ready():
            try:
                # Wait for task to complete with timeout
                task.get(timeout=timeout)
            except Exception as e:
                logger.error(f"Error waiting for task {task_id}: {e}")
                return None
        
        if not task.ready():
            logger.warning(f"Task {task_id} not ready yet")
            return None
        
        if task.failed():
            logger.error(f"Task {task_id} failed: {task.result}")
            return None
        
        result = task.result
        if isinstance(result, bytes):
            return result
        
        logger.error(f"Task {task_id} result is not audio data")
        return None
    
    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel an async TTS task if possible.
        
        Args:
            task_id (str): Task ID to cancel
            
        Returns:
            bool: True if cancelled, False otherwise
        """
        from celery.result import AsyncResult
        
        task = AsyncResult(task_id)
        
        if task.ready():
            logger.warning(f"Task {task_id} already completed, cannot cancel")
            return False
        
        try:
            task.revoke(terminate=True)
            logger.info(f"Cancelled task {task_id}")
            return True
        except Exception as e:
            logger.error(f"Error cancelling task {task_id}: {e}")
            return False
    
    def prewarm_cache(self, phrases: List[str], voices: List[str] = None) -> str:
        """
        Prewarm TTS cache with common phrases.
        
        Args:
            phrases (List[str]): List of phrases to generate
            voices (List[str]): List of voice IDs to use
            
        Returns:
            str: Task ID for tracking the prewarming operation
        """
        if not phrases:
            logger.warning("No phrases provided for prewarming")
            return None
        
        # Get current provider type
        provider_type = self._get_provider_type()
        
        # Get available provider types
        if self.fallback_manager:
            provider_types = [self.fallback_manager.primary_provider_name] + \
                             self.fallback_manager.fallback_provider_names
        else:
            provider_types = [provider_type]
        
        # Create voice mapping
        voice_ids = {}
        if voices:
            for provider in provider_types:
                voice_ids[provider] = [
                    self._map_voice_id_for_provider(voice, provider) 
                    for voice in voices
                ]
        
        # Submit prewarming task
        task = prewarm_task.delay(
            common_phrases=phrases,
            provider_types=provider_types,
            voice_ids=voice_ids
        )
        
        logger.info(f"Submitted prewarming task {task.id} for {len(phrases)} phrases")
        return task.id
    
    def _map_voice_id_for_provider(self, voice_id: str, provider_type: str) -> str:
        """
        Map voice ID for a specific provider.
        
        Args:
            voice_id (str): Voice identifier
            provider_type (str): Provider type
            
        Returns:
            str: Mapped voice ID for the provider
        """
        if not voice_id or not self.voice_mapping:
            return voice_id
        
        # Check if voice mapping exists for this voice and provider
        if voice_id in self.voice_mapping and provider_type in self.voice_mapping[voice_id]:
            mapped_voice = self.voice_mapping[voice_id][provider_type]
            return mapped_voice
            
        return voice_id
    
    def initialize_dialog_manager(self):
        """
        Initialize the dialog manager with configured settings.
        
        This creates a DialogManager instance with settings from the config.
        """
        from .dialog_manager import DialogManager
        
        # Get dialog settings from config
        dialog_config = self.config.get("dialog", {})
        
        # Create dialog manager with settings from config or defaults
        self.dialog_manager = DialogManager(
            min_fragment_size=dialog_config.get("min_fragment_size", 5),
            inter_sentence_pause_ms=dialog_config.get("inter_sentence_pause_ms", 300),
            initial_fragment_length=dialog_config.get("initial_fragment_length", 15),
            end_of_turn_pause_ms=dialog_config.get("end_of_turn_pause_ms", 800),
            punctuation_pause_ms=dialog_config.get("punctuation_pause_ms", None)
        )
        
        logger.info("Dialog manager initialized with configured settings")
    
    def generate_dialog_speech_stream(self, text: str, voice_id: Optional[str] = None,
                                     speed: float = 1.0, urgency: float = 0.0,
                                     context: Optional[Dict[str, Any]] = None,
                                     turn_id: Optional[str] = None) -> Generator[bytes, None, None]:
        """
        Generate speech stream optimized for dialog with natural pauses and turn-taking.
        
        This method uses the DialogManager to process text into conversation-optimized
        fragments with appropriate pauses. It includes optimizations for initial response
        latency and natural dialog flow.
        
        Args:
            text (str): Dialog text to convert to speech
            voice_id (Optional[str]): Voice identifier
            speed (float): Speech speed factor
            urgency (float): Urgency factor (0.0-1.0) that reduces pauses for urgent messages
            context (Optional[Dict[str, Any]]): Additional context for the dialog turn
            turn_id (Optional[str]): Unique ID for this dialog turn
            
        Returns:
            Generator[bytes, None, None]: Generator yielding audio chunks
            
        Raises:
            ValueError: If no suitable provider is available
        """
        # Initialize dialog manager if not already done
        if not self.dialog_manager:
            self.initialize_dialog_manager()
        
        # Map voice ID if needed
        mapped_voice_id = self._map_voice_id(voice_id)
        
        # Emit dialog turn start event
        self.events.emit(TTSEvent(
            TTSEventType.DIALOG_TURN_START,
            {"text": text, "turn_id": turn_id, "voice_id": mapped_voice_id}
        ))
        
        start_time = time.time()
        total_fragments = 0
        audio_generated = False
        
        # Check if provider supports streaming
        if not isinstance(self.provider, StreamingTTSProvider):
            logger.warning("Current provider doesn't support streaming for dialog")
            
            # Try to find a streaming provider via fallback
            if self.fallback_manager:
                found_streaming_provider = False
                
                # Try each fallback provider
                for provider_name in self.fallback_manager.fallback_provider_names:
                    try:
                        provider_config = self.config.get("provider_config", {}).get(provider_name, {})
                        provider = TTSProviderFactory.create_provider(
                            provider_name, self.redis_client, provider_config
                        )
                        
                        if isinstance(provider, StreamingTTSProvider):
                            logger.info(f"Found streaming provider for dialog: {provider_name}")
                            self.provider = provider
                            found_streaming_provider = True
                            break
                    except Exception as e:
                        logger.error(f"Error checking provider {provider_name} for dialog: {e}")
                
                if not found_streaming_provider:
                    raise ValueError("No streaming-capable provider available for dialog")
            else:
                raise ValueError("Current provider doesn't support streaming and no fallbacks available")
        
        try:
            # Process the dialog turn into fragments with appropriate timing
            for fragment_info in self.dialog_manager.process_dialog_turn(
                text, turn_id=turn_id, context=context, urgency=urgency
            ):
                # Skip final marker
                if fragment_info.get("turn_complete", False):
                    # Emit dialog turn end event
                    self.events.emit(TTSEvent(
                        TTSEventType.DIALOG_TURN_END,
                        {
                            "turn_id": turn_id,
                            "fragment_count": fragment_info.get("fragment_count", total_fragments),
                            "duration": fragment_info.get("turn_duration", time.time() - start_time)
                        }
                    ))
                    continue
                
                fragment_text = fragment_info.get("fragment", "")
                if not fragment_text:
                    continue
                
                total_fragments += 1
                
                # Emit fragment processing event
                self.events.emit(TTSEvent(
                    TTSEventType.FRAGMENT_PROCESSING,
                    {
                        "fragment": fragment_text,
                        "index": fragment_info.get("index", 0),
                        "turn_id": fragment_info.get("turn_id", turn_id)
                    }
                ))
                
                # Generate audio for this fragment
                try:
                    # For first fragment, emit first response event
                    if total_fragments == 1:
                        first_fragment_start = time.time()
                        
                    chunk_count = 0
                    for audio_chunk in self.provider.generate_speech_stream(fragment_text, mapped_voice_id, speed):
                        # For first fragment, first chunk, emit first response latency event
                        if total_fragments == 1 and chunk_count == 0:
                            first_response_latency = time.time() - first_fragment_start
                            self.events.emit(TTSEvent(
                                TTSEventType.FIRST_RESPONSE_LATENCY,
                                {"latency_sec": first_response_latency, "turn_id": turn_id}
                            ))
                        
                        chunk_count += 1
                        audio_generated = True
                        
                        # Emit audio chunk event
                        self.events.emit(TTSEvent(
                            TTSEventType.AUDIO_CHUNK_GENERATED,
                            {"size": len(audio_chunk), "fragment_index": fragment_info.get("index", 0)}
                        ))
                        
                        yield audio_chunk
                    
                    # Apply natural pause if specified
                    pause_ms = fragment_info.get("pause_after_ms", 0)
                    if pause_ms > 0:
                        # Emit pause event
                        self.events.emit(TTSEvent(
                            TTSEventType.DIALOG_PAUSE,
                            {"duration_ms": pause_ms, "turn_id": turn_id}
                        ))
                        
                        # Actually pause for the specified time
                        time.sleep(pause_ms / 1000.0)
                    
                except Exception as fragment_error:
                    logger.error(f"Error generating speech for fragment: {fragment_error}")
                    
                    # Try fallback for this fragment if available
                    if self.fallback_manager:
                        logger.info(f"Attempting fallback for dialog fragment: {fragment_text[:30]}...")
                        success, fallback_provider = self.fallback_manager.try_fallback(str(fragment_error))
                        
                        if success and isinstance(fallback_provider, StreamingTTSProvider):
                            self.provider = fallback_provider
                            
                            try:
                                # Try with fallback provider
                                for audio_chunk in self.provider.generate_speech_stream(
                                    fragment_text, mapped_voice_id, speed
                                ):
                                    audio_generated = True
                                    yield audio_chunk
                                
                                # Apply pause if specified
                                pause_ms = fragment_info.get("pause_after_ms", 0)
                                if pause_ms > 0:
                                    time.sleep(pause_ms / 1000.0)
                                
                            except Exception as fallback_fragment_error:
                                logger.error(f"Fallback also failed for fragment: {fallback_fragment_error}")
                                # Continue to next fragment rather than failing completely
            
            # If no audio was generated, yield empty bytes to avoid breaking the generator
            if not audio_generated:
                logger.warning("No audio generated for any fragments in dialog turn")
                yield b""
            
        except Exception as e:
            logger.error(f"Error in dialog speech generation: {e}")
            
            # Emit error event
            self.events.emit(TTSEvent(
                TTSEventType.ERROR,
                {"error": str(e), "turn_id": turn_id}
            ))
            
            # Yield empty bytes to avoid breaking the generator
            yield b"" 