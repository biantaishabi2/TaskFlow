from typing import Dict, Any, Optional, List, Callable, Union
from collections import defaultdict
import logging
import asyncio

from core.base_interfaces import BaseChatInterface, ChatModeFactory

logger = logging.getLogger(__name__)


class SequentialChat(BaseChatInterface):
    """Implementation of a sequential chat where multiple agents perform in sequence.
    
    This class manages conversations where agents process tasks in a defined order,
    with each agent receiving the context and output from preceding agents.
    """
    
    def __init__(self, agents: Dict[str, Any], initial_prompt: str, 
                 context_handler: Optional[Callable] = None, 
                 config: Optional[Dict[str, Any]] = None):
        """Initialize a sequential chat with multiple agents.
        
        Args:
            agents: Dictionary containing agents in execution order
            initial_prompt: Initial prompt to start the conversation
            context_handler: Optional function to process context between agents
            config: Optional configuration parameters
        
        Raises:
            ValueError: If less than two agents are provided
        """
        if len(agents) < 2:
            raise ValueError("SequentialChat requires at least 2 agents")
            
        self.agents = self._setup_agents(agents)
        self.initial_prompt = initial_prompt
        self.context_handler = context_handler or self._default_context_handler
        self.config = config or {}
        self.chat_history = []
        self.callbacks = defaultdict(list)
        self.is_chat_active = False
        self.max_turns = self.config.get('max_turns', 10)
        self.turn_count = 0
        self.current_step = 0
        self.context = {}
        
        # Save agent order for easy access
        self.agent_order = list(self.agents.keys())
    
    def _setup_agents(self, agents: Dict[str, Any]) -> Dict[str, Any]:
        """Set up and validate the agents for the sequential chat.
        
        Args:
            agents: Dictionary of agents in the order they should execute
            
        Returns:
            Validated dictionary of agents
            
        Raises:
            ValueError: If any agent is invalid
        """
        if len(agents) < 2:
            raise ValueError("SequentialChat requires at least 2 agents")
        
        # Validate agents
        for role, agent in agents.items():
            # Check that the agent has the required methods
            if not hasattr(agent, 'generate_response'):
                logger.warning(f"Agent {role} might not be compatible - missing generate_response method")
        
        return agents
    
    async def initiate_chat(self, message: str, sender: Optional[str] = None) -> Any:
        """Start a new sequential chat chain.
        
        Args:
            message: The initial message to start the conversation
            sender: Optional identifier of the sender (defaults to system)
            
        Returns:
            The response from the first agent in the sequence
        """
        self.is_chat_active = True
        self.turn_count = 0
        self.current_step = 0
        
        # Reset context and chat history
        self.chat_history = []
        self.context = {}
        
        # Set default sender if not provided
        if not sender:
            sender = "system"
        
        # Record the initial message
        self._add_to_history(sender, message)
        
        # Call the callbacks for message sent
        self._trigger_callbacks('message_sent', {
            'sender': sender,
            'message': message
        })
        
        # Add initial message to context
        self.context = self.context_handler(self.context, {
            'sender': sender,
            'message': message
        })
        
        # Get response from the first agent
        first_agent_role = self.agent_order[0]
        response = await self._get_agent_response(first_agent_role, message, self.context)
        
        # Update context with first agent's response
        self.context = self.context_handler(self.context, {
            'agent': first_agent_role,
            'response': response
        })
        
        # Move to the next agent for next turn
        self.current_step += 1
        
        self.turn_count += 1
        
        return response
    
    async def continue_chat(self, message: Optional[str] = None, sender: Optional[str] = None) -> Any:
        """Continue the sequential processing to the next agent.
        
        Args:
            message: Optional additional input for the next agent
            sender: Optional identifier of the sender
            
        Returns:
            The response from the next agent in the sequence
            
        Raises:
            ValueError: If the chat is not active or the sequence is complete
        """
        if not self.is_chat_active:
            raise ValueError("Chat is not active. Call initiate_chat first.")
        
        if self.is_complete():
            logger.info("Sequential chat chain is complete")
            return self.end_chat()
        
        if self.turn_count >= self.max_turns:
            logger.warning(f"Reached maximum number of turns ({self.max_turns})")
            return self.end_chat()
        
        # Get the current agent in the sequence
        current_agent_role = self.agent_order[self.current_step]
        
        # If additional message is provided, add it to the context
        if message:
            sender = sender or "user"
            self._add_to_history(sender, message)
            
            # Call the callbacks for message sent
            self._trigger_callbacks('message_sent', {
                'sender': sender,
                'message': message
            })
            
            # Update context with the new message
            self.context = self.context_handler(self.context, {
                'sender': sender,
                'message': message
            })
            
        # Get response from the current agent
        response = await self._get_agent_response(current_agent_role, message, self.context)
        
        # Update context with the agent's response
        self.context = self.context_handler(self.context, {
            'agent': current_agent_role,
            'response': response
        })
        
        # Move to the next agent
        self.current_step += 1
        
        self.turn_count += 1
        
        return response
    
    def end_chat(self) -> Dict[str, Any]:
        """End the sequential chat chain and return summary information.
        
        Returns:
            Dictionary containing chat summary and metadata
        """
        self.is_chat_active = False
        
        # Call the callbacks for chat ended
        self._trigger_callbacks('chat_ended', {
            'history': self.chat_history,
            'turn_count': self.turn_count,
            'context': self.context
        })
        
        return {
            'history': self.chat_history,
            'turn_count': self.turn_count,
            'agents': list(self.agents.keys()),
            'context': self.context
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

    def is_complete(self) -> bool:
        """Check if the sequential chat has completed all steps.
        
        Returns:
            True if all agents have processed, False otherwise
        """
        return self.current_step >= len(self.agents)
    
    def _add_to_history(self, sender: str, message: str) -> None:
        """Add a message to the chat history.
        
        Args:
            sender: The sender of the message
            message: The message content
        """
        self.chat_history.append({
            'sender': sender,
            'message': message,
            'turn': self.turn_count,
            'step': self.current_step
        })
    
    async def _get_agent_response(self, agent_role: str, message: str, context: Dict[str, Any]) -> str:
        """Get a response from the specified agent.
        
        Args:
            agent_role: The role of the agent to get a response from
            message: The message to respond to
            context: The current context of the conversation
            
        Returns:
            The agent's response
        """
        agent = self.agents[agent_role]
        
        # Call the agent's generate_response method
        try:
            if hasattr(agent, 'generate_response'):
                # Check if the agent supports context and if generate_response is async
                if hasattr(agent, 'supports_context') and agent.supports_context:
                    if asyncio.iscoroutinefunction(agent.generate_response):
                        response = await agent.generate_response(message, self.chat_history, context)
                    else:
                        response = agent.generate_response(message, self.chat_history, context)
                else:
                    if asyncio.iscoroutinefunction(agent.generate_response):
                        response = await agent.generate_response(message, self.chat_history)
                    else:
                        response = agent.generate_response(message, self.chat_history)
            else:
                # Fallback for testing or simple string responses
                response = f"Response from {agent_role}: Acknowledging context and '{message}'"
                logger.warning(f"Agent {agent_role} doesn't have generate_response method, using fallback")
        except Exception as e:
            logger.error(f"Error getting response from agent {agent_role}: {str(e)}")
            response = f"Error: Could not get response from {agent_role}"
        
        # Add the response to the chat history
        self._add_to_history(agent_role, response)
        
        # Call the callbacks for response received
        self._trigger_callbacks('response_received', {
            'sender': agent_role,
            'message': response,
            'context': context
        })
        
        return response
    
    def _default_context_handler(self, previous_context: Dict[str, Any], 
                                current_info: Dict[str, Any]) -> Dict[str, Any]:
        """Default context handler that merges the previous context with new information.
        
        Args:
            previous_context: The existing context dictionary
            current_info: New information to add to the context
            
        Returns:
            Updated context dictionary
        """
        # Create a new context dictionary to avoid modifying the original
        updated_context = previous_context.copy()
        
        # Handle the special case of an agent's response
        if 'agent' in current_info and 'response' in current_info:
            agent_role = current_info['agent']
            if 'agent_responses' not in updated_context:
                updated_context['agent_responses'] = {}
            
            # Store the agent's response
            updated_context['agent_responses'][agent_role] = current_info['response']
            
            # Store the last agent to respond
            updated_context['last_agent'] = agent_role
            updated_context['last_response'] = current_info['response']
        
        # Handle the case of a user/system message
        elif 'sender' in current_info and 'message' in current_info:
            sender = current_info['sender']
            if 'messages' not in updated_context:
                updated_context['messages'] = []
            
            # Store the message
            updated_context['messages'].append({
                'sender': sender,
                'message': current_info['message']
            })
        
        # Handle other information by adding it directly to the context
        for key, value in current_info.items():
            if key not in ['agent', 'sender']:  # Skip keys that are handled specially
                updated_context[key] = value
        
        return updated_context
    
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


class SequentialChatFactory(ChatModeFactory):
    """Factory for creating SequentialChat instances."""
    
    @classmethod
    def create(cls, agents: Dict[str, Any], initial_prompt: str, 
              tools: Optional[Dict[str, Any]] = None, 
              config: Optional[Dict[str, Any]] = None) -> BaseChatInterface:
        """Create a SequentialChat instance.
        
        Args:
            agents: Dictionary of agents to use in the chat
            initial_prompt: Initial prompt to start the conversation
            tools: Optional dictionary of tools to bind to the agents
            config: Optional configuration parameters
            
        Returns:
            A configured SequentialChat instance
            
        Raises:
            ValueError: If the configuration is invalid
        """
        if len(agents) < 2:
            raise ValueError("SequentialChat requires at least 2 agents")
        
        # Extract context handler from config if provided
        context_handler = None
        if config and 'context_handler' in config:
            context_handler = config.pop('context_handler')
        
        # Bind tools to agents if supported
        if tools:
            for agent_name, agent in agents.items():
                if hasattr(agent, 'bind_tools'):
                    try:
                        agent.bind_tools(tools)
                    except Exception as e:
                        logger.warning(f"Failed to bind tools to agent {agent_name}: {str(e)}")
        
        return SequentialChat(agents, initial_prompt, context_handler, config)
    
    @classmethod
    def from_config(cls, config_dict: Dict[str, Any]) -> 'SequentialChatFactory':
        """Create a factory instance from configuration.
        
        Args:
            config_dict: Dictionary containing configuration parameters
            
        Returns:
            A configured factory instance
        """
        # This is a simple implementation that just returns the class itself
        # In a more complex scenario, this might return a specialized factory
        return cls