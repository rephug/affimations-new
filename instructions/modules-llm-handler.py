#!/usr/bin/env python
# LLM Handler Module for Morning Coffee application

import os
import json
import logging
import requests
from typing import Optional, Dict, Any, List, Union
from tenacity import retry, stop_after_attempt, wait_exponential

# Configure logging
logger = logging.getLogger("llm-handler")

class LLMHandler:
    """Handler for LLM API interactions with multiple provider support."""
    
    def __init__(self, llm_type: str, api_key: Optional[str] = None, 
                 model: Optional[str] = None, endpoint: Optional[str] = None):
        """
        Initialize the LLM handler.
        
        Args:
            llm_type (str): Type of LLM to use (openai, llama, claude)
            api_key (Optional[str]): API key for the LLM provider
            model (Optional[str]): Model name or identifier
            endpoint (Optional[str]): Custom endpoint URL for local models
        """
        self.llm_type = llm_type.lower()
        self.api_key = api_key
        self.model = model
        self.endpoint = endpoint
        
        # Validate the configuration
        self._validate_config()
    
    def _validate_config(self):
        """Validate the LLM configuration."""
        if self.llm_type not in ['openai', 'llama', 'claude']:
            raise ValueError(f"Unsupported LLM type: {self.llm_type}")
        
        if self.llm_type in ['openai', 'claude'] and not self.api_key:
            raise ValueError(f"{self.llm_type.capitalize()} API key is required")
        
        if self.llm_type == 'llama' and not self.endpoint:
            raise ValueError("Endpoint URL is required for Llama models")
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_response(self, user_input: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> Optional[str]:
        """
        Get a response from the LLM based on user input and conversation history.
        
        Args:
            user_input (str): The user's input text
            conversation_history (Optional[List[Dict[str, str]]]): Previous conversation history
            
        Returns:
            Optional[str]: The LLM's response text or None if failed
        """
        try:
            # Initialize conversation history if None
            if conversation_history is None:
                conversation_history = []
            
            # Get response based on the configured LLM type
            if self.llm_type == 'openai':
                return self._get_openai_response(user_input, conversation_history)
            elif self.llm_type == 'llama':
                return self._get_llama_response(user_input, conversation_history)
            elif self.llm_type == 'claude':
                return self._get_claude_response(user_input, conversation_history)
            else:
                logger.error(f"Unsupported LLM type: {self.llm_type}")
                return None
        except Exception as e:
            logger.error(f"Error getting LLM response: {e}")
            return None
    
    def _get_openai_response(self, user_input: str, conversation_history: List[Dict[str, str]]) -> Optional[str]:
        """Get a response from OpenAI."""
        try:
            import openai
            openai.api_key = self.api_key
            
            # Extract just the role and content from conversation history
            messages = [
                {"role": msg.get("role", "user"), "content": msg.get("content", "")}
                for msg in conversation_history
            ]
            
            # Add system message if not present
            if not any(msg.get("role") == "system" for msg in messages):
                messages.insert(0, {
                    "role": "system",
                    "content": "You are a helpful, positive voice assistant for a morning routine app called 'Morning Coffee'. "
                               "Keep responses concise (1-2 sentences) as they will be read out loud over a phone call. "
                               "Be uplifting, motivational, and help the user start their day with positivity."
                })
            
            # Get response from OpenAI
            response = openai.chat.completions.create(
                model=self.model or "gpt-3.5-turbo",
                messages=messages,
                max_tokens=100,  # Keep responses short for voice calls
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error getting OpenAI response: {e}")
            return None
    
    def _get_llama_response(self, user_input: str, conversation_history: List[Dict[str, str]]) -> Optional[str]:
        """Get a response from a local Llama model via API endpoint."""
        try:
            # Format the conversation for Llama
            system_prompt = ("You are a helpful, positive voice assistant for a morning routine app called 'Morning Coffee'. "
                            "Keep responses concise as they will be read out loud over a phone call. "
                            "Be uplifting, motivational, and help the user start their day with positivity.")
            
            prompt = f"{system_prompt}\n\n"
            
            for msg in conversation_history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                
                if role == "user":
                    prompt += f"User: {content}\n"
                elif role == "assistant":
                    prompt += f"Assistant: {content}\n"
            
            # Add the current user input
            prompt += f"User: {user_input}\nAssistant: "
            
            # Make request to the local Llama API
            response = requests.post(
                self.endpoint,
                json={
                    "prompt": prompt,
                    "max_tokens": 100,
                    "temperature": 0.7,
                    "stop": ["User:", "\n"]
                },
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("output", "").strip()
            else:
                logger.error(f"Error from Llama API: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error getting Llama response: {e}")
            return None
    
    def _get_claude_response(self, user_input: str, conversation_history: List[Dict[str, str]]) -> Optional[str]:
        """Get a response from Claude."""
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.api_key)
            
            # Extract just the role and content from conversation history
            messages = []
            
            # Add system message
            system_content = ("You are a helpful, positive voice assistant for a morning routine app called 'Morning Coffee'. "
                             "Keep responses concise (1-2 sentences) as they will be read out loud over a phone call. "
                             "Be uplifting, motivational, and help the user start their day with positivity.")
            
            # Format messages for Claude
            messages = [
                {
                    "role": "system",
                    "content": system_content
                }
            ]
            
            # Add conversation history
            for msg in conversation_history:
                role = msg.get("role")
                if role in ["user", "assistant"]:
                    messages.append({
                        "role": role,
                        "content": msg.get("content", "")
                    })
            
            # Get response from Claude
            response = client.messages.create(
                model=self.model or "claude-3-opus-20240229",
                max_tokens=100,
                messages=messages
            )
            
            return response.content[0].text
        except Exception as e:
            logger.error(f"Error getting Claude response: {e}")
            return None
    
    def health_check(self) -> bool:
        """
        Check the health of the LLM integration.
        
        Returns:
            bool: True if healthy, False otherwise
        """
        try:
            # Simple check based on LLM type
            if self.llm_type == 'openai':
                import openai
                openai.api_key = self.api_key
                # Just a minimal API call to check if the key works
                response = openai.models.list()
                return len(response.data) > 0
            
            elif self.llm_type == 'llama':
                # Check if the endpoint is reachable
                response = requests.get(f"{self.endpoint}/health")
                return response.status_code == 200
            
            elif self.llm_type == 'claude':
                import anthropic
                client = anthropic.Anthropic(api_key=self.api_key)
                # List models to check if the key works
                response = client.models.list()
                return len(response.data) > 0
            
            return False
        
        except Exception as e:
            logger.error(f"Error checking LLM health: {e}")
            return False
