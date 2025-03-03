# Claude 客户端工具包

一个全面的Python工具包，用于与Claude命令行工具进行交互。

## 客户端实现

本工具包提供了多种Claude客户端实现：

1. **基础版 (ClaudeClient)** - 简单的请求-响应交互
2. **增强版 (EnhancedClaudeClient)** - 支持任务完成分析和自动跟进
3. **Gemini增强版** - 使用Google Gemini模型分析任务完成状态

## 简介

这套工具封装了与Claude命令行工具的交互过程，使您能够以编程方式发送请求并获取Claude的回复，无需手动操作命令行界面。

### 基础版特点
- 自动管理Claude进程的生命周期
- 处理所有状态转换和交互确认
- 发送自定义请求并获取响应
- 自动处理超时和异常情况

### 增强版额外特点
- 智能判断任务是否完成
- 自动生成跟进问题直到任务完成
- 记录完整对话历史
- 支持对话状态分析

### Gemini增强版特点
- 使用Google Gemini 2.0 Flash模型分析任务完成状态
- 更智能的语义理解能力
- 能够处理不同类型的响应格式
- 可以识别列表、代码等特殊结构的完整性

## 安装要求

### 基本需求
- Python 3.6+
- pexpect 库
- 已安装Claude命令行工具

### Gemini增强版额外需求
- google-generativeai 库
- 有效的Google Gemini API密钥

## 使用方法

### 基础版用法

```python
from claude_client import ClaudeClient

# 创建客户端实例
client = ClaudeClient()

try:
    # 启动 Claude 进程
    client.start()
    
    # 发送请求并获取响应
    response = client.send_request("请帮我写一个Python函数来计算斐波那契数列")
    print(response)
    
    # 发送另一个请求
    response = client.send_request("现在帮我优化这个函数")
    print(response)
finally:
    # 确保关闭 Claude 进程
    client.close()
```

### 增强版用法

```python
from enhanced_claude_client import EnhancedClaudeClient

# 创建增强版客户端实例
client = EnhancedClaudeClient()

try:
    # 启动 Claude 进程
    client.start()
    
    # 发送请求并等待任务完成（自动跟进）
    response, history = client.send_request(
        "请写一个Python程序，包含以下功能：\n1. 读取CSV文件\n2. 分析数据\n3. 生成报表",
        auto_continue=True,
        max_iterations=3
    )
    
    # 输出最终响应
    print(response)
    
    # 显示完整对话历史
    for i, (question, answer) in enumerate(history):
        print(f"交互 {i+1}:")
        print(f"问: {question}")
        print(f"答: {answer[:100]}...")  # 只显示前100个字符
finally:
    # 确保关闭 Claude 进程
    client.close()
```

### Gemini增强版用法

```python
from enhanced_claude_client import EnhancedClaudeClient
from agent_tools import GeminiTaskAnalyzer

# 设置Gemini API密钥
api_key = "YOUR_GEMINI_API_KEY"  # 或从环境变量获取

# 创建Gemini分析器
analyzer = GeminiTaskAnalyzer(api_key=api_key)

# 创建使用Gemini分析器的客户端
client = EnhancedClaudeClient(analyzer=analyzer)

try:
    # 启动Claude进程
    client.start()
    
    # 发送请求并等待任务完成
    response, history = client.send_request(
        "请介绍一下Python语言的主要特点",
        auto_continue=True,
        max_iterations=3
    )
    
    # 输出最终响应
    print(response)
finally:
    # 关闭客户端
    client.close()
```

### 命令行使用

#### 基础版

```bash
# 直接发送单个请求
python claude_client.py "请帮我编写一个Python脚本来分析CSV文件"

# 启用调试模式
python claude_client.py --debug "请帮我编写一个Python脚本来分析CSV文件"

# 设置超时时间（秒）
python claude_client.py --timeout 120 "请帮我编写一个复杂的机器学习模型"

# 进入交互模式
python claude_client.py
```

#### 增强版

```bash
# 直接发送单个请求（自动跟进）
python enhanced_claude_client.py "请编写一个详细的机器学习模型"

# 禁用自动跟进
python enhanced_claude_client.py --no-auto "请分析这段代码"

# 设置最大交互次数
python enhanced_claude_client.py --max-iter 5 "请详细解释量子计算原理"

# 启用调试模式
python enhanced_claude_client.py --debug "请解释递归函数"
```

#### Gemini增强版

