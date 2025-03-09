"""
NestedChat implementation for AG2-Agent.

This module implements a nested chat pattern where a parent chat can spawn child chats,
allowing for hierarchical conversation structures.
"""

from typing import Dict, List, Any, Optional, Callable, Union
import asyncio
import logging
from collections import defaultdict

from core.base_interfaces import BaseChatInterface

logger = logging.getLogger(__name__)


class NestedChat(BaseChatInterface):
    """
    Implementation of nested chat where parent chats can spawn child chats.
    
    Features:
    - Hierarchical chat structure with parent and child conversations
    - Context sharing between parent and child chats
    - Support for multiple levels of nesting
    - Flexible child chat creation and management
    """
    
    def __init__(self, agents: Dict[str, Any], initial_prompt: str,
                 config: Optional[Dict[str, Any]] = None):
        """
        Initialize a NestedChat instance.
        
        Args:
            agents: Dictionary of agents keyed by role name
            initial_prompt: The system prompt that sets up the main conversation
            config: Configuration parameters for the nested chat
                - max_depth: Maximum nesting depth allowed (default: 3)
                - context_sharing: How context is shared ("bidirectional", "down_only", "up_only")
                - default_child_mode: Default mode for child chats ("sequential", "two_agent", etc.)
        """
        self.agents = agents
        self.initial_prompt = initial_prompt
        self.config = config or {}
        
        # Set default configuration
        self.max_depth = self.config.get("max_depth", 3)
        self.context_sharing = self.config.get("context_sharing", "bidirectional")
        self.default_child_mode = self.config.get("default_child_mode", "two_agent")
        
        # Initialize state
        self.history = []
        self.context = {}
        self.parent = None
        self.children = {}
        self.depth = 0
        self.active = False
        self.callbacks = defaultdict(list)
        
        # Track current active agent and message
        self.current_agent = None
        self.last_message = None
        
        # If this is a child chat, capture the parent and adjust depth
        if "parent" in self.config:
            self.parent = self.config["parent"]
            self.depth = self.parent.depth + 1
        
    async def initiate_chat(self, message: str, sender: Optional[str] = None) -> str:
        """
        Start a new nested chat with an initial message.
        
        Args:
            message: The initial message to start the conversation
            sender: Optional identifier of the sender
            
        Returns:
            The response to the initial message
        """
        # Check if we're exceeding the maximum depth
        if self.max_depth is not None and self.depth >= self.max_depth:
            raise ValueError(f"Maximum nesting depth ({self.max_depth}) exceeded")
        
        self.active = True
        sender = sender or "user"
        self.last_message = message
        
        # Add the initial message to history
        self.history.append({
            "sender": sender,
            "message": message,
            "type": "message"
        })
        
        # Default to the first agent in the dict if sender is not an agent
        if sender not in self.agents:
            self.current_agent = list(self.agents.keys())[0]
        else:
            # Find the next agent after the sender
            agent_keys = list(self.agents.keys())
            if sender in agent_keys:
                sender_idx = agent_keys.index(sender)
                next_idx = (sender_idx + 1) % len(agent_keys)
                self.current_agent = agent_keys[next_idx]
            else:
                self.current_agent = agent_keys[0]
        
        # Get response from the selected agent
        response = await self._get_agent_response(self.current_agent, message)
        
        # Add the response to history
        self.history.append({
            "sender": self.current_agent,
            "message": response,
            "type": "message"
        })
        
        # Update context if needed
        self._update_context()
        
        # Trigger response generated callbacks
        self._trigger_callbacks("response_generated", {
            "sender": self.current_agent,
            "message": response
        })
        
        return response
    
    async def continue_chat(self, message: Optional[str] = None, 
                           sender: Optional[str] = None) -> str:
        """
        Continue the nested chat, with optional child chat creation.
        
        Args:
            message: Optional message to add to the conversation
            sender: Optional identifier of the sender
            
        Returns:
            The next response in the conversation
        """
        if not self.active:
            raise ValueError("Chat is not active. Call initiate_chat first.")
        
        # If a message is provided, add it to history
        if message is not None:
            sender = sender or "user"
            self.last_message = message
            
            # Add the message to history
            self.history.append({
                "sender": sender,
                "message": message,
                "type": "message"
            })
            
            # Trigger message received callbacks
            self._trigger_callbacks("message_received", {
                "sender": sender,
                "message": message
            })
        
        # Determine the next agent to respond
        agent_keys = list(self.agents.keys())
        if self.current_agent in agent_keys:
            current_idx = agent_keys.index(self.current_agent)
            next_idx = (current_idx + 1) % len(agent_keys)
            self.current_agent = agent_keys[next_idx]
        else:
            self.current_agent = agent_keys[0]
        
        # Get response from the next agent
        response = await self._get_agent_response(self.current_agent)
        
        # Check if the response indicates a need for a child chat
        if self._should_create_child_chat(response):
            # Extract child chat parameters from the response
            child_params = self._extract_child_chat_params(response)
            
            # Create and initiate the child chat
            child_id, child_chat = await self._create_child_chat(child_params)
            
            # Add an entry to the history indicating a child chat was created
            self.history.append({
                "sender": self.current_agent,
                "message": f"Creating child chat: {child_id}",
                "type": "system",
                "child_id": child_id
            })
            
            # Return the child chat creation notification
            return f"Child chat '{child_id}' has been created and initiated."
        
        # For normal responses, add to history
        self.history.append({
            "sender": self.current_agent,
            "message": response,
            "type": "message"
        })
        
        # Update shared context
        self._update_context()
        
        # Trigger response generated callbacks
        self._trigger_callbacks("response_generated", {
            "sender": self.current_agent,
            "message": response
        })
        
        return response
    
    def end_chat(self) -> Dict[str, Any]:
        """
        End the nested chat and clean up resources.
        
        Returns:
            A dictionary containing conversation summary and metadata
        """
        if not self.active:
            logger.warning("Chat was already ended or not started.")
        
        # End all child chats first
        for child_id, child_chat in self.children.items():
            if child_chat.active:
                child_results = child_chat.end_chat()
                # Store child results in this chat's context
                self.context[f"child_{child_id}_results"] = child_results
        
        self.active = False
        
        # Prepare results
        results = {
            "history": self.history,
            "context": self.context,
            "child_chats": {child_id: {"active": child.active} 
                           for child_id, child in self.children.items()},
            "depth": self.depth
        }
        
        # Trigger chat ended callbacks
        self._trigger_callbacks("chat_ended", results)
        
        return results
    
    def get_chat_history(self) -> List[Dict[str, Any]]:
        """
        Get the full history of the conversation.
        
        Returns:
            A list of message dictionaries representing the conversation history
        """
        return self.history
    
    def register_callback(self, event_type: str, callback_fn: Callable) -> None:
        """
        Register a callback function for specific events.
        
        Args:
            event_type: Type of event to trigger the callback
            callback_fn: Function to call when the event occurs
        """
        self.callbacks[event_type].append(callback_fn)
    
    async def get_child_chat(self, child_id: str) -> Optional[BaseChatInterface]:
        """
        Get a child chat by ID.
        
        Args:
            child_id: Identifier of the child chat
            
        Returns:
            The child chat instance if it exists, None otherwise
        """
        return self.children.get(child_id)
    
    async def create_child_chat(self, mode: str, agents: Dict[str, Any], 
                              initial_prompt: str, 
                              config: Optional[Dict[str, Any]] = None) -> str:
        """
        Explicitly create a new child chat.
        
        Args:
            mode: The chat mode for the child ("sequential", "two_agent", etc.)
            agents: Dictionary mapping role names to agent references
            initial_prompt: The initial prompt for the child chat
            config: Optional configuration for the child chat
            
        Returns:
            The ID of the new child chat
        """
        if self.max_depth is not None and self.depth >= self.max_depth:
            raise ValueError(f"Maximum nesting depth ({self.max_depth}) exceeded")
        
        # Prepare child parameters
        child_params = {
            "mode": mode,
            "agents": agents,
            "initial_prompt": initial_prompt,
            "config": config or {}
        }
        
        # Create the child chat
        child_id, _ = await self._create_child_chat(child_params)
        
        # Add an entry to the history
        self.history.append({
            "sender": "system",
            "message": f"Created child chat: {child_id}",
            "type": "system",
            "child_id": child_id
        })
        
        return child_id
    
    async def _get_agent_response(self, agent_name: str, 
                                 specific_prompt: Optional[str] = None) -> str:
        """Get response from a specific agent."""
        agent = self.agents[agent_name]
        
        if specific_prompt:
            # If a specific prompt is provided, use it
            prompt = specific_prompt
        else:
            # Otherwise use the last message
            prompt = self.last_message if self.last_message else self.initial_prompt
        
        # Get relevant history for context
        relevant_history = self._get_relevant_history(agent_name)
        
        # Generate response
        try:
            response = await agent.generate_response(
                prompt, 
                history=relevant_history,
                context=self.context
            )
            return response
        except Exception as e:
            logger.error(f"Error getting response from agent {agent_name}: {str(e)}")
            return f"[Agent {agent_name} encountered an error: {str(e)}]"
    
    def _get_relevant_history(self, agent_name: str) -> List[Dict[str, Any]]:
        """Get relevant conversation history for an agent."""
        # Filter out system messages about child chats for clarity
        return [msg for msg in self.history if msg.get("type") == "message"]
    
    def _should_create_child_chat(self, response: str) -> bool:
        """Determine if we should create a child chat based on the response."""
        # Simple heuristic: Check for keywords in the response
        child_indicators = [
            "create child chat",
            "start subtask",
            "create subtask",
            "initiate child conversation",
            "create nested chat"
        ]
        
        response_lower = response.lower()
        return any(indicator in response_lower for indicator in child_indicators)
    
    def _extract_child_chat_params(self, response: str) -> Dict[str, Any]:
        """Extract child chat parameters from an agent response."""
        # Default parameters
        params = {
            "mode": self.default_child_mode,
            "agents": {k: v for k, v in self.agents.items()},
            "initial_prompt": "Subtask from parent chat",
            "config": {"parent": self}
        }
        
        # In a real implementation, this would parse structured information from the response
        # For example, it might look for JSON blocks or special formatting
        
        # Simple example of extraction logic (would be more sophisticated in practice)
        if "mode:" in response:
            mode_text = response.split("mode:")[1].split("\n")[0].strip()
            params["mode"] = mode_text
            
        if "subtask:" in response:
            subtask_text = response.split("subtask:")[1].split("\n")[0].strip()
            params["initial_prompt"] = subtask_text
        
        return params
    
    async def _create_child_chat(self, params: Dict[str, Any]) -> tuple[str, BaseChatInterface]:
        """Create a child chat with the given parameters."""
        # Generate a unique ID for the child
        child_id = f"child_{len(self.children) + 1}"
        
        # Ensure the child config includes parent reference
        if "config" not in params:
            params["config"] = {}
        params["config"]["parent"] = self
        
        # In a real implementation, this would use the orchestration manager
        # to create the appropriate chat mode
        
        # For now, just create another NestedChat (would be more flexible in practice)
        child_chat = NestedChat(
            params["agents"],
            params["initial_prompt"],
            params["config"]
        )
        
        # Store the child chat
        self.children[child_id] = child_chat
        
        # Initiate the child chat with the initial prompt
        await child_chat.initiate_chat(params["initial_prompt"])
        
        return child_id, child_chat
    
    def _update_context(self) -> None:
        """Update shared context based on the context sharing configuration."""
        # If we have a parent, update context appropriately
        if self.parent:
            if self.context_sharing in ["bidirectional", "up_only"]:
                # Share our context up to the parent
                for key, value in self.context.items():
                    # Prefix child-specific keys to avoid collision
                    parent_key = f"child_{self.depth}_{key}"
                    self.parent.context[parent_key] = value
            
            if self.context_sharing in ["bidirectional", "down_only"]:
                # Get context from parent
                for key, value in self.parent.context.items():
                    # Only copy keys that don't start with "child_" to avoid loops
                    if not key.startswith("child_"):
                        self.context[f"parent_{key}"] = value
    
    def _trigger_callbacks(self, event_type: str, data: Dict[str, Any]) -> None:
        """Trigger registered callbacks for an event."""
        for callback in self.callbacks[event_type]:
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Error in {event_type} callback: {str(e)}")


class NestedChatFactory:
    """Factory for creating NestedChat instances."""
    
    @classmethod
    def create(cls, agents: Dict[str, Any], initial_prompt: str,
              tools: Optional[Dict[str, Any]] = None,
              config: Optional[Dict[str, Any]] = None) -> BaseChatInterface:
        """Create a NestedChat instance."""
        return NestedChat(agents, initial_prompt, config)