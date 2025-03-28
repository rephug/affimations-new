#!/usr/bin/env python
# Voice Provider Pool Management

import logging
import threading
import time
import uuid
from typing import Dict, List, Set, Any, Optional, Tuple, Type, Union, TypeVar
from enum import Enum
import queue
from datetime import datetime, timedelta
import copy
import statistics

# Local imports
from .base_provider import BaseTTSProvider, StreamingTTSProvider
from .events import TTSEventEmitter, TTSEventType

logger = logging.getLogger("tts-voice-pool")

# Type for any TTS provider
ProviderT = TypeVar('ProviderT', bound=BaseTTSProvider)


class ProviderStatus(Enum):
    """Possible status values for a provider in the pool."""
    INITIALIZING = "initializing"  # Provider is being created
    AVAILABLE = "available"        # Provider is available for use
    IN_USE = "in_use"              # Provider is currently in use
    COOLING_DOWN = "cooling_down"  # Provider is in cool-down period
    ERROR = "error"                # Provider has encountered an error
    TERMINATED = "terminated"      # Provider has been terminated


class PooledProvider:
    """Wrapper for a TTS provider in the pool."""
    
    def __init__(self, provider: BaseTTSProvider, provider_type: str, voice_id: str, 
                 ttl: int = 3600):
        """
        Initialize a pooled provider.
        
        Args:
            provider: The TTS provider instance
            provider_type: Type identifier for the provider
            voice_id: Voice identifier
            ttl: Time-to-live in seconds
        """
        self.id = str(uuid.uuid4())
        self.provider = provider
        self.provider_type = provider_type
        self.voice_id = voice_id
        self.ttl = ttl
        
        self.status = ProviderStatus.INITIALIZING
        self.created_at = time.time()
        self.last_used_at = None
        self.usage_count = 0
        self.error_count = 0
        self.total_processing_time = 0
        
        # For tracking streaming sessions
        self.current_session_id = None
        self.session_start_time = None
    
    def mark_available(self) -> None:
        """Mark the provider as available."""
        self.status = ProviderStatus.AVAILABLE
    
    def mark_in_use(self) -> None:
        """Mark the provider as being in use."""
        self.status = ProviderStatus.IN_USE
        self.last_used_at = time.time()
        self.usage_count += 1
        self.session_start_time = time.time()
    
    def mark_cooling_down(self) -> None:
        """Mark the provider as in cooling down period."""
        self.status = ProviderStatus.COOLING_DOWN
        
        # Track processing time if in a session
        if self.session_start_time is not None:
            self.total_processing_time += time.time() - self.session_start_time
            self.session_start_time = None
            self.current_session_id = None
    
    def mark_error(self) -> None:
        """Mark the provider as having an error."""
        self.status = ProviderStatus.ERROR
        self.error_count += 1
        
        # Reset session tracking
        self.session_start_time = None
        self.current_session_id = None
    
    def mark_terminated(self) -> None:
        """Mark the provider as terminated."""
        self.status = ProviderStatus.TERMINATED
        
        # Reset session tracking
        self.session_start_time = None
        self.current_session_id = None
    
    def is_expired(self) -> bool:
        """Check if the provider has exceeded its TTL."""
        if self.last_used_at is None:
            # Use creation time if never used
            return (time.time() - self.created_at) > self.ttl
        
        return (time.time() - self.last_used_at) > self.ttl
    
    def start_session(self, session_id: str) -> None:
        """
        Track the start of a streaming session.
        
        Args:
            session_id: Unique session identifier
        """
        self.current_session_id = session_id
        self.session_start_time = time.time()
    
    def end_session(self) -> float:
        """
        End a streaming session and return its duration.
        
        Returns:
            Session duration in seconds
        """
        duration = 0
        if self.session_start_time is not None:
            duration = time.time() - self.session_start_time
            self.total_processing_time += duration
            self.session_start_time = None
            self.current_session_id = None
        
        return duration
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics for this provider.
        
        Returns:
            Dictionary of provider statistics
        """
        current_age = time.time() - self.created_at
        
        stats = {
            "id": self.id,
            "provider_type": self.provider_type,
            "voice_id": self.voice_id,
            "status": self.status.value,
            "age_seconds": current_age,
            "ttl_seconds": self.ttl,
            "usage_count": self.usage_count,
            "error_count": self.error_count,
            "total_processing_time": self.total_processing_time,
            "avg_processing_time": self.total_processing_time / max(1, self.usage_count),
            "in_session": self.current_session_id is not None
        }
        
        if self.last_used_at:
            stats["idle_time"] = time.time() - self.last_used_at
        
        return stats


class PoolConfiguration:
    """Configuration for a provider pool."""
    
    def __init__(self, 
                 provider_type: str,
                 voice_id: str,
                 min_size: int = 1,
                 max_size: int = 5,
                 ttl: int = 3600,
                 warm_up_count: int = 1,
                 cool_down_seconds: int = 5,
                 scaling_threshold: float = 0.7,
                 provider_factory=None,
                 provider_args: Dict[str, Any] = None):
        """
        Initialize pool configuration.
        
        Args:
            provider_type: Type identifier for the provider
            voice_id: Voice identifier
            min_size: Minimum number of providers in the pool
            max_size: Maximum number of providers in the pool
            ttl: Time-to-live in seconds
            warm_up_count: Number of providers to initialize at startup
            cool_down_seconds: Cool-down period after a provider is used
            scaling_threshold: Usage threshold for scaling up (0.0-1.0)
            provider_factory: Function to create new providers
            provider_args: Additional arguments for the provider factory
        """
        self.provider_type = provider_type
        self.voice_id = voice_id
        self.min_size = min_size
        self.max_size = max_size
        self.ttl = ttl
        self.warm_up_count = warm_up_count
        self.cool_down_seconds = cool_down_seconds
        self.scaling_threshold = scaling_threshold
        self.provider_factory = provider_factory
        self.provider_args = provider_args or {}
    
    def get_pool_key(self) -> str:
        """
        Get unique key for this pool configuration.
        
        Returns:
            Pool key string
        """
        return f"{self.provider_type}_{self.voice_id}"
    
    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> 'PoolConfiguration':
        """
        Create a pool configuration from a dictionary.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Pool configuration object
        """
        return cls(
            provider_type=config["provider_type"],
            voice_id=config["voice_id"],
            min_size=config.get("min_size", 1),
            max_size=config.get("max_size", 5),
            ttl=config.get("ttl", 3600),
            warm_up_count=config.get("warm_up_count", 1),
            cool_down_seconds=config.get("cool_down_seconds", 5),
            scaling_threshold=config.get("scaling_threshold", 0.7),
            provider_args=config.get("provider_args", {})
        )


class ProviderPool:
    """Manages a pool of providers with the same type and voice."""
    
    def __init__(self, config: PoolConfiguration, event_emitter: Optional[TTSEventEmitter] = None):
        """
        Initialize a provider pool.
        
        Args:
            config: Pool configuration
            event_emitter: Event emitter for notifications
        """
        self.config = config
        self.event_emitter = event_emitter
        
        # Track all providers
        self.providers: Dict[str, PooledProvider] = {}
        
        # Separate tracking by status for quick access
        self.available_providers: Set[str] = set()
        self.in_use_providers: Set[str] = set()
        self.cooling_providers: Set[str] = set()
        self.error_providers: Set[str] = set()
        
        # Thread safety
        self.lock = threading.RLock()
        
        # Warm up the pool with initial providers
        self._initialize_pool()
        
        # Start maintenance thread
        self._shutdown = threading.Event()
        self._maintenance_thread = threading.Thread(
            target=self._maintenance_loop,
            daemon=True,
            name=f"pool-{config.provider_type}-{config.voice_id}"
        )
        self._maintenance_thread.start()
        
        # Pool stats
        self.request_count = 0
        self.checkout_count = 0
        self.checkout_failures = 0
        self.creation_failures = 0
        self.provider_errors = 0
        self.pool_expansions = 0
        self.pool_contractions = 0
        self.checkout_times: List[float] = []
    
    def _initialize_pool(self) -> None:
        """Initialize the pool with warm-up providers."""
        for _ in range(self.config.warm_up_count):
            self._create_provider()
    
    def _create_provider(self) -> Optional[str]:
        """
        Create a new provider and add it to the pool.
        
        Returns:
            Provider ID or None if creation failed
        """
        if not self.config.provider_factory:
            logger.error(f"Cannot create provider: no factory for {self.config.provider_type}")
            return None
        
        try:
            # Create the provider
            provider = self.config.provider_factory(
                voice_id=self.config.voice_id,
                **self.config.provider_args
            )
            
            pooled_provider = PooledProvider(
                provider=provider,
                provider_type=self.config.provider_type,
                voice_id=self.config.voice_id,
                ttl=self.config.ttl
            )
            
            with self.lock:
                self.providers[pooled_provider.id] = pooled_provider
                
                # Check provider health before marking as available
                try:
                    if hasattr(provider, 'is_healthy') and callable(provider.is_healthy):
                        health_check = provider.is_healthy()
                        if not health_check:
                            logger.warning(f"Provider {pooled_provider.id} failed health check")
                            pooled_provider.mark_error()
                            self.error_providers.add(pooled_provider.id)
                            self.provider_errors += 1
                            return None
                    
                    # Mark as available
                    pooled_provider.mark_available()
                    self.available_providers.add(pooled_provider.id)
                    
                    if self.event_emitter:
                        self.event_emitter.emit(
                            TTSEventType.INFO,
                            f"Created provider {pooled_provider.id} for {self.config.provider_type}/{self.config.voice_id}"
                        )
                    
                    logger.info(f"Created provider {pooled_provider.id} for {self.config.provider_type}/{self.config.voice_id}")
                    return pooled_provider.id
                
                except Exception as e:
                    logger.error(f"Error initializing provider: {e}")
                    pooled_provider.mark_error()
                    self.error_providers.add(pooled_provider.id)
                    self.provider_errors += 1
                    self.creation_failures += 1
                    return None
        
        except Exception as e:
            logger.error(f"Error creating provider: {e}")
            self.creation_failures += 1
            return None
    
    def checkout_provider(self) -> Optional[Tuple[str, BaseTTSProvider]]:
        """
        Get an available provider from the pool.
        
        Returns:
            Tuple of (provider_id, provider) or None if no provider available
        """
        start_time = time.time()
        self.request_count += 1
        
        with self.lock:
            # First try to get an available provider
            if self.available_providers:
                provider_id = next(iter(self.available_providers))
                provider = self.providers[provider_id]
                
                # Update provider status
                provider.mark_in_use()
                self.available_providers.remove(provider_id)
                self.in_use_providers.add(provider_id)
                
                self.checkout_count += 1
                checkout_time = time.time() - start_time
                self.checkout_times.append(checkout_time)
                
                return provider_id, provider.provider
            
            # If no available providers, try to create one if under max size
            if len(self.providers) < self.config.max_size:
                self.pool_expansions += 1
                provider_id = self._create_provider()
                
                if provider_id:
                    provider = self.providers[provider_id]
                    
                    # Update provider status
                    provider.mark_in_use()
                    self.available_providers.remove(provider_id)
                    self.in_use_providers.add(provider_id)
                    
                    self.checkout_count += 1
                    checkout_time = time.time() - start_time
                    self.checkout_times.append(checkout_time)
                    
                    return provider_id, provider.provider
            
            # Could not provide a provider
            self.checkout_failures += 1
            return None
    
    def return_provider(self, provider_id: str, error: bool = False) -> bool:
        """
        Return a provider to the pool.
        
        Args:
            provider_id: Provider ID to return
            error: Whether the provider encountered an error
            
        Returns:
            Success status
        """
        with self.lock:
            if provider_id not in self.providers:
                logger.warning(f"Attempted to return unknown provider: {provider_id}")
                return False
            
            provider = self.providers[provider_id]
            
            # Remove from in-use set
            if provider_id in self.in_use_providers:
                self.in_use_providers.remove(provider_id)
            
            if error:
                # Mark with error
                provider.mark_error()
                self.error_providers.add(provider_id)
                self.provider_errors += 1
                
                # End any active session
                if provider.current_session_id:
                    provider.end_session()
                
                return True
            
            # End any active session
            if provider.current_session_id:
                provider.end_session()
            
            # Put in cooling down state initially
            provider.mark_cooling_down()
            self.cooling_providers.add(provider_id)
            
            # Schedule transition to available after cool-down
            threading.Timer(
                self.config.cool_down_seconds,
                self._activate_after_cooldown,
                args=[provider_id]
            ).start()
            
            return True
    
    def _activate_after_cooldown(self, provider_id: str) -> None:
        """
        Transition a provider from cooling to available.
        
        Args:
            provider_id: Provider ID
        """
        with self.lock:
            if provider_id not in self.providers:
                return
            
            provider = self.providers[provider_id]
            
            # Skip if provider is not in cooling state
            if provider.status != ProviderStatus.COOLING_DOWN:
                return
            
            # Skip if provider has expired
            if provider.is_expired():
                self._terminate_provider(provider_id)
                return
            
            # Transition to available
            if provider_id in self.cooling_providers:
                self.cooling_providers.remove(provider_id)
            
            provider.mark_available()
            self.available_providers.add(provider_id)
    
    def _terminate_provider(self, provider_id: str) -> None:
        """
        Terminate and remove a provider from the pool.
        
        Args:
            provider_id: Provider ID
        """
        with self.lock:
            if provider_id not in self.providers:
                return
            
            provider = self.providers[provider_id]
            
            # Remove from status sets
            for status_set in [self.available_providers, self.in_use_providers, 
                              self.cooling_providers, self.error_providers]:
                if provider_id in status_set:
                    status_set.remove(provider_id)
            
            # Mark as terminated
            provider.mark_terminated()
            
            # Clean up provider resources if possible
            try:
                if hasattr(provider.provider, 'cleanup') and callable(provider.provider.cleanup):
                    provider.provider.cleanup()
            except Exception as e:
                logger.error(f"Error during provider cleanup: {e}")
            
            # Remove from pool
            del self.providers[provider_id]
            self.pool_contractions += 1
            
            logger.info(f"Terminated provider {provider_id}")
    
    def start_streaming_session(self, provider_id: str, session_id: str) -> bool:
        """
        Mark the start of a streaming session.
        
        Args:
            provider_id: Provider ID
            session_id: Session ID
            
        Returns:
            Success status
        """
        with self.lock:
            if provider_id not in self.providers:
                return False
            
            provider = self.providers[provider_id]
            provider.start_session(session_id)
            return True
    
    def end_streaming_session(self, provider_id: str) -> bool:
        """
        Mark the end of a streaming session.
        
        Args:
            provider_id: Provider ID
            
        Returns:
            Success status
        """
        with self.lock:
            if provider_id not in self.providers:
                return False
            
            provider = self.providers[provider_id]
            provider.end_session()
            return True
    
    def _maintenance_loop(self) -> None:
        """
        Perform regular maintenance on the pool.
        - Remove expired providers
        - Scale up/down based on usage
        - Clean up error providers
        """
        while not self._shutdown.is_set():
            try:
                # Sleep for a bit
                time.sleep(10)
                
                with self.lock:
                    # Track expired providers to remove
                    expired_ids = []
                    
                    # Check for expired providers
                    for provider_id, provider in self.providers.items():
                        if provider.status in [ProviderStatus.AVAILABLE, ProviderStatus.COOLING_DOWN] and provider.is_expired():
                            expired_ids.append(provider_id)
                    
                    # Remove expired providers
                    for provider_id in expired_ids:
                        self._terminate_provider(provider_id)
                    
                    # Check if we need to scale up based on utilization
                    self._adjust_pool_size()
                    
                    # Try to recover error providers periodically
                    self._recover_error_providers()
            
            except Exception as e:
                logger.error(f"Error in pool maintenance: {e}")
    
    def _adjust_pool_size(self) -> None:
        """Adjust pool size based on utilization."""
        with self.lock:
            # Calculate utilization
            total_providers = len(self.providers)
            if total_providers == 0:
                return
            
            in_use = len(self.in_use_providers)
            utilization = in_use / total_providers
            
            # Scale up if utilization is above threshold and below max size
            if (utilization >= self.config.scaling_threshold and 
                total_providers < self.config.max_size):
                self._create_provider()
                logger.info(f"Scaling up pool {self.config.provider_type}/{self.config.voice_id} due to high utilization: {utilization:.2f}")
            
            # Scale down if too many available providers and above min size
            available = len(self.available_providers)
            if available > 1 and total_providers > self.config.min_size:
                excess = available - 1  # Keep at least one available
                
                # Remove excess available providers, oldest first
                available_providers = [
                    (pid, self.providers[pid])
                    for pid in self.available_providers
                ]
                
                # Sort by last used time (oldest first)
                available_providers.sort(
                    key=lambda x: x[1].last_used_at if x[1].last_used_at else 0
                )
                
                # Remove oldest providers
                for i in range(min(excess, total_providers - self.config.min_size)):
                    if i < len(available_providers):
                        self._terminate_provider(available_providers[i][0])
                        logger.info(f"Scaling down pool {self.config.provider_type}/{self.config.voice_id} due to excess capacity")
    
    def _recover_error_providers(self) -> None:
        """Try to recover providers in error state."""
        with self.lock:
            # Limit number of providers to recover at once
            error_ids = list(self.error_providers)[:3]
            
            for provider_id in error_ids:
                # Just remove the provider, will be replaced when needed
                self._terminate_provider(provider_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics for this pool.
        
        Returns:
            Dictionary of pool statistics
        """
        with self.lock:
            total_providers = len(self.providers)
            available = len(self.available_providers)
            in_use = len(self.in_use_providers)
            cooling = len(self.cooling_providers)
            errors = len(self.error_providers)
            
            # Calculate average checkout time
            avg_checkout_time = 0
            if self.checkout_times:
                # Keep only the last 100 checkout times
                if len(self.checkout_times) > 100:
                    self.checkout_times = self.checkout_times[-100:]
                avg_checkout_time = sum(self.checkout_times) / len(self.checkout_times)
            
            stats = {
                "provider_type": self.config.provider_type,
                "voice_id": self.config.voice_id,
                "config": {
                    "min_size": self.config.min_size,
                    "max_size": self.config.max_size,
                    "ttl": self.config.ttl,
                    "scaling_threshold": self.config.scaling_threshold
                },
                "total_providers": total_providers,
                "providers_by_status": {
                    "available": available,
                    "in_use": in_use,
                    "cooling": cooling,
                    "error": errors
                },
                "request_count": self.request_count,
                "checkout_count": self.checkout_count,
                "checkout_failures": self.checkout_failures,
                "creation_failures": self.creation_failures,
                "provider_errors": self.provider_errors,
                "pool_expansions": self.pool_expansions,
                "pool_contractions": self.pool_contractions,
                "avg_checkout_time": avg_checkout_time,
                "utilization": in_use / max(1, total_providers)
            }
            
            # Add individual provider stats if requested
            provider_stats = [
                provider.get_stats()
                for provider in self.providers.values()
            ]
            stats["providers"] = provider_stats
            
            return stats
    
    def shutdown(self) -> None:
        """Shutdown the pool and terminate all providers."""
        self._shutdown.set()
        
        with self.lock:
            # Terminate all providers
            for provider_id in list(self.providers.keys()):
                self._terminate_provider(provider_id)
        
        logger.info(f"Shutdown pool {self.config.provider_type}/{self.config.voice_id}")


