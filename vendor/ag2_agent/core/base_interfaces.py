from typing import Any, Dict, List, Callable, Optional, Union
from collections import defaultdict


class BaseChatInterface:
    """Base interface for all chat modes implementations."""
    
    async def initiate_chat(self, message: str, sender: Optional[str] = None) -> Any:
        """Start a new chat conversation.
        
        Args:
            message: The initial message to start the conversation
            sender: Optional identifier of the sender
            
        Returns:
            The response to the initial message
        """
        raise NotImplementedError
    
    async def continue_chat(self, message: Optional[str] = None, sender: Optional[str] = None) -> Any:
        """Continue an ongoing conversation.
        
        Args:
            message: Optional new message to add to the conversation
            sender: Optional identifier of the sender
            
        Returns:
            The next response in the conversation
        """
        raise NotImplementedError
    
    def end_chat(self) -> Dict[str, Any]:
        """End the conversation and clean up resources.
        
        Returns:
            A dictionary containing conversation summary and metadata
        """
        raise NotImplementedError
    
    def get_chat_history(self) -> List[Dict[str, Any]]:
        """Get the full history of the conversation.
        
        Returns:
            A list of message dictionaries representing the conversation history
        """
        raise NotImplementedError
    
    def register_callback(self, event_type: str, callback_fn: Callable) -> None:
        """Register a callback function for specific events.
        
        Args:
            event_type: Type of event to trigger the callback
            callback_fn: Function to call when the event occurs
        """
        raise NotImplementedError


class ChatModeFactory:
    """Base factory interface for creating chat mode instances."""
    
    @classmethod
    def create(cls, agents: Dict[str, Any], initial_prompt: str, 
               tools: Optional[Dict[str, Any]] = None, 
               config: Optional[Dict[str, Any]] = None) -> BaseChatInterface:
        """Create a chat mode instance.
        
        Args:
            agents: Dictionary of agents to use in the chat
            initial_prompt: Initial prompt to start the conversation
            tools: Optional dictionary of tools available to agents
            config: Optional configuration parameters
            
        Returns:
            An instance of a class implementing BaseChatInterface
        """
        raise NotImplementedError
    
    @classmethod
    def from_config(cls, config_dict: Dict[str, Any]) -> 'ChatModeFactory':
        """Create a factory instance from configuration.
        
        Args:
            config_dict: Dictionary containing configuration parameters
            
        Returns:
            A configured factory instance
        """
        raise NotImplementedError