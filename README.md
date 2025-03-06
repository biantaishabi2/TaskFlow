# 任务规划与执行系统

任务规划与执行系统是一个集成了Claude和Gemini的智能任务分解和执行框架，可以自动将复杂任务拆分为可管理的小任务，并按照依赖关系执行它们。

## 主要功能

- **任务分析与拆分**：使用Claude分析复杂任务，将其拆解为结构化的子任务
- **依赖关系管理**：自动识别和处理子任务间的依赖关系
- **上下文管理**：追踪和传递任务执行过程中的上下文信息
- **并行任务执行**：支持并行执行无依赖关系的任务
- **任务状态智能分析**：使用Gemini模型分析任务完成状态
- **适应性执行**：根据任务状态分析结果动态调整执行流程

## 系统架构

系统由以下核心组件构成：

- **任务规划器(TaskPlanner)**：负责分析任务需求和拆分任务
- **任务执行器(TaskExecutor)**：负责执行具体子任务
- **上下文管理器(ContextManager)**：管理任务执行过程中的上下文
- **Claude集成**：提供任务执行的主要能力
- **Gemini集成**：提供任务状态的智能分析

## 快速开始

### 安装

确保系统已安装Python 3.8+，然后安装本项目：

```bash
# 从源码安装
git clone https://github.com/yourusername/task_planner.git
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
> # 仅进行任务规划
> task-planner plan "设计一个数据分析流程" 
> task-planner plan -f task.txt --output custom_output
> 
> # 执行已拆分的多个子任务（不进行规划）
> task-planner run-subtasks -f subtasks.json --logs-dir custom_logs
> ```

#### 使用预定义子任务

如果你已经有了任务拆分的结果，可以直接使用`run-subtasks`命令执行这些子任务：

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
from task_planner.core.context_management import ContextManager
from task_planner.core.task_decomposition_system import TaskDecompositionSystem

# 方法1: 使用完整的任务分解系统（规划者和执行者双层循环）
system = TaskDecompositionSystem()
result = system.execute_complex_task("我的复杂任务描述")

# 方法2: 分开使用规划器和执行器
# 初始化组件
context_manager = ContextManager()
planner = TaskPlanner("我的复杂任务描述", context_manager=context_manager)
executor = TaskExecutor(context_manager=context_manager, use_gemini=True)

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

- **task_planner/server/**: 服务器组件
  - `task_api_server.py`: API服务器
  - `task_visualization_server.py`: 可视化服务器
  - `task_monitor.py`: 任务监控

## 高级功能

### Gemini任务状态分析

系统集成了Google的Gemini模型，用于分析任务完成状态。详情请参阅[Gemini集成指南](Gemini集成指南.md)。

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

## 测试

系统使用pytest进行全面的测试，所有测试均已通过。详细的测试报告请查看[测试文档](README_TESTING.md)。

```bash
# 安装测试依赖
pip install pytest pytest-mock

# 运行所有测试 (已全部通过)
python -m pytest tests/ -v

# 运行核心组件测试
python -m pytest tests/test_context_manager.py tests/test_task_context.py tests/test_context_management.py tests/test_task_executor.py tests/test_task_planner.py -v

# 运行功能和集成测试
python -m pytest tests/test_basic_features.py tests/test_advanced_features.py tests/test_subsystem_integration.py -v

# 运行端到端测试
python -m pytest tests/test_end_to_end.py -v

# 运行新的V3重构测试（一次性执行所有测试）
python -m tests.test_v3.run_full_tests -v
```

### 测试覆盖范围

测试套件全面覆盖了系统的所有核心功能和组件，包括：

- **核心组件单元测试**: 测试各个组件的独立功能
  - TaskContext测试 (7/7)
  - ContextManager测试 (8/8)
  - TaskExecutor测试 (6/6)
  - TaskPlanner测试 (6/6)

- **集成测试和功能测试**: 测试组件间的交互和系统功能
  - 基本功能测试 (3/3)
  - 高级功能测试 (3/3)
  - 子系统集成测试 (4/4)
  - 端到端测试 (3/3)
  - 任务分解测试 (9/9)

- **V3重构测试套件**: 验证最新重构的系统功能
  - 基础路径处理测试 (5个测试用例)
  - 高级路径处理测试 (6个测试用例)
  - 边界条件和错误处理测试 (7个测试用例) 
  - 端到端集成流程测试 (2个测试用例)
  - 总计20个测试用例，全部通过

- **测试场景**:
  - 正常执行路径
  - 错误处理和恢复
  - 动态计划调整
  - 文件和数据传递
  - 多任务链式执行
  - 边界条件（空任务、超大输入等）
  - 异常情况（循环依赖、特殊字符等）

## 许可证

本项目采用MIT许可证 - 详情请参阅LICENSE文件。

## 致谢

感谢Claude和Gemini团队提供的强大模型支持。