#!/usr/bin/env python3
"""
任务拆分与执行系统 - 上下文管理模块测试
"""

import os
import json
import unittest
from datetime import datetime
from task_planner.core.context_management import TaskContext, ContextManager

class TestTaskContext(unittest.TestCase):
    """测试TaskContext类"""
    
    def setUp(self):
        """测试前的准备工作"""
        self.task_id = "test_task_1"
        self.global_context = {"project": "test_project", "env": "test"}
        self.context = TaskContext(self.task_id, self.global_context)
        
    def test_init(self):
        """测试初始化"""
        self.assertEqual(self.context.task_id, self.task_id)
        self.assertEqual(self.context.global_context, self.global_context)
        self.assertEqual(self.context.local_context, {})
        self.assertEqual(self.context.artifacts, {})
        self.assertEqual(self.context.execution_history, [])
        
    def test_update_context(self):
        """测试更新上下文"""
        # 更新本地上下文
        self.context.update_local("test_key", "test_value")
        self.assertEqual(self.context.local_context["test_key"], "test_value")
        
        # 更新全局上下文
        self.context.update_global("global_key", "global_value")
        self.assertEqual(self.context.global_context["global_key"], "global_value")
        
    def test_add_artifact(self):
        """测试添加工件"""
        self.context.add_artifact("test_artifact", "test_content", {"type": "text"})
        
        # 检查工件是否已添加
        self.assertIn("test_artifact", self.context.artifacts)
        self.assertEqual(self.context.artifacts["test_artifact"]["content"], "test_content")
        self.assertEqual(self.context.artifacts["test_artifact"]["metadata"], {"type": "text"})
        self.assertIn("created_at", self.context.artifacts["test_artifact"])
        
    def test_add_execution_record(self):
        """测试添加执行记录"""
        self.context.add_execution_record("test_action", "test_result", {"detail": "test"})
        
        # 检查执行记录是否已添加
        self.assertEqual(len(self.context.execution_history), 1)
        record = self.context.execution_history[0]
        self.assertEqual(record["action"], "test_action")
        self.assertEqual(record["result"], "test_result")
        self.assertEqual(record["metadata"], {"detail": "test"})
        self.assertIn("timestamp", record)
        
    def test_serialize_deserialize(self):
        """测试序列化和反序列化"""
        # 添加一些数据
        self.context.update_local("test_key", "test_value")
        self.context.add_artifact("test_artifact", "test_content")
        self.context.add_execution_record("test_action", "test_result")
        
        # 序列化
        serialized = self.context.serialize()
        
        # 检查序列化结果
        self.assertEqual(serialized["task_id"], self.task_id)
        self.assertEqual(serialized["global_context"], self.global_context)
        self.assertEqual(serialized["local_context"]["test_key"], "test_value")
        self.assertEqual(len(serialized["execution_history"]), 1)
        
        # 反序列化
        new_context = TaskContext.deserialize(serialized)
        
        # 检查反序列化结果
        self.assertEqual(new_context.task_id, self.task_id)
        self.assertEqual(new_context.global_context, self.global_context)
        self.assertEqual(new_context.local_context["test_key"], "test_value")
        self.assertEqual(len(new_context.execution_history), 1)
        
    def test_save_load_file(self):
        """测试保存和加载文件"""
        # 添加一些数据
        self.context.update_local("test_key", "test_value")
        self.context.add_artifact("test_artifact", "test_content")
        
        # 保存到文件
        file_path = "/tmp/test_context.json"
        self.context.save_to_file(file_path)
        
        # 检查文件是否存在
        self.assertTrue(os.path.exists(file_path))
        
        # 从文件加载
        loaded_context = TaskContext.load_from_file(file_path)
        
        # 检查加载结果
        self.assertEqual(loaded_context.task_id, self.task_id)
        self.assertEqual(loaded_context.global_context, self.global_context)
        self.assertEqual(loaded_context.local_context["test_key"], "test_value")
        
        # 清理文件
        os.remove(file_path)


