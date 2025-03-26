# MCPTool

MCPTool 是一个适配层工具，用于将 MCP (Model Context Protocol) 服务器的工具转换为 AG2 Executor 可调用的格式。

## 组件说明

- **MCPTool.py**: 适配层实现，负责将 MCP 工具转换为 AG2 格式
- **client.py**: 原始 MCP 客户端实现，较为复杂（约1000行代码）
- **client_sdk.py**: 新版纯 SDK 实现的客户端，更简洁可靠（约500行代码）
- **config.py**: 配置管理，处理多作用域配置（项目/全局/mcprc）

## 使用方法

### 1. 配置 MCP 服务器

```python
from MCPTool.config import add_server

# 添加 Stdio 类型服务器（推荐）
add_server("my_stdio_server", {
    "type": "stdio",
    "command": "python",
    "args": ["server.py"],
    "env": {"DEBUG": "1"}
})

# 添加 SSE 类型服务器（实验性支持）
add_server("my_sse_server", {
    "type": "sse",
    "url": "http://localhost:8000/events"
})
```

### 2. 使用适配层

```python
from MCPTool import MCPTool, MCPClient

# 初始化客户端和适配层
client = MCPClient()
tool = MCPTool(client)

# 获取可用工具列表
tools = await tool.get_tools()

# 执行工具调用
result = await tool.execute("mcp__server_name__tool_name", {"arg1": "value1"})
```

### 3. 使用SSE连接

```python
from MCPTool import MCPClient
from MCPTool.config import add_server

# 添加SSE服务器配置
add_server("my_sse_server", {
    "type": "sse",
    "url": "http://localhost:8000/mcp",  # 替换为实际的SSE服务器地址
    "timeout": 5.0,  # 连接超时(秒)
    "sse_read_timeout": 300.0,  # SSE读取超时(秒)
    "headers": {  # 可选的请求头
        "Authorization": "Bearer YOUR_TOKEN"
    }
})

# 连接服务器
client = MCPClient()
server = await client.connect_server("my_sse_server")

# 获取工具列表和使用工具
tools = await server.list_tools()
result = await server.execute_tool("tool_name", {"param": "value"})

# 完成后断开连接
await client.disconnect_all()
```

### 4. 选择客户端实现

默认情况下使用SDK实现的客户端，更简洁可靠。可以通过环境变量控制：

```bash
# 使用SDK实现（默认）
export MCP_USE_SDK_CLIENT=1

# 使用旧版客户端
export MCP_USE_SDK_CLIENT=0
```

## 工作流程

1. MCPTool 作为适配层接收来自 AG2 Executor 的调用
2. 通过 client_sdk.py（或 client.py）连接到 MCP 服务器
3. 使用 config.py 管理服务器配置
4. 执行工具调用并返回结果

## 配置说明

支持三种配置作用域：
- **项目级**: 针对特定项目的配置
- **全局级**: 适用于所有项目的配置
- **mcprc**: 通过 .mcprc 文件定义的配置

配置优先级：项目级 > mcprc > 全局级

## 功能实现状态

MCPTool已成功实现以下功能：

1. **配置管理系统** ✅
   - 多作用域配置支持（项目/全局/mcprc）
   - 基于Pydantic的类型安全配置
   - 服务器配置CRUD接口

2. **MCP客户端** ✅
   - **Stdio传输方式** ✅ - 完全支持并经过测试
   - **SSE传输方式** ✅ - 两个版本均已实现，SDK版本新添加支持
   - 异步通信协议
   - 服务器连接和断开管理
   - 双版本实现（旧版和SDK版）

3. **AG2适配层** ✅
   - MCP工具到AG2格式的转换
   - 工具发现和描述获取
   - 工具调用和结果处理

4. **资源管理** ✅
   - 使用AsyncExitStack确保资源正确释放
   - 进程管理与错误恢复
   - 超时保护和异常处理

## 实现与优化历程

1. **创建基础文件结构** ✅
   - 创建 `__init__.py`, `MCPTool.py`, `client.py`, `config.py`

2. **实现配置管理(`config.py`)** ✅
   - 使用Pydantic模型定义配置结构
   - 实现多作用域配置管理(项目/全局/mcprc)
   - 添加配置CRUD接口

3. **实现MCP客户端(`client.py`)** ✅
   - 创建MCPServer和MCPClient类
   - 实现两种传输方式(SSE/Stdio)，但SSE未经全面测试
   - 支持标准SDK和自定义实现的双模式连接

4. **实现适配层(`MCPTool.py`)** ✅
   - 开发AG2格式转换机制
   - 实现工具调用和结果处理

5. **性能和可靠性优化** ✅
   - 对标SDK示例重构连接管理
   - 添加重试机制和并发操作支持
   - 实现异步上下文管理器
   - 创建纯SDK版本(`client_sdk.py`)，更简洁可靠

6. **测试与验证** ⚠️
   - **Stdio连接** ✅ - 已测试，工作正常
   - **SSE连接** ❌ - 尚未全面测试
   - **everything服务器** ✅ - 已测试，工作正常
   - 核心工具(echo, add, printEnv) ✅ - 已验证

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

## MCP客户端正确使用方法（SDK版本）

根据官方Python SDK示例和我们的最新实现，推荐的MCP客户端使用方式如下：

### 1. 创建服务器连接

