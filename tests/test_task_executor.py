"""
测试TaskExecutor类的功能
"""

import pytest
import os
import json
import tempfile
from unittest.mock import patch, MagicMock, mock_open
from task_planner.core.task_executor import TaskExecutor
from task_planner.core.context_management import TaskContext, ContextManager

class MockClaudeResponse:
    """模拟Claude API响应"""
    def __init__(self, content, status="success", error_msg=None, task_status=None):
        self.response = {
            "status": status,
            "output": content,
            "error_msg": error_msg,
            "duration": 1.2
        }
        if task_status:
            self.response["task_status"] = task_status
        
    def __getitem__(self, key):
        return self.response.get(key)
        
    def get(self, key, default=None):
        return self.response.get(key, default)

# 模拟Claude API调用
def mock_claude_api(prompt, **kwargs):
    """模拟Claude API调用"""
    # 返回成功的响应
    return {
        "status": "success",
        "output": """任务执行成功！

以下是执行结果的JSON格式：

```json
{
  "task_id": "test_task",
  "success": true,
  "result": {
    "summary": "任务执行成功",
    "details": "任务已完成所有要求的处理"
  },
  "artifacts": {
    "report": "path/to/report.md"
  },
  "next_steps": ["验证结果", "继续下一步"]
}
```

我还生成了以下文件：

report.md：
```
# 任务报告
这是一个测试报告文件
```
""",
        "duration": 1.5
    }

