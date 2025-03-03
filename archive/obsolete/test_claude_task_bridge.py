#!/usr/bin/env python3
"""
Claude任务执行桥接模块测试
"""

import os
import json
import unittest
from unittest.mock import patch, MagicMock
from claude_task_bridge import TaskLLMBridge, TaskClaudeBridge

class TestTaskLLMBridge(unittest.TestCase):
    """测试TaskLLMBridge类"""
    
    def setUp(self):
        """测试前的准备工作"""
        self.bridge = TaskLLMBridge()
        self.task_context = {
            "task_id": "test_task",
            "task_type": "code_generation",
            "stage": "execution"
        }
        
    def test_with_task_context(self):
        """测试设置任务上下文"""
        result = self.bridge.with_task_context(self.task_context)
        
        # 检查任务上下文是否已设置
        self.assertEqual(self.bridge.task_context, self.task_context)
        # 检查返回值是否支持链式调用
        self.assertEqual(result, self.bridge)
        
    @patch.object(TaskLLMBridge, 'get_decision')
    def test_get_task_decision(self, mock_get_decision):
        """测试获取任务决策"""
        # 设置模拟返回值
        mock_get_decision.return_value = "y"
        
        # 设置任务上下文
        self.bridge.with_task_context(self.task_context)
        
        # 调用方法
        claude_output = "请确认是否继续？[y/n]"
        task_goal = "生成Python代码"
        result = self.bridge.get_task_decision(claude_output, task_goal)
        
        # 检查结果
        self.assertEqual(result, "y")
        # 检查是否调用了基础方法
        mock_get_decision.assert_called_once()
        # 检查调用参数
        args, kwargs = mock_get_decision.call_args
        self.assertEqual(args[0], claude_output)


