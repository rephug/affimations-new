#!/usr/bin/env python
# AssemblyAI Handler Module for Morning Coffee application
# Direct REST API implementation to avoid SDK validation issues

import logging
import json
import time
from typing import Optional, Dict, Any, List, Union
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

# Configure logging
logger = logging.getLogger("assemblyai-handler")

class AssemblyAIHandler:
    """Handler for AssemblyAI API interactions using direct REST API calls."""
    
    # AssemblyAI API endpoints
    BASE_URL = "https://api.assemblyai.com/v2"
    TRANSCRIPT_ENDPOINT = f"{BASE_URL}/transcript"
    
    def __init__(self, api_key: str):
        """
        Initialize the AssemblyAI handler.
        
        Args:
            api_key (str): AssemblyAI API key
        """
        self.api_key = api_key
        self.headers = {
            "Authorization": api_key,
            "Content-Type": "application/json"
        }
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def submit_transcription(self, audio_url: str) -> Optional[Dict[str, Any]]:
        """
        Submit an audio file for transcription using direct REST API.
        
        Args:
            audio_url (str): URL of the audio file to transcribe
            
        Returns:
            Optional[Dict[str, Any]]: Job information or None if failed
        """
        try:
            # Create transcription configuration - using direct API call
            data = {
                "audio_url": audio_url,
                "language_code": "en",
                "speaker_labels": False,
                "punctuate": True,
                "format_text": True
            }
            
            # Submit the audio file for transcription
            response = requests.post(
                self.TRANSCRIPT_ENDPOINT,
                json=data,
                headers=self.headers
            )
            response.raise_for_status()
            
            result = response.json()
            transcript_id = result.get("id")
            
            if not transcript_id:
                logger.error(f"No transcript ID returned from AssemblyAI: {result}")
                return None
                
            logger.info(f"Submitted audio for transcription. Job ID: {transcript_id}")
            
            return {
                "job_id": transcript_id,
                "status": "submitted"
            }
        except Exception as e:
            logger.error(f"Error submitting transcription to AssemblyAI: {e}")
            return None
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def check_transcription_status(self, job_id: str) -> Dict[str, Any]:
        """
        Check the status of a transcription job using direct REST API.
        
        Args:
            job_id (str): The ID of the transcription job
            
        Returns:
            Dict[str, Any]: Status information with text if completed
        """
        try:
            # Check the status of the job
            url = f"{self.TRANSCRIPT_ENDPOINT}/{job_id}"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            transcript = response.json()
            status = transcript.get("status")
            
            # Determine the status
            if status == "completed":
                logger.info(f"Transcription completed for job {job_id}")
                return {
                    "status": "completed",
                    "text": transcript.get("text", "")
                }
            elif status in ["queued", "processing"]:
                logger.info(f"Transcription in progress for job {job_id}: {status}")
                return {
                    "status": "in_progress"
                }
            else:
                logger.error(f"AssemblyAI transcription failed: {status} for job {job_id}")
                return {
                    "status": "error",
                    "error": f"Transcription failed with status: {status}"
                }
        except Exception as e:
            logger.error(f"Error checking AssemblyAI transcription status: {e}")
            return {
                "status": "error",
                "error": str(e)
            } 