class TestTaskExecutor:
    
    @pytest.fixture
    def setup_executor(self, temp_dir):
        """设置TaskExecutor测试环境"""
        # 创建上下文目录
        context_dir = os.path.join(temp_dir, "context")
        os.makedirs(context_dir, exist_ok=True)
        os.makedirs(os.path.join(context_dir, "results"), exist_ok=True)
        
        # 创建上下文管理器
        context_manager = ContextManager(context_dir)
        
        # 创建任务执行器
        executor = TaskExecutor(context_manager=context_manager, verbose=False, use_gemini=False)
        
        return {
            "executor": executor,
            "context_manager": context_manager,
            "context_dir": context_dir
        }
    
    @patch("task_planner.core.task_executor.claude_api", side_effect=mock_claude_api)
    def test_execute_subtask_basic(self, mock_claude, setup_executor):
        """测试基本子任务执行功能"""
        executor = setup_executor["executor"]
        context_manager = setup_executor["context_manager"]
        context_dir = setup_executor["context_dir"]
        
        # 创建子任务定义
        subtask = {
            "id": "test_task",
            "name": "测试任务",
            "instruction": "这是一个测试任务，请执行并返回结果",
            "output_files": {
                "main_result": os.path.join(context_dir, "results/test_task/result.json"),
                "report": os.path.join(context_dir, "results/test_task/report.md")
            },
            "success_criteria": ["执行成功"]
        }
        
        # 创建任务上下文
        context_manager.create_subtask_context("planner", "test_task")
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(subtask["output_files"]["main_result"]), exist_ok=True)
        
        # 执行子任务
        result = executor.execute_subtask(subtask)
        
        # 验证执行结果
        assert result["task_id"] == "test_task"
        assert result["success"] is True
        assert "result" in result
        assert result["result"]["summary"] == "任务执行成功"
        assert "next_steps" in result
        
        # 验证结果文件创建
        assert os.path.exists(subtask["output_files"]["main_result"])
        
        # 验证上下文更新
        task_context = context_manager.task_contexts["test_task"]
        assert task_context.local_context["success"] is True
        assert "output_main_result" in task_context.file_paths
        
        # 验证执行历史记录
        records = [r for r in task_context.execution_history if r["action"] == "execution_completed"]
        assert len(records) > 0

    @patch("task_planner.core.task_executor.claude_api")
    def test_execute_subtask_with_error(self, mock_claude, setup_executor):
        """测试子任务执行出错的情况"""
        executor = setup_executor["executor"]
        context_manager = setup_executor["context_manager"]
        context_dir = setup_executor["context_dir"]
        
        # 模拟Claude API出错
        mock_claude.return_value = {
            "status": "error",
            "error_msg": "模拟的API错误",
            "output": "",
            "duration": 0.5
        }
        
        # 创建子任务定义
        subtask = {
            "id": "error_task",
            "name": "错误测试任务",
            "instruction": "这个任务会失败",
            "output_files": {
                "main_result": os.path.join(context_dir, "results/error_task/result.json")
            }
        }
        
        # 创建任务上下文
        context_manager.create_subtask_context("planner", "error_task")
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(subtask["output_files"]["main_result"]), exist_ok=True)
        
        # 执行子任务
        result = executor.execute_subtask(subtask)
        
        # 验证执行结果
        assert result["task_id"] == "error_task"
        assert result["success"] is False
        assert "error" in result
        assert result["error"] == "模拟的API错误"
        
        # 验证错误结果文件创建
        assert os.path.exists(subtask["output_files"]["main_result"])
        
        # 验证上下文更新
        task_context = context_manager.task_contexts["error_task"]
        assert "claude_response" in task_context.local_context
        
        # 验证执行历史记录
        records = [r for r in task_context.execution_history if r["action"] == "claude_execution_failed"]
        assert len(records) > 0

    @patch("task_planner.core.task_executor.claude_api")
    def test_json_extraction(self, mock_claude, setup_executor):
        """测试从Claude响应中提取JSON结果"""
        executor = setup_executor["executor"]
        context_manager = setup_executor["context_manager"]
        
        # 模拟Claude API返回JSON结果
        mock_claude.return_value = {
            "status": "success",
            "output": """
执行任务...

```json
{
  "task_id": "json_task",
  "success": true,
  "result": {
    "summary": "JSON提取测试成功",
    "details": "成功从Claude响应中提取JSON"
  },
  "data": {
    "key1": "value1",
    "key2": "value2"
  }
}
```
            """,
            "duration": 1.0
        }
        
        # 创建子任务定义
        subtask = {
            "id": "json_task",
            "name": "JSON测试任务",
            "instruction": "返回JSON格式的结果"
        }
        
        # 创建任务上下文
        context_manager.create_subtask_context("planner", "json_task")
        
        # 执行子任务
        result = executor.execute_subtask(subtask)
        
        # 验证JSON提取结果
        assert result["task_id"] == "json_task"
        assert result["success"] is True
        assert result["result"]["summary"] == "JSON提取测试成功"
        # 注意：data字段不会直接包含在结果对象中，因为它不是标准字段格式
        # TaskExecutor中的_verify_and_normalize_result方法对结果进行了规范化

    @patch("task_planner.core.task_executor.claude_api")
    def test_task_context_preparation(self, mock_claude, setup_executor):
        """测试任务上下文准备功能"""
        executor = setup_executor["executor"]
        context_manager = setup_executor["context_manager"]
        
        # 创建子任务定义
        subtask = {
            "id": "context_task",
            "name": "上下文测试任务",
            "instruction": "请处理上下文中的信息",
            "input_files_mapping": {
                "input_data": "/path/to/input.json"
            },
            "dependencies": ["dep_task"]
        }
        
        # 创建任务上下文并添加依赖任务结果
        task_context = TaskContext("context_task")
        task_context.update_local("dependency_results", {
            "dep_task": {
                "success": True,
                "result": {"summary": "依赖任务成功"}
            }
        })
        
        # 手动调用准备提示方法
        prompt = executor._prepare_context_aware_prompt(subtask, task_context)
        
        # 验证提示中包含关键信息
        assert "上下文测试任务" in prompt
        assert "请处理上下文中的信息" in prompt
        assert "input_data: /path/to/input.json" in prompt

    def test_report_file_creation(self, setup_executor, temp_dir):
        """测试文件生成功能 - 专注于report.md"""
        executor = setup_executor["executor"]
        context_dir = setup_executor["context_dir"]
        
        # 创建测试任务上下文
        task_context = TaskContext("file_task", base_dir=os.path.join(context_dir, "results/file_task"))
        os.makedirs(task_context.base_dir, exist_ok=True)
        
        # 准备测试文本内容 - 只包含报告文件
        text = """
处理完成，以下是生成的文件：

```file: report.md
# 测试报告
这是一个自动生成的报告
## 测试结果
- 测试1: 通过
- 测试2: 通过
```
        """
        
        # 创建测试子任务
        subtask = {
            "id": "file_task",
            "output_files": {
                "report": os.path.join(context_dir, "results/file_task/report.md")
            }
        }
        
        # 调用文件提取方法
        executor._extract_and_store_artifacts_from_text(text, subtask, task_context)
        
        # 验证report.md文件存在
        report_path = os.path.join(context_dir, "results/file_task/report.md")
        assert os.path.exists(report_path), "report.md文件应该被创建"
        
        # 读取文件内容并验证
        with open(report_path, 'r') as f:
            content = f.read()
            assert "# 测试报告" in content
            assert "- 测试1: 通过" in content
        
        # 检查文件引用是否被添加到任务上下文
        report_refs = []
        for name, ref in task_context.file_paths.items():
            if os.path.basename(ref['path']) == 'report.md':
                report_refs.append(name)
        
        assert len(report_refs) > 0, "应该有报告文件的引用"

    # 修改这个测试为不依赖于Gemini组件的版本
    @patch("task_planner.core.task_executor.claude_api")
    def test_task_status_recording(self, mock_claude, setup_executor):
        """测试任务状态记录功能"""
        # 创建执行器，不启用Gemini
        context_manager = setup_executor["context_manager"]
        executor = TaskExecutor(context_manager=context_manager, use_gemini=False)
        
        # 模拟Claude API响应，包含任务状态
        mock_claude.return_value = {
            "status": "success",
            "output": "任务已完成",
            "task_status": {
                "is_complete": True,
                "completion_score": 0.95
            },
            "conversation_history": ["历史记录1", "历史记录2"],
            "duration": 1.0
        }
        
        # 创建子任务定义
        subtask = {
            "id": "status_task",
            "name": "状态测试任务",
            "instruction": "测试任务状态记录功能"
        }
        
        # 创建任务上下文
        context_manager.create_subtask_context("planner", "status_task")
        
        # 执行子任务
        result = executor.execute_subtask(subtask)
        
        # 验证任务状态被记录
        task_context = context_manager.task_contexts["status_task"]
        assert "task_status" in task_context.local_context
        assert task_context.local_context["task_status"]["is_complete"] is True
        
        # 验证Claude响应被记录
        assert "claude_response" in task_context.local_context