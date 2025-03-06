"""
Tests for TaskExecutor with improved path handling and status validation
"""

import pytest
import os
import json
import tempfile
from unittest.mock import patch, MagicMock

def test_task_execution_with_gemini_status(mock_claude_api, mock_gemini, test_task_definition):
    """测试使用Gemini进行任务状态判断的执行流程"""
    try:
        from task_planner.core.task_executor import TaskExecutor
        from task_planner.core.context_management import TaskContext
    except ImportError:
        pytest.skip("TaskExecutor或TaskContext不可用")
        
    # 设置mock返回
    mock_claude_api.return_value = {
        "status": "success",
        "output": "我已经完成了任务...",
        "error_msg": "",
        "task_status": "COMPLETED"
    }
    
    # 创建执行器实例，默认使用Gemini
    executor = TaskExecutor(verbose=True)
    
    # 执行任务
    result = executor.execute_subtask(test_task_definition)
    
    # 验证结果包含预期的字段
    assert "success" in result
    assert "task_id" in result
    assert result["task_id"] == "test_task_1"
    assert result["success"] is True

def test_needs_verification_status(mock_claude_api, mock_gemini, temp_dir):
    """测试NEEDS_VERIFICATION状态和文件验证"""
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
    
    # 创建测试任务
    test_output_file = os.path.join(temp_dir, "test_output.json")
    
    # 创建任务定义
    task = {
        "id": "verify_test",
        "name": "验证测试",
        "description": "测试文件验证功能",
        "output_files": {
            "main_output": test_output_file
        }
    }
    
    # 执行任务 - 文件不存在的情况
    executor = TaskExecutor(verbose=True)
    result = executor.execute_subtask(task)
    
    # 验证结果应该失败，因为文件不存在
    assert result["success"] is False
    assert "未能创建预期的输出文件" in result.get("error", "")
    
    # 创建输出文件
    with open(test_output_file, 'w') as f:
        f.write('{"status": "success"}')
    
    # 再次执行任务 - 文件存在的情况
    result = executor.execute_subtask(task)
    
    # 验证结果应该成功
    assert result["success"] is True

def test_prepare_context_aware_prompt():
    """测试_prepare_context_aware_prompt方法的路径处理"""
    try:
        from task_planner.core.task_executor import TaskExecutor
        from task_planner.core.context_management import TaskContext
    except ImportError:
        pytest.skip("TaskExecutor或TaskContext不可用")
    
    # 创建执行器实例
    executor = TaskExecutor()
    
    # 创建任务定义，使用相对路径
    subtask = {
        "id": "path_test",
        "name": "路径测试",
        "instruction": "测试路径处理",
        "output_files": {
            "relative_output": "relative/path/output.json",
            "absolute_output": "/tmp/absolute/path/output.json"
        }
    }
    
    # 创建任务上下文
    task_context = TaskContext(task_id="path_test")
    
    # 生成提示词
    prompt = executor._prepare_context_aware_prompt(subtask, task_context)
    
    # 检查提示词是否包含工作目录信息
    assert "当前工作目录:" in prompt
    
    # 检查提示词是否包含绝对路径
    assert "你必须创建以下具体文件（使用完整的绝对路径）" in prompt
    
    # 检查提示词中的相对路径是否被转换为绝对路径
    current_dir = os.getcwd()
    expected_path = os.path.join(current_dir, "relative/path/output.json")
    
    # 检查相对路径是否被转换为绝对路径，绝对路径是否保持不变
    assert expected_path in prompt
    assert "/tmp/absolute/path/output.json" in prompt
    
    # 检查重要提示
    assert "使用完整的绝对路径" in prompt
    assert "不要尝试使用相对路径" in prompt

def test_verify_output_files(temp_dir):
    """测试输出文件验证功能"""
    try:
        from task_planner.core.task_executor import TaskExecutor
    except ImportError:
        pytest.skip("TaskExecutor不可用")
    
    # 创建执行器实例
    executor = TaskExecutor()
    
    # 创建任务定义
    test_file1 = os.path.join(temp_dir, "exists.json")
    test_file2 = os.path.join(temp_dir, "not_exists.json")
    
    # 创建第一个文件
    with open(test_file1, 'w') as f:
        f.write('{"test": true}')
    
    # 创建任务定义，包含两个文件
    task = {
        "id": "file_verify_test",
        "output_files": {
            "exists": test_file1,
            "not_exists": test_file2
        }
    }
    
    # 验证文件
    missing_files = executor._verify_output_files(task)
    
    # 应该只有一个缺失的文件
    assert len(missing_files) == 1
    assert test_file2 in missing_files
    
    # 创建第二个文件
    with open(test_file2, 'w') as f:
        f.write('{"test": true}')
    
    # 再次验证
    missing_files = executor._verify_output_files(task)
    
    # 应该没有缺失的文件
    assert len(missing_files) == 0

