"""
AG2-Wrapper 聊天模式模块包

这个包提供了各种聊天模式的实现，例如LLM驱动的用户代理、群聊等。
"""

# 移除对不存在模块的导入
# from ag2_wrapper.chat_modes.two_agent import TwoAgentChat

# 修改前：
# from ag2_wrapper.chat_modes.llm_driven_agent import LLMDrivenUserProxy

# 修改为相对导入:
from .llm_driven_agent import LLMDrivenUserProxy

# 可以根据需要添加其他导入
