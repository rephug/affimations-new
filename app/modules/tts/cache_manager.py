#!/usr/bin/env python
# Multi-layer TTS Cache Manager

import os
import json
import time
import hashlib
import logging
import threading
import functools
from typing import Dict, Any, Optional, List, Tuple, Callable, Union
from pathlib import Path
from datetime import datetime, timedelta
import shutil

# For type hints
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger("tts-cache")

class TTSCacheKey:
    """Class for generating and managing cache keys."""
    
    @staticmethod
    def generate(text: str, provider_type: str, voice_id: str, 
                 speed: float = 1.0, **kwargs) -> str:
        """
        Generate a cache key from TTS parameters.
        
        Args:
            text: The text to synthesize
            provider_type: The TTS provider (google, kokoro, etc.)
            voice_id: The voice identifier
            speed: Speech rate
            **kwargs: Additional parameters that affect output
            
        Returns:
            A unique hash key for the given parameters
        """
        # Create a deterministic string representation of the parameters
        param_str = f"{text}|{provider_type}|{voice_id}|{speed}"
        
        # Add any additional parameters that affect the output
        for k in sorted(kwargs.keys()):
            param_str += f"|{k}:{kwargs[k]}"
        
        # Generate SHA-256 hash
        return hashlib.sha256(param_str.encode('utf-8')).hexdigest()
    
    @staticmethod
    def parse(key: str) -> Dict[str, Any]:
        """
        Parse a cache key to extract metadata (for debugging).
        This is a stub since we use a hash function.
        
        Args:
            key: The cache key
            
        Returns:
            Dict with metadata if available
        """
        return {"key": key}


class MemoryCacheBackend:
    """Memory-based cache using LRU strategy."""
    
    def __init__(self, max_size: int = 100, ttl: int = 3600):
        """
        Initialize memory cache backend.
        
        Args:
            max_size: Maximum number of items to store
            ttl: Time-to-live in seconds
        """
        self.max_size = max_size
        self.ttl = ttl
        self.cache = {}  # key -> (value, timestamp)
        self.lock = threading.RLock()
        self.hits = 0
        self.misses = 0
        
        # Start cleanup thread
        self.cleanup_thread = threading.Thread(
            target=self._cleanup_expired, 
            daemon=True
        )
        self.cleanup_thread.start()
    
    def get(self, key: str) -> Optional[bytes]:
        """
        Get item from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        with self.lock:
            if key not in self.cache:
                self.misses += 1
                return None
            
            value, timestamp = self.cache[key]
            
            # Check if expired
            if time.time() - timestamp > self.ttl:
                del self.cache[key]
                self.misses += 1
                return None
            
            # Update timestamp to mark as recently used
            self.cache[key] = (value, time.time())
            self.hits += 1
            return value
    
    def set(self, key: str, value: bytes) -> bool:
        """
        Set item in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            
        Returns:
            True if successfully cached
        """
        with self.lock:
            # Enforce max size with LRU eviction
            if len(self.cache) >= self.max_size and key not in self.cache:
                # Find oldest entry
                oldest_key = min(
                    self.cache.items(), 
                    key=lambda x: x[1][1]
                )[0]
                del self.cache[oldest_key]
            
            # Set with current timestamp
            self.cache[key] = (value, time.time())
            return True
    
    def delete(self, key: str) -> bool:
        """
        Delete item from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if deleted, False if not found
        """
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False
    
    def clear(self) -> bool:
        """
        Clear the entire cache.
        
        Returns:
            True on success
        """
        with self.lock:
            self.cache.clear()
            return True
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dict with hit/miss stats and cache size
        """
        with self.lock:
            return {
                "backend": "memory",
                "size": len(self.cache),
                "max_size": self.max_size,
                "hits": self.hits,
                "misses": self.misses,
                "hit_ratio": self.hits / (self.hits + self.misses) if (self.hits + self.misses) > 0 else 0,
                "memory_usage_kb": sum(len(v[0]) for v in self.cache.values()) / 1024
            }
    
    def _cleanup_expired(self):
        """Periodically clean up expired entries."""
        while True:
            time.sleep(60)  # Check every minute
            with self.lock:
                current_time = time.time()
                expired_keys = [
                    k for k, (_, timestamp) in self.cache.items()
                    if current_time - timestamp > self.ttl
                ]
                for k in expired_keys:
                    del self.cache[k]


