#!/usr/bin/env python
# Celery Task Configuration for TTS Background Processing

import os
import logging
import time
import tempfile
import json
from typing import Dict, Any, Optional, List, Tuple, Union
from functools import wraps
import threading

# Celery imports
from celery import Celery, Task, current_task
from celery.exceptions import SoftTimeLimitExceeded
from celery.signals import task_failure, task_success, task_retry

# Redis for results and caching
import redis

# Import local modules
from .provider_factory import TTSProviderFactory
from .base_provider import BaseTTSProvider

logger = logging.getLogger("tts-tasks")

# Initialize Celery app with specific configuration
celery_app = Celery('tts_tasks')
celery_app.conf.update(
    broker_url=os.environ.get('CELERY_BROKER_URL', 'redis://redis:6379/0'),
    result_backend=os.environ.get('CELERY_RESULT_BACKEND', 'redis://redis:6379/0'),
    task_serializer='pickle',  # Use pickle for binary data
    accept_content=['json', 'pickle'],
    result_serializer='pickle',
    task_time_limit=60,  # 1 minute hard limit
    task_soft_time_limit=30,  # 30 seconds soft limit
    worker_prefetch_multiplier=1,  # Process one task at a time
    task_acks_late=True,  # Acknowledge tasks after execution
    task_reject_on_worker_lost=True,  # Requeue tasks if worker dies
    result_expires=3600,  # Results expire after 1 hour
    task_track_started=True,  # Track when tasks are started
    worker_max_tasks_per_child=100,  # Restart worker after 100 tasks
)

# Define task queues with priorities
celery_app.conf.task_queues = {
    'tts_high': {'exchange': 'tts', 'routing_key': 'high'},
    'tts_normal': {'exchange': 'tts', 'routing_key': 'normal'},
    'tts_low': {'exchange': 'tts', 'routing_key': 'low'}
}

# Route tasks to appropriate queues
celery_app.conf.task_routes = {
    'modules.tts.tasks.generate_speech_task': {'queue': 'tts_high'},
    'modules.tts.tasks.prewarm_task': {'queue': 'tts_low'},
    'modules.tts.tasks.batch_generation_task': {'queue': 'tts_normal'},
}

# Configure default queue
celery_app.conf.task_default_queue = 'tts_normal'

# Get Redis client from environment or use default
redis_url = os.environ.get('REDIS_URL', 'redis://redis:6379/0')

def get_redis_client():
    """Get Redis client for caching and results."""
    try:
        return redis.Redis.from_url(redis_url)
    except Exception as e:
        logger.error(f"Error connecting to Redis: {e}")
        return None

# Task metrics and logging
@task_failure.connect
def log_task_failure(sender=None, task_id=None, exception=None, args=None, kwargs=None, **extras):
    """Log task failures for monitoring."""
    logger.error(f"Task {task_id} failed: {exception}")
    
    # Store failure in Redis for monitoring
    redis_client = get_redis_client()
    if redis_client:
        try:
            failure_data = {
                'task_id': task_id,
                'task_name': sender.name if sender else 'unknown',
                'error': str(exception),
                'timestamp': time.time()
            }
            redis_client.lpush('tts:task:failures', json.dumps(failure_data))
            redis_client.ltrim('tts:task:failures', 0, 99)  # Keep last 100 failures
        except Exception as e:
            logger.error(f"Error storing failure data: {e}")

@task_success.connect
def log_task_success(sender=None, result=None, **kwargs):
    """Log task successes for monitoring."""
    task_id = kwargs.get('task_id', 'unknown')
    task_name = sender.name if sender else 'unknown'
    
    # Only log metadata for successful tasks (avoid logging large audio data)
    if result and isinstance(result, bytes):
        logger.info(f"Task {task_id} ({task_name}) completed successfully: {len(result)} bytes generated")
    else:
        logger.info(f"Task {task_id} ({task_name}) completed successfully")

