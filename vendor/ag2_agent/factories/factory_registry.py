from typing import Dict, Type
from vendor.ag2_agent.core.base_interfaces import ChatModeFactory
from vendor.ag2_agent.chat_modes.two_agent_chat import TwoAgentChatFactory
from vendor.ag2_agent.chat_modes.sequential_chat import SequentialChatFactory
from vendor.ag2_agent.chat_modes.group_chat import GroupChatFactory
from vendor.ag2_agent.chat_modes.nested_chat import NestedChatFactory
from vendor.ag2_agent.chat_modes.swarm import SwarmFactory


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