#!/usr/bin/env python3
"""
任务拆分与执行系统测试脚本
测试系统的各个组件和完整工作流程
"""

import os
import unittest
from unittest.mock import patch, MagicMock
import json
import tempfile
import shutil
from datetime import datetime

# 导入被测试的模块
from task_planner.core.context_management import TaskContext, ContextManager
from task_planner.core.task_planner import TaskPlanner
from task_planner.core.task_executor import TaskExecutor
from task_planner.core.task_decomposition_system import TaskDecompositionSystem

class TestTaskContext(unittest.TestCase):
    """测试TaskContext类的功能"""
    
    def setUp(self):
        """测试前的准备工作"""
        self.task_context = TaskContext("test_task")
        
    def test_update_context(self):
        """测试更新上下文功能"""
        # 更新全局上下文
        self.task_context.update_global("test_key", "test_value")
        self.assertEqual(self.task_context.global_context["test_key"], "test_value")
        
        # 更新本地上下文
        self.task_context.update_local("local_key", "local_value")
        self.assertEqual(self.task_context.local_context["local_key"], "local_value")
        
    def test_add_artifact(self):
        """测试添加工件功能"""
        # 添加代码工件
        code = "def test_function():\n    return 'Hello World'"
        self.task_context.add_artifact("test_code", code)
        
        # 验证工件是否正确添加
        self.assertIn("test_code", self.task_context.artifacts)
        self.assertEqual(self.task_context.artifacts["test_code"]["content"], code)
        self.assertIn("metadata", self.task_context.artifacts["test_code"])
        
        # 添加带元数据的工件
        metadata = {"type": "text", "format": "markdown"}
        self.task_context.add_artifact("test_doc", "# Test Document", metadata)
        
        # 验证元数据是否正确添加
        self.assertEqual(self.task_context.artifacts["test_doc"]["metadata"]["type"], "text")
        self.assertEqual(self.task_context.artifacts["test_doc"]["metadata"]["format"], "markdown")
        
    def test_execution_record(self):
        """测试执行记录功能"""
        # 添加执行记录
        self.task_context.add_execution_record("test_action", "test_result")
        
        # 验证记录是否正确添加
        self.assertEqual(len(self.task_context.execution_history), 1)
        self.assertEqual(self.task_context.execution_history[0]["action"], "test_action")
        self.assertEqual(self.task_context.execution_history[0]["result"], "test_result")
        
    def test_serialization(self):
        """测试序列化和反序列化功能"""
        # 准备测试数据
        self.task_context.update_global("global_key", "global_value")
        self.task_context.update_local("local_key", "local_value")
        self.task_context.add_artifact("test_artifact", "test_content")
        self.task_context.add_execution_record("test_action", "test_result")
        
        # 序列化
        serialized_data = self.task_context.serialize()
        
        # 反序列化
        reconstructed_context = TaskContext.deserialize(serialized_data)
        
        # 验证数据是否一致
        self.assertEqual(reconstructed_context.task_id, self.task_context.task_id)
        self.assertEqual(reconstructed_context.global_context, self.task_context.global_context)
        self.assertEqual(reconstructed_context.local_context, self.task_context.local_context)
        self.assertEqual(reconstructed_context.artifacts.keys(), self.task_context.artifacts.keys())
        self.assertEqual(len(reconstructed_context.execution_history), len(self.task_context.execution_history))
        