class RedisCacheBackend:
    """Redis-based distributed cache backend."""
    
    def __init__(self, 
                 host: str = 'localhost', 
                 port: int = 6379,
                 db: int = 0,
                 password: Optional[str] = None,
                 ttl: int = 86400,
                 prefix: str = 'tts:'):
        """
        Initialize Redis cache backend.
        
        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            password: Redis password
            ttl: Default TTL in seconds
            prefix: Key prefix for TTS cache
        """
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.ttl = ttl
        self.prefix = prefix
        self.client = None
        self.available = False
        self.hits = 0
        self.misses = 0
        
        # Connect to Redis
        self._connect()
    
    def _connect(self):
        """Establish connection to Redis."""
        if not REDIS_AVAILABLE:
            logger.warning("Redis package not installed. Redis caching unavailable.")
            return
        
        try:
            self.client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                socket_timeout=5
            )
            # Test connection
            self.client.ping()
            self.available = True
            logger.info("Connected to Redis cache")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            self.available = False
    
    def _format_key(self, key: str) -> str:
        """Add prefix to key."""
        return f"{self.prefix}{key}"
    
    def get(self, key: str) -> Optional[bytes]:
        """
        Get item from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        if not self.available:
            return None
        
        try:
            formatted_key = self._format_key(key)
            value = self.client.get(formatted_key)
            
            if value is None:
                self.misses += 1
                return None
            
            self.hits += 1
            return value
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None
    
    def set(self, key: str, value: bytes) -> bool:
        """
        Set item in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            
        Returns:
            True if successfully cached
        """
        if not self.available:
            return False
        
        try:
            formatted_key = self._format_key(key)
            self.client.set(formatted_key, value, ex=self.ttl)
            return True
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """
        Delete item from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if deleted, False if not found
        """
        if not self.available:
            return False
        
        try:
            formatted_key = self._format_key(key)
            result = self.client.delete(formatted_key)
            return result > 0
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False
    
    def clear(self) -> bool:
        """
        Clear all cache entries with our prefix.
        
        Returns:
            True on success
        """
        if not self.available:
            return False
        
        try:
            pattern = f"{self.prefix}*"
            cursor = 0
            while True:
                cursor, keys = self.client.scan(cursor, pattern, 100)
                if keys:
                    self.client.delete(*keys)
                if cursor == 0:
                    break
            return True
        except Exception as e:
            logger.error(f"Redis clear error: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dict with hit/miss stats and cache info
        """
        if not self.available:
            return {
                "backend": "redis",
                "available": False,
                "error": "Redis not available"
            }
        
        try:
            info = self.client.info()
            pattern = f"{self.prefix}*"
            cache_keys = self.client.keys(pattern)
            memory_used = 0
            
            # Sample a subset of keys to estimate memory usage
            sample_keys = cache_keys[:min(100, len(cache_keys))]
            if sample_keys:
                for key in sample_keys:
                    key_memory = self.client.memory_usage(key) or 0
                    memory_used += key_memory
                
                # Extrapolate for all keys
                if len(sample_keys) > 0:
                    memory_used = memory_used * (len(cache_keys) / len(sample_keys))
            
            return {
                "backend": "redis",
                "available": True,
                "size": len(cache_keys),
                "hits": self.hits,
                "misses": self.misses,
                "hit_ratio": self.hits / (self.hits + self.misses) if (self.hits + self.misses) > 0 else 0,
                "memory_usage_kb": memory_used / 1024,
                "redis_version": info.get("redis_version", "unknown"),
                "redis_memory_used_kb": info.get("used_memory", 0) / 1024
            }
        except Exception as e:
            logger.error(f"Redis stats error: {e}")
            return {
                "backend": "redis",
                "available": True,
                "error": str(e),
                "hits": self.hits,
                "misses": self.misses
            }


