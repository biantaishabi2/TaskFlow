from typing import Dict, Any, Optional, List, Callable, Union
from collections import defaultdict
import logging
import asyncio

from vendor.ag2_agent.core.base_interfaces import BaseChatInterface, ChatModeFactory

logger = logging.getLogger(__name__)


class TwoAgentChat(BaseChatInterface):
    """Implementation of a chat between two agents.
    
    This class manages a simple back-and-forth conversation between two agents.
    """
    
    def __init__(self, agents: Dict[str, Any], initial_prompt: str, config: Optional[Dict[str, Any]] = None):
        """Initialize a chat between two agents.
        
        Args:
            agents: Dictionary containing the two agents
            initial_prompt: Initial prompt to start the conversation
            config: Optional configuration parameters
        
        Raises:
            ValueError: If not exactly two agents are provided
        """
        if len(agents) != 2:
            raise ValueError("TwoAgentChat requires exactly 2 agents")
            
        self.agents = self._setup_agents(agents)
        self.initial_prompt = initial_prompt
        self.config = config or {}
        self.chat_history = []
        self.callbacks = defaultdict(list)
        self.current_speaker = None
        self.listener = None
        self.is_chat_active = False
        self.max_turns = self.config.get('max_turns', 10)
        self.turn_count = 0
    
    def _setup_agents(self, agents: Dict[str, Any]) -> Dict[str, Any]:
        """Set up and validate the agents for the chat.
        
        Args:
            agents: Dictionary of agents
            
        Returns:
            Validated dictionary of agents
            
        Raises:
            ValueError: If any agent is invalid
        """
        if len(agents) != 2:
            raise ValueError("TwoAgentChat requires exactly 2 agents")
        
        # Get the agent roles (keys)
        agent_roles = list(agents.keys())
        self.agent1_role = agent_roles[0]
        self.agent2_role = agent_roles[1]
        
        # Validate agents
        for role, agent in agents.items():
            # Here we would validate that the agent has the required methods
            # This is a placeholder and would need to be customized based on 
            # the specific agent interface requirements
            if not hasattr(agent, 'generate_response'):
                logger.warning(f"Agent {role} might not be compatible - missing generate_response method")
        
        return agents
    
    async def initiate_chat(self, message: str, sender: Optional[str] = None) -> Any:
        """Start a new chat between the two agents.
        
        Args:
            message: The initial message to start the conversation
            sender: Optional identifier of the sender (defaults to the first agent)
            
        Returns:
            The response from the agent that received the message
        """
        self.is_chat_active = True
        self.turn_count = 0
        
        # Clear chat history
        self.chat_history = []
        
        # Determine sender and listener
        if sender and sender in self.agents:
            self.current_speaker = sender
            roles = list(self.agents.keys())
            self.listener = roles[0] if roles[0] != sender else roles[1]
        else:
            # Default to first agent as sender
            self.current_speaker = self.agent1_role
            self.listener = self.agent2_role
        
        # Record the initial message
        self._add_to_history(self.current_speaker, message)
        
        # Call the callbacks for message sent
        self._trigger_callbacks('message_sent', {
            'sender': self.current_speaker,
            'message': message
        })
        
        # Get response from the listener
        response = await self._get_agent_response(self.listener, message)
        
        # Swap roles for next turn
        self._swap_roles()
        
        self.turn_count += 1
        
        return response
    
    async def continue_chat(self, message: Optional[str] = None, sender: Optional[str] = None) -> Any:
        """Continue the ongoing chat.
        
        Args:
            message: Optional message to add to the conversation
            sender: Optional identifier of the sender
            
        Returns:
            The next response in the conversation
            
        Raises:
            ValueError: If the chat is not active or has reached max turns
        """
        if not self.is_chat_active:
            raise ValueError("Chat is not active. Call initiate_chat first.")
        
        if self.turn_count >= self.max_turns:
            logger.warning(f"Reached maximum number of turns ({self.max_turns})")
            return self.end_chat()
        
        # If sender is provided, validate and use it
        if sender and sender in self.agents:
            self.current_speaker = sender
            roles = list(self.agents.keys())
            self.listener = roles[0] if roles[0] != sender else roles[1]
        
        # Get last message if none provided
        if message is None:
            if not self.chat_history:
                raise ValueError("No message provided and no chat history exists")
            message = self.chat_history[-1]['message']
        else:
            # Add the provided message to history
            self._add_to_history(self.current_speaker, message)
            
            # Call the callbacks for message sent
            self._trigger_callbacks('message_sent', {
                'sender': self.current_speaker,
                'message': message
            })
        
        # Get response from the listener
        response = await self._get_agent_response(self.listener, message)
        
        # Swap roles for next turn
        self._swap_roles()
        
        self.turn_count += 1
        
        return response
    
    def end_chat(self) -> Dict[str, Any]:
        """End the conversation and return summary information.
        
        Returns:
            Dictionary containing chat summary and metadata
        """
        self.is_chat_active = False
        
        # Call the callbacks for chat ended
        self._trigger_callbacks('chat_ended', {
            'history': self.chat_history,
            'turn_count': self.turn_count
        })
        
        return {
            'history': self.chat_history,
            'turn_count': self.turn_count,
            'agents': list(self.agents.keys())
        }
    
    def get_chat_history(self) -> List[Dict[str, Any]]:
        """Get the full history of the conversation.
        
        Returns:
            A list of message dictionaries representing the conversation history
        """
        return self.chat_history
    
    def register_callback(self, event_type: str, callback_fn: Callable) -> None:
        """Register a callback function for specific events.
        
        Args:
            event_type: Type of event to trigger the callback
            callback_fn: Function to call when the event occurs
        """
        self.callbacks[event_type].append(callback_fn)
    
    def _add_to_history(self, sender: str, message: str) -> None:
        """Add a message to the chat history.
        
        Args:
            sender: The sender of the message
            message: The message content
        """
        self.chat_history.append({
            'sender': sender,
            'message': message,
            'turn': self.turn_count
        })
    
    async def _get_agent_response(self, agent_role: str, message: str) -> str:
        """Get a response from the specified agent.
        
        Args:
            agent_role: The role of the agent to get a response from
            message: The message to respond to
            
        Returns:
            The agent's response
        """
        agent = self.agents[agent_role]
        
        # Call the agent's generate_response method
        # This is a placeholder and would need to be adapted to the actual agent interface
        try:
            if hasattr(agent, 'generate_response'):
                # Check if the agent's generate_response is async
                if asyncio.iscoroutinefunction(agent.generate_response):
                    response = await agent.generate_response(message, self.chat_history)
                else:
                    response = agent.generate_response(message, self.chat_history)
            else:
                # Fallback for testing or simple string responses
                response = f"Response from {agent_role}: Acknowledging '{message}'"
                logger.warning(f"Agent {agent_role} doesn't have generate_response method, using fallback")
        except Exception as e:
            logger.error(f"Error getting response from agent {agent_role}: {str(e)}")
            response = f"Error: Could not get response from {agent_role}"
        
        # Add the response to the chat history
        self._add_to_history(agent_role, response)
        
        # Call the callbacks for response received
        self._trigger_callbacks('response_received', {
            'sender': agent_role,
            'message': response
        })
        
        return response
    
    def _swap_roles(self) -> None:
        """Swap the current speaker and listener roles."""
        self.current_speaker, self.listener = self.listener, self.current_speaker
    
    def _trigger_callbacks(self, event_type: str, data: Dict[str, Any]) -> None:
        """Trigger all registered callbacks for a specific event.
        
        Args:
            event_type: The type of event that occurred
            data: Data associated with the event
        """
        for callback in self.callbacks.get(event_type, []):
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Error in callback for {event_type}: {str(e)}")


