"""
测试任务链中的文件依赖关系处理，特别是当前置任务文件缺失时的行为
"""

import os
import json
import pytest
import tempfile
from unittest.mock import patch, MagicMock
from task_planner.core.task_planner import TaskPlanner
from task_planner.core.task_executor import TaskExecutor
from task_planner.core.context_management import ContextManager

class TestFileDependencies:
    
    @pytest.fixture
    def setup_test_env(self):
        """设置测试环境"""
        # 创建临时目录
        temp_dir = tempfile.mkdtemp()
        
        # 创建上下文管理器
        context_manager = ContextManager(context_dir=temp_dir)
        
        # 创建规划者和执行者
        with patch('task_planner.core.task_planner.OpenAI'):
            planner = TaskPlanner("测试任务链", context_manager=context_manager)
        executor = TaskExecutor(context_manager=context_manager)
        
        return {
            "temp_dir": temp_dir,
            "context_manager": context_manager,
            "planner": planner,
            "executor": executor
        }
    
    @patch("task_planner.core.task_executor.claude_api")
    def test_task_chain_with_missing_files(self, mock_claude, setup_test_env):
        """测试当前置任务文件缺失时的任务链行为"""
        temp_dir = setup_test_env["temp_dir"]
        context_manager = setup_test_env["context_manager"]
        executor = setup_test_env["executor"]
        
        # 设置一个测试任务
        task = {
            "id": "task1",
            "name": "测试任务",
            "instruction": "测试文件缺失情况",
            "output_files": {
                "main_result": "results/task1/result.json",
                "data": "results/task1/data.csv"
            }
        }
        
        # 确保输出目录存在
        for output_type, output_path in task["output_files"].items():
            os.makedirs(os.path.join(temp_dir, os.path.dirname(output_path)), exist_ok=True)
        
        # 模拟任务执行但不创建文件（应该失败）
        mock_claude.return_value = {
            "status": "success",
            "output": "Task completed, but no files were created."
        }
        
        # 执行任务
        result = executor.execute_subtask(task)
        
        # 验证任务失败，且包含正确的错误信息
        assert result["success"] == False, "当文件缺失时任务应该失败"
        assert "error" in result, "结果中应包含错误字段"
        assert "缺失的文件" in result["error"], "错误消息应包含缺失文件提示"
        assert "main_result" in result["error"] or "result.json" in result["error"], "错误消息应包含缺失的主结果文件"
        assert "data" in result["error"] or "data.csv" in result["error"], "错误消息应包含缺失的数据文件"
    
    @patch("task_planner.core.task_executor.claude_api")
    def test_partial_file_dependencies(self, mock_claude, setup_test_env):
        """测试部分文件创建情况的处理"""
        temp_dir = setup_test_env["temp_dir"]
        executor = setup_test_env["executor"]
        
        # 设置一个测试任务
        task = {
            "id": "task1",
            "name": "测试任务",
            "instruction": "测试部分文件创建情况",
            "output_files": {
                "main_result": "results/task1/result.json",
                "data": "results/task1/data.csv"
            }
        }
        
        # 确保输出目录存在
        for output_type, output_path in task["output_files"].items():
            os.makedirs(os.path.join(temp_dir, os.path.dirname(output_path)), exist_ok=True)
        
        # 模拟任务执行但只创建部分文件
        mock_claude.return_value = {
            "status": "success",
            "output": "Task completed, but only created the result.json file."
        }
        
        # 手动创建第一个任务的 main_result 文件，但不创建 data 文件
        with open(os.path.join(temp_dir, "results/task1/result.json"), "w") as f:
            json.dump({"task_id": "task1", "success": True}, f)
        
        # 执行任务
        result = executor.execute_subtask(task)
        
        # 验证任务失败，因为没有创建所有文件
        assert result["success"] == False, "当部分文件缺失时任务应该失败"
        assert "error" in result, "结果中应包含错误字段"
        assert "缺失的文件" in result["error"], "错误消息应包含缺失文件提示"
        assert "data" in result["error"] or "data.csv" in result["error"], "错误消息应包含缺失的数据文件"
        assert "main_result" not in result["error"] and "result.json" not in result["error"], "错误消息不应包含已创建的文件"
    
    @patch("task_planner.core.task_executor.claude_api")
    def test_successful_file_dependencies(self, mock_claude, setup_test_env):
        """测试所有文件都成功创建的情况"""
        temp_dir = setup_test_env["temp_dir"]
        executor = setup_test_env["executor"]
        
        # 设置一个测试任务
        task = {
            "id": "task1",
            "name": "测试任务",
            "instruction": "测试所有文件创建成功的情况",
            "output_files": {
                "main_result": "results/task1/result.json",
                "data": "results/task1/data.csv"
            }
        }
        
        # 确保输出目录存在
        for output_type, output_path in task["output_files"].items():
            os.makedirs(os.path.join(temp_dir, os.path.dirname(output_path)), exist_ok=True)
        
        # 模拟任务执行并创建所有文件
        mock_claude.return_value = {
            "status": "success",
            "output": "Task completed successfully, all files created."
        }
        
        # 手动创建所有输出文件
        with open(os.path.join(temp_dir, "results/task1/result.json"), "w") as f:
            json.dump({"task_id": "task1", "success": True}, f)
        with open(os.path.join(temp_dir, "results/task1/data.csv"), "w") as f:
            f.write("id,value\n1,test\n2,test2")
        
        # 执行任务
        result = executor.execute_subtask(task)
        
        # 验证任务成功
        assert result["success"] == True, "当所有文件都创建时任务应该成功"
        assert "error" not in result, "成功的任务不应包含错误字段"