class TestContextManager(unittest.TestCase):
    """测试ContextManager类"""
    
    def setUp(self):
        """测试前的准备工作"""
        self.context_dir = "/tmp/test_contexts"
        self.manager = ContextManager(self.context_dir)
        
        # 创建一个父任务上下文
        self.parent_task_id = "parent_task"
        self.manager.task_contexts[self.parent_task_id] = TaskContext(self.parent_task_id)
        self.manager.task_contexts[self.parent_task_id].update_local("parent_key", "parent_value")
        self.manager.task_contexts[self.parent_task_id].add_artifact("parent_artifact", "parent_content")
        
    def tearDown(self):
        """测试后的清理工作"""
        # 清理测试目录
        if os.path.exists(self.context_dir):
            # 递归删除目录及其内容
            import shutil
            shutil.rmtree(self.context_dir)
    
    def test_create_subtask_context(self):
        """测试创建子任务上下文"""
        # 完全继承
        subtask_id = "subtask_1"
        subtask_context = self.manager.create_subtask_context(self.parent_task_id, subtask_id)
        
        # 检查继承结果
        self.assertEqual(subtask_context.task_id, subtask_id)
        self.assertEqual(subtask_context.local_context["parent_key"], "parent_value")
        self.assertEqual(subtask_context.local_context["_parent_task_id"], self.parent_task_id)
        
        # 部分继承
        subtask_id2 = "subtask_2"
        subtask_context2 = self.manager.create_subtask_context(
            self.parent_task_id, 
            subtask_id2,
            context_subset=["parent_key"]
        )
        
        # 检查部分继承结果
        self.assertEqual(subtask_context2.task_id, subtask_id2)
        self.assertEqual(subtask_context2.local_context["parent_key"], "parent_value")
        
    def test_update_task_context(self):
        """测试更新任务上下文"""
        # 创建一个测试任务
        task_id = "test_task"
        self.manager.task_contexts[task_id] = TaskContext(task_id)
        
        # 更新任务上下文
        update_data = {"key1": "value1", "key2": "value2"}
        self.manager.update_task_context(task_id, update_data)
        
        # 检查更新结果
        context = self.manager.task_contexts[task_id]
        self.assertEqual(context.local_context["key1"], "value1")
        self.assertEqual(context.local_context["key2"], "value2")
        
        # 更新全局上下文
        self.manager.update_task_context(task_id, {"global_key": "global_value"}, update_global=True)
        
        # 检查全局上下文更新
        self.assertEqual(self.manager.global_context["global_key"], "global_value")
        self.assertEqual(context.global_context["global_key"], "global_value")
        
    def test_propagate_results(self):
        """测试传播结果"""
        # 创建源任务和目标任务
        source_id = "source_task"
        target_id = "target_task"
        
        self.manager.task_contexts[source_id] = TaskContext(source_id)
        self.manager.task_contexts[target_id] = TaskContext(target_id)
        
        # 添加源任务数据
        source_context = self.manager.task_contexts[source_id]
        source_context.update_local("result_key", "result_value")
        source_context.add_artifact("result_artifact", "artifact_content")
        
        # 传播结果，包括工件
        self.manager.propagate_results(source_id, [target_id], artifact_keys=["result_artifact"])
        
        # 检查传播结果
        target_context = self.manager.task_contexts[target_id]
        self.assertEqual(target_context.local_context["result_key"], "result_value")
        self.assertIn("result_artifact", target_context.artifacts)
        
        # 测试选择性传播
        target_id2 = "target_task2"
        self.manager.task_contexts[target_id2] = TaskContext(target_id2)
        
        # 只传播上下文，不传播工件
        self.manager.propagate_results(source_id, [target_id2], keys=["result_key"], artifact_keys=[])
        
        # 检查选择性传播结果
        target_context2 = self.manager.task_contexts[target_id2]
        self.assertEqual(target_context2.local_context["result_key"], "result_value")
        self.assertNotIn("result_artifact", target_context2.artifacts)  # 没有传播工件
        
    def test_get_execution_summary(self):
        """测试获取执行摘要"""
        # 创建测试任务
        task_id = "summary_task"
        self.manager.task_contexts[task_id] = TaskContext(task_id)
        
        # 添加任务数据
        context = self.manager.task_contexts[task_id]
        context.update_local("success", True)
        context.update_local("output", "Task output")
        context.add_artifact("summary_artifact", "artifact_content")
        context.add_execution_record("test_action", "test_result")
        
        # 获取执行摘要
        summary = self.manager.get_execution_summary(task_id)
        
        # 检查摘要内容
        self.assertEqual(summary["task_id"], task_id)
        self.assertEqual(summary["success"], True)
        self.assertEqual(summary["output"], "Task output")
        self.assertEqual(summary["artifacts"], ["summary_artifact"])
        self.assertEqual(summary["execution_events"], 1)
        
    def test_save_load_all_contexts(self):
        """测试保存和加载所有上下文"""
        # 添加一些测试数据
        self.manager.global_context["global_key"] = "global_value"
        
        task_id = "save_load_task"
        self.manager.task_contexts[task_id] = TaskContext(task_id)
        self.manager.task_contexts[task_id].update_local("local_key", "local_value")
        
        # 保存所有上下文
        self.manager.save_all_contexts()
        
        # 创建新的管理器并加载
        new_manager = ContextManager(self.context_dir)
        new_manager.load_all_contexts()
        
        # 检查加载结果
        self.assertEqual(new_manager.global_context["global_key"], "global_value")
        self.assertIn(task_id, new_manager.task_contexts)
        self.assertEqual(new_manager.task_contexts[task_id].local_context["local_key"], "local_value")


if __name__ == "__main__":
    unittest.main()