class TTSTask(Task):
    """Base class for TTS tasks with common functionality."""
    
    _providers = {}  # Cache for provider instances
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        logger.error(f"Task {task_id} failed: {exc}")
        
        # Add to failure metrics
        provider_name = kwargs.get('provider_type', 'unknown')
        self._increment_counter(f"tts:metrics:failures:{provider_name}")
    
    def on_success(self, retval, task_id, args, kwargs):
        """Handle task success."""
        # Add to success metrics
        provider_name = kwargs.get('provider_type', 'unknown')
        self._increment_counter(f"tts:metrics:successes:{provider_name}")
        
        # Track latency if we have start time
        if hasattr(self, 'start_time'):
            duration = time.time() - self.start_time
            redis_client = get_redis_client()
            if redis_client:
                try:
                    redis_client.lpush(f"tts:metrics:latency:{provider_name}", str(duration))
                    redis_client.ltrim(f"tts:metrics:latency:{provider_name}", 0, 99)
                except Exception:
                    pass
    
    def _increment_counter(self, key):
        """Increment a counter in Redis."""
        redis_client = get_redis_client()
        if redis_client:
            try:
                redis_client.incr(key)
            except Exception:
                pass
    
    def _get_provider(self, provider_type, provider_config=None):
        """Get or create a TTS provider instance."""
        # Try to reuse provider if available
        if provider_type in self._providers:
            return self._providers[provider_type]
        
        # Create new provider
        redis_client = get_redis_client()
        config = provider_config or {}
        
        try:
            provider = TTSProviderFactory.create_provider(
                provider_type,
                redis_client,
                config
            )
            
            # Cache provider for reuse
            self._providers[provider_type] = provider
            return provider
        except Exception as e:
            logger.error(f"Error creating provider {provider_type}: {e}")
            raise

@celery_app.task(bind=True, base=TTSTask, max_retries=3, 
                retry_backoff=True, retry_backoff_max=60,
                time_limit=60, soft_time_limit=30,
                queue='tts_high')
def generate_speech_task(self, text, provider_type, provider_config=None, 
                         voice_id=None, speed=1.0, use_cache=True):
    """
    Generate speech using the specified provider.
    
    Args:
        text: Text to convert to speech
        provider_type: Provider type to use
        provider_config: Provider configuration (optional)
        voice_id: Voice identifier (optional)
        speed: Speech speed factor (default: 1.0)
        use_cache: Whether to use cache (default: True)
        
    Returns:
        bytes: Audio data
    """
    self.start_time = time.time()
    logger.info(f"Generating speech with {provider_type}: {text[:50]}...")
    
    try:
        # Get Redis client for caching
        redis_client = get_redis_client()
        
        # Check cache if enabled
        if use_cache and redis_client:
            cache_key = f"tts:cache:{provider_type}:{voice_id or 'default'}:{hash(text)}"
            cached_audio = redis_client.get(cache_key)
            if cached_audio:
                logger.info(f"Cache hit for {text[:30]}...")
                return cached_audio
        
        # Get provider
        provider = self._get_provider(provider_type, provider_config)
        
        # Set voice if provided
        if voice_id and hasattr(provider, 'set_voice'):
            provider.set_voice(voice_id)
        
        # Generate speech
        audio_data = provider.generate_speech(text, voice_id, speed)
        
        # Cache result if successful
        if audio_data and use_cache and redis_client:
            redis_client.setex(cache_key, 86400, audio_data)  # 24 hour TTL
        
        return audio_data
        
    except SoftTimeLimitExceeded:
        logger.warning(f"Task timed out: {text[:50]}...")
        raise
        
    except Exception as e:
        logger.error(f"Error generating speech: {e}")
        
        # Retry with exponential backoff
        retry_count = self.request.retries
        max_retries = self.max_retries
        
        if retry_count < max_retries:
            logger.info(f"Retrying task ({retry_count+1}/{max_retries})")
            raise self.retry(exc=e)
        else:
            logger.error(f"Max retries reached, failing task")
            raise

@celery_app.task(bind=True, base=TTSTask, 
                time_limit=300, soft_time_limit=240,
                queue='tts_normal')
