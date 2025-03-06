"""
Tests for the automatic continuation feature
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
import os
import tempfile

def test_continue_feature_with_toolmanager(mock_claude_api, mock_run_async_tool):
    """测试使用ToolManager实现的继续功能"""
    try:
        from task_planner.core.task_executor import TaskExecutor
    except ImportError:
        pytest.skip("TaskExecutor不可用")
    
    # 模拟claude_api返回CONTINUE状态
    mock_claude_api.return_value = {
        "status": "success",
        "output": "我开始处理任务，但需要继续...",
        "error_msg": "",
        "task_status": "CONTINUE"
    }
    
    # 设置mock_run_async_tool的返回值
    mock_result = MagicMock()
    mock_result.success = True
    mock_result.message = "工具执行成功"
    mock_result.response = "执行结果"
    mock_run_async_tool.return_value = mock_result
    
    # 创建执行器实例
    executor = TaskExecutor(verbose=True)
    
    # 创建测试任务
    task = {
        "id": "continue_test",
        "name": "自动继续测试",
        "instruction": "测试使用ToolManager的继续功能"
    }
    
    # 执行任务
    with patch.object(executor, '_verify_output_files', return_value=[]):
        result = executor.execute_subtask(task)
    
    # 验证工具被正确调用
    assert mock_run_async_tool.called
    
    # 最终结果应该仍然基于mock_claude_api的返回值
    assert "task_id" in result
    assert result["task_id"] == "continue_test"

def test_continue_fallback_mechanism(mock_claude_api):
    """测试当工具调用失败时可能的回退机制"""
    try:
        from task_planner.core.task_executor import TaskExecutor
    except ImportError:
        pytest.skip("TaskExecutor不可用")
    
    # 设置mock返回CONTINUE状态
    mock_claude_api.return_value = {
        "status": "success",
        "output": "我需要继续...",
        "error_msg": "",
        "task_status": "CONTINUE"
    }
    
    # 让_run_async_tool抛出异常，模拟工具调用失败
    def mock_run_async_tool_function(self, coro):
        raise Exception("工具调用失败")
    
    # 使用patch替换相关函数
    with patch.object(TaskExecutor, '_run_async_tool', mock_run_async_tool_function):
        
        # 创建执行器实例
        executor = TaskExecutor(verbose=True)
        
        # 创建测试任务
        task = {
            "id": "fallback_test",
            "name": "回退机制测试",
            "instruction": "测试工具调用失败时的回退机制"
        }
        
        # 执行任务
        with patch.object(executor, '_verify_output_files', return_value=[]):
            result = executor.execute_subtask(task)
        
        # 我们只验证工具调用失败时，执行不会中断
        assert "task_id" in result
        assert result["task_id"] == "fallback_test"

def test_multi_continue_scenario(mock_claude_api):
    """测试需要多次继续的场景"""
    try:
        from task_planner.core.task_executor import TaskExecutor
    except ImportError:
        pytest.skip("TaskExecutor不可用")
    
    # 模拟CONTINUE状态
    mock_claude_api.return_value = {
        "status": "success",
        "output": "部分处理...",
        "error_msg": "",
        "task_status": "CONTINUE"
    }
    
    # 让_run_async_tool直接成功
    tool_result = MagicMock()
    tool_result.success = True
    tool_result.message = "工具执行成功"
    
    def mock_run_async_tool(self, coro):
        return tool_result
    
    # 使用patch替换相关函数
    with patch.object(TaskExecutor, '_run_async_tool', mock_run_async_tool):
        
        # 创建执行器实例
        executor = TaskExecutor(verbose=True)
        
        # 创建测试任务
        task = {
            "id": "multi_continue_test",
            "name": "多次继续测试",
            "instruction": "测试需要多次继续的复杂任务"
        }
        
        # 使用spy记录_run_async_tool的调用次数
        with patch.object(executor, '_run_async_tool', wraps=mock_run_async_tool) as spy, \
             patch.object(executor, '_verify_output_files', return_value=[]):
            result = executor.execute_subtask(task)
        
        # 验证_run_async_tool至少被调用了一次
        assert spy.call_count >= 1
        
        # 验证任务ID正确
        assert result["task_id"] == "multi_continue_test"

def test_needs_more_info_status(mock_claude_api):
    """测试NEEDS_MORE_INFO状态处理"""
    try:
        from task_planner.core.task_executor import TaskExecutor
    except ImportError:
        pytest.skip("TaskExecutor不可用")
    
    # 设置mock返回NEEDS_MORE_INFO状态
    mock_claude_api.return_value = {
        "status": "success",
        "output": "我需要更多信息才能继续...",
        "error_msg": "",
        "task_status": "NEEDS_MORE_INFO"
    }
    
    # 创建执行器实例
    executor = TaskExecutor(verbose=True)
    
    # 创建测试任务
    task = {
        "id": "needs_more_info_test",
        "name": "需要更多信息测试",
        "instruction": "测试NEEDS_MORE_INFO状态"
    }
    
    # 执行任务
    with patch.object(executor, '_verify_output_files', return_value=[]):
        result = executor.execute_subtask(task)
    
    # 只需要验证任务ID正确
    assert "task_id" in result
    assert result["task_id"] == "needs_more_info_test"
    
    # 验证有结果或响应
    assert any(key in result for key in ["result", "response"])