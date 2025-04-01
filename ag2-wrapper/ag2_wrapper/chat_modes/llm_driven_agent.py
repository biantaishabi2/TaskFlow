"""
AG2-Wrapper LLM驱动的自动用户代理模块

这个模块提供了一个完全由LLM驱动的自动用户代理，该代理能够代替人类用户参与对话，
自主处理工具调用并做出决策。
"""

import logging
import sys
from typing import Dict, Any, Optional, List, Callable, Union, Literal
from pathlib import Path
from . import content_tool_call_agent
import inspect
import json
import asyncio
import functools


# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

try:
    import autogen
    from autogen import ConversableAgent, UserProxyAgent, Agent # 确保导入了 ConversableAgent
except ImportError:
    raise ImportError(
        "未找到autogen包。请确保已正确安装:\n"
        "$ pip install pyautogen"
    )
from ..agent_tools import LLMResponseAgent, ResponseType

# Placeholder for the actual default system message
DEFAULT_USER_PROXY_AGENT_SYSTEM_MESSAGE = "You are a helpful assistant." 

logger = logging.getLogger(__name__)

class LLMDrivenUserProxy(content_tool_call_agent.ContentToolCallAgent):
    """
    LLM驱动的自动用户代理，完全由LLM控制。
    主要功能：
    1. 自动处理工具调用
    2. 生成对话响应
    3. 验证消息结构
    """
    
    def __init__(
        self,
        name: str, # Explicitly define common params
        llm_config: Union[Dict, Literal[False]],
        code_execution_config: Union[Dict, Literal[False]] = False,
        system_message: Optional[Union[str, List]] = DEFAULT_USER_PROXY_AGENT_SYSTEM_MESSAGE,
        human_input_mode: str = "NEVER",
        **kwargs, # Keep kwargs for flexibility
    ):
        """初始化代理"""
        # Set up code executor
        from autogen.coding import LocalCommandLineCodeExecutor
        executor = LocalCommandLineCodeExecutor(timeout=500, work_dir=".")
        # Prepare code_execution_config, handling the False case
        effective_code_execution_config = {"executor": executor} if code_execution_config is not False else False

        # Call parent init ONCE
        super().__init__(
            name=name,
            system_message=system_message,
            human_input_mode=human_input_mode,
            code_execution_config=effective_code_execution_config, # Pass the prepared config
            llm_config=llm_config, # Pass llm_config to parent
            **kwargs, # Pass remaining kwargs
        )
        
        # Initialize internal LLMResponseAgent for decision making
        # Use the passed llm_config directly
        self._llm_response_agent = LLMResponseAgent() if llm_config else None
        
        # Commented out redundant response_agent initialization
        # self.response_agent = LLMResponseAgent() 
        
        logger.debug(f"Initializing LLMDrivenUserProxy '{name}'") # Changed log message slightly

        # --- 手动移除继承自父类的 check_termination_and_human_reply ---
        # 查找需要移除的函数
        func_to_remove = ConversableAgent.check_termination_and_human_reply
        # 创建一个新的列表，只包含不需要移除的函数
        new_reply_func_list = []
        removed = False
        for func_tuple in self._reply_func_list:
            if func_tuple.get("reply_func") == func_to_remove:
                removed = True
                logger.debug(f"Removing inherited reply function: {getattr(func_to_remove, '__name__', 'unknown')}")
            else:
                new_reply_func_list.append(func_tuple)
        
        # 替换旧列表
        self._reply_func_list = new_reply_func_list
        if not removed:
             logger.warning("Could not find ConversableAgent.check_termination_and_human_reply in the initial reply function list.")
        # --- 移除结束 ---

        # 不再需要清空列表，因为我们已经手动移除了不需要的项
        # self._reply_func_list = [] # Clear defaults 

        # 1. Async tool call execution (highest priority)
        self.register_reply(Agent, LLMDrivenUserProxy.a_generate_tool_calls_reply, position=1)
        # 2. Sync code execution (less common in AG2 direct use) - Changed from async
        self.register_reply(Agent, LLMDrivenUserProxy.generate_code_execution_reply, position=2) 
        # 3. Async termination/response check (using LLM)
        self.register_reply(Agent, LLMDrivenUserProxy.a_check_termination_and_human_reply, position=3)

        # 4. Fallback termination check if no LLM config (for compatibility)
        if not self._llm_response_agent:
            self.register_reply(Agent, ConversableAgent.check_termination_and_human_reply, position=4)

        # 5. Fallback LLM reply generation (should ideally not be triggered)
        # self.register_reply(Agent, ConversableAgent.generate_llm_reply, position=5)

        logger.debug(f"Registered reply functions for {name}")

        logger.info("使用LLMDrivenUserProxy，自动处理工具调用")

    def get_human_input(self, prompt=""):
        """获取用户输入（由LLM自动判断）"""
        # 收集聊天历史
        chat_history = []
        # self.chat_messages 属性直接返回 self._oai_messages
        for agent_sender_obj, messages in self.chat_messages.items(): # agent_sender_obj 是 Agent 对象
            sender_name = agent_sender_obj.name if hasattr(agent_sender_obj, 'name') else 'unknown_sender'
            for msg in messages[-5:]:  # 获取每个发送者的最近5条消息
                # 完整地复制消息字典中的相关字段
                processed_msg = {
                    # 使用发送者名称，而不是对象
                    "sender_name": sender_name, 
                    # 保留原始 role (如果存在)
                    "role": msg.get("role"),
                    # 保留 content (如果存在)
                    "content": msg.get("content"),
                    # 保留 tool_calls (如果存在且不为 None)
                    "tool_calls": msg.get("tool_calls"),
                    # 保留 function_call (如果存在且不为 None)
                    "function_call": msg.get("function_call"),
                    # 保留 tool_responses (如果存在且不为 None)
                    "tool_responses": msg.get("tool_responses"),
                    # (可选) 保留 name 字段 (某些消息格式可能使用)
                    "name": msg.get("name") 
                }
                # 过滤掉值为 None 的键，保持消息简洁
                filtered_msg = {k: v for k, v in processed_msg.items() if v is not None}
                chat_history.append(filtered_msg)

        # 将这个 *完整* 的 chat_history 传递给 response_agent
        response = self._llm_response_agent.get_response(chat_history)
        
        # 打印响应判断结果
        print(f"\n=== 响应判断结果 ===")
        print(f"类型: {response['type']}")
        print(f"消息: {response['message']}")
        print(f"理由: {response['reasoning']}")
        print("=== 响应判断结束 ===\n")
        
        # 根据响应类型返回不同值
        if response["type"] == ResponseType.TOOL_APPROVED:
            print(f"[判断] 允许执行工具：{response['reasoning']}")
            return ""  # 返回空字符串，允许工具执行
        
        elif response["type"] == ResponseType.TOOL_REJECTED:
            print(f"[判断] 拒绝执行工具：{response['reasoning']}")
            return f"我拒绝执行该操作，原因：{response['reasoning']}"
        
        elif response["type"] == ResponseType.TASK_COMPLETED:
            print(f"[判断] 任务已完成：{response['reasoning']}")
            return "exit"
        
        else:  # TEXT_RESPONSE
            print(f"[判断] 继续对话：{response['reasoning']}")
            return response["message"] or "请继续"

    def validate_tools(self) -> bool:
        """
        验证必要工具是否已正确注册
        """
        try:
            required_tools = ['search_web']  # 可以根据需要添加其他必要工具
            for tool in required_tools:
                if tool not in self.function_map:
                    logger.error("必需的工具'%s'未注册", tool)
                    return False
            return True
        except Exception as e:
            logger.error("验证工具时出错: %s", str(e))
            return False
