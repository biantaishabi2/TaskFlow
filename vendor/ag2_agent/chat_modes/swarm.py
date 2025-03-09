"""
Swarm implementation for AG2-Agent.

This module implements a swarm pattern where multiple agents collaborate on complex tasks
by dividing work, specializing in different areas, and communicating results.
"""

from typing import Dict, List, Any, Optional, Callable, Union, Set
import asyncio
import logging
from collections import defaultdict
import uuid

from core.base_interfaces import BaseChatInterface

logger = logging.getLogger(__name__)


class Swarm(BaseChatInterface):
    """
    Implementation of swarm pattern where agents collaborate on complex tasks.
    
    Features:
    - Task decomposition and distribution
    - Agent specialization and expertise
    - Dynamic handoffs between agents
    - Results aggregation and synthesis
    """
    
    def __init__(self, agents: Dict[str, Any], initial_prompt: str,
                 config: Optional[Dict[str, Any]] = None):
        """
        Initialize a Swarm instance.
        
        Args:
            agents: Dictionary of agents keyed by role/expertise
            initial_prompt: The system prompt describing the main task
            config: Configuration parameters for the swarm
                - coordinator: Name of agent that coordinates task decomposition (default: first agent)
                - synthesizer: Name of agent that synthesizes results (default: coordinator)
                - max_subtasks: Maximum number of subtasks allowed (default: 5)
                - parallel_execution: Whether to execute subtasks in parallel (default: True)
        """
        self.agents = agents
        self.initial_prompt = initial_prompt
        self.config = config or {}
        
        # Set default configuration
        self.coordinator_name = self.config.get("coordinator", list(agents.keys())[0])
        self.synthesizer_name = self.config.get("synthesizer", self.coordinator_name)
        self.max_subtasks = self.config.get("max_subtasks", 5)
        self.parallel_execution = self.config.get("parallel_execution", True)
        
        # Initialize state
        self.history = []
        self.context = {}
        self.subtasks = {}
        self.subtask_results = {}
        self.task_assignments = {}
        self.active = False
        self.main_task_complete = False
        self.callbacks = defaultdict(list)
        
        # Get coordinator and synthesizer agents
        self.coordinator = self.agents[self.coordinator_name]
        self.synthesizer = self.agents[self.synthesizer_name]
    
    async def initiate_chat(self, message: str, sender: Optional[str] = None) -> str:
        """
        Start a new swarm with an initial task description.
        
        Args:
            message: The main task description
            sender: Optional identifier of the sender
            
        Returns:
            The coordinator's response with task decomposition
        """
        self.active = True
        sender = sender or "user"
        
        # Add the initial message to history
        self.history.append({
            "sender": sender,
            "message": message,
            "type": "main_task"
        })
        
        # Store the main task in context
        self.context["main_task"] = message
        
        # Trigger task received callbacks
        self._trigger_callbacks("task_received", {
            "sender": sender,
            "task": message
        })
        
        # Get coordinator to decompose the task
        coordinator_prompt = (
            f"作为协调者，你的工作是将这个复杂任务分解为更小的子任务，并将其分配给专业代理。对于每个子任务，请指明：\n"
            f"1. 清晰的子任务描述\n"
            f"2. 哪种代理专长最适合完成该子任务\n"
            f"3. 子任务之间的任何依赖关系\n\n"
            f"主任务: {message}\n\n"
            f"可用的代理专长: {', '.join(self.agents.keys())}\n\n"
            f"请以结构化格式提供您的回应，明确编号每个子任务。请使用中文回复。"
        )
        
        # Get decomposition from coordinator
        decomposition = await self._get_agent_response(
            self.coordinator_name, coordinator_prompt
        )
        
        # Add decomposition to history
        self.history.append({
            "sender": self.coordinator_name,
            "message": decomposition,
            "type": "task_decomposition"
        })
        
        # Parse the decomposition and create subtasks
        subtasks = self._parse_task_decomposition(decomposition)
        
        # Store subtasks in context
        self.context["subtasks"] = subtasks
        self.subtasks = subtasks
        
        # Trigger tasks decomposed callbacks
        self._trigger_callbacks("tasks_decomposed", {
            "subtasks": subtasks,
            "coordinator": self.coordinator_name
        })
        
        # Return the decomposition response
        return (
            f"Task received and decomposed into {len(subtasks)} subtasks. "
            f"Use continue_chat() to execute the subtasks."
        )
    
    async def continue_chat(self, message: Optional[str] = None, 
                           sender: Optional[str] = None) -> str:
        """
        Continue the swarm process by executing subtasks or synthesizing results.
        
        Args:
            message: Optional message or instructions
            sender: Optional sender identifier
            
        Returns:
            Progress update or final synthesized results
        """
        if not self.active:
            raise ValueError("Swarm is not active. Call initiate_chat first.")
        
        # If message is provided, add it to history
        if message:
            sender = sender or "user"
            self.history.append({
                "sender": sender,
                "message": message,
                "type": "instruction"
            })
            
            # If it's an instruction to focus on specific subtasks
            if "focus on" in message.lower() or "prioritize" in message.lower():
                self._update_subtask_priorities(message)
        
        # If all subtasks are complete, synthesize results
        if self.main_task_complete:
            return "The main task is already complete. No further processing needed."
            
        # Check if all subtasks are complete
        all_complete = all(
            subtask_id in self.subtask_results
            for subtask_id in self.subtasks.keys()
        )
        
        if all_complete and not self.main_task_complete:
            # Synthesize results
            synthesis = await self._synthesize_results()
            
            # Mark main task as complete
            self.main_task_complete = True
            
            # Return synthesis
            return synthesis
        
        # Execute pending subtasks
        pending_subtasks = {
            subtask_id: subtask
            for subtask_id, subtask in self.subtasks.items()
            if subtask_id not in self.subtask_results
        }
        
        # Determine which subtasks can be executed (no pending dependencies)
        executable_subtasks = {}
        for subtask_id, subtask in pending_subtasks.items():
            dependencies = subtask.get("dependencies", [])
            if all(dep in self.subtask_results for dep in dependencies):
                executable_subtasks[subtask_id] = subtask
        
        if not executable_subtasks:
            return "No executable subtasks found. There may be circular dependencies."
        
        # Execute subtasks
        if self.parallel_execution:
            # Execute all executable subtasks in parallel
            tasks = [
                self._execute_subtask(subtask_id, subtask)
                for subtask_id, subtask in executable_subtasks.items()
            ]
            await asyncio.gather(*tasks)
            
            return (
                f"Executed {len(executable_subtasks)} subtasks in parallel. "
                f"{len(self.subtask_results)}/{len(self.subtasks)} subtasks completed. "
                f"Use continue_chat() to proceed."
            )
        else:
            # Execute just the first executable subtask
            subtask_id = list(executable_subtasks.keys())[0]
            subtask = executable_subtasks[subtask_id]
            await self._execute_subtask(subtask_id, subtask)
            
            return (
                f"Executed subtask '{subtask_id}'. "
                f"{len(self.subtask_results)}/{len(self.subtasks)} subtasks completed. "
                f"Use continue_chat() to proceed."
            )
    
    def end_chat(self) -> Dict[str, Any]:
        """
        End the swarm and clean up resources.
        
        Returns:
            A dictionary containing task results and metadata
        """
        if not self.active:
            logger.warning("Swarm was already ended or not started.")
        
        self.active = False
        
        # Prepare results
        results = {
            "main_task": self.context.get("main_task", ""),
            "complete": self.main_task_complete,
            "subtasks": self.subtasks,
            "subtask_results": self.subtask_results,
            "final_result": self.context.get("final_result", None),
            "history": self.history
        }
        
        # Trigger swarm ended callbacks
        self._trigger_callbacks("swarm_ended", results)
        
        return results
    
    def get_chat_history(self) -> List[Dict[str, Any]]:
        """
        Get the full history of the swarm process.
        
        Returns:
            A list of message dictionaries representing the swarm history
        """
        return self.history
    
    def register_callback(self, event_type: str, callback_fn: Callable) -> None:
        """
        Register a callback function for specific events.
        
        Args:
            event_type: Type of event to trigger the callback
                - "task_received": When the main task is received
                - "tasks_decomposed": When tasks are decomposed
                - "subtask_started": When a subtask begins execution
                - "subtask_completed": When a subtask is completed
                - "results_synthesized": When final results are synthesized
                - "swarm_ended": When the swarm is ended
            callback_fn: Function to call when the event occurs
        """
        self.callbacks[event_type].append(callback_fn)
    
    def get_subtask_status(self) -> Dict[str, Any]:
        """
        Get the current status of all subtasks.
        
        Returns:
            Dictionary with subtask status information
        """
        status = {}
        for subtask_id, subtask in self.subtasks.items():
            status[subtask_id] = {
                "description": subtask.get("description", ""),
                "assigned_to": subtask.get("assigned_to", ""),
                "dependencies": subtask.get("dependencies", []),
                "complete": subtask_id in self.subtask_results,
                "result": self.subtask_results.get(subtask_id, None)
            }
            
        return status
    
    async def execute_specific_subtask(self, subtask_id: str) -> Optional[str]:
        """
        Execute a specific subtask regardless of dependencies.
        
        Args:
            subtask_id: ID of the subtask to execute
            
        Returns:
            The result of the subtask, or None if the subtask doesn't exist
        """
        if subtask_id not in self.subtasks:
            return None
            
        subtask = self.subtasks[subtask_id]
        await self._execute_subtask(subtask_id, subtask)
        
        return self.subtask_results.get(subtask_id)
    
    async def _get_agent_response(self, agent_name: str, 
                                 prompt: str,
                                 context_data: Optional[Dict[str, Any]] = None) -> str:
        """Get response from a specific agent."""
        agent = self.agents[agent_name]
        
        # Prepare context for this specific request
        request_context = {}
        if context_data:
            request_context.update(context_data)
        
        # Include global context as well
        request_context.update(self.context)
        
        # Generate response
        try:
            # Get a limited history relevant to this request
            relevant_history = self._get_relevant_history(agent_name)
            
            response = await agent.generate_response(
                prompt, 
                history=relevant_history,
                context=request_context
            )
            return response
        except Exception as e:
            logger.error(f"Error getting response from agent {agent_name}: {str(e)}")
            return f"[Agent {agent_name} encountered an error: {str(e)}]"
    
    def _get_relevant_history(self, agent_name: str) -> List[Dict[str, Any]]:
        """Get relevant conversation history for an agent."""
        # For the swarm implementation, only include high-level events
        # and specific subtask history if the agent worked on it before
        relevant_types = ["main_task", "task_decomposition", "instruction", "result_synthesis"]
        
        # Include subtask executions if this agent was involved
        agent_subtasks = [entry for entry in self.history
                        if entry.get("type") == "subtask_execution"
                        and entry.get("agent") == agent_name]
        
        # Filter main history
        main_history = [entry for entry in self.history
                      if entry.get("type") in relevant_types]
        
        # Combine and sort by implicit order in the history list
        combined = main_history + agent_subtasks
        return sorted(combined, key=lambda x: self.history.index(x))
    
    def _parse_task_decomposition(self, decomposition: str) -> Dict[str, Dict[str, Any]]:
        """Parse the coordinator's task decomposition into structured subtasks."""
        # This is a simplified parsing logic for demonstration
        # In a real implementation, this would use more robust parsing
        # such as asking the model to output structured JSON
        
        subtasks = {}
        current_subtask = None
        
        # Split by lines for simple parsing
        lines = decomposition.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Look for subtask headers (numbers or "Subtask N:")
            if (line.startswith(("Subtask", "Task", "Step")) and ":" in line) or line[0].isdigit():
                if current_subtask:
                    # Store the previous subtask
                    subtask_id = f"subtask_{len(subtasks) + 1}"
                    subtasks[subtask_id] = current_subtask
                
                # Start a new subtask
                current_subtask = {
                    "description": line.split(":", 1)[1].strip() if ":" in line else line,
                    "dependencies": [],
                    "assigned_to": None
                }
            
            # Look for agent assignment
            elif current_subtask and ("agent:" in line.lower() or "expertise:" in line.lower()):
                for agent_name in self.agents.keys():
                    if agent_name.lower() in line.lower():
                        current_subtask["assigned_to"] = agent_name
                        break
                        
                # If no specific agent found, assign to the first matching expertise keyword
                if not current_subtask["assigned_to"]:
                    for agent_name in self.agents.keys():
                        # Look for words that might indicate expertise
                        expertise_keywords = agent_name.lower().split("_")
                        if any(keyword in line.lower() for keyword in expertise_keywords):
                            current_subtask["assigned_to"] = agent_name
                            break
            
            # Look for dependencies
            elif current_subtask and ("depends" in line.lower() or "after" in line.lower() or "prerequisite" in line.lower()):
                # This is a simplified dependency extraction
                # Look for numbers that might indicate subtask IDs
                for i in range(1, len(subtasks) + 1):
                    if str(i) in line:
                        current_subtask["dependencies"].append(f"subtask_{i}")
            
            # Add additional details to description
            elif current_subtask:
                current_subtask["description"] += " " + line
        
        # Add the last subtask
        if current_subtask:
            subtask_id = f"subtask_{len(subtasks) + 1}"
            subtasks[subtask_id] = current_subtask
            
        # Assign agents to subtasks that didn't get an assignment
        for subtask_id, subtask in subtasks.items():
            if not subtask["assigned_to"]:
                # Assign to coordinator as fallback
                subtask["assigned_to"] = self.coordinator_name
        
        return subtasks
    
    def _update_subtask_priorities(self, instruction: str) -> None:
        """Update subtask priorities based on user instruction."""
        # This method would implement logic to prioritize certain subtasks
        # based on user instructions. For simplicity, we're not implementing
        # the full details here, but it would typically involve:
        # 1. Parsing the instruction to identify which subtasks to prioritize
        # 2. Marking those subtasks for priority execution
        # 3. Potentially reordering the subtask execution queue
        
        # This is where additional logic would go
        pass
    
    async def _execute_subtask(self, subtask_id: str, subtask: Dict[str, Any]) -> None:
        """Execute a specific subtask using the assigned agent."""
        agent_name = subtask.get("assigned_to")
        if not agent_name or agent_name not in self.agents:
            # Default to coordinator if no valid agent is assigned
            agent_name = self.coordinator_name
            
        # Create the subtask prompt
        subtask_prompt = self._create_subtask_prompt(subtask_id, subtask)
        
        # Create context with dependency results
        dependency_context = {}
        for dep_id in subtask.get("dependencies", []):
            if dep_id in self.subtask_results:
                dependency_context[f"dependency_{dep_id}_result"] = self.subtask_results[dep_id]
        
        # Add subtask execution entry to history
        self.history.append({
            "sender": "system",
            "message": f"Executing subtask '{subtask_id}' using agent '{agent_name}'",
            "type": "subtask_execution",
            "subtask_id": subtask_id,
            "agent": agent_name
        })
        
        # Trigger subtask started callbacks
        self._trigger_callbacks("subtask_started", {
            "subtask_id": subtask_id,
            "agent": agent_name,
            "description": subtask.get("description", "")
        })
        
        # Execute the subtask
        result = await self._get_agent_response(
            agent_name,
            subtask_prompt,
            context_data=dependency_context
        )
        
        # Store the result
        self.subtask_results[subtask_id] = result
        
        # Add result to history
        self.history.append({
            "sender": agent_name,
            "message": result,
            "type": "subtask_result",
            "subtask_id": subtask_id
        })
        
        # Trigger subtask completed callbacks
        self._trigger_callbacks("subtask_completed", {
            "subtask_id": subtask_id,
            "agent": agent_name,
            "result": result
        })
    
    def _create_subtask_prompt(self, subtask_id: str, subtask: Dict[str, Any]) -> str:
        """Create a prompt for a specific subtask."""
        description = subtask.get("description", "")
        
        # Start with main task context
        prompt = (
            f"你正在作为一个较大任务的一部分处理一个子任务。\n\n"
            f"主任务: {self.context.get('main_task', '')}\n\n"
            f"你的子任务 ({subtask_id}): {description}\n\n"
        )
        
        # Add dependency information if applicable
        dependencies = subtask.get("dependencies", [])
        if dependencies:
            prompt += "这个子任务基于以下已完成的子任务：\n\n"
            for dep_id in dependencies:
                if dep_id in self.subtask_results:
                    dep_result = self.subtask_results[dep_id]
                    dep_desc = self.subtasks.get(dep_id, {}).get("description", "")
                    prompt += f"- {dep_id}: {dep_desc}\n"
                    prompt += f"  结果: {dep_result[:200]}...\n\n"
        
        # Add final instructions
        prompt += (
            f"请全面完成这个子任务并提供你的结果。"
            f"请专注于这个子任务的具体要求。请使用中文回复。"
        )
        
        return prompt
    
    async def _synthesize_results(self) -> str:
        """Synthesize all subtask results into a final result."""
        # Create synthesizer prompt
        synthesis_prompt = (
            f"你是一个复杂任务的综合者，该任务已被分解为多个子任务。\n\n"
            f"主任务: {self.context.get('main_task', '')}\n\n"
            f"以下子任务已经完成。你的工作是将所有结果综合为一个连贯的最终回应，以解决主任务。\n\n"
        )
        
        # Add all subtask results
        for subtask_id, result in self.subtask_results.items():
            subtask = self.subtasks.get(subtask_id, {})
            description = subtask.get("description", "")
            agent = subtask.get("assigned_to", "unknown")
            
            synthesis_prompt += f"子任务 {subtask_id} ({agent}):\n"
            synthesis_prompt += f"描述: {description}\n"
            synthesis_prompt += f"结果: {result}\n\n"
        
        # Add final instructions
        synthesis_prompt += (
            f"将所有这些结果综合为一个全面的最终回应，以解决主任务。"
            f"确保你的综合报告组织良好，整合所有相关信息，并提供完整的解决方案。请使用中文回复。"
        )
        
        # Get synthesis from synthesizer
        synthesis = await self._get_agent_response(
            self.synthesizer_name,
            synthesis_prompt
        )
        
        # Store synthesis in context
        self.context["final_result"] = synthesis
        
        # Add synthesis to history
        self.history.append({
            "sender": self.synthesizer_name,
            "message": synthesis,
            "type": "result_synthesis"
        })
        
        # Trigger results synthesized callbacks
        self._trigger_callbacks("results_synthesized", {
            "synthesizer": self.synthesizer_name,
            "synthesis": synthesis
        })
        
        return synthesis
    
    def _trigger_callbacks(self, event_type: str, data: Dict[str, Any]) -> None:
        """Trigger registered callbacks for an event."""
        for callback in self.callbacks[event_type]:
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Error in {event_type} callback: {str(e)}")


class SwarmFactory:
    """Factory for creating Swarm instances."""
    
    @classmethod
    def create(cls, agents: Dict[str, Any], initial_prompt: str,
              tools: Optional[Dict[str, Any]] = None,
              config: Optional[Dict[str, Any]] = None) -> BaseChatInterface:
        """Create a Swarm instance."""
        return Swarm(agents, initial_prompt, config)