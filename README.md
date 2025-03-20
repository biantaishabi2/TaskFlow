# 任务规划与执行系统

任务规划与执行系统是一个集成了Claude、Gemini和AG2-Agent的智能任务分解和执行框架，可以自动将复杂任务拆分为可管理的小任务，并按照依赖关系执行它们。

## 主要功能

- **任务分析与拆分**：使用Claude分析复杂任务，将其拆解为结构化的子任务
- **依赖关系管理**：自动识别和处理子任务间的依赖关系
- **上下文管理**：追踪和传递任务执行过程中的上下文信息
- **并行任务执行**：支持并行执行无依赖关系的任务
- **任务状态智能分析**：使用Gemini模型分析任务完成状态
- **适应性执行**：根据任务状态分析结果动态调整执行流程
- **AG2-Agent集成**：支持使用AG2-Agent执行器系统进行多种模式的任务执行

## 系统架构

系统由以下核心组件构成：

- **任务规划器(TaskPlanner)**：负责分析任务需求和拆分任务
- **任务执行器(TaskExecutor)**：负责执行具体子任务
- **上下文管理器(ContextManager)**：管理任务执行过程中的上下文
- **Claude集成**：提供任务执行的主要能力
- **Gemini集成**：提供任务状态的智能分析
- **AG2-Agent执行器**：提供多种执行模式的任务处理能力

## 快速开始

### 安装

确保系统已安装Python 3.8+，然后安装本项目：

```bash
# 从源码安装
git clone git@github.com:biantaishabi2/TaskFlow.git
cd task_planner
pip install -e .
```

### 命令行使用

安装后，可以通过`task-planner`命令行工具使用系统功能：

```bash
# 查看帮助信息
task-planner --help
```

系统提供以下主要子命令：

| 命令          | 描述                   | 示例                                 |
|---------------|------------------------|--------------------------------------|
| plan          | 分析并规划任务         | `task-planner plan "任务描述"`        |
| run-task      | 执行新任务             | `task-planner run-task "任务描述"`    |
| run-subtasks  | 执行预定义子任务文件   | `task-planner run-subtasks tasks.json`|
| resume        | 恢复已存在任务         | `task-planner resume task_123456`     |

#### 1. 分析和规划任务
```bash
task-planner plan [任务描述|文件路径] [选项]

# 示例：
# 分析任务并输出规划结果
task-planner plan "设计一个数据分析流程"

# 从文件读取任务并指定输出目录
task-planner plan task.txt --file --output custom_output

# 生成详细的任务分析报告
task-planner plan "开发网站后端API" --detailed
```

#### 2. 执行新任务
```bash
task-planner run-task [任务描述|文件路径] [选项]

# 示例：
task-planner run-task "开发一个命令行计算器应用"
task-planner run-task task.json --file
```

#### 3. 执行预定义子任务
```bash
task-planner run-subtasks [子任务文件路径] [选项]

# 示例：
task-planner run-subtasks examples/demo_subtasks/code_subtasks.json
task-planner run-subtasks my_tasks.json --logs-dir custom_logs --use-claude

# 从指定子任务开始执行
task-planner run-subtasks my_tasks.json --start-from task_id

# 设置执行超时时间（默认500秒）
task-planner run-subtasks my_tasks.json --timeout 600
```

子任务执行支持以下选项：
- `--start-from TASK_ID`: 指定从哪个子任务开始执行
- `--timeout SECONDS`: 设置任务执行超时时间（默认500秒）
- `--logs-dir DIR`: 指定日志输出目录
- `--use-claude`: 使用Claude执行器而不是默认的AG2执行器

#### 4. 恢复任务
```bash
task-planner resume [任务ID] [选项]

# 示例：
task-planner resume task_1689321456 --logs-dir custom_logs
```

#### 执行器选择

系统提供了两种执行器：

1. **AG2执行器（默认）**：基于AG2-Agent的执行器，使用双代理模式进行任务执行：
   - 包含一个 AssistantAgent 和一个 LLMDrivenUserProxy
   - 支持复杂的工具调用和文件操作
   - 自动管理对话历史和上下文
   - 支持任务状态分析和验证
   - 默认使用 OpenRouter API 访问高性能模型

