#!/usr/bin/env python
# TTS Benchmarking Module

import time
import logging
import json
import io
import os
from typing import Dict, Any, List, Optional, Tuple, Generator
from collections import defaultdict
import statistics
import datetime

# Optional visualization imports - will gracefully degrade if not available
try:
    import matplotlib.pyplot as plt
    import numpy as np
    VISUALIZATION_AVAILABLE = True
except ImportError:
    VISUALIZATION_AVAILABLE = False

logger = logging.getLogger("tts-benchmark")

class TTSBenchmark:
    """
    Benchmark TTS provider performance.
    
    This class measures and compares performance metrics across different TTS providers,
    including latency, throughput, and audio quality characteristics.
    """
    
    def __init__(self, tts_service):
        """
        Initialize benchmark with TTS service.
        
        Args:
            tts_service: The TTSService instance to benchmark
        """
        self.tts_service = tts_service
        self.results = []  # Store historical benchmark results
        self.result_timestamps = []  # Timestamps for each benchmark run
        
        # Default test phrases with different characteristics
        self.default_test_phrases = [
            # Short phrase
            "Hello, how are you today?",
            # Medium length with punctuation
            "Welcome to our service. We're excited to help you with your needs. Please let us know how we can assist you.",
            # Long complex text with various punctuation
            "The quick brown fox jumps over the lazy dog. This pangram contains all letters of the English alphabet. It's commonly used to test fonts, keyboards, and other text-processing systems. How efficiently can different TTS systems handle this varied content? That's what we're measuring today!"
        ]

    def benchmark_providers(self, text: Optional[str] = None, 
                            voice_ids: Optional[List[str]] = None,
                            test_streaming: bool = True,
                            iterations: int = 3,
                            warm_up: bool = True) -> Dict[str, Any]:
        """
        Benchmark all available providers with the given text.
        
        Args:
            text: Text to synthesize (or None to use default test phrases)
            voice_ids: List of voice IDs to test
            test_streaming: Whether to test streaming capabilities
            iterations: Number of iterations for each test for consistent results
            warm_up: Whether to perform a warm-up run before benchmarking
            
        Returns:
            Dictionary of benchmark results
        """
        # Use default test text if none provided
        if text is None:
            # Use middle length text from defaults
            text = self.default_test_phrases[1]
        
        # Use default voice IDs if none provided
        if voice_ids is None:
            voice_ids = ["default_female", "default_male"]
        
        logger.info(f"Starting benchmark with {len(voice_ids)} voices, streaming={test_streaming}")
        
        all_results = {}
        fallback_manager = getattr(self.tts_service, 'fallback_manager', None)
        
        if not fallback_manager:
            # Just test the current provider
            provider_name = self._get_provider_name(self.tts_service.provider)
            provider_results = self._benchmark_provider(
                self.tts_service.provider, 
                provider_name,
                text, 
                voice_ids,
                test_streaming,
                iterations,
                warm_up
            )
            all_results[provider_name] = provider_results
        else:
            # Test primary provider
            primary_name = fallback_manager.primary_provider_name
            logger.info(f"Benchmarking primary provider: {primary_name}")
            primary_results = self._benchmark_provider(
                fallback_manager.primary_provider,
                primary_name,
                text,
                voice_ids,
                test_streaming,
                iterations,
                warm_up
            )
            all_results[primary_name] = primary_results
            
            # Test fallback providers
            for provider_name in fallback_manager.fallback_provider_names:
                try:
                    logger.info(f"Benchmarking fallback provider: {provider_name}")
                    # Get provider instance
                    provider_config = self.tts_service.config.get("provider_config", {}).get(provider_name, {})
                    provider = self.tts_service.tts_factory.create_provider(
                        provider_name, self.tts_service.redis_client, provider_config
                    )
                    
                    # Benchmark this provider
                    provider_results = self._benchmark_provider(
                        provider,
                        provider_name,
                        text,
                        voice_ids,
                        test_streaming,
                        iterations,
                        warm_up
                    )
                    all_results[provider_name] = provider_results
                except Exception as e:
                    logger.error(f"Error benchmarking provider {provider_name}: {e}")
                    all_results[provider_name] = {
                        "provider": provider_name,
                        "error": str(e),
                        "batch": {},
                        "streaming": None
                    }
        
        # Store results with timestamp
        timestamp = datetime.datetime.now().isoformat()
        benchmark_data = {
            "timestamp": timestamp,
            "text": text,
            "voice_ids": voice_ids,
            "test_streaming": test_streaming,
            "iterations": iterations,
            "results": all_results
        }
        
        self.results.append(benchmark_data)
        self.result_timestamps.append(timestamp)
        
        logger.info(f"Benchmark completed for {len(all_results)} providers")
        return all_results
    
    def _benchmark_provider(self, provider, provider_name: str, text: str,
                          voice_ids: List[str], test_streaming: bool, 
                          iterations: int, warm_up: bool) -> Dict[str, Any]:
        """
        Benchmark a specific provider.
        
        Args:
            provider: Provider instance
            provider_name: Provider name
            text: Text to synthesize
            voice_ids: Voice IDs to test
            test_streaming: Whether to test streaming
            iterations: Number of iterations for each test
            warm_up: Whether to perform warm-up runs
            
        Returns:
            Benchmark results for this provider
        """
        results = {
            "provider": provider_name,
            "batch": defaultdict(dict),
            "streaming": defaultdict(dict) if test_streaming else None,
            "metrics": {
                "character_rate": 0,
                "audio_ratio": 0,
                "avg_latency": 0
            }
        }
        
        # Count characters (excluding spaces) for throughput calculation
        char_count = len([c for c in text if not c.isspace()])
        
        # Test batch synthesis
        for voice_id in voice_ids:
            batch_times = []
            batch_sizes = []
            success = False
            error = None
            
            try:
                # Warm up if requested
                if warm_up:
                    try:
                        provider.generate_speech("Hello world", voice_id)
                    except Exception as e:
                        logger.warning(f"Warm-up failed for {provider_name} with voice {voice_id}: {e}")
                
                # Run benchmark iterations
                for i in range(iterations):
                    try:
                        # Benchmark batch generation
                        start_time = time.time()
                        audio_data = provider.generate_speech(text, voice_id)
                        end_time = time.time()
                        
                        if audio_data:
                            success = True
                            generation_time = end_time - start_time
                            batch_times.append(generation_time)
                            batch_sizes.append(len(audio_data))
                    except Exception as e:
                        logger.error(f"Iteration {i} failed for {provider_name} with voice {voice_id}: {e}")
                        error = str(e)
                
                # Calculate statistics if successful iterations
                if batch_times:
                    results["batch"][voice_id] = {
                        "success": True,
                        "avg_time": statistics.mean(batch_times),
                        "min_time": min(batch_times),
                        "max_time": max(batch_times),
                        "std_dev": statistics.stdev(batch_times) if len(batch_times) > 1 else 0,
                        "avg_audio_size": statistics.mean(batch_sizes),
                        "character_rate": char_count / statistics.mean(batch_times),
                        "iterations_completed": len(batch_times),
                        "iterations_requested": iterations
                    }
                else:
                    results["batch"][voice_id] = {
                        "success": False,
                        "error": error or "No successful iterations"
                    }
            except Exception as e:
                results["batch"][voice_id] = {
                    "success": False,
                    "error": str(e)
                }
        
        # Test streaming synthesis if requested
        if test_streaming and hasattr(provider, 'generate_speech_stream'):
            for voice_id in voice_ids:
                streaming_times = []
                first_chunk_times = []
                chunk_counts = []
                audio_sizes = []
                success = False
                error = None
                
                try:
                    # Run benchmark iterations
                    for i in range(iterations):
                        try:
                            # Prepare text for streaming - split into sentences
                            sentences = [s.strip() + "." for s in text.split(".") if s.strip()]
                            
                            # If provider expects generator, create one; otherwise use text directly
                            if hasattr(provider, 'accepts_generator') and provider.accepts_generator:
                                text_input = (sentence for sentence in sentences)
                            else:
                                text_input = text
                            
                            # Benchmark streaming
                            start_time = time.time()
                            first_chunk_time = None
                            total_audio_size = 0
                            chunk_count = 0
                            
                            for chunk in provider.generate_speech_stream(text_input, voice_id):
                                # Record time to first chunk
                                if first_chunk_time is None:
                                    first_chunk_time = time.time()
                                
                                total_audio_size += len(chunk)
                                chunk_count += 1
                            
                            end_time = time.time()
                            
                            # Record successful iteration
                            success = True
                            total_time = end_time - start_time
                            streaming_times.append(total_time)
                            
                            if first_chunk_time is not None:
                                first_chunk_times.append(first_chunk_time - start_time)
                                
                            chunk_counts.append(chunk_count)
                            audio_sizes.append(total_audio_size)
                        except Exception as e:
                            logger.error(f"Streaming iteration {i} failed for {provider_name} with voice {voice_id}: {e}")
                            error = str(e)
                    
                    # Calculate statistics if successful iterations
                    if streaming_times:
                        results["streaming"][voice_id] = {
                            "success": True,
                            "avg_total_time": statistics.mean(streaming_times),
                            "avg_first_chunk_time": statistics.mean(first_chunk_times) if first_chunk_times else None,
                            "avg_chunk_count": statistics.mean(chunk_counts),
                            "avg_audio_size": statistics.mean(audio_sizes),
                            "character_rate": char_count / statistics.mean(streaming_times),
                            "iterations_completed": len(streaming_times),
                            "iterations_requested": iterations
                        }
                    else:
                        results["streaming"][voice_id] = {
                            "success": False,
                            "error": error or "No successful iterations"
                        }
                except Exception as e:
                    results["streaming"][voice_id] = {
                        "success": False,
                        "error": str(e)
                    }
        
        # Calculate aggregated metrics
        successful_batch_voices = [v for v in results["batch"].values() if v.get("success", False)]
        if successful_batch_voices:
            # Character rate (chars/sec) - higher is better
            char_rates = [r.get("character_rate", 0) for r in successful_batch_voices]
            results["metrics"]["character_rate"] = statistics.mean(char_rates)
            
            # Average latency - lower is better
            latencies = [r.get("avg_time", 0) for r in successful_batch_voices]
            results["metrics"]["avg_latency"] = statistics.mean(latencies)
        
        if test_streaming and results["streaming"]:
            successful_streaming_voices = [v for v in results["streaming"].values() if v.get("success", False)]
            if successful_streaming_voices:
                # First chunk latency - lower is better
                first_chunk_latencies = [
                    r.get("avg_first_chunk_time", 0) 
                    for r in successful_streaming_voices 
                    if r.get("avg_first_chunk_time") is not None
                ]
                if first_chunk_latencies:
                    results["metrics"]["avg_first_chunk_latency"] = statistics.mean(first_chunk_latencies)
        
        return results
    
    def generate_report(self, results: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate a comprehensive report from benchmark results.
        
        Args:
            results: Benchmark results or None to use last results
            
        Returns:
            Dictionary with report and generated charts
        """
        if results is None:
            if not self.results:
                return {"error": "No benchmark results available"}
            results = self.results[-1]["results"]
        
        report = {
            "summary": {},
            "provider_comparison": {},
            "voice_comparison": {},
            "streaming_vs_batch": {},
            "details": results,
            "charts": {}
        }
        
        # Get list of all providers
        providers = list(results.keys())
        
        # Generate provider comparison
        batch_latencies = []
        batch_char_rates = []
        streaming_latencies = []
        first_chunk_latencies = []
        provider_data = {}
        
        for provider_name, provider_results in results.items():
            provider_data[provider_name] = {"batch": {}, "streaming": {}}
            
            # Calculate average batch metrics
            batch_times = []
            batch_sizes = []
            char_rates = []
            
            for voice_id, voice_results in provider_results.get("batch", {}).items():
                if voice_results.get("success", False):
                    batch_times.append(voice_results.get("avg_time", 0))
                    batch_sizes.append(voice_results.get("avg_audio_size", 0))
                    char_rates.append(voice_results.get("character_rate", 0))
            
            if batch_times:
                avg_batch_time = statistics.mean(batch_times)
                avg_char_rate = statistics.mean(char_rates)
                batch_latencies.append(avg_batch_time)
                batch_char_rates.append(avg_char_rate)
                
                provider_data[provider_name]["batch"] = {
                    "avg_latency": avg_batch_time,
                    "avg_char_rate": avg_char_rate,
                    "avg_size": statistics.mean(batch_sizes) if batch_sizes else 0
                }
                
                report["summary"][provider_name] = {
                    "avg_batch_latency": avg_batch_time,
                    "avg_char_rate": avg_char_rate
                }
            
            # Calculate streaming metrics if available
            if provider_results.get("streaming"):
                streaming_times = []
                first_chunk_times = []
                
                for voice_id, voice_results in provider_results["streaming"].items():
                    if voice_results.get("success", False):
                        streaming_times.append(voice_results.get("avg_total_time", 0))
                        if voice_results.get("avg_first_chunk_time") is not None:
                            first_chunk_times.append(voice_results.get("avg_first_chunk_time", 0))
                
                if streaming_times:
                    avg_streaming_time = statistics.mean(streaming_times)
                    streaming_latencies.append(avg_streaming_time)
                    
                    provider_data[provider_name]["streaming"]["avg_latency"] = avg_streaming_time
                    report["summary"][provider_name]["avg_streaming_latency"] = avg_streaming_time
                
                if first_chunk_times:
                    avg_first_chunk_time = statistics.mean(first_chunk_times)
                    first_chunk_latencies.append(avg_first_chunk_time)
                    
                    provider_data[provider_name]["streaming"]["avg_first_chunk_latency"] = avg_first_chunk_time
                    report["summary"][provider_name]["avg_first_chunk_latency"] = avg_first_chunk_time
        
        # Add provider comparison data
        report["provider_comparison"] = provider_data
        
        # Generate charts if visualization is available
        if VISUALIZATION_AVAILABLE:
            # Batch latency chart
            if batch_latencies:
                try:
                    fig, ax = plt.subplots(figsize=(10, 6))
                    y_pos = np.arange(len(providers))
                    ax.barh(y_pos, batch_latencies, align='center')
                    ax.set_yticks(y_pos)
                    ax.set_yticklabels(providers)
                    ax.invert_yaxis()  # Labels read top-to-bottom
                    ax.set_xlabel('Time (seconds)')
                    ax.set_title('Batch Synthesis Latency by Provider')
                    
                    buf = io.BytesIO()
                    fig.savefig(buf, format='png')
                    buf.seek(0)
                    
                    report["charts"]["batch_latency"] = buf.getvalue()
                    plt.close(fig)
                except Exception as e:
                    logger.error(f"Error generating batch latency chart: {e}")
            
            # Character rate chart
            if batch_char_rates:
                try:
                    fig, ax = plt.subplots(figsize=(10, 6))
                    y_pos = np.arange(len(providers))
                    ax.barh(y_pos, batch_char_rates, align='center')
                    ax.set_yticks(y_pos)
                    ax.set_yticklabels(providers)
                    ax.invert_yaxis()
                    ax.set_xlabel('Characters per second')
                    ax.set_title('Character Processing Rate by Provider')
                    
                    buf = io.BytesIO()
                    fig.savefig(buf, format='png')
                    buf.seek(0)
                    
                    report["charts"]["char_rate"] = buf.getvalue()
                    plt.close(fig)
                except Exception as e:
                    logger.error(f"Error generating character rate chart: {e}")
            
            # Streaming latency chart (combined with first chunk latency)
            if streaming_latencies and first_chunk_latencies:
                try:
                    fig, ax = plt.subplots(figsize=(10, 6))
                    x = np.arange(len(providers))
                    width = 0.35
                    
                    ax.bar(x - width/2, first_chunk_latencies, width, label='First Chunk Latency')
                    ax.bar(x + width/2, streaming_latencies, width, label='Total Streaming Latency')
                    
                    ax.set_ylabel('Time (seconds)')
                    ax.set_title('Streaming Synthesis Latency by Provider')
                    ax.set_xticks(x)
                    ax.set_xticklabels(providers)
                    ax.legend()
                    
                    buf = io.BytesIO()
                    fig.savefig(buf, format='png')
                    buf.seek(0)
                    
                    report["charts"]["streaming_latency"] = buf.getvalue()
                    plt.close(fig)
                except Exception as e:
                    logger.error(f"Error generating streaming latency chart: {e}")
        
        return report
    
    def save_report(self, report: Dict[str, Any], output_dir: str) -> str:
        """
        Save benchmark report to disk.
        
        Args:
            report: Report data from generate_report()
            output_dir: Directory to save report
            
        Returns:
            Path to saved report directory
        """
        # Create timestamped directory for this report
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        report_dir = os.path.join(output_dir, f"tts_benchmark_{timestamp}")
        
        try:
            os.makedirs(report_dir, exist_ok=True)
            
            # Save summary as JSON
            summary_path = os.path.join(report_dir, "summary.json")
            with open(summary_path, 'w') as f:
                # Create a copy without binary data
                report_copy = {k: v for k, v in report.items() if k != 'charts'}
                json.dump(report_copy, f, indent=2)
            
            # Save charts as PNG files
            for chart_name, chart_data in report.get("charts", {}).items():
                chart_path = os.path.join(report_dir, f"{chart_name}.png")
                with open(chart_path, 'wb') as f:
                    f.write(chart_data)
            
            logger.info(f"Benchmark report saved to {report_dir}")
            return report_dir
        
        except Exception as e:
            logger.error(f"Error saving benchmark report: {e}")
            return None
    
    def _get_provider_name(self, provider) -> str:
        """
        Extract a readable name from a provider instance.
        
        Args:
            provider: Provider instance
            
        Returns:
            Provider name
        """
        # Get provider type from class name
        provider_class = provider.__class__.__name__
        
        # Extract provider type from class name
        if provider_class.endswith("Provider"):
            provider_type = provider_class[:-8].lower()
        else:
            provider_type = provider_class.lower()
            
        return provider_type
    
    def analyze_quality(self, samples: Dict[str, bytes]) -> Dict[str, Any]:
        """
        Analyze audio quality metrics for samples.
        
        Args:
            samples: Dictionary mapping provider names to audio samples
            
        Returns:
            Quality metrics
        """
        # Note: Implementing advanced audio quality metrics would 
        # require additional libraries for signal processing
        quality_metrics = {}
        
        for provider_name, audio_data in samples.items():
            # Basic size-based metrics for now
            quality_metrics[provider_name] = {
                "size": len(audio_data),
                "size_per_char": len(audio_data) / 100  # Assuming standard text length
            }
            
            # Here we would add additional quality metrics like:
            # - Signal-to-noise ratio
            # - Spectral analysis
            # - Clarity metrics
            # But these require audio processing libraries
        
        return quality_metrics
    
    def compare_historical_performance(self, provider_name: str) -> Dict[str, Any]:
        """
        Compare historical performance for a specific provider.
        
        Args:
            provider_name: Provider to analyze
            
        Returns:
            Historical performance data
        """
        if not self.results:
            return {"error": "No historical data available"}
        
        historical_data = {
            "timestamps": [],
            "batch_latency": [],
            "streaming_latency": [],
            "first_chunk_latency": []
        }
        
        for result in self.results:
            if provider_name in result["results"]:
                provider_results = result["results"][provider_name]
                
                # Add timestamp
                historical_data["timestamps"].append(result["timestamp"])
                
                # Extract metrics
                batch_times = []
                for voice_results in provider_results.get("batch", {}).values():
                    if voice_results.get("success", False):
                        batch_times.append(voice_results.get("avg_time", 0))
                
                if batch_times:
                    historical_data["batch_latency"].append(statistics.mean(batch_times))
                else:
                    historical_data["batch_latency"].append(None)
                
                # Extract streaming metrics if available
                if provider_results.get("streaming"):
                    streaming_times = []
                    first_chunk_times = []
                    
                    for voice_results in provider_results["streaming"].values():
                        if voice_results.get("success", False):
                            streaming_times.append(voice_results.get("avg_total_time", 0))
                            if voice_results.get("avg_first_chunk_time") is not None:
                                first_chunk_times.append(voice_results.get("avg_first_chunk_time", 0))
                    
                    if streaming_times:
                        historical_data["streaming_latency"].append(statistics.mean(streaming_times))
                    else:
                        historical_data["streaming_latency"].append(None)
                    
                    if first_chunk_times:
                        historical_data["first_chunk_latency"].append(statistics.mean(first_chunk_times))
                    else:
                        historical_data["first_chunk_latency"].append(None)
                else:
                    historical_data["streaming_latency"].append(None)
                    historical_data["first_chunk_latency"].append(None)
        
        return historical_data
    
    def compare_providers(self, metrics: List[str] = None) -> Dict[str, Any]:
        """
        Compare providers across specified metrics.
        
        Args:
            metrics: List of metrics to compare
            
        Returns:
            Comparison data
        """
        if not self.results:
            return {"error": "No results available for comparison"}
        
        if metrics is None:
            metrics = ["avg_batch_latency", "avg_streaming_latency", "avg_first_chunk_latency", "avg_char_rate"]
        
        latest_results = self.results[-1]["results"]
        comparison = {metric: {} for metric in metrics}
        
        for provider_name, provider_results in latest_results.items():
            # Extract batch metrics
            batch_data = {}
            batch_times = []
            char_rates = []
            
            for voice_results in provider_results.get("batch", {}).values():
                if voice_results.get("success", False):
                    batch_times.append(voice_results.get("avg_time", 0))
                    char_rates.append(voice_results.get("character_rate", 0))
            
            if batch_times:
                batch_data["avg_batch_latency"] = statistics.mean(batch_times)
            if char_rates:
                batch_data["avg_char_rate"] = statistics.mean(char_rates)
            
            # Extract streaming metrics
            streaming_data = {}
            if provider_results.get("streaming"):
                streaming_times = []
                first_chunk_times = []
                
                for voice_results in provider_results["streaming"].values():
                    if voice_results.get("success", False):
                        streaming_times.append(voice_results.get("avg_total_time", 0))
                        if voice_results.get("avg_first_chunk_time") is not None:
                            first_chunk_times.append(voice_results.get("avg_first_chunk_time", 0))
                
                if streaming_times:
                    streaming_data["avg_streaming_latency"] = statistics.mean(streaming_times)
                if first_chunk_times:
                    streaming_data["avg_first_chunk_latency"] = statistics.mean(first_chunk_times)
            
            # Combine metrics
            provider_metrics = {**batch_data, **streaming_data}
            
            # Add to comparison
            for metric in metrics:
                if metric in provider_metrics:
                    comparison[metric][provider_name] = provider_metrics[metric]
        
        # Find best provider for each metric
        winners = {}
        for metric in metrics:
            if comparison[metric]:
                if "latency" in metric:
                    # Lower is better for latency metrics
                    best_provider = min(comparison[metric].items(), key=lambda x: x[1])
                    winners[metric] = {"provider": best_provider[0], "value": best_provider[1]}
                else:
                    # Higher is better for other metrics (e.g., character rate)
                    best_provider = max(comparison[metric].items(), key=lambda x: x[1])
                    winners[metric] = {"provider": best_provider[0], "value": best_provider[1]}
        
        return {
            "metrics": comparison,
            "winners": winners
        } 