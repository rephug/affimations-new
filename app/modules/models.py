#!/usr/bin/env python
# Data Models Module for Morning Coffee application

import datetime
from typing import Optional, Dict, Any, List

class User:
    """User model for Morning Coffee application."""
    
    def __init__(
        self,
        id: str,
        phone_number: str,
        name: str,
        affirmation_preferences: Optional[List[str]] = None,
        active: bool = True,
        created_at: Optional[datetime.datetime] = None
    ):
        """
        Initialize a User object.
        
        Args:
            id (str): Unique identifier for the user
            phone_number (str): User's phone number
            name (str): User's name
            affirmation_preferences (List[str], optional): List of preferred affirmation themes
            active (bool): Whether the user is active
            created_at (datetime.datetime, optional): When the user was created
        """
        self.id = id
        self.phone_number = phone_number
        self.name = name
        self.affirmation_preferences = affirmation_preferences or []
        self.active = active
        self.created_at = created_at or datetime.datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert User to dictionary representation.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the User
        """
        return {
            "id": self.id,
            "phone_number": self.phone_number,
            "name": self.name,
            "affirmation_preferences": self.affirmation_preferences,
            "active": self.active,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """
        Create User from dictionary representation.
        
        Args:
            data (Dict[str, Any]): Dictionary representation of User
            
        Returns:
            User: Instantiated User object
        """
        created_at = None
        if data.get("created_at"):
            try:
                created_at = datetime.datetime.fromisoformat(data["created_at"])
            except (ValueError, TypeError):
                created_at = datetime.datetime.now()
                
        return cls(
            id=data.get("id", ""),
            phone_number=data.get("phone_number", ""),
            name=data.get("name", ""),
            affirmation_preferences=data.get("affirmation_preferences", []),
            active=data.get("active", True),
            created_at=created_at
        )


class CallSession:
    """Call session model for tracking call state."""
    
    STATES = [
        "initiated",       # Call has been initiated
        "in_progress",     # Call is active
        "recording",       # Call is recording user's speech
        "processing",      # Processing user's speech
        "responding",      # LLM is generating a response
        "playing_audio",   # Playing audio to user
        "completed",       # Call completed successfully
        "failed"           # Call failed
    ]
    
    def __init__(
        self,
        id: str,
        user_id: str,
        call_control_id: str,
        state: str = "initiated",
        affirmation: Optional[str] = None,
        recordings: Optional[List[Dict[str, Any]]] = None,
        transcriptions: Optional[List[Dict[str, Any]]] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        started_at: Optional[datetime.datetime] = None,
        completed_at: Optional[datetime.datetime] = None
    ):
        """
        Initialize a CallSession object.
        
        Args:
            id (str): Unique identifier for the session
            user_id (str): ID of the user
            call_control_id (str): Telnyx call control ID
            state (str): Current state of the call
            affirmation (str, optional): Daily affirmation for this call
            recordings (List[Dict[str, Any]], optional): List of recording details
            transcriptions (List[Dict[str, Any]], optional): List of transcription details
            conversation_history (List[Dict[str, Any]], optional): History of the conversation
            started_at (datetime.datetime, optional): When the call started
            completed_at (datetime.datetime, optional): When the call completed
        """
        self.id = id
        self.user_id = user_id
        self.call_control_id = call_control_id
        self.state = state if state in self.STATES else "initiated"
        self.affirmation = affirmation
        self.recordings = recordings or []
        self.transcriptions = transcriptions or []
        self.conversation_history = conversation_history or []
        self.started_at = started_at or datetime.datetime.now()
        self.completed_at = completed_at
    
    def add_recording(self, recording_url: str, recording_id: str) -> None:
        """
        Add a recording to the session.
        
        Args:
            recording_url (str): URL of the recording
            recording_id (str): ID of the recording
        """
        self.recordings.append({
            "url": recording_url,
            "id": recording_id,
            "timestamp": datetime.datetime.now().isoformat()
        })
    
    def add_transcription(self, text: str, transcription_id: str) -> None:
        """
        Add a transcription to the session.
        
        Args:
            text (str): Transcribed text
            transcription_id (str): ID of the transcription
        """
        self.transcriptions.append({
            "text": text,
            "id": transcription_id,
            "timestamp": datetime.datetime.now().isoformat()
        })
    
    def add_conversation_entry(self, role: str, content: str) -> None:
        """
        Add an entry to the conversation history.
        
        Args:
            role (str): Role of the speaker (user/assistant)
            content (str): Content of the message
        """
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.datetime.now().isoformat()
        })
    
    def update_state(self, state: str) -> bool:
        """
        Update the state of the call session.
        
        Args:
            state (str): New state
            
        Returns:
            bool: True if state was updated, False if invalid state
        """
        if state in self.STATES:
            self.state = state
            # If the call is completed or failed, set the completed_at time
            if state in ["completed", "failed"] and not self.completed_at:
                self.completed_at = datetime.datetime.now()
            return True
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert CallSession to dictionary representation.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the CallSession
        """
        return {
            "id": self.id,
            "user_id": self.user_id,
            "call_control_id": self.call_control_id,
            "state": self.state,
            "affirmation": self.affirmation,
            "recordings": self.recordings,
            "transcriptions": self.transcriptions,
            "conversation_history": self.conversation_history,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CallSession':
        """
        Create CallSession from dictionary representation.
        
        Args:
            data (Dict[str, Any]): Dictionary representation of CallSession
            
        Returns:
            CallSession: Instantiated CallSession object
        """
        started_at = None
        if data.get("started_at"):
            try:
                started_at = datetime.datetime.fromisoformat(data["started_at"])
            except (ValueError, TypeError):
                started_at = datetime.datetime.now()
                
        completed_at = None
        if data.get("completed_at"):
            try:
                completed_at = datetime.datetime.fromisoformat(data["completed_at"])
            except (ValueError, TypeError):
                completed_at = None
                
        return cls(
            id=data.get("id", ""),
            user_id=data.get("user_id", ""),
            call_control_id=data.get("call_control_id", ""),
            state=data.get("state", "initiated"),
            affirmation=data.get("affirmation"),
            recordings=data.get("recordings", []),
            transcriptions=data.get("transcriptions", []),
            conversation_history=data.get("conversation_history", []),
            started_at=started_at,
            completed_at=completed_at
        )