```bash
# 直接分析特定文本
python gemini_claude_example.py analyze

# Python特点分析示例
python gemini_claude_example.py python

# 代码生成分析示例
python gemini_claude_example.py code

# 长篇回复分析示例
python gemini_claude_example.py partial
```

### 示例文件

我们提供了完整的示例文件，展示不同使用场景：

#### 基础版示例 (`claude_client_example.py`)

```bash
# 基本示例
python claude_client_example.py basic

# 连续对话示例
python claude_client_example.py conversation

# 超时处理示例
python claude_client_example.py timeout

# 集成示例
python claude_client_example.py integration
```

#### 增强版示例 (`enhanced_claude_example.py`)

```bash
# 基本示例
python enhanced_claude_example.py basic

# 自动继续对话示例
python enhanced_claude_example.py auto

# 交互式使用示例
python enhanced_claude_example.py interactive

# 需要更多信息示例
python enhanced_claude_example.py more_info
```

#### Gemini增强版示例 (`gemini_claude_example.py`)

```bash
# Python特点分析
python gemini_claude_example.py python

# 代码生成分析
python gemini_claude_example.py code

# 长篇回复分析
python gemini_claude_example.py partial

# 直接分析特定文本
python gemini_claude_example.py analyze
```

## API 参考

### 基础版 - ClaudeClient 类

#### 初始化参数

- `debug` (bool, 可选): 启用调试输出。默认为 False。
- `timeout` (int, 可选): 等待 Claude 响应的超时时间（秒）。默认为 60。

#### 方法

- `start()`: 启动 Claude 进程并准备接收请求。
  - 返回: bool - 启动是否成功

- `send_request(request_text)`: 发送请求到 Claude 并等待响应。
  - 参数: `request_text` (str) - 要发送给 Claude 的请求文本
  - 返回: str - Claude 的响应文本（最后 2000 个字符）
  - 异常:
    - `RuntimeError`: Claude 进程不存在或已终止
    - `TimeoutError`: 等待响应超时

- `close()`: 关闭 Claude 进程并释放资源。

### 增强版 - EnhancedClaudeClient 类

#### 初始化参数

- `analyzer` (可选): 任务分析器实例，默认使用规则分析器
- `followup_generator` (可选): 跟进问题生成器实例，默认使用规则生成器
- `debug` (bool, 可选): 启用调试输出。默认为 False。
- `timeout` (int, 可选): 等待 Claude 响应的超时时间（秒）。默认为 60。

#### 方法

- `start()`: 启动 Claude 进程并准备接收请求。
  - 返回: bool - 启动是否成功

- `send_request(request_text, auto_continue=True, max_iterations=3)`: 发送请求并可选择自动继续对话直到任务完成。
  - 参数:
    - `request_text` (str): 请求文本
    - `auto_continue` (bool): 是否自动继续对话直到任务完成
    - `max_iterations` (int): 最大自动交互次数
  - 返回:
    - `response` (str): Claude的最终响应文本
    - `conversation_history` (list): 完整的对话历史记录

- `analyze_completion(response)`: 分析任务是否完成。
  - 参数: `response` (str): Claude的响应文本
  - 返回: 任务状态 ("COMPLETED", "NEEDS_MORE_INFO", "CONTINUE")

- `generate_followup(task_status, conversation_history, last_response)`: 生成跟进问题。
  - 返回: 生成的跟进问题，如果不需要跟进则返回None

- `close()`: 关闭 Claude 进程并释放资源。

## 任务分析器

增强版客户端支持多种任务分析器：

### 规则分析器 (RuleBasedAnalyzer)

使用预定义规则判断任务是否完成：
- 完成指示词: "希望这对你有帮助", "总结一下", 等
- 需要更多信息指示词: "你能提供更多信息吗", "请说明", 等

### LLM分析器 (LLMTaskAnalyzer)

使用另一个LLM来判断任务是否完成，通过分析对话历史和最新响应。

### Gemini分析器 (GeminiTaskAnalyzer)

使用Google的Gemini 2.0 Flash模型分析任务完成状态：
- 更强的语义理解能力
- 能识别不同类型的任务（代码、解释、事实、创意）
- 根据任务类型调整判断标准
- 能识别列表格式完整性

#### 初始化参数

- `api_key` (str, 可选): Gemini API密钥
- `model_name` (str, 可选): Gemini模型名称，默认为'gemini-2.0-flash'

