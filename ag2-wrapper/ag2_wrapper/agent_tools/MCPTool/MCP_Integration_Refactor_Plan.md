# MCP 工具集成重构计划 (修订版)

本文档概述了将 MCP (Multi-Capability Protocol) 工具更深入、更健壮地集成到 AG2TwoAgentExecutor 中的计划。目标是统一工具注册逻辑，确保正确的提示词注入，并修复现有的参数转换问题。

## 背景与问题

当前集成存在以下问题：

1.  **参数转换错误**: `MCPTool._convert_parameters` 无法正确将 MCP SDK 返回的参数格式转换为 AG2 Executor 所需的 JSON Schema。
2.  **提示词未注入**: AG2 Executor 的系统提示词未包含从 MCP 服务器获取的工具描述和参数，导致 LLM 无法准确调用这些工具。
3.  **注册方式不统一**: MCP 工具在示例脚本中预先注册到 `ToolManager`，而标准工具在 Executor 内部通过 `ToolLoader` 注册。
4.  **注册的 Prompt 不正确**: 示例脚本中注册 MCP 工具时使用了硬编码的提示词，而非服务器返回的真实信息。

## 核心原则

*   **统一注册**: 所有工具（标准 AG2 工具和 MCP 工具）的发现和注册逻辑应统一在 `AG2TwoAgentExecutor` 内部完成。
*   **准确提示**: 系统提示词必须包含所有可用工具（包括 MCP 工具）的准确名称、描述和参数信息。
*   **动态入口**: 为每个 MCP 工具动态创建并注册一个轻量级的函数入口点到 AutoGen，以符合其按名称匹配函数调用的机制。
*   **适配层核心**: `MCPTool.py` 作为核心适配层，负责与 `MCPClient` 交互，转换工具格式，并处理执行路由。
*   **示例简化**: 示例脚本 (`ag2_integration_example.py`) 应专注于配置和启动 Executor，而非工具注册细节。

## 修改方案步骤

1.  **修复 `MCPTool.py`**:
    *   **优先级最高**: 调试并彻底修复 `MCPTool._convert_parameters` 方法。确保能正确解析 `mcp` SDK 返回的工具参数结构（如 `inputSchema`）并生成有效的 AG2 JSON Schema。
    *   验证 `MCPServer.call` 中对 `tools/list` 响应的解析逻辑，确保数据准确性。
    *   完善 `MCPTool._normalize_result` 以更好地处理不同类型的工具执行结果和错误。

2.  **修改 `AG2TwoAgentExecutor.__init__` / `create`**:
    *   调整构造函数或工厂方法，使其能够接收一个已初始化的 `MCPTool` 实例（包含 `MCPClient`）。

3.  **重构 `AG2TwoAgentExecutor._initialize_tools`**:
    *   **合并逻辑**: 此方法将负责初始化 *所有* 工具。
    *   **标准工具**: 保留使用 `ToolLoader` 加载标准 AG2 工具的逻辑，并将其注册到 `self.tool_manager` 和 AutoGen。
    *   **MCP 工具**:
        *   获取传入的 `MCPTool` 实例。
        *   调用 `await mcp_tool.get_tools()` 获取 AG2 格式的 MCP 工具列表 (`ag2_tools`)。
        *   循环遍历 `ag2_tools`：
            *   为每个 `ag2_tool` 创建一个包装器函数 (使用 `functools.partial` 或闭包)，该函数捕获 `ag2_tool['name']` 和共享的 `mcp_tool` 实例，并在调用时执行 `await mcp_tool.execute(captured_name, **kwargs)`。
            *   使用 `register_function` 将此包装器注册到 AutoGen，`name` 为 `ag2_tool['name']`，`description` 使用 `ag2_tool['description']` 和格式化的参数信息 (`ag2_tool['parameters']`)。
            *   将 `ag2_tool` 的相关信息（或包装器引用）添加到 `self.tool_manager` 或内部列表，供 `_build_tools_prompt` 使用。

4.  **修改 `AG2TwoAgentExecutor._build_tools_prompt`**:
    *   确保此方法能访问 `self.tool_manager` 或包含所有工具信息的内部列表。
    *   遍历**所有**已注册的工具（标准 + MCP），提取名称、描述和参数。
    *   构建包含所有工具信息的 `{TOOLS_SECTION}`，注入到 `DEFAULT_SYSTEM_PROMPT`。

5.  **简化 `ag2_integration_example.py`**:
    *   移除所有 MCP 工具发现和注册的代码（`get_tools`, 循环, `tool_manager.register_tool`)。
    *   保留服务器配置 (`configure_mcp_servers`)。
    *   创建 `MCPClient` 和 `MCPTool` 实例 (`get_mcp_tool`)。
    *   创建 `AG2ToolManager`, `ContextManager`, `ConfigManager`。
    *   调用 `AG2TwoAgentExecutor.create`，将 `MCPTool` 实例和其他管理器传入。
    *   调用 `executor.execute()`。

## 预期结果

*   `AG2TwoAgentExecutor` 成为工具管理的中心。
*   系统提示词准确反映所有可用工具及其用法。
*   AutoGen 能够正确路由对 MCP 工具的调用。
*   代码结构更清晰，集成逻辑更健壮。
*   示例脚本更简洁，专注于演示执行流程。 