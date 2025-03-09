"""
AG2-Agent Tool Integration Module

This module provides adapters to integrate external tool systems (like the agent_tools package)
with the AG2-Agent framework.
"""

from typing import Dict, Any, Optional, List, Callable, Type, Union
import logging
import asyncio
from collections import defaultdict

logger = logging.getLogger(__name__)


class ToolManagerAdapter:
    """
    Adapter class that wraps the external ToolManager for use with AG2-Agent.
    
    This adapter provides a consistent interface for registering and using tools
    from the agent_tools package within the AG2-Agent framework.
    """
    
    def __init__(self, tool_manager):
        """
        Initialize the adapter with an external tool manager.
        
        Args:
            tool_manager: An instance of a tool manager (e.g., from agent_tools.tool_manager.ToolManager)
        """
        self.tool_manager = tool_manager
        self.registered_tools = {}
    
    def register_tool_from_instance(self, name: str, tool_instance, description: Optional[str] = None):
        """
        Register a tool directly from an instance.
        
        Args:
            name: The name to register the tool under
            tool_instance: An instance of a tool class
            description: Optional description of the tool
        """
        self.tool_manager.register_tool(name, tool_instance)
        self.registered_tools[name] = {
            'instance': tool_instance,
            'description': description or getattr(tool_instance, '__doc__', '')
        }
    
    def create_and_register_tool(self, name: str, tool_class: Type, 
                               params: Dict[str, Any] = None,
                               description: Optional[str] = None):
        """
        Create a tool instance and register it with the manager.
        
        Args:
            name: The name to register the tool under
            tool_class: The class of the tool to instantiate
            params: Parameters to pass to the tool constructor
            description: Optional description of the tool
        """
        params = params or {}
        tool_instance = tool_class(**params)
        self.register_tool_from_instance(name, tool_instance, description)
    
    async def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a registered tool.
        
        Args:
            tool_name: The name of the tool to execute
            params: Parameters to pass to the tool execution
            
        Returns:
            The result of the tool execution
            
        Raises:
            ValueError: If the tool is not registered
        """
        if tool_name not in self.registered_tools:
            raise ValueError(f"Tool '{tool_name}' not registered")
        
        try:
            result = await self.tool_manager.execute_tool(tool_name, params)
            return {
                'success': result.success,
                'result': result.result,
                'error': result.error,
                'tool': tool_name
            }
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {str(e)}")
            return {
                'success': False,
                'result': None,
                'error': f"Execution error: {str(e)}",
                'tool': tool_name
            }
    
    def get_registered_tools(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all registered tools.
        
        Returns:
            A dictionary mapping tool names to their information
        """
        return self.registered_tools


class LLMServiceAdapter:
    """
    Adapter class that wraps an external LLM service for use with AG2-Agent.
    
    This adapter provides a consistent interface for using LLM services
    from the agent_tools package within the AG2-Agent framework.
    """
    
    def __init__(self, llm_service):
        """
        Initialize the adapter with an external LLM service.
        
        Args:
            llm_service: An instance of an LLM service (e.g., from agent_tools.llm_service.LLMService)
        """
        self.llm_service = llm_service
    
    async def generate_response(self, 
                              prompt: str, 
                              system_prompt: Optional[str] = None,
                              messages: Optional[List[Dict[str, str]]] = None,
                              stream: bool = False) -> Dict[str, Any]:
        """
        Generate a response from the LLM.
        
        Args:
            prompt: The prompt to send to the LLM
            system_prompt: Optional system prompt
            messages: Optional list of previous messages
            stream: Whether to stream the response
            
        Returns:
            The LLM's response
        """
        # Create a request object expected by the LLM service
        request = type('Request', (), {})()
        request.messages = [type('Message', (), {'content': prompt})]
        
        # Process the request
        result = await self.llm_service.process_chat_request(request)
        
        return {
            'raw_response': result.get('raw_response', ''),
            'content': result.get('raw_response', ''),  # Alias for compatibility
            'model': getattr(self.llm_service, 'current_role', 'default')
        }
    
    def set_role(self, role_name: str) -> None:
        """
        Set the current role/persona for the LLM service.
        
        Args:
            role_name: The name of the role to set
        """
        if hasattr(self.llm_service, 'current_role'):
            self.llm_service.current_role = role_name


