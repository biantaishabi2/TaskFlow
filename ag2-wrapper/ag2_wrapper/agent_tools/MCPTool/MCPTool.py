"""
MCP适配层实现

这个模块负责将MCP服务器的工具转换为AG2 Executor可调用的格式。
提供工具发现、描述获取和执行接口。
"""

import logging
import asyncio
import functools
from typing import Any, Dict, List, Optional, Tuple, Callable

from .client_sdk import MCPClient, MCPError, TransportError

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MCPTool")


class MCPTool:
    """MCP工具适配器
    
    将MCP服务器的工具转换为AG2 Executor可调用的格式。
    """
    
    def __init__(self, client: MCPClient):
        """初始化MCPTool
        
        Args:
            client: MCP客户端实例
        """
        self.client = client
        self._tools_cache: Optional[Dict[str, List[Dict[str, Any]]]] = None
    
    async def get_tools(self) -> List[Dict[str, Any]]:
        """获取所有可用工具列表，转换为AG2格式
        
        Returns:
            AG2格式的工具列表
        """
        if self._tools_cache is None:
            # 获取所有服务器的工具
            server_tools = await self.client.list_all_tools()
            self._tools_cache = server_tools
        else:
            server_tools = self._tools_cache
        
        # 转换为AG2格式
        ag2_tools = []
        
        for server_name, tools in server_tools.items():
            for tool in tools:
                ag2_tool = self._convert_to_ag2_format(server_name, tool)
                ag2_tools.append(ag2_tool)
        
        return ag2_tools
    
    def _convert_to_ag2_format(self, server_name: str, mcp_tool: Dict[str, Any]) -> Dict[str, Any]:
        """将MCP工具转换为AG2格式
        
        Args:
            server_name: 服务器名称
            mcp_tool: MCP工具定义
            
        Returns:
            AG2格式的工具定义
        """
        tool_name = mcp_tool.get("name", "unknown")
        description = mcp_tool.get("description", "")
        
        # 创建AG2格式的工具
        ag2_tool = {
            "name": f"mcp__{server_name}__{tool_name}",
            "description": description,
            "parameters": self._convert_parameters(mcp_tool.get("parameters", {})),
            "execute": functools.partial(
                self._execute_tool, 
                server_name=server_name, 
                tool_name=tool_name
            )
        }
        
        return ag2_tool
    
    def _convert_parameters(self, mcp_params: Dict[str, Any]) -> Dict[str, Any]:
        """将MCP参数转换为AG2参数格式
        
        Args:
            mcp_params: MCP参数定义
            
        Returns:
            AG2格式的参数定义
        """
        # 简单的参数转换，保持原始参数结构
        # 在实际应用中，可能需要更复杂的转换逻辑
        ag2_params = {
            "type": "object",
            "properties": {},
            "required": []
        }
        
        for param_name, param_info in mcp_params.items():
            # 参数信息转换
            param_type = param_info.get("type", "string")
            param_desc = param_info.get("description", "")
            
            ag2_params["properties"][param_name] = {
                "type": param_type,
                "description": param_desc
            }
            
            # 处理必填参数
            if param_info.get("required", False):
                ag2_params["required"].append(param_name)
        
        return ag2_params
    
    async def _execute_tool(self, 
                           parameters: Dict[str, Any], 
                           server_name: str, 
                           tool_name: str) -> Dict[str, Any]:
        """执行MCP工具
        
        Args:
            parameters: 工具参数
            server_name: 服务器名称
            tool_name: 工具名称
            
        Returns:
            工具执行结果
        """
        try:
            result = await self.client.execute_tool(server_name, tool_name, parameters)
            return self._normalize_result(result)
        except (MCPError, TransportError) as e:
            logger.error(f"工具执行失败: {str(e)}")
            return {
                "error": True,
                "message": str(e),
                "content": [{"type": "text", "text": f"工具执行失败: {str(e)}"}]
            }
    
    def _normalize_result(self, mcp_result: Dict[str, Any]) -> Dict[str, Any]:
        """标准化MCP结果格式
        
        Args:
            mcp_result: MCP结果
            
        Returns:
            标准化后的结果
        """
        # 默认结果格式
        normalized = {
            "error": False,
            "content": []
        }
        
        # 检查错误
        if mcp_result.get("isError", False):
            normalized["error"] = True
            normalized["message"] = mcp_result.get("errorMessage", "Unknown error")
        
        # 处理内容
        content_items = mcp_result.get("content", [])
        if isinstance(content_items, list):
            for item in content_items:
                item_type = item.get("type", "text")
                
                if item_type == "text" and "text" in item:
                    normalized["content"].append({
                        "type": "text",
                        "text": item["text"]
                    })
                elif item_type == "image" and "image" in item:
                    normalized["content"].append({
                        "type": "image",
                        "image": item["image"]
                    })
        elif isinstance(content_items, str):
            # 处理字符串内容
            normalized["content"].append({
                "type": "text",
                "text": content_items
            })
        
        # 确保至少有一个内容项
        if not normalized["content"]:
            normalized["content"].append({
                "type": "text",
                "text": "工具返回了空结果"
            })
        
        return normalized
    
    async def register_tools(self, register_func: Callable[[Dict[str, Any]], None]) -> int:
        """将MCP工具注册到AG2 Executor
        
        Args:
            register_func: 工具注册函数
            
        Returns:
            注册的工具数量
        """
        tools = await self.get_tools()
        
        for tool in tools:
            register_func(tool)
        
        return len(tools)
    
    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具调用
        
        Args:
            tool_name: 完整的工具名称 (格式: "mcp__server__tool")
            parameters: 工具参数
            
        Returns:
            工具执行结果
        """
        # 解析工具名称
        parts = tool_name.split("__")
        if len(parts) != 3 or parts[0] != "mcp":
            raise ValueError(f"无效的MCP工具名称: {tool_name}, 格式应为: mcp__server__tool")
        
        server_name = parts[1]
        mcp_tool_name = parts[2]
        
        # 执行工具
        return await self._execute_tool(parameters, server_name, mcp_tool_name)
