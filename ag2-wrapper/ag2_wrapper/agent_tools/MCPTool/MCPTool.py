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
        # 处理可能的列表类型
        if isinstance(mcp_tool, list):
            logger.warning(f"工具定义为列表类型，尝试转换第一个元素: {mcp_tool}")
            if len(mcp_tool) > 0:
                mcp_tool = mcp_tool[0]
            else:
                logger.error("工具定义列表为空")
                mcp_tool = {"name": "unknown", "description": "空工具定义"}
        
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
        """将MCP参数(inputSchema)转换为AG2兼容的JSON Schema参数格式"""
        ag2_params = {
            "type": "object",
            "properties": {},
            "required": []
        }

        if not isinstance(mcp_params, dict):
            logger.warning(f"MCP参数格式无效，预期为字典，实际为: {type(mcp_params)}. 返回空参数定义。")
            # 如果输入不是字典，直接返回默认空结构，避免后续错误
            return ag2_params

        # 遍历MCP参数字典的顶层键（预期为参数名）
        for param_name, param_info in mcp_params.items():
            prop_definition = {} # 用于存储当前参数的JSON Schema定义

            if isinstance(param_info, dict):
                # 如果param_info是字典，从中提取类型、描述等
                prop_definition["type"] = param_info.get("type", "string") # 默认为string类型
                prop_definition["description"] = param_info.get("description", "")

                # 添加其他可能的JSON Schema属性
                if "enum" in param_info:
                    prop_definition["enum"] = param_info["enum"]
                if "default" in param_info:
                    prop_definition["default"] = param_info["default"]
                # 可以根据需要添加更多属性 (e.g., format, pattern, items for array type)

                # 检查参数是否必需
                # 假设必需信息存储在param_info字典的 "required" 键中
                if param_info.get("required", False):
                     # 只有当参数被标记为必需时，才添加到顶层的required列表
                     if param_name not in ag2_params["required"]:
                          ag2_params["required"].append(param_name)

            elif isinstance(param_info, str):
                 # 如果param_info只是一个字符串，将其用作描述，类型默认为string
                 prop_definition["type"] = "string"
                 prop_definition["description"] = param_info
                 logger.warning(f"参数 '{param_name}' 的定义是一个字符串，已将其用作描述。")

            elif isinstance(param_info, list):
                 # 如果是列表，假设是枚举值
                 prop_definition["type"] = "string" # 或者根据列表内容判断类型？默认为string
                 prop_definition["description"] = f"可选值: {', '.join(map(str, param_info))}"
                 prop_definition["enum"] = param_info
                 logger.warning(f"参数 '{param_name}' 的定义是一个列表，已将其视为枚举值。")
            else:
                # 处理其他意外类型
                prop_definition["type"] = "string" # 仍然默认为string
                prop_definition["description"] = f"未知的参数定义类型: {type(param_info).__name__}"
                logger.warning(f"参数 '{param_name}' 的定义类型未知 ({type(param_info).__name__})，已默认处理。")


            # 将处理好的参数定义添加到 'properties' 字典中
            if prop_definition: # 确保我们确实生成了定义
                ag2_params["properties"][param_name] = prop_definition

        # 注意：另一种可能是 'required' 是 mcp_params 顶层的一个列表
        # 例如: mcp_params = {"properties": {...}, "required": ["p1", "p2"]}
        # 如果是这种情况，需要调整逻辑来读取顶层的 required 列表。
        # 但基于当前代码的尝试，我们先假设 required 在每个参数的定义里。

        # 最后，清理 required 列表，确保其中只包含实际存在的属性名
        ag2_params["required"] = [p for p in ag2_params.get("required", []) if p in ag2_params["properties"]]

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
