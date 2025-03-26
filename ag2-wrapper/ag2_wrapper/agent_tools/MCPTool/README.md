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

### 3. 选择客户端实现

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
   - **SSE传输方式** ⚠️ - 有限支持，仅旧版客户端中实现，未经全面测试
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
   - SDK版本尚不支持SSE连接
   - 旧版本有SSE实现但缺少全面测试

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

## 下一步计划

1. **SSE支持完善**
   - 为SDK版本实现SSE支持
   - 编写SSE服务器测试用例

2. **增强测试覆盖**
   - 添加单元测试
   - 扩展测试场景

3. **文档更新**
   - 保持文档与实现的一致性
   - 提供更详细的使用指南

4. **性能优化**
   - 添加连接池管理
   - 优化序列化过程

注: ✅表示已完成且稳定，⚠️表示部分完成或有限制，❌表示未完成