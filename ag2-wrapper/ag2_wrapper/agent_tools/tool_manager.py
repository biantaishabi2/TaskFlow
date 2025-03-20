"""
工具调用管理系统

职责：
1. 工具注册中心 - 统一管理所有可用工具
2. 执行调度器   - 根据工具名称路由调用请求
3. 异常处理层   - 统一处理工具未找到等异常

架构关系：
Server Bot → ToolManager → [APICallTool, OtherTools...]

设计理念：
┌─────────────┐       ┌─────────────┐
│  Server Bot │       │  ToolManager│
└──────┬──────┘       └──────┬──────┘
       │                     │ manages
       │   execute_tool()    ├───────────────────┐
       └─────────────────────┤                   │
                             │                   ▼
                             │        ┌─────────────────────┐
                             │        │  Registered Tools   │
                             └───────►├─────────────────────┤
                                      │ - APICallTool       │
                                      │ - ShellCommandTool  │
                                      │ - DatabaseQueryTool │
                                      └─────────────────────┘
"""
from typing import Dict, Type, Tuple
from .tools import BaseTool, ToolCallResult
import json
import logging

logger = logging.getLogger(__name__)

class ToolManager:
    def __init__(self):
        # 工具注册表：{工具名称: 工具实例}
        self._tools: Dict[str, BaseTool] = {}
        
    def register_tool(self, name: str, tool: BaseTool):
        """注册工具到管理系统
        Args:
            name: 工具标识符 (e.g. "api_call")
            tool: 实现BaseTool的具体工具实例
        """
        self._tools[name] = tool
        
    async def execute_tool(self, tool_name: str, params: Dict):
        tool = self._tools.get(tool_name)
        if not tool:
            return ToolCallResult(success=False, error="工具未注册")
        
        # 修改后的验证逻辑
        is_valid, error = tool.validate_parameters(params)
        if not is_valid:
            return ToolCallResult(
                success=False,
                error=f"参数验证失败: {error}",  # 携带具体错误描述
                details={
                    "tool": tool_name,
                    "invalid_params": params
                }
            )
        
        return await tool.execute(params) 