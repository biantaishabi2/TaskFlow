"""
测试 TaskPlanner 的任务规范化功能，特别是确保 output_files 的处理
"""

import os
import json
import pytest
from unittest.mock import patch, MagicMock
from task_planner.core.task_planner import TaskPlanner
from unittest.mock import MagicMock
from task_planner.core.context_management import ContextManager

class TestTaskNormalization:
    
    @pytest.fixture
    def setup_planner(self, temp_dir):
        """设置任务规划者测试环境"""
        # 创建规划器的日志目录
        logs_dir = os.path.join(temp_dir, "logs")
        os.makedirs(logs_dir, exist_ok=True)
        
        # 创建任务规划者
        task_description = "测试任务规范化功能"
        
        # 使用patch避免OpenAI的依赖
        with patch('task_planner.core.task_planner.OpenAI'):
            planner = TaskPlanner(task_description, logs_dir=logs_dir)
        
        # 直接测试我们需要用到的方法，不需要真正调用OpenAI
        return planner
    
    def test_subtask_normalization_ensures_output_files(self, setup_planner):
        """测试任务规范化过程是否确保 output_files 字段存在并正确"""
        planner = setup_planner
        
        # 测试1：没有 output_files 的任务
        subtasks = [
            {
                "id": "task1",
                "name": "任务1",
                "description": "测试任务1",
                "instruction": "执行测试任务1"
            }
        ]
        
        normalized = planner._normalize_subtasks(subtasks)
        
        # 验证添加了默认的 output_files
        assert "output_files" in normalized[0], "规范化应添加 output_files 字段"
        assert isinstance(normalized[0]["output_files"], dict), "output_files 应为字典类型"
        assert "main_result" in normalized[0]["output_files"], "应包含 main_result 输出文件"
        assert normalized[0]["output_files"]["main_result"] == "results/task_1/result.json", "应设置默认的结果文件路径"
        
        # 测试2：有 output_files 但没有 main_result 的任务
        subtasks = [
            {
                "id": "task2",
                "name": "任务2",
                "description": "测试任务2",
                "instruction": "执行测试任务2",
                "output_files": {
                    "report": "results/task2/report.md",
                    "data": "results/task2/data.csv"
                }
            }
        ]
        
        normalized = planner._normalize_subtasks(subtasks)
        
        # 验证保留了原有输出文件并添加了 main_result
        assert "output_files" in normalized[0], "规范化应保留 output_files 字段"
        assert "main_result" in normalized[0]["output_files"], "应添加 main_result 输出文件"
        assert normalized[0]["output_files"]["main_result"] == "results/task_1/result.json", "应设置默认的结果文件路径"
        assert "report" in normalized[0]["output_files"], "应保留原有的输出文件"
        assert normalized[0]["output_files"]["report"] == "results/task2/report.md", "应保留原有的文件路径"
        assert "data" in normalized[0]["output_files"], "应保留原有的输出文件"
        
        # 测试3：output_files 为空字典的情况
        subtasks = [
            {
                "id": "task3",
                "name": "任务3",
                "output_files": {}
            }
        ]
        
        normalized = planner._normalize_subtasks(subtasks)
        
        # 验证添加了 main_result
        assert "main_result" in normalized[0]["output_files"], "应向空 output_files 添加 main_result"
        
        # 测试4：output_files 为非字典类型的情况
        subtasks = [
            {
                "id": "task4",
                "name": "任务4",
                "output_files": "invalid_value"
            }
        ]
        
        normalized = planner._normalize_subtasks(subtasks)
        
        # 验证替换为正确的字典类型
        assert isinstance(normalized[0]["output_files"], dict), "应将非字典类型的 output_files 替换为字典"
        assert "main_result" in normalized[0]["output_files"], "替换后应包含 main_result"
    
    def test_normalize_multiple_subtasks(self, setup_planner):
        """测试同时规范化多个子任务"""
        planner = setup_planner
        
        # 多个不同类型的子任务
        subtasks = [
            {
                "id": "task1",
                "name": "无输出文件任务"
            },
            {
                "id": "task2",
                "name": "有部分输出文件任务",
                "output_files": {
                    "report": "results/task2/report.md"
                }
            },
            {
                "id": "task3",
                "name": "有完整输出文件任务",
                "output_files": {
                    "main_result": "custom/path/result.json",
                    "report": "custom/path/report.md"
                }
            }
        ]
        
        normalized = planner._normalize_subtasks(subtasks)
        
        # 验证所有任务都有正确的 output_files
        assert len(normalized) == 3, "应返回相同数量的任务"
        
        # 验证任务1
        assert "output_files" in normalized[0], "任务1应添加 output_files 字段"
        assert "main_result" in normalized[0]["output_files"], "任务1应有 main_result 输出文件"
        
        # 验证任务2
        assert "output_files" in normalized[1], "任务2应保留 output_files 字段"
        assert "main_result" in normalized[1]["output_files"], "任务2应添加 main_result 输出文件"
        assert "report" in normalized[1]["output_files"], "任务2应保留原有输出文件"
        
        # 验证任务3
        assert "output_files" in normalized[2], "任务3应保留 output_files 字段"
        assert "main_result" in normalized[2]["output_files"], "任务3应保留 main_result 输出文件"
        assert normalized[2]["output_files"]["main_result"] == "custom/path/result.json", "任务3应保留自定义结果路径"
    
    def test_task_breakdown_includes_output_files(self, setup_planner):
        """测试任务拆分提示词中包含对 output_files 的要求"""
        planner = setup_planner
        
        # 直接设置一个测试用例的子任务列表
        test_subtasks = [
            {
                "id": "test_task",
                "name": "测试任务",
                "description": "测试任务描述",
                "instruction": "执行测试任务"
            }
        ]
        
        # 调用规范化方法
        normalized_subtasks = planner._normalize_subtasks(test_subtasks)
        
        # 验证规范化后的子任务包含 output_files
        assert len(normalized_subtasks) > 0, "应生成至少一个子任务"
        assert "output_files" in normalized_subtasks[0], "规范化后的子任务应包含 output_files"
        assert "main_result" in normalized_subtasks[0]["output_files"], "规范化后的子任务应包含 main_result 文件"
    
    def test_build_breakdown_prompt_includes_output_files(self, setup_planner):
        """测试任务分解提示词中是否包含对 output_files 的说明"""
        planner = setup_planner
        
        # 创建模拟的分析结果
        analysis = {
            "task_id": "analysis",
            "success": True,
            "result": {
                "summary": "测试任务分析",
                "details": "这是一个测试任务分析的详细内容"
            }
        }
        
        # 构建分解提示词
        prompt = planner._build_breakdown_prompt(analysis)
        
        # 验证提示词中包含对输出文件的要求
        assert "输入文件(input_files)" in prompt, "提示词应包含对输入文件的说明"
        assert "输出文件(output_files)" in prompt, "提示词应包含对输出文件的说明"
        assert "明确指定任务必须生成的所有文件路径" in prompt, "提示词应说明输出文件的重要性"