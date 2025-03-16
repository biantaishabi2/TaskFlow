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
git clone git@github.com:biantaishabi2/task_planner.git
cd task_planner
pip install -e .
```

### 命令行使用

安装后，可以通过`task-planner`命令行工具使用系统功能：

```bash
# 查看帮助信息
task-planner --help

# 运行可视化服务器
task-planner visualization --port 8080 --api-url http://localhost:5000

# 运行分布式系统
task-planner distributed --mode master --api-port 5000 --task "复杂任务描述"
```

> 注意：新增的子命令需要额外安装一次才能生效:
>
> ```bash
> # 重新安装更新CLI命令
> pip install -e .
> 
> # 然后可以使用新增的命令
> # 执行单个任务
> task-planner execute "设计一个简单的Python网站内容管理系统"
> task-planner execute -f task.txt --logs-dir custom_logs
> 
> # 使用Claude执行器（默认使用AG2执行器）
> task-planner execute "创建数据分析报告" --use-claude
> 
> # 仅进行任务规划
> task-planner plan "设计一个数据分析流程" 
> task-planner plan -f task.txt --output custom_output
> 
> # 执行已拆分的多个子任务（不进行规划）
> task-planner run-subtasks -f subtasks.json --logs-dir custom_logs
> 
> # 使用Claude执行器运行子任务（默认使用AG2执行器）
> task-planner run-subtasks subtasks.json --use-claude
> ```

#### 执行器选择

系统提供了两种执行器：

1. **AG2执行器（默认）**：基于AG2-Agent的执行器，使用双代理模式进行任务执行，支持更复杂的交互和工具调用。
2. **Claude执行器**：基于Claude的执行器，适用于需要强大语言理解和生成能力的任务。

可以通过`--use-claude`参数选择使用Claude执行器：

```bash
# 使用Claude执行器
task-planner execute "创建数据分析报告" --use-claude

# 使用默认的AG2执行器
task-planner execute "创建数据分析报告"
```

#### 使用预定义子任务

如果你已经有了任务拆分的结果，可以直接使用`task-planner run-subtasks`命令执行这些子任务：

1. 准备子任务JSON文件，例如：

```json
[
  {
    "id": "task1",
    "name": "第一个子任务",
    "description": "任务1的描述",
    "instruction": "任务1的具体指令...",
    "dependencies": []
  },
  {
    "id": "task2",
    "name": "第二个子任务",
    "description": "任务2的描述",
    "instruction": "任务2的具体指令...",
    "dependencies": ["task1"]
  }
]
```

2. 执行子任务序列：

```bash
task-planner run-subtasks -f path/to/subtasks.json
```

系统会按照依赖关系顺序执行子任务，并将任务执行结果和上下文信息保存到日志目录中。

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
system = TaskDecompositionSystem()
result = system.execute_complex_task("我的复杂任务描述")

# 使用Claude执行器
system_claude = TaskDecompositionSystem(use_claude=True)
result = system_claude.execute_complex_task("我的复杂任务描述")

# 方法2: 分开使用规划器和执行器
# 初始化组件
context_manager = ContextManager()
planner = TaskPlanner("我的复杂任务描述", context_manager=context_manager)

# 使用AG2执行器（推荐）
executor = AG2TwoAgentExecutor(context_manager=context_manager)

# 或者使用Claude执行器
# executor = TaskExecutor(context_manager=context_manager, use_gemini=True)

# 任务分析和拆分
analysis = planner.analyze_task()
subtasks = planner.break_down_task(analysis)

# 执行任务
for subtask in subtasks:
    result = executor.execute_subtask(subtask)
    print(f"任务 {subtask['name']} 执行结果: {result['success']}")
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
  - `ag2_agent/`: AG2-Agent执行器系统
    - `core/`: AG2-Agent核心组件
    - `chat_modes/`: 不同的聊天模式实现
    - `factories/`: 工厂模式实现
    - `utils/`: 工具和辅助功能

- **ag2_engine/**: AG2执行引擎
  - `adapters/`: 适配器
  - `ag2_executor.py`: AG2执行器
  - `config_loader.py`: 配置加载器

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