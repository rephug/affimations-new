#!/usr/bin/env python
# Main application for Morning Coffee

import os
import time
import logging
import threading
from typing import Dict, Any, List

from flask import Flask, request, jsonify, Response
from flask_cors import CORS

from config import config
from modules.tts.tts_service import TTSService
from modules.tts.provider_factory import TTSProviderFactory
from modules.tts.fallback_manager import TTSFallbackManager
from modules.tts.voice_pool import VoicePoolManager
from modules.tts.telnyx_streaming import TelnyxStreamingManager
from modules.tts.call_metrics import CallQualityMonitor
from modules.tts.dialog_manager import DialogManager
from modules.tts.cache_manager import TTSCacheManager
from modules.tts.predictive import PredictiveGenerator
from modules.tts.benchmarking import TTSBenchmark
from modules.redis_store import RedisStore
from modules.openai_transcription_handler import OpenAITranscriptionHandler
from modules.assemblyai_handler import AssemblyAIHandler
from modules.telnyx_handler import TelnyxHandler
from modules.llm_handler import LLMHandler
from api_blueprint import api
from webhook_blueprint import webhooks
from routes.metrics import register_metrics_blueprint

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Log to console
        logging.FileHandler(os.path.join('logs', 'app.log'))  # Log to file
    ]
)
logger = logging.getLogger('app')