2. **Claude执行器**：基于Claude的执行器，适用于需要强大语言理解和生成能力的任务。

可以通过`--use-claude`参数选择使用Claude执行器：

```bash
# 使用Claude执行器
task-planner run-task "创建数据分析报告" --use-claude

# 使用默认的AG2执行器
task-planner run-task "创建数据分析报告"
```

#### 预定义子任务格式

子任务文件应为JSON数组，示例：
```json
[
  {
    "id": "requirements_analysis",
    "name": "需求分析",
    "description": "分析计算器应用需求",
    "instruction": "作为需求分析师，请分析...",
    "priority": "high",
    "dependencies": [],
    "output_files": {
      "main_result": "output/task1/result.json",
      "code_file": "output/task1/implementation.py"
    },
    "success_criteria": [
      "代码文件被成功创建",
      "代码符合PEP8规范"
    ],
    "timeout": 500
  },
  {
    "id": "core_implementation",
    "name": "核心功能实现",
    "description": "实现计算器核心功能",
    "instruction": "作为Python开发工程师，请实现...",
    "dependencies": ["requirements_analysis"],
    "output_files": {
      "main_result": "output/task2/result.json",
      "test_file": "output/task2/test_implementation.py"
    },
    "success_criteria": [
      "测试通过"
    ],
    "timeout": 500,
    "priority": "high"
  }
]
```

#### 输出和日志

任务执行过程中会生成以下输出：

1. **主要结果文件**：每个子任务都会生成一个 JSON 格式的结果文件，包含：
   ```json
   {
     "task_id": "task_xxx",
     "success": true,
     "result": {
       "summary": "任务执行结果摘要",
       "details": "详细执行结果"
     },
     "artifacts": {
       "generated_files": ["文件1路径", "文件2路径"]
     }
   }
   ```

2. **日志目录结构**：
   ```
   logs/
   ├── task_xxx/              # 任务ID目录
   │   ├── analysis.json      # 任务分析结果
   │   ├── subtasks/          # 子任务输出
   │   │   ├── subtask_1/     # 子任务工作目录
   │   │   │   ├── result.json  # 子任务结果
   │   │   │   └── output/      # 子任务生成的文件
   │   │   └── subtask_2/
   │   └── execution.log      # 执行日志
   └── task_api_server.log    # API服务器日志
   ```

3. **错误处理**：
   - 执行失败时会生成详细的错误日志
   - 位于 `logs/task_xxx/error_taskid.log`
   - 包含错误信息、堆栈跟踪和上下文数据

### Python API 使用

也可以在Python代码中使用系统API：

```python
from task_planner.core.task_planner import TaskPlanner
from task_planner.core.task_executor import TaskExecutor
from task_planner.core.ag2_two_agent_executor import AG2TwoAgentExecutor
from task_planner.core.context_management import ContextManager
from task_planner.core.task_decomposition_system import TaskDecompositionSystem

# 方法1: 使用完整的任务分解系统（规划者和执行者双层循环）
# 默认使用AG2执行器
system = TaskDecompositionSystem(logs_dir="custom_logs")
result = system.execute_complex_task("我的复杂任务描述")

# 使用Claude执行器
system_claude = TaskDecompositionSystem(use_claude=True, logs_dir="claude_logs")
result = system_claude.execute_complex_task("我的复杂任务描述")

# 方法2: 分开使用规划器和执行器
# 初始化组件
context_manager = ContextManager(context_dir="custom_context")
planner = TaskPlanner("我的复杂任务描述", context_manager=context_manager)

# 使用AG2执行器（推荐）
executor = AG2TwoAgentExecutor()
# 或使用Claude执行器
# executor = TaskExecutor(context_manager=context_manager, use_gemini=True)

# 任务分析和拆分
analysis = planner.analyze_task()
subtasks = planner.break_down_task(analysis)

# 执行任务
for subtask in subtasks:
    result = executor.execute_subtask(subtask)
    print(f"任务 {subtask['name']} 执行结果: {result['success']}")
    if result['success']:
        print(f"结果摘要: {result['result']['summary']}")
```

## 项目结构

项目采用Python包结构组织代码，核心模块位于`src/task_planner/`目录下：

