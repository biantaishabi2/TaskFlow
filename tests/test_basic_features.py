"""
Tests for basic features of the task planner system.
"""

import pytest
import os
import json
import tempfile
from unittest.mock import patch, MagicMock
from task_planner.core.context_management import ContextManager
from task_planner.core.task_planner import TaskPlanner
from task_planner.core.task_executor import TaskExecutor

class MockResponse:
    """Mock for OpenAI API responses"""
    def __init__(self, content):
        self.choices = [MagicMock(message=MagicMock(content=content))]

# Mock for claude_api
def mock_claude_api(prompt, **kwargs):
    """Mock Claude API responses"""
    return {
        "status": "success",
        "output": """Task completed successfully.

```json
{
  "task_id": "test_task",
  "success": true,
  "result": {
    "summary": "Task execution summary",
    "details": "Task execution details"
  },
  "artifacts": {
    "report": "path/to/report.md"
  },
  "next_steps": ["Optional next step"]
}
```

Files created:
- `result.json`: Results
- `report.md`: Report

```file: report.md
# Task Report
Task execution report
```
""",
        "duration": 1.5
    }

class TestBasicFeatures:
    
    @pytest.fixture
    def setup_test(self, temp_dir):
        """Setup test environment"""
        # Create context directory
        context_dir = os.path.join(temp_dir, "context")
        os.makedirs(context_dir, exist_ok=True)
        
        # Create subdirectories needed for tests
        os.makedirs(os.path.join(context_dir, "results"), exist_ok=True)
        os.makedirs(os.path.join(context_dir, "subtasks"), exist_ok=True)
        
        return {
            "temp_dir": temp_dir,
            "context_dir": context_dir
        }
    
    @patch("task_planner.core.task_planner.OpenAI")
    def test_task_analysis_feature(self, mock_openai, setup_test):
        """Test task analysis feature"""
        context_dir = setup_test["context_dir"]
        
        # Prepare mock
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"task_id": "task_analysis", "success": true, "result": {"summary": "Task analysis complete", "task_type": "Data processing", "goals": ["Process data"], "technical_requirements": ["Python", "Data analysis"], "challenges": ["Large dataset"], "approach": "Incremental processing"}}'
                )
            )
        ]
        mock_openai.return_value.chat.completions.create.return_value = mock_response
        
        # Create planner
        context_manager = ContextManager(context_dir)
        task_description = "Analyze a large dataset and extract patterns for future prediction"
        planner = TaskPlanner(task_description, context_manager)
        
        # Run task analysis
        analysis = planner.analyze_task()
        
        # Check results
        assert analysis["task_id"] == "task_analysis"
        assert analysis["success"] is True
        assert "summary" in analysis["result"]
        assert "task_type" in analysis["result"]
        assert "goals" in analysis["result"]
        assert "technical_requirements" in analysis["result"]
        assert "challenges" in analysis["result"]
        
        # Check context storage
        assert "analysis" in planner.plan_context.local_context
        assert planner.plan_context.local_context["analysis"] == analysis
        
        # Check execution records
        records = [r for r in planner.plan_context.execution_history if r["action"] == "analysis_completed"]
        assert len(records) > 0
    
    @patch("task_planner.core.task_planner.OpenAI")
    def test_task_breakdown_feature(self, mock_openai, setup_test):
        """Test task breakdown feature"""
        context_dir = setup_test["context_dir"]
        
        # Prepare mocks
        # Analysis response
        mock_analysis = MagicMock()
        mock_analysis.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"task_id": "task_analysis", "success": true, "result": {"summary": "Task analysis complete"}}'
                )
            )
        ]
        
        # Breakdown response
        mock_breakdown = MagicMock()
        mock_breakdown.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"subtasks": [{"id": "task_1", "name": "Subtask 1", "description": "Description for subtask 1", "instruction": "Execute subtask 1", "input_files": {"data": "input/data.csv"}, "output_files": {"main_result": "results/task_1/result.json", "report": "results/task_1/report.md"}, "success_criteria": ["Criterion 1", "Criterion 2"], "dependencies": []}, {"id": "task_2", "name": "Subtask 2", "description": "Description for subtask 2", "instruction": "Execute subtask 2", "input_files": {"result": "task_1:main_result"}, "output_files": {"main_result": "results/task_2/result.json", "model": "results/task_2/model.pkl"}, "success_criteria": ["Criterion 1"], "dependencies": ["task_1"]}]}'
                )
            )
        ]
        
        mock_openai.return_value.chat.completions.create.side_effect = [
            mock_analysis,
            mock_breakdown
        ]
        
        # Create planner
        context_manager = ContextManager(context_dir)
        task_description = "Analyze a large dataset and extract patterns"
        planner = TaskPlanner(task_description, context_manager)
        
        # Break down task
        subtasks = planner.break_down_task()
        
        # Check results
        assert len(subtasks) == 2
        assert subtasks[0]["id"] == "task_1"
        assert subtasks[1]["id"] == "task_2"
        assert "name" in subtasks[0]
        assert "instruction" in subtasks[0]
        assert "input_files" in subtasks[0]
        assert "output_files" in subtasks[0]
        assert "success_criteria" in subtasks[0]
        assert "dependencies" in subtasks[0]
        
        # Check dependencies
        assert "task_1" in subtasks[1]["dependencies"]
        
        # Check directory creation
        assert os.path.exists(os.path.join(context_dir, "results", "task_1"))
        assert os.path.exists(os.path.join(context_dir, "results", "task_2"))
        assert os.path.exists(os.path.join(context_dir, "subtasks", "task_1.json"))
        assert os.path.exists(os.path.join(context_dir, "subtasks", "task_2.json"))
        
        # Check context creation
        assert "task_1" in context_manager.task_contexts
        assert "task_2" in context_manager.task_contexts
        
        # Check execution records
        records = [r for r in planner.plan_context.execution_history if r["action"] == "breakdown_completed"]
        assert len(records) > 0
    
    @patch("task_planner.core.task_executor.claude_api", side_effect=mock_claude_api)
    def test_task_execution_feature(self, mock_claude, setup_test):
        """Test task execution feature"""
        context_dir = setup_test["context_dir"]
        
        # Setup context manager and executor
        context_manager = ContextManager(context_dir)
        executor = TaskExecutor(context_manager)
        
        # Create test subtask
        subtask = {
            "id": "test_task",
            "name": "Test Task",
            "instruction": "Analyze dataset and create report",
            "output_files": {
                "main_result": os.path.join(context_dir, "results/test_task/result.json"),
                "report": os.path.join(context_dir, "results/test_task/report.md")
            },
            "success_criteria": ["Complete analysis"]
        }
        
        # Create context
        context_manager.create_subtask_context("planner", "test_task")
        
        # Create output directories
        os.makedirs(os.path.dirname(subtask["output_files"]["main_result"]), exist_ok=True)
        
        # Execute subtask
        result = executor.execute_subtask(subtask)
        
        # Check execution result
        assert result["task_id"] == "test_task"
        assert result["success"] is True
        assert "result" in result
        assert result["result"]["summary"] == "Task execution summary"
        assert "next_steps" in result
        
        # Check result file
        assert os.path.exists(subtask["output_files"]["main_result"])
        
        # Check report file
        report_path = os.path.join(context_dir, "results/test_task/report.md")
        assert os.path.exists(report_path)
        
        # Check report content
        with open(report_path, "r") as f:
            content = f.read()
            assert "# Task Report" in content
        
        # Check context update
        task_context = context_manager.task_contexts["test_task"]
        assert task_context.local_context["success"] is True
        assert "output_main_result" in task_context.file_paths
        
        # Check execution records
        records = [r for r in task_context.execution_history if r["action"] == "execution_completed"]
        assert len(records) > 0