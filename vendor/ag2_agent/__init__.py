"""
AG2-Agent - a flexible orchestration framework for agent interactions
"""

import sys
import os
# Add the current directory to the path so relative imports work
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from vendor.ag2_agent.core.orchestration_manager import OrchestrationManager
from vendor.ag2_agent.factories.factory_registry import register_default_factories

__version__ = "0.1.0"


def create_orchestration_manager(config_path=None):
    """Create and initialize an OrchestrationManager with default factories.
    
    Args:
        config_path: Optional path to a configuration file
        
    Returns:
        An initialized OrchestrationManager
    """
    # Create the manager
    manager = OrchestrationManager(config_path)
    
    # Register all default factories
    factories = register_default_factories()
    for mode_name, factory_class in factories.items():
        manager.register_chat_factory(mode_name, factory_class)
    
    return manager