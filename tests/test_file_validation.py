"""
测试任务执行器文件验证逻辑 - 重构后的功能
"""

import os
import json
import pytest
from unittest.mock import patch, MagicMock
from task_planner.core.task_executor import TaskExecutor
from task_planner.core.context_management import TaskContext, ContextManager

class TestFileValidation:
    
    @pytest.fixture
    def setup_test_env(self, temp_dir):
        """设置测试环境"""
        context_dir = os.path.join(temp_dir, "test_validation")
        os.makedirs(context_dir, exist_ok=True)
        
        # 创建上下文管理器
        context_manager = ContextManager(context_dir=context_dir)
        
        # 创建执行器
        executor = TaskExecutor(context_manager=context_manager)
        
        return {
            "context_dir": context_dir,
            "context_manager": context_manager,
            "executor": executor
        }
    
    @patch("task_planner.core.task_executor.claude_api")
    def test_file_validation_logic(self, mock_claude, setup_test_env):
        """测试文件验证逻辑能否正确识别和报告缺失文件"""
        context_dir = setup_test_env["context_dir"]
        executor = setup_test_env["executor"]
        
        # 准备一个有多个输出文件的任务
        subtask = {
            "id": "validation_task",
            "name": "验证测试任务",
            "instruction": "测试文件验证逻辑",
            "output_files": {
                "main_result": "results/validation/result.json",
                "report": "results/validation/report.md"
            }
        }
        
        # 模拟Claude API成功返回但不创建文件
        mock_claude.return_value = {
            "status": "success",
            "output": "Task completed, but no files were created."
        }
        
        # 测试1：没有创建任何文件的情况
        result = executor.execute_subtask(subtask)
        
        # 验证任务失败并包含正确的错误信息
        assert result["success"] == False, "当文件缺失时任务应该失败"
        assert "error" in result, "结果中应包含错误字段"
        assert "任务执行失败" in result["error"], "错误消息应包含失败提示"
        assert "缺失的文件" in result["error"], "错误消息应包含缺失文件提示"
        assert "main_result" in result["error"] or "result.json" in result["error"], "错误消息应包含缺失的主结果文件"
        assert "report" in result["error"] or "report.md" in result["error"], "错误消息应包含缺失的报告文件"
        
        # 测试2：只创建部分文件的情况
        os.makedirs(os.path.join(context_dir, "results/validation"), exist_ok=True)
        with open(os.path.join(context_dir, "results/validation/result.json"), "w") as f:
            json.dump({"task_id": "validation_task", "success": True}, f)
        
        result = executor.execute_subtask(subtask)
        
        # 验证任务仍然失败，但错误消息中只包含未创建的文件
        assert result["success"] == False, "当部分文件缺失时任务应该失败"
        assert "缺失的文件" in result["error"], "错误消息应包含缺失文件提示"
        assert "report" in result["error"] or "report.md" in result["error"], "错误消息应包含缺失的报告文件"
        assert "main_result" not in result["error"] and "result.json" not in result["error"], "错误消息不应包含已创建的文件"
        
        # 测试3：创建所有文件的情况
        with open(os.path.join(context_dir, "results/validation/report.md"), "w") as f:
            f.write("# Test Report\nThis is a test report.")
        
        result = executor.execute_subtask(subtask)
        
        # 验证当所有文件都存在时，任务应该成功
        assert result["success"] == True, "当所有文件都已创建时任务应该成功"
        assert "error" not in result, "成功结果不应包含错误字段"
    
    @patch("task_planner.core.task_executor.claude_api")
    def test_no_placeholder_creation(self, mock_claude, setup_test_env):
        """测试执行器不再创建JSON占位符文件"""
        context_dir = setup_test_env["context_dir"]
        executor = setup_test_env["executor"]
        
        # 准备任务
        subtask = {
            "id": "placeholder_task",
            "name": "占位符测试任务",
            "instruction": "测试不创建占位符",
            "output_files": {
                "main_result": "results/placeholder/result.json"
            }
        }
        
        # 确保输出目录存在
        os.makedirs(os.path.join(context_dir, "results/placeholder"), exist_ok=True)
        
        # 模拟Claude API成功返回但不创建文件
        mock_claude.return_value = {
            "status": "success",
            "output": "Task completed but no file was created."
        }
        
        # 执行任务
        result = executor.execute_subtask(subtask)
        
        # 验证任务失败且没有创建占位符文件
        assert result["success"] == False, "当文件缺失时任务应该失败"
        assert not os.path.exists(os.path.join(context_dir, "results/placeholder/result.json")), "不应创建占位符文件"
    
    @patch("task_planner.core.task_executor.claude_api")
    def test_error_handling_no_placeholder(self, mock_claude, setup_test_env):
        """测试任务错误处理时不会创建占位符结果文件"""
        context_dir = setup_test_env["context_dir"]
        executor = setup_test_env["executor"]
        
        # 准备任务
        subtask = {
            "id": "error_task",
            "name": "错误处理测试任务",
            "instruction": "测试错误处理情况",
            "output_files": {
                "main_result": "results/error/result.json"
            }
        }
        
        # 确保输出目录存在
        os.makedirs(os.path.join(context_dir, "results/error"), exist_ok=True)
        
        # 模拟Claude API抛出异常
        mock_claude.side_effect = Exception("模拟执行错误")
        
        # 执行任务
        result = executor.execute_subtask(subtask)
        
        # 验证任务失败
        assert result["success"] == False, "当执行出错时任务应该失败"
        assert "error" in result, "结果中应包含错误字段"
        assert "模拟执行错误" in result["error"], "错误消息应包含原始错误信息"
        
        # 验证没有创建占位符JSON文件
        assert not os.path.exists(os.path.join(context_dir, "results/error/result.json")), "不应创建占位符文件"
        
        # 验证创建了错误日志文件
        logs_dir = os.path.join(context_dir, "logs")
        assert os.path.exists(logs_dir), "应该创建日志目录"
        error_logs = [f for f in os.listdir(logs_dir) if f.startswith("error_") and f.endswith(".log")]
        assert len(error_logs) > 0, "应该创建错误日志文件"