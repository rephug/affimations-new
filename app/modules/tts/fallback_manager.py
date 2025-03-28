#!/usr/bin/env python
# TTS Fallback Manager for Morning Coffee application

import logging
import time
import threading
import random
from typing import Dict, Any, Optional, List, Callable, Tuple

from .provider_factory import TTSProviderFactory
from .base_provider import BaseTTSProvider, StreamingTTSProvider

logger = logging.getLogger("tts-fallback")

class ProviderStatus:
    """Status tracker for TTS provider health."""
    
    def __init__(self, provider_name: str, provider: BaseTTSProvider):
        """
        Initialize provider status.
        
        Args:
            provider_name: Name of the provider
            provider: Provider instance
        """
        self.provider_name = provider_name
        self.provider = provider
        self.is_healthy = True
        self.last_check_time = 0
        self.failure_count = 0
        self.last_error = None
        self.recovery_attempts = 0

class TTSFallbackManager:
    """
    Manager for TTS provider fallbacks.
    
    This class manages fallback between different TTS providers when the
    primary provider fails, handling health checks and automatic failover.
    """
    
    def __init__(self, 
                 primary_provider: str, 
                 fallback_providers: List[str],
                 provider_factory: Callable = None,
                 redis_client: Any = None,
                 provider_configs: Dict[str, Dict[str, Any]] = None,
                 health_check_interval: int = 300,
                 max_failures: int = 3,
                 auto_recovery: bool = True,
                 recovery_backoff_base: int = 30):
        """
        Initialize the fallback manager.
        
        Args:
            primary_provider: Name of the primary provider
            fallback_providers: List of fallback provider names in priority order
            provider_factory: Factory function to create providers (defaults to TTSProviderFactory)
            redis_client: Redis client for caching (optional)
            provider_configs: Configuration for each provider
            health_check_interval: Seconds between health checks
            max_failures: Maximum failures before provider is marked unhealthy
            auto_recovery: Whether to automatically try to recover primary provider
            recovery_backoff_base: Base seconds for exponential backoff on recovery attempts
        """
        self.primary_provider_name = primary_provider
        self.fallback_provider_names = fallback_providers
        self.redis_client = redis_client
        self.provider_configs = provider_configs or {}
        self.health_check_interval = health_check_interval
        self.max_failures = max_failures
        self.auto_recovery = auto_recovery
        self.recovery_backoff_base = recovery_backoff_base
        
        # Use the provided factory or default to TTSProviderFactory
        self.provider_factory = provider_factory or TTSProviderFactory.create_provider
        
        # Lock for thread safety
        self.lock = threading.RLock()
        
        # Provider tracking
        self.providers: Dict[str, ProviderStatus] = {}
        
        # Current active provider
        self.current_provider_name = primary_provider
        
        # Initialize providers
        self._initialize_providers()
        
        # Start health check thread if auto-recovery is enabled
        if self.auto_recovery:
            self._start_health_check_thread()
        
        # Stats
        self.stats = {
            "fallbacks": 0,
            "recoveries": 0,
            "health_checks": 0
        }
        
        logger.info(f"Fallback manager initialized with primary: {primary_provider}, " + 
                   f"fallbacks: {fallback_providers}")
    
    def _initialize_providers(self) -> None:
        """Initialize primary and fallback providers."""
        with self.lock:
            # Initialize primary provider
            self._create_provider(self.primary_provider_name)
            
            # Current provider is initially the primary
            self.current_provider_name = self.primary_provider_name
            
            # Initialize fallback providers
            for provider_name in self.fallback_provider_names:
                self._create_provider(provider_name)
    
    def _create_provider(self, provider_name: str) -> Optional[BaseTTSProvider]:
        """
        Create a provider instance.
        
        Args:
            provider_name: Provider name
            
        Returns:
            Provider instance or None if creation failed
        """
        try:
            # Get configuration for this provider
            config = self.provider_configs.get(provider_name, {})
            
            # Create provider using factory
            provider = self.provider_factory(
                provider_name, 
                self.redis_client, 
                config
            )
            
            # Create status object
            provider_status = ProviderStatus(provider_name, provider)
            self.providers[provider_name] = provider_status
            
            logger.info(f"Created provider: {provider_name}")
            return provider
        except Exception as e:
            logger.error(f"Failed to create provider {provider_name}: {e}")
            return None
    
    def get_provider(self) -> BaseTTSProvider:
        """
        Get current active provider.
        
        Returns:
            Current active provider instance
        """
        with self.lock:
            # Get current provider status
            provider_status = self.providers.get(self.current_provider_name)
            
            if not provider_status:
                # This shouldn't happen, but fallback to primary if it does
                self.current_provider_name = self.primary_provider_name
                provider_status = self.providers.get(self.primary_provider_name)
                
                if not provider_status:
                    # Critical error - no primary provider
                    logger.critical("No primary provider available!")
                    raise ValueError("No TTS provider available")
            
            return provider_status.provider
    
    def check_provider_health(self, provider_name: str) -> bool:
        """
        Check if a provider is healthy.
        
        Args:
            provider_name: Provider name to check
            
        Returns:
            True if provider is healthy, False otherwise
        """
        with self.lock:
            provider_status = self.providers.get(provider_name)
            if not provider_status:
                return False
            
            # Skip health check if we've checked recently
            if time.time() - provider_status.last_check_time < self.health_check_interval:
                return provider_status.is_healthy
            
            try:
                # Perform health check
                provider_status.last_check_time = time.time()
                self.stats["health_checks"] += 1
                
                # Get provider instance
                provider = provider_status.provider
                
                # Run health check
                health = provider.health_check()
                
                # Check health status
                is_healthy = health.get("status") in ["healthy", "ok"]
                provider_status.is_healthy = is_healthy
                
                if not is_healthy:
                    logger.warning(f"Provider {provider_name} reported unhealthy: {health}")
                    provider_status.failure_count += 1
                    provider_status.last_error = health.get("error", "Unknown error")
                else:
                    # Reset failure count on successful check
                    provider_status.failure_count = 0
                    provider_status.last_error = None
                
                return is_healthy
            except Exception as e:
                logger.error(f"Error checking health for provider {provider_name}: {e}")
                provider_status.is_healthy = False
                provider_status.failure_count += 1
                provider_status.last_error = str(e)
                return False
    
    def mark_provider_failure(self, provider_name: str, error: Optional[str] = None) -> None:
        """
        Mark a provider as failed.
        
        Args:
            provider_name: Provider name
            error: Optional error message
        """
        with self.lock:
            provider_status = self.providers.get(provider_name)
            if not provider_status:
                return
            
            provider_status.failure_count += 1
            provider_status.last_error = error
            
            # Mark unhealthy if too many failures
            if provider_status.failure_count >= self.max_failures:
                logger.warning(f"Provider {provider_name} marked unhealthy after {provider_status.failure_count} failures")
                provider_status.is_healthy = False
    
    def try_fallback(self, error: Optional[str] = None) -> Tuple[bool, BaseTTSProvider]:
        """
        Try to fall back to next provider.
        
        Args:
            error: Optional error message from the current provider
            
        Returns:
            Tuple of (success, provider) where success is True if fallback was successful
            and provider is the new provider instance
        """
        with self.lock:
            current_name = self.current_provider_name
            
            # Mark current provider as failed
            self.mark_provider_failure(current_name, error)
            
            # Try to find a healthy fallback provider
            fallback_candidates = self.fallback_provider_names.copy()
            
            # Add primary provider as last resort if current is not primary
            if current_name != self.primary_provider_name:
                fallback_candidates.append(self.primary_provider_name)
            
            # Filter out current provider
            fallback_candidates = [p for p in fallback_candidates if p != current_name]
            
            # Try each provider in order
            for provider_name in fallback_candidates:
                provider_status = self.providers.get(provider_name)
                
                if not provider_status:
                    continue
                
                # Check health if we haven't recently
                if time.time() - provider_status.last_check_time >= self.health_check_interval:
                    self.check_provider_health(provider_name)
                
                # Use this provider if it's healthy
                if provider_status.is_healthy:
                    self.current_provider_name = provider_name
                    self.stats["fallbacks"] += 1
                    
                    logger.info(f"Falling back from {current_name} to {provider_name}")
                    return True, provider_status.provider
            
            # No healthy providers found
            logger.error("No healthy providers available for fallback!")
            
            # Return current provider as fallback failed
            current_provider = self.providers.get(current_name).provider
            return False, current_provider
    
    def reset_to_primary(self) -> Tuple[bool, BaseTTSProvider]:
        """
        Reset to primary provider.
        
        Returns:
            Tuple of (success, provider) where success is True if reset was successful
            and provider is the new provider instance
        """
        with self.lock:
            if self.current_provider_name == self.primary_provider_name:
                # Already using primary
                return True, self.get_provider()
            
            # Check if primary is healthy
            primary_status = self.providers.get(self.primary_provider_name)
            if not primary_status:
                logger.error("Primary provider not found!")
                return False, self.get_provider()
            
            # Update health check
            is_healthy = self.check_provider_health(self.primary_provider_name)
            
            if is_healthy:
                # Reset to primary
                self.current_provider_name = self.primary_provider_name
                self.stats["recoveries"] += 1
                
                logger.info(f"Reset from {self.current_provider_name} to primary {self.primary_provider_name}")
                return True, primary_status.provider
            else:
                logger.warning(f"Cannot reset to primary provider {self.primary_provider_name}: not healthy")
                return False, self.get_provider()
    
    def _start_health_check_thread(self) -> None:
        """Start background thread for health checks and recovery."""
        def health_check_worker():
            """Worker function for health check thread."""
            while True:
                try:
                    # Sleep first to avoid immediate check
                    time.sleep(self.health_check_interval)
                    
                    with self.lock:
                        # Check health of all providers
                        for provider_name, provider_status in self.providers.items():
                            # Skip health check if we've checked recently
                            if time.time() - provider_status.last_check_time < self.health_check_interval:
                                continue
                            
                            # Perform health check
                            self.check_provider_health(provider_name)
                        
                        # Try to recover primary if not current and it's healthy
                        if (self.current_provider_name != self.primary_provider_name and
                            self.providers.get(self.primary_provider_name).is_healthy):
                            self.reset_to_primary()
                        
                        # Try to recover unhealthy providers with backoff
                        for provider_name, provider_status in self.providers.items():
                            if not provider_status.is_healthy:
                                # Apply exponential backoff
                                backoff = self.recovery_backoff_base * (2 ** provider_status.recovery_attempts)
                                
                                # Add some jitter to avoid thundering herd
                                backoff = backoff * (0.75 + 0.5 * random.random())
                                
                                # Check if it's time to retry
                                if time.time() - provider_status.last_check_time >= backoff:
                                    logger.info(f"Attempting recovery for {provider_name}")
                                    
                                    # Try to recreate the provider
                                    try:
                                        new_provider = self._create_provider(provider_name)
                                        if new_provider:
                                            # Check health of new instance
                                            health = new_provider.health_check()
                                            
                                            is_healthy = health.get("status") in ["healthy", "ok"]
                                            if is_healthy:
                                                provider_status.is_healthy = True
                                                provider_status.failure_count = 0
                                                provider_status.last_error = None
                                                provider_status.recovery_attempts = 0
                                                logger.info(f"Successfully recovered {provider_name}")
                                            else:
                                                provider_status.recovery_attempts += 1
                                                logger.warning(f"Recovery attempt for {provider_name} failed, will retry later")
                                    except Exception as e:
                                        provider_status.recovery_attempts += 1
                                        logger.error(f"Error attempting recovery for {provider_name}: {e}")
                
                except Exception as e:
                    logger.error(f"Error in health check thread: {e}")
        
        # Start the thread
        thread = threading.Thread(target=health_check_worker, daemon=True)
        thread.start()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics and status information.
        
        Returns:
            Dictionary with statistics and provider status
        """
        with self.lock:
            result = {
                "current_provider": self.current_provider_name,
                "primary_provider": self.primary_provider_name,
                "stats": self.stats.copy(),
                "providers": {}
            }
            
            # Add provider status
            for provider_name, provider_status in self.providers.items():
                result["providers"][provider_name] = {
                    "is_healthy": provider_status.is_healthy,
                    "failure_count": provider_status.failure_count,
                    "last_error": provider_status.last_error,
                    "last_check_time": provider_status.last_check_time,
                    "recovery_attempts": provider_status.recovery_attempts
                }
            
            return result 