class ResponseParserAdapter:
    """
    Adapter class that wraps an external response parser for use with AG2-Agent.
    
    This adapter provides a consistent interface for using response parsers
    from the agent_tools package within the AG2-Agent framework.
    """
    
    def __init__(self, parser):
        """
        Initialize the adapter with an external parser.
        
        Args:
            parser: An instance of a parser (e.g., from agent_tools.parser.BaseResponseParser)
        """
        self.parser = parser
    
    def parse_response(self, response: str) -> Dict[str, Any]:
        """
        Parse a response from an LLM.
        
        Args:
            response: The raw response string from the LLM
            
        Returns:
            Parsed response with thought, tool_calls, content, etc.
        """
        parsed = self.parser.parse(response)
        
        return {
            'thought': parsed.thought,
            'tool_calls': parsed.tool_calls,
            'content': parsed.content,
            'api_call': parsed.api_call
        }


class TaskAnalyzerAdapter:
    """
    Adapter class that wraps an external task analyzer for use with AG2-Agent.
    
    This adapter provides a consistent interface for using task analyzers
    from the agent_tools package within the AG2-Agent framework.
    """
    
    def __init__(self, analyzer):
        """
        Initialize the adapter with an external analyzer.
        
        Args:
            analyzer: An instance of a task analyzer (e.g., from agent_tools.task_analyzer.BaseTaskAnalyzer)
        """
        self.analyzer = analyzer
    
    async def analyze_task(self, 
                        conversation_history: List[Dict[str, str]], 
                        last_response: str) -> str:
        """
        Analyze if a task is complete.
        
        Args:
            conversation_history: The conversation history
            last_response: The last response from the LLM
            
        Returns:
            Task status ("COMPLETED", "NEEDS_MORE_INFO", or "CONTINUE")
        """
        # Convert conversation history format if needed
        formatted_history = []
        for msg in conversation_history:
            formatted_history.append((msg.get('message', ''), msg.get('response', '')))
        
        # Handle both sync and async analyzers
        if hasattr(self.analyzer, 'analyze'):
            # Sync analyzer
            return self.analyzer.analyze(formatted_history, last_response)
        elif hasattr(self.analyzer, '_async_analyze'):
            # Async analyzer
            return await self.analyzer._async_analyze(formatted_history, last_response)
        else:
            # Default to completed if we can't analyze
            logger.warning("Task analyzer doesn't have expected methods. Defaulting to COMPLETED.")
            return "COMPLETED"


class FollowupGeneratorAdapter:
    """
    Adapter class that wraps an external followup generator for use with AG2-Agent.
    
    This adapter provides a consistent interface for using followup generators
    from the agent_tools package within the AG2-Agent framework.
    """
    
    def __init__(self, generator):
        """
        Initialize the adapter with an external generator.
        
        Args:
            generator: An instance of a followup generator (e.g., from agent_tools.followup_generator.FollowupGenerator)
        """
        self.generator = generator
    
    async def generate_followup(self, 
                            task_status: str, 
                            conversation_history: List[Dict[str, str]],
                            last_response: str) -> Optional[str]:
        """
        Generate a followup question based on the task status.
        
        Args:
            task_status: The status of the task from a task analyzer
            conversation_history: The conversation history
            last_response: The last response from the LLM
            
        Returns:
            A followup question or None
        """
        # Convert conversation history format if needed
        formatted_history = []
        for msg in conversation_history:
            formatted_history.append((msg.get('message', ''), msg.get('response', '')))
        
        # Handle both sync and async generators
        if hasattr(self.generator, 'generate_followup'):
            if asyncio.iscoroutinefunction(self.generator.generate_followup):
                # Async generator
                return await self.generator.generate_followup(task_status, formatted_history, last_response)
            else:
                # Sync generator
                return self.generator.generate_followup(task_status, formatted_history, last_response)
        else:
            logger.warning("Followup generator doesn't have expected methods. Returning None.")
            return None