def create_app(config_obj=None):
    """
    Create and configure the Flask application.
    
    Args:
        config_obj: Optional configuration object to use instead of default config
                   (useful for testing)
    
    Returns:
        Flask application instance
    """
    # Initialize Flask app
    app = Flask(__name__)
    CORS(app)  # Enable CORS for all routes
    
    # Use provided config or default config
    app_config = config_obj or config
    
    # Check configuration
    validation = app_config.validate()
    if not validation['valid']:
        logger.warning(f"Missing required configuration: {', '.join(validation['missing'])}")
        logger.warning("Some functionality may be limited")
    
    # Create directories for logs and cache if they don't exist
    os.makedirs(os.path.join('logs', 'call_metrics'), exist_ok=True)
    os.makedirs(os.path.join('cache', 'tts'), exist_ok=True)
    
    # Initialize service clients
    redis_store = RedisStore(
        host=app_config.REDIS_HOST,
        port=app_config.REDIS_PORT,
        password=app_config.REDIS_PASSWORD,
        db=app_config.REDIS_DB
    )
    
    # Initialize Telnyx handler
    telnyx_handler = TelnyxHandler(
        api_key=app_config.TELNYX_API_KEY,
        phone_number=app_config.TELNYX_PHONE_NUMBER,
        messaging_profile_id=app_config.TELNYX_MESSAGING_PROFILE_ID,
        app_id=app_config.TELNYX_APP_ID
    )
    
    # Initialize the enhanced TTS components
    
    # 1. Initialize the multi-layer cache manager
    cache_manager = TTSCacheManager(
        redis_client=redis_store.redis,
        cache_dir=os.path.join('cache', 'tts'),
        memory_capacity=app_config.TTS_CACHE_MEMORY_CAPACITY,
        redis_ttl=app_config.TTS_CACHE_TTL,
        enable_memory_cache=app_config.TTS_CACHE_MEMORY_ENABLED,
        enable_redis_cache=app_config.TTS_CACHE_REDIS_ENABLED,
        enable_file_cache=app_config.TTS_CACHE_FILE_ENABLED
    )
    
    # 2. Initialize the voice pool manager for provider resource management
    voice_pool_manager = VoicePoolManager(
        initial_pool_size=app_config.TTS_VOICE_POOL_SIZE,
        min_pool_size=app_config.TTS_VOICE_POOL_MIN_SIZE,
        max_pool_size=app_config.TTS_VOICE_POOL_MAX_SIZE,
        provider_ttl=app_config.TTS_VOICE_POOL_TTL,
        provider_factory=TTSProviderFactory(),
        provider_configs=app_config.get_tts_provider_config()
    )
    
    # 3. Initialize the TTS fallback manager for provider failover
    fallback_manager = TTSFallbackManager(
        primary_provider_name=app_config.TTS_PROVIDER,
        fallback_providers=app_config.TTS_FALLBACK_PROVIDERS,
        provider_configs=app_config.get_tts_provider_config(),
        provider_factory=TTSProviderFactory(),
        health_check_interval=app_config.TTS_HEALTH_CHECK_INTERVAL
    )
    
    # 4. Initialize the Telnyx streaming manager for real-time audio
    telnyx_streaming_manager = TelnyxStreamingManager(
        telnyx_api_key=app_config.TELNYX_API_KEY,
        chunk_size_ms=app_config.TTS_STREAMING_CHUNK_SIZE_MS,
        buffer_threshold=app_config.TTS_STREAMING_BUFFER_THRESHOLD,
        max_silence_ms=app_config.TTS_STREAMING_MAX_SILENCE_MS,
        max_active_streams=app_config.TTS_STREAMING_MAX_ACTIVE_STREAMS
    )
    
    # 5. Initialize dialog manager for conversation flow
    dialog_manager = DialogManager(
        initial_fragment_words=app_config.TTS_INITIAL_FRAGMENT_WORDS,
        min_first_fragment_words=app_config.TTS_MIN_FIRST_FRAGMENT_WORDS,
        sentence_pause_ms=app_config.TTS_SENTENCE_PAUSE_MS,
        min_pause_ms=app_config.TTS_MIN_PAUSE_MS,
        break_on_punctuation=app_config.TTS_BREAK_ON_PUNCTUATION.split(',')
    )
    
    # 6. Initialize the TTS service with all the new components
    tts_config = {
        "default_provider": app_config.TTS_PROVIDER,
        "cache_enabled": app_config.TTS_CACHE_ENABLED,
        "cache_ttl": app_config.TTS_CACHE_TTL,
        "provider_config": app_config.get_tts_provider_config(),
        "voice_mapping": app_config.TTS_VOICE_MAPPING
    }
    
    tts_service = TTSService(
        redis_client=redis_store.redis,
        telnyx_handler=telnyx_handler,
        config=tts_config,
        cache_manager=cache_manager,
        fallback_manager=fallback_manager,
        voice_pool_manager=voice_pool_manager,
        dialog_manager=dialog_manager
    )
    
    # 7. Initialize the call quality monitor for metrics collection
    call_quality_monitor = CallQualityMonitor(
        tts_service=tts_service,
        telnyx_streaming_manager=telnyx_streaming_manager
    )
    
    # 8. Initialize predictive generator for prewarming
    predictive_generator = PredictiveGenerator(
        tts_service=tts_service,
        cache_manager=cache_manager,
        prediction_depth=app_config.TTS_PREDICTION_DEPTH,
        min_confidence=app_config.TTS_PREDICTION_MIN_CONFIDENCE
    )
    
    # 9. Initialize TTS benchmark for performance measurement
    tts_benchmark = TTSBenchmark(
        provider_factory=TTSProviderFactory(),
        provider_configs=app_config.get_tts_provider_config(),
        results_dir=os.path.join('logs', 'benchmarks')
    )
    
    # Initialize transcription handlers - use OpenAI if available, fall back to AssemblyAI
    transcription_handler = None
    
    # First try to initialize OpenAI handler if API key is available
    if app_config.OPENAI_API_KEY:
        try:
            transcription_handler = OpenAITranscriptionHandler(
                api_key=app_config.OPENAI_API_KEY,
                model=app_config.OPENAI_TRANSCRIBE_MODEL
            )
            logger.info(f"Using OpenAI for transcription with model: {app_config.OPENAI_TRANSCRIBE_MODEL}")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI transcription handler: {e}")
            transcription_handler = None
    
    # Fall back to AssemblyAI if OpenAI initialization failed or no OpenAI API key
    if transcription_handler is None and app_config.ASSEMBLYAI_API_KEY:
        try:
            transcription_handler = AssemblyAIHandler(
                api_key=app_config.ASSEMBLYAI_API_KEY
            )
            logger.info("Using AssemblyAI for transcription")
        except Exception as e:
            logger.error(f"Failed to initialize AssemblyAI handler: {e}")
            transcription_handler = None
    
    if transcription_handler is None:
        logger.warning("No transcription handler available - call functionality will be limited")
    
    # Initialize LLM handler
    llm_handler = LLMHandler(
        llm_type=app_config.LLM_TYPE,
        api_key=app_config.LLM_API_KEY,
        model=app_config.LLM_MODEL,
        endpoint=app_config.LLM_ENDPOINT
    )
    
    # Register blueprints
    app.register_blueprint(api, url_prefix='/api')
    app.register_blueprint(webhooks, url_prefix='/webhooks')
    register_metrics_blueprint(app)
    
    # Store service clients in app config for access in routes
    app.config['REDIS_STORE'] = redis_store
    app.tts_service = tts_service  # Make directly accessible
    app.telnyx_streaming_manager = telnyx_streaming_manager  # Direct access
    app.tts_benchmark = tts_benchmark  # Direct access
    app.config['TTS_SERVICE'] = tts_service
    app.config['CACHE_MANAGER'] = cache_manager
    app.config['VOICE_POOL_MANAGER'] = voice_pool_manager
    app.config['FALLBACK_MANAGER'] = fallback_manager
    app.config['TELNYX_STREAMING_MANAGER'] = telnyx_streaming_manager
    app.config['CALL_QUALITY_MONITOR'] = call_quality_monitor
    app.config['DIALOG_MANAGER'] = dialog_manager
    app.config['PREDICTIVE_GENERATOR'] = predictive_generator
    app.config['TTS_BENCHMARK'] = tts_benchmark
    app.config['TRANSCRIPTION_HANDLER'] = transcription_handler
    app.config['TELNYX_HANDLER'] = telnyx_handler
    app.config['LLM_HANDLER'] = llm_handler
    
    # Store config in app
    app.config['APP_CONFIG'] = app_config
    
    # Prewarm cache for common phrases if enabled
    if app_config.TTS_PREWARM_ENABLED:
        def prewarm_cache():
            try:
                logger.info("Starting cache prewarming")
                common_phrases = app_config.TTS_PREWARM_PHRASES
                if not common_phrases:
                    logger.warning("No phrases configured for prewarming")
                    return
                    
                # Generate speech for each common phrase
                for phrase in common_phrases:
                    try:
                        # Use default voice
                        tts_service.generate_speech(text=phrase)
                        logger.debug(f"Prewarmed cache for phrase: {phrase[:30]}...")
                    except Exception as e:
                        logger.error(f"Failed to prewarm cache for phrase: {e}")
                
                logger.info(f"Cache prewarming completed for {len(common_phrases)} phrases")
            except Exception as e:
                logger.error(f"Error in cache prewarming: {e}")
        
        # Start prewarming in background thread
        prewarm_thread = threading.Thread(target=prewarm_cache)
        prewarm_thread.daemon = True
        prewarm_thread.start()
    
    # Start the fallback manager's health check thread
    fallback_manager.start_health_check_thread()
    
    logger.info("Morning Coffee application initialized with enhanced TTS components")
    
    # Root endpoint
    @app.route('/')
    def index():
        """Root endpoint with application information."""
        return jsonify({
            "name": "Morning Coffee",
            "version": "1.0.0",
            "description": "A system that sends daily affirmations via SMS, calls users, and enables AI conversation",
            "components": {
                "streaming": telnyx_streaming_manager.is_healthy(),
                "tts_fallback": fallback_manager.is_healthy(),
                "voice_pool": voice_pool_manager.get_available_providers() > 0
            }
        })
    
    # Enhanced health check endpoint
    @app.route('/health')
    def health():
        """Comprehensive health check endpoint."""
        start_time = time.time()
        
        # Check Redis connection
        redis_health = redis_store.health_check()
        
        # Check TTS service
        tts_health = tts_service.health_check()
        
        # Check new components
        fallback_health = {
            "status": "ok" if fallback_manager.is_healthy() else "degraded",
            "current_provider": fallback_manager.current_provider_name,
            "healthy_providers": len(fallback_manager.get_healthy_providers())
        }
        
        voice_pool_health = {
            "status": "ok" if voice_pool_manager.get_available_providers() > 0 else "degraded",
            "available_providers": voice_pool_manager.get_available_providers(),
            "total_providers": voice_pool_manager.get_total_providers()
        }
        
        streaming_health = {
            "status": "ok" if telnyx_streaming_manager.is_healthy() else "degraded",
            "active_sessions": telnyx_streaming_manager.get_active_session_count(),
            "uptime_seconds": telnyx_streaming_manager.get_uptime_seconds()
        }
        
        cache_health = {
            "status": "ok",
            "hit_rate": cache_manager.get_hit_rate(),
            "total_requests": cache_manager.get_total_requests()
        }
        
        # Overall health status - only consider Redis critical at startup
        status_checks = [
            redis_health['status'] == 'ok',
            fallback_health['status'] == 'ok',
            voice_pool_health['status'] == 'ok',
            streaming_health['status'] == 'ok'
        ]
        
        if all(status_checks):
            overall_status = "ok"
        elif redis_health['status'] != 'ok':
            overall_status = "error"
        else:
            overall_status = "degraded"
        
        # Assemble response
        health_data = {
            "status": overall_status,
            "timestamp": time.time(),
            "checks": {
                "redis": redis_health,
                "tts": tts_health,
                "fallback_manager": fallback_health,
                "voice_pool": voice_pool_health,
                "streaming": streaming_health,
                "cache": cache_health
            },
            "response_time_ms": int((time.time() - start_time) * 1000)
        }
        
        # Add transcription service check if available
        if transcription_handler:
            try:
                transcription_health = transcription_handler.health_check()
                health_data["checks"]["transcription"] = transcription_health
                if transcription_health.get("status") != "healthy":
                    overall_status = "degraded"
            except Exception as e:
                logger.error(f"Error checking transcription service health: {e}")
                health_data["checks"]["transcription"] = {
                    "status": "error",
                    "message": str(e)
                }
                overall_status = "degraded"
        
        # Add LLM service check
        if llm_handler:
            try:
                llm_health_result = llm_handler.health_check()
                # Handle boolean return from LLM handler
                if isinstance(llm_health_result, bool):
                    llm_health = {"status": "ok" if llm_health_result else "error"}
                else:
                    llm_health = llm_health_result
                    
                health_data["checks"]["llm"] = llm_health
                if not llm_health_result:
                    overall_status = "degraded"
            except Exception as e:
                logger.error(f"LLM health check failed: {e}")
                health_data["checks"]["llm"] = {"status": "error", "message": str(e)}
                overall_status = "degraded"
        
        # Update overall status
        health_data["status"] = overall_status
        
        # Return with appropriate status code
        status_code = 200 if overall_status == "ok" else 500 if overall_status == "error" else 200
        return jsonify(health_data), status_code
    
    # Development routes (disabled in production)
    if app_config.DEBUG:
        @app.route('/dev/tts/test', methods=['POST'])
        def test_tts():
            """Test TTS generation."""
            data = request.json
            if not data or 'text' not in data:
                return jsonify({"error": "Text is required"}), 400
                
            voice_id = data.get('voice_id')
            voice_style = data.get('style')
            
            # Use voice_style if provided (for OpenAI-style voice instructions)
            if voice_style and tts_service.supports_capability("voice_style"):
                # Generate speech using voice style instruction
                audio_bytes = tts_service.generate_with_style(
                    text=data['text'],
                    style=voice_style
                )
            else:
                # Generate speech using regular voice ID
                audio_bytes = tts_service.generate_speech(
                    text=data['text'],
                    voice_id=voice_id
                )
                
            if not audio_bytes:
                return jsonify({"error": "TTS failed"}), 500
                
            # Return audio as binary response
            return Response(audio_bytes, mimetype='audio/wav')
            
        @app.route('/dev/tts/test_stream', methods=['POST'])
        def test_tts_stream():
            """Test TTS streaming generation."""
            data = request.json
            if not data or 'text' not in data:
                return jsonify({"error": "Text is required"}), 400
                
            voice_id = data.get('voice_id')
            call_id = data.get('call_id', 'test-call-' + str(int(time.time())))
            
            # Start monitoring this test call
            call_quality_monitor.start_call_monitoring(call_id, {"type": "test"})
            
            try:
                # Create audio player to play the streamed audio
                from modules.tts.audio_player import AudioPlayer
                player = AudioPlayer(sample_rate=24000)
                
                # Generate streaming speech
                for chunk in tts_service.generate_speech_stream(
                    text=data['text'],
                    voice_id=voice_id,
                    call_id=call_id
                ):
                    player.add_chunk(chunk)
                
                # Start playback once we have some chunks
                player.start()
                
                # Wait for playback to complete
                player.wait_for_completion()
                
                return jsonify({
                    "status": "success",
                    "message": f"Streaming completed for call {call_id}"
                })
            except Exception as e:
                logger.error(f"Error in TTS streaming test: {e}")
                call_quality_monitor.record_error(call_id, "streaming_test", str(e))
                return jsonify({"error": f"Streaming failed: {str(e)}"}), 500
            finally:
                # End call monitoring
                call_quality_monitor.end_call_monitoring(call_id)
        
        @app.route('/dev/tts/providers', methods=['GET'])
        def list_providers():
            """List available TTS providers and their status."""
            providers = fallback_manager.get_provider_statuses()
            return jsonify({
                "primary": fallback_manager.primary_provider_name,
                "current": fallback_manager.current_provider_name,
                "providers": providers
            })
            
        @app.route('/dev/tts/fallback/test', methods=['POST'])
        def test_fallback():
            """Test fallback functionality by forcing a provider failure."""
            data = request.json or {}
            provider = data.get('provider')
            
            if not provider:
                return jsonify({"error": "Provider name is required"}), 400
            
            # Force a provider to fail
            fallback_manager.mark_provider_failed(provider)
            
            return jsonify({
                "status": "success",
                "message": f"Provider {provider} marked as failed",
                "current_provider": fallback_manager.current_provider_name
            })
            
        @app.route('/dev/tts/benchmark/run', methods=['POST'])
        def run_benchmark():
            """Run TTS benchmark test."""
            data = request.json or {}
            providers = data.get('providers', [])
            text = data.get('text', 'This is a benchmark test for TTS providers.')
            iterations = data.get('iterations', 3)
            
            task_id = tts_benchmark.start_benchmark(
                providers=providers,
                test_text=text,
                iterations=iterations
            )
            
            return jsonify({
                "status": "benchmark_started",
                "task_id": task_id,
                "message": f"Benchmark started with {len(providers) or 'all'} providers"
            })
        
        @app.route('/dev/tts/benchmark/status/<task_id>', methods=['GET'])
        def get_benchmark_status(task_id):
            """Get the status of a benchmark task."""
            status = tts_benchmark.get_task_status(task_id)
            
            return jsonify({
                "task_id": task_id,
                "status": status["status"],
                "progress": status.get("progress", 0),
                "results": status.get("results", {})
            })
        
        @app.route('/dev/tts/benchmark/compare', methods=['POST'])
        def compare_providers():
            """Compare multiple TTS providers for the same text."""
            data = request.json or {}
            text = data.get('text', 'This is a comparison test for TTS providers.')
            providers = data.get('providers', fallback_manager.get_all_provider_names())
            voice_id = data.get('voice_id', 'default_female')
            
            results = {}
            
            # Test each provider
            for provider_name in providers:
                try:
                    # Switch to this provider
                    fallback_manager.force_provider(provider_name)
                    
                    # Generate speech and measure time
                    start_time = time.time()
                    audio_data = tts_service.generate_speech(text=text, voice_id=voice_id)
                    end_time = time.time()
                    
                    results[provider_name] = {
                        "success": audio_data is not None,
                        "generation_time": end_time - start_time,
                        "audio_size": len(audio_data) if audio_data else 0
                    }
                except Exception as e:
                    results[provider_name] = {
                        "success": False,
                        "error": str(e)
                    }
            
            # Restore original provider
            fallback_manager.reset_to_primary()
            
            return jsonify({
                "text": text,
                "voice_id": voice_id,
                "results": results
            })
            
        @app.route('/dev/tts/benchmark/latency', methods=['POST'])
        def test_latency():
            """Test latency characteristics for TTS providers."""
            data = request.json or {}
            text = data.get('text', 'This is a latency test for TTS streaming.')
            provider = data.get('provider')
            voice_id = data.get('voice_id', 'default_female')
            
            # If provider specified, force it
            original_provider = None
            if provider:
                original_provider = fallback_manager.current_provider_name
                fallback_manager.force_provider(provider)
            
            results = {
                "provider": fallback_manager.current_provider_name,
                "voice_id": voice_id,
                "text": text
            }
            
            try:
                # Test batch generation
                start_time = time.time()
                audio_data = tts_service.generate_speech(text=text, voice_id=voice_id)
                batch_time = time.time() - start_time
                
                results["batch"] = {
                    "success": audio_data is not None,
                    "total_time": batch_time,
                    "audio_size": len(audio_data) if audio_data else 0
                }
                
                # Test streaming generation
                start_time = time.time()
                first_chunk_time = None
                total_chunks = 0
                total_audio_size = 0
                
                for chunk in tts_service.generate_speech_stream(text=text, voice_id=voice_id):
                    if first_chunk_time is None:
                        first_chunk_time = time.time() - start_time
                    
                    total_chunks += 1
                    total_audio_size += len(chunk)
                
                stream_total_time = time.time() - start_time
                
                results["streaming"] = {
                    "success": True,
                    "time_to_first_chunk": first_chunk_time,
                    "total_time": stream_total_time,
                    "chunk_count": total_chunks,
                    "audio_size": total_audio_size
                }
                
                # Test dialog-optimized streaming
                start_time = time.time()
                first_chunk_time = None
                total_chunks = 0
                total_audio_size = 0
                
                for chunk in tts_service.generate_dialog_speech_stream(text=text, voice_id=voice_id):
                    if first_chunk_time is None:
                        first_chunk_time = time.time() - start_time
                    
                    total_chunks += 1
                    total_audio_size += len(chunk)
                
                dialog_total_time = time.time() - start_time
                
                results["dialog"] = {
                    "success": True,
                    "time_to_first_chunk": first_chunk_time,
                    "total_time": dialog_total_time,
                    "chunk_count": total_chunks,
                    "audio_size": total_audio_size
                }
                
            except Exception as e:
                logger.error(f"Error in latency test: {e}")
                results["error"] = str(e)
            
            # Restore original provider if needed
            if original_provider:
                fallback_manager.force_provider(original_provider)
            
            return jsonify(results)
            
        @app.route('/dev/monitoring/test', methods=['POST'])
        def test_monitoring():
            """Test call quality monitoring with simulated metrics."""
            data = request.json or {}
            call_id = data.get('call_id', f'test-monitoring-{int(time.time())}')
            duration = data.get('duration', 30)
            error_count = data.get('error_count', 0)
            
            # Start monitoring
            call_quality_monitor.start_call_monitoring(call_id, {"type": "test_monitoring"})
            
            # Simulate some metrics
            call_quality_monitor.start_call_phase(call_id, "greeting")
            call_quality_monitor.record_generation(call_id, 0.5, 100)
            
            # Simulate errors if requested
            for i in range(error_count):
                call_quality_monitor.record_error(
                    call_id, 
                    "test_error", 
                    f"Test error {i+1}", 
                    "test_component"
                )
            
            # Simulate user responses
            call_quality_monitor.record_user_response(call_id, "speech", 2.5)
            call_quality_monitor.end_call_phase(call_id, "greeting")
            
            # End monitoring
            call_quality_monitor.end_call_monitoring(call_id, "completed")
            
            return jsonify({
                "status": "success",
                "call_id": call_id,
                "message": f"Test monitoring completed for call {call_id}"
            })
        
        @app.route('/dev/monitoring/metrics/<call_id>', methods=['GET'])
        def get_call_metrics(call_id):
            """Get metrics for a specific call."""
            metrics = call_quality_monitor.get_call_metrics(call_id)
            
            if not metrics:
                return jsonify({"error": f"No metrics found for call {call_id}"}), 404
            
            return jsonify(metrics)
        
        @app.route('/dev/monitoring/stats', methods=['GET'])
        def get_monitoring_stats():
            """Get aggregated monitoring statistics."""
            time_period = request.args.get('period', 'day')  # day, week, month
            
            stats = call_quality_monitor.get_aggregated_stats(time_period)
            
            return jsonify({
                "period": time_period,
                "stats": stats
            })
        
        @app.route('/dev/cache/clear', methods=['POST'])
        def clear_cache():
            """Clear the TTS cache."""
            data = request.json or {}
            scope = data.get('scope', 'all')  # all, memory, redis, file
            
            if scope == 'all':
                cache_manager.clear_all()
            elif scope == 'memory':
                cache_manager.clear_memory_cache()
            elif scope == 'redis':
                cache_manager.clear_redis_cache()
            elif scope == 'file':
                cache_manager.clear_file_cache()
            else:
                return jsonify({"error": f"Invalid scope: {scope}"}), 400
                
            return jsonify({
                "status": "success",
                "message": f"Cache cleared (scope: {scope})"
            })
        
        @app.route('/dev/cache/stats', methods=['GET'])
        def get_cache_stats():
            """Get cache statistics."""
            stats = {
                "memory": cache_manager.get_memory_cache_stats(),
                "redis": cache_manager.get_redis_cache_stats(),
                "file": cache_manager.get_file_cache_stats(),
                "hit_rate": cache_manager.get_hit_rate(),
                "miss_rate": cache_manager.get_miss_rate(),
                "total_requests": cache_manager.get_total_requests()
            }
            
            return jsonify(stats)
        
        @app.route('/dev/tts/dialog/test', methods=['POST'])
        def test_dialog():
            """Test the dialog manager with a conversation snippet."""
            data = request.json or {}
            text = data.get('text', 'Hello there. How are you doing today? I hope you are having a great day!')
            voice_id = data.get('voice_id', 'default_female')
            
            # Process text through dialog manager
            fragments = dialog_manager.process_dialog_turn(text)
            
            # Return the dialog fragments and timing information
            return jsonify({
                "text": text,
                "fragments": fragments,
                "total_fragments": len(fragments),
                "fragment_words": [len(f["fragment"].split()) for f in fragments]
            })
            
        @app.route('/dev/voice-pool/stats', methods=['GET'])
        def get_voice_pool_stats():
            """Get voice pool statistics."""
            stats = {
                "total_providers": voice_pool_manager.get_total_providers(),
                "available_providers": voice_pool_manager.get_available_providers(),
                "checkout_count": voice_pool_manager.get_checkout_count(),
                "creation_count": voice_pool_manager.get_creation_count(),
                "provider_types": voice_pool_manager.get_provider_types()
            }
            
            return jsonify(stats)
        
        @app.route('/dev/performance/stress-test', methods=['POST'])
        def run_stress_test():
            """Run a stress test for TTS generation with multiple concurrent requests."""
            data = request.json or {}
            concurrent_requests = data.get('concurrent_requests', 5)
            text = data.get('text', 'This is a stress test for the TTS system.')
            voice_id = data.get('voice_id', 'default_female')
            
            results = []
            start_time = time.time()
            
            def process_request(index):
                request_start = time.time()
                try:
                    audio_data = tts_service.generate_speech(text=text, voice_id=voice_id)
                    return {
                        "index": index,
                        "success": audio_data is not None,
                        "time": time.time() - request_start,
                        "audio_size": len(audio_data) if audio_data else 0
                    }
                except Exception as e:
                    return {
                        "index": index,
                        "success": False,
                        "error": str(e),
                        "time": time.time() - request_start
                    }
            
            # Create and start threads
            threads = []
            for i in range(concurrent_requests):
                t = threading.Thread(target=lambda idx=i: results.append(process_request(idx)))
                threads.append(t)
                t.start()
            
            # Wait for all threads to complete
            for t in threads:
                t.join()
            
            total_time = time.time() - start_time
            success_count = sum(1 for r in results if r.get("success", False))
            
            return jsonify({
                "concurrent_requests": concurrent_requests,
                "total_time": total_time,
                "success_count": success_count,
                "requests_per_second": concurrent_requests / total_time if total_time > 0 else 0,
                "results": results
            })
            
        @app.route('/dev/predictive/test', methods=['POST'])
        def test_predictive_generation():
            """Test predictive generation for likely next phrases."""
            data = request.json or {}
            context = data.get('context', 'Hello')
            depth = data.get('depth', 2)
            
            predictions = predictive_generator.predict_next_phrases(context, depth)
            
            return jsonify({
                "context": context,
                "depth": depth,
                "predictions": predictions,
                "total_predictions": len(predictions)
            })
    
    return app

# Run the application
if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=config.PORT, debug=config.DEBUG) 