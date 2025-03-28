#!/usr/bin/env python
# Spark TTS API Server
# Provides a simple API to generate speech from text using Spark TTS

import os
import io
import sys
import time
import logging
import tempfile
import argparse
from typing import Optional, Dict, Any
from pathlib import Path

import torch
import numpy as np
from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import soundfile as sf

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("spark-tts-server")

# Parse command line arguments
parser = argparse.ArgumentParser(description="Spark TTS Server")
parser.add_argument("--device", type=int, default=-1, help="Device ID (-1 for CPU, 0+ for GPU)")
parser.add_argument("--model_dir", type=str, default="/app/Spark-TTS/pretrained_models/Spark-TTS-0.5B", help="Path to the model directory")
parser.add_argument("--port", type=int, default=8020, help="Port to run the server on")
args = parser.parse_args()

# Constants
DEVICE_ID = args.device
DEVICE = torch.device(f"cuda:{DEVICE_ID}" if torch.cuda.is_available() and DEVICE_ID >= 0 else "cpu")
logger.info(f"Device set to use {DEVICE}")
MODEL_DIR = Path(args.model_dir)
TEMP_DIR = Path(tempfile.gettempdir())

# Add Spark-TTS directory to Python path
spark_tts_dir = "/app/Spark-TTS"
if spark_tts_dir not in sys.path:
    sys.path.append(spark_tts_dir)
    logger.info(f"Added {spark_tts_dir} to sys.path")

# Create Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Global model variable
tts_model = None

def load_model():
    """Load the TTS model using the SparkTTS CLI implementation."""
    try:
        logger.info(f"Loading Spark TTS model from {MODEL_DIR} on {DEVICE}")
        
        # Import the SparkTTS class from CLI
        from cli.SparkTTS import SparkTTS
        
        # Check if model directory exists
        if not MODEL_DIR.exists():
            logger.error(f"Model directory {MODEL_DIR} does not exist")
            return None
            
        # Log available model files
        if MODEL_DIR.exists():
            logger.info(f"Model directory exists and contains: {[f.name for f in MODEL_DIR.iterdir()]}")
        
        # Initialize the SparkTTS model
        model = SparkTTS(MODEL_DIR, device=DEVICE)
        logger.info("Successfully loaded Spark TTS model")
        return model
            
    except Exception as e:
        logger.error(f"Error loading TTS model: {str(e)}")
        logger.error("Stack trace:", exc_info=True)
        return None

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    global tts_model
    
    is_healthy = tts_model is not None
    
    return jsonify({
        "status": "healthy" if is_healthy else "unhealthy",
        "model": "SparkAudio/Spark-TTS-0.5B",
        "device": str(DEVICE),
        "gpu_available": torch.cuda.is_available()
    })

@app.route('/generate', methods=['POST'])
def generate_speech_endpoint():
    """Generate speech from text API endpoint."""
    global tts_model
    
    if tts_model is None:
        return jsonify({"error": "Model not initialized"}), 500
        
    try:
        data = request.get_json()
        text = data.get('text')
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        # Optional parameters (with defaults)
        gender = data.get('gender', 'female')  # female or male
        pitch = data.get('pitch', 'moderate')  # very_low, low, moderate, high, very_high
        speed = data.get('speed', 'moderate')  # very_low, low, moderate, high, very_high
        temperature = float(data.get('temperature', 0.8))
        
        # Generate speech
        logger.info(f"Generating speech for text: {text[:50]}{'...' if len(text) > 50 else ''}")
        
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            output_path = temp_file.name
            
            # Optional parameters
            prompt_speech_path = None
            prompt_text = None
            
            # Check if voice cloning is requested
            voice_id = data.get('voice_id')
            if voice_id:
                # If voice_id is provided, use it for voice cloning
                # Note: This would need prompt_speech_path which we don't handle in this simplified version
                logger.warning("Voice cloning not implemented in this version, using default voice settings")
                
            # Generate speech using the inference method
            start_time = time.time()
            audio_array = tts_model.inference(
                text=text,
                prompt_speech_path=prompt_speech_path,
                prompt_text=prompt_text,
                gender=gender,
                pitch=pitch,
                speed=speed,
                temperature=temperature
            )
            end_time = time.time()
            
            logger.info(f"Speech generation took {end_time - start_time:.2f} seconds")
            
            # Write audio to file
            sf.write(output_path, audio_array, tts_model.sample_rate)
            
            # Send the file
            return send_file(
                output_path,
                mimetype='audio/wav',
                as_attachment=True,
                download_name='generated_speech.wav'
            )
            
    except Exception as e:
        logger.error(f"Speech generation failed: {str(e)}")
        logger.error("Stack trace:", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/info', methods=['GET'])
def get_service_info():
    """Get service information."""
    return jsonify({
        "name": "Spark TTS Service",
        "model": "SparkAudio/Spark-TTS-0.5B",
        "device": str(DEVICE),
        "gpu_available": torch.cuda.is_available(),
        "sample_rate": tts_model.sample_rate if tts_model else 24000
    })

@app.route('/tts', methods=['POST'])
def tts_endpoint():
    """Alias for generate_speech_endpoint to maintain backward compatibility."""
    return generate_speech_endpoint()

if __name__ == '__main__':
    # Initialize the model
    logger.info("Initializing TTS model...")
    tts_model = load_model()
    
    if tts_model is None:
        logger.error("Failed to initialize TTS model. Server will start, but generation will fail.")
    
    # Use the port from arguments
    port = int(os.environ.get("PORT", args.port))
    logger.info(f"Starting server on port {port}...")
    app.run(host='0.0.0.0', port=port) 