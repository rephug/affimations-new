#!/usr/bin/env python
# Data Models Module for Morning Coffee application

from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class Message:
    """Message in a conversation."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class UserSession:
    """User session data."""
    user_number: str
    affirmation: Optional[str] = None
    conversation_history: List[Message] = field(default_factory=list)
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def add_message(self, role: str, content: str) -> None:
        """Add a message to the conversation history."""
        self.conversation_history.append(Message(role=role, content=content))
        self.last_updated = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "user_number": self.user_number,
            "affirmation": self.affirmation,
            "conversation_history": [
                {"role": msg.role, "content": msg.content, "timestamp": msg.timestamp}
                for msg in self.conversation_history
            ],
            "last_updated": self.last_updated
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserSession':
        """Create from dictionary."""
        session = cls(user_number=data.get("user_number", ""))
        session.affirmation = data.get("affirmation")
        session.last_updated = data.get("last_updated", datetime.now().isoformat())
        
        # Add conversation history
        for msg_data in data.get("conversation_history", []):
            msg = Message(
                role=msg_data.get("role", "user"),
                content=msg_data.get("content", ""),
                timestamp=msg_data.get("timestamp", datetime.now().isoformat())
            )
            session.conversation_history.append(msg)
        
        return session

@dataclass
class CallState:
    """State of a Telnyx call."""
    call_control_id: str
    user_number: str
    stage: str = "init"  # init, greeting, recording_affirmation, chat_intro, recording_chat, ai_response, ended
    affirmation: Optional[str] = None
    last_transcription: Optional[str] = None
    pending_transcription: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    end_time: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "call_control_id": self.call_control_id,
            "user_number": self.user_number,
            "stage": self.stage,
            "affirmation": self.affirmation,
            "last_transcription": self.last_transcription,
            "pending_transcription": self.pending_transcription,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
            "end_time": self.end_time
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CallState':
        """Create from dictionary."""
        return cls(
            call_control_id=data.get("call_control_id", ""),
            user_number=data.get("user_number", ""),
            stage=data.get("stage", "init"),
            affirmation=data.get("affirmation"),
            last_transcription=data.get("last_transcription"),
            pending_transcription=data.get("pending_transcription"),
            created_at=data.get("created_at", datetime.now().isoformat()),
            last_updated=data.get("last_updated", datetime.now().isoformat()),
            end_time=data.get("end_time")
        )

@dataclass
class TranscriptionJob:
    """AssemblyAI transcription job."""
    job_id: str
    call_control_id: str
    client_state: str
    status: str = "pending"  # pending, processing, completed, error
    text: Optional[str] = None
    start_time: float = field(default_factory=lambda: datetime.now().timestamp())
    completed_at: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "job_id": self.job_id,
            "call_control_id": self.call_control_id,
            "client_state": self.client_state,
            "status": self.status,
            "text": self.text,
            "start_time": self.start_time,
            "completed_at": self.completed_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TranscriptionJob':
        """Create from dictionary."""
        return cls(
            job_id=data.get("job_id", ""),
            call_control_id=data.get("call_control_id", ""),
            client_state=data.get("client_state", ""),
            status=data.get("status", "pending"),
            text=data.get("text"),
            start_time=data.get("start_time", datetime.now().timestamp()),
            completed_at=data.get("completed_at")
        )
