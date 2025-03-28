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
logger = logging.getLogger("telnyx-handler")

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
            filename = f"{uuid.uuid4()}.wav"
            
        try:
            # Create multipart form data for the file upload
            files = {
                'file': (filename, file_data, content_type)
            }
            
            # Set up the data payload
            data = {
                'public': 'true',  # Make the file publicly accessible
                # Include bucket ID if provided
                'bucket_id': os.environ.get('TELNYX_STORAGE_BUCKET_ID', '')
            }
            
            # Set up headers with authentication
            headers = {
                'Authorization': f'Bearer {self.api_key}'
            }
            
            # Upload the file to Telnyx Storage
            response = requests.post(
                'https://api.telnyx.com/v2/files',
                headers=headers,
                files=files,
                data=data
            )
            
            # Check for successful upload
            if response.status_code == 200 or response.status_code == 201:
                response_data = response.json()
                public_url = response_data.get('data', {}).get('public_url')
                file_id = response_data.get('data', {}).get('id')
                
                logger.info(f"File uploaded successfully. File ID: {file_id}")
                return {
                    "url": public_url,
                    "id": file_id,
                    "content_type": content_type
                }
            else:
                logger.error(f"Failed to upload file to Telnyx Storage: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error uploading to Telnyx Storage: {e}")
            return None
    
    def get_codec_capabilities(self) -> Dict[str, Any]:
        """
        Get information about supported codecs and HD audio capabilities.
        
        Returns:
            Dict[str, Any]: Codec and HD audio information
        """
        return {
            "hd_audio_enabled": self.use_hd_audio,
            "codec_preferences": self.default_codec_preferences,
            "primary_codec": self.default_codec_preferences[0] if self.default_codec_preferences else None,
            "audio_sample_rate": self.default_audio_sample_rate,
            "audio_format": self.default_audio_format
        }
    
    def enable_hd_audio(self, enabled: bool = True) -> None:
        """
        Enable or disable HD audio.
        
        Args:
            enabled (bool): Whether to enable HD audio
        """
        self.use_hd_audio = enabled
        logger.info(f"HD audio {'enabled' if enabled else 'disabled'}")
    
    def set_codec_preferences(self, codec_preferences: List[str]) -> None:
        """
        Set codec preferences for calls.
        
        Args:
            codec_preferences (List[str]): List of codec preferences in order of preference
        """
        self.default_codec_preferences = codec_preferences
        logger.info(f"Set codec preferences: {', '.join(codec_preferences)}")
    
    def set_audio_sample_rate(self, sample_rate: int) -> None:
        """
        Set audio sample rate for HD calls.
        
        Args:
            sample_rate (int): Sample rate in Hz (e.g., 16000, 24000, 48000)
        """
        if sample_rate not in [8000, 16000, 24000, 48000]:
            logger.warning(f"Unusual sample rate: {sample_rate}. Recommended values are 8000, 16000, 24000, or 48000 Hz.")
        self.default_audio_sample_rate = sample_rate
        logger.info(f"Set audio sample rate: {sample_rate} Hz")
