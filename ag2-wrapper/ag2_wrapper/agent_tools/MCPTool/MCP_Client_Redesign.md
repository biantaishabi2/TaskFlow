# MCP 客户端实现与重构说明

## 实现概述

MCPTool 是一个适配层工具，将 MCP (Model Context Protocol) 服务器的工具转换为 AG2 Executor 可调用的格式。

**MCP客户端 (`client_sdk.py`)**
- 约500行代码
- 完全基于官方MCP SDK实现
- 简洁、可靠，支持Stdio和SSE传输
- 良好的资源管理和错误处理

## 主要组件

### 1. 文件结构
```
MCPTool/
├── __init__.py                # 包导出
├── MCPTool.py                 # 适配层主类，转换MCP工具为AG2格式
├── client_sdk.py              # 基于MCP SDK的客户端实现
├── config.py                  # 配置管理
└── test_basic.py              # 基础功能测试
```

### 2. 配置管理实现 (`config.py`)

已完成的配置系统使用Pydantic进行模型定义：

```python
# 服务器配置模型
class McpServerConfig(BaseModel):
    type: Literal["stdio", "sse"]
    command: Optional[str] = None
    args: Optional[List[str]] = None
    env: Optional[Dict[str, str]] = None
    url: Optional[str] = None  # For SSE

# 配置管理接口
def add_server(name: str, config: dict, scope="project") -> None
def remove_server(name: str, scope="project") -> None
def list_servers() -> Dict[str, dict]
def get_server(name: str) -> Optional[dict]
```

### 3. 核心客户端类 (`client_sdk.py`)

```python
class MCPServer:
    """MCP服务器连接，纯SDK实现"""
    
    def __init__(self, name: str, config: dict):
        self.name = name
        self.config = config
        self.session = None
        self._tools_cache = None
        self._exit_stack = AsyncExitStack()
        self._lock = asyncio.Lock()
        self._connected = False
    
    async def connect(self) -> None: ...
    async def disconnect(self) -> None: ...
    async def call(self, method: str, params: Optional[Dict[str, Any]] = None) -> Any: ...
    async def list_tools(self) -> List[Dict[str, Any]]: ...
    async def execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]: ...

class MCPClient:
    """MCP客户端管理类"""
    
    def __init__(self):
        self.servers: Dict[str, MCPServer] = {}
        self._exit_stack = AsyncExitStack()
        self._global_lock = asyncio.Lock()
        self._initialized = False
    
    async def initialize(self) -> None: ...
    async def connect_server(self, name: str) -> MCPServer: ...
    async def disconnect_all(self) -> None: ...
    async def list_all_tools(self) -> Dict[str, List[Dict[str, Any]]]: ...
    async def execute_tool(self, server_name: str, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]: ...
```

### 4. 适配层 (`MCPTool.py`)

```python
class MCPTool:
    """MCP工具适配器"""
    
    def __init__(self, client: MCPClient):
        self.client = client
        self._tools_cache = None
    
    async def get_tools(self) -> List[Dict[str, Any]]: ...
    async def register_tools(self, register_func: Callable) -> int: ...
    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]: ...
```

## 功能实现状态

1. **配置管理系统** ✅
   - 多作用域配置支持（项目/全局/mcprc）
   - 基于Pydantic的类型安全配置
   - 服务器配置CRUD接口

2. **MCP客户端** ✅
   - **Stdio传输方式** ✅ - 完全支持并经过测试
   - **SSE传输方式** ✅ - 已实现并通过测试
   - 异步通信协议
   - 服务器连接和断开管理
   - 基于官方MCP SDK实现

3. **AG2适配层** ✅
   - MCP工具到AG2格式的转换
   - 工具发现和描述获取
   - 工具调用和结果处理

4. **资源管理** ✅
   - 使用AsyncExitStack确保资源正确释放
   - 进程管理与错误恢复
   - 超时保护和异常处理
   - SSE和Stdio连接的可靠资源清理

## 优化历程

1. **初始实现**
   - 创建基础客户端和服务器接口
   - 实现配置管理系统
   - 添加SSE和Stdio传输层
   - 实现基本的工具调用

2. **资源管理优化**
   - 修复进程清理问题
   - 添加AsyncExitStack管理资源
   - 改进错误处理和超时控制

3. **SDK整合**
   - 对照SDK示例重构连接逻辑
   - 创建纯SDK实现的client_sdk.py
   - 添加版本选择机制
   - 实现SDK版本的SSE连接支持

4. **测试与验证**
   - 实现测试脚本
   - 验证工具列表获取和执行
   - 测试资源清理流程

