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


# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

try:
    import autogen
    from autogen import ConversableAgent # 确保导入了 ConversableAgent
except ImportError:
    raise ImportError(
        "未找到autogen包。请确保已正确安装:\n"
        "$ pip install pyautogen"
    )
from ..agent_tools import LLMResponseAgent, ResponseType

logger = logging.getLogger(__name__)

class LLMDrivenUserProxy(content_tool_call_agent.ContentToolCallAgent):
    """
    LLM驱动的自动用户代理，完全由LLM控制。
    主要功能：
    1. 自动处理工具调用
    2. 生成对话响应
    3. 验证消息结构
    """
    
    def __init__(self, *args, **kwargs):
        """初始化代理"""
        # 设置代码执行配置
        from autogen.coding import LocalCommandLineCodeExecutor
        
        # 创建代码执行器，使用coding_workspace作为工作目录
        executor = LocalCommandLineCodeExecutor(
            timeout=500,
            work_dir="."  # 使用当前目录作为工作目录
        )
        
        # 添加代码执行配置
        kwargs['code_execution_config'] = {
            "executor": executor
        }
        
        # 调用父类初始化
        super().__init__(*args, **kwargs)
        
        # --- 开始修改 V2: 使用 Wrapper 解决 TypeError ---
        def _tool_reply_wrapper(recipient, messages=None, sender=None, config=None):
            """包装函数，以正确的参数调用实例方法。"""
            # 注意：AutoGen 调用 reply_func 时，第一个参数是 recipient (即 self)
            # 所以这里的 recipient 就是 LLMDrivenUserProxy 实例本身
            # 我们需要调用实例上的 generate_tool_calls_reply 方法
            return recipient.generate_tool_calls_reply(messages=messages, sender=sender, config=config)

        # 手动替换原始的工具调用回复函数为我们覆盖的版本
        original_tool_reply_func_name = "generate_tool_calls_reply"
        found_and_replaced = False
        for i, func_dict in enumerate(self._reply_func_list):
            # 检查函数名是否匹配我们要替换的那个
            # 我们只替换同步版本 (generate_tool_calls_reply)，不替换异步版本 (a_generate_tool_calls_reply)
            if hasattr(func_dict['reply_func'], '__name__') and \
               func_dict['reply_func'].__name__ == original_tool_reply_func_name and \
               not inspect.iscoroutinefunction(func_dict['reply_func']): # 确保是同步版本

                # 替换为包装函数
                self._reply_func_list[i]['reply_func'] = _tool_reply_wrapper
                logger.info(f"成功将原始 '{original_tool_reply_func_name}' 替换为 _reply_func_list 中的包装器版本。")
                found_and_replaced = True
                # break # 暂时不 break

        if not found_and_replaced:
            logger.warning(f"无法在 _reply_func_list 中找到原始的 '{original_tool_reply_func_name}' 进行替换。工具调用可能仍会使用原始逻辑。")
        # --- 结束修改 V2 ---

        # 创建默认响应代理
        self.response_agent = LLMResponseAgent()
        
        logger.debug("LLMDrivenUserProxy initialized with %d tools", len(self.function_map))

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
        response = self.response_agent.get_response(chat_history)
        
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

    def generate_tool_calls_reply(
        self,
        messages: Optional[list[dict[str, Any]]] = None,
        sender: Optional["Agent"] = None, # Use "Agent" in quotes for forward reference if needed
        config: Optional[Any] = None,
    ) -> tuple[bool, Optional[dict[str, Any]]]:
        """Generate a reply using tool call.
        OVERRIDE: Correctly handles async tool functions by using run_coroutine_threadsafe.
        """
        if config is None:
            config = self
        if messages is None:
            # Ensure we access messages correctly if sender context matters
            # Get messages from the perspective of the recipient (self)
            messages = self._oai_messages.get(sender) if sender else list(self._oai_messages.values())[0] # Simplistic fallback
            if not messages:
                messages = [] # Ensure it's a list

        if not messages: # Handle case where no messages are found
             logger.warning("generate_tool_calls_reply received no messages after checking sender context.")
             return False, None

        message = messages[-1]
        tool_returns = []

        if not isinstance(message, dict):
            logger.error(f"Last message is not a dictionary: {type(message)}")
            return False, None # Cannot process if message format is wrong

        tool_calls = message.get("tool_calls", [])
        if not isinstance(tool_calls, list):
            logger.error(f"tool_calls is not a list: {type(tool_calls)}")
            return False, None # Cannot process if tool_calls format is wrong

        # --- Loop through tool calls --- 
        for tool_call in tool_calls:
            if not isinstance(tool_call, dict):
                logger.warning(f"Skipping invalid tool_call item (not a dict): {tool_call}")
                continue

            function_call = tool_call.get("function")
            if not isinstance(function_call, dict):
                 logger.warning(f"Skipping invalid function_call (not a dict): {function_call}")
                 continue

            tool_call_id = tool_call.get("id")
            func_name = function_call.get("name")
            if func_name is None:
                logger.warning(f"Skipping tool call with no function name: {function_call}")
                continue

            func = self._function_map.get(func_name, None)
            if func is None:
                 logger.error(f"Function {func_name} not found in function map.")
                 content = f"Error: Function '{func_name}' not registered."
                 is_error = True
            else:
                # --- Execute the function --- 
                try:
                    # ****** Use run_coroutine_threadsafe for async functions ******
                    if inspect.iscoroutinefunction(func):
                        logger.warning(f"Attempting to run async tool '{func_name}' from sync generate_tool_calls_reply via run_coroutine_threadsafe.")
                        try:
                             # Get the running loop. This should exist as we are inside generate_reply -> generate_tool_calls_reply
                             loop = asyncio.get_running_loop() 
                             # We execute a_execute_function, which handles argument parsing and calling the actual tool func
                             future = asyncio.run_coroutine_threadsafe(
                                 self.a_execute_function(function_call, call_id=tool_call_id), loop
                             )
                             # Wait for the result with a timeout
                             _, func_return = future.result(timeout=60) # Adjust timeout as needed
                             logger.info(f"Async tool '{func_name}' execution via threadsafe completed.")
                        except RuntimeError as loop_err:
                             logger.error(f"Could not get running loop for async tool '{func_name}': {loop_err}")
                             func_return = {"content": f"Error: Could not get event loop for '{func_name}'.", "is_error": True}
                        except asyncio.TimeoutError:
                             logger.error(f"Async tool '{func_name}' execution timed out via threadsafe.")
                             func_return = {"content": f"Error: Tool execution for '{func_name}' timed out.", "is_error": True}
                        except Exception as async_exec_err:
                             logger.error(f"Error running async tool '{func_name}' via threadsafe: {async_exec_err}", exc_info=True)
                             func_return = {"content": f"Error executing async tool '{func_name}': {async_exec_err}", "is_error": True}

                    else:
                        # If it's sync, call it directly using execute_function
                        logger.info(f"Executing synchronous tool '{func_name}'...")
                        _, func_return = self.execute_function(function_call, call_id=tool_call_id)
                        logger.info(f"Synchronous tool '{func_name}' execution completed.")

                    # Extract content and error status from func_return dict
                    content = func_return.get("content", "")
                    if content is None: content = "" # Ensure content is a string
                    is_error = func_return.get("is_error", False)

                except Exception as e:
                    content = f"Error during function execution logic for {func_name}: {e}"
                    logger.error(content, exc_info=True)
                    is_error = True

            # --- Format the tool response --- 
            tool_response = {
                "role": "tool",
                "content": str(content), # Ensure content is string
                # "is_error": is_error # Optionally include
            }
            if tool_call_id is not None:
                tool_response["tool_call_id"] = tool_call_id

            tool_returns.append(tool_response)

        # --- Return the final tool message --- 
        if tool_returns:
            combined_content = "\n\n".join([self._str_for_tool_response(tr) for tr in tool_returns])
            return True, {
                "role": "tool",
                "tool_responses": tool_returns,
                "content": combined_content,
            }

        return False, None
