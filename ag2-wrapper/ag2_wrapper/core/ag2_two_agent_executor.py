"""
AG2 Two Agent Executor
基于 AG2 Wrapper 的双代理执行器实现
用于适配 TaskExecutor 的任务执行接口
"""

from autogen import AssistantAgent, register_function
from ..chat_modes.llm_driven_agent import LLMDrivenUserProxy
import os
import logging
import asyncio
import concurrent.futures
from typing import Dict, Any, Optional, List, Tuple
from task_planner.core.context_management import TaskContext
from .ag2tools import AG2ToolManager
from .tool_utils import ToolLoader, ToolError
import json
from pathlib import Path
from ..core.config import create_openrouter_config

logger = logging.getLogger(__name__)

# 定义默认系统提示词
DEFAULT_SYSTEM_PROMPT = """你是一个有帮助的AI助手。
使用你的编程和语言技能解决任务。
在以下情况中，为用户提供Python代码（放在python代码块中）或shell脚本（放在sh代码块中）来执行：
    1. 当你需要收集信息时，使用代码输出你需要的信息，例如浏览或搜索网络、下载/读取文件、打印网页或文件内容、获取当前日期/时间、检查操作系统。当打印了足够的信息，并且任务可以基于你的语言能力解决时，你可以自己解决任务。
    2. 当你需要用代码执行某些任务时，使用代码执行任务并输出结果。明智地完成任务。
如果需要，可以一步一步地解决任务。如果没有提供计划，请先解释你的计划。明确说明哪一步使用代码，哪一步使用你的语言能力。
使用代码时，你必须在代码块中指明脚本类型。用户除了执行你建议的代码外，不能提供任何其他反馈或执行任何其他操作。用户不能修改你的代码。因此，不要提供需要用户修改的不完整代码。如果代码不打算由用户执行，请不要使用代码块。
不要在一个回复中包含多个代码块。不要要求用户复制并粘贴结果。相反，在相关情况下使用'print'函数输出结果。检查用户返回的执行结果。
如果结果表明有错误，请修复错误并修改文件。如果错误无法修复，或者即使代码成功执行后任务仍未解决，请分析问题，重新审视你的假设，收集你需要的额外信息，并考虑尝试不同的方法。
当你找到答案时，请仔细验证答案。如果可能，在你的回复中包含可验证的证据。
当一切完成后，在最后回复"TERMINATE"。

## 可用工具列表

{TOOLS_SECTION}
"""

