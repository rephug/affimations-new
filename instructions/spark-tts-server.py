#!/usr/bin/env python
# Spark TTS API Server
# Provides a simple API to generate speech from text using Spark TTS

import os
import io
import time
import uuid
import logging
import tempfile
from typing import Optional, Dict, Any, List, Union
from pathlib import Path
import json

import torch
import torchaudio
import numpy as np
from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import soundfile as sf
from transformers import pipeline, AutoModelForTextToSpeech, AutoProcessor, set_seed

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("spark-tts-server")

# Constants
MODEL_ID = os.environ.get("SPARK_TTS_MODEL_ID", "SparkAudio/Spark-TTS-0.5B")
MODEL_DIR = Path(os.environ.get("SPARK_TTS_MODEL_DIR", "/app/models"))
SAMPLE_RATE = int(os.environ.get("SPARK_TTS_SAMPLE_RATE", "24000"))
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
DEFAULT_SEED = 42

# Create Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Create output directory for audio files if needed
TEMP_DIR = Path(tempfile.gettempdir()) / "spark-tts"
TEMP_DIR.mkdir(exist_ok=True, parents=True)

# Global variables for model and processor
model = None
processor = None
tts_pipeline = None

def load_model():
    """Load the Spark TTS model and processor."""
    global model, processor, tts_pipeline
    logger.info(f"Loading Spark TTS model {MODEL_ID} on {DEVICE}")
    
    try:
        # Load model and processor
        model = AutoModelForTextToSpeech.from_pretrained(MODEL_ID, cache_dir=MODEL_DIR)
        processor = AutoProcessor.from_pretrained(MODEL_ID, cache_dir=MODEL_DIR)
        
        # Move model to GPU if available
        model = model.to(DEVICE)
        
        # Create TTS pipeline
        tts_pipeline = pipeline(
            "text-to-speech", 
            model=model, 
            tokenizer=processor, 
            device=DEVICE
        )
        
        logger.info("Model loaded successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        return False

def generate_speech(
    text: str, 
    voice_id: Optional[str] = None,
    speed: float = 1.0,
    seed: Optional[int] = None
) -> Optional[bytes]:
    """
    Generate speech from text using Spark TTS.
    
    Args:
        text: The text to convert to speech
        voice_id: Optional voice identifier (not used in base Spark TTS)
        speed: Speech speed factor (1.0 = normal)
        seed: Random seed for reproducibility
        
    Returns:
        Audio data as bytes or None if generation failed
    """
    try:
        # Set seed for reproducibility if provided
        if seed is not None:
            set_seed(seed)
        else:
            set_seed(DEFAULT_SEED)
        
        logger.info(f"Generating speech for text: {text[:50]}{'...' if len(text) > 50 else ''}")
        start_time = time.time()
        
        # Generate speech using the TTS pipeline
        outputs = tts_pipeline(
            text,
            forward_params={"do_sample": True}
        )
        
        # Get audio data
        audio_array = outputs["audio"]
        
        # Handle speed adjustments if needed
        if speed != 1.0:
            # This is a simple way to adjust speed by resampling
            # For more sophisticated speed adjustment, you might want to use a different method
            new_sample_rate = int(SAMPLE_RATE * (1 / speed))
            audio_array = torchaudio.functional.resample(
                torch.tensor(audio_array).unsqueeze(0),
                orig_freq=SAMPLE_RATE,
                new_freq=new_sample_rate
            ).squeeze(0).numpy()
        
        # Save to a temporary file
        audio_file = TEMP_DIR / f"{uuid.uuid4()}.wav"
        sf.write(str(audio_file), audio_array, SAMPLE_RATE)
        
        # Read the file as bytes
        with open(audio_file, "rb") as f:
            audio_data = f.read()
        
        # Clean up the temporary file
        audio_file.unlink()
        
        generation_time = time.time() - start_time
        logger.info(f"Speech generated in {generation_time:.2f} seconds")
        
        return audio_data
    
    except Exception as e:
        logger.error(f"Error generating speech: {e}")
        return None

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    if model is None or processor is None:
        return jsonify({"status": "error", "message": "Model not loaded"}), 503
    
    return jsonify({
        "status": "healthy",
        "model": MODEL_ID,
        "device": DEVICE,
        "gpu_available": torch.cuda.is_available(),
        "timestamp": time.time()
    })

@app.route('/tts', methods=['POST'])
def tts_endpoint():
    """
    Text-to-speech endpoint.
    
    Expected JSON body:
    {
        "text": "Text to convert to speech",
        "voice_id": "default",  # Optional, defaults to None
        "speed": 1.0,           # Optional, defaults to 1.0
        "seed": 42              # Optional, defaults to None
    }
    
    Returns:
        Audio file in WAV format
    """
    try:
        # Parse request data
        data = request.json
        if not data or 'text' not in data:
            return jsonify({"status": "error", "message": "Missing required field: text"}), 400
        
        text = data['text']
        voice_id = data.get('voice_id')
        speed = float(data.get('speed', 1.0))
        seed = data.get('seed')
        
        # Generate speech
        audio_data = generate_speech(text, voice_id, speed, seed)
        
        if audio_data is None:
            return jsonify({"status": "error", "message": "Failed to generate speech"}), 500
        
        # Return the audio file
        return send_file(
            io.BytesIO(audio_data),
            mimetype='audio/wav',
            as_attachment=True,
            download_name=f"speech_{uuid.uuid4()}.wav"
        )
    
    except Exception as e:
        logger.error(f"Error in TTS endpoint: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/voices', methods=['GET'])
def voices_endpoint():
    """
    Get available voices.
    
    Note: Basic Spark TTS doesn't support multiple voices, so this is a placeholder.
    Returns a single default voice. This could be extended with voice cloning or
    fine-tuned models in the future.
    
    Returns:
        JSON list of available voices
    """
    voices = [
        {
            "id": "default",
            "name": "Spark Default",
            "description": "Default voice for Spark TTS",
            "sample_rate": SAMPLE_RATE
        }
    ]
    
    return jsonify({"voices": voices})

@app.route('/info', methods=['GET'])
def info_endpoint():
    """
    Get information about the TTS service.
    
    Returns:
        JSON with service information
    """
    return jsonify({
        "name": "Spark TTS Service",
        "model": MODEL_ID,
        "sample_rate": SAMPLE_RATE,
        "device": DEVICE,
        "gpu_available": torch.cuda.is_available(),
        "version": "1.0.0"
    })

def main():
    """Initialize and start the Flask application."""
    # Load the model
    success = load_model()
    if not success:
        logger.error("Failed to load model, exiting")
        exit(1)
    
    # Get port from environment variable or use default
    port = int(os.environ.get("PORT", 8020))
    
    # Start the Flask app
    app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == '__main__':
    main()