class TestContextManager(unittest.TestCase):
    """测试ContextManager类的功能"""
    
    def setUp(self):
        """测试前的准备工作"""
        self.temp_dir = tempfile.mkdtemp()
        self.context_manager = ContextManager(context_dir=self.temp_dir)
        
    def tearDown(self):
        """测试后的清理工作"""
        shutil.rmtree(self.temp_dir)
        
    def test_create_subtask_context(self):
        """测试创建子任务上下文功能"""
        # 创建父任务上下文
        parent_context = TaskContext("parent_task")
        parent_context.update_local("parent_key", "parent_value")
        self.context_manager.task_contexts["parent_task"] = parent_context
        
        # 创建子任务上下文
        subtask_context = self.context_manager.create_subtask_context("parent_task", "subtask_1")
        
        # 验证子任务上下文是否继承父任务上下文
        self.assertEqual(subtask_context.local_context["parent_key"], "parent_value")
        self.assertEqual(subtask_context.local_context["_parent_task_id"], "parent_task")
        
        # 验证子任务上下文是否被添加到管理器
        self.assertIn("subtask_1", self.context_manager.task_contexts)
        
    def test_update_task_context(self):
        """测试更新任务上下文功能"""
        # 创建任务上下文
        task_context = TaskContext("test_task")
        self.context_manager.task_contexts["test_task"] = task_context
        
        # 更新任务上下文
        update_data = {"key1": "value1", "key2": "value2"}
        self.context_manager.update_task_context("test_task", update_data)
        
        # 验证更新是否成功
        self.assertEqual(task_context.local_context["key1"], "value1")
        self.assertEqual(task_context.local_context["key2"], "value2")
        
        # 测试同时更新全局上下文
        self.context_manager.update_task_context("test_task", {"global_key": "global_value"}, update_global=True)
        
        # 验证全局上下文是否更新
        self.assertEqual(self.context_manager.global_context["global_key"], "global_value")
        
    def test_propagate_results(self):
        """测试结果传播功能"""
        # 创建源任务和目标任务上下文
        source_context = TaskContext("source_task")
        source_context.update_local("result_key", "result_value")
        source_context.add_artifact("source_artifact", "artifact_content")
        
        target_context = TaskContext("target_task")
        
        # 添加到管理器
        self.context_manager.task_contexts["source_task"] = source_context
        self.context_manager.task_contexts["target_task"] = target_context
        
        # 传播结果
        # 在实际实现中，默认不传递工件，需要显式指定
        artifact_keys = ["source_artifact"]
        self.context_manager.propagate_results("source_task", ["target_task"], 
                                              artifact_keys=artifact_keys)
        
        # 验证传播是否成功
        self.assertEqual(target_context.local_context["result_key"], "result_value")
        self.assertIn("source_artifact", target_context.artifacts)
        
    def test_get_execution_summary(self):
        """测试获取执行摘要功能"""
        # 创建任务上下文
        task_context = TaskContext("test_task")
        task_context.update_local("success", True)
        task_context.update_local("output", "test output")
        task_context.add_artifact("test_artifact", "artifact content")
        task_context.add_execution_record("test_action", "test_result")
        
        # 添加到管理器
        self.context_manager.task_contexts["test_task"] = task_context
        
        # 获取执行摘要
        summary = self.context_manager.get_execution_summary("test_task")
        
        # 验证摘要内容
        self.assertEqual(summary["task_id"], "test_task")
        self.assertEqual(summary["success"], True)
        self.assertEqual(summary["output"], "test output")
        self.assertEqual(summary["artifacts"], ["test_artifact"])
        # 根据实际实现，execution_events 可能是数量而不是列表
        self.assertEqual(summary["execution_events"], 1)
        

class TestTaskDecompositionSystem(unittest.TestCase):
    """测试任务拆分与执行系统整体功能"""
    
    def setUp(self):
        """测试前的准备工作"""
        self.temp_dir = tempfile.mkdtemp()
        
        # 创建模拟对象
        self.mock_planner = MagicMock(spec=TaskPlanner)
        self.mock_executor = MagicMock(spec=TaskExecutor)
        
        # 初始化系统
        self.system = TaskDecompositionSystem(logs_dir=self.temp_dir)
        
    def tearDown(self):
        """测试后的清理工作"""
        shutil.rmtree(self.temp_dir)
        
    def test_execute_complex_task(self):
        """测试复杂任务执行流程"""
        # 使用内联补丁来覆盖类内部创建的实例
        with patch('task_planner.core.task_decomposition_system.TaskPlanner') as mock_planner_class, \
             patch('task_planner.core.task_decomposition_system.TaskExecutor') as mock_executor_class:
            
            # 设置模拟对象的行为
            mock_planner = mock_planner_class.return_value
            mock_executor = mock_executor_class.return_value
            
            # 设置分析和拆分任务的返回值
            mock_planner.analyze_task.return_value = {"result": {"summary": "Task analysis"}}
            mock_planner.break_down_task.return_value = [
                {"id": "subtask_1", "name": "Subtask 1"},
                {"id": "subtask_2", "name": "Subtask 2"}
            ]
            
            # 设置获取下一个子任务的行为
            mock_planner.get_next_subtask.side_effect = [
                {"id": "subtask_1", "name": "Subtask 1"},
                {"id": "subtask_2", "name": "Subtask 2"},
                None  # 表示没有更多子任务
            ]
            
            # 设置执行子任务的返回值
            mock_executor.execute_subtask.return_value = {
                "task_id": "subtask_1",
                "success": True,
                "result": {
                    "summary": "Task executed successfully"
                }
            }
            
            # 设置任务完成状态
            mock_planner.is_complete.side_effect = [False, False, True]
            
            # 设置最终结果
            mock_planner.get_final_result.return_value = {
                "success": True,
                "result": {
                    "summary": "Complex task completed successfully"
                }
            }
            
            # 执行复杂任务
            task_description = "Test complex task"
            result = self.system.execute_complex_task(task_description)
            
            # 验证任务执行流程
            mock_planner_class.assert_called_once()
            mock_executor_class.assert_called_once()
            mock_planner.analyze_task.assert_called_once()
            mock_planner.break_down_task.assert_called_once()
            self.assertEqual(mock_planner.get_next_subtask.call_count, 2)
            self.assertEqual(mock_executor.execute_subtask.call_count, 2)
            self.assertEqual(mock_planner.process_result.call_count, 2)
            mock_planner.get_final_result.assert_called_once()
            
            # 验证返回结果
            self.assertEqual(result["success"], True)
            self.assertEqual(result["result"]["summary"], "Complex task completed successfully")


# 如果直接运行此脚本，执行所有测试
if __name__ == "__main__":
    unittest.main()