class AG2TwoAgentExecutor:
    """
    基于 AG2 的双代理执行器
    使用 AssistantAgent 和 LLMDrivenUserProxy 来执行任务
    适配 TaskExecutor 的接口规范
    """
    
    # 文件读取时间戳字典,key为文件路径,value为最后读取时间
    read_timestamps: Dict[str, float]
    
    def __init__(self, context_manager=None):
        """初始化
        
        Args:
            context_manager: 上下文管理器实例，用于管理任务上下文
        """
        # 初始化上下文管理器
        self.context_manager = context_manager
        
        # 初始化工具管理器
        self.tool_manager = AG2ToolManager()
        
        # 初始化工具加载器
        self.tool_loader = ToolLoader()
        
        # 使用标准配置格式
        self.llm_config = {
            "config_list": [{
                "model": "anthropic/claude-3.5-sonnet",
                "api_key": os.environ.get("OPENROUTER_API_KEY"),
                "base_url": "https://openrouter.ai/api/v1",
                "api_type": "openai"
            }],
            "temperature": 0.4,
            "timeout": 500
        }
        
        # 使用模块级全局时间戳字典，确保所有工具共享同一个引用
        from ..agent_tools.global_timestamps import GLOBAL_TIMESTAMPS
        self.read_timestamps = GLOBAL_TIMESTAMPS
        
        # 添加路径标准化辅助函数
        self.normalize_path = lambda p: str(Path(p).resolve())
        
        # 初始化工具 - 使用同步方式
        self._initialize_tools_sync()

    def __del__(self):
        """析构函数"""
        pass
        
    def _build_tools_prompt(self, tools_list):
        """构建工具部分的提示词
        
        Args:
            tools_list: 工具列表，每个元素是(工具类, 提示词)对
            
        Returns:
            str: 工具部分提示词
        """
        tools_section = []
        
        for tool_class, prompt in tools_list:
            tool = tool_class()
            
            # 构建参数描述
            params_desc = []
            
            if tool.parameters:
                params_desc.append("**参数**:")
                for param_name, param_info in tool.parameters.items():
                    required = "必需" if param_info.get("required", False) else "可选"
                    param_type = param_info.get("type", "未知")
                    desc = param_info.get("description", "")
                    params_desc.append(f"- {param_name} ({param_type}, {required}): {desc}")
            
            # 组装工具描述
            tool_section = [
                f"### {tool.name}",
                f"{tool.description}",
                "",
            ]
            
            # 添加参数描述
            if params_desc:
                tool_section.extend(params_desc)
                tool_section.append("")
            
            # 添加工具提示词
            tool_section.append(f"{prompt}")
            tool_section.append("---")
                
            tools_section.append("\n".join(tool_section))
        
        return "\n".join(tools_section)

    def _initialize_tools_sync(self):
        """同步初始化工具"""
        try:
            # 只加载通用工具
            tools = self.tool_loader.load_tools_sync(category="common", use_cache=True)
            
            # 构建工具提示词部分
            tools_section = self._build_tools_prompt(tools)
            
            # 构建完整系统提示词
            system_prompt = DEFAULT_SYSTEM_PROMPT.replace("{TOOLS_SECTION}", tools_section)
            
            # 创建助手代理
            self.assistant = AssistantAgent(
                name="任务助手",
                system_message=system_prompt,
                llm_config=self.llm_config
            )
            
            # 创建用户代理
            self.executor = LLMDrivenUserProxy(
                name="用户代理",
                human_input_mode="ALWAYS"
            )
            
            # 注册工具
            for tool_class, prompt in tools:
                try:
                    # 创建工具实例
                    tool_instance = tool_class()
                    
                    # 创建带context的同步工具包装函数
                    executor = self  # 捕获 self 引用
                    def tool_wrapper_sync(params: Dict[str, Any]) -> Dict[str, Any]:
                        try:
                            # 确保 params 中有 kwargs
                            if "kwargs" not in params:
                                params = {"kwargs": params}
                                
                            # 确保 kwargs 中有 context
                            if "context" not in params["kwargs"]:
                                params["kwargs"]["context"] = {}
                                
                            # 重要: 无论LLM传入什么时间戳字典，都直接替换为执行器的引用
                            # 这样可以完全绕过LLM构造参数的问题
                            params["kwargs"]["context"]["read_timestamps"] = executor.read_timestamps
                            
                            # 统一路径处理 - 添加辅助函数供工具使用
                            params["kwargs"]["context"]["normalize_path"] = executor.normalize_path
                            
                            # 确认时间戳字典ID是否一致
                            ts_dict_id = id(params["kwargs"]["context"]["read_timestamps"])
                            if ts_dict_id != id(executor.read_timestamps):
                                logging.error(f"工具 {tool_instance.name} - 时间戳字典ID不一致")
                            
                            # 执行工具
                            result = tool_instance.execute_sync(params)
                            
                            # 处理返回结果
                            if hasattr(result, 'success'):
                                # 如果是 ToolCallResult
                                if result.success:
                                    # 优先使用 result_for_assistant
                                    if hasattr(result, 'result_for_assistant') and result.result_for_assistant is not None:
                                        return {"result": result.result_for_assistant}
                                    
                                    # 检查是否是结论工具
                                    if tool_instance.name == "return_conclusion":
                                        return {
                                            **result.result,
                                            "should_terminate": True
                                        }
                                    return result.result if result.result is not None else {}
                                else:
                                    raise Exception(result.error or "工具执行失败")
                            else:
                                # 如果是直接返回结果
                                return result if result is not None else {}
                                
                        except Exception as e:
                            logging.error(f"工具 {tool_instance.name} 执行失败: {str(e)}")
                            raise
                    
                    # 注册到 AutoGen
                    register_function(
                        tool_wrapper_sync,
                        name=tool_instance.name,
                        description=f"{tool_instance.description}\n\n{prompt}",
                        caller=self.assistant,
                        executor=self.executor
                    )
                    
                    # 注册到工具管理器
                    self.tool_manager.register_tool(
                        tools=[tool_instance],
                        caller=self.assistant,
                        executor=self.executor
                    )
                    
                    logging.debug(f"成功注册工具: {tool_instance.name}")
                    
                except Exception as e:
                    logging.error(f"注册工具 {tool_class.__name__} 失败: {str(e)}")
                    continue
            
            logging.info(f"成功初始化 {len(tools)} 个工具")
            
        except Exception as e:
            logging.error(f"工具初始化失败: {str(e)}")
            raise

    def _safe_get_message_attribute(self, message: Any, attr_name: str, default_value: Any = "") -> Any:
        """安全获取消息的属性或键值
        
        支持从字典、对象或其他类型的消息中获取属性值
        
        Args:
            message: 消息对象或字典
            attr_name: 属性或键名
            default_value: 默认值，当属性不存在时返回
            
        Returns:
            属性值或默认值
        """
        try:
            if isinstance(message, dict):
                return message.get(attr_name, default_value)
            elif hasattr(message, attr_name):
                return getattr(message, attr_name, default_value)
            else:
                return default_value
        except Exception as e:
            logger.warning(f"获取消息属性 {attr_name} 时出错: {str(e)}")
            return default_value

    def _execute_with_timeout(self, prompt: str, task_definition: Dict[str, Any], 
                              task_context: TaskContext, timeout: Optional[int]) -> Dict[str, Any]:
        """同步执行任务，带超时控制"""
        try:
            # 1. 从 TaskContext 获取对话历史并转换为 AG2 格式
            conversation_history = task_context.local_context.get('conversation_history', [])
            recent_history = self._filter_recent_history(conversation_history, 5)
            
            ag2_messages = []
            for msg in recent_history:
                ag2_messages.append({
                    "name": "task_assistant" if msg["role"] == "assistant" else "task_executor",
                    "content": msg["content"]
                })
            
            # 2. 将 read_timestamps 添加到上下文
            task_context.update_local('read_timestamps', self.read_timestamps)
            
            # 3. 直接执行对话，使用concurrent.futures在线程池中执行，添加超时控制
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    self.executor.initiate_chat,
                    self.assistant,
                    message=prompt,
                    chat_history=ag2_messages
                )
                
                # 添加超时控制
                try:
                    chat_result = future.result(timeout=timeout or self.llm_config.get("timeout", 500))
                except concurrent.futures.TimeoutError:
                    logger.error(f"任务执行超时 (timeout={timeout}s)")
                    return {
                        "status": "error",
                        "error_msg": f"任务执行超时 (timeout={timeout}s)",
                        "task_status": "TIMEOUT",
                        "success": False
                    }
            
            # 4. 从上下文中更新 read_timestamps
            updated_timestamps = task_context.local_context.get('read_timestamps', {})
            self.read_timestamps.update(updated_timestamps)
            
            # 5. 如果上下文中有新的read_timestamps，合并到self.read_timestamps
            # 注: 大部分更新应该已经在工具调用时完成，这里是为了确保从上下文获取其他可能的更新
            if 'read_timestamps' in task_context.local_context:
                self.read_timestamps.update(task_context.local_context['read_timestamps'])
            
            # 6. 将新的对话结果转换并追加到历史记录
            new_messages = []
            if hasattr(chat_result, 'chat_history') and chat_result.chat_history:
                for msg in chat_result.chat_history:
                    try:
                        name = self._safe_get_message_attribute(msg, 'name')
                        content = self._safe_get_message_attribute(msg, 'content')
                        timestamp = self._safe_get_message_attribute(msg, 'timestamp', '')
                        
                        new_messages.append({
                            "role": "assistant" if name == "task_assistant" or name == "任务助手" else "user",
                            "content": content,
                            "timestamp": timestamp
                        })
                    except Exception as e:
                        logger.warning(f"处理消息时出错: {str(e)}, 消息类型: {type(msg)}")
                        continue
            
            # 7. 更新回 TaskContext
            task_context.update_local('conversation_history', conversation_history + new_messages)
            
            # 8. 分析对话结果
            task_status = self._analyze_chat_result(chat_result, task_definition)
            final_response = self._extract_final_response(chat_result)
            
            # 9. 根据任务状态返回结果
            logger.info(f"任务状态: {task_status}")
            
            if task_status == "COMPLETED":
                logger.info("根据任务状态标记为成功")
                return {
                    "status": "success",
                    "output": final_response,
                    "task_status": "COMPLETED",
                    "success": True
                }
            else:
                logger.info(f"任务未完成或执行出错，状态: {task_status}")
                return {
                    "status": "error",
                    "output": final_response,
                    "task_status": task_status,
                    "success": False,
                    "error_msg": "任务未完成或执行出错"
                }
            
        except Exception as e:
            logger.error(f"任务执行出错: {str(e)}")
            return {
                "status": "error",
                "error_msg": str(e),
                "task_status": "ERROR",
                "success": False
            }

    def execute(self, 
                prompt: str,
                task_definition: Dict[str, Any],
                task_context: TaskContext,
                timeout: Optional[int] = None,
                max_history_turns: int = 5) -> Dict[str, Any]:
        """
        执行任务 - 纯同步实现
        
        Args:
            prompt: 任务提示
            task_definition: 任务定义
            task_context: 任务上下文
            timeout: 超时时间(秒)
            max_history_turns: 最大历史对话轮数
            
        Returns:
            Dict[str, Any]: 执行结果
        """
        subtask_id = task_definition.get('id', 'unknown')
        logger.info(f"任务 {subtask_id} 开始执行")
        
        try:
            # 直接调用同步方法执行
            result = self._execute_with_timeout(
                prompt=prompt,
                task_definition=task_definition,
                task_context=task_context,
                timeout=timeout
            )
            
            logger.info(f"任务 {subtask_id} 执行完成，结果状态: {result.get('status', 'unknown')}")
            return result
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"任务 {subtask_id} 执行出错: {error_msg}", exc_info=True)
            return {
                "status": "error",
                "error_msg": error_msg,
                "task_status": "ERROR",
                "success": False
            }

    def _filter_recent_history(self, history: list, max_turns: int) -> list:
        """
        筛选最近的对话历史
        
        Args:
            history: 完整的对话历史
            max_turns: 保留的最大对话轮次
            
        Returns:
            筛选后的对话历史
        """
        # 如果历史记录为空，直接返回
        if not history:
            return []
        
        # 计算一轮对话(一问一答)需要的消息数
        messages_per_turn = 2
        max_messages = max_turns * messages_per_turn
        
        # 如果历史消息数量在限制范围内，返回全部
        if len(history) <= max_messages:
            return history
        
        # 否则只返回最近的几轮对话
        return history[-max_messages:]
        
    def _build_message(self, prompt: str, task_definition: Dict[str, Any]) -> str:
        """构建完整的任务消息"""
        # 组合关键信息
        message_parts = [
            prompt,
            "\n## 任务要求",
            f"任务ID: {task_definition.get('id', 'unknown')}",
        ]
        
        # 添加输出文件要求
        if 'output_files' in task_definition:
            message_parts.append("\n## 输出文件要求")
            for output_type, path in task_definition['output_files'].items():
                message_parts.append(f"- {output_type}: {path}")
                
        # 添加成功标准
        if 'success_criteria' in task_definition:
            message_parts.append("\n## 成功标准")
            for criteria in task_definition['success_criteria']:
                message_parts.append(f"- {criteria}")
                
        return "\n".join(message_parts)
        
    def _analyze_chat_result(self, chat_result: Any, task_definition: Dict[str, Any]) -> str:
        """
        分析对话结果,检查任务完成状态
        
        Args:
            chat_result: 对话结果
            task_definition: 任务定义
            
        Returns:
            str: 任务状态 (COMPLETED/ERROR)
        """
        try:
            # 添加详细调试日志
            logger.info("======= 开始分析聊天结果 =======")
            logger.info(f"聊天结果类型: {type(chat_result)}")
            
            chat_history = None
            if hasattr(chat_result, 'chat_history'):
                chat_history = chat_result.chat_history
                logger.info(f"聊天历史类型: {type(chat_history)}")
                logger.info(f"聊天历史长度: {len(chat_history)}")
            elif isinstance(chat_result, dict) and 'chat_history' in chat_result:
                chat_history = chat_result['chat_history']
                logger.info(f"聊天历史类型(字典): {type(chat_history)}")
                logger.info(f"聊天历史长度: {len(chat_history)}")
            else:
                logger.warning("未找到聊天历史")
            
            # 详细记录每条消息
            if chat_history:
                for i, msg in enumerate(chat_history):
                    logger.info(f"消息 #{i+1}:")
                    logger.info(f"类型: {type(msg)}")
                    
                    if isinstance(msg, dict):
                        logger.info(f"键: {list(msg.keys())}")
                        for k, v in msg.items():
                            logger.info(f"  {k}: {v}")
                    else:
                        # 尝试使用常见属性获取信息
                        name = self._safe_get_message_attribute(msg, 'name', 'unknown')
                        content = self._safe_get_message_attribute(msg, 'content', '')
                        role = self._safe_get_message_attribute(msg, 'role', 'unknown')
                        logger.info(f"  name: {name}")
                        logger.info(f"  role: {role}")
                        logger.info(f"  content: {content}")
            
            # 0. 优先检查最后一条消息是否包含exit信号
            if hasattr(chat_result, 'chat_history') and chat_result.chat_history:
                # 获取最后一条消息
                last_msg = chat_result.chat_history[-1]
                content = self._safe_get_message_attribute(last_msg, 'content', '').lower()
                name = self._safe_get_message_attribute(last_msg, 'name', '')
                
                logger.info(f"检查最后一条消息: '{content}' (发送者: {name})")
                
                # 详细记录匹配逻辑
                has_exit = content.endswith('exit') or ' exit' in content or content == 'exit'
                logger.info(f"content.endswith('exit'): {content.endswith('exit')}")
                logger.info(f"' exit' in content: {' exit' in content}")
                logger.info(f"content == 'exit': {content == 'exit'}")
                logger.info(f"最终判断 exit 信号: {has_exit}")
                
                # 检查TERMINATE关键词
                has_terminate = 'terminate' in content.lower()
                logger.info(f"'terminate' in content.lower(): {has_terminate}")
                
                if has_exit:
                    logger.info(f"检测到exit信号，最后消息: '{content}'，标记任务为完成")
                    return "COMPLETED"
                
                if has_terminate:
                    logger.info(f"检测到TERMINATE信号，最后消息: '{content}'，标记任务为完成")
                    return "COMPLETED"
            
            # 1. 检查基本错误
            error = self._safe_get_message_attribute(chat_result, 'error')
                
            if error:
                logger.warning(f"对话结果包含错误: {error}")
                return "ERROR"
            
            # 2. 检查判断结果
            judgment = self._safe_get_message_attribute(chat_result, 'judgment')
            judgment_type = None
                
            # 从judgment中获取类型信息
            if judgment:
                judgment_type = self._safe_get_message_attribute(judgment, 'type')
                    
                if judgment_type == 'TASK_COMPLETED':
                    logger.info("根据判断结果标记任务为完成")
                    return "COMPLETED"
            
            # 3. 检查必要的输出文件是否存在
            if 'output_files' in task_definition:
                missing_files = []
                for output_type, path in task_definition['output_files'].items():
                    if not os.path.exists(path):
                        missing_files.append(path)
                        
                if missing_files:
                    logger.warning(f"缺少输出文件: {missing_files}")
                    return "ERROR"
            
            # 4. 检查对话历史中的最后几条消息
            chat_history = None
            if hasattr(chat_result, 'chat_history'):
                chat_history = chat_result.chat_history
            elif isinstance(chat_result, dict) and 'chat_history' in chat_result:
                chat_history = chat_result['chat_history']
                
            if chat_history:
                # 取最后几条消息
                last_messages = chat_history[-3:]
                for msg in reversed(last_messages):
                    name = self._safe_get_message_attribute(msg, 'name')
                    content = self._safe_get_message_attribute(msg, 'content', '').lower()
                        
                    if name == 'task_assistant' or name == '任务助手':
                        # 检查是否包含完成或失败的关键词
                        if 'task completed' in content or '任务完成' in content or 'completed' in content:
                            logger.info("根据对话内容标记任务为完成")
                            return "COMPLETED"
                        elif 'failed' in content or '失败' in content or 'error' in content:
                            logger.info("根据对话内容标记任务为失败")
                            return "ERROR"
            
            # 5. 如果没有明确的完成标志，返回ERROR
            return "ERROR"
        except Exception as e:
            logger.error(f"分析对话结果时出错: {str(e)}")
            return "ERROR"
        
    def _extract_final_response(self, chat_result: Any) -> str:
        """提取最终响应"""
        try:
            if hasattr(chat_result, 'chat_history') and chat_result.chat_history:
                # 获取最后一条助手消息
                for message in reversed(chat_result.chat_history):
                    name = self._safe_get_message_attribute(message, 'name')
                    if name == 'task_assistant' or name == '任务助手':
                        return self._safe_get_message_attribute(message, 'content')
            elif isinstance(chat_result, dict) and 'chat_history' in chat_result:
                # 字典形式的聊天历史
                for message in reversed(chat_result['chat_history']):
                    name = self._safe_get_message_attribute(message, 'name')
                    if name == 'task_assistant' or name == '任务助手':
                        return self._safe_get_message_attribute(message, 'content')
            
            # 如果找不到特定消息，尝试获取最后一条消息
            if hasattr(chat_result, 'chat_history') and chat_result.chat_history:
                if chat_result.chat_history:
                    last_msg = chat_result.chat_history[-1]
                    return self._safe_get_message_attribute(last_msg, 'content')
                    
            return ""
        except Exception as e:
            logger.error(f"提取最终响应时出错: {str(e)}")
            return ""

    def execute_subtask(self, subtask, task_context=None):
        """
        执行单个子任务
        
        参数:
            subtask (dict): 子任务定义
            task_context (TaskContext, optional): 任务上下文
            
        返回:
            dict: 执行结果
        """
        # 获取任务ID
        subtask_id = subtask.get('id', 'unknown')
        subtask_name = subtask.get('name', subtask_id)
        logger.info(f"开始执行子任务: {subtask_name} (ID: {subtask_id})")
        
        # 如果没有提供任务上下文，尝试获取或创建一个新的
        if task_context is None:
            try:
                if self.context_manager is not None:
                    # 如果上下文不存在，创建一个新的
                    if subtask_id not in self.context_manager.task_contexts:
                        logger.info(f"为子任务 {subtask_id} 创建新的上下文")
                        task_context = self.context_manager.create_subtask_context('root', subtask_id)
                    else:
                        logger.info(f"使用已存在的上下文: {subtask_id}")
                        task_context = self.context_manager.task_contexts[subtask_id]
                else:
                    # 如果没有上下文管理器，创建一个独立的上下文
                    from task_planner.core.context_management import TaskContext
                    logger.info(f"创建独立上下文: {subtask_id} (无上下文管理器)")
                    task_context = TaskContext(subtask_id)
            except Exception as e:
                logger.error(f"创建或获取任务上下文时出错: {str(e)}")
                return {
                    "status": "error",
                    "error_msg": f"上下文初始化失败: {str(e)}",
                    "task_status": "ERROR",
                    "success": False
                }
        
        try:
            # 构建任务提示
            prompt = self._build_message(subtask.get('description', ''), subtask)
            logger.info(f"子任务 {subtask_id} 提示构建完成，长度: {len(prompt)}")
            
            # 执行任务
            logger.info(f"开始执行子任务 {subtask_id} 主体逻辑")
            result = self.execute(
                prompt=prompt,
                task_definition=subtask,
                task_context=task_context,
                timeout=subtask.get('timeout', None)
            )
            
            # 检查结果并记录
            task_status = result.get('task_status', 'UNKNOWN')
            success = result.get('success', False)
            status_str = "成功" if success else "失败"
            logger.info(f"子任务 {subtask_id} 执行完成，状态: {task_status}，结果: {status_str}")
            
            # 清晰的返回格式，确保TaskDecompositionSystem能正确处理
            return {
                "status": "success" if success else "error",
                "output": result.get('output', ''),
                "task_status": task_status,
                "success": success,
                "error_msg": result.get('error_msg', '') if not success else None
            }
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"子任务 {subtask_id} 执行过程中出现异常: {error_msg}", exc_info=True)
            return {
                "status": "error",
                "error_msg": error_msg,
                "task_status": "ERROR",
                "success": False
            }