@pytest.mark.asyncio
async def test_continue_on_incomplete_task(mock_tool_execution):
    """测试任务未完成时的自动继续功能"""
    # 使用mock模拟CONTINUE状态和后续调用
    try:
        from task_planner.core.task_executor import TaskExecutor
    except ImportError:
        pytest.skip("TaskExecutor不可用")
    
    # 创建模拟的claude_api函数，第一次返回CONTINUE状态，第二次返回COMPLETED
    mock_responses = [
        {
            "status": "success",
            "output": "我开始处理任务...",
            "error_msg": "",
            "task_status": "CONTINUE"
        },
        {
            "status": "success",
            "output": "任务已完成",
            "error_msg": "",
            "task_status": "COMPLETED"
        }
    ]
    
    mock_claude_api = MagicMock(side_effect=mock_responses)
    
    # 使用patch替换真实的claude_api
    with patch('task_planner.core.task_executor.claude_api', mock_claude_api):
        # 创建执行器实例
        executor = TaskExecutor(verbose=True)
        
        # 创建测试任务
        task = {
            "id": "test_continue",
            "name": "自动继续测试",
            "instruction": "创建一个需要多次交互的任务"
        }
        
        # 执行任务
        result = executor.execute_subtask(task)
        
        # 验证claude_api被调用了两次
        assert mock_claude_api.call_count == 2
        
        # 第二次调用应该包含"继续"的消息
        second_call_args = mock_claude_api.call_args_list[1][0]
        assert "继续" in second_call_args[0].lower()
        
        # 验证最终结果是成功的
        assert result["success"] is True

def test_timeout_handling():
    """测试超时处理机制"""
    try:
        from task_planner.core.task_executor import TaskExecutor
    except ImportError:
        pytest.skip("TaskExecutor不可用")
    
    # 模拟claude_api超时
    def mock_timeout(*args, **kwargs):
        raise TimeoutError("操作超时")
    
    with patch('task_planner.core.task_executor.claude_api', side_effect=mock_timeout):
        # 创建执行器实例，设置短超时
        executor = TaskExecutor(timeout=1, verbose=True)
        
        # 创建一个简单任务
        task = {
            "id": "timeout_test",
            "name": "超时测试",
            "instruction": "测试超时处理"
        }
        
        # 执行任务
        result = executor.execute_subtask(task)
        
        # 验证结果包含超时信息
        assert result["success"] is False
        assert "超时" in result.get("error", "").lower() or "timeout" in result.get("error", "").lower()

def test_error_recovery():
    """测试在发生错误时的恢复机制"""
    # 这是一个简单的恢复测试，模拟执行过程中的错误
    try:
        from task_planner.core.task_executor import TaskExecutor
    except ImportError:
        pytest.skip("TaskExecutor不可用")
    
    # 设置mock以模拟错误和恢复
    side_effects = [
        Exception("模拟错误"),  # 第一次调用抛出异常
        {  # 第二次调用正常返回
            "status": "success",
            "output": "恢复后的执行",
            "error_msg": "",
            "task_status": "COMPLETED"
        }
    ]
    
    mock_claude_api = MagicMock(side_effect=side_effects)
    
    with patch('task_planner.core.task_executor.claude_api', mock_claude_api):
        # 创建执行器实例，启用重试
        executor = TaskExecutor(verbose=True, max_retries=1)
        
        # 创建测试任务
        task = {
            "id": "error_recovery_test",
            "name": "错误恢复测试",
            "instruction": "测试错误恢复机制"
        }
        
        # 执行任务
        result = executor.execute_subtask(task)
        
        # 验证最终结果是成功的
        assert result["success"] is True
        
        # 验证重试机制被触发
        assert mock_claude_api.call_count == 2