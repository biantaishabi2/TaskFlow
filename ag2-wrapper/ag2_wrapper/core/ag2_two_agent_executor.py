"""
AG2 Two Agent Executor
基于 AG2 Wrapper 的双代理执行器实现
用于适配 TaskExecutor 的任务执行接口
"""

from autogen import AssistantAgent
from ..chat_modes.llm_driven_agent import LLMDrivenUserProxy
import os
import logging
import asyncio
import concurrent.futures
from typing import Dict, Any, Optional
from task_planner.core.context_management import TaskContext
from .tools import AG2ToolManager
from ..agent_tools.file_operation_tool import FileOperationTool
import json
from pathlib import Path
from ..core.config import create_openrouter_config

logger = logging.getLogger(__name__)

class AG2TwoAgentExecutor:
    """
    基于 AG2 的双代理执行器
    使用 AssistantAgent 和 LLMDrivenUserProxy 来执行任务
    适配 TaskExecutor 的接口规范
    """
    
    def __init__(self):
        """初始化"""
        # 初始化工具管理器
        self.tool_manager = AG2ToolManager()
        
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
        
        # 创建助手代理
        self.assistant = AssistantAgent(
            name="任务助手",
            llm_config=self.llm_config
        )

        # 创建用户代理
        self.executor = LLMDrivenUserProxy(
            name="用户代理",
            human_input_mode="ALWAYS"
        )
        
        # 注册工具
        self.tool_manager.register_tool(
            caller=self.assistant,
            executor=self.executor
        )
        
    async def _execute_with_timeout(self, prompt: str, task_definition: Dict[str, Any], 
                                  task_context: TaskContext, timeout: Optional[int]) -> Dict[str, Any]:
        """带超时控制的异步执行"""
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
            
            # 2. 使用asyncio.wait_for执行对话
            chat_result = await asyncio.wait_for(
                self.executor.initiate_chat(
                    self.assistant,
                    message=prompt,
                    chat_history=ag2_messages
                ),
                timeout=timeout or self.llm_config.get("timeout", 500)
            )
            
            # 3. 将新的对话结果转换并追加到历史记录
            new_messages = []
            for msg in chat_result.chat_history:
                new_messages.append({
                    "role": "assistant" if msg["name"] == "task_assistant" else "user",
                    "content": msg["content"],
                    "timestamp": msg.get("timestamp", "")
                })
            
            # 4. 更新回 TaskContext
            task_context.update_local('conversation_history', conversation_history + new_messages)
            
            return {
                "status": "success",
                "output": self._extract_final_response(chat_result),
                "task_status": self._analyze_chat_result(chat_result, task_definition)
            }
            
        except asyncio.TimeoutError:
            logger.error(f"任务执行超时 (timeout={timeout}s)")
            return {
                "status": "error",
                "error_msg": f"任务执行超时 (timeout={timeout}s)",
                "task_status": "TIMEOUT"
            }
        except Exception as e:
            logger.error(f"任务执行出错: {str(e)}")
            return {
                "status": "error",
                "error_msg": str(e),
                "task_status": "ERROR"
            }
            
    def execute(self, 
                prompt: str,
                task_definition: Dict[str, Any],
                task_context: TaskContext,
                timeout: Optional[int] = None,
                max_history_turns: int = 5) -> Dict[str, Any]:
        """
        执行任务 - 主要做格式转换和执行对话
        
        Args:
            prompt: 任务提示
            task_definition: 任务定义
            task_context: 任务上下文
            timeout: 超时时间(秒)
            max_history_turns: 最大历史对话轮数
            
        Returns:
            Dict[str, Any]: 执行结果
        """
        # 使用事件循环执行异步任务
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(
            self._execute_with_timeout(
                prompt=prompt,
                task_definition=task_definition,
                task_context=task_context,
                timeout=timeout
            )
        )
        
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
        分析对话结果,只做基础检查
        详细的任务状态分析由 TaskExecutor 负责
        """
        # 只检查基本错误
        if getattr(chat_result, 'error', None):
            return "ERROR"
            
        # 检查必要的输出文件是否存在
        if 'output_files' in task_definition:
            missing_files = []
            for output_type, path in task_definition['output_files'].items():
                if not os.path.exists(path):
                    missing_files.append(path)
                    
            if missing_files:
                logger.warning(f"缺少输出文件: {missing_files}")
                return "ERROR"
                
        # 返回完成状态,让 TaskExecutor 进行更详细的分析
        return "COMPLETED"
        
    def _extract_final_response(self, chat_result: Any) -> str:
        """提取最终响应"""
        if hasattr(chat_result, 'chat_history') and chat_result.chat_history:
            # 获取最后一条助手消息
            for message in reversed(chat_result.chat_history):
                if message.get('name') == 'task_assistant':
                    return message.get('content', '')
                    
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
        
        # 如果没有提供任务上下文，尝试获取或创建一个新的
        if task_context is None:
            if self.context_manager is not None:
                # 如果上下文不存在，创建一个新的
                if subtask_id not in self.context_manager.task_contexts:
                    task_context = self.context_manager.create_subtask_context('root', subtask_id)
                else:
                    task_context = self.context_manager.task_contexts[subtask_id]
            else:
                # 如果没有上下文管理器，创建一个独立的上下文
                from task_planner.core.context_management import TaskContext
                task_context = TaskContext(subtask_id)
            
        # 构建任务提示
        prompt = self._build_message(subtask.get('description', ''), subtask)
        
        # 执行任务
        return self.execute(
            prompt=prompt,
            task_definition=subtask,
            task_context=task_context,
            timeout=subtask.get('timeout', None)
        )