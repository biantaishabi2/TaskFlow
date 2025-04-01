"""
MCP客户端实现（SDK版本）

纯粹基于MCP SDK的客户端实现，简洁且可靠。
提供服务器连接、工具列表获取和工具执行功能。
"""

import asyncio
import logging
import os
from contextlib import AsyncExitStack
from typing import Dict, List, Optional, Any

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MCPClient_SDK")

# 客户端标识
CLIENT_INFO = {
    "name": "ag2",
    "version": "0.1.0"
}

# 标准异常类，保持与原实现兼容
class MCPError(Exception):
    """MCP错误"""
    pass

class TransportError(Exception):
    """传输错误"""
    pass

class MCPServer:
    """MCP服务器连接
    
    纯SDK实现的服务器连接类，处理与MCP服务器的连接和通信。
    """
    
    def __init__(self, name: str, config: dict):
        """初始化服务器连接
        
        Args:
            name: 服务器名称
            config: 服务器配置，包含类型、命令、参数等
        """
        self.name = name
        self.config = config
        self.session = None
        self._tools_cache = None
        self._exit_stack = AsyncExitStack()
        self._lock = asyncio.Lock()
        self._connected = False
    
    @property
    def transport_type(self) -> str:
        """获取传输类型"""
        return self.config["type"]
    
    async def connect(self) -> None:
        """连接到服务器
        
        使用SDK提供的方法连接到服务器。
        """
        async with self._lock:
            if self._connected and self.session:
                return
            
            logger.info(f"开始连接服务器 {self.name}...")
            
            try:
                # 连接到服务器
                if self.transport_type == "stdio":
                    await self._connect_stdio()
                elif self.transport_type == "sse":
                    await self._connect_sse()
                else:
                    raise ValueError(f"不支持的传输类型: {self.transport_type}")
                
                self._connected = True
                logger.info(f"服务器 {self.name} 连接成功")
            
            except Exception as e:
                logger.error(f"连接服务器 {self.name} 失败: {str(e)}")
                
                # 确保清理资源
                await self._exit_stack.aclose()
                self._exit_stack = AsyncExitStack()
                self.session = None
                self._connected = False
                
                # 重新抛出异常
                raise TransportError(f"连接服务器失败: {str(e)}")
    
    async def _connect_stdio(self) -> None:
        """使用stdio连接服务器
        
        完全基于SDK的stdio连接实现。
        """
        try:
            # 导入SDK组件
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
            
            # 获取配置参数
            command = self.config["command"]
            args = self.config.get("args", [])
            env = {**os.environ, **self.config.get("env", {})} if self.config.get("env") else None
            
            # 创建服务器参数
            server_params = StdioServerParameters(
                command=command,
                args=args,
                env=env
            )
            
            # 使用SDK连接
            logger.info(f"使用SDK stdio_client连接服务器: {self.name}")
            stdio_transport = await self._exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            
            # 创建会话
            read, write = stdio_transport
            self.session = await self._exit_stack.enter_async_context(
                ClientSession(read, write)
            )
            
            # 初始化会话
            await self.session.initialize()
            logger.info(f"SDK stdio连接服务器成功: {self.name}")
        
        except ImportError as e:
            logger.error(f"无法导入SDK模块: {str(e)}")
            raise ImportError(f"使用SDK连接需要安装MCP SDK: {str(e)}")
        
        except Exception as e:
            logger.error(f"stdio连接失败: {str(e)}")
            raise
    
    async def _connect_sse(self) -> None:
        """使用SSE连接服务器
        
        基于SDK的sse_client实现SSE连接。
        """
        try:
            # 导入SDK组件
            from mcp import ClientSession
            from mcp.client.sse import sse_client
            
            # 获取配置参数
            url = self.config.get("url")
            if not url:
                raise ValueError("SSE连接缺少必要的URL参数")
            
            # 设置请求头（可选）
            headers = self.config.get("headers", {})
            
            # 使用SDK的SSE客户端连接
            logger.info(f"使用SDK sse_client连接服务器: {self.name}, URL: {url}")
            
            # 设置超时参数
            timeout = float(self.config.get("timeout", 5.0))  # 连接超时
            sse_read_timeout = float(self.config.get("sse_read_timeout", 300.0))  # SSE读取超时
            
            # 使用SDK连接
            sse_transport = await self._exit_stack.enter_async_context(
                sse_client(url, headers=headers, timeout=timeout, sse_read_timeout=sse_read_timeout)
            )
            
            # 创建会话
            read, write = sse_transport
            self.session = await self._exit_stack.enter_async_context(
                ClientSession(read, write)
            )
            
            # 初始化会话
            await self.session.initialize()
            logger.info(f"SDK SSE连接服务器成功: {self.name}")
            
        except ImportError as e:
            logger.error(f"无法导入SDK SSE模块: {str(e)}")
            raise ImportError(f"使用SDK SSE连接需要安装完整的MCP SDK: {str(e)}")
        
        except Exception as e:
            logger.error(f"SSE连接失败: {str(e)}")
            raise
    
    async def disconnect(self) -> None:
        """断开连接并清理资源
        
        使用SDK标准方式清理资源。
        """
        async with self._lock:
            if not self._connected and not self.session:
                return
            
            logger.info(f"正在断开服务器连接: {self.name}")
            
            # 标记为已断开
            self._connected = False
            
            # 释放会话引用
            self.session = None
            self._tools_cache = None
            
            # 关闭退出栈
            try:
                logger.debug(f"服务器 {self.name}: 尝试优雅关闭 (aclose) 退出栈 (超时 5 秒)，这会等待进程退出...")
                await asyncio.wait_for(self._exit_stack.aclose(), timeout=5.0)
                logger.info(f"服务器 {self.name} 资源已通过 aclose 优雅清理")
            except asyncio.TimeoutError:
                logger.warning(f"服务器 {self.name}: 等待服务器进程退出超时 (5s)。进程可能仍在运行。")
                # ---- 强制终止逻辑 (理想情况，但当前无法实现) ----
                # TODO: 需要获取进程对象 self._process 并调用 kill() 
                # if self._process and self._process.returncode is None:
                #     logger.warning(f"服务器 {self.name}: 强制终止未退出的进程...")
                #     self._process.kill()
                # else:
                #     logger.error(f"服务器 {self.name}: 无法执行强制终止，进程对象不可用或已退出。")
                logger.error(f"服务器 {self.name}: 由于无法获取进程对象，无法执行强制终止。进程可能仍在后台运行。")
            except Exception as e:
                # 捕获 aclose 可能引发的其他错误
                logger.error(f"清理 {self.name} 资源 (aclose) 时发生意外错误: {str(e)}")
            finally:
                # 无论是否超时或出错，都重置 exit_stack
                self._exit_stack = AsyncExitStack() # 创建新的退出栈
                # self._process = None # 如果能获取到进程对象，在这里清理引用
                logger.info(f"服务器 {self.name} 断开连接逻辑完成 (exit_stack 已重置)")
    
    async def call(self, method: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """调用服务器方法
        
        使用SDK会话调用服务器方法。
        
        Args:
            method: 方法名称
            params: 方法参数
            
        Returns:
            方法执行结果
        """
        # 确保已连接
        if not self._connected or not self.session:
            await self.connect()
        
        try:
            if method == "tools/list":
                # 获取工具列表
                logger.info(f"获取服务器 {self.name} 工具列表")
                tools_response = await self.session.list_tools()
                logger.info(f"工具响应类型: {type(tools_response)}")
                
                # 解析工具列表
                tools = []
                
                # 处理不同的响应格式
                if isinstance(tools_response, list):
                    # 处理列表响应
                    for item in tools_response:
                        if isinstance(item, tuple) and len(item) > 1 and item[0] == "tools":
                            for tool in item[1]:
                                tools.append({
                                    "name": tool.name,
                                    "description": getattr(tool, "description", ""),
                                    "parameters": getattr(tool, "inputSchema", {})
                                })
                
                # 用于调试的额外工具属性提取
                if not tools:
                    try:
                        # 检查是否有工具属性
                        tool_objects = getattr(tools_response, "tools", None)
                        if isinstance(tool_objects, list):
                            for tool in tool_objects:
                                tools.append({
                                    "name": tool.name,
                                    "description": getattr(tool, "description", ""),
                                    "parameters": getattr(tool, "inputSchema", {})
                                })
                    except (AttributeError, TypeError):
                        pass
                
                logger.info(f"解析得到 {len(tools)} 个工具")
                return {"tools": tools}
            
            elif method == "tools/execute":
                # 执行工具
                tool_name = params.get("name", "")
                arguments = params.get("arguments", {})
                
                logger.info(f"执行工具 {tool_name} 使用参数: {arguments}")
                logger.info(f"[MCPServer.call]即将调用 await session.call_tool('{tool_name}')...")
                try:
                    result = await self.session.call_tool(tool_name, arguments)
                    logger.info(f"[MCPServer.call] await session.call_tool('{tool_name}') 返回，结果类型: {type(result)}")
                except Exception as call_tool_exc:
                    logger.error(f"[MCPServer.call] await session.call_tool('{tool_name}') 抛出异常: {call_tool_exc}", exc_info=True)
                    raise MCPError(f"call_tool failed: {str(call_tool_exc)}") from call_tool_exc
                
                # 处理结果
                if result is None:
                    return {"content": [{"type": "text", "text": "工具执行结果为空"}]}
                
                if isinstance(result, dict):
                    # 确保一致的返回格式
                    if "content" in result:
                        return result
                    else:
                        # 将字典转为文本内容
                        import json
                        return {"content": [{"type": "text", "text": json.dumps(result)}]}
                else:
                    # 其他类型结果
                    return {"content": [{"type": "text", "text": str(result)}]}
            
            else:
                # 其他通用方法
                logger.info(f"调用方法 {method}")
                try:
                    # 尝试找到SDK方法
                    result = await self.session.call_method(method, params or {})
                    
                    # 处理结果
                    if isinstance(result, dict):
                        return result
                    else:
                        return {"content": [{"type": "text", "text": str(result)}]}
                
                except Exception as e:
                    logger.error(f"调用方法 {method} 失败: {str(e)}")
                    raise MCPError(f"调用方法失败: {str(e)}")
        
        except Exception as e:
            logger.error(f"服务器 {self.name} 调用 {method} 失败: {str(e)}")
            raise MCPError(f"调用失败: {str(e)}")
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """获取工具列表
        
        Returns:
            工具列表
        """
        if self._tools_cache is not None:
            return self._tools_cache
        
        result = await self.call("tools/list")
        tools = result.get("tools", [])
        self._tools_cache = tools
        return tools
    
    # 兼容性别名
    get_tools = list_tools
    
    async def execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具
        
        Args:
            tool_name: 工具名称
            args: 工具参数
            
        Returns:
            工具执行结果
        """
        return await self.call("tools/execute", {
            "name": tool_name,
            "arguments": args
        })


class MCPClient:
    """MCP客户端
    
    管理多个MCP服务器的连接和工具调用。
    支持自动加载配置文件中的服务器。
    """
    
    def __init__(self):
        """初始化客户端"""
        self.servers: Dict[str, MCPServer] = {}
        self._exit_stack = AsyncExitStack()
        self._global_lock = asyncio.Lock()
        self._initialized = False
    
    async def initialize(self) -> None:
        """初始化客户端
        
        加载配置的服务器。
        """
        async with self._global_lock:
            if self._initialized:
                return
            
            # 从配置加载服务器
            from .config import list_servers
            server_configs = list_servers()
            
            for name, config in server_configs.items():
                self.servers[name] = MCPServer(name, config)
            
            self._initialized = True
            logger.info(f"客户端初始化完成，发现 {len(self.servers)} 个服务器")
    
    async def connect_server(self, name: str) -> MCPServer:
        """连接到指定服务器
        
        Args:
            name: 服务器名称
            
        Returns:
            连接的服务器对象
            
        Raises:
            ValueError: 如果找不到服务器
        """
        # 确保客户端已初始化
        if not self._initialized:
            await self.initialize()
        
        # 检查服务器是否存在
        if name not in self.servers:
            # 尝试从配置加载
            from .config import get_server
            config = get_server(name)
            
            if not config:
                raise ValueError(f"未找到服务器配置: {name}")
            
            # 创建服务器对象
            self.servers[name] = MCPServer(name, config)
        
        # 连接服务器
        server = self.servers[name]
        await server.connect()
        return server
    
    async def disconnect_all(self) -> None:
        """断开所有服务器连接
        
        按照SDK示例实现，顺序断开所有连接。
        """
        async with self._global_lock:
            logger.info("开始断开所有服务器连接")
            
            if not self.servers:
                logger.info("没有需要断开的服务器")
                return
            
            # 逐个断开服务器连接
            for name, server in self.servers.items():
                try:
                    logger.info(f"断开服务器: {name}")
                    await server.disconnect()
                    logger.info(f"服务器 {name} 已断开")
                except Exception as e:
                    logger.warning(f"断开服务器 {name} 时出错: {str(e)}")
            
            # 清理服务器字典
            self.servers.clear()
            logger.info("服务器字典已清空")
            
            # 重置退出栈
            await self._exit_stack.aclose()
            self._exit_stack = AsyncExitStack()
            
            # 重置初始化状态
            self._initialized = False
            logger.info("所有资源已清理")
    
    async def list_all_tools(self) -> Dict[str, List[Dict[str, Any]]]:
        """获取所有服务器的工具列表
        
        Returns:
            以服务器名称为键，工具列表为值的字典
        """
        # 确保客户端已初始化
        if not self._initialized:
            await self.initialize()
        
        results = {}
        
        # 逐个获取服务器的工具列表
        for name, server in self.servers.items():
            try:
                logger.info(f"获取服务器 {name} 的工具列表")
                tools = await self._get_server_tools(name, server)
                results[name] = tools
                logger.info(f"获取到服务器 {name} 的 {len(tools)} 个工具")
            except Exception as e:
                logger.error(f"获取服务器 {name} 工具列表失败: {str(e)}")
                results[name] = []
        
        return results
    
    async def _get_server_tools(self, server_name: str, server: MCPServer) -> List[Dict[str, Any]]:
        """获取单个服务器的工具列表
        
        Args:
            server_name: 服务器名称
            server: 服务器对象
            
        Returns:
            工具列表
        """
        try:
            # 确保已连接
            if not server._connected:
                logger.info(f"连接服务器 {server_name} 以获取工具列表")
                await server.connect()
            
            # 获取工具列表
            tools = await server.list_tools()
            return tools
        except Exception as e:
            logger.error(f"获取服务器 {server_name} 工具列表时出错: {str(e)}")
            # 返回空列表
            return []
    
    async def execute_tool(self, server_name: str, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具
        
        Args:
            server_name: 服务器名称
            tool_name: 工具名称
            args: 工具参数
            
        Returns:
            工具执行结果
        """
        # 连接服务器
        server = await self.connect_server(server_name)
        
        # 重试参数
        max_retries = 2
        retry_delay = 1.0
        
        logger.info(f"执行工具 {server_name}/{tool_name}")
        
        # 重试逻辑
        for attempt in range(max_retries):
            try:
                # 执行工具
                result = await server.execute_tool(tool_name, args)
                
                # 记录成功
                if attempt > 0:
                    logger.info(f"工具执行成功 (重试 {attempt}/{max_retries})")
                else:
                    logger.info(f"工具执行成功")
                
                return result
            
            except Exception as e:
                if attempt < max_retries - 1:
                    # 还有重试机会
                    logger.warning(f"工具执行失败，正在重试 ({attempt+1}/{max_retries}): {str(e)}")
                    await asyncio.sleep(retry_delay)
                else:
                    # 达到最大重试次数
                    logger.error(f"工具执行失败，已达到最大重试次数: {str(e)}")
                    
                    # 返回错误消息
                    error_msg = f"执行工具 {server_name}/{tool_name} 失败: {str(e)}"
                    return {
                        "error": True,
                        "message": error_msg,
                        "content": [{"type": "text", "text": error_msg}]
                    }
    
    async def call_method(self, server_name: str, method: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """调用服务器方法
        
        Args:
            server_name: 服务器名称
            method: 方法名称
            params: 方法参数
            
        Returns:
            方法执行结果
        """
        # 连接服务器
        server = await self.connect_server(server_name)
        
        # 调用方法
        return await server.call(method, params)