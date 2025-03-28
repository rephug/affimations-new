#!/usr/bin/env python
# Script to download Spark TTS model files

import os
import logging
from pathlib import Path
from huggingface_hub import snapshot_download

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("download-spark-tts")

# Constants
MODEL_ID = os.environ.get("SPARK_TTS_MODEL_ID", "SparkAudio/Spark-TTS-0.5B")
MODEL_DIR = Path(os.environ.get("SPARK_TTS_MODEL_DIR", "/app/models"))

def download_model():
    """
    Download model files from Hugging Face Hub.
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        logger.info(f"Downloading model {MODEL_ID} to {MODEL_DIR}")
        
        # Create model directory if it doesn't exist
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        
        # Download the model files
        snapshot_download(
            repo_id=MODEL_ID,
            local_dir=MODEL_DIR,
            local_dir_use_symlinks=False  # Don't use symlinks in Docker
        )
        
        logger.info(f"Successfully downloaded model to {MODEL_DIR}")
        
        # Verify essential files exist
        model_files = list(MODEL_DIR.glob("*.bin")) + list(MODEL_DIR.glob("*.json"))
        if not model_files:
            logger.error("No model files found after download")
            return False
        
        logger.info(f"Found {len(model_files)} model files")
        return True
    
    except Exception as e:
        logger.error(f"Error downloading model: {e}")
        return False

if __name__ == "__main__":
    success = download_model()
    if not success:
        logger.error("Failed to download model, exiting")
        exit(1)
    
    logger.info("Model download complete")