```python
from MCPTool import MCPClient, MCPServer
from .config import add_server

# 添加服务器配置
add_server("time_server", {
    "type": "stdio",
    "command": "python",
    "args": ["-m", "mcp_server_time"]
})

# 创建客户端并连接服务器
client = MCPClient()
server = await client.connect_server("time_server")
```

### 2. 获取工具列表

```python
# 获取特定服务器的工具列表
tools = await server.list_tools()

# 或者获取所有服务器的工具列表
all_tools = await client.list_all_tools()
```

### 3. 执行工具

```python
# 通过服务器直接执行工具
result = await server.execute_tool("tool_name", {"param1": "value1"})

# 或通过客户端指定服务器执行工具
result = await client.execute_tool("server_name", "tool_name", {"param1": "value1"})
```

### 4. 资源清理

```python
# 断开所有连接
await client.disconnect_all()

# 或断开特定服务器
await server.disconnect()
```

## 测试方法

在测试MCPTool与MCP服务器的集成时，建议采用以下最佳实践：

1. **资源管理**
   - 测试应包含适当的清理逻辑，确保进程正确终止
   - 使用超时保护防止测试卡住
   - 确保在异常情况下也能释放资源

2. **工具测试**
   - 测试基本工具：echo, add, printEnv
   - 验证工具参数和结果处理
   - 测试错误情况下的行为

3. **配置管理**
   - 测试多种配置场景
   - 验证配置优先级和作用域管理

4. **测试SSE连接**
   - 先启动SSE服务器：`python -m ag2_wrapper.agent_tools.MCPTool.test_echo_server`
   - 然后在另一个终端中运行客户端测试：`python -m ag2_wrapper.agent_tools.MCPTool.test_sse`
   - 确保正确清理资源和连接

### 提供的测试文件

MCPTool包含以下测试文件，用于验证功能和集成：

1. **test_basic.py**
   - 基础功能测试脚本
   - 测试客户端初始化、服务器连接和工具执行
   - 使用stdio连接验证核心功能
   - 运行方式：`python -m ag2_wrapper.agent_tools.MCPTool.test_basic`

2. **test_echo_server.py**
   - 简单的MCP Echo服务器，提供echo工具
   - 使用SSE传输方式
   - 主要用于测试SSE客户端实现
   - 运行方式：`python -m ag2_wrapper.agent_tools.MCPTool.test_echo_server`

3. **test_sse.py**
   - SSE连接测试脚本
   - 连接到运行中的SSE服务器并验证功能
   - 需要先启动test_echo_server.py
   - 运行方式：`python -m ag2_wrapper.agent_tools.MCPTool.test_sse`

4. **test_sdk_example.py**
   - 使用SDK示例服务器的测试脚本
   - 验证与SDK示例服务器的集成
   - 测试fetch工具功能
   - 运行方式：`python -m ag2_wrapper.agent_tools.MCPTool.test_sdk_example`

## 与AG2 Executor集成

要在AG2 Executor中通过MCPTool调用MCP服务器工具，需要完成以下步骤：

### 1. 安装依赖

在AG2 Executor环境中安装必要的依赖：

```bash
# 安装MCPTool依赖
pip install mcp-sdk uvicorn starlette httpx httpx-sse
```

### 2. 配置MCP服务器

在您的项目中添加MCP服务器配置：

```python
from ag2_wrapper.agent_tools.MCPTool.config import add_server

# 添加Stdio类型服务器
add_server("time_server", {
    "type": "stdio",
    "command": "python",
    "args": ["-m", "mcp_server_time"]
})

# 添加SSE类型服务器
add_server("web_server", {
    "type": "sse",
    "url": "http://localhost:8000/sse"
})
```

### 3. 注册MCP工具到AG2 Executor

在AG2 Executor中注册MCPTool：

```python
from ag2_wrapper.core.ag2_executor import AG2TwoAgentExecutor
from ag2_wrapper.agent_tools.MCPTool import MCPTool, MCPClient

# 初始化客户端和工具
mcp_client = MCPClient()
mcp_tool = MCPTool(mcp_client)

# 创建AG2 Executor
executor = await AG2TwoAgentExecutor.create(
    # ...其他参数...
)

# 注册MCP工具
tools = await mcp_tool.get_tools()
for tool in tools:
    executor.register_tool(tool)
```

### 4. 在执行完成后清理资源

```python
# 在使用完成后清理资源
await mcp_client.disconnect_all()
```

### 5. 执行调用示例

通过AG2 Executor调用MCP工具：

```python
# 获取当前时间（time_server提供的工具）
result = await executor.execute(
    "获取洛杉矶和东京的当前时间", 
    tools=["mcp__time_server__get_current_time"]
)

# 获取网页内容（web_server提供的工具）
result = await executor.execute(
    "获取https://example.com的网页内容",
    tools=["mcp__web_server__fetch"]
)
```

## 下一步计划

1. **增强测试覆盖**
   - 添加更多边缘情况测试
   - 添加长时间运行的稳定性测试

2. **性能优化**
   - 添加连接池管理
   - 优化序列化和错误处理
   - 实现更高效的资源管理

3. **高级功能**
   - 实现gRPC支持
   - 添加服务器自动发现功能
   - 实现服务器健康检查和自动重连

4. **AG2集成增强**
   - 提供内置的常用MCP服务器集成
   - 实现更简便的工具注册机制
   - 提供工具使用示例和模板

注: ✅表示已完成且稳定，⚠️表示部分完成或有限制，❌表示未完成