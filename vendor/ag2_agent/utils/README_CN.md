# AG2-Agent 工具集成模块

本模块提供了一系列适配器类，用于将外部工具系统(如agent_tools包)集成到AG2-Agent框架中。

## 工具集成适配器 (tool_integration.py)

### ToolManagerAdapter

这个适配器类封装了外部工具管理器，提供一致的接口用于在AG2-Agent中注册和使用工具。

```python
# 创建适配器
adapter = ToolManagerAdapter(external_tool_manager)

# 注册工具实例
adapter.register_tool_from_instance("api_call", api_tool_instance)

# 创建并注册工具
adapter.create_and_register_tool(
    name="file_op", 
    tool_class=FileOperationTool
)

# 执行工具
result = await adapter.execute_tool("api_call", {"url": "...", "method": "GET"})
```

### LLMServiceAdapter

封装外部LLM服务的适配器，用于在AG2-Agent中使用外部LLM服务。

```python
# 创建适配器
llm_adapter = LLMServiceAdapter(external_llm_service)

# 生成响应
response = await llm_adapter.generate_response(
    prompt="你好，请帮我解答一个问题...",
    system_prompt="你是一个专业助手"
)

# 设置角色
llm_adapter.set_role("expert")
```

### ResponseParserAdapter

封装外部响应解析器的适配器，用于解析LLM响应中的工具调用。

```python
# 创建适配器
parser_adapter = ResponseParserAdapter(external_parser)

# 解析响应
parsed = parser_adapter.parse_response(llm_response)
print(parsed["thought"])  # 思考过程
print(parsed["tool_calls"])  # 工具调用
```

### TaskAnalyzerAdapter

封装外部任务分析器的适配器，用于分析任务是否完成。

```python
# 创建适配器
analyzer_adapter = TaskAnalyzerAdapter(external_analyzer)

# 分析任务状态
status = await analyzer_adapter.analyze_task(conversation_history, last_response)
# status可能是 "COMPLETED", "NEEDS_MORE_INFO", 或 "CONTINUE"
```

### FollowupGeneratorAdapter

封装外部跟进问题生成器的适配器，用于生成跟进问题。

```python
# 创建适配器
generator_adapter = FollowupGeneratorAdapter(external_generator)

# 生成跟进问题
followup = await generator_adapter.generate_followup(
    task_status="CONTINUE",
    conversation_history=chat_history,
    last_response=last_response
)
```

## LLM配置适配器 (llm_config_adapter.py)

### ExternalLLMConfig

允许在AG2-Agent中使用外部LLM服务的配置适配器。

```python
# 创建配置
config = ExternalLLMConfig(
    llm_service=external_service,
    model_name="custom-model",
    temperature=0.7,
    max_tokens=1000
)

# 生成响应
response = await config.generate(
    messages=[
        {"role": "system", "content": "你是一个助手"},
        {"role": "user", "content": "你好"}
    ]
)
```

### GeminiAnalyzerConfig

专门为Gemini任务分析器设计的配置适配器。

```python
# 创建配置
gemini_config = GeminiAnalyzerConfig(gemini_analyzer)

# 分析对话
status = await gemini_config.analyze_chat(messages, last_response)
```

## 使用示例

请参考项目中的示例文件：
- `examples/tool_integration_example.py` - 工具集成演示
- `examples/llm_config_example.py` - LLM配置演示

## 设计原则

这些适配器遵循以下设计原则：
1. **接口一致性** - 提供统一的接口，隐藏外部系统的复杂性
2. **错误处理** - 内置全面的错误处理，确保稳定性
3. **异步支持** - 同时支持同步和异步操作方法
4. **类型安全** - 使用严格的类型注解确保类型安全
5. **无侵入性** - 不修改原有系统，通过适配器模式实现集成