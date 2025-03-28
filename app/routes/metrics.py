#!/usr/bin/env python
# Metrics Dashboard Routes

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
import statistics

from flask import Blueprint, jsonify, request, render_template, current_app, Response, abort

# Create blueprint
metrics_blueprint = Blueprint('metrics', __name__, url_prefix='/metrics')

logger = logging.getLogger("metrics-api")

@metrics_blueprint.route('/', methods=['GET'])
def metrics_dashboard():
    """Render the main metrics dashboard page."""
    try:
        return render_template('metrics/dashboard.html')
    except Exception as e:
        logger.error(f"Error rendering metrics dashboard: {e}")
        return jsonify({"error": str(e)}), 500

@metrics_blueprint.route('/call/<call_id>', methods=['GET'])
def get_call_metrics(call_id: str):
    """Get detailed metrics for a specific call."""
    try:
        # Access the call quality monitor from the app context
        call_monitor = current_app.tts_service.call_quality_monitor
        metrics = call_monitor.get_call_metrics(call_id)
        
        if not metrics:
            return jsonify({"error": f"Call {call_id} not found"}), 404
            
        return jsonify(metrics)
    except Exception as e:
        logger.error(f"Error retrieving call metrics: {e}")
        return jsonify({"error": str(e)}), 500

@metrics_blueprint.route('/calls', methods=['GET'])
def get_calls_list():
    """Get a list of recent calls with basic info."""
    try:
        # Get time period from query parameters (default to 'today')
        time_period = request.args.get('period', 'today')
        
        # Access the call quality monitor from the app context
        call_monitor = current_app.tts_service.call_quality_monitor
        
        # Filter calls by time period
        calls = call_monitor._filter_calls_by_time_period(time_period)
        
        # Create a simplified list for the API
        calls_list = []
        for call in calls:
            calls_list.append({
                "call_id": call.call_id,
                "started_at": call.started_at,
                "ended_at": call.ended_at,
                "duration": call.duration,
                "status": call.completion_status,
                "error_count": call.error_count,
                "is_active": call.is_active
            })
        
        # Sort by start time, newest first
        calls_list.sort(key=lambda x: x["started_at"], reverse=True)
        
        return jsonify({
            "total_calls": len(calls_list),
            "period": time_period,
            "calls": calls_list
        })
    except Exception as e:
        logger.error(f"Error retrieving calls list: {e}")
        return jsonify({"error": str(e)}), 500

@metrics_blueprint.route('/aggregated', methods=['GET'])
def get_aggregated_metrics():
    """Get aggregated metrics for a time period."""
    try:
        # Get time period from query parameters (default to 'today')
        time_period = request.args.get('period', 'today')
        
        # Access the call quality monitor from the app context
        call_monitor = current_app.tts_service.call_quality_monitor
        
        # Get aggregated metrics
        metrics = call_monitor.get_aggregated_metrics(time_period)
        
        return jsonify({
            "period": time_period,
            "metrics": metrics
        })
    except Exception as e:
        logger.error(f"Error retrieving aggregated metrics: {e}")
        return jsonify({"error": str(e)}), 500

@metrics_blueprint.route('/trends', methods=['GET'])
def get_quality_trends():
    """Get quality trends over time."""
    try:
        # Get time period from query parameters (default to 'week')
        time_period = request.args.get('period', 'week')
        
        # Access the call quality monitor from the app context
        call_monitor = current_app.tts_service.call_quality_monitor
        
        # Get quality trends
        trends = call_monitor.get_quality_trends(time_period)
        
        return jsonify({
            "period": time_period,
            "trends": trends
        })
    except Exception as e:
        logger.error(f"Error retrieving quality trends: {e}")
        return jsonify({"error": str(e)}), 500

@metrics_blueprint.route('/providers', methods=['GET'])
def get_provider_stats():
    """Get statistics about TTS providers."""
    try:
        # Access the TTS service from the app context
        tts_service = current_app.tts_service
        
        # Check if fallback manager exists
        if not hasattr(tts_service, 'fallback_manager'):
            return jsonify({"error": "Fallback manager not available"}), 404
        
        # Get provider statistics from the fallback manager
        fallback_manager = tts_service.fallback_manager
        provider_stats = {
            "primary_provider": fallback_manager.primary_provider_name,
            "current_provider": fallback_manager.current_provider_name,
            "available_providers": fallback_manager.get_available_providers(),
            "health_statuses": fallback_manager.get_provider_statuses(),
            "fallback_stats": fallback_manager.get_statistics()
        }
        
        return jsonify(provider_stats)
    except Exception as e:
        logger.error(f"Error retrieving provider statistics: {e}")
        return jsonify({"error": str(e)}), 500