class VoicePoolManager:
    """
    Manages pools of pre-initialized TTS providers for faster response.
    
    Features:
    - Provider lifecycle management (creation, checkout, return, termination)
    - Pooling by provider type and voice
    - Time-based expiration of idle providers
    - Automatic scaling based on utilization
    - Statistics tracking
    - Health monitoring
    """
    
    def __init__(self, event_emitter: Optional[TTSEventEmitter] = None):
        """
        Initialize the voice pool manager.
        
        Args:
            event_emitter: Event emitter for notifications
        """
        self.event_emitter = event_emitter
        self.provider_factories = {}
        self.pools: Dict[str, ProviderPool] = {}
        self.lock = threading.RLock()
        
        # Track active providers
        self.active_checkouts: Dict[str, Tuple[str, str]] = {}  # provider_id -> (pool_key, session_id)
        
        logger.info("VoicePoolManager initialized")
    
    def register_provider_factory(self, provider_type: str, factory_func) -> None:
        """
        Register a factory function for creating providers.
        
        Args:
            provider_type: Provider type identifier
            factory_func: Function that creates a provider instance
        """
        with self.lock:
            self.provider_factories[provider_type] = factory_func
            logger.info(f"Registered provider factory for {provider_type}")
    
    def create_pool(self, config: Union[PoolConfiguration, Dict[str, Any]]) -> str:
        """
        Create a new provider pool.
        
        Args:
            config: Pool configuration
            
        Returns:
            Pool key
        """
        with self.lock:
            if isinstance(config, dict):
                config = PoolConfiguration.from_dict(config)
            
            # Check if factory is registered
            if config.provider_type not in self.provider_factories:
                raise ValueError(f"No factory registered for provider type: {config.provider_type}")
            
            # Set factory function
            config.provider_factory = self.provider_factories[config.provider_type]
            
            # Create the pool
            pool_key = config.get_pool_key()
            
            # Skip if pool already exists
            if pool_key in self.pools:
                logger.warning(f"Pool already exists: {pool_key}")
                return pool_key
            
            self.pools[pool_key] = ProviderPool(config, self.event_emitter)
            logger.info(f"Created pool {pool_key}")
            
            return pool_key
    
    def get_provider(self, provider_type: str, voice_id: str) -> Optional[Tuple[str, BaseTTSProvider]]:
        """
        Get a provider from the pool.
        
        Args:
            provider_type: Provider type
            voice_id: Voice identifier
            
        Returns:
            Tuple of (provider_id, provider) or None if not available
        """
        pool_key = f"{provider_type}_{voice_id}"
        
        with self.lock:
            # Check if pool exists
            if pool_key not in self.pools:
                logger.warning(f"No pool for {pool_key}")
                return None
            
            # Checkout from pool
            result = self.pools[pool_key].checkout_provider()
            if not result:
                return None
            
            provider_id, provider = result
            
            # Track checkout
            self.active_checkouts[provider_id] = (pool_key, None)
            
            return provider_id, provider
    
    def return_provider(self, provider_id: str, error: bool = False) -> bool:
        """
        Return a provider to its pool.
        
        Args:
            provider_id: Provider ID
            error: Whether the provider encountered an error
            
        Returns:
            Success status
        """
        with self.lock:
            if provider_id not in self.active_checkouts:
                logger.warning(f"Attempted to return unknown provider: {provider_id}")
                return False
            
            pool_key, _ = self.active_checkouts[provider_id]
            
            if pool_key not in self.pools:
                logger.warning(f"Pool no longer exists for provider: {provider_id}")
                del self.active_checkouts[provider_id]
                return False
            
            # Return to pool
            result = self.pools[pool_key].return_provider(provider_id, error)
            
            # Remove from active checkouts
            if result:
                del self.active_checkouts[provider_id]
            
            return result
    
    def begin_streaming_session(self, provider_id: str, session_id: str) -> bool:
        """
        Begin a streaming session with a provider.
        
        Args:
            provider_id: Provider ID
            session_id: Session ID
            
        Returns:
            Success status
        """
        with self.lock:
            if provider_id not in self.active_checkouts:
                logger.warning(f"Attempted to start session for unknown provider: {provider_id}")
                return False
            
            pool_key, _ = self.active_checkouts[provider_id]
            
            if pool_key not in self.pools:
                logger.warning(f"Pool no longer exists for provider: {provider_id}")
                return False
            
            # Update session tracking
            self.active_checkouts[provider_id] = (pool_key, session_id)
            
            # Update pool tracking
            return self.pools[pool_key].start_streaming_session(provider_id, session_id)
    
    def end_streaming_session(self, provider_id: str) -> bool:
        """
        End a streaming session with a provider.
        
        Args:
            provider_id: Provider ID
            
        Returns:
            Success status
        """
        with self.lock:
            if provider_id not in self.active_checkouts:
                logger.warning(f"Attempted to end session for unknown provider: {provider_id}")
                return False
            
            pool_key, session_id = self.active_checkouts[provider_id]
            
            if pool_key not in self.pools:
                logger.warning(f"Pool no longer exists for provider: {provider_id}")
                return False
            
            # Update session tracking
            self.active_checkouts[provider_id] = (pool_key, None)
            
            # Update pool tracking
            return self.pools[pool_key].end_streaming_session(provider_id)
    
    def get_pool_stats(self, provider_type: str = None, voice_id: str = None) -> Dict[str, Any]:
        """
        Get statistics for pools.
        
        Args:
            provider_type: Filter by provider type (optional)
            voice_id: Filter by voice ID (optional)
            
        Returns:
            Dictionary of pool statistics
        """
        with self.lock:
            stats = {
                "total_pools": len(self.pools),
                "total_active_providers": len(self.active_checkouts),
                "pools": []
            }
            
            # Filter pools
            filtered_pools = []
            for pool_key, pool in self.pools.items():
                if provider_type and pool.config.provider_type != provider_type:
                    continue
                
                if voice_id and pool.config.voice_id != voice_id:
                    continue
                
                filtered_pools.append((pool_key, pool))
            
            # Get stats for each pool
            for pool_key, pool in filtered_pools:
                pool_stats = pool.get_stats()
                stats["pools"].append(pool_stats)
            
            return stats
    
    def shutdown(self) -> None:
        """Shutdown all pools."""
        with self.lock:
            for pool_key, pool in self.pools.items():
                pool.shutdown()
            
            self.pools.clear()
            self.active_checkouts.clear()
        
        logger.info("VoicePoolManager shutdown complete")
    
    def update_pool_configuration(self, 
                                 provider_type: str, 
                                 voice_id: str, 
                                 updates: Dict[str, Any]) -> bool:
        """
        Update configuration for a pool.
        
        Args:
            provider_type: Provider type
            voice_id: Voice ID
            updates: Configuration updates
            
        Returns:
            Success status
        """
        pool_key = f"{provider_type}_{voice_id}"
        
        with self.lock:
            if pool_key not in self.pools:
                logger.warning(f"No pool for {pool_key}")
                return False
            
            pool = self.pools[pool_key]
            
            # Update configuration
            for key, value in updates.items():
                if hasattr(pool.config, key):
                    setattr(pool.config, key, value)
            
            logger.info(f"Updated configuration for pool {pool_key}")
            return True
    
    def get_provider_with_fallback(self, provider_types: List[str], voice_id: str) -> Optional[Tuple[str, BaseTTSProvider]]:
        """
        Get a provider with fallback to alternate types.
        
        Args:
            provider_types: Prioritized list of provider types
            voice_id: Voice ID
            
        Returns:
            Tuple of (provider_id, provider) or None if not available
        """
        for provider_type in provider_types:
            result = self.get_provider(provider_type, voice_id)
            if result:
                return result
        
        return None
    
    def cleanup_unused_pools(self, max_idle_time: int = 3600) -> int:
        """
        Remove pools that haven't been used for a while.
        
        Args:
            max_idle_time: Maximum idle time in seconds
            
        Returns:
            Number of pools removed
        """
        pools_to_remove = []
        
        with self.lock:
            for pool_key, pool in self.pools.items():
                # Consider a pool unused if it has no in-use providers
                # and hasn't had a checkout in a while
                stats = pool.get_stats()
                
                if (stats["providers_by_status"]["in_use"] == 0 and
                    time.time() - pool.request_count > max_idle_time):
                    pools_to_remove.append(pool_key)
        
        # Remove pools
        for pool_key in pools_to_remove:
            self.remove_pool(pool_key)
        
        return len(pools_to_remove)
    
    def remove_pool(self, pool_key: str) -> bool:
        """
        Remove a pool.
        
        Args:
            pool_key: Pool key
            
        Returns:
            Success status
        """
        with self.lock:
            if pool_key not in self.pools:
                return False
            
            # Shutdown the pool
            self.pools[pool_key].shutdown()
            
            # Remove pool
            del self.pools[pool_key]
            
            logger.info(f"Removed pool {pool_key}")
            return True
    
    def adjust_all_pool_sizes(self, scaling_factor: float) -> None:
        """
        Adjust size of all pools by a scaling factor.
        
        Args:
            scaling_factor: Factor to multiply min/max sizes by
        """
        with self.lock:
            for pool_key, pool in self.pools.items():
                # Calculate new sizes
                new_min = max(1, int(pool.config.min_size * scaling_factor))
                new_max = max(new_min, int(pool.config.max_size * scaling_factor))
                
                # Update configuration
                pool.config.min_size = new_min
                pool.config.max_size = new_max
                
                logger.info(f"Adjusted pool {pool_key} size: min={new_min}, max={new_max}") 