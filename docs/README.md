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

### 基本用法

```python
from task_planner.core.task_planner import TaskPlanner
from task_planner.core.task_executor import TaskExecutor
from task_planner.core.context_management import ContextManager

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

## 主要模块说明

- **core/**: 核心功能模块
  - `task_planner.py`: 任务分析和拆分
  - `task_executor.py`: 任务执行
  - `context_management.py`: 上下文管理
  
- **distributed/**: 分布式和并行执行
  - `parallel_task_executor.py`: 并行任务执行
  - `distributed_task_decomposition_system.py`: 分布式任务拆分
  
- **util/**: 辅助工具
  - `claude_cli.py`: Claude命令行集成
  - `claude_task_bridge.py`: Claude任务桥接

- **vendor/**: 内置依赖
  - `claude_client/`: Claude客户端库
    - `agent_tools/`: 包含Gemini分析器等工具

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

## 许可证

本项目采用MIT许可证 - 详情请参阅LICENSE文件。

## 致谢

感谢Claude和Gemini团队提供的强大模型支持。