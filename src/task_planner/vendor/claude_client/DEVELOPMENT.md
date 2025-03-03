# Claude客户端工具包开发指南

本文档为开发者提供扩展和改进Claude客户端工具包的指南。

## 项目结构

```
.
├── claude_client.py            # 基础版Claude客户端
├── enhanced_claude_client.py   # 增强版Claude客户端
├── pexpect_claude.py           # 底层Claude交互实现
├── claude_client_example.py    # 基础版示例
├── enhanced_claude_example.py  # 增强版示例
├── gemini_claude_example.py    # Gemini分析器示例
├── agent_tools/                # 工具组件集
│   ├── __init__.py
│   ├── followup_generator.py   # 跟进问题生成器
│   ├── gemini_analyzer.py      # Gemini任务分析器
│   ├── llm_service.py          # LLM服务接口
│   ├── parser.py               # 响应解析器
│   ├── task_analyzer.py        # 任务分析器
│   ├── tool_manager.py         # 工具调用管理
│   └── tools.py                # 基础工具实现
└── ClaudeClient_README.md      # 用户文档
```

## 关键组件

### 1. 底层交互 (pexpect_claude.py)

处理与Claude命令行工具的低级别交互，包括进程管理、状态检测和输入/输出处理。

### 2. 基础客户端 (claude_client.py)

提供简洁的API用于与Claude交互，封装了底层复杂性。

### 3. 增强客户端 (enhanced_claude_client.py)

扩展了基础客户端，添加了任务完成分析和自动跟进功能。

### 4. 任务分析器 (agent_tools/task_analyzer.py)

负责判断Claude的响应是否完成了任务。目前提供两种实现：
- RuleBasedAnalyzer: 基于规则的判断
- LLMTaskAnalyzer: 使用另一个LLM进行判断

### 5. Gemini分析器 (agent_tools/gemini_analyzer.py)

使用Google Gemini 2.0 Flash模型分析任务完成状态。

### 6. 跟进生成器 (agent_tools/followup_generator.py)

根据任务状态生成适当的跟进问题。

## 扩展指南

### 添加新的任务分析器

1. 在agent_tools包中创建新的分析器模块:

```python
# agent_tools/my_analyzer.py
from .task_analyzer import BaseTaskAnalyzer

class MyCustomAnalyzer(BaseTaskAnalyzer):
    def __init__(self, **kwargs):
        # 初始化代码
        pass
        
    def analyze(self, conversation_history, last_response):
        # 分析逻辑
        # 返回 "COMPLETED", "NEEDS_MORE_INFO" 或 "CONTINUE"
        return "COMPLETED"
```

2. 在`agent_tools/__init__.py`中导出您的分析器:

```python
# 在现有导入后添加
from .my_analyzer import MyCustomAnalyzer
```

3. 在客户端中使用您的分析器:

```python
from enhanced_claude_client import EnhancedClaudeClient
from agent_tools import MyCustomAnalyzer

analyzer = MyCustomAnalyzer()
client = EnhancedClaudeClient(analyzer=analyzer)
```

### 添加新的跟进生成器

1. 创建自定义跟进生成器:

```python
# agent_tools/my_generator.py
from .followup_generator import FollowupGenerator

class MyCustomGenerator(FollowupGenerator):
    def __init__(self, **kwargs):
        super().__init__()
        # 初始化代码
        
    def generate_followup(self, task_status, conversation_history, last_response):
        # 跟进问题生成逻辑
        if task_status == "NEEDS_MORE_INFO":
            return "自定义跟进问题"
        elif task_status == "CONTINUE":
            return "继续完成任务的自定义提示"
        return None
```

2. 在`agent_tools/__init__.py`中导出:

```python
from .my_generator import MyCustomGenerator
```

3. 在客户端中使用:

```python
generator = MyCustomGenerator()
client = EnhancedClaudeClient(followup_generator=generator)
```

### 使用其他LLM服务

要使用不同的LLM服务进行任务分析或跟进生成，您需要:

1. 实现LLMService接口:

```python
class MyLLMService:
    def __init__(self, **kwargs):
        # 初始化您的LLM服务
        pass
        
    async def process_chat_request(self, request):
        # 调用您的LLM API
        response = "您的LLM返回的内容"
        return {"raw_response": response}
```

2. 创建使用该服务的分析器:

```python
from agent_tools import LLMTaskAnalyzer

my_service = MyLLMService()
analyzer = LLMTaskAnalyzer(my_service)
client = EnhancedClaudeClient(analyzer=analyzer)
```

### 修改状态判断逻辑

如果您想修改规则分析器的判断规则:

1. 继承RuleBasedAnalyzer并覆盖判断逻辑:

```python
from agent_tools import RuleBasedAnalyzer

class MyRuleAnalyzer(RuleBasedAnalyzer):
    def __init__(self):
        super().__init__()
        # 添加自定义完成指示词
        self.completion_indicators.extend([
            "任务已完成",
            "这样就可以了"
        ])
        
    def analyze(self, conversation_history, last_response):
        # 可以完全覆盖分析逻辑，或调用父类方法后进行额外处理
        result = super().analyze(conversation_history, last_response)
        # 自定义额外规则
        if "特殊标记" in last_response:
            return "COMPLETED"
        return result
```

## 调试与测试

### 调试模式

使用`debug=True`启用详细日志:

```python
client = EnhancedClaudeClient(debug=True)
```

### 测试特定文本

可以使用Gemini分析器测试特定文本而不启动Claude:

```python
from agent_tools import GeminiTaskAnalyzer

analyzer = GeminiTaskAnalyzer()
result = analyzer.analyze([("问题", "...")], "回答")
print(f"分析结果: {result}")
```

### 日志记录

建议为复杂的自定义实现添加详细日志:

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class MyAnalyzer(BaseTaskAnalyzer):
    def analyze(self, conversation_history, last_response):
        logger.debug(f"分析回复: {last_response[:100]}...")
        # 分析逻辑
```

## 性能优化

1. **缓存机制**: 考虑为频繁使用的分析添加缓存。
2. **批处理**: 对于批量请求，避免频繁启动/关闭Claude进程。
3. **异步处理**: 使用异步IO可以提高多任务处理性能。

## 贡献指南

贡献新功能或改进时，请遵循以下原则:

1. **接口一致性**: 保持与现有接口兼容
2. **可扩展性**: 设计便于扩展的组件
3. **异常处理**: 妥善处理所有可能的错误情况
4. **文档**: 为新功能添加充分的文档说明
5. **示例**: 提供使用示例

## 下一步开发方向

1. **支持更多LLM**: 添加对更多模型的支持
2. **重构状态管理**: 改进Claude的状态检测和处理
3. **Web API接口**: 添加REST API接口
4. **流式处理**: 支持Claude的流式输出
5. **多模态支持**: 添加处理图像输入的能力