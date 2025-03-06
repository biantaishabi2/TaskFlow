"""
测试任务提示词生成逻辑 - 特别是关于文件创建的重要性强调
"""

import os
import pytest
from task_planner.core.task_executor import TaskExecutor
from task_planner.core.context_management import TaskContext, ContextManager

class TestPromptGeneration:
    
    @pytest.fixture
    def setup_test_env(self, temp_dir):
        """设置测试环境"""
        context_dir = os.path.join(temp_dir, "test_prompts")
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
    
    def test_prompt_includes_file_creation_emphasis(self, setup_test_env):
        """测试生成的提示词是否强调文件创建的重要性"""
        executor = setup_test_env["executor"]
        
        # 创建基本任务定义
        subtask = {
            "id": "prompt_test",
            "name": "提示词测试任务",
            "instruction": "执行测试任务，生成一些文件",
            "output_files": {
                "main_result": "results/prompt_test/result.json",
                "report": "results/prompt_test/report.md",
                "data": "results/prompt_test/data.csv"
            }
        }
        
        # 创建任务上下文
        task_context = TaskContext("prompt_test")
        
        # 生成提示词
        prompt = executor._prepare_context_aware_prompt(subtask, task_context)
        
        # 验证基础信息存在
        assert "任务：提示词测试任务" in prompt, "提示词应包含任务名称"
        assert "执行测试任务，生成一些文件" in prompt, "提示词应包含任务指令"
        
        # 验证文件输出部分存在
        assert "## 输出文件要求" in prompt, "提示词应包含输出文件要求部分"
        assert "你必须创建以下具体文件" in prompt, "提示词应明确要求创建文件"
        
        # 验证包含所有输出文件
        assert "main_result" in prompt or "result.json" in prompt, "提示词应包含结果文件"
        assert "report" in prompt or "report.md" in prompt, "提示词应包含报告文件"
        assert "data" in prompt or "data.csv" in prompt, "提示词应包含数据文件"
        
        # 验证重要性强调部分
        assert "重要提示" in prompt, "提示词应包含重要性强调部分"
        assert "你必须实际创建这些文件" in prompt, "提示词应强调实际创建文件"
        assert "任务的成功完全取决于这些文件是否被成功创建" in prompt, "提示词应强调文件创建与任务成功的关系"
        assert "如果任何一个文件未被创建，整个任务将被视为失败" in prompt, "提示词应强调缺失文件导致失败"
        assert "在回复中，请明确列出你已创建的每个文件的完整路径" in prompt, "提示词应要求列出创建的文件"
        assert "如果无法创建任何文件，请明确指出并解释原因" in prompt, "提示词应要求说明无法创建文件的原因"
    
    def test_prompt_format_with_different_output_types(self, setup_test_env):
        """测试不同输出文件类型的提示词格式"""
        executor = setup_test_env["executor"]
        
        # 创建带有复杂输出文件的任务
        subtask = {
            "id": "complex_outputs",
            "name": "复杂输出测试",
            "instruction": "测试复杂输出文件",
            "output_files": {
                "main_result": "results/complex/result.json",
                "visualization": "results/complex/chart.png",
                "source_code": "results/complex/script.py",
                "documentation": "results/complex/docs.md"
            }
        }
        
        # 创建任务上下文
        task_context = TaskContext("complex_outputs")
        
        # 生成提示词
        prompt = executor._prepare_context_aware_prompt(subtask, task_context)
        
        # 验证所有输出文件都在提示词中
        for output_type, file_path in subtask["output_files"].items():
            assert output_type in prompt or os.path.basename(file_path) in prompt, f"提示词应包含{output_type}输出文件"
        
        # 验证一致性强调
        assert prompt.count("如果任何一个文件未被创建，整个任务将被视为失败") == 1, "重要提示不应重复"
    
    def test_prompt_with_complex_context(self, setup_test_env):
        """测试上下文复杂情况下的提示词生成"""
        context_dir = setup_test_env["context_dir"]
        executor = setup_test_env["executor"]
        
        # 创建复杂任务
        subtask = {
            "id": "context_test",
            "name": "上下文测试",
            "instruction": "测试复杂上下文",
            "output_files": {
                "main_result": "results/context_test/result.json",
                "report": "results/context_test/report.md"
            },
            "input_files_mapping": {
                "previous_result": "results/prev_task/result.json",
                "reference_data": "data/reference.csv"
            },
            "dependencies": ["prev_task"]
        }
        
        # 创建复杂任务上下文
        task_context = TaskContext("context_test")
        
        # 添加进度信息
        task_context.update_local("progress", {
            "current_index": 2,
            "total_tasks": 5,
            "completed_tasks": ["task1", "prev_task"]
        })
        
        # 添加依赖结果
        task_context.update_local("dependency_results", {
            "prev_task": {
                "success": True,
                "result": {"summary": "前置任务成功完成"}
            }
        })
        
        # 模拟依赖文件
        os.makedirs(os.path.join(context_dir, "results/prev_task"), exist_ok=True)
        with open(os.path.join(context_dir, "results/prev_task/result.json"), "w") as f:
            f.write('{"success": true, "data": "测试数据"}')
        
        # 生成提示词
        prompt = executor._prepare_context_aware_prompt(subtask, task_context)
        
        # 验证基本要素
        assert "上下文测试" in prompt, "提示词应包含任务名称" 
        assert "输出文件要求" in prompt, "提示词应包含输出文件要求"
        assert "你必须创建以下具体文件" in prompt, "提示词应强调文件创建"
        
        # 验证重要性强调部分存在
        assert "重要提示" in prompt, "提示词应包含重要性强调部分"
        assert "任务的成功完全取决于这些文件是否被成功创建" in prompt, "提示词应强调文件创建的重要性"
        
        # 验证输入文件部分
        assert "## 输入文件" in prompt or "前置任务结果文件" in prompt, "提示词应包含输入文件信息"
        assert "previous_result" in prompt, "提示词应包含输入文件映射"