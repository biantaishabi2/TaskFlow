"""
Standard LLM Agent Module for AG2-Agent

This module provides a standard LLM agent implementation that uses the AG2-compatible
config_list format for configuration and supports model fallback mechanisms.
"""

from typing import Dict, Any, List, Optional, Union
import logging
import asyncio
import os

logger = logging.getLogger(__name__)

class StandardLLMAgent:
    """
    LLM Agent that uses the standard AG2 config_list configuration format.
    
    This agent supports:
    - Standard AG2 config_list format
    - Built-in model fallback mechanism
    - Complete message history handling
    - Seamless integration with OpenAI, OpenRouter, and other standard API services
    
    Example config:
    ```python
    llm_config = {
        "config_list": [
            {
                "api_type": "openai",
                "model": "gpt-4o",
                "api_key": os.environ["OPENAI_API_KEY"]
            },
            {
                "api_type": "openai",
                "model": "gpt-3.5-turbo",
                "api_key": os.environ["OPENAI_API_KEY"],
                "base_url": "https://openrouter.ai/api/v1"
            }
        ]
    }
    ```
    """
    
    def __init__(self, name: str, llm_config: Dict[str, Any], 
                 system_message: Optional[str] = None,
                 tools: Optional[List[Dict[str, Any]]] = None):
        """
        Initialize the standard LLM agent.
        
        Args:
            name: The name of the agent
            llm_config: Configuration dictionary with config_list format
            system_message: Optional system message (overrides config)
            tools: Optional list of tools the agent can use
        """
        self.name = name
        self.llm_config = llm_config
        self.history = []
        self.tools = tools or []
        
        # Extract or use provided system message
        self._system_message = system_message or self._get_system_message()
        
        # Validate configuration
        if not self._validate_config():
            logger.warning("Invalid or incomplete LLM configuration")
    
    def _validate_config(self) -> bool:
        """
        Validate the provided configuration.
        
        Returns:
            True if configuration is valid, False otherwise
        """
        if not isinstance(self.llm_config, dict):
            logger.error("LLM configuration must be a dictionary")
            return False
            
        config_list = self.llm_config.get("config_list", [])
        if not config_list or not isinstance(config_list, list):
            logger.error("config_list must be a non-empty list")
            return False
            
        # Check at least one entry has required fields
        valid_entries = 0
        for config in config_list:
            if isinstance(config, dict) and "model" in config:
                valid_entries += 1
                
        if valid_entries == 0:
            logger.error("At least one valid configuration with 'model' field is required")
            return False
            
        return True
    
    def _get_system_message(self) -> str:
        """
        Extract system message from configuration.
        
        Returns:
            System message string
        """
        config_list = self.llm_config.get("config_list", [])
        for config in config_list:
            if isinstance(config, dict) and "system_message" in config:
                return config["system_message"]
        
        # Default system message if none provided
        return "You are a helpful assistant."
    
    async def generate_response(self, message: str, 
                               history: Optional[List[Dict[str, Any]]] = None,
                               context: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate a response using the configured LLM(s) with fallback support.
        
        Args:
            message: The message to respond to
            history: Optional chat history
            context: Optional additional context
            
        Returns:
            The generated response text
            
        Raises:
            Exception: If all configured models fail
        """
        config_list = self.llm_config.get("config_list", [])
        if not config_list:
            raise ValueError("No configuration found in config_list")
            
        # Prepare messages
        messages = self._prepare_messages(message, history)
        
        # Try each configuration in order until one succeeds
        last_error = None
        for config in config_list:
            try:
                # 确保环境变量被正确处理（特别是API密钥）
                if "${OPENROUTER_API_KEY}" in str(config.get("api_key", "")):
                    config["api_key"] = os.environ.get("OPENROUTER_API_KEY", "")
                    
                response = await self._call_llm_api(config, messages, context)
                return response
            except Exception as e:
                logger.warning(f"Error with model {config.get('model')}: {str(e)}")
                last_error = e
                continue
                
        # If we get here, all models failed
        error_msg = f"All models in config_list failed. Last error: {str(last_error)}"
        logger.error(error_msg)
        raise Exception(error_msg)
    
    def _prepare_messages(self, message: str, 
                         history: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, str]]:
        """
        Prepare the complete messages list including history and system message.
        
        Args:
            message: Current message
            history: Optional conversation history
            
        Returns:
            List of formatted messages for the API
        """
        messages = []
        
        # Add system message if present
        if self._system_message:
            messages.append({"role": "system", "content": self._system_message})
            
        # Add chat history if provided
        if history:
            for entry in history:
                # Determine the role based on the sender
                if "sender" in entry and "message" in entry:
                    role = "assistant" if entry["sender"] == self.name else "user"
                    messages.append({"role": role, "content": entry["message"]})
                elif "role" in entry and "content" in entry:
                    # If the history already has role/content format
                    messages.append({"role": entry["role"], "content": entry["content"]})
                    
        # Add the current message as user message if not empty
        if message and message.strip():
            messages.append({"role": "user", "content": message})
            
        return messages
    
    async def _call_llm_api(self, config: Dict[str, Any], 
                          messages: List[Dict[str, str]],
                          context: Optional[Dict[str, Any]] = None) -> str:
        """
        Call the appropriate LLM API based on configuration.
        
        Args:
            config: Configuration dictionary for this specific model
            messages: Formatted messages to send
            context: Optional additional context
            
        Returns:
            The response content as a string
        """
        api_type = config.get("api_type", "openai").lower()
        
        if api_type == "openai":
            return await self._call_openai_api(config, messages, context)
        elif api_type == "anthropic":
            return await self._call_anthropic_api(config, messages, context)
        elif api_type == "google":
            return await self._call_google_api(config, messages, context)
        else:
            raise ValueError(f"Unsupported API type: {api_type}")
            
    async def _call_openai_api(self, config: Dict[str, Any], 
                              messages: List[Dict[str, str]],
                              context: Optional[Dict[str, Any]] = None) -> str:
        """
        Call OpenAI or compatible API.
        
        Args:
            config: OpenAI configuration
            messages: Formatted messages
            context: Optional additional context
            
        Returns:
            Response content
        """
        try:
            from openai import AsyncOpenAI
            
            # Get API key from config or environment
            api_key = config.get("api_key", os.environ.get("OPENROUTER_API_KEY", os.environ.get("OPENAI_API_KEY")))
            
            # Handle optional base_url (used for OpenRouter, etc.)
            base_url = config.get("base_url")
            
            # Create client with appropriate configuration
            client_args = {"api_key": api_key}
            if base_url:
                client_args["base_url"] = base_url
                
            client = AsyncOpenAI(**client_args)
            
            # Prepare extra headers if specified
            extra_headers = config.get("extra_headers", {})
            
            # Configure request parameters
            request_params = {
                "model": config.get("model"),
                "messages": messages,
                "temperature": config.get("temperature", 0.7)
            }
            
            # Add max_tokens if specified
            if "max_tokens" in config:
                request_params["max_tokens"] = config["max_tokens"]
                
            # Add extra headers if any
            if extra_headers:
                request_params["extra_headers"] = extra_headers
                
            # Add stream parameter if specified
            if "stream" in config:
                request_params["stream"] = config["stream"]
                
            # Call the OpenAI API
            response = await client.chat.completions.create(**request_params)
            
            # Extract and return content
            if hasattr(response, "choices") and response.choices:
                return response.choices[0].message.content
            else:
                return "No response generated"
                
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {str(e)}")
            raise
    
    async def _call_anthropic_api(self, config: Dict[str, Any], 
                                messages: List[Dict[str, str]],
                                context: Optional[Dict[str, Any]] = None) -> str:
        """
        Call Anthropic Claude API.
        
        Args:
            config: Anthropic configuration
            messages: Formatted messages
            context: Optional additional context
            
        Returns:
            Response content
        """
        try:
            from anthropic import AsyncAnthropic, HUMAN_PROMPT, AI_PROMPT
            
            # Get API key from config or environment
            api_key = config.get("api_key", os.environ.get("ANTHROPIC_API_KEY"))
            
            # Create client
            client = AsyncAnthropic(api_key=api_key)
            
            # Convert messages to Anthropic format
            # (More complex conversion would be implemented here)
            prompt = ""
            system_message = None
            
            for message in messages:
                if message["role"] == "system":
                    system_message = message["content"]
                elif message["role"] == "user":
                    prompt += f"{HUMAN_PROMPT} {message['content']}"
                elif message["role"] == "assistant":
                    prompt += f"{AI_PROMPT} {message['content']}"
            
            # Add final AI prompt
            prompt += AI_PROMPT
            
            # Call the Anthropic API
            response = await client.completion(
                model=config.get("model", "claude-3-opus-20240229"),
                prompt=prompt,
                system=system_message,
                max_tokens_to_sample=config.get("max_tokens", 1000),
                temperature=config.get("temperature", 0.7)
            )
            
            return response.completion
            
        except Exception as e:
            logger.error(f"Error calling Anthropic API: {str(e)}")
            raise
    
    async def _call_google_api(self, config: Dict[str, Any], 
                             messages: List[Dict[str, str]],
                             context: Optional[Dict[str, Any]] = None) -> str:
        """
        Call Google Gemini API.
        
        Args:
            config: Google API configuration
            messages: Formatted messages
            context: Optional additional context
            
        Returns:
            Response content
        """
        try:
            # Import appropriate Google client
            import google.generativeai as genai
            
            # Get API key from config or environment
            api_key = config.get("api_key", os.environ.get("GOOGLE_API_KEY"))
            
            # Configure genai
            genai.configure(api_key=api_key)
            
            # Get model
            model = genai.GenerativeModel(config.get("model", "gemini-pro"))
            
            # Convert messages to Google format
            system_message = None
            chat_messages = []
            
            for message in messages:
                if message["role"] == "system":
                    system_message = message["content"]
                elif message["role"] == "user":
                    chat_messages.append({"role": "user", "parts": [message["content"]]})
                elif message["role"] == "assistant":
                    chat_messages.append({"role": "model", "parts": [message["content"]]})
            
            # Start chat
            chat = model.start_chat(system_instruction=system_message)
            
            # Add previous messages to chat history
            for msg in chat_messages[:-1]:  # All except the last
                if msg["role"] == "user":
                    chat.send_message(msg["parts"][0])
                    
            # Send the last user message and get response
            if chat_messages and chat_messages[-1]["role"] == "user":
                response = chat.send_message(chat_messages[-1]["parts"][0])
                return response.text
            else:
                return "No valid user message to respond to"
                
        except Exception as e:
            logger.error(f"Error calling Google API: {str(e)}")
            raise
            
    def bind_tools(self, tools: Dict[str, Any]) -> None:
        """
        Bind tools to this agent for tool calling.
        
        Args:
            tools: Dictionary of tools to bind
        """
        # Currently a stub implementation - to be expanded in future
        self.tools = tools