## 实现原理

### 基础版 ClaudeClient

通过以下步骤与 Claude 交互:

1. **启动**: 初始化 Claude 命令行进程并处理初始状态
2. **状态管理**: 自动检测和处理 Claude 的不同状态
3. **请求发送**: 将用户输入发送到 Claude 并等待处理
4. **响应处理**: 捕获 Claude 的输出并返回
5. **资源清理**: 在客户端关闭时正确终止 Claude 进程

### 增强版 EnhancedClaudeClient

1. **基础交互**: 复用基础版的交互机制
2. **任务分析**: 分析Claude的响应，判断任务是否完成
3. **自动跟进**: 根据任务状态生成后续问题
4. **对话记录**: 维护完整的对话历史
5. **完整返回**: 返回最终响应和对话历史

### Gemini分析逻辑

1. **任务类型检测**: 根据原始请求识别任务类型
2. **提示构建**: 构建详细的分析提示，包含原始请求、任务类型、对话历史和最新回复
3. **模型调用**: 发送请求到Gemini API
4. **结果解析**: 解析模型返回结果，确定任务状态
5. **伪判断回退**: 如果API调用失败，使用规则进行基本判断

## 工具组件集成

增强版客户端使用了`agent_tools`包中的组件：

- **task_analyzer**: 任务完成状态分析器
- **gemini_analyzer**: 基于Gemini的任务分析器
- **followup_generator**: 自动跟进问题生成器
- **llm_service**: LLM服务统一接口 (可选使用)
- **parser**: LLM响应解析器 (可选使用)

## 性能与准确性比较

| 分析器类型 | 优点 | 缺点 | 适用场景 |
|----------|------|------|---------|
| **规则分析器** | 速度快、不需要API调用 | 识别准确率有限，依赖关键词 | 简单任务、明确结构的回复 |
| **Gemini分析器** | 高准确率、理解语义、识别结构 | 需要API调用、较慢 | 复杂任务、多样化的回复格式 |

## 示例效果

规则分析器和Gemini分析器在分析Python特点列表时的对比：

**Python特点列表**:
```
Python是一种高级解释型编程语言，其主要特点包括:
- 简洁易读的语法
- 动态类型系统
- 自动内存管理
- 丰富的标准库
- 跨平台兼容性
- 面向对象编程支持
- 函数式编程特性
- 强大的社区和生态系统
```

- **规则分析器**: 可能判断为"CONTINUE"（除非包含完成指示词）
- **Gemini分析器**: 正确判断为"COMPLETED"（识别为完整列表）

## 注意事项

- 确保已安装Claude命令行工具并且可以运行`claude`命令
- 使用Gemini分析器需要设置有效的API密钥
- 客户端返回的是Claude最后2000个字符的输出
- 默认超时时间为60秒，处理复杂请求时可能需要增加
- 每次只能运行一个客户端实例

## 依赖

- [pexpect_claude.py](/home/wangbo/document/wangbo/dev/pexpect_claude.py): 基础的Claude交互类
- [agent_tools](/home/wangbo/document/wangbo/dev/agent_tools/): 增强功能组件集
- [google-generativeai](https://pypi.org/project/google-generativeai/): Gemini API访问（仅Gemini增强版需要）

## 应用场景

1. **服务组件**: 将Claude集成到更大的应用程序或服务中
2. **批处理请求**: 批量处理多个请求并保存结果
3. **自动化工作流**: 将Claude作为自动化工作流的一部分
4. **问答系统**: 构建基于Claude的问答系统
5. **内容生成**: 自动化内容创建和优化过程
6. **智能助手**: 构建能够自动跟进的对话助手
7. **长任务处理**: 自动处理需要多轮交互的复杂任务
8. **状态感知交互**: 使用Gemini分析器实现更精确的对话状态管理

## 安装Gemini支持

```bash
# 安装google-generativeai包
pip install google-generativeai

# 设置环境变量
export GEMINI_API_KEY="your_api_key_here"
```

## 故障排除

如果遇到问题，请尝试以下步骤：

1. 启用调试模式查看详细日志: `client = EnhancedClaudeClient(debug=True)`
2. 增加超时时间处理复杂请求: `client = EnhancedClaudeClient(timeout=180)`
3. 确保仅运行一个Claude实例
4. 如果使用Gemini分析器时出错，检查API密钥是否有效
5. 如果客户端无响应，尝试手动终止后台Claude进程