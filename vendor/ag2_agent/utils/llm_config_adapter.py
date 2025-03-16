"""
AG2-Agent LLM Configuration Adapter Module

This module provides classes to adapt external LLM services to AG2-Agent's
configuration requirements.

DEPRECATION NOTICE: ExternalLLMConfig is deprecated and will be removed in a future version.
                    Please use the standard AG2 config_list format with StandardLLMAgent instead.
"""

from typing import Dict, Any, Optional, List, Union, Callable
import logging
import asyncio
import inspect
import warnings

logger = logging.getLogger(__name__)


class ExternalLLMConfig:
    """
    DEPRECATED: Configuration adapter for external LLM services.
    
    This class is deprecated and will be removed in future versions.
    Please use StandardLLMAgent with standard AG2 config_list format instead.
    
    Example of recommended standard config:
    ```python
    llm_config = {
        "config_list": [
            {
                "api_type": "openai",
                "model": "gpt-4o",
                "api_key": os.environ["OPENAI_API_KEY"]
            }
        ]
    }
    ```
    """
    
    def __init__(self, 
                llm_service,
                model_name: str = "external-llm",
                temperature: float = 0.7,
                max_tokens: Optional[int] = None):
        """
        Initialize the external LLM configuration.
        
        DEPRECATED: This class is deprecated. Please use StandardLLMAgent with
                    standard AG2 config_list format instead.
        
        Args:
            llm_service: An instance of an external LLM service
            model_name: Identifier for the model
            temperature: Temperature setting for generation
            max_tokens: Maximum tokens to generate
        """
        warnings.warn(
            "ExternalLLMConfig is deprecated and will be removed in future versions. "
            "Please use StandardLLMAgent with standard AG2 config_list format instead.",
            DeprecationWarning,
            stacklevel=2
        )
        
        self.llm_service = llm_service
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.description = f"External LLM service: {model_name}"
    
    async def generate(self, 
                     messages: List[Dict[str, str]],
                     temperature: Optional[float] = None,
                     max_tokens: Optional[int] = None,
                     **kwargs) -> Dict[str, Any]:
        """
        Generate a response using the external LLM service.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            temperature: Optional temperature override
            max_tokens: Optional max tokens override
            **kwargs: Additional parameters passed to the LLM service
            
        Returns:
            A dictionary containing the response content
        """
        # Extract the system message and prompt
        system_prompt = None
        last_message = None
        
        for msg in messages:
            if msg.get('role') == 'system':
                system_prompt = msg.get('content')
            if msg.get('role') == 'user':
                last_message = msg.get('content')
        
        # If no user message was found, use the last message
        if last_message is None and messages:
            last_message = messages[-1].get('content', '')
        
        # Prepare the request
        request = type('Request', (), {})()
        request.messages = [type('Message', (), {'content': last_message})]
        
        # Call the LLM service
        try:
            # Check if the LLM service expects a specific format
            if hasattr(self.llm_service, 'process_chat_request'):
                result = await self.llm_service.process_chat_request(request)
                content = result.get('raw_response', '')
            elif hasattr(self.llm_service, 'generate'):
                params = {
                    'temperature': temperature or self.temperature,
                    'max_tokens': max_tokens or self.max_tokens,
                    **kwargs
                }
                
                # Check if the generate method is async
                if asyncio.iscoroutinefunction(self.llm_service.generate):
                    result = await self.llm_service.generate(last_message, **params)
                else:
                    result = self.llm_service.generate(last_message, **params)
                
                # Check result format
                if isinstance(result, dict):
                    content = result.get('content', result.get('text', str(result)))
                else:
                    content = str(result)
            else:
                # Fallback: try a direct call
                content = str(await self._call_service(last_message, system_prompt))
        except Exception as e:
            logger.error(f"Error generating response from external LLM: {str(e)}")
            content = f"Error: Failed to generate response: {str(e)}"
        
        return {
            'content': content,
            'model': self.model_name,
            'role': 'assistant',
            'metadata': {
                'temperature': temperature or self.temperature,
                'max_tokens': max_tokens or self.max_tokens,
                'service_type': type(self.llm_service).__name__
            }
        }
    
    async def _call_service(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Attempt to call the LLM service directly as a fallback.
        
        Args:
            prompt: The prompt to send
            system_prompt: Optional system prompt
            
        Returns:
            The generated response
        """
        # Try to find a suitable method to call
        for method_name in ['call', '__call__', 'chat', 'complete', 'predict']:
            if hasattr(self.llm_service, method_name):
                method = getattr(self.llm_service, method_name)
                
                # Prepare arguments based on method signature
                sig = inspect.signature(method)
                kwargs = {}
                
                if 'prompt' in sig.parameters:
                    kwargs['prompt'] = prompt
                elif 'message' in sig.parameters:
                    kwargs['message'] = prompt
                elif 'text' in sig.parameters:
                    kwargs['text'] = prompt
                
                if system_prompt and 'system_prompt' in sig.parameters:
                    kwargs['system_prompt'] = system_prompt
                
                if 'temperature' in sig.parameters:
                    kwargs['temperature'] = self.temperature
                
                if 'max_tokens' in sig.parameters:
                    kwargs['max_tokens'] = self.max_tokens
                
                # Call the method
                if not kwargs and len(sig.parameters) == 1:
                    # If no kwargs match but the method takes one argument, just pass the prompt
                    result = method(prompt)
                else:
                    result = method(**kwargs)
                
                # If the result is awaitable, await it
                if inspect.isawaitable(result):
                    result = await result
                
                return result
        
        # If no suitable method was found
        raise ValueError(f"Could not find a suitable method to call on {type(self.llm_service).__name__}")


class GeminiAnalyzerConfig(ExternalLLMConfig):
    """
    Configuration adapter specifically for Gemini-based task analyzers.
    
    This adapter tailors the interface to work with the GeminiTaskAnalyzer.
    """
    
    def __init__(self, gemini_analyzer, **kwargs):
        """
        Initialize the Gemini analyzer configuration.
        
        Args:
            gemini_analyzer: An instance of GeminiTaskAnalyzer
            **kwargs: Additional configuration parameters
        """
        super().__init__(
            llm_service=gemini_analyzer,
            model_name=getattr(gemini_analyzer, 'model_name', 'gemini-analyzer'),
            **kwargs
        )
    
    async def analyze_chat(self, 
                         messages: List[Dict[str, str]],
                         last_response: str) -> str:
        """
        Analyze a chat to determine if a task is complete.
        
        Args:
            messages: List of message dictionaries
            last_response: The last response in the conversation
            
        Returns:
            Task status ("COMPLETED", "NEEDS_MORE_INFO", or "CONTINUE")
        """
        # Convert messages to the format expected by the analyzer
        history = []
        for i in range(0, len(messages) - 1, 2):
            if i + 1 < len(messages):
                history.append((
                    messages[i].get('content', ''),
                    messages[i+1].get('content', '')
                ))
        
        # Use the analyzer to analyze the task
        if hasattr(self.llm_service, 'analyze'):
            # Check if the analyze method is async
            if asyncio.iscoroutinefunction(self.llm_service.analyze):
                result = await self.llm_service.analyze(history, last_response)
            else:
                result = self.llm_service.analyze(history, last_response)
            
            return result
        
        # Default to CONTINUE if the analyzer doesn't have an analyze method
        return "CONTINUE"