class TwoAgentChatFactory(ChatModeFactory):
    """Factory for creating TwoAgentChat instances."""
    
    @classmethod
    def create(cls, agents: Dict[str, Any], initial_prompt: str, 
              tools: Optional[Dict[str, Any]] = None, 
              config: Optional[Dict[str, Any]] = None) -> BaseChatInterface:
        """Create a TwoAgentChat instance.
        
        Args:
            agents: Dictionary of agents to use in the chat
            initial_prompt: Initial prompt to start the conversation
            tools: Optional dictionary of tools to bind to the agents
            config: Optional configuration parameters
            
        Returns:
            A configured TwoAgentChat instance
            
        Raises:
            ValueError: If the configuration is invalid
        """
        if len(agents) != 2:
            raise ValueError("TwoAgentChat requires exactly 2 agents")
        
        # Bind tools to agents if supported
        if tools:
            for agent_name, agent in agents.items():
                if hasattr(agent, 'bind_tools'):
                    try:
                        agent.bind_tools(tools)
                    except Exception as e:
                        logger.warning(f"Failed to bind tools to agent {agent_name}: {str(e)}")
        
        return TwoAgentChat(agents, initial_prompt, config)
    
    @classmethod
    def from_config(cls, config_dict: Dict[str, Any]) -> 'TwoAgentChatFactory':
        """Create a factory instance from configuration.
        
        Args:
            config_dict: Dictionary containing configuration parameters
            
        Returns:
            A configured factory instance
        """
        # This is a simple implementation that just returns the class itself
        # In a more complex scenario, this might return a specialized factory
        return cls