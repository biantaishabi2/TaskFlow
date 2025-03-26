"""
MCP客户端实现

这个模块处理与MCP服务器的连接和通信，支持两种连接方式（SSE/Stdio）。
提供异步接口进行服务器连接和工具调用。
"""

import asyncio
import json
import os
import subprocess
import logging
from typing import Dict, List, Optional, Any, Union
import aiohttp
from abc import ABC, abstractmethod
from contextlib import AsyncExitStack

from .config import get_server, list_servers

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MCPClient")

# 客户端标识
CLIENT_INFO = {
    "name": "ag2",
    "version": "0.1.0"
}

# 连接超时（秒）
CONNECTION_TIMEOUT = 5.0


class TransportError(Exception):
    """传输错误"""
    pass


class MCPError(Exception):
    """MCP错误"""
    pass


class Transport(ABC):
    """传输抽象基类"""
    
    @abstractmethod
    async def connect(self) -> None:
        """连接到服务器"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """断开连接"""
        pass
    
    @abstractmethod
    async def send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """发送请求"""
        pass
    
    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """是否已连接"""
        pass


class SSETransport(Transport):
    """SSE传输实现"""
    
    def __init__(self, url: str):
        self.url = url
        self.session: Optional[aiohttp.ClientSession] = None
        self._connected = False
    
    async def connect(self) -> None:
        """连接到SSE服务器"""
        if self.is_connected:
            return
        
        self.session = aiohttp.ClientSession()
        try:
            # 发送初始化请求
            response = await self.session.post(
                self.url,
                json={
                    "method": "client/info",
                    "params": CLIENT_INFO
                },
                timeout=CONNECTION_TIMEOUT
            )
            response.raise_for_status()
            self._connected = True
            logger.info(f"成功连接到SSE服务器: {self.url}")
        except Exception as e:
            if self.session:
                await self.session.close()
                self.session = None
            raise TransportError(f"连接SSE服务器失败: {str(e)}")
    
    async def disconnect(self) -> None:
        """断开SSE连接"""
        if self.session:
            await self.session.close()
            self.session = None
            self._connected = False
            logger.info(f"已断开SSE服务器连接: {self.url}")
    
    async def send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """通过SSE发送请求"""
        if not self.is_connected or not self.session:
            raise TransportError("SSE未连接")
        
        request_data = {
            "method": method,
            "params": params or {}
        }
        
        try:
            response = await self.session.post(
                self.url,
                json=request_data,
                timeout=CONNECTION_TIMEOUT * 2  # 请求超时更长
            )
            response.raise_for_status()
            result = await response.json()
            
            if "error" in result:
                raise MCPError(f"MCP错误: {result['error'].get('message', 'Unknown error')}")
            
            return result.get("result")
        except MCPError:
            raise
        except Exception as e:
            raise TransportError(f"SSE请求失败: {str(e)}")
    
    @property
    def is_connected(self) -> bool:
        """是否已连接到SSE服务器"""
        return self._connected and self.session is not None


class StdioTransport(Transport):
    """Stdio传输实现
    
    遵循MCP SDK示例的最佳实践，实现可靠的资源管理。
    使用AsyncExitStack确保所有资源正确清理。
    """
    
    def __init__(self, command: str, args: Optional[List[str]] = None, env: Optional[Dict[str, str]] = None):
        self.command = command
        self.args = args or []
        self.env = env or {}
        self.process: Optional[subprocess.Popen] = None
        self._connected = False
        self._cleanup_lock = asyncio.Lock()  # 添加锁以确保清理操作的线程安全
        self._exit_stack = AsyncExitStack()  # 用于管理资源
    
    async def connect(self) -> None:
        """启动子进程连接
        
        使用AsyncExitStack管理资源生命周期，确保所有资源都能正确清理。
        """
        if self.is_connected:
            return
            
        async with self._cleanup_lock:
            # 确保之前的资源已清理
            if self.process is not None:
                await self._safe_cleanup()
                
            # 创建新的退出栈
            self._exit_stack = AsyncExitStack()
            
            # 合并环境变量
            full_env = {**os.environ, **self.env}
            
            try:
                # 构建命令行
                cmd_line = [self.command] + self.args
                logger.info(f"启动进程: {' '.join(cmd_line)}")
                
                # 启动子进程
                self.process = subprocess.Popen(
                    cmd_line,
                    env=full_env,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1  # 行缓冲
                )
                
                # 注册进程清理回调
                self._exit_stack.push_async_callback(self._clean_process_async)
                
                logger.info(f"进程已启动，PID: {self.process.pid}")
                
                # 检查进程是否正常启动
                if self.process.poll() is not None:
                    exit_code = self.process.returncode
                    stderr_output = self.process.stderr.read() if self.process.stderr else ""
                    raise TransportError(f"进程启动后立即终止，退出码: {exit_code}，错误输出: {stderr_output}")
                
                # 验证stdin/stdout可用
                if not self.process.stdin or not self.process.stdout:
                    raise TransportError("进程标准输入输出未正确初始化")
                
                # 发送初始化请求
                init_request = {
                    "method": "client/info",
                    "params": CLIENT_INFO
                }
                
                self.process.stdin.write(json.dumps(init_request) + "\n")
                self.process.stdin.flush()
                
                logger.debug("已发送初始化请求，等待响应")
                
                # 等待响应
                response_line = self.process.stdout.readline().strip()
                if not response_line:
                    stderr_output = self.process.stderr.read() if self.process.stderr else ""
                    raise TransportError(f"Stdio进程无响应，错误输出: {stderr_output}")
                
                # 解析响应
                try:
                    response = json.loads(response_line)
                except json.JSONDecodeError as e:
                    raise TransportError(f"无效的JSON响应: {response_line}, 错误: {str(e)}")
                    
                if "error" in response:
                    raise MCPError(f"MCP初始化错误: {response['error'].get('message', 'Unknown error')}")
                
                # 连接成功
                self._connected = True
                logger.info(f"成功连接到Stdio进程: {self.command} (PID: {self.process.pid})")
                
            except Exception as e:
                logger.error(f"连接失败: {str(e)}")
                
                # 确保清理资源
                await self._exit_stack.aclose()
                self._exit_stack = AsyncExitStack()
                self.process = None
                self._connected = False
                
                raise TransportError(f"连接Stdio进程失败: {str(e)}")
    
    async def _clean_process_async(self, *args):
        """异步清理进程资源
        
        此方法专为AsyncExitStack的push_async_callback设计，
        遵循SDK示例的最佳实践进行资源清理。
        """
        if not self.process:
            return
            
        proc_info = f"{self.command} (PID: {self.process.pid if self.process else 'None'})"
        logger.info(f"异步清理进程资源: {proc_info}")
        
        # 创建一个后台任务来处理进程清理
        loop = asyncio.get_running_loop()
        try:
            # 使用run_in_executor在后台线程中执行同步清理
            await loop.run_in_executor(None, self._clean_process_sync)
        except Exception as e:
            logger.error(f"清理进程时出错: {str(e)}")
        finally:
            # 确保清理完成，即使有异常
            self._connected = False
            self.process = None
            logger.info(f"进程异步清理完成: {proc_info}")
    
    def _clean_process_sync(self):
        """同步清理进程资源 (在线程池执行)
        
        使用更安全的方式终止进程：
        1. 尝试发送EOF到stdin
        2. 终止进程并等待
        3. 必要时强制终止
        4. 关闭所有管道
        """
        if not self.process:
            return
            
        proc_info = f"{self.command} (PID: {self.process.pid})"
        logger.info(f"开始同步清理进程: {proc_info}")
        
        # 1. 首先尝试关闭stdin发送EOF信号
        try:
            if self.process.stdin and not self.process.stdin.closed:
                logger.info(f"关闭stdin: {proc_info}")
                self.process.stdin.close()
        except Exception as e:
            logger.warning(f"关闭stdin出错: {str(e)}")
        
        # 2. 检查进程是否仍在运行
        if self.process.poll() is None:
            try:
                # 先尝试正常终止
                logger.info(f"发送TERM信号: {proc_info}")
                self.process.terminate()
                
                try:
                    # 等待最多3秒让进程自行退出
                    exit_code = self.process.wait(timeout=3.0)
                    logger.info(f"进程已正常终止，退出码: {exit_code}")
                except subprocess.TimeoutExpired:
                    # 强制终止
                    logger.warning(f"进程未响应，发送KILL信号: {proc_info}")
                    self.process.kill()
                    
                    try:
                        exit_code = self.process.wait(timeout=2.0)
                        logger.info(f"进程已强制终止，退出码: {exit_code}")
                    except subprocess.TimeoutExpired:
                        logger.error(f"无法终止进程: {proc_info}")
            except Exception as e:
                logger.warning(f"终止进程出错: {str(e)}")
        else:
            logger.info(f"进程已终止，退出码: {self.process.returncode}")
        
        # 3. 关闭其他管道
        for name, pipe in [("stdout", self.process.stdout), ("stderr", self.process.stderr)]:
            try:
                if pipe and not pipe.closed:
                    logger.info(f"关闭{name}: {proc_info}")
                    pipe.close()
            except Exception as e:
                logger.warning(f"关闭{name}时出错: {str(e)}")
        
        logger.info(f"进程同步清理完成: {proc_info}")
    
    async def disconnect(self) -> None:
        """终止子进程并清理资源
        
        使用AsyncExitStack的aclose方法清理所有资源，
        确保即使在异常情况下也能正确清理。
        """
        async with self._cleanup_lock:
            if not self._connected and not self.process:
                return
                
            proc_info = f"{self.command} (PID: {self.process.pid if self.process else 'None'})"
            logger.info(f"断开Stdio进程连接: {proc_info}")
            
            try:
                # 使用exit_stack的aclose方法，这会触发之前注册的所有回调
                await self._exit_stack.aclose()
            except Exception as e:
                logger.error(f"关闭退出栈出错: {str(e)}")
            finally:
                # 重置状态
                self._exit_stack = AsyncExitStack()
                self._connected = False
                self.process = None
                logger.info(f"Stdio进程连接已断开: {proc_info}")
    
    async def send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """通过Stdio发送请求"""
        if not self.is_connected or not self.process:
            raise TransportError("Stdio未连接")
        
        request_data = {
            "method": method,
            "params": params or {}
        }
        
        try:
            # 发送请求
            if not self.process.stdin or self.process.stdin.closed:
                raise TransportError("进程stdin已关闭或不可用")
                
            self.process.stdin.write(json.dumps(request_data) + "\n")
            self.process.stdin.flush()
            
            # 检查进程是否已终止
            if self.process.poll() is not None:
                exit_code = self.process.returncode
                raise TransportError(f"进程已终止，退出码: {exit_code}")
            
            # 读取响应
            if not self.process.stdout or self.process.stdout.closed:
                raise TransportError("进程stdout已关闭或不可用")
                
            response_line = self.process.stdout.readline().strip()
            if not response_line:
                stderr = self.process.stderr.read() if self.process.stderr and not self.process.stderr.closed else ""
                raise TransportError(f"Stdio进程无响应，错误输出: {stderr}")
            
            try:
                response = json.loads(response_line)
            except json.JSONDecodeError:
                raise TransportError(f"无效的JSON响应: {response_line}")
            
            if "error" in response:
                raise MCPError(f"MCP错误: {response['error'].get('message', 'Unknown error')}")
            
            return response.get("result")
        except MCPError:
            raise
        except Exception as e:
            # 如果连接已断开，尝试重新清理进程以确保资源释放
            if self.process and self.process.poll() is not None:
                logger.warning(f"发送请求时检测到进程已终止，清理资源")
                await self._safe_cleanup()
            raise TransportError(f"Stdio请求失败: {str(e)}")
    
    @property
    def is_connected(self) -> bool:
        """是否已连接Stdio进程"""
        return (self._connected and 
                self.process is not None and 
                self.process.poll() is None and
                hasattr(self.process, 'stdin') and self.process.stdin and not self.process.stdin.closed and
                hasattr(self.process, 'stdout') and self.process.stdout and not self.process.stdout.closed)
        
    def __del__(self):
        """析构函数确保进程被清理，即使没有正确调用disconnect方法"""
        if hasattr(self, 'process') and self.process:
            logger.warning(f"在析构函数中清理进程: {self.command} (PID: {self.process.pid if self.process else 'None'})")
            try:
                self._clean_process()
            except Exception as e:
                # 在析构函数中不能引发异常
                logger.error(f"在析构函数中清理进程时出错: {str(e)}")
                pass


class MCPServer:
    """MCP服务器包装类
    
    改进版本使用MCP SDK的标准方法实现服务器连接和会话管理。
    使用AsyncExitStack确保资源正确释放。
    实现可靠的连接和断开逻辑，确保资源安全清理。
    """
    
    def __init__(self, name: str, config: dict):
        """初始化MCP服务器连接
        
        Args:
            name: 服务器名称
            config: 服务器配置
        """
        self.name = name
        self.config = config
        self._transport: Optional[Transport] = None
        self._tools_cache: Optional[List[Dict[str, Any]]] = None
        self._exit_stack = AsyncExitStack()  # 资源管理
        self._session: Optional[Any] = None  # ClientSession类型
        self._lock = asyncio.Lock()
        self._connected = False
        
    async def call(self, method: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """调用服务器方法
        
        遵循simple-chatbot示例实现方式，直接使用SDK的session接口。
        
        Args:
            method: 方法名称
            params: 方法参数
            
        Returns:
            方法调用结果
        """
        # 确保已连接
        if not self._connected:
            await self.connect()
        
        # 确认会话可用
        if not self._session and not self._transport:
            raise RuntimeError(f"服务器 {self.name} 未初始化")
        
        try:
            if method == "tools/list":
                # 获取工具列表
                if self._session:
                    # 使用SDK会话方式
                    logger.info(f"使用SDK获取工具列表: {self.name}")
                    try:
                        tools_response = await self._session.list_tools()
                        # 日志记录工具响应类型，辅助调试
                        logger.info(f"工具响应类型: {type(tools_response)}")
                        tools = []
                        
                        # 处理各种可能的工具响应格式
                        if hasattr(tools_response, 'tools'):
                            # 直接属性
                            for tool in tools_response.tools:
                                tools.append({
                                    "name": tool.name,
                                    "description": tool.description,
                                    "parameters": getattr(tool, "inputSchema", {})
                                })
                                
                        elif isinstance(tools_response, list):
                            # 列表格式
                            for item in tools_response:
                                if isinstance(item, tuple) and len(item) > 1 and item[0] == "tools":
                                    for tool in item[1]:
                                        tools.append({
                                            "name": tool.name,
                                            "description": tool.description,
                                            "parameters": getattr(tool, "inputSchema", {})
                                        })
                        
                        # 特殊处理：直接提取SDK对象内容
                        if not tools and hasattr(tools_response, '__dict__'):
                            logger.info(f"使用SDK对象提取: {tools_response.__dict__}")
                            # 尝试提取可能的工具列表
                            for key, value in tools_response.__dict__.items():
                                if isinstance(value, list) and value and hasattr(value[0], 'name'):
                                    for tool in value:
                                        tools.append({
                                            "name": tool.name,
                                            "description": getattr(tool, "description", ""),
                                            "parameters": getattr(tool, "inputSchema", {})
                                        })
                        
                        logger.info(f"解析得到 {len(tools)} 个工具")
                    except Exception as e:
                        logger.error(f"解析工具列表出错: {str(e)}")
                        tools = []
                else:
                    # 使用自定义传输方式
                    result = await self._transport.send_request(method, params)
                    if not result:
                        return {"tools": []}
                    tools = result.get("tools", [])
                
                return {"tools": tools}
                
            elif method == "tools/execute":
                # 执行工具调用
                tool_name = params.get("name", "")
                arguments = params.get("arguments", {})
                
                logger.info(f"执行工具 {tool_name} 使用参数: {arguments}")
                
                if self._session:
                    # 使用SDK执行工具
                    result = await self._session.call_tool(tool_name, arguments)
                else:
                    # 使用自定义实现
                    result = await self._transport.send_request(method, params)
                
                # 格式化结果
                if result is None:
                    return {"content": [{"type": "text", "text": "工具执行结果为空"}]}
                
                if isinstance(result, dict):
                    # 确保一致的返回格式
                    if "content" in result:
                        return result
                    else:
                        # 将字典转为文本内容返回
                        return {"content": [{"type": "text", "text": json.dumps(result)}]}
                else:
                    # 其他类型直接转字符串
                    return {"content": [{"type": "text", "text": str(result)}]}
            else:
                # 其他方法根据可用会话方式处理
                logger.info(f"调用方法: {method}")
                
                if self._session and hasattr(self._session, 'call_method'):
                    # 使用SDK通用调用
                    result = await self._session.call_method(method, params or {})
                elif self._transport:
                    # 使用自定义传输
                    result = await self._transport.send_request(method, params)
                else:
                    raise NotImplementedError(f"无法处理方法: {method}")
                
                # 格式化结果
                if isinstance(result, dict):
                    return result
                else:
                    return {"content": [{"type": "text", "text": str(result)}]}
                    
        except Exception as e:
            logger.error(f"服务器 {self.name} 调用方法 {method} 失败: {str(e)}")
            # 重新包装异常
            raise MCPError(f"调用失败 {method}: {str(e)}")
    
    # 为保持兼容性，添加旧名称的方法
    async def list_tools(self) -> List[Dict[str, Any]]:
        """获取工具列表"""
        if self._tools_cache is not None:
            return self._tools_cache
        
        result = await self.call("tools/list")
        tools = result.get("tools", [])
        self._tools_cache = tools
        return tools
        
    # 为兼容性添加旧方法名作为别名
    get_tools = list_tools
    
    async def execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具调用"""
        return await self.call("tools/execute", {
            "name": tool_name,
            "arguments": args
        })
    
    @property
    def transport_type(self) -> str:
        """获取传输类型"""
        return self.config["type"]
    
    def create_transport(self) -> Transport:
        """创建传输实例，自定义实现
        
        对于标准SDK连接使用标准方法，仅在SDK不可用时使用此方法。
        """
        if self.transport_type == "sse":
            return SSETransport(self.config["url"])
        elif self.transport_type == "stdio":
            return StdioTransport(
                command=self.config["command"],
                args=self.config.get("args"),
                env=self.config.get("env")
            )
        else:
            raise ValueError(f"不支持的传输类型: {self.transport_type}")
    
    async def connect(self) -> None:
        """连接到服务器
        
        使用AsyncExitStack管理资源，确保正确清理。
        使用SDK标准方式连接，完全遵循SDK示例实现。
        """
        async with self._lock:
            # 如果已连接则直接返回
            if self._connected and self._session:
                return
            
            # 先断开之前的连接，确保资源被清理
            if self._session or self._transport:
                try:
                    await self._exit_stack.aclose()
                    self._exit_stack = AsyncExitStack()
                    self._session = None
                    self._transport = None
                    self._connected = False
                except Exception as e:
                    logger.warning(f"清理之前的连接资源时出错 {self.name}: {str(e)}")
            
            logger.info(f"开始连接服务器 {self.name}...")
            
            try:
                # 使用SDK方式连接
                if self.transport_type == "stdio":
                    await self._connect_with_sdk()
                elif self.transport_type == "sse":
                    # 暂不支持SSE连接，但使用自定义的SSE实现
                    logger.info(f"使用SSE连接服务器 {self.name}...")
                    self._transport = SSETransport(self.config["url"])
                    
                    # 将传输添加到退出栈以便自动清理
                    await self._exit_stack.enter_async_context(
                        _TransportContextManager(self._transport)
                    )
                    
                    # 连接传输
                    await self._transport.connect()
                    self._connected = True
                    logger.info(f"SSE连接服务器成功: {self.name}")
                else:
                    raise ValueError(f"不支持的传输类型: {self.transport_type}")
            
            except Exception as e:
                logger.error(f"连接服务器 {self.name} 失败: {str(e)}")
                
                # 确保资源清理
                try:
                    await self._exit_stack.aclose()
                    self._exit_stack = AsyncExitStack()
                except Exception as cleanup_error:
                    logger.error(f"清理连接资源时出错: {cleanup_error}")
                
                self._session = None
                self._transport = None
                self._connected = False
                
                # 重新抛出异常
                raise
                
    async def _connect_with_sdk(self):
        """使用SDK连接服务器
        
        使用MCP Python SDK的正式API，遵循示例实现方式。
        """
        try:
            # 导入SDK所需模块
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
            
            # 获取命令路径
            command = self.config["command"]
            args = self.config.get("args", [])
            env = {**os.environ, **self.config.get("env", {})} if self.config.get("env") else None
            
            # 创建服务器参数
            server_params = StdioServerParameters(
                command=command,
                args=args,
                env=env
            )
            
            # 使用SDK创建连接
            logger.info(f"使用SDK stdio_client连接服务器: {self.name}")
            stdio_transport = await self._exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            
            # 创建会话
            read, write = stdio_transport
            session = await self._exit_stack.enter_async_context(
                ClientSession(read, write)
            )
            
            # 初始化会话
            await session.initialize()
            self._session = session
            self._connected = True
            logger.info(f"SDK连接服务器成功: {self.name}")
            
        except ImportError as e:
            logger.error(f"无法导入SDK模块: {str(e)}")
            raise ImportError(f"使用SDK连接需要安装MCP SDK: {str(e)}")
        except Exception as e:
            logger.error(f"SDK连接失败: {str(e)}")
            raise
        
    async def disconnect(self) -> None:
        """断开连接并清理资源
        
        完全遵循SDK实现方式，简单直接地调用exit_stack.aclose()。
        """
        async with self._lock:
            if not self._connected and not self._session and not self._transport:
                return
                
            logger.info(f"正在断开服务器连接: {self.name}")
            
            # 标记为已断开
            self._connected = False
            
            # 释放引用，避免循环引用
            self._session = None
            self._transport = None
            self._tools_cache = None
            
            # 直接关闭exit_stack，不使用额外的包装或超时
            try:
                await self._exit_stack.aclose()
                logger.info(f"服务器 {self.name} 资源已清理")
            except Exception as e:
                logger.error(f"清理 {self.name} 资源出错: {str(e)}")
            
            # 创建新的exit_stack供下次使用
            self._exit_stack = AsyncExitStack()
            logger.info(f"服务器 {self.name} 断开连接完成")
    
