"""
GroupChat implementation for AG2-Agent.

This module implements a multi-agent group chat where multiple agents can participate
in a discussion, with configurable speaking order and facilitation.
"""

from typing import Dict, List, Any, Optional, Callable, Union, Set
import asyncio
import logging
from collections import defaultdict

from core.base_interfaces import BaseChatInterface

logger = logging.getLogger(__name__)


class GroupChat(BaseChatInterface):
    """
    Implementation of multi-agent group chat where agents can discuss in parallel.
    
    Features:
    - Multiple agents can participate in the conversation
    - Configurable speaking order (round-robin, dynamic, or custom)
    - Optional facilitator agent to guide the discussion
    - Support for termination conditions and max rounds
    """
    
    def __init__(self, agents: Dict[str, Any], initial_prompt: str,
                 config: Optional[Dict[str, Any]] = None):
        """
        Initialize a GroupChat instance.
        
        Args:
            agents: Dictionary of agents keyed by role name
            initial_prompt: The system prompt that sets up the group discussion
            config: Configuration parameters for the group chat
                - max_rounds: Maximum number of discussion rounds
                - speaking_order: How agents take turns ("round_robin", "dynamic", or custom function)
                - facilitator: Name of agent that should act as facilitator
                - termination_condition: Function that determines when to end the chat
        """
        self.agents = agents
        self.initial_prompt = initial_prompt
        self.config = config or {}
        
        # Set default configuration
        self.max_rounds = self.config.get("max_rounds", 10)
        self.speaking_order = self.config.get("speaking_order", "round_robin")
        self.facilitator_name = self.config.get("facilitator")
        self.termination_condition = self.config.get("termination_condition")
        
        # Initialize state
        self.history = []
        self.context = {}
        self.current_round = 0
        self.current_speaker_idx = 0
        self.speaker_queue = list(self.agents.keys())
        self.active = False
        self.callbacks = defaultdict(list)
        
        # Set up facilitator if specified
        if self.facilitator_name and self.facilitator_name in self.agents:
            self.facilitator = self.agents[self.facilitator_name]
        else:
            self.facilitator = None
            
        # Track which agents have spoken in current round
        self.spoken_in_round = set()
        
    async def initiate_chat(self, message: str, sender: Optional[str] = None) -> str:
        """
        Start a new group chat with an initial message.
        
        Args:
            message: The initial message/task for the group
            sender: Optional name of the sender (defaults to "user")
            
        Returns:
            The response from the first agent in the group
        """
        self.active = True
        sender = sender or "user"
        
        # Add the initial message to history
        self.history.append({
            "sender": sender,
            "message": message,
            "round": 0
        })
        
        # Trigger message received callbacks
        self._trigger_callbacks("message_received", {
            "sender": sender,
            "message": message
        })
        
        # If we have a facilitator, let them speak first
        if self.facilitator and self.facilitator_name:
            self.current_round = 1
            facilitator_message = await self._get_agent_response(
                self.facilitator_name, message
            )
            
            # Add facilitator's response to history
            self.history.append({
                "sender": self.facilitator_name,
                "message": facilitator_message,
                "round": self.current_round
            })
            
            # Set up next speaker (skip facilitator in order)
            self.speaker_queue = [name for name in self.agents.keys() 
                                 if name != self.facilitator_name]
            self.spoken_in_round = {self.facilitator_name}
            
            return facilitator_message
        
        # Otherwise, let the first agent in the queue speak
        else:
            self.current_round = 1
            next_speaker = self._get_next_speaker()
            speaker_message = await self._get_agent_response(next_speaker, message)
            
            # Add the response to history
            self.history.append({
                "sender": next_speaker,
                "message": speaker_message,
                "round": self.current_round
            })
            
            # Mark speaker as having spoken
            self.spoken_in_round = {next_speaker}
            
            return speaker_message
            
    async def continue_chat(self, message: Optional[str] = None, 
                           sender: Optional[str] = None) -> str:
        """
        Continue the group chat, getting the next agent's response.
        
        Args:
            message: Optional message from external source (like user)
            sender: Optional sender name
            
        Returns:
            The next agent's response in the conversation
        """
        if not self.active:
            raise ValueError("Chat is not active. Call initiate_chat first.")
            
        # If external message is provided, add it to history
        if message and sender:
            self.history.append({
                "sender": sender,
                "message": message,
                "round": self.current_round
            })
            
            # Trigger message received callbacks
            self._trigger_callbacks("message_received", {
                "sender": sender,
                "message": message
            })
            
        # Check if all agents have spoken in this round
        all_spoken = len(self.spoken_in_round) >= len(self.agents)
        
        # If all agents have spoken, start new round
        if all_spoken:
            self.current_round += 1
            self.spoken_in_round = set()
            
            # Check termination conditions
            if self.current_round > self.max_rounds:
                self.active = False
                return "Group chat has reached the maximum number of rounds."
                
            if self.termination_condition and self._check_termination():
                self.active = False
                return "Group chat has reached its conclusion."
                
            # Let facilitator summarize or guide if present
            if self.facilitator and self.facilitator_name:
                facilitator_message = await self._get_facilitator_input()
                self.history.append({
                    "sender": self.facilitator_name,
                    "message": facilitator_message,
                    "round": self.current_round
                })
                self.spoken_in_round.add(self.facilitator_name)
        
        # Get next speaker
        next_speaker = self._get_next_speaker()
        
        # Get the agent's response
        speaker_message = await self._get_agent_response(next_speaker)
        
        # Add response to history
        self.history.append({
            "sender": next_speaker,
            "message": speaker_message,
            "round": self.current_round
        })
        
        # Mark speaker as having spoken
        self.spoken_in_round.add(next_speaker)
        
        # Trigger response generated callbacks
        self._trigger_callbacks("response_generated", {
            "sender": next_speaker,
            "message": speaker_message,
            "round": self.current_round
        })
        
        return speaker_message
    
    def end_chat(self) -> Dict[str, Any]:
        """
        End the group chat and return results.
        
        Returns:
            Dictionary containing chat results, including history and context
        """
        if not self.active:
            logger.warning("Chat was already ended or not started.")
            
        self.active = False
        
        # Trigger chat ended callbacks
        self._trigger_callbacks("chat_ended", {
            "history": self.history,
            "context": self.context,
            "rounds": self.current_round
        })
        
        return {
            "history": self.history,
            "context": self.context,
            "rounds": self.current_round
        }
    
    def get_chat_history(self) -> List[Dict[str, Any]]:
        """
        Get the full conversation history.
        
        Returns:
            List of message dictionaries
        """
        return self.history
    
    def register_callback(self, event_type: str, callback_fn: Callable) -> None:
        """
        Register a callback function for specific events.
        
        Args:
            event_type: Type of event ("message_received", "response_generated", "chat_ended")
            callback_fn: Function to call when the event occurs
        """
        self.callbacks[event_type].append(callback_fn)
        
    async def _get_agent_response(self, agent_name: str, 
                                 specific_prompt: Optional[str] = None) -> str:
        """Get response from a specific agent."""
        agent = self.agents[agent_name]
        
        if specific_prompt:
            # If a specific prompt is provided, use it
            prompt = specific_prompt
        else:
            # Otherwise construct prompt from chat history
            prompt = self._construct_prompt_for_agent(agent_name)
            
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
    
    def _construct_prompt_for_agent(self, agent_name: str) -> str:
        """Construct a prompt for an agent based on recent history."""
        # Get recent messages
        recent_messages = self._get_recent_messages()
        
        # Format them into a prompt
        formatted_history = "\n".join([
            f"{msg['sender']}: {msg['message']}" for msg in recent_messages
        ])
        
        # Create the full prompt
        prompt = (
            f"You are in a group discussion. "
            f"The initial task/question was: {self.initial_prompt}\n\n"
            f"Recent conversation:\n{formatted_history}\n\n"
            f"It's now your turn to speak as {agent_name}. "
            f"Respond to the conversation above."
        )
        
        return prompt
    
    def _get_recent_messages(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get the most recent messages from history."""
        return self.history[-limit:] if len(self.history) > limit else self.history
    
    def _get_relevant_history(self, agent_name: str) -> List[Dict[str, Any]]:
        """Get relevant conversation history for an agent."""
        # For now, return the full history, but this could be customized
        # to filter or process history differently for each agent
        return self.history
    
    def _get_next_speaker(self) -> str:
        """Determine the next agent to speak based on speaking order."""
        if callable(self.speaking_order):
            # Custom function determines speaking order
            return self.speaking_order(
                self.agents, self.history, self.spoken_in_round
            )
        
        elif self.speaking_order == "round_robin":
            # Simple round-robin order
            available_speakers = [name for name in self.speaker_queue 
                                 if name not in self.spoken_in_round]
            
            if not available_speakers:
                # All have spoken, reset for next round
                self.current_round += 1
                self.spoken_in_round = set()
                return self.speaker_queue[0]
            
            return available_speakers[0]
            
        elif self.speaking_order == "dynamic":
            # Dynamically determine based on conversation need
            # This could be determined by a special agent or heuristics
            
            # For now, use round-robin as fallback
            available_speakers = [name for name in self.speaker_queue 
                                 if name not in self.spoken_in_round]
            
            if not available_speakers:
                self.current_round += 1
                self.spoken_in_round = set()
                return self.speaker_queue[0]
                
            return available_speakers[0]
        
        else:
            # Default to round-robin
            available_speakers = [name for name in self.speaker_queue 
                                 if name not in self.spoken_in_round]
            
            if not available_speakers:
                self.current_round += 1
                self.spoken_in_round = set()
                return self.speaker_queue[0]
                
            return available_speakers[0]
    
    async def _get_facilitator_input(self) -> str:
        """Get input from the facilitator agent."""
        if not self.facilitator or not self.facilitator_name:
            return ""
            
        # Create a special prompt for the facilitator
        prompt = (
            f"As the facilitator of this group discussion, please summarize the "
            f"key points from round {self.current_round-1} and guide the group "
            f"to focus on the most important aspects in round {self.current_round}."
        )
        
        return await self._get_agent_response(self.facilitator_name, prompt)
    
    def _check_termination(self) -> bool:
        """Check if the chat should terminate based on configured condition."""
        if not self.termination_condition:
            return False
            
        return self.termination_condition(
            self.history, self.context, self.current_round
        )
        
    def _trigger_callbacks(self, event_type: str, data: Dict[str, Any]) -> None:
        """Trigger registered callbacks for an event."""
        for callback in self.callbacks[event_type]:
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Error in {event_type} callback: {str(e)}")


class GroupChatFactory:
    """Factory for creating GroupChat instances."""
    
    @classmethod
    def create(cls, agents: Dict[str, Any], initial_prompt: str,
              tools: Optional[Dict[str, Any]] = None,
              config: Optional[Dict[str, Any]] = None) -> BaseChatInterface:
        """Create a GroupChat instance."""
        return GroupChat(agents, initial_prompt, config)