@metrics_blueprint.route('/benchmark', methods=['GET'])
def get_benchmark_results():
    """Get TTS provider benchmark results."""
    try:
        # Check if benchmark service exists in the app context
        if not hasattr(current_app, 'tts_benchmark'):
            return jsonify({"error": "Benchmark service not available"}), 404
            
        benchmark_service = current_app.tts_benchmark
        
        # Get benchmark results from the service
        results = benchmark_service.get_latest_results()
        
        return jsonify(results)
    except Exception as e:
        logger.error(f"Error retrieving benchmark results: {e}")
        return jsonify({"error": str(e)}), 500

@metrics_blueprint.route('/benchmark/trigger', methods=['POST'])
def trigger_benchmark():
    """Trigger a new benchmark run."""
    try:
        # Check if benchmark service exists in the app context
        if not hasattr(current_app, 'tts_benchmark'):
            return jsonify({"error": "Benchmark service not available"}), 404
            
        # Get parameters from request
        params = request.get_json() or {}
        providers = params.get('providers', [])
        test_text = params.get('test_text', 'This is a benchmark test for TTS providers.')
        iterations = params.get('iterations', 3)
        
        # Validate parameters
        if iterations < 1 or iterations > 10:
            return jsonify({"error": "Iterations must be between 1 and 10"}), 400
            
        # Trigger benchmark
        benchmark_service = current_app.tts_benchmark
        task_id = benchmark_service.start_benchmark(
            providers=providers,
            test_text=test_text,
            iterations=iterations
        )
        
        return jsonify({
            "status": "Benchmark started",
            "task_id": task_id
        })
    except Exception as e:
        logger.error(f"Error triggering benchmark: {e}")
        return jsonify({"error": str(e)}), 500

@metrics_blueprint.route('/benchmark/status/<task_id>', methods=['GET'])
def get_benchmark_status(task_id: str):
    """Get the status of a benchmark task."""
    try:
        # Check if benchmark service exists in the app context
        if not hasattr(current_app, 'tts_benchmark'):
            return jsonify({"error": "Benchmark service not available"}), 404
            
        # Get status from the service
        benchmark_service = current_app.tts_benchmark
        status = benchmark_service.get_task_status(task_id)
        
        if not status:
            return jsonify({"error": f"Task {task_id} not found"}), 404
            
        return jsonify(status)
    except Exception as e:
        logger.error(f"Error retrieving benchmark status: {e}")
        return jsonify({"error": str(e)}), 500

@metrics_blueprint.route('/cache', methods=['GET'])
def get_cache_stats():
    """Get statistics about the TTS cache."""
    try:
        # Access the TTS service from the app context
        tts_service = current_app.tts_service
        
        # Check if cache manager exists
        if not hasattr(tts_service, 'cache_manager'):
            return jsonify({"error": "Cache manager not available"}), 404
            
        # Get cache statistics
        cache_manager = tts_service.cache_manager
        cache_stats = cache_manager.get_statistics()
        
        return jsonify(cache_stats)
    except Exception as e:
        logger.error(f"Error retrieving cache statistics: {e}")
        return jsonify({"error": str(e)}), 500

@metrics_blueprint.route('/voice-pool', methods=['GET'])
def get_voice_pool_stats():
    """Get statistics about the voice pool manager."""
    try:
        # Access the TTS service from the app context
        tts_service = current_app.tts_service
        
        # Check if voice pool manager exists
        if not hasattr(tts_service, 'voice_pool_manager'):
            return jsonify({"error": "Voice pool manager not available"}), 404
            
        # Get voice pool statistics
        voice_pool = tts_service.voice_pool_manager
        pool_stats = {
            "total_providers": voice_pool.get_total_providers(),
            "active_providers": voice_pool.get_active_providers(),
            "available_providers": voice_pool.get_available_providers(),
            "checkout_stats": voice_pool.get_checkout_statistics(),
            "pool_size_history": voice_pool.get_pool_size_history()
        }
        
        return jsonify(pool_stats)
    except Exception as e:
        logger.error(f"Error retrieving voice pool statistics: {e}")
        return jsonify({"error": str(e)}), 500

@metrics_blueprint.route('/streaming', methods=['GET'])
def get_streaming_stats():
    """Get statistics about streaming sessions."""
    try:
        # Access the streaming manager from the app context
        if not hasattr(current_app, 'telnyx_streaming_manager'):
            return jsonify({"error": "Streaming manager not available"}), 404
            
        streaming_manager = current_app.telnyx_streaming_manager
        
        # Get streaming statistics
        stats = streaming_manager.get_statistics()
        
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error retrieving streaming statistics: {e}")
        return jsonify({"error": str(e)}), 500