def batch_generation_task(self, texts, provider_type, provider_config=None, 
                         voice_id=None, speed=1.0, use_cache=True):
    """
    Generate speech for multiple texts in batch.
    
    Args:
        texts: List of texts to convert to speech
        provider_type: Provider type to use
        provider_config: Provider configuration (optional)
        voice_id: Voice identifier (optional)
        speed: Speech speed factor (default: 1.0)
        use_cache: Whether to use cache (default: True)
        
    Returns:
        Dict[str, bytes]: Dictionary mapping text to audio data
    """
    self.start_time = time.time()
    logger.info(f"Batch generating speech with {provider_type}: {len(texts)} texts")
    
    results = {}
    provider = None
    
    try:
        # Get provider
        provider = self._get_provider(provider_type, provider_config)
        
        # Set voice if provided
        if voice_id and hasattr(provider, 'set_voice'):
            provider.set_voice(voice_id)
        
        # Get Redis client for caching
        redis_client = get_redis_client()
        
        # Process each text
        for text in texts:
            try:
                # Skip empty text
                if not text:
                    continue
                
                # Check cache if enabled
                cache_key = None
                if use_cache and redis_client:
                    cache_key = f"tts:cache:{provider_type}:{voice_id or 'default'}:{hash(text)}"
                    cached_audio = redis_client.get(cache_key)
                    if cached_audio:
                        results[text] = cached_audio
                        continue
                
                # Generate speech
                audio_data = provider.generate_speech(text, voice_id, speed)
                
                # Cache result if successful
                if audio_data and use_cache and redis_client and cache_key:
                    redis_client.setex(cache_key, 86400, audio_data)  # 24 hour TTL
                
                results[text] = audio_data
                
            except Exception as e:
                logger.error(f"Error generating speech for text '{text[:30]}...': {e}")
                results[text] = None
        
        return results
        
    except SoftTimeLimitExceeded:
        logger.warning(f"Batch task timed out")
        return results
        
    except Exception as e:
        logger.error(f"Error in batch generation: {e}")
        raise

@celery_app.task(bind=True, base=TTSTask,
                time_limit=600, soft_time_limit=540,
                queue='tts_low')
def prewarm_task(self, common_phrases, provider_types, voice_ids=None):
    """
    Prewarm TTS providers by generating common phrases.
    
    Args:
        common_phrases: List of common phrases to generate
        provider_types: List of provider types to prewarm
        voice_ids: Dictionary mapping provider types to list of voice IDs
        
    Returns:
        Dict: Results of prewarming
    """
    results = {
        'total': 0,
        'success': 0,
        'errors': 0,
        'providers': {}
    }
    
    logger.info(f"Prewarming {len(provider_types)} providers with {len(common_phrases)} phrases")
    
    voice_ids = voice_ids or {}
    redis_client = get_redis_client()
    
    for provider_type in provider_types:
        try:
            # Get provider
            provider = self._get_provider(provider_type)
            
            # Get voices for this provider
            provider_voices = voice_ids.get(provider_type, [None])
            
            # Initialize provider stats
            results['providers'][provider_type] = {
                'total': 0,
                'success': 0,
                'errors': 0,
                'voices': {}
            }
            
            # Process each voice
            for voice_id in provider_voices:
                # Set voice if provided
                if voice_id and hasattr(provider, 'set_voice'):
                    provider.set_voice(voice_id)
                
                # Initialize voice stats
                results['providers'][provider_type]['voices'][voice_id or 'default'] = {
                    'total': 0,
                    'success': 0,
                    'errors': 0
                }
                
                # Generate speech for each phrase
                for phrase in common_phrases:
                    try:
                        results['total'] += 1
                        results['providers'][provider_type]['total'] += 1
                        results['providers'][provider_type]['voices'][voice_id or 'default']['total'] += 1
                        
                        # Check cache first
                        cache_key = f"tts:cache:{provider_type}:{voice_id or 'default'}:{hash(phrase)}"
                        cached = False
                        
                        if redis_client:
                            cached_audio = redis_client.get(cache_key)
                            if cached_audio:
                                # Already cached
                                cached = True
                        
                        if not cached:
                            # Generate and cache
                            audio_data = provider.generate_speech(phrase, voice_id, 1.0)
                            
                            if audio_data and redis_client:
                                redis_client.setex(cache_key, 86400, audio_data)  # 24 hour TTL
                        
                        # Update success stats
                        results['success'] += 1
                        results['providers'][provider_type]['success'] += 1
                        results['providers'][provider_type]['voices'][voice_id or 'default']['success'] += 1
                        
                    except Exception as e:
                        # Update error stats
                        results['errors'] += 1
                        results['providers'][provider_type]['errors'] += 1
                        results['providers'][provider_type]['voices'][voice_id or 'default']['errors'] += 1
                        logger.error(f"Error prewarming {provider_type} with voice {voice_id} for phrase '{phrase[:30]}...': {e}")
            
        except Exception as e:
            logger.error(f"Error prewarming provider {provider_type}: {e}")
    
    logger.info(f"Prewarming completed: {results['success']}/{results['total']} successful")
    return results 