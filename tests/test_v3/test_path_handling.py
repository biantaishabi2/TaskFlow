"""
Tests for path handling enhancements
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
    
    # 检查提示词中是否包含正确的绝对路径
    assert absolute_path in prompt
    
    # 确保绝对路径描述正确
    assert "你必须创建以下具体文件（使用完整的绝对路径）" in prompt
    assert f"- absolute_output: {absolute_path}" in prompt

def test_relative_path_conversion(temp_dir):
    """测试相对路径转换"""
    try:
        from task_planner.core.task_executor import TaskExecutor
        from task_planner.core.context_management import TaskContext
    except ImportError:
        pytest.skip("TaskExecutor或TaskContext不可用")
    
    # 创建执行器实例
    executor = TaskExecutor()
    
    # 创建任务定义，使用相对路径
    subtask = {
        "id": "relative_path_test",
        "name": "相对路径测试",
        "instruction": "测试相对路径处理",
        "output_files": {
            "relative_output": "output/result.json"
        }
    }
    
    # 创建任务上下文
    task_context = TaskContext(task_id="relative_path_test")
    
    # 生成提示词
    prompt = executor._prepare_context_aware_prompt(subtask, task_context)
    
    # 检查提示词中的相对路径是否被转换为绝对路径
    current_dir = os.getcwd()
    expected_path = os.path.join(current_dir, "output/result.json")
    
    assert expected_path in prompt

def test_context_dir_path_handling(temp_dir):
    """测试上下文目录下路径处理"""
    try:
        from task_planner.core.task_executor import TaskExecutor
        from task_planner.core.context_management import ContextManager, TaskContext
    except ImportError:
        pytest.skip("TaskExecutor、ContextManager或TaskContext不可用")
    
    # 创建上下文管理器
    context_dir = os.path.join(temp_dir, "context")
    os.makedirs(context_dir, exist_ok=True)
    
    context_manager = MagicMock()
    context_manager.context_dir = context_dir
    
    # 创建执行器实例，使用自定义上下文管理器
    executor = TaskExecutor()
    executor.context_manager = context_manager
    
    # 创建任务定义，使用相对路径
    subtask = {
        "id": "context_path_test",
        "name": "上下文路径测试",
        "instruction": "测试上下文路径处理",
        "output_files": {
            "context_output": "result.json"
        }
    }
    
    # 创建任务上下文
    task_context = TaskContext(task_id="context_path_test")
    
    # 生成提示词
    prompt = executor._prepare_context_aware_prompt(subtask, task_context)
    
    # 检查提示词中的路径是否与上下文目录正确合并
    expected_path = os.path.join(context_dir, "result.json")
    assert expected_path in prompt

def test_path_verification(mock_claude_api, temp_dir, monkeypatch):
    """测试路径验证功能"""
    try:
        from task_planner.core.task_executor import TaskExecutor
    except ImportError:
        pytest.skip("TaskExecutor不可用")
    
    # 设置mock返回NEEDS_VERIFICATION状态
    mock_claude_api.return_value = {
        "status": "success",
        "output": "我已经完成了任务...",
        "error_msg": "",
        "task_status": "NEEDS_VERIFICATION"
    }
    
    # 创建嵌套的输出目录
    nested_dir = os.path.join(temp_dir, "nested", "path")
    os.makedirs(nested_dir, exist_ok=True)
    
    # 创建测试任务
    test_output_file = os.path.join(nested_dir, "nested_output.json")
    
    # 创建任务定义
    task = {
        "id": "path_verify_test",
        "name": "路径验证测试",
        "description": "测试嵌套路径验证功能",
        "output_files": {
            "nested_output": test_output_file
        }
    }
    
    # 创建原始的_process_direct_result方法的引用，稍后恢复
    original_process_result = TaskExecutor._process_direct_result
    
    def mock_process_result(self, response, subtask, task_context):
        """模拟结果处理，确保success状态与task_status一致"""
        result = original_process_result(self, response, subtask, task_context)
        # 如果task_status是ERROR，确保success为False
        if 'task_status' in response and response['task_status'] == "ERROR":
            result['success'] = False
        return result
        
    # 替换方法
    monkeypatch.setattr(TaskExecutor, '_process_direct_result', mock_process_result)
    
    # 执行任务 - 文件不存在的情况
    executor = TaskExecutor(verbose=True)
    result = executor.execute_subtask(task)
    
    # 验证结果应该失败，因为文件不存在
    assert result["success"] is False
    
    # 创建输出文件
    with open(test_output_file, 'w') as f:
        f.write('{"status": "success"}')
    
    # 重置mock返回值，保持NEEDS_VERIFICATION状态
    mock_claude_api.return_value = {
        "status": "success",
        "output": "我已经完成了任务...",
        "error_msg": "",
        "task_status": "NEEDS_VERIFICATION"
    }
    
    # 再次执行任务 - 文件存在的情况
    result = executor.execute_subtask(task)
    
    # 验证结果应该成功
    assert result["success"] is True

def test_multiple_output_files(mock_claude_api, temp_dir, monkeypatch):
    """测试多个输出文件处理"""
    try:
        from task_planner.core.task_executor import TaskExecutor
    except ImportError:
        pytest.skip("TaskExecutor不可用")
    
    # 设置mock返回NEEDS_VERIFICATION状态
    mock_claude_api.return_value = {
        "status": "success",
        "output": "我已经创建了所有文件...",
        "error_msg": "",
        "task_status": "NEEDS_VERIFICATION"
    }
    
    # 创建测试任务
    file1 = os.path.join(temp_dir, "output1.json")
    file2 = os.path.join(temp_dir, "output2.json")
    file3 = os.path.join(temp_dir, "output3.json")
    
    # 创建任务定义
    task = {
        "id": "multi_file_test",
        "name": "多文件测试",
        "description": "测试多个输出文件",
        "output_files": {
            "output1": file1,
            "output2": file2,
            "output3": file3
        }
    }
    
    # 创建原始的_process_direct_result方法的引用
    original_process_result = TaskExecutor._process_direct_result
    
    def mock_process_result(self, response, subtask, task_context):
        """模拟结果处理，确保success状态与task_status一致"""
        result = original_process_result(self, response, subtask, task_context)
        # 如果task_status是ERROR，确保success为False
        if 'task_status' in response and response['task_status'] == "ERROR":
            result['success'] = False
        return result
        
    # 替换方法
    monkeypatch.setattr(TaskExecutor, '_process_direct_result', mock_process_result)
    
    # 创建两个文件，留一个未创建
    with open(file1, 'w') as f:
        f.write('{"status": "success"}')
    
    with open(file2, 'w') as f:
        f.write('{"status": "success"}')
    
    # 执行任务 - 部分文件存在的情况
    executor = TaskExecutor(verbose=True)
    result = executor.execute_subtask(task)
    
    # 验证结果应该失败，因为有一个文件不存在
    assert result["success"] is False
    
    # 创建最后一个文件
    with open(file3, 'w') as f:
        f.write('{"status": "success"}')
    
    # 重置mock返回值，保持NEEDS_VERIFICATION状态
    mock_claude_api.return_value = {
        "status": "success",
        "output": "我已经创建了所有文件...",
        "error_msg": "",
        "task_status": "NEEDS_VERIFICATION"
    }
    
    # 再次执行任务 - 所有文件都存在的情况
    result = executor.execute_subtask(task)
    
    # 验证结果应该成功
    assert result["success"] is True