@metrics_blueprint.route('/health', methods=['GET'])
def get_system_health():
    """Get overall system health metrics."""
    try:
        health_data = {
            "status": "operational",
            "components": {}
        }
        
        # Check TTS service health
        tts_service = current_app.tts_service
        health_data["components"]["tts_service"] = {
            "status": "operational",
            "provider": tts_service.current_provider_name if hasattr(tts_service, 'current_provider_name') else "unknown"
        }
        
        # Check streaming manager health if available
        if hasattr(current_app, 'telnyx_streaming_manager'):
            streaming_manager = current_app.telnyx_streaming_manager
            health_data["components"]["streaming_manager"] = {
                "status": "operational" if streaming_manager.is_healthy() else "degraded",
                "active_sessions": streaming_manager.get_active_session_count()
            }
        
        # Check cache health if available
        if hasattr(tts_service, 'cache_manager'):
            cache_manager = tts_service.cache_manager
            cache_stats = cache_manager.get_statistics()
            health_data["components"]["cache"] = {
                "status": "operational",
                "hit_rate": cache_stats.get("hit_rate", 0)
            }
        
        # Check voice pool health if available
        if hasattr(tts_service, 'voice_pool_manager'):
            voice_pool = tts_service.voice_pool_manager
            health_data["components"]["voice_pool"] = {
                "status": "operational",
                "available_providers": voice_pool.get_available_providers()
            }
        
        # Overall status determination - if any component is not operational, system is degraded
        for component in health_data["components"].values():
            if component["status"] != "operational":
                health_data["status"] = "degraded"
                break
        
        return jsonify(health_data)
    except Exception as e:
        logger.error(f"Error retrieving system health: {e}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

@metrics_blueprint.route('/latency', methods=['GET'])
def get_latency_stats():
    """Get latency statistics for different operations."""
    try:
        # Get time period from query parameters (default to 'today')
        time_period = request.args.get('period', 'today')
        
        # Access the call quality monitor from the app context
        call_monitor = current_app.tts_service.call_quality_monitor
        
        # Filter calls by time period
        calls = call_monitor._filter_calls_by_time_period(time_period)
        
        # Collect latency metrics
        generation_times = []
        first_chunk_latencies = []
        
        for call in calls:
            generation_times.extend(call.generation_times)
            first_chunk_latencies.extend(call.first_chunk_latencies)
        
        # Calculate statistics if data is available
        latency_stats = {
            "period": time_period,
            "tts_generation": {
                "count": len(generation_times),
                "min": min(generation_times) if generation_times else None,
                "max": max(generation_times) if generation_times else None,
                "avg": statistics.mean(generation_times) if generation_times else None,
                "median": statistics.median(generation_times) if generation_times else None,
                "p95": statistics.quantiles(generation_times, n=20)[18] if len(generation_times) >= 20 else None
            },
            "first_chunk": {
                "count": len(first_chunk_latencies),
                "min": min(first_chunk_latencies) if first_chunk_latencies else None,
                "max": max(first_chunk_latencies) if first_chunk_latencies else None,
                "avg": statistics.mean(first_chunk_latencies) if first_chunk_latencies else None,
                "median": statistics.median(first_chunk_latencies) if first_chunk_latencies else None,
                "p95": statistics.quantiles(first_chunk_latencies, n=20)[18] if len(first_chunk_latencies) >= 20 else None
            }
        }
        
        return jsonify(latency_stats)
    except Exception as e:
        logger.error(f"Error retrieving latency statistics: {e}")
        return jsonify({"error": str(e)}), 500

@metrics_blueprint.route('/export/calls', methods=['GET'])
def export_call_data():
    """Export call data as JSON."""
    try:
        # Get time period from query parameters (default to 'today')
        time_period = request.args.get('period', 'today')
        
        # Access the call quality monitor from the app context
        call_monitor = current_app.tts_service.call_quality_monitor
        
        # Filter calls by time period
        calls = call_monitor._filter_calls_by_time_period(time_period)
        
        # Format call data for export
        call_data = []
        for call in calls:
            call_data.append(call_monitor._format_call_metrics(call))
        
        # Create response with JSON data
        response = Response(
            json.dumps(call_data, indent=2),
            mimetype='application/json',
            headers={'Content-Disposition': f'attachment;filename=call_data_{time_period}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'}
        )
        
        return response
    except Exception as e:
        logger.error(f"Error exporting call data: {e}")
        return jsonify({"error": str(e)}), 500

def register_metrics_blueprint(app):
    """Register the metrics blueprint with the Flask app."""
    app.register_blueprint(metrics_blueprint)
    logger.info("Metrics blueprint registered") 