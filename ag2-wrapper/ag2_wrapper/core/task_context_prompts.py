"""
任务上下文管理器

这个模块负责管理子任务之间的上下文传递，包括：
1. 定义上下文共享的方式和格式
2. 提供上下文文件的 JSON 模板
3. 生成上下文管理相关的提示词
4. 指导 LLM 如何维护和更新任务上下文文件

注意：这个模块与 ag2_context.py 不同，后者负责 AG2 执行器运行时的上下文管理。
本模块专注于任务之间的上下文传递。
"""

import os
import json
from typing import Dict, Any

def get_context_template(task_id: str, step_id: str) -> str:
    """
    获取任务上下文的JSON模板
    
    Args:
        task_id: 任务ID
        step_id: 步骤ID
        
    Returns:
        str: 格式化后的JSON模板
    """
    return f"""{{
  "task_id": "{task_id}",
  "step_id": "{step_id}",
  "global_context": {{}},
  "local_context": {{
    "status": "pending",
    "start_time": "",
    "end_time": "",
    "success": false,
    "output": "",
    "error": null,
    "conversation_history": [],
    "read_timestamps": {{}},
    "metrics": {{}}
  }},
  "file_paths": {{}},
  "execution_history": [],
  "base_dir": "",
  "artifacts": {{}}
}}"""

def get_context_prompt(task_id: str, step_id: str, parent_step_id: str = None) -> str:
    """
    生成上下文管理相关的提示词
    
    Args:
        task_id: 当前任务ID
        step_id: 当前步骤ID
        parent_step_id: 父步骤ID(可选)
        
    Returns:
        str: 格式化后的上下文管理提示词
    """
    return f'''## 上下文管理职责
你需要在执行任务的同时,维护当前步骤的上下文文件。上下文文件位于当前工作目录的.context子目录下:

1. 上下文文件路径约定: 
- 全局上下文: .context/global_context.json (只读)
- 当前步骤上下文: .context/task_{task_id}/step_{step_id}.json (可读写)
- 父步骤上下文: .context/task_{task_id}/step_{parent_step_id}.json (只读,如果存在)
- 上下文历史: .context/history.json (只读)

2. 当前步骤上下文文件结构:
{get_context_template(task_id, step_id)}

3. 更新上下文的时机:
- 步骤开始时:
  * 读取全局上下文和父步骤上下文(如果存在)
  * 创建当前步骤的上下文文件
  * 设置status为"running"
  * 记录start_time
  * 初始化conversation_history
- 执行过程中:
  * 只更新当前步骤的上下文文件
  * 更新conversation_history
  * 记录read_timestamps
  * 添加execution_history
  * 保存生成的artifacts
- 步骤完成时:
  * 设置status为"completed"
  * 记录end_time
  * 设置success状态
  * 保存output
- 发生错误时:
  * 设置status为"error"
  * 记录error信息

4. 使用Python代码读写上下文示例:
```python
import json
import os
from datetime import datetime

# 确保步骤目录存在
step_dir = f".context/task_{task_id}"
os.makedirs(step_dir, exist_ok=True)

# 读取全局上下文(只读)
with open(".context/global_context.json", "r") as f:
    global_context = json.load(f)

# 读取父步骤上下文(只读,如果存在)
parent_context = None
if "{parent_step_id}":
    parent_context_path = f"{step_dir}/step_{parent_step_id}.json"
    if os.path.exists(parent_context_path):
        with open(parent_context_path, "r") as f:
            parent_context = json.load(f)

# 创建或更新当前步骤的上下文
current_step_path = f"{step_dir}/step_{step_id}.json"
context = {{
    "task_id": "{task_id}",
    "step_id": "{step_id}",
    "global_context": global_context,
    "local_context": {{
        "status": "running",
        "start_time": datetime.now().isoformat(),
        "conversation_history": [],
        "parent_step_output": parent_context["local_context"]["output"] if parent_context else None
    }}
}}

# 写入当前步骤的上下文文件
with open(current_step_path, "w") as f:
    json.dump(context, f, indent=2, ensure_ascii=False)
```

5. 注意事项:
- 只能读取和修改当前步骤的上下文文件
- 不能修改全局上下文、父步骤上下文和历史文件
- 使用task_id和step_id构建文件路径
- 保持JSON格式的完整性和正确性
- 使用ensure_ascii=False确保正确处理中文
- 使用indent=2保持文件的可读性
- 时间戳使用ISO格式(datetime.now().isoformat())
- 文件操作要使用with语句确保正确关闭

你应该在步骤执行的关键节点维护当前步骤的上下文文件,确保执行状态和结果被正确记录。
可以读取父步骤的上下文来获取必要信息,但不能修改它。这样可以保持完整的执行历史记录。''' 