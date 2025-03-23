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
        self._tools: Dict[str, Dict[str, Any]] = {}
        self.external_tool_managers: List[Any] = []
    
    def register_tool(self, 
                     tool_class: Type[BaseTool], 
                     prompt: str, 
                     context: Dict[str, Any] = None) -> None:
        """注册工具到管理器
        
        Args:
            tool_class: 工具类
            prompt: 工具提示词
            context: 工具上下文（可选）
        """
        try:
            # 获取工具类的初始化参数
            init_params = {}
            if hasattr(tool_class, '__init__'):
                sig = inspect.signature(tool_class.__init__)
                # 过滤掉self参数
                params = {k: v for k, v in sig.parameters.items() if k != 'self'}
                # 从context中获取匹配的参数
                if context:
                    init_params = {
                        k: context[k] 
                        for k in params.keys() 
                        if k in context
                    }
            
            # 创建工具实例
            try:
                tool_instance = tool_class(**init_params)
            except TypeError as e:
                logger.warning(f"使用参数创建工具实例失败: {str(e)}，尝试无参创建")
                tool_instance = tool_class()
            
            # 设置上下文
            if context:
                for key, value in context.items():
                    try:
                        # 检查是否有setter方法
                        setter = getattr(tool_instance.__class__, key).fset if hasattr(tool_instance.__class__, key) else None
                        if setter is not None:
                            setattr(tool_instance, key, value)
                        elif hasattr(tool_instance, key):
                            # 对于全局属性，即使已经有值也要更新
                            if key in ['read_timestamps', 'normalize_path']:
                                setattr(tool_instance, key, value)
                                logger.debug(f"已更新工具 {tool_instance.name} 的全局属性: {key}")
                            else:
                                setattr(tool_instance, key, value)
                        else:
                            # 对于全局属性，如果不存在则添加
                            if key in ['read_timestamps', 'normalize_path']:
                                setattr(tool_instance, key, value)
                                logger.debug(f"已添加工具 {tool_instance.name} 的全局属性: {key}")
                            else:
                                logger.debug(f"工具 {tool_instance.name} 不支持设置属性: {key}")
                    except AttributeError:
                        # 对于全局属性，如果设置失败则记录警告
                        if key in ['read_timestamps', 'normalize_path']:
                            logger.warning(f"无法为工具 {tool_instance.name} 设置全局属性: {key}")
                        else:
                            logger.debug(f"工具 {tool_instance.name} 不支持设置属性: {key}")
                
            # 只注册到内部工具表
            self._tools[tool_instance.name] = tool_instance
            
            logging.debug(f"成功注册工具: {tool_instance.name}")
            
        except Exception as e:
            logging.error(f"注册工具失败: {str(e)}")
            raise
    
    def register_external_tool_manager(self, tool_manager: Any) -> None:
        """注册外部工具管理器
        
        Args:
            tool_manager: 外部工具管理器实例，必须实现execute_tool方法
        """
        if not hasattr(tool_manager, 'execute_tool'):
            raise ValueError("外部工具管理器必须实现execute_tool方法")
            
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
                "name": tool.name,
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

    def get_tool(self, name: str) -> BaseTool | None:
        """获取工具实例"""
        return self._tools.get(name)