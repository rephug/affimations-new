#!/usr/bin/env python
# Script to download Spark TTS model files

import os
import logging
import glob
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
        download_path = snapshot_download(
            repo_id=MODEL_ID,
            local_dir=str(MODEL_DIR),  # Convert Path to string for compatibility
            ignore_patterns=[".*"],  # Ignore hidden files
        )
        
        logger.info(f"Downloaded model to {download_path}")
        
        # Check what files were downloaded
        all_files = []
        for ext in ["*.bin", "*.json", "*.pt", "*.onnx", "*.safetensors", "config.*"]:
            pattern = os.path.join(download_path, "**", ext)
            all_files.extend(glob.glob(pattern, recursive=True))
            # Also check directly in MODEL_DIR
            pattern = os.path.join(MODEL_DIR, "**", ext)
            all_files.extend(glob.glob(pattern, recursive=True))
        
        logger.info(f"Found {len(all_files)} model-related files")
        if all_files:
            for file in all_files[:5]:  # Log first 5 files for debugging
                logger.info(f"Found file: {file}")
            return True
        
        # If we found no model files but the download reported success,
        # the model might be in a subdirectory
        subdirs = [d for d in os.listdir(download_path) 
                   if os.path.isdir(os.path.join(download_path, d))]
        
        if subdirs:
            logger.info(f"Found subdirectories: {subdirs}")
            # Check files in subdirectories
            for subdir in subdirs:
                subdir_path = os.path.join(download_path, subdir)
                files_in_subdir = []
                for ext in ["*.bin", "*.json", "*.pt", "*.onnx", "*.safetensors", "config.*"]:
                    pattern = os.path.join(subdir_path, "**", ext)
                    files_in_subdir.extend(glob.glob(pattern, recursive=True))
                
                if files_in_subdir:
                    logger.info(f"Found {len(files_in_subdir)} model files in {subdir}")
                    return True
        
        logger.error("No model files found after download")
        # List all files in the download directory for debugging
        logger.info(f"Contents of download directory: {os.listdir(download_path)}")
        return False
    
    except Exception as e:
        logger.error(f"Error downloading model: {e}")
        return False

if __name__ == "__main__":
    success = download_model()
    if not success:
        logger.error("Failed to download model, exiting")
        exit(1)
    
    logger.info("Model download complete") 