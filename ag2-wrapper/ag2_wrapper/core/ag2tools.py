"""
AG2Wrapper工具管理模块

这个模块提供工具管理功能，支持注册和使用工具，以及与AG2/AutoGen框架的集成。
"""

import os
import sys
import json
import logging
import inspect
from typing import Dict, Any, List, Optional, Callable, Union, Type
from .base_tool import BaseTool  # 添加基类导入
from autogen import register_function, ConversableAgent
from pathlib import Path

logger = logging.getLogger(__name__)

class AG2ToolManager:
    """
    AG2工具管理器 - 管理和注册可用于AG2/AutoGen框架的工具
    
    主要功能：
    - 工具注册和管理
    - 工具规范生成 (用于AutoGen)
    - 工具执行和结果处理
    - 集成外部工具管理器
    """
    
    def __init__(self):
        """初始化工具管理器"""
        # 内部工具注册表: {工具名称: 工具配置}
        self._tools: dict[str, BaseTool] = {}  # 添加类型注解
        
        # 外部工具管理器列表
        self.external_tool_managers = []
    
    def register_tool(self, 
                     tools: List[BaseTool],
                     caller: ConversableAgent,
                     executor: ConversableAgent):
        """注册工具到AG2
        
        Args:
            tools: 要注册的工具列表
            caller: 调用者代理
            executor: 执行代理
        """
        for tool in tools:
            # 注册到内部工具表
            self._tools[tool.name] = {
                'tool': tool,
                'description': tool.description,
                'parameters': tool.parameters
            }
            
            # 创建工具包装函数
            async def tool_wrapper(**kwargs):
                return await tool.execute(kwargs)
            
            # 注册到 AutoGen，确保传入所有必需参数
            register_function(
                tool_wrapper,
                name=tool.name,  # 工具名称
                caller=caller,   # 调用者代理
                executor=executor,  # 执行代理
                description=tool.description  # 工具描述
            )
    
    def register_external_tool_manager(self, tool_manager) -> None:
        """注册外部工具管理器
        参数要求：
        - 必须实现execute_tool方法
        - 应该实现get_registered_tools方法
        注意：多个工具管理器会按注册顺序尝试执行
        """
        self.external_tool_managers.append(tool_manager)
        logger.debug(f"已注册外部工具管理器: {tool_manager.__class__.__name__}")
    
    async def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具的统一入口
        处理流程：
        1. 优先检查内部工具
        2. 按注册顺序检查外部工具管理器
        3. 标准化返回格式
        错误处理：
        - 记录详细错误日志
        - 返回标准化错误格式
        """
        # 首先尝试内部工具
        if tool_name in self._tools:
            return await self._execute_internal_tool(tool_name, params)
        
        # 然后尝试外部工具管理器
        for manager in self.external_tool_managers:
            try:
                # 调用外部工具管理器
                result = await manager.execute_tool(tool_name, params)
                return self._normalize_external_result(result)
            except Exception as e:
                # 如果这个管理器不能处理，继续尝试下一个
                continue
        
        # 如果都找不到，抛出异常
        raise ValueError(f"工具未找到: {tool_name}")
    
    async def _execute_internal_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行内部注册的工具
        
        Args:
            tool_name: 工具名称
            params: 工具参数
            
        Returns:
            工具执行结果
        """
        tool = self._tools[tool_name]
        function = tool.execute
        
        try:
            # 检查函数是否是异步的
            if inspect.iscoroutinefunction(function):
                result = await function(**params)
            else:
                result = function(**params)
                
            # 标准化结果
            return {
                'success': True,
                'result': result,
                'tool': tool_name
            }
            
        except Exception as e:
            logger.error(f"执行工具{tool_name}失败: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'tool': tool_name
            }
    
    def _normalize_external_result(self, result) -> Dict[str, Any]:
        """
        标准化外部工具结果格式
        
        Args:
            result: 外部工具返回的结果
            
        Returns:
            标准格式的结果字典
        """
        # 如果已经是字典格式，简单验证必需字段
        if isinstance(result, dict):
            if 'success' in result:
                return {
                    'success': result.get('success', False),
                    'result': result.get('result'),
                    'error': result.get('error'),
                    'tool': result.get('tool', 'unknown')
                }
        
        # 如果是外部工具返回的特定类型
        if hasattr(result, 'success') and hasattr(result, 'result'):
            # 可能是ToolCallResult类型
            return {
                'success': getattr(result, 'success', False),
                'result': getattr(result, 'result'),
                'error': getattr(result, 'error', None),
                'tool': getattr(result, 'tool', 'unknown')
            }
        
        # 无法识别的结果，视为成功并返回原始结果
        return {
            'success': True,
            'result': result,
            'tool': 'external'
        }
    
    def get_registered_tools(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有注册的工具信息
        
        Returns:
            工具信息字典
        """
        tools_info = {}
        
        # 添加内部工具
        for name, tool in self._tools.items():
            tools_info[name] = {
                'description': tool.description,
                'parameters': tool.parameters
            }
        
        # 添加外部工具管理器中的工具
        for manager in self.external_tool_managers:
            if hasattr(manager, 'get_registered_tools'):
                external_tools = manager.get_registered_tools()
                for name, info in external_tools.items():
                    # 跳过与内部工具冲突的名称
                    if name not in tools_info:
                        tools_info[name] = {
                            'description': info.get('description', f'External tool {name}'),
                            'parameters': info.get('parameters', {})
                        }
        
        return tools_info
    
    def create_openai_tools_spec(self) -> List[Dict[str, Any]]:
        """创建OpenAI工具规范"""
        return [{
            "type": "function",
            "function": {
                "name": tool.name,  # 使用属性访问而不是字典访问
                "description": tool.description,
                "parameters": {
                    "type": "object",
                    "properties": tool.parameters,
                    "required": [
                        param_name
                        for param_name, param_info in tool.parameters.items()
                        if param_info.get("required", False)
                    ]
                }
            }
        } for tool in self._tools.values()]

    def get_tool(self, name: str) -> BaseTool | None:  # 添加返回类型注解
        return self._tools.get(name)