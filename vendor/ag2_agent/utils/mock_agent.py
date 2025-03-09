from typing import List, Dict, Any, Optional, Union
from unittest.mock import AsyncMock


class MockAgent:
    """A simple mock agent for testing purposes.
    
    This agent can be used to simulate responses without requiring a real LLM backend.
    It can be configured with predefined responses or a response generation pattern.
    """
    
    def __init__(self, name: str, responses: Optional[List[str]] = None, 
                 tools: Optional[Dict[str, Any]] = None):
        """Initialize a mock agent.
        
        Args:
            name: The name of the agent
            responses: Optional list of predefined responses to return in sequence
            tools: Optional dictionary of tools available to the agent
        """
        self.name = name
        self.responses = responses or []
        self.tools = tools or {}
        self.response_index = 0
        self.bind_tools_called = False
    
    async def generate_response(self, message: str, 
                              history: Optional[List[Dict[str, Any]]] = None,
                              context: Optional[Dict[str, Any]] = None) -> str:
        """Generate a response to the given message.
        
        Args:
            message: The message to respond to
            history: Optional chat history
            context: Optional context information
            
        Returns:
            The agent's response
        """
        if self.responses:
            # Return predefined responses in sequence
            response = self.responses[self.response_index % len(self.responses)]
            self.response_index += 1
            return response
        else:
            # Generate a simple echo response
            return f"Response from {self.name}: Acknowledging context and '{message}'"
    
    def bind_tools(self, tools: Dict[str, Any]) -> None:
        """Bind tools to this agent.
        
        Args:
            tools: Dictionary of tools to bind
        """
        self.tools.update(tools)
        self.bind_tools_called = True


class SimpleHumanAgent(MockAgent):
    """A simple human agent simulator for testing.
    
    This agent is designed to represent a human user in the conversation,
    primarily for testing purposes.
    """
    
    def __init__(self, name: str = "Human", responses: Optional[List[str]] = None):
        """Initialize a human agent simulator.
        
        Args:
            name: The name of the agent, defaults to "Human"
            responses: Optional list of predefined responses
        """
        super().__init__(name, responses)
    
    async def generate_response(self, message: str, 
                              history: Optional[List[Dict[str, Any]]] = None,
                              context: Optional[Dict[str, Any]] = None) -> str:
        """Generate a human-like response.
        
        Args:
            message: The message to respond to
            history: Optional chat history
            context: Optional context information
            
        Returns:
            The agent's response
        """
        if self.responses:
            response = self.responses[self.response_index % len(self.responses)]
            self.response_index += 1
            return response
        else:
            return f"[{self.name}] Received: '{message}'"


class SimpleAssistantAgent(MockAgent):
    """A simple assistant agent simulator for testing.
    
    This agent is designed to represent an AI assistant in the conversation,
    primarily for testing purposes.
    """
    
    def __init__(self, name: str = "Assistant", responses: Optional[List[str]] = None, 
                 system_message: str = "You are a helpful assistant."):
        """Initialize an assistant agent simulator.
        
        Args:
            name: The name of the agent, defaults to "Assistant"
            responses: Optional list of predefined responses
            system_message: System message defining the assistant's behavior
        """
        super().__init__(name, responses)
        self.system_message = system_message
    
    async def generate_response(self, message: str, 
                              history: Optional[List[Dict[str, Any]]] = None,
                              context: Optional[Dict[str, Any]] = None) -> str:
        """Generate an assistant-like response.
        
        Args:
            message: The message to respond to
            history: Optional chat history
            context: Optional context information
            
        Returns:
            The agent's response
        """
        if self.responses:
            response = self.responses[self.response_index % len(self.responses)]
            self.response_index += 1
            return response
        else:
            # Generate a more elaborate response pattern
            return f"I'm {self.name}. In response to '{message}', I would say: This is a simulated assistant response."