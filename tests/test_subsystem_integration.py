"""
Subsystem integration tests for task planner system.
Tests interaction between core components.
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

class TestSubsystemIntegration:
    
    @pytest.fixture
    def setup_integration(self, temp_dir):
        """Setup test environment"""
        # Create context directory
        context_dir = os.path.join(temp_dir, "context")
        os.makedirs(context_dir, exist_ok=True)
        
        # Create subdirectories needed for tests
        os.makedirs(os.path.join(context_dir, "results"), exist_ok=True)
        os.makedirs(os.path.join(context_dir, "subtasks"), exist_ok=True)
        
        # Create context manager
        context_manager = ContextManager(context_dir)
        
        # Return setup context
        return {
            "context_manager": context_manager,
            "context_dir": context_dir,
            "temp_dir": temp_dir
        }
    
    @patch("task_planner.core.task_planner.OpenAI")
    @patch("task_planner.core.task_executor.claude_api", side_effect=mock_claude_api)
    def test_planner_context_manager_integration(self, mock_claude, mock_openai, setup_integration):
        """Test integration between TaskPlanner and ContextManager"""
        context_manager = setup_integration["context_manager"]
        
        # Prepare mock for analyze_task and break_down_task
        mock_analyze = MagicMock()
        mock_analyze.choices = [MagicMock(message=MagicMock(content='{"task_id": "task_analysis", "success": true, "result": {"summary": "Task analysis complete"}}'))]
        
        mock_breakdown = MagicMock()
        mock_breakdown_content = '''
        {
            "subtasks": [
                {
                    "id": "task_1",
                    "name": "Subtask 1",
                    "description": "Description for subtask 1",
                    "instruction": "Execute subtask 1",
                    "input_files": {"data": "input/data.csv"},
                    "output_files": {
                        "main_result": "results/task_1/result.json",
                        "report": "results/task_1/report.md"
                    },
                    "success_criteria": ["Criterion 1", "Criterion 2"],
                    "dependencies": []
                },
                {
                    "id": "task_2",
                    "name": "Subtask 2",
                    "description": "Description for subtask 2",
                    "instruction": "Execute subtask 2",
                    "input_files": {"result": "task_1:main_result"},
                    "output_files": {
                        "main_result": "results/task_2/result.json",
                        "model": "results/task_2/model.pkl"
                    },
                    "success_criteria": ["Criterion 1"],
                    "dependencies": ["task_1"]
                }
            ]
        }
        '''
        mock_breakdown.choices = [MagicMock(message=MagicMock(content=mock_breakdown_content.replace("\n", "").replace(" ", "")))]
        
        # Set up the mock to return different values based on the call
        mock_openai.return_value.chat.completions.create.side_effect = [
            mock_analyze,  # First call for analyze_task
            mock_breakdown  # Second call for break_down_task
        ]
        
        # Create planner
        task_description = "Test integration task"
        planner = TaskPlanner(task_description, context_manager)
        
        # Break down task
        subtasks = planner.break_down_task()
        
        # Check context creation
        assert "planner" in context_manager.task_contexts
        assert "task_1" in context_manager.task_contexts
        assert "task_2" in context_manager.task_contexts
        
        # Check directory creation
        context_dir = setup_integration["context_dir"]
        assert os.path.exists(os.path.join(context_dir, "results", "task_1"))
        assert os.path.exists(os.path.join(context_dir, "results", "task_2"))
        assert os.path.exists(os.path.join(context_dir, "subtasks", "task_1.json"))
        
        # Check next subtask
        subtask = planner.get_next_subtask()
        assert subtask["id"] == "task_1"
        
        # Check task context
        task_context = context_manager.task_contexts["task_1"]
        assert "progress" in task_context.local_context
        assert task_context.local_context["progress"]["current_index"] == 0
        assert task_context.local_context["progress"]["total_tasks"] == 2
    
    @patch("task_planner.core.task_executor.claude_api", side_effect=mock_claude_api)
    def test_executor_context_manager_integration(self, mock_claude, setup_integration):
        """Test integration between TaskExecutor and ContextManager"""
        context_manager = setup_integration["context_manager"]
        context_dir = setup_integration["context_dir"]
        
        # Create executor
        executor = TaskExecutor(context_manager)
        
        # Create test subtask
        subtask = {
            "id": "test_task",
            "name": "Test Task",
            "instruction": "Execute test task and create report",
            "output_files": {
                "main_result": os.path.join(context_dir, "results/test_task/result.json"),
                "report": os.path.join(context_dir, "results/test_task/report.md")
            },
            "success_criteria": ["Task completed"]
        }
        
        # Create context
        context_manager.create_subtask_context("planner", "test_task")
        
        # Create output directories
        os.makedirs(os.path.dirname(subtask["output_files"]["main_result"]), exist_ok=True)
        
        # Execute subtask
        result = executor.execute_subtask(subtask)
        
        # Check result
        assert result["task_id"] == "test_task"
        assert result["success"] is True
        
        # Check context update
        task_context = context_manager.task_contexts["test_task"]
        assert task_context.local_context["success"] is True
        assert "summary" in task_context.local_context
        
        # Check file references
        assert "output_main_result" in task_context.file_paths
        assert os.path.exists(task_context.file_paths["output_main_result"]["path"])
        
        # Check report file
        report_path = os.path.join(context_dir, "results/test_task/report.md")
        assert os.path.exists(report_path)
    
    @patch("task_planner.core.task_planner.OpenAI")
    @patch("task_planner.core.task_executor.claude_api", side_effect=mock_claude_api)
    def test_planner_executor_integration(self, mock_claude, mock_openai, setup_integration):
        """Test integration between TaskPlanner and TaskExecutor"""
        context_manager = setup_integration["context_manager"]
        context_dir = setup_integration["context_dir"]
        
        # Prepare mock for analyze_task and break_down_task
        mock_analyze = MagicMock()
        mock_analyze.choices = [MagicMock(message=MagicMock(content='{"task_id": "task_analysis", "success": true, "result": {"summary": "Task analysis complete"}}'))]
        
        mock_breakdown = MagicMock()
        mock_breakdown_content = '''
        {
            "subtasks": [
                {
                    "id": "task_1",
                    "name": "Test Subtask",
                    "instruction": "Execute test task",
                    "output_files": {
                        "main_result": "results/task_1/result.json",
                        "report": "results/task_1/report.md"
                    },
                    "success_criteria": ["Task completed"],
                    "dependencies": []
                }
            ]
        }
        '''
        mock_breakdown.choices = [MagicMock(message=MagicMock(content=mock_breakdown_content.replace("\n", "").replace(" ", "")))]
        
        # Set up the mock to return different values based on the call
        mock_openai.return_value.chat.completions.create.side_effect = [
            mock_analyze,  # First call for analyze_task
            mock_breakdown  # Second call for break_down_task
        ]
        
        # Create planner and executor
        task_description = "Test integration task"
        planner = TaskPlanner(task_description, context_manager)
        executor = TaskExecutor(context_manager)
        
        # Break down task
        planner.break_down_task()
        
        # Get subtask
        subtask = planner.get_next_subtask()
        
        # Execute subtask
        result = executor.execute_subtask(subtask)
        
        # Process result
        planner.process_result(subtask["id"], result)
        
        # Check result storage
        assert subtask["id"] in planner.results
        assert planner.results[subtask["id"]]["success"] is True
        
        # Check output files
        assert os.path.exists(os.path.join(context_dir, "results", "task_1", "result.json"))
        assert os.path.exists(os.path.join(context_dir, "results", "task_1", "report.md"))
        
        # Get final result
        with patch.object(planner.client.chat.completions, "create") as mock_final:
            mock_final_response = MagicMock()
            mock_final_content = '''
            {
                "task_id": "final_result", 
                "success": true, 
                "result": {
                    "summary": "Task completed successfully", 
                    "details": "All subtasks executed successfully"
                }
            }
            '''
            mock_final_response.choices = [MagicMock(message=MagicMock(content='{"task_id":"final_result","success":true,"result":{"summary":"Task completed successfully","details":"All subtasks executed successfully"}}'))]
            mock_final.return_value = mock_final_response
            
            final_result = planner.get_final_result()
        
        # Check final result
        assert final_result["task_id"] == "final_result"
        assert final_result["success"] is True
        assert final_result["result"]["summary"] == "Task completed successfully"
        
        # Check final result file
        assert os.path.exists(os.path.join(context_dir, "final_result.json"))
    
    def test_file_propagation(self, setup_integration):
        """Test file reference propagation between tasks"""
        context_manager = setup_integration["context_manager"]
        context_dir = setup_integration["context_dir"]
        
        # Create contexts
        context_manager.create_subtask_context("planner", "task_1")
        context_manager.create_subtask_context("planner", "task_2")
        
        # Create task 1 output files
        task1_dir = os.path.join(context_dir, "results", "task_1")
        os.makedirs(task1_dir, exist_ok=True)
        
        result_file = os.path.join(task1_dir, "result.json")
        with open(result_file, "w") as f:
            json.dump({"task_id": "task_1", "success": True, "data": "Test data"}, f)
            
        report_file = os.path.join(task1_dir, "report.md")
        with open(report_file, "w") as f:
            f.write("# Task Report")
        
        # Add file references to task_1
        context_manager.task_contexts["task_1"].add_file_reference(
            "output_main_result",
            result_file,
            {"type": "output_file", "output_type": "main_result"}
        )
        
        context_manager.task_contexts["task_1"].add_file_reference(
            "output_report",
            report_file,
            {"type": "output_file", "output_type": "report"}
        )
        
        # Update task context
        context_manager.task_contexts["task_1"].update_local("success", True)
        
        # Propagate results to task_2 with file references
        context_manager.propagate_results("task_1", ["task_2"], 
                                         file_reference_keys=["output_main_result", "output_report"])
        
        # Check file propagation
        task2_context = context_manager.task_contexts["task_2"]
        assert "output_main_result" in task2_context.file_paths
        assert task2_context.file_paths["output_main_result"]["path"] == result_file
        assert "output_report" in task2_context.file_paths
        
        # Check context propagation
        assert task2_context.local_context["success"] is True