- **task_planner/core/**: 核心功能模块
  - `task_planner.py`: 任务分析和拆分
  - `task_executor.py`: 任务执行
  - `context_management.py`: 上下文管理
  - `task_decomposition_system.py`: 整合规划和执行的系统
  - `tools/`: 核心工具模块
  
- **task_planner/distributed/**: 分布式和并行执行
  - `parallel_task_executor.py`: 并行任务执行
  - `distributed_task_decomposition_system.py`: 分布式任务拆分
  
- **task_planner/util/**: 辅助工具
  - `claude_cli.py`: Claude命令行集成
  - `claude_task_bridge.py`: Claude任务桥接

- **task_planner/vendor/**: 内置依赖
  - `claude_client/`: Claude客户端库
    - `agent_tools/`: 包含Gemini分析器等工具
      - `gemini_analyzer.py`: Gemini任务分析工具

- **task_planner/server/**: 服务器组件
  - `task_api_server.py`: API服务器
  - `task_visualization_server.py`: 可视化服务器
  - `task_monitor.py`: 任务监控

## 高级功能

### Gemini任务状态分析

系统集成了Google的Gemini模型，用于分析任务完成状态。详情请参阅[Gemini集成指南](Gemini集成指南.md)。

### AG2-Agent执行器系统

系统集成了AG2-Agent执行器，支持多种聊天模式进行任务执行：

- **集群聊天(Swarm)**：多个agent协同解决问题
- **序列聊天(Sequential)**：多个agent按顺序处理任务
- **双Agent聊天(Two-Agent)**：两个agent协作处理任务
- **群组聊天(Group)**：多个agent以小组形式协作
- **嵌套聊天(Nested)**：支持agent之间的嵌套对话

使用示例:

```python
from ag2_engine.ag2_executor import AG2Executor
from configs.ag2_config import load_config

# 加载配置
config = load_config("configs/ag2_config.yaml")
# 创建执行器
executor = AG2Executor(config)
# 执行任务
result = executor.execute("使用序列聊天模式分析数据")
```

#### AG2引擎与OpenRouter集成

AG2引擎现已支持通过OpenRouter API调用各种LLM模型，包括Google Gemini、Anthropic Claude等。这种集成方式提供了几个重要的优势：

- **灵活的模型选择**：通过单一API访问多种LLM模型
- **模型回退机制**：当主模型不可用时，自动尝试备选模型
- **标准化配置**：使用统一的`config_list`格式配置多个LLM模型

配置示例：

```yaml
# AG2配置文件示例 (configs/ag2_config.yaml)
agents:
  task_planner:
    name: "任务规划专家"
    type: "llm"
    system_message: "你是一个专业的任务规划专家，负责将复杂任务分解为可执行的子任务。"
    llm_config:
      config_list:
        - api_type: "openai"  # 使用OpenAI兼容API格式
          model: "google/gemini-2.0-flash-lite-001"  # Gemini模型
          temperature: 0.2
          api_key: "${OPENROUTER_API_KEY}"  # 使用环境变量
          base_url: "https://openrouter.ai/api/v1"  # OpenRouter端点
          extra_headers:
            HTTP-Referer: "https://github.com/anthropics/claude-code"
            X-Title: "AG2-Executor-Task-Planner"
```

设置环境变量并运行：

```bash
export OPENROUTER_API_KEY=your_api_key_here
python examples/ag2_execution_example.py
```
### 并行任务执行

对于没有相互依赖的任务，系统支持并行执行以提高效率：

```python
from task_planner.distributed.parallel_task_executor import ParallelTaskExecutor

executor = ParallelTaskExecutor(max_workers=4, context_manager=context_manager)
results = executor.execute_subtasks(subtasks)
```

## 项目文档

- [任务拆分与执行系统设计文档](代码注释生成系统设计文档.md)
- [任务拆分和执行系统实现步骤](任务拆分和执行系统实现步骤.md)
- [Gemini集成指南](Gemini集成指南.md)
- [代码结构重构文档](docs/code_structure_refactor.md)
- [重构V2文档](docs/refactor_v2.md)

## 部署

系统提供了Docker支持，可以通过以下方式快速部署：

```bash
# 构建Docker镜像
docker build -t task-planner .

# 运行容器
docker run -p 5000:5000 -p 8080:8080 task-planner
```

详细的Docker部署说明请参阅[Docker部署文档](README_DOCKER.md)。

## 许可证

本项目采用MIT许可证 - 详情请参阅LICENSE文件。

## 致谢

感谢Claude、Gemini和AG2-Agent团队提供的强大模型支持。

#### 使用预定义子任务

如果你已经有了任务拆分的结果，可以直接使用`task-planner run-subtasks`命令执行这些子任务：

1. 准备子任务JSON文件，例如 `subtasks.json`：

```json
[
  {
    "id": "task1",
    "name": "第一个子任务",
    "description": "任务1的描述",
    "instruction": "任务1的具体指令...",
    "dependencies": [],
    "output_files": {
      "main_result": "output/task1/result.json",
      "code_file": "output/task1/implementation.py"
    },
    "success_criteria": [
      "代码文件被成功创建",
      "代码符合PEP8规范"
    ],
    "timeout": 500,
    "priority": "high"
  },
  {
    "id": "task2",
    "name": "第二个子任务",
    "description": "任务2的描述",
    "instruction": "任务2的具体指令...",
    "dependencies": ["task1"],
    "output_files": {
      "main_result": "output/task2/result.json",
      "test_file": "output/task2/test_implementation.py"
    },
    "success_criteria": [
      "测试通过"
    ],
    "timeout": 500,
    "priority": "high"
  }
]
```

2. 执行子任务序列：

```bash
# 基本用法
task-planner run-subtasks subtasks.json

# 指定日志目录和执行器
task-planner run-subtasks subtasks.json --logs-dir custom_logs --use-claude
```

系统会：
- 按照依赖关系顺序执行子任务
- 自动创建必要的输出目录
- 验证每个任务的输出文件
- 生成详细的执行日志和结果文件
- 在任务失败时提供错误诊断信息

子任务定义支持的字段：
- `id`: 任务唯一标识符（必需）
- `name`: 任务名称（必需）
- `description`: 任务描述
- `instruction`: 具体执行指令（必需）
- `dependencies`: 依赖任务的ID列表
- `output_files`: 预期输出文件配置
  - `main_result`: 主要结果文件（必需）
  - 其他自定义输出文件
- `success_criteria`: 成功标准列表
- `timeout`: 执行超时时间（秒）
- `priority`: 任务优先级（high/normal/low）

## 环境配置

系统使用以下环境变量进行配置：

### 必需的环境变量

```bash
# OpenRouter API密钥（用于AG2执行器）
export OPENROUTER_API_KEY="your_openrouter_api_key"

# Claude API密钥（用于Claude执行器）
export CLAUDE_API_KEY="your_claude_api_key"

# 可选：Gemini API密钥（用于任务状态分析）
export GEMINI_API_KEY="your_gemini_api_key"
```

### 可选的环境变量

```bash
# 自定义API基础URL
export OPENROUTER_BASE_URL="https://openrouter.ai/api/v1"
export CLAUDE_BASE_URL="https://api.anthropic.com"

# 默认日志目录
export TASK_PLANNER_LOGS_DIR="custom_logs"

# 默认上下文目录
export TASK_PLANNER_CONTEXT_DIR="custom_context"

# 执行超时设置（秒，默认500秒）
export TASK_EXECUTOR_TIMEOUT="500"
```

### 配置文件

除了环境变量，也可以使用配置文件进行设置。创建 `~/.task_planner/config.yaml`：

```yaml
api:
  openrouter:
    api_key: "your_openrouter_api_key"
    base_url: "https://openrouter.ai/api/v1"
    default_model: "google/gemini-2.0-flash-lite-001"
  
  claude:
    api_key: "your_claude_api_key"
    base_url: "https://api.anthropic.com"
    
  gemini:
    api_key: "your_gemini_api_key"

execution:
  default_timeout: 500  # 默认执行超时时间（秒）
  logs_dir: "custom_logs"
  context_dir: "custom_context"
  
  # 执行器配置
  executor:
    type: "ag2"  # 或 "claude"
    parallel_tasks: 3
    retry_attempts: 2
```