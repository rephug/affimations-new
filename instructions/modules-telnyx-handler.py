#!/usr/bin/env python
# Telnyx Handler Module for Morning Coffee application

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

class TelnyxHandler:
    """Handler for Telnyx API interactions."""
    
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
        
        # Set the API key for the Telnyx client
        telnyx.api_key = api_key
    
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
    def make_call(self, to: str, webhook_url: str, user_number: str) -> Optional[Dict[str, Any]]:
        """
        Make a call using Telnyx.
        
        Args:
            to (str): Recipient phone number
            webhook_url (str): Webhook URL for call events
            user_number (str): User's phone number for reference
            
        Returns:
            Optional[Dict[str, Any]]: Response data or None if failed
        """
        try:
            # Create a call using Telnyx Call Control API
            call = telnyx.Call.create(
                connection_id=self.app_id,
                to=to,
                from_=self.phone_number,
                webhook_url=webhook_url,
                # Store user number in custom data for reference in webhooks
                custom_headers=json.dumps({"user": user_number})
            )
            
            logger.info(f"Call initiated with control ID: {call.call_control_id}")
            
            return {
                "call_control_id": call.call_control_id,
                "status": "initiated"
            }
        except Exception as e:
            logger.error(f"Error making call via Telnyx: {e}")
            return None
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def play_audio(self, call_control_id: str, audio_url: str, client_state: str) -> bool:
        """
        Play audio in a call.
        
        Args:
            call_control_id (str): Call control ID
            audio_url (str): URL of the audio file to play
            client_state (str): Client state to track playback
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Play audio using Telnyx Call Control API
            telnyx.Call.play_audio(
                call_control_id=call_control_id,
                audio_url=audio_url,
                client_state=client_state
            )
            
            logger.info(f"Playing audio with client state: {client_state}")
            return True
        except Exception as e:
            logger.error(f"Error playing audio via Telnyx: {e}")
            return False
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def start_recording(self, call_control_id: str, client_state: str) -> bool:
        """
        Start recording a call.
        
        Args:
            call_control_id (str): Call control ID
            client_state (str): Client state to track recording
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Start recording using Telnyx Call Control API
            telnyx.Call.record_start(
                call_control_id=call_control_id,
                format="wav",
                channels="single",
                client_state=client_state
            )
            
            logger.info(f"Started recording with client state: {client_state}")
            return True
        except Exception as e:
            logger.error(f"Error starting recording via Telnyx: {e}")
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
    def upload_to_storage(self, file_data: bytes, filename: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Upload a file to Telnyx Storage.
        
        Args:
            file_data (bytes): The file data to upload
            filename (str, optional): Filename to use, will generate one if not provided
            
        Returns:
            Optional[Dict[str, Any]]: Response with URL if successful, None otherwise
        """
        if filename is None:
            filename = f"{uuid.uuid4()}.wav"
            
        try:
            # Create multipart form data for the file upload
            files = {
                'file': (filename, file_data, 'audio/wav')
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
                    "id": file_id
                }
            else:
                logger.error(f"Failed to upload file to Telnyx Storage: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error uploading to Telnyx Storage: {e}")
            return None
