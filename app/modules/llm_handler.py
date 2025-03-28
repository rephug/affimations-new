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
            llm_type (str): Type of LLM to use (openai, llama, claude, gemini)
            api_key (Optional[str]): API key for the LLM provider
            model (Optional[str]): Model name or identifier
            endpoint (Optional[str]): Custom endpoint URL for local models or Vertex AI
        """
        self.llm_type = llm_type.lower()
        self.api_key = api_key
        self.model = model
        self.endpoint = endpoint
        
        # Validate the configuration
        self._validate_config()
    
    def _validate_config(self):
        """Validate the configuration."""
        # Skip validation if needed
        if os.environ.get('SKIP_LLM_VALIDATION', '').lower() == 'true':
            logger.warning("Skipping LLM validation due to SKIP_LLM_VALIDATION=True")
            return
            
        # Check that we have a valid LLM type
        if self.llm_type not in ['openai', 'llama', 'claude', 'gemini']:
            raise ValueError(f"Unsupported LLM type: {self.llm_type}")
            
        # Check that we have an API key or endpoint
        if not self.api_key and self.llm_type != 'llama':
            raise ValueError(f"{self.llm_type.capitalize()} API key is required")
            
        # For Llama, check that we have an endpoint
        if self.llm_type == 'llama' and not self.endpoint:
            raise ValueError("Llama endpoint URL is required")
    
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
            elif self.llm_type == 'gemini':
                return self._get_gemini_response(user_input, conversation_history)
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
            
            # Add the current user input
            messages.append({"role": "user", "content": user_input})
            
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
            
            # Add current user message
            messages.append({
                "role": "user",
                "content": user_input
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
    
    def _get_gemini_response(self, user_input: str, conversation_history: List[Dict[str, str]]) -> Optional[str]:
        """Get a response from Google's Gemini API."""
        try:
            # Determine if we're using Vertex AI or direct API access
            if self.endpoint and 'googleapis.com' in self.endpoint:
                return self._get_vertex_gemini_response(user_input, conversation_history)
            else:
                return self._get_direct_gemini_response(user_input, conversation_history)
        except Exception as e:
            logger.error(f"Error getting Gemini response: {e}")
            return None
    
    def _get_vertex_gemini_response(self, user_input: str, conversation_history: List[Dict[str, str]]) -> Optional[str]:
        """Use Vertex AI endpoint for Gemini."""
        try:
            # Format the system prompt
            system_prompt = ("You are a helpful, positive voice assistant for a morning routine app called 'Morning Coffee'. "
                          "Keep responses concise (1-2 sentences) as they will be read out loud over a phone call. "
                          "Be uplifting, motivational, and help the user start their day with positivity.")
            
            # Convert conversation history to Vertex AI format
            messages = []
            
            # Add system role as a user message with a specific tag
            messages.append({
                "role": "user",
                "parts": [{"text": f"[SYSTEM]: {system_prompt}"}]
            })
            
            # Add previous conversation
            for msg in conversation_history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                
                # Map roles to Vertex AI expected format
                vertex_role = "user" if role == "user" else "model"
                
                messages.append({
                    "role": vertex_role,
                    "parts": [{"text": content}]
                })
            
            # Add the current user input
            messages.append({
                "role": "user",
                "parts": [{"text": user_input}]
            })
            
            # Prepare the request payload
            payload = {
                "contents": messages,
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 100,
                    "topK": 40,
                    "topP": 0.95
                }
            }
            
            # Make request to Vertex AI Gemini API
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                self.endpoint,
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                # Extract text from the response
                if 'candidates' in result and len(result['candidates']) > 0:
                    candidate = result['candidates'][0]
                    if 'content' in candidate and 'parts' in candidate['content']:
                        text_parts = [part.get('text', '') for part in candidate['content']['parts'] if 'text' in part]
                        return ''.join(text_parts).strip()
            else:
                logger.error(f"Error from Vertex AI Gemini API: {response.status_code} - {response.text}")
            
            return None
        except Exception as e:
            logger.error(f"Error getting Vertex AI Gemini response: {e}")
            return None
    
    def _get_direct_gemini_response(self, user_input: str, conversation_history: List[Dict[str, str]]) -> Optional[str]:
        """Use direct Gemini API access."""
        try:
            # Format the system prompt
            system_prompt = ("You are a helpful, positive voice assistant for a morning routine app called 'Morning Coffee'. "
                          "Keep responses concise (1-2 sentences) as they will be read out loud over a phone call. "
                          "Be uplifting, motivational, and help the user start their day with positivity.")
            
            # Build the conversation in Gemini format
            messages = []
            
            # Start with system role
            messages.append({
                "role": "system",
                "content": system_prompt
            })
            
            # Add conversation history
            for msg in conversation_history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                
                # Ensure we're using the standard roles
                if role not in ["user", "assistant", "system"]:
                    role = "user" if role == "user" else "assistant"
                
                messages.append({
                    "role": role,
                    "content": content
                })
            
            # Add current user message
            messages.append({
                "role": "user",
                "content": user_input
            })
            
            # Create the API URL using the model
            model_id = self.model or "gemini-2.0-flash"
            
            # New endpoint format for Gemini chat completions
            api_url = f"https://generativelanguage.googleapis.com/v1/chat/completions?key={self.api_key}"
            
            # Prepare request payload
            payload = {
                "model": model_id,
                "messages": messages,
                "max_tokens": 100,
                "temperature": 0.7,
                "top_p": 1
            }
            
            # Make the request
            response = requests.post(
                api_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Gemini API response: {result}")
                
                # Parse the response according to chat completions format
                if 'choices' in result and len(result['choices']) > 0:
                    choice = result['choices'][0]
                    if 'message' in choice and 'content' in choice['message']:
                        return choice['message']['content'].strip()
            else:
                error_details = response.json() if response.text else "No details"
                logger.error(f"Error from Gemini API: {response.status_code} - {error_details}")
                
                # Fallback to older format
                return self._fallback_gemini_request(user_input, conversation_history)
            
            return None
        except Exception as e:
            logger.error(f"Error getting direct Gemini response: {e}")
            return None
            
    def _fallback_gemini_request(self, user_input: str, conversation_history: List[Dict[str, str]]) -> Optional[str]:
        """Fallback method using older Gemini generateContent API."""
        try:
            # Format the system prompt
            system_prompt = ("You are a helpful, positive voice assistant for a morning routine app called 'Morning Coffee'. "
                          "Keep responses concise (1-2 sentences) as they will be read out loud over a phone call. "
                          "Be uplifting, motivational, and help the user start their day with positivity.")
            
            # Convert to Gemini's content format
            messages = []
            
            # Add system as a user message with special prefix
            messages.append({
                "role": "user",
                "parts": [{"text": f"[SYSTEM]: {system_prompt}"}]
            })
            
            # Add conversation history
            for msg in conversation_history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                
                # Map to Gemini's format (model instead of assistant)
                gemini_role = "user" if role == "user" else "model"
                
                messages.append({
                    "role": gemini_role,
                    "parts": [{"text": content}]
                })
            
            # Add current user message
            messages.append({
                "role": "user",
                "parts": [{"text": user_input}]
            })
            
            # Create the API URL using the model
            model_id = self.model or "gemini-2.0-flash"
            api_url = f"https://generativelanguage.googleapis.com/v1/models/{model_id}:generateContent?key={self.api_key}"
            
            # Prepare request payload
            payload = {
                "contents": messages,
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 100,
                    "topK": 40,
                    "topP": 0.95
                }
            }
            
            # Make the request
            response = requests.post(
                api_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Parse the response
                if 'candidates' in result and len(result['candidates']) > 0:
                    candidate = result['candidates'][0]
                    if 'content' in candidate and 'parts' in candidate['content']:
                        text_parts = [part.get('text', '') for part in candidate['content']['parts'] if 'text' in part]
                        return ''.join(text_parts).strip()
            else:
                logger.error(f"Error from Gemini generateContent API: {response.status_code} - {response.text}")
            
            return None
        except Exception as e:
            logger.error(f"Error in fallback Gemini request: {e}")
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
                
            elif self.llm_type == 'gemini':
                # For Gemini, make a direct API call to check health
                try:
                    # We'll use a very simple completion to test
                    model_id = self.model or "gemini-2.0-flash"
                    api_url = f"https://generativelanguage.googleapis.com/v1/models/{model_id}?key={self.api_key}"
                    
                    # Make a lightweight request to just check if the model exists
                    response = requests.get(api_url)
                    
                    if response.status_code == 200:
                        return True
                        
                    # If that fails, try a minimal completion as backup
                    if 400 <= response.status_code < 500:
                        logger.warning(f"Gemini model info check failed, trying minimal completion test")
                        test_response = self.get_response("Hello")
                        return test_response is not None
                        
                    return False
                except Exception as e:
                    logger.error(f"Gemini health check failed: {e}")
                    return False
            
            return False
        
        except Exception as e:
            logger.error(f"Error checking LLM health: {e}")
            return False 