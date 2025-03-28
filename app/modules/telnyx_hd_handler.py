#!/usr/bin/env python
# Enhanced Telnyx Handler Module for Morning Coffee application with HD Audio and OPUS support

import os
import json
import uuid
import logging
import requests
from typing import Optional, Dict, Any, List, Union
from tenacity import retry, stop_after_attempt, wait_exponential
import telnyx

# Configure logging
logger = logging.getLogger("telnyx-hd-handler")

class TelnyxHDHandler:
    """Enhanced Handler for Telnyx API interactions with HD Audio and OPUS codec support."""
    
    def __init__(self, api_key: str, phone_number: str, messaging_profile_id: str, app_id: str):
        """
        Initialize the Telnyx handler.
        
        Args:
            api_key (str): Telnyx API key
            phone_number (str): Telnyx phone number
            messaging_profile_id (str): Telnyx messaging profile ID
            app_id (str): Telnyx application ID (connection ID)
        """
        self.api_key = api_key
        self.phone_number = phone_number
        self.messaging_profile_id = messaging_profile_id
        self.app_id = app_id
        
        # HD Audio and OPUS configuration
        self.default_codec_preferences = ["OPUS", "G722", "AMR-WB", "G711A", "G711U"]
        self.default_audio_format = "wav"
        self.default_audio_sample_rate = 24000
        self.use_hd_audio = True  # Enable HD audio by default
        
        # Set the API key for the Telnyx client
        telnyx.api_key = api_key
        
        logger.info("Initialized enhanced Telnyx handler with HD Audio and OPUS support")
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def send_sms(self, to: str, text: str) -> Optional[Dict[str, Any]]:
        """
        Send an SMS using Telnyx.
        
        Args:
            to (str): Recipient phone number
            text (str): Message text
            
        Returns:
            Optional[Dict[str, Any]]: Response data or None if failed
        """
        try:
            # Send SMS using Telnyx
            message = telnyx.Message.create(
                from_=self.phone_number,
                to=to,
                text=text,
                messaging_profile_id=self.messaging_profile_id
            )
            
            logger.info(f"SMS sent with ID: {message.id}")
            
            return {
                "id": message.id,
                "status": "sent"
            }
        except Exception as e:
            logger.error(f"Error sending SMS via Telnyx: {e}")
            return None
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def make_hd_call(self, to: str, webhook_url: str, user_number: str, 
                     codec_preferences: Optional[List[str]] = None,
                     audio_format: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Make a high-definition call using Telnyx with OPUS codec preference.
        
        Args:
            to (str): Recipient phone number
            webhook_url (str): Webhook URL for call events
            user_number (str): User's phone number for reference
            codec_preferences (Optional[List[str]]): List of codec preferences, defaults to OPUS first
            audio_format (Optional[str]): Audio format for call media, defaults to 'wav'
            
        Returns:
            Optional[Dict[str, Any]]: Response data or None if failed
        """
        try:
            # Use provided codec preferences or defaults
            codecs = codec_preferences or self.default_codec_preferences
            format_value = audio_format or self.default_audio_format
            
            # Create a call using Telnyx Call Control API with HD Audio configuration
            call = telnyx.Call.create(
                connection_id=self.app_id,
                to=to,
                from_=self.phone_number,
                webhook_url=webhook_url,
                # Store user number in custom data for reference in webhooks
                custom_headers=json.dumps({"user": user_number}),
                # HD Audio configuration
                audio_url=None,  # No initial audio to play
                codec_preferences=codecs,  # Set codec preferences with OPUS first
                use_hd_audio=self.use_hd_audio,  # Enable HD audio
                # Additional audio configuration
                audio_format=format_value,
                answer_on_bridge=False,  # Answer the call before bridging
                record_audio=False,  # Don't automatically record the call
                timout_secs=60  # 60 seconds timeout for call
            )
            
            logger.info(f"HD call initiated with control ID: {call.call_control_id} using OPUS codec")
            
            return {
                "call_control_id": call.call_control_id,
                "status": "initiated",
                "hd_audio": self.use_hd_audio,
                "codec_preferences": codecs
            }
        except Exception as e:
            logger.error(f"Error making HD call via Telnyx: {e}")
            return None
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def play_hd_audio(self, call_control_id: str, audio_url: str, client_state: str) -> bool:
        """
        Play high-definition audio in a call.
        
        Args:
            call_control_id (str): Call control ID
            audio_url (str): URL of the audio file to play
            client_state (str): Client state to track playback
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Play audio using Telnyx Call Control API with HD Audio settings
            telnyx.Call.play_audio(
                call_control_id=call_control_id,
                audio_url=audio_url,
                client_state=client_state,
                # Additional options for HD audio
                loop=False,
                sample_rate=self.default_audio_sample_rate,  # Use 24kHz for HD audio
                trim_silence=True,  # Trim silence to improve experience
                overlay=False  # Don't overlay audio on top of existing call audio
            )
            
            logger.info(f"Playing HD audio with client state: {client_state}")
            return True
        except Exception as e:
            logger.error(f"Error playing HD audio via Telnyx: {e}")
            return False
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def start_hd_recording(self, call_control_id: str, client_state: str, 
                         channels: str = "single", format: str = "wav") -> bool:
        """
        Start recording a call in high-definition audio.
        
        Args:
            call_control_id (str): Call control ID
            client_state (str): Client state to track recording
            channels (str): Channel configuration (single or dual)
            format (str): Recording format (wav, mp3)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Start recording using Telnyx Call Control API with HD settings
            telnyx.Call.record_start(
                call_control_id=call_control_id,
                format=format,  # WAV for high quality
                channels=channels,  # Use single or dual as needed
                client_state=client_state,
                # Specify sample rate for HD audio
                sample_rate=self.default_audio_sample_rate,  # 24kHz for HD audio
                trim_silence=True  # Trim silence for better processing
            )
            
            logger.info(f"Started HD recording with client state: {client_state}")
            return True
        except Exception as e:
            logger.error(f"Error starting HD recording via Telnyx: {e}")
            return False
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def stop_recording(self, call_control_id: str) -> bool:
        """
        Stop recording a call.
        
        Args:
            call_control_id (str): Call control ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Stop recording using Telnyx Call Control API
            telnyx.Call.record_stop(call_control_id=call_control_id)
            
            logger.info(f"Stopped recording for call: {call_control_id}")
            return True
        except Exception as e:
            logger.error(f"Error stopping recording via Telnyx: {e}")
            return False
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def hangup_call(self, call_control_id: str) -> bool:
        """
        Hang up a call.
        
        Args:
            call_control_id (str): Call control ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Hang up call using Telnyx Call Control API
            telnyx.Call.hangup(call_control_id=call_control_id)
            
            logger.info(f"Hung up call: {call_control_id}")
            return True
        except Exception as e:
            logger.error(f"Error hanging up call via Telnyx: {e}")
            return False
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def upload_to_storage(self, file_data: bytes, filename: Optional[str] = None,
                         content_type: str = "audio/wav") -> Optional[Dict[str, Any]]:
        """
        Upload a file to Telnyx Storage.
        
        Args:
            file_data (bytes): The file data to upload
            filename (str, optional): Filename to use, will generate one if not provided
            content_type (str): MIME type of the file
            
        Returns:
            Optional[Dict[str, Any]]: Response with URL if successful, None otherwise
        """
        if filename is None:
            filename = f"audio_{uuid.uuid4()}.wav"
            
        try:
            # Create the upload first
            response = requests.post(
                "https://api.telnyx.com/v2/media",
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                },
                json={
                    "media_name": filename,
                    "content_type": content_type
                }
            )
            response.raise_for_status()
            upload_data = response.json().get("data", {})
            upload_id = upload_data.get("id")
            
            if not upload_id:
                logger.error("Failed to get upload ID from Telnyx API")
                return None
                
            # Now upload the file data to the provided URL
            upload_url = upload_data.get("upload_url")
            if not upload_url:
                logger.error("No upload URL provided by Telnyx")
                return None
                
            upload_response = requests.put(
                upload_url,
                data=file_data,
                headers={"Content-Type": content_type}
            )
            upload_response.raise_for_status()
            
            # Return details including the download URL
            return {
                "id": upload_id,
                "url": upload_data.get("public_url"),
                "status": "uploaded",
                "filename": filename
            }
            
        except Exception as e:
            logger.error(f"Error uploading file to Telnyx Storage: {e}")
            return None
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check health of Telnyx service.
        
        Returns:
            Dict[str, Any]: Health status information
        """
        try:
            # Try to make a simple API call to check connection
            response = requests.get(
                "https://api.telnyx.com/v2/available_phone_numbers",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Accept": "application/json"
                },
                params={"filter[country_code]": "US", "filter[limit]": 1}
            )
            
            if response.status_code == 200:
                return {
                    "status": "healthy",
                    "message": "Telnyx API connection is functioning normally",
                    "features": {
                        "hd_audio": self.use_hd_audio,
                        "codecs": self.default_codec_preferences
                    }
                }
            else:
                return {
                    "status": "unhealthy",
                    "message": f"Telnyx API returned status code: {response.status_code}",
                    "details": response.text
                }
                
        except Exception as e:
            logger.error(f"Telnyx health check failed: {e}")
            return {
                "status": "unhealthy",
                "message": str(e)
            } 