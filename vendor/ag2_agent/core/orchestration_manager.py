from typing import Dict, Any, Optional, List, Type, Union
import yaml
import json
import os

from vendor.ag2_agent.core.base_interfaces import BaseChatInterface, ChatModeFactory


class OrchestrationManager:
    """Central manager for orchestrating agent interactions through different chat modes.
    
    The OrchestrationManager serves as the main entry point for creating and managing
    different chat interactions between agents. It maintains registries for agents,
    prompts, tools, and chat mode factories.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the orchestration manager.
        
        Args:
            config_path: Optional path to a configuration file (YAML or JSON)
                to load predefined settings
        """
        self.agent_registry: Dict[str, Any] = {}
        self.prompt_registry: Dict[str, Dict[str, Any]] = {}
        self.tool_registry: Dict[str, Dict[str, Any]] = {}
        self.chat_factories: Dict[str, Type[ChatModeFactory]] = {}
        
        # Load configuration if provided
        if config_path:
            self._load_config(config_path)
    
    def _load_config(self, config_path: str) -> None:
        """Load configuration from a YAML or JSON file.
        
        Args:
            config_path: Path to the configuration file
            
        Raises:
            ValueError: If the file format is not supported or file doesn't exist
            FileNotFoundError: If the config file doesn't exist
        """
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        file_ext = os.path.splitext(config_path)[1].lower()
        
        try:
            with open(config_path, 'r') as f:
                if file_ext == '.yaml' or file_ext == '.yml':
                    config = yaml.safe_load(f)
                elif file_ext == '.json':
                    config = json.load(f)
                else:
                    raise ValueError(f"Unsupported configuration file format: {file_ext}")
        except Exception as e:
            raise ValueError(f"Error loading configuration: {str(e)}")
        
        # Process configuration sections
        if 'agents' in config:
            for name, agent_config in config.get('agents', {}).items():
                self.register_agent(name, agent_config)
                
        if 'prompts' in config:
            for name, prompt_config in config.get('prompts', {}).items():
                self.register_prompt(
                    name, 
                    prompt_config.get('template'),
                    prompt_config.get('agent_type')
                )
                
        if 'tools' in config:
            for name, tool_config in config.get('tools', {}).items():
                # Note: actual tool functions need to be loaded dynamically
                # This is a placeholder that would need to be implemented
                # based on how tools are defined in the application
                self.register_tool(
                    name,
                    None,  # Tool function placeholder
                    tool_config.get('description')
                )
                
        # Chat modes would need a proper factory registration mechanism
    
    def register_agent(self, name: str, agent_config: Any, overwrite: bool = False) -> None:
        """Register an agent with the orchestration manager.
        
        Args:
            name: Unique identifier for the agent
            agent_config: Configuration for the agent (dictionary or instance)
            overwrite: Whether to overwrite an existing agent with the same name
            
        Raises:
            ValueError: If an agent with the same name exists and overwrite is False
        """
        if name in self.agent_registry and not overwrite:
            raise ValueError(f"Agent '{name}' already registered. Set overwrite=True to replace.")
        
        self.agent_registry[name] = agent_config
    
    def register_prompt(self, name: str, prompt_template: Any, agent_type: Optional[str] = None) -> None:
        """Register a prompt template.
        
        Args:
            name: Name of the prompt template
            prompt_template: The template string or callable
            agent_type: Optional agent type this prompt is designed for
        """
        self.prompt_registry[name] = {
            'template': prompt_template,
            'agent_type': agent_type
        }
    
    def register_tool(self, name: str, tool_function: Any, description: Optional[str] = None) -> None:
        """Register a tool that can be used by agents.
        
        Args:
            name: Name of the tool
            tool_function: Function or class implementing the tool
            description: Description of what the tool does (for LLM understanding)
        """
        self.tool_registry[name] = {
            'function': tool_function,
            'description': description
        }
    
    def register_chat_factory(self, mode_name: str, factory_class: Type[ChatModeFactory]) -> None:
        """Register a chat mode factory.
        
        Args:
            mode_name: Name of the chat mode
            factory_class: Factory class for creating instances of this chat mode
        """
        self.chat_factories[mode_name] = factory_class
    
    def create_chat(self, mode: str, agents: Optional[Union[List[str], Dict[str, Any]]] = None, 
                   initial_prompt: Optional[str] = None, config: Optional[Dict[str, Any]] = None) -> BaseChatInterface:
        """Create a chat instance of the specified mode.
        
        Args:
            mode: Name of the chat mode to create
            agents: List of agent names or dictionary mapping roles to agent names
            initial_prompt: Initial prompt to start the conversation
            config: Additional configuration specific to this chat mode
            
        Returns:
            An instance of the requested chat mode
            
        Raises:
            ValueError: If the mode is not supported or configuration is invalid
        """
        if mode not in self.chat_factories:
            raise ValueError(f"Chat mode '{mode}' not supported. Available modes: {list(self.chat_factories.keys())}")
        
        # Resolve agent references if needed
        resolved_agents = {}
        if isinstance(agents, list):
            # Convert list of agent names to dictionary
            for i, agent_name in enumerate(agents):
                if agent_name in self.agent_registry:
                    resolved_agents[f"agent_{i}"] = self.agent_registry[agent_name]
                else:
                    raise ValueError(f"Agent '{agent_name}' not found in registry")
        elif isinstance(agents, dict):
            # Resolve agent names to actual agents
            for role, agent_name in agents.items():
                if agent_name in self.agent_registry:
                    resolved_agents[role] = self.agent_registry[agent_name]
                else:
                    resolved_agents[role] = agent_name  # Assume it's already an agent instance
        elif agents is None:
            # No agents provided, use empty dict
            resolved_agents = {}
        
        factory = self.chat_factories[mode]
        return factory.create(
            agents=resolved_agents,
            initial_prompt=initial_prompt,
            tools=self.tool_registry,
            config=config
        )
    
    def get_agent(self, name: str) -> Any:
        """Get a registered agent by name.
        
        Args:
            name: Name of the agent to retrieve
            
        Returns:
            The agent configuration or instance
            
        Raises:
            ValueError: If the agent is not found
        """
        if name not in self.agent_registry:
            raise ValueError(f"Agent '{name}' not found in registry")
        
        return self.agent_registry[name]
    
    def get_prompt(self, name: str) -> Dict[str, Any]:
        """Get a registered prompt template by name.
        
        Args:
            name: Name of the prompt template to retrieve
            
        Returns:
            The prompt template configuration
            
        Raises:
            ValueError: If the prompt template is not found
        """
        if name not in self.prompt_registry:
            raise ValueError(f"Prompt '{name}' not found in registry")
        
        return self.prompt_registry[name]
    
    def get_tool(self, name: str) -> Dict[str, Any]:
        """Get a registered tool by name.
        
        Args:
            name: Name of the tool to retrieve
            
        Returns:
            The tool configuration
            
        Raises:
            ValueError: If the tool is not found
        """
        if name not in self.tool_registry:
            raise ValueError(f"Tool '{name}' not found in registry")
        
        return self.tool_registry[name]