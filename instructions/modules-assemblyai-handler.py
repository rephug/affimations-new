#!/usr/bin/env python
# AssemblyAI Handler Module for Morning Coffee application

import logging
from typing import Optional, Dict, Any, List, Union
from tenacity import retry, stop_after_attempt, wait_exponential
import assemblyai as aai

# Configure logging
logger = logging.getLogger("assemblyai-handler")

class AssemblyAIHandler:
    """Handler for AssemblyAI API interactions."""
    
    def __init__(self, api_key: str):
        """
        Initialize the AssemblyAI handler.
        
        Args:
            api_key (str): AssemblyAI API key
        """
        self.api_key = api_key
        
        # Set the API key for AssemblyAI
        aai.settings.api_key = api_key
        
        # Create a transcriber
        self.transcriber = aai.Transcriber()
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def submit_transcription(self, audio_url: str) -> Optional[Dict[str, Any]]:
        """
        Submit an audio file for transcription.
        
        Args:
            audio_url (str): URL of the audio file to transcribe
            
        Returns:
            Optional[Dict[str, Any]]: Job information or None if failed
        """
        try:
            # Create a transcription configuration
            config = aai.TranscriptionConfig(
                language_code="en",  # English language
                speaker_labels=False,  # We don't need to identify different speakers
                punctuate=True,       # Add punctuation
                format_text=True      # Apply smart formatting
            )
            
            # Submit the audio file for transcription
            transcript = self.transcriber.submit_url(audio_url, config=config)
            
            logger.info(f"Submitted audio for transcription. Job ID: {transcript.id}")
            
            return {
                "job_id": transcript.id,
                "status": "submitted"
            }
        except Exception as e:
            logger.error(f"Error submitting transcription to AssemblyAI: {e}")
            return None
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def check_transcription_status(self, job_id: str) -> Dict[str, Any]:
        """
        Check the status of a transcription job.
        
        Args:
            job_id (str): The ID of the transcription job
            
        Returns:
            Dict[str, Any]: Status information with text if completed
        """
        try:
            # Check the status of the job
            transcript = self.transcriber.get_by_id(job_id)
            
            # Determine the status
            if transcript.status == aai.TranscriptionStatus.completed:
                logger.info(f"Transcription completed for job {job_id}")
                return {
                    "status": "completed",
                    "text": transcript.text
                }
            elif transcript.status in [aai.TranscriptionStatus.queued, aai.TranscriptionStatus.processing]:
                logger.info(f"Transcription in progress for job {job_id}: {transcript.status}")
                return {
                    "status": "in_progress"
                }
            else:
                logger.error(f"AssemblyAI transcription failed: {transcript.status} for job {job_id}")
                return {
                    "status": "error",
                    "error": f"Transcription failed with status: {transcript.status}"
                }
        except Exception as e:
            logger.error(f"Error checking AssemblyAI transcription status: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
