#!/usr/bin/env python3
"""
测试工具调用失败时的回退机制
"""

import os
import json
import unittest
from unittest.mock import patch, MagicMock, Mock
import sys
import asyncio
from time import sleep
from datetime import datetime

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.task_planner.core.task_executor import TaskExecutor
from src.task_planner.core.context_management import TaskContext

class ToolCallFailureError(Exception):
    """模拟工具调用失败的错误"""
    pass

class MockClaudeResponse:
    """模拟Claude响应的类"""
    
    def __init__(self, status="success", output="任务完成", task_status="CONTINUE"):
        self.status = status
        self.output = output
        self.task_status = task_status
    
    def __getitem__(self, key):
        if key == "status":
            return self.status
        elif key == "output":
            return self.output
        elif key == "task_status":
            return self.task_status
        elif key == "error_msg":
            return "错误信息"
        
        return None
        
    def get(self, key, default=None):
        value = self.__getitem__(key)
        return value if value is not None else default

class TestToolFallbackMechanism(unittest.TestCase):
    """测试工具调用失败时的回退机制"""
    
    def setUp(self):
        """测试前准备"""
        self.task_context = TaskContext("test_task_id")
        self.subtask = {
            "id": "test_task_id",
            "name": "测试任务",
            "instruction": "测试工具调用失败时的回退机制",
            "timeout": 30,
            "output_files": {
                "main_result": "/home/wangbo/document/wangbo/task_planner/output/task1_result.json"
            }
        }
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(self.subtask["output_files"]["main_result"]), exist_ok=True)
        
        # 创建TaskExecutor实例
        self.task_executor = TaskExecutor(timeout=30, verbose=True)
        
        # 不再尝试直接修改has_agent_tools，而是会在测试中模拟必要的工具调用
    
    @patch('task_planner.core.task_executor.claude_api')
    @patch('task_planner.core.task_executor.TaskExecutor._run_async_tool')
    @patch('task_planner.core.task_executor.has_agent_tools', True)
    def test_tool_call_failure_fallback(self, mock_run_async, mock_claude_api):
        """测试工具调用失败时会正确回退到API调用"""
        # 设置第一次工具调用失败
        mock_run_async.return_value = MagicMock(success=False, error="工具调用失败")
        
        # 设置API调用返回
        first_response = MockClaudeResponse(status="success", output="任务进行中", task_status="CONTINUE")
        second_response = MockClaudeResponse(status="success", output="任务完成", task_status="COMPLETED")
        mock_claude_api.side_effect = [first_response, second_response]
        
        # 执行任务
        result = self.task_executor.execute_subtask(self.subtask, self.task_context)
        
        # 验证结果
        self.assertTrue(result.get("success", False))
        self.assertEqual(mock_claude_api.call_count, 2)  # 应该调用了两次
        self.assertEqual(mock_run_async.call_count, 1)  # 工具尝试调用一次
        
        # 打印调试信息
        print(f"异步工具调用次数: {mock_run_async.call_count}")
        print(f"Claude API调用次数: {mock_claude_api.call_count}")
        print(f"最终任务状态: {result.get('success')}")
    
    @patch('task_planner.core.task_executor.claude_api')
    @patch('task_planner.core.task_executor.TaskExecutor._run_async_tool')
    def test_multiple_tool_call_failures(self, mock_run_async, mock_claude_api):
        """测试多次工具调用失败的情况"""
        # 设置工具调用抛出异常
        mock_run_async.side_effect = ToolCallFailureError("工具总是失败")
        
        # 设置claude_api调用的模拟响应
        first_response = MockClaudeResponse(status="success", output="任务进行中", task_status="CONTINUE")
        second_response = MockClaudeResponse(status="success", output="任务完成", task_status="COMPLETED")
        mock_claude_api.side_effect = [first_response, second_response]
        
        # 执行任务
        result = self.task_executor.execute_subtask(self.subtask, self.task_context)
        
        # 验证结果
        self.assertTrue(result.get("success", False))
        
        # 验证调用次数和错误处理
        self.assertEqual(mock_claude_api.call_count, 2)  # 应该调用了两次
        
        # 打印调试信息
        print(f"Claude API调用次数: {mock_claude_api.call_count}")
        print(f"最终任务状态: {result.get('success')}")
    
    @patch('task_planner.core.task_executor.claude_api')
    @patch('task_planner.core.task_executor.TaskExecutor._run_async_tool')
    def test_api_fallback_failure(self, mock_run_async, mock_claude_api):
        """测试API调用回退也失败的情况"""
        # 设置工具调用抛出异常
        mock_run_async.side_effect = ToolCallFailureError("工具总是失败")
        
        # 设置第一次claude_api调用返回CONTINUE状态
        first_response = MockClaudeResponse(status="success", output="任务进行中", task_status="CONTINUE")
        # 设置第二次claude_api调用失败
        mock_claude_api.side_effect = [
            first_response,
            Exception("API调用失败")
        ]
        
        # 执行任务 - 会捕获异常并返回错误结果
        result = self.task_executor.execute_subtask(self.subtask, self.task_context)
        
        # 验证结果
        self.assertFalse(result.get("success", True))
        self.assertIn("error", result)
        
        # 验证调用次数
        self.assertEqual(mock_claude_api.call_count, 2)  # 应该调用了两次
        
        # 打印调试信息
        print(f"Claude API调用次数: {mock_claude_api.call_count}")
        print(f"错误信息: {result.get('error')}")
    
    @patch('task_planner.core.task_executor.claude_api')
    @patch('os.path.exists')
    def test_task_status_tracking(self, mock_exists, mock_claude_api):
        """测试任务状态追踪和验证"""
        # 设置claude_api返回NEEDS_VERIFICATION状态
        response = MockClaudeResponse(status="success", output="任务验证中", task_status="NEEDS_VERIFICATION")
        mock_claude_api.return_value = response
        
        # 模拟文件验证通过
        def mock_exists_func(path):
            if path == self.subtask["output_files"]["main_result"]:
                return True
            return False
        
        mock_exists.side_effect = mock_exists_func
        
        # 执行任务
        result = self.task_executor.execute_subtask(self.subtask, self.task_context)
        
        # 验证结果
        self.assertTrue(result.get("success", False))
        self.assertEqual(mock_claude_api.call_count, 1)  # 应该只调用了一次
        
        # 打印调试信息
        print(f"Claude API调用次数: {mock_claude_api.call_count}")
        print(f"最终任务状态: {result.get('success')}")

        # 验证任务状态是否已从NEEDS_VERIFICATION更新为COMPLETED
        self.assertIn('task_status', self.task_context.local_context)
        if 'task_status' in self.task_context.local_context:
            self.assertEqual(self.task_context.local_context['task_status'], 'COMPLETED')

if __name__ == "__main__":
    unittest.main()