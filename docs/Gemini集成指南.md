# Gemini集成指南

## 概述

任务规划与执行系统现已集成Google的Gemini模型，用于增强任务完成状态的判断能力。通过Gemini分析器，系统可以更智能地判断Claude的任务执行是否完成，是否需要更多信息，或者是否应该继续执行。

## 功能特点

- **智能任务状态分析**：使用Gemini 2.0 Flash模型分析Claude的输出，判断任务完成状态
- **三种状态判断**：
  - `COMPLETED` - 任务已完成，无需更多交互
  - `NEEDS_MORE_INFO` - 需要用户提供更多信息才能继续
  - `CONTINUE` - 任务进行中但尚未完成
- **对话历史管理**：保存完整对话历史，支持上下文连贯的任务执行
- **全自动回退机制**：当Gemini不可用时自动回退到规则匹配方式

## 使用方法

### 环境准备

1. 确保已设置Gemini API密钥环境变量：

```bash
export GEMINI_API_KEY=your_gemini_api_key
```

2. 确保项目依赖已正确安装：

```bash
# 如果使用外部依赖方式
pip install google-generativeai

# 如果直接使用项目内置的vendor/claude_client
# 无需额外安装
```

### 代码示例

```python
from task_planner.core.task_executor import TaskExecutor
from task_planner.core.context_management import ContextManager

# 初始化上下文管理器
context_manager = ContextManager()

# 初始化任务执行器，启用Gemini分析
executor = TaskExecutor(
    context_manager=context_manager,
    use_gemini=True,  # 启用Gemini分析
    verbose=True
)

# 定义子任务
subtask = {
    "id": "data_analysis",
    "name": "数据分析",
    "description": "分析客户数据",
    "instruction": "请分析这份客户数据并提供洞察..."
}

# 执行子任务
result = executor.execute_subtask(subtask)

# 获取任务状态分析结果
task_status = result.get('task_status') 
print(f"任务状态: {task_status}")

# 根据任务状态采取不同的行动
if task_status == 'NEEDS_MORE_INFO':
    # 需要用户提供更多信息
    print("需要用户提供更多信息")
elif task_status == 'CONTINUE':
    # 任务未完成，需要继续
    print("任务未完成，需要继续")
elif task_status == 'COMPLETED':
    # 任务已完成
    print("任务已完成")
```

## 工作原理

1. 任务执行器将指令发送给Claude
2. Claude生成回复
3. 系统将Claude的回复发送给Gemini分析器
4. Gemini分析器评估回复内容，判断任务状态
5. 系统记录任务状态，并根据需要进行后续处理

## 架构说明

系统使用了多层回退机制：

1. 首先尝试从项目内部vendor目录导入需要的组件
2. 如果失败，尝试从外部依赖路径导入
3. 如果都失败，回退到常规的任务执行逻辑

这种设计确保了代码的可移植性和稳健性，使项目能够在不同环境中正常运行。

## 依赖说明

- **必须依赖**：
  - Python 3.8+
  - claude_client库（可以使用内置的vendor版本）

- **可选依赖**（使用Gemini分析器时）：
  - google-generativeai包
  - 有效的Gemini API密钥

## 常见问题

1. **Q: Gemini API密钥如何获取？**  
   A: 请访问[Google AI Studio](https://makersuite.google.com/)注册并获取API密钥

2. **Q: 如何确认Gemini分析器是否正常工作？**  
   A: 设置`verbose=True`，日志中会显示"任务状态分析: [状态]"的信息

3. **Q: 为什么我看不到任务状态分析结果？**  
   A: 请确认以下几点：
   - 是否设置了有效的Gemini API密钥
   - 是否启用了`use_gemini=True`参数
   - 检查导入路径是否正确