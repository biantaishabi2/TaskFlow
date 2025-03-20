"""
AG2-Wrapper包

一个AG2/AutoGen框架的封装，简化多Agent对话系统的创建和使用。
"""

__version__ = "0.1.0"

from .core.wrapper import AG2Wrapper
from .core.config import create_openai_config, create_openrouter_config