class _TransportContextManager:
    """用于将Transport对象与AsyncExitStack一起使用的上下文管理器封装类"""
    
    def __init__(self, transport: Transport):
        self.transport = transport
    
    async def __aenter__(self):
        return self.transport
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.transport:
            try:
                await self.transport.disconnect()
            except Exception as e:
                logger.error(f"断开传输连接时出错: {str(e)}")
                # 不重新抛出异常，确保清理继续进行


class MCPClient:
    """MCP客户端管理类
    
    管理多个MCP服务器的连接和工具调用。
    支持自动加载配置文件中的服务器定义。
    提供统一的接口进行工具调用。
    """
    
    def __init__(self):
        """初始化MCP客户端"""
        self.servers: Dict[str, MCPServer] = {}
        self._connection_timeout = CONNECTION_TIMEOUT
        self._exit_stack = AsyncExitStack()
        self._global_lock = asyncio.Lock()
        self._initialized = False
    
    async def initialize(self) -> None:
        """初始化客户端（懒加载初始化）"""
        async with self._global_lock:
            if self._initialized:
                return
            
            # 加载配置的服务器
            server_configs = list_servers()
            for name, config in server_configs.items():
                self.servers[name] = MCPServer(name, config)
            
            self._initialized = True
            logger.info(f"MCP客户端初始化完成，发现 {len(self.servers)} 个服务器")
    
    async def load_servers(self) -> None:
        """加载所有配置的服务器"""
        async with self._global_lock:
            # 清除现有服务器
            disconnect_tasks = []
            for server in self.servers.values():
                disconnect_tasks.append(asyncio.create_task(server.disconnect()))
            
            # 等待所有断开连接任务完成
            if disconnect_tasks:
                await asyncio.gather(*disconnect_tasks, return_exceptions=True)
            
            self.servers.clear()
            
            # 加载配置的服务器
            server_configs = list_servers()
            for name, config in server_configs.items():
                self.servers[name] = MCPServer(name, config)
            
            logger.info(f"重新加载服务器完成，发现 {len(self.servers)} 个服务器")
    
    async def connect_server(self, name: str) -> MCPServer:
        """连接到指定服务器
        
        Args:
            name: 服务器名称
            
        Returns:
            已连接的服务器对象
            
        Raises:
            ValueError: 如果找不到服务器配置
            各种连接异常
        """
        # 确保客户端已初始化
        if not self._initialized:
            await self.initialize()
        
        if name not in self.servers:
            # 尝试从配置加载服务器
            config = get_server(name)
            if not config:
                raise ValueError(f"未找到服务器配置: {name}")
            self.servers[name] = MCPServer(name, config)
        
        server = self.servers[name]
        await server.connect()
        return server
    
    async def connect_all(self) -> List[MCPServer]:
        """连接所有服务器
        
        Returns:
            成功连接的服务器列表
        """
        # 确保客户端已初始化
        if not self._initialized:
            await self.initialize()
        
        # 使用任务并行连接所有服务器
        connect_tasks = {}
        connected_servers = []
        
        for name, server in self.servers.items():
            task = asyncio.create_task(server.connect())
            connect_tasks[name] = task
        
        # 等待所有连接任务完成
        for name, task in connect_tasks.items():
            try:
                await task
                connected_servers.append(self.servers[name])
                logger.info(f"服务器 {name} 连接成功")
            except Exception as e:
                logger.error(f"连接服务器失败 {name}: {str(e)}")
        
        return connected_servers
    
    async def disconnect_all(self) -> None:
        """断开所有服务器连接，并清理资源
        
        完全按照SDK示例中的ChatSession.cleanup_servers实现：
        顺序关闭服务器，避免并行执行带来的竞态问题。
        """
        async with self._global_lock:
            logger.info("开始断开所有服务器连接")
            
            if not self.servers:
                logger.info("没有需要断开的服务器")
                return
            
            # 按照SDK示例，顺序断开每个服务器，而非并行
            for name, server in self.servers.items():
                try:
                    logger.info(f"断开服务器: {name}")
                    await server.disconnect()
                    logger.info(f"服务器 {name} 已断开")
                except Exception as e:
                    # 记录错误但继续断开其他服务器
                    logger.warning(f"断开服务器 {name} 时出错: {str(e)}")
            
            # 清理服务器字典
            self.servers.clear()
            logger.info("服务器字典已清空")
            
            # 重置退出栈 - 直接调用，不使用额外的包装
            await self._exit_stack.aclose()
            self._exit_stack = AsyncExitStack()
            
            # 重置初始化状态
            self._initialized = False
            logger.info("所有资源已清理")
    
    
    async def list_all_tools(self) -> Dict[str, List[Dict[str, Any]]]:
        """获取所有服务器的工具列表
        
        使用并行任务方式获取所有服务器的工具，遵循SDK样例实现。
        
        Returns:
            以服务器名称为键，工具列表为值的字典
        """
        # 确保客户端已初始化
        if not self._initialized:
            await self.initialize()
        
        # 使用任务并行获取所有服务器的工具列表
        tool_tasks = {}
        results = {}
        
        for name, server in self.servers.items():
            logger.info(f"创建获取服务器 {name} 工具列表的任务")
            # 直接创建任务，确保每个任务独立执行
            tool_tasks[name] = asyncio.create_task(self._get_server_tools(name, server))
        
        # 等待所有获取工具列表的任务完成
        for name, task in tool_tasks.items():
            try:
                results[name] = await task
                logger.info(f"获取到服务器 {name} 的 {len(results[name])} 个工具")
            except Exception as e:
                logger.error(f"获取服务器 {name} 工具列表失败: {str(e)}")
                results[name] = []
        
        return results
    
    async def _get_server_tools(self, server_name: str, server: MCPServer) -> List[Dict[str, Any]]:
        """获取单个服务器的工具列表
        
        处理连接和异常情况，确保即使发生错误也返回有效结果。
        
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
            # 返回空列表而不是抛出异常
            return []
    
    async def execute_tool(self, server_name: str, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具调用
        
        遵循SDK样例的实现方式，包含重试逻辑和详细的错误处理。
        
        Args:
            server_name: 服务器名称
            tool_name: 工具名称
            args: 工具参数
            
        Returns:
            工具执行结果
            
        Raises:
            ValueError: 如果找不到服务器配置
            MCPError: 如果工具执行失败
        """
        # 连接服务器
        server = await self.connect_server(server_name)
        
        # 重试参数
        max_retries = 2
        retry_delay = 1.0
        
        logger.info(f"执行工具 {server_name}/{tool_name}")
        
        # 实现重试逻辑
        for attempt in range(max_retries):
            try:
                # 执行工具调用
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
                    # 已达到最大重试次数
                    logger.error(f"工具执行失败，已达到最大重试次数: {str(e)}")
                    
                    # 格式化错误消息作为结果返回
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
            方法调用结果
        """
        server = await self.connect_server(server_name)
        return await server.call(method, params)
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        try:
            # 使用超时来确保不会无限等待
            await asyncio.wait_for(self.disconnect_all(), timeout=10.0)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            logger.warning("断开连接超时或被取消")
        except Exception as e:
            logger.error(f"断开连接时出错: {str(e)}")
        logger.info("上下文管理器退出完成")
