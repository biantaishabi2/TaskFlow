from typing import Dict, Type
from core.base_interfaces import ChatModeFactory
from chat_modes.two_agent_chat import TwoAgentChatFactory
from chat_modes.sequential_chat import SequentialChatFactory
from chat_modes.group_chat import GroupChatFactory
from chat_modes.nested_chat import NestedChatFactory
from chat_modes.swarm import SwarmFactory


def register_default_factories() -> Dict[str, Type[ChatModeFactory]]:
    """Register and return the default chat mode factories.
    
    Returns:
        Dictionary mapping mode names to factory classes
    """
    factories = {}
    
    # Register all built-in factories
    factories['two_agent'] = TwoAgentChatFactory
    factories['sequential'] = SequentialChatFactory
    factories['group'] = GroupChatFactory
    factories['nested'] = NestedChatFactory
    factories['swarm'] = SwarmFactory
    
    return factories