class TestTaskClaudeBridge(unittest.TestCase):
    """测试TaskClaudeBridge类"""
    
    def setUp(self):
        """测试前的准备工作"""
        # 使用MagicMock模拟LLM桥接
        self.llm_bridge = MagicMock(spec=TaskLLMBridge)
        self.bridge = TaskClaudeBridge(llm_bridge=self.llm_bridge)
        
        # 设置测试任务上下文
        self.task_context = {
            "task_id": "test_task",
            "task_type": "code_generation",
            "context": {
                "language": "python",
                "requirements": ["计算斐波那契数列"]
            },
            "artifacts": {}
        }
        
    def test_create_task_enhanced_prompt(self):
        """测试创建增强版提示"""
        initial_prompt = "编写一个函数计算斐波那契数列"
        
        # 调用方法
        enhanced_prompt = self.bridge._create_task_enhanced_prompt(initial_prompt, self.task_context)
        
        # 检查结果是否包含必要元素
        self.assertIn("# 任务执行: test_task", enhanced_prompt)
        self.assertIn("## 任务指令", enhanced_prompt)
        self.assertIn(initial_prompt, enhanced_prompt)
        self.assertIn("## 任务上下文", enhanced_prompt)
        self.assertIn("python", enhanced_prompt)
        self.assertIn("## 输出格式要求", enhanced_prompt)
        self.assertIn("```json", enhanced_prompt)
        
    @patch.object(TaskClaudeBridge, '_parse_task_results')  
    def test_parse_task_results_with_json(self, mock_parse):
        """测试解析包含JSON的任务结果"""
        # 模拟交互记录
        interactions = [
            {"role": "user", "content": "测试提示", "timestamp": "2025-02-27 12:00:00"},
            {"role": "claude", "content": """
            这是任务执行的输出。
            
            ```json
            {
              "task_id": "test_task",
              "success": true,
              "result": {
                "summary": "成功计算斐波那契数列",
                "details": "详细结果"
              },
              "artifacts": {
                "python_code": "def fibonacci(n):\\n    a, b = 0, 1\\n    for _ in range(n):\\n        yield a\\n        a, b = b, a + b"
              },
              "next_steps": [
                "测试函数",
                "添加文档"
              ]
            }
            ```
            """, "timestamp": "2025-02-27 12:01:00"}
        ]
        
        # 设置mock返回值
        expected_result = {
            "task_id": "test_task",
            "success": True,
            "result": {
                "summary": "成功计算斐波那契数列",
                "details": "详细结果"
            },
            "artifacts": {
                "python_code": "def fibonacci(n):\n    a, b = 0, 1\n    for _ in range(n):\n        yield a\n        a, b = b, a + b"
            },
            "next_steps": [
                "测试函数",
                "添加文档"
            ]
        }
        mock_parse.return_value = expected_result
        
        # 调用方法
        result = self.bridge._parse_task_results(interactions, self.task_context)
        
        # 检查结果与mock返回值是否一致
        self.assertEqual(result, expected_result)
        self.assertEqual(result["task_id"], "test_task")
        self.assertEqual(result["success"], True)
        self.assertEqual(result["result"]["summary"], "成功计算斐波那契数列")
        self.assertIn("python_code", result["artifacts"])
        self.assertEqual(len(result["next_steps"]), 2)
        
    @patch.object(TaskClaudeBridge, '_parse_task_results')
    def test_parse_task_results_without_json(self, mock_parse):
        """测试解析不包含JSON的任务结果"""
        # 模拟交互记录
        interactions = [
            {"role": "user", "content": "测试提示", "timestamp": "2025-02-27 12:00:00"},
            {"role": "claude", "content": """
            这是任务执行的输出，没有JSON格式结果，但有代码块。
            
            ```python
            def fibonacci(n):
                a, b = 0, 1
                for _ in range(n):
                    yield a
                    a, b = b, a + b
            ```
            """, "timestamp": "2025-02-27 12:01:00"}
        ]
        
        # 设置mock返回值
        expected_result = {
            "task_id": "test_task",
            "success": True,
            "result": {
                "summary": "任务执行完成，发现了Python代码",
                "details": "任务生成了斐波那契数列函数"
            },
            "artifacts": {
                "python_code_1": "def fibonacci(n):\n    a, b = 0, 1\n    for _ in range(n):\n        yield a\n        a, b = b, a + b"
            }
        }
        mock_parse.return_value = expected_result
        
        # 调用方法
        result = self.bridge._parse_task_results(interactions, self.task_context)
        
        # 检查结果与mock返回值是否一致
        self.assertEqual(result, expected_result)
        self.assertEqual(result["task_id"], "test_task")
        self.assertEqual(result["success"], True)
        self.assertIn("python_code_1", result["artifacts"])
        self.assertEqual(
            result["artifacts"]["python_code_1"].strip(), 
            "def fibonacci(n):\n    a, b = 0, 1\n    for _ in range(n):\n        yield a\n        a, b = b, a + b"
        )
        
    @patch.object(TaskClaudeBridge, 'llm_controlled_session')
    def test_task_controlled_session(self, mock_session):
        """测试任务控制会话"""
        # 设置模拟返回值
        mock_interactions = [
            {"role": "user", "content": "测试提示", "timestamp": "2025-02-27 12:00:00"},
            {"role": "claude", "content": "这是Claude的输出", "timestamp": "2025-02-27 12:01:00"}
        ]
        mock_session.return_value = mock_interactions
        
        # 调用方法
        initial_prompt = "测试提示"
        result = self.bridge.task_controlled_session(initial_prompt, self.task_context)
        
        # 检查结果
        self.assertEqual(len(result), 3)  # 原始交互 + 结果
        self.assertEqual(result[0], mock_interactions[0])
        self.assertEqual(result[1], mock_interactions[1])
        self.assertEqual(result[2]["role"], "system")  # 额外添加的系统消息
        
        # 检查是否调用了基础方法
        mock_session.assert_called_once()
        # 检查调用是否包含增强版提示
        args, kwargs = mock_session.call_args
        self.assertIn("# 任务执行: test_task", args[0])


if __name__ == "__main__":
    unittest.main()