class FilesystemCacheBackend:
    """Filesystem-based persistent cache backend."""
    
    def __init__(self, 
                 cache_dir: Optional[str] = None,
                 max_size_mb: int = 1024,  # 1GB default
                 ttl: int = 2592000):  # 30 days default
        """
        Initialize filesystem cache backend.
        
        Args:
            cache_dir: Directory for cache files
            max_size_mb: Maximum size in MB
            ttl: Time-to-live in seconds
        """
        self.cache_dir = cache_dir or os.path.join(
            os.path.expanduser("~"), ".tts_cache"
        )
        self.max_size_mb = max_size_mb
        self.ttl = ttl
        self.hits = 0
        self.misses = 0
        
        # Create cache directory if it doesn't exist
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # JSON metadata file for tracking file info
        self.metadata_path = os.path.join(self.cache_dir, "metadata.json")
        self.metadata = self._load_metadata()
        
        # Start cleanup thread for expired items
        self.cleanup_thread = threading.Thread(
            target=self._cleanup_expired_and_oversized, 
            daemon=True
        )
        self.cleanup_thread.start()
    
    def _load_metadata(self) -> Dict[str, Dict[str, Any]]:
        """Load metadata or create if it doesn't exist."""
        if os.path.exists(self.metadata_path):
            try:
                with open(self.metadata_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load cache metadata: {e}")
        
        return {}
    
    def _save_metadata(self):
        """Save metadata to disk."""
        try:
            with open(self.metadata_path, 'w') as f:
                json.dump(self.metadata, f)
        except Exception as e:
            logger.error(f"Failed to save cache metadata: {e}")
    
    def _get_file_path(self, key: str) -> str:
        """Get file path for a cache key."""
        return os.path.join(self.cache_dir, key)
    
    def get(self, key: str) -> Optional[bytes]:
        """
        Get item from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        file_path = self._get_file_path(key)
        
        if not os.path.exists(file_path):
            self.misses += 1
            return None
        
        # Check metadata for expiration
        if key in self.metadata:
            timestamp = self.metadata[key].get("timestamp", 0)
            if time.time() - timestamp > self.ttl:
                # Expired
                self.delete(key)
                self.misses += 1
                return None
        
        try:
            with open(file_path, 'rb') as f:
                data = f.read()
            
            # Update access time in metadata
            if key in self.metadata:
                self.metadata[key]["last_accessed"] = time.time()
                self._save_metadata()
            
            self.hits += 1
            return data
        except Exception as e:
            logger.error(f"Failed to read cache file {key}: {e}")
            self.misses += 1
            return None
    
    def set(self, key: str, value: bytes) -> bool:
        """
        Set item in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            
        Returns:
            True if successfully cached
        """
        file_path = self._get_file_path(key)
        
        try:
            with open(file_path, 'wb') as f:
                f.write(value)
            
            # Update metadata
            self.metadata[key] = {
                "timestamp": time.time(),
                "last_accessed": time.time(),
                "size": len(value)
            }
            self._save_metadata()
            
            # Check if we need to clean up
            self._check_size_limit()
            
            return True
        except Exception as e:
            logger.error(f"Failed to write cache file {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """
        Delete item from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if deleted, False if not found
        """
        file_path = self._get_file_path(key)
        
        if not os.path.exists(file_path):
            return False
        
        try:
            os.remove(file_path)
            
            # Remove from metadata
            if key in self.metadata:
                del self.metadata[key]
                self._save_metadata()
            
            return True
        except Exception as e:
            logger.error(f"Failed to delete cache file {key}: {e}")
            return False
    
    def clear(self) -> bool:
        """
        Clear the entire cache.
        
        Returns:
            True on success
        """
        try:
            # Delete all files except metadata
            for filename in os.listdir(self.cache_dir):
                if filename != "metadata.json":
                    file_path = os.path.join(self.cache_dir, filename)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
            
            # Reset metadata
            self.metadata = {}
            self._save_metadata()
            
            return True
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dict with hit/miss stats and cache size
        """
        total_size = 0
        file_count = 0
        
        try:
            for filename in os.listdir(self.cache_dir):
                if filename != "metadata.json":
                    file_path = os.path.join(self.cache_dir, filename)
                    if os.path.isfile(file_path):
                        total_size += os.path.getsize(file_path)
                        file_count += 1
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
        
        return {
            "backend": "filesystem",
            "size": file_count,
            "cache_dir": self.cache_dir,
            "total_size_mb": total_size / (1024 * 1024),
            "max_size_mb": self.max_size_mb,
            "hits": self.hits,
            "misses": self.misses,
            "hit_ratio": self.hits / (self.hits + self.misses) if (self.hits + self.misses) > 0 else 0
        }
    
    def _check_size_limit(self):
        """Check if cache exceeds size limit and clean up if needed."""
        total_size = 0
        
        try:
            for filename in os.listdir(self.cache_dir):
                if filename != "metadata.json":
                    file_path = os.path.join(self.cache_dir, filename)
                    if os.path.isfile(file_path):
                        total_size += os.path.getsize(file_path)
        except Exception as e:
            logger.error(f"Failed to check cache size: {e}")
            return
        
        # Convert to MB
        total_size_mb = total_size / (1024 * 1024)
        
        if total_size_mb > self.max_size_mb:
            # Need to clean up - delete least recently accessed files
            self._cleanup_by_lru(total_size_mb - self.max_size_mb)
    
    def _cleanup_by_lru(self, space_to_free_mb: float):
        """
        Clean up cache by removing least recently used files.
        
        Args:
            space_to_free_mb: Space to free in MB
        """
        if not self.metadata:
            return
        
        # Sort by last accessed time
        sorted_items = sorted(
            self.metadata.items(),
            key=lambda x: x[1].get("last_accessed", 0)
        )
        
        space_freed = 0
        bytes_to_free = space_to_free_mb * 1024 * 1024
        
        for key, data in sorted_items:
            if space_freed >= bytes_to_free:
                break
            
            # Delete file
            file_path = self._get_file_path(key)
            try:
                if os.path.exists(file_path):
                    size = os.path.getsize(file_path)
                    os.remove(file_path)
                    space_freed += size
                    
                    # Remove from metadata
                    del self.metadata[key]
            except Exception as e:
                logger.error(f"Failed to delete cache file during cleanup: {e}")
        
        # Save updated metadata
        self._save_metadata()
    
    def _cleanup_expired_and_oversized(self):
        """Periodically clean up expired files and check size limits."""
        while True:
            time.sleep(3600)  # Run every hour
            
            try:
                # Check for expired items
                current_time = time.time()
                expired_keys = [
                    key for key, data in self.metadata.items()
                    if current_time - data.get("timestamp", 0) > self.ttl
                ]
                
                for key in expired_keys:
                    self.delete(key)
                
                # Check size limits
                self._check_size_limit()
            except Exception as e:
                logger.error(f"Error during cache cleanup: {e}")


class TTSCacheManager:
    """
    Multi-layer caching system for TTS audio with memory, Redis, and filesystem support.
    
    This manages caching across multiple backends with different persistence and
    performance characteristics:
    
    1. Memory cache: Fast, in-process LRU cache for frequent requests
    2. Redis cache: Distributed cache shared across processes/servers
    3. Filesystem cache: Long-term persistent storage for less frequent items
    
    Features statistics tracking, cache prewarming, and automatic management of
    cache tiers.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the cache manager.
        
        Args:
            config: Configuration dictionary with settings for each cache layer
        """
        self.config = config or {}
        self.lock = threading.RLock()
        self.stats = {
            "gets": 0,
            "sets": 0,
            "hits": 0,
            "misses": 0,
            "hit_ratio": 0,
            "tier_hits": {
                "memory": 0,
                "redis": 0,
                "filesystem": 0
            }
        }
        
        # Initialize cache backends
        self._init_backends()
        
        # Commonly used phrases for prewarming
        self.common_phrases = self.config.get("common_phrases", [
            "Hello, how are you today?",
            "I didn't quite catch that.",
            "Could you please repeat that?",
            "Thank you for your patience.",
            "Is there anything else I can help you with?",
            "Just a moment, please.",
            "I'll transfer you to a specialist.",
            "Could you confirm that for me?",
            "I apologize for the inconvenience.",
            "Let me check that for you."
        ])
        
        logger.info("TTSCacheManager initialized")
    
    def _init_backends(self):
        """Initialize all cache backends based on configuration."""
        memory_config = self.config.get("memory", {})
        redis_config = self.config.get("redis", {})
        filesystem_config = self.config.get("filesystem", {})
        
        self.backends = []
        
        # Memory cache (always enabled)
        self.memory_cache = MemoryCacheBackend(
            max_size=memory_config.get("max_size", 100),
            ttl=memory_config.get("ttl", 3600)
        )
        self.backends.append(("memory", self.memory_cache))
        
        # Redis cache (if enabled)
        if redis_config.get("enabled", False):
            self.redis_cache = RedisCacheBackend(
                host=redis_config.get("host", "localhost"),
                port=redis_config.get("port", 6379),
                db=redis_config.get("db", 0),
                password=redis_config.get("password"),
                ttl=redis_config.get("ttl", 86400),
                prefix=redis_config.get("prefix", "tts:")
            )
            if self.redis_cache.available:
                self.backends.append(("redis", self.redis_cache))
        else:
            self.redis_cache = None
        
        # Filesystem cache (if enabled)
        if filesystem_config.get("enabled", True):
            self.filesystem_cache = FilesystemCacheBackend(
                cache_dir=filesystem_config.get("cache_dir"),
                max_size_mb=filesystem_config.get("max_size_mb", 1024),
                ttl=filesystem_config.get("ttl", 2592000)
            )
            self.backends.append(("filesystem", self.filesystem_cache))
        else:
            self.filesystem_cache = None
    
    def get(self, key: str) -> Optional[bytes]:
        """
        Get item from cache, trying each backend in order.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        with self.lock:
            self.stats["gets"] += 1
        
        # Try each backend in order
        for backend_name, backend in self.backends:
            value = backend.get(key)
            if value is not None:
                # Found in this tier
                with self.lock:
                    self.stats["hits"] += 1
                    self.stats["tier_hits"][backend_name] += 1
                    self.stats["hit_ratio"] = self.stats["hits"] / self.stats["gets"]
                
                # If found in a lower tier, propagate to higher tiers
                self._propagate_to_higher_tiers(key, value, backend_name)
                
                return value
        
        # Not found in any tier
        with self.lock:
            self.stats["misses"] += 1
            self.stats["hit_ratio"] = self.stats["hits"] / self.stats["gets"] if self.stats["gets"] > 0 else 0
        
        return None
    
    def _propagate_to_higher_tiers(self, key: str, value: bytes, found_tier: str):
        """
        Propagate a cache item to higher (faster) tiers.
        
        Args:
            key: Cache key
            value: Value to propagate
            found_tier: Tier where the value was found
        """
        # Get index of the tier where the value was found
        tier_index = next(i for i, (name, _) in enumerate(self.backends) if name == found_tier)
        
        # Propagate to all higher tiers
        for i in range(tier_index):
            tier_name, backend = self.backends[i]
            backend.set(key, value)
    
    def set(self, key: str, value: bytes) -> bool:
        """
        Set item in all cache backends.
        
        Args:
            key: Cache key
            value: Value to cache
            
        Returns:
            True if successfully cached in at least one backend
        """
        with self.lock:
            self.stats["sets"] += 1
        
        success = False
        
        # Set in all backends
        for _, backend in self.backends:
            if backend.set(key, value):
                success = True
        
        return success
    
    def set_tts_result(self, text: str, audio_data: bytes, provider_type: str, 
                      voice_id: str, speed: float = 1.0, **kwargs) -> str:
        """
        Store TTS result in cache with auto-generated key.
        
        Args:
            text: The text that was synthesized
            audio_data: The audio data to cache
            provider_type: The TTS provider used
            voice_id: The voice identifier used
            speed: Speech rate
            **kwargs: Additional parameters that affect the output
            
        Returns:
            The generated cache key
        """
        # Generate key
        key = TTSCacheKey.generate(text, provider_type, voice_id, speed, **kwargs)
        
        # Store in cache
        self.set(key, audio_data)
        
        return key
    
    def get_tts_result(self, text: str, provider_type: str, voice_id: str,
                      speed: float = 1.0, **kwargs) -> Optional[bytes]:
        """
        Retrieve TTS result from cache using parameters.
        
        Args:
            text: The text to synthesize
            provider_type: The TTS provider
            voice_id: The voice identifier
            speed: Speech rate
            **kwargs: Additional parameters that affect output
            
        Returns:
            Cached audio data or None if not found
        """
        # Generate key
        key = TTSCacheKey.generate(text, provider_type, voice_id, speed, **kwargs)
        
        # Get from cache
        return self.get(key)
    
    def delete(self, key: str) -> bool:
        """
        Delete item from all cache backends.
        
        Args:
            key: Cache key
            
        Returns:
            True if deleted from at least one backend
        """
        success = False
        
        # Delete from all backends
        for _, backend in self.backends:
            if backend.delete(key):
                success = True
        
        return success
    
    def clear(self) -> bool:
        """
        Clear all cache backends.
        
        Returns:
            True if all backends were cleared successfully
        """
        success = True
        
        # Clear all backends
        for _, backend in self.backends:
            if not backend.clear():
                success = False
        
        return success
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive cache statistics.
        
        Returns:
            Dict with combined stats from all backends
        """
        with self.lock:
            stats = {
                "global": {
                    "gets": self.stats["gets"],
                    "sets": self.stats["sets"],
                    "hits": self.stats["hits"],
                    "misses": self.stats["misses"],
                    "hit_ratio": self.stats["hit_ratio"],
                    "tier_hits": self.stats["tier_hits"]
                },
                "backends": {}
            }
        
        # Get stats from each backend
        for name, backend in self.backends:
            stats["backends"][name] = backend.get_stats()
        
        return stats
    
    def prewarm(self, provider_type: str, voice_id: str, common_phrases: Optional[List[str]] = None,
               speed: float = 1.0, tts_func: Optional[Callable[[str, str, float], bytes]] = None) -> int:
        """
        Prewarm cache with common phrases.
        
        Args:
            provider_type: The TTS provider to use
            voice_id: The voice identifier to use
            common_phrases: List of phrases to prewarm (defaults to self.common_phrases)
            speed: Speech rate
            tts_func: Function to generate TTS audio if not in cache
            
        Returns:
            Number of phrases prewarmed
        """
        phrases = common_phrases or self.common_phrases
        count = 0
        
        for phrase in phrases:
            # Check if already in cache
            key = TTSCacheKey.generate(phrase, provider_type, voice_id, speed)
            if self.get(key) is not None:
                # Already cached
                continue
            
            # Generate if not in cache and function provided
            if tts_func:
                try:
                    audio_data = tts_func(phrase, voice_id, speed)
                    if audio_data:
                        self.set(key, audio_data)
                        count += 1
                        # Small delay to avoid overloading TTS service
                        time.sleep(0.1)
                except Exception as e:
                    logger.error(f"Error prewarming cache for phrase '{phrase}': {e}")
        
        return count
    
    def prewarm_async(self, provider_type: str, voice_id: str, 
                     common_phrases: Optional[List[str]] = None,
                     speed: float = 1.0, 
                     tts_func: Optional[Callable[[str, str, float], bytes]] = None) -> threading.Thread:
        """
        Prewarm cache asynchronously in a background thread.
        
        Args:
            provider_type: The TTS provider to use
            voice_id: The voice identifier to use
            common_phrases: List of phrases to prewarm
            speed: Speech rate
            tts_func: Function to generate TTS audio if not in cache
            
        Returns:
            Thread object running the prewarming
        """
        thread = threading.Thread(
            target=self.prewarm,
            args=(provider_type, voice_id),
            kwargs={
                "common_phrases": common_phrases,
                "speed": speed,
                "tts_func": tts_func
            },
            daemon=True
        )
        thread.start()
        return thread
    
    def add_common_phrase(self, phrase: str):
        """
        Add a phrase to the common phrases list.
        
        Args:
            phrase: Phrase to add
        """
        if phrase not in self.common_phrases:
            self.common_phrases.append(phrase)
    
    def optimize_cache(self):
        """
        Optimize cache by cleaning up and reorganizing.
        
        This performs maintenance operations like:
        - Removing expired items
        - Ensuring heavily used items are in faster tiers
        - Managing cache size limits
        """
        # This is a placeholder for potential future optimizations
        # Currently, backends manage their own cleanup
        pass 