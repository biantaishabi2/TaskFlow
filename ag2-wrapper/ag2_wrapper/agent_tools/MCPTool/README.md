# MCPTool

MCPTool 是一个适配层工具，用于将 MCP (Model Context Protocol) 服务器的工具转换为 AG2 Executor 可调用的格式。

## 组件说明

- **MCPTool.py**: 适配层实现，负责将 MCP 工具转换为 AG2 格式
- **client.py**: MCP 客户端实现，负责服务器连接和工具管理
- **config.py**: 配置管理，处理多作用域配置（项目/全局/mcprc）

## 使用方法

### 1. 配置 MCP 服务器

```python
from MCPTool.config import add_server

# 添加 SSE 类型服务器
add_server("my_sse_server", {
    "type": "sse",
    "url": "http://localhost:8000/events"
})

# 添加 Stdio 类型服务器
add_server("my_stdio_server", {
    "type": "stdio",
    "command": "python",
    "args": ["server.py"],
    "env": {"DEBUG": "1"}
})
```

### 2. 使用适配层

```python
from MCPTool.MCPTool import MCPTool
from MCPTool.client import MCPClient

# 初始化客户端和适配层
client = MCPClient()
tool = MCPTool(client)

# 获取可用工具列表
tools = await tool.get_tools()

# 执行工具调用
result = await tool.execute("tool_name", {"arg1": "value1"})
```

## 工作流程

1. MCPTool 作为适配层接收来自 AG2 Executor 的调用
2. 通过 client.py 连接到 MCP 服务器
3. 使用 config.py 管理服务器配置
4. 执行工具调用并返回结果

## 配置说明

支持三种配置作用域：
- **项目级**: 针对特定项目的配置
- **全局级**: 适用于所有项目的配置
- **mcprc**: 通过 .mcprc 文件定义的配置

配置优先级：项目级 > mcprc > 全局级

## 实现总结

MCPTool已成功实现以下功能：

1. **配置管理系统**：
   - 多作用域配置支持（项目/全局/mcprc）
   - 基于Pydantic的类型安全配置
   - 服务器配置CRUD接口

2. **MCP客户端**：
   - 支持SSE和Stdio两种传输方式
   - 异步通信协议
   - 服务器连接和断开管理

3. **AG2适配层**：
   - MCP工具到AG2格式的转换
   - 工具发现和描述获取
   - 工具调用和结果处理

实现符合MCP设计文档中的要求，提供了一个完整的AG2与MCP服务器之间的桥梁。

## 实施步骤

1. **创建基础文件结构** ✅
   - 创建 `__init__.py`, `MCPTool.py`, `client.py`, `config.py`

2. **实现配置管理(`config.py`)** ✅
   - 使用Pydantic模型定义配置结构
   - 实现多作用域配置管理(项目/全局/mcprc)
   - 添加配置CRUD接口

3. **实现MCP客户端(`client.py`)** ✅
   - 创建MCPServer和MCPClient类
   - 实现两种传输方式(SSE/Stdio)
   - 支持标准SDK和自定义实现的双模式连接

4. **实现适配层(`MCPTool.py`)** ✅
   - 开发AG2格式转换机制
   - 实现工具调用和结果处理

5. **测试设置** ✅
   - 安装MCP Python SDK: `pip install git+https://github.com/modelcontextprotocol/python-sdk.git`
   - 安装示例服务器: `pip install mcp-server-time mcp-server-fetch`

6. **优化与最佳实践集成** ✅
   - 对标SDK示例实现优化连接管理
   - 添加重试机制和并发操作支持
   - 实现异步上下文管理器

7. **执行集成测试** ⚠️
   - MCP服务器通信需要特定的环境配置
   - 实现代码已完成，但测试需要根据实际环境调整

## MCP客户端正确使用方法

根据官方Python SDK示例，正确的MCP客户端使用方式如下：

### 1. 创建服务器连接

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from contextlib import AsyncExitStack

# 创建服务器参数
server_params = StdioServerParameters(
    command="python",  # 或其他命令
    args=["-m", "mcp_server_time"],  # 服务器参数
    env={...}  # 可选环境变量
)

# 使用AsyncExitStack管理资源
exit_stack = AsyncExitStack()

# 连接服务器
stdio_transport = await exit_stack.enter_async_context(
    stdio_client(server_params)
)
read_stream, write_stream = stdio_transport

# 创建会话
session = await exit_stack.enter_async_context(
    ClientSession(read_stream, write_stream)
)
await session.initialize()
```

### 2. 获取工具列表

```python
# 获取工具列表
tools_response = await session.list_tools()
tools = []

# 处理返回的工具列表
for item in tools_response:
    if isinstance(item, tuple) and item[0] == "tools":
        for tool in item[1]:
            tools.append({
                "name": tool.name, 
                "description": tool.description,
                "input_schema": tool.inputSchema
            })
```

### 3. 执行工具

```python
# 执行工具
try:
    result = await session.call_tool(
        "tool_name", 
        {"param1": "value1"}
    )
    # 处理结果
except Exception as e:
    # 错误处理
```

### 4. 资源清理

```python
# 清理资源
await exit_stack.aclose()
```

### 测试方法

在测试MCPTool与MCP服务器的集成时，应采用以下最佳实践：

1. **正确的资源管理**：
   - 使用AsyncExitStack确保所有资源正确释放
   - 实现适当的错误处理和重试机制
   - 在连接断开时及时清理资源

2. **配置管理**：
   - 使用JSON配置文件管理服务器设置
   - 支持命令和参数的灵活配置
   - 示例配置：
     ```json
     {
       "mcpServers": {
         "time": {
           "command": "python",
           "args": ["-m", "mcp_server_time"]
         }
       }
     }
     ```

3. **部署时测试**：
   - 确保在实际环境中测试服务器连接
   - 验证工具参数和执行逻辑
   - 使用调试日志跟踪通信问题

通过遵循这些最佳实践，可以确保MCPTool与MCP服务器之间的可靠通信。

注: ✅表示已完成，❌表示未完成，⏳表示进行中