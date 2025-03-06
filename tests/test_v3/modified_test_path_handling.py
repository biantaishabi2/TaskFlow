"""
Tests for path handling enhancements (simplified version)
"""

import pytest
import os
import tempfile
from unittest.mock import patch, MagicMock

def test_absolute_path_handling(temp_dir):
    """测试绝对路径处理"""
    try:
        from task_planner.core.task_executor import TaskExecutor
        from task_planner.core.context_management import TaskContext
    except ImportError:
        pytest.skip("TaskExecutor或TaskContext不可用")
    
    # 创建执行器实例
    executor = TaskExecutor()
    
    # 创建测试文件路径
    absolute_path = os.path.join(temp_dir, "absolute.json")
    
    # 创建任务定义，使用绝对路径
    subtask = {
        "id": "absolute_path_test",
        "name": "绝对路径测试",
        "instruction": "测试绝对路径处理",
        "output_files": {
            "absolute_output": absolute_path
        }
    }
    
    # 创建任务上下文
    task_context = TaskContext(task_id="absolute_path_test")
    
    # 生成提示词
    prompt = executor._prepare_context_aware_prompt(subtask, task_context)
    
    # 检查提示词中是否包含绝对路径
    assert absolute_path in prompt
    
    # 检查提示内容
    assert "输出文件要求" in prompt