## 当前局限性

1. **SSE支持**
   - 两个版本现在均支持SSE连接
   - 需要进行完整的端到端测试验证

2. **未实现的高级功能**
   - gRPC支持
   - 热重载
   - 监控指标

3. **测试覆盖**
   - 单元测试覆盖率有限
   - 主要依赖集成测试

## 当前状态

SSE支持已经完成并通过了测试：
1. 两个客户端版本都已实现SSE连接支持
2. 已通过与echo服务器的集成测试验证了功能
3. 资源管理机制已经过测试，确保可靠的连接和断开

### 测试文件

1. **test_echo_server.py**
   - 简单的MCP Echo服务器，使用SSE传输方式
   - 提供echo工具用于测试SSE客户端实现
   - 运行方式：`python -m ag2_wrapper.agent_tools.MCPTool.test_echo_server`

2. **test_sse.py**
   - SSE连接测试脚本，连接到运行中的SSE服务器
   - 测试获取工具列表和调用工具
   - 运行方式：`python -m ag2_wrapper.agent_tools.MCPTool.test_sse`

3. **test_sdk_example.py**
   - 使用SDK示例服务器的测试脚本
   - 验证与SDK服务器的兼容性
   - 运行方式：`python -m ag2_wrapper.agent_tools.MCPTool.test_sdk_example`

## 与AG2 Executor集成

将MCPTool集成到AG2 Executor需要以下步骤：

1. **安装依赖**
   ```bash
   pip install mcp-sdk uvicorn starlette httpx httpx-sse
   ```

2. **初始化MCPTool**
   ```python
   from ag2_wrapper.agent_tools.MCPTool import MCPTool, MCPClient
   from ag2_wrapper.agent_tools.MCPTool.config import add_server
   
   # 配置服务器
   add_server("time_server", {
       "type": "stdio",
       "command": "python",
       "args": ["-m", "mcp_server_time"]
   })
   
   # 初始化客户端和工具
   mcp_client = MCPClient()
   mcp_tool = MCPTool(mcp_client)
   ```

3. **注册MCP工具**
   ```python
   # 获取并注册工具
   tools = await mcp_tool.get_tools()
   for tool in tools:
       executor.register_tool(tool)
   ```

4. **资源管理**
   ```python
   # 使用try/finally确保资源释放
   try:
       # 使用AG2 Executor
       result = await executor.execute(prompt, tools=["mcp__time_server__get_current_time"])
   finally:
       # 清理资源
       await mcp_client.disconnect_all()
   ```

## 下一步计划

1. **增强适配层功能**
   - 简化工具注册过程
   - 改进错误处理和异常恢复机制
   - 提供更友好的工具发现接口

2. **扩展支持的服务器**
   - 添加内置常用MCP服务器集成
   - 提供服务器模板和示例代码
   - 实现服务器自动发现机制

3. **性能优化**
   - 添加连接池管理
   - 优化序列化和响应处理
   - 实现懒加载和按需连接机制

## 使用建议

1. **首选SDK版客户端**
   ```python
   # 设置环境变量选择SDK版（默认）
   os.environ["MCP_USE_SDK_CLIENT"] = "1"
   
   # 或在程序启动前保持默认值（默认为SDK版）
   ```

2. **连接Stdio服务器**
   ```python
   # 配置服务器
   add_server("my_stdio_server", {
       "type": "stdio",
       "command": "python",
       "args": ["-m", "my_mcp_server"],
       "env": {"DEBUG": "1"}
   })
   
   # 连接服务器
   client = MCPClient()
   server = await client.connect_server("my_stdio_server")
   ```

3. **连接SSE服务器**
   ```python
   # 配置SSE服务器
   add_server("my_sse_server", {
       "type": "sse",
       "url": "http://localhost:8000/mcp",
       "timeout": 5.0,            # 连接超时（秒）
       "sse_read_timeout": 300.0, # SSE读取超时（秒）
       "headers": {               # 可选的请求头
           "Authorization": "Bearer YOUR_TOKEN"
       }
   })
   
   # 连接服务器
   client = MCPClient()
   server = await client.connect_server("my_sse_server")
   
   # 使用完后断开连接
   await server.disconnect()
   # 或断开所有连接
   await client.disconnect_all()
   ```

4. **适当的资源管理**
   ```python
   try:
       # 使用客户端
       tools = await server.list_tools()
       result = await server.execute_tool("tool_name", {"param": "value"})
   finally:
       # 确保断开连接
       await client.disconnect_all()
   ```

注: ✅表示已完成且稳定，⚠️表示部分完成或有限制，❌表示未完成
