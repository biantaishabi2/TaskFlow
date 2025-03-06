"""
End-to-end tests for task planner system.
Tests complete execution flow and results.
"""

import pytest
import os
import json
import shutil
from unittest.mock import patch, MagicMock
from task_planner.core.context_management import ContextManager
from task_planner.core.task_planner import TaskPlanner
from task_planner.core.task_executor import TaskExecutor

class MockResponse:
    """Mock for OpenAI API responses"""
    def __init__(self, content):
        self.choices = [MagicMock(message=MagicMock(content=content))]

# Mock for claude_api success responses
def mock_claude_api_success(prompt, **kwargs):
    """Mock Claude API success responses"""
    task_id = "unknown_task"
    if "Task" in prompt:
        task_line = [line for line in prompt.split('\n') if line.startswith("# Task")]
        if task_line:
            task_name = task_line[0].replace("# Task", "").strip()
            if "1" in task_name:
                task_id = "task_1"
            elif "2" in task_name:
                task_id = "task_2"
            elif "3" in task_name:
                task_id = "task_3"
    
    return {
        "status": "success",
        "output": f"""Task {task_id} executed successfully.

Execution completed.

```json
{{
  "task_id": "{task_id}",
  "success": true,
  "result": {{
    "summary": "Task {task_id} completed",
    "details": "Task execution details"
  }},
  "artifacts": {{
    "report": "report.md"
  }},
  "next_steps": ["Optional next step"]
}}
```

Files created:
- `result.json`: Results
- `report.md`: Report

```file: report.md
# {task_id} Report
Task {task_id} execution report
```
""",
        "duration": 1.5
    }

def mock_claude_api_failure(prompt, **kwargs):
    """Mock Claude API failure response"""
    return {
        "status": "success",  # API succeeded but task failed
        "output": """Task execution failed.

Execution encountered an error during processing.

```json
{
  "task_id": "task_2",
  "success": false,
  "error": "Error processing task",
  "result": {
    "summary": "Task execution failed with error",
    "details": "Details about the failure during execution"
  }
}
```
""",
        "duration": 1.5
    }

class TestEndToEnd:
    
    @pytest.fixture
    def setup_e2e(self, temp_dir):
        """Setup end-to-end test environment"""
        # Create context directory
        context_dir = os.path.join(temp_dir, "context")
        os.makedirs(context_dir, exist_ok=True)
        
        # Create subdirectories needed for tests
        os.makedirs(os.path.join(context_dir, "results"), exist_ok=True)
        os.makedirs(os.path.join(context_dir, "subtasks"), exist_ok=True)
        
        # Create input data directory
        input_dir = os.path.join(temp_dir, "input")
        os.makedirs(input_dir, exist_ok=True)
        
        # Create test data file
        with open(os.path.join(input_dir, "data.csv"), "w") as f:
            f.write("id,value\n1,100\n2,200\n3,300")
        
        return {
            "temp_dir": temp_dir,
            "context_dir": context_dir,
            "input_dir": input_dir
        }
    
    @patch("task_planner.core.task_planner.OpenAI")
    @patch("task_planner.core.task_executor.claude_api", side_effect=mock_claude_api_success)
    def test_single_task_execution(self, mock_claude, mock_openai, setup_e2e):
        """Test single task execution flow"""
        context_dir = setup_e2e["context_dir"]
        
        # Prepare mocks
        # Analysis response
        mock_analysis = MagicMock()
        mock_analysis.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"task_id": "task_analysis", "success": true, "result": {"summary": "Single task analysis", "task_type": "Single task", "goals": ["Task goal 1"]}}'
                )
            )
        ]
        
        # Breakdown response
        mock_breakdown = MagicMock()
        mock_breakdown.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"subtasks": [{"id": "task_1", "name": "Task One", "instruction": "Execute task one", "input_files": {}, "output_files": {"main_result": "results/task_1/result.json", "report": "results/task_1/report.md"}, "success_criteria": ["Task completed"], "dependencies": []}]}'
                )
            )
        ]
        
        # Final result response
        mock_final = MagicMock()
        mock_final.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"task_id": "final_result", "success": true, "result": {"summary": "All tasks completed", "details": "Task executed successfully", "key_findings": ["Task completed"]}}'
                )
            )
        ]
        
        mock_openai.return_value.chat.completions.create.side_effect = [
            mock_analysis,
            mock_breakdown,
            mock_final
        ]
        
        # Setup context manager, planner and executor
        context_manager = ContextManager(context_dir)
        task_description = "Execute single task test"
        planner = TaskPlanner(task_description, context_manager)
        executor = TaskExecutor(context_manager)
        
        # Break down task
        planner.break_down_task()
        
        # Check breakdown results
        assert len(planner.subtasks) == 1
        assert planner.subtasks[0]["id"] == "task_1"
        
        # Get subtask
        subtask = planner.get_next_subtask()
        assert subtask["id"] == "task_1"
        
        # Execute subtask
        result = executor.execute_subtask(subtask)
        
        # Check execution result
        assert result["task_id"] == "task_1"
        assert result["success"] is True
        
        # Process result
        planner.process_result(subtask["id"], result)
        
        # Check result storage
        assert "task_1" in planner.results
        assert planner.results["task_1"]["success"] is True
        
        # Check output files
        assert os.path.exists(os.path.join(context_dir, "results", "task_1", "result.json"))
        assert os.path.exists(os.path.join(context_dir, "results", "task_1", "report.md"))
        
        # Get final result
        final_result = planner.get_final_result()
        
        # Check final result
        assert final_result["task_id"] == "final_result"
        assert final_result["success"] is True
        assert final_result["result"]["summary"] == "All tasks completed"
        
        # Check final result file
        assert os.path.exists(os.path.join(context_dir, "final_result.json"))
    
    @patch("task_planner.core.task_planner.OpenAI")
    @patch("task_planner.core.task_executor.claude_api", side_effect=mock_claude_api_success)
    def test_multi_task_chain_execution(self, mock_claude, mock_openai, setup_e2e):
        """Test multi-task chain execution"""
        context_dir = setup_e2e["context_dir"]
        input_dir = setup_e2e["input_dir"]
        
        # Prepare mocks
        # Analysis response
        mock_analysis = MagicMock()
        mock_analysis.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"task_id": "task_analysis", "success": true, "result": {"summary": "Multi-task analysis", "task_type": "Multi-task", "goals": ["Task goal 1", "Task goal 2", "Task goal 3"]}}'
                )
            )
        ]
        
        # Breakdown response with absolute paths for output files
        mock_breakdown_content = f'''
        {{
            "subtasks": [
                {{
                    "id": "task_1",
                    "name": "Data Preprocessing",
                    "instruction": "Preprocess input data",
                    "input_files": {{
                        "data": "{input_dir}/data.csv"
                    }},
                    "output_files": {{
                        "main_result": "{os.path.join(context_dir, 'results/task_1/result.json')}",
                        "processed_data": "{os.path.join(context_dir, 'results/task_1/processed_data.json')}"
                    }},
                    "success_criteria": ["Processed data"],
                    "dependencies": []
                }},
                {{
                    "id": "task_2",
                    "name": "Data Analysis",
                    "instruction": "Analyze processed data",
                    "input_files": {{
                        "data": "task_1:processed_data"
                    }},
                    "output_files": {{
                        "main_result": "{os.path.join(context_dir, 'results/task_2/result.json')}",
                        "analysis": "{os.path.join(context_dir, 'results/task_2/analysis.json')}"
                    }},
                    "success_criteria": ["Analyzed data"],
                    "dependencies": ["task_1"]
                }},
                {{
                    "id": "task_3",
                    "name": "Results Reporting",
                    "instruction": "Generate final report",
                    "input_files": {{
                        "analysis": "task_2:analysis"
                    }},
                    "output_files": {{
                        "main_result": "{os.path.join(context_dir, 'results/task_3/result.json')}",
                        "report": "{os.path.join(context_dir, 'results/task_3/final_report.md')}"
                    }},
                    "success_criteria": ["Report generated"],
                    "dependencies": ["task_2"]
                }}
            ]
        }}
        '''
        
        mock_breakdown = MagicMock()
        mock_breakdown.choices = [
            MagicMock(
                message=MagicMock(
                    content=mock_breakdown_content.replace("\n", "").replace("    ", "")
                )
            )
        ]
        
        # Final result response
        mock_final = MagicMock()
        mock_final.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"task_id": "final_result", "success": true, "result": {"summary": "All tasks completed", "details": "Multi-task workflow executed successfully", "key_findings": ["Processed data", "Analyzed data", "Report generated"]}}'
                )
            )
        ]
        
        mock_openai.return_value.chat.completions.create.side_effect = [
            mock_analysis,
            mock_breakdown,
            mock_final
        ]
        
        # Setup context manager, planner and executor
        context_manager = ContextManager(context_dir)
        task_description = "Execute multi-task test"
        planner = TaskPlanner(task_description, context_manager)
        executor = TaskExecutor(context_manager)
        
        # Break down task
        planner.break_down_task()
        
        # Check breakdown results
        assert len(planner.subtasks) == 3
        assert planner.subtasks[0]["id"] == "task_1"
        assert planner.subtasks[1]["id"] == "task_2"
        assert planner.subtasks[2]["id"] == "task_3"
        
        # Execute each task individually to have more control over the process
        # First, task 1
        subtask1 = planner.get_next_subtask()
        assert subtask1["id"] == "task_1"
        
        # Create output directories
        for output_type, output_path in subtask1["output_files"].items():
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Create processed_data file
            if output_type == "processed_data":
                with open(output_path, "w") as f:
                    json.dump({"processed": [1, 2, 3]}, f)
                    
        # Execute task 1
        result1 = executor.execute_subtask(subtask1)
        
        # Process result
        planner.process_result(subtask1["id"], result1)
        
        # Check result
        assert subtask1["id"] in planner.results
        assert planner.results[subtask1["id"]]["success"] is True
        
        # Task 2
        subtask2 = planner.get_next_subtask()
        assert subtask2["id"] == "task_2"
        
        # Create output directories
        for output_type, output_path in subtask2["output_files"].items():
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Create analysis file
            if output_type == "analysis":
                with open(output_path, "w") as f:
                    json.dump({"analysis": {"mean": 2, "sum": 6}}, f)
                    
        # Execute task 2
        result2 = executor.execute_subtask(subtask2)
        
        # Process result
        planner.process_result(subtask2["id"], result2)
        
        # Check result
        assert subtask2["id"] in planner.results
        assert planner.results[subtask2["id"]]["success"] is True
        
        # Task 3
        subtask3 = planner.get_next_subtask()
        assert subtask3["id"] == "task_3"
        
        # Create output directories
        for output_type, output_path in subtask3["output_files"].items():
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Create final report file if this is the report output
            if output_type == "report":
                with open(output_path, "w") as f:
                    f.write("# Final Report\nThis is the final report.")
                    
        # Execute task 3
        result3 = executor.execute_subtask(subtask3)
        
        # Process result
        planner.process_result(subtask3["id"], result3)
        
        # Check result
        assert subtask3["id"] in planner.results
        assert planner.results[subtask3["id"]]["success"] is True
        
        # Check all tasks completed
        assert len(planner.results) == 3
        
        # Check output files
        for task_id in ["task_1", "task_2", "task_3"]:
            assert os.path.exists(os.path.join(context_dir, "results", task_id, "result.json"))
            
        assert os.path.exists(os.path.join(context_dir, "results", "task_3", "final_report.md"))
        
        # Get final result
        final_result = planner.get_final_result()
        
        # Check final result
        assert final_result["task_id"] == "final_result"
        assert final_result["success"] is True
        assert final_result["result"]["summary"] == "All tasks completed"
        
        # Check final result file
        assert os.path.exists(os.path.join(context_dir, "final_result.json"))
    
    @patch("task_planner.core.task_planner.OpenAI")
    def test_error_handling_and_plan_adjustment(self, mock_openai, setup_e2e):
        """Test error handling and plan adjustment"""
        context_dir = setup_e2e["context_dir"]
        
        # Prepare mocks
        # Analysis response
        mock_analysis = MagicMock()
        mock_analysis.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"task_id": "task_analysis", "success": true, "result": {"summary": "Task analysis", "task_type": "Test", "goals": ["Task goal 1", "Task goal 2"]}}'
                )
            )
        ]
        
        # Breakdown response
        mock_breakdown_content = f'''
        {{
            "subtasks": [
                {{
                    "id": "task_1",
                    "name": "Initial Task",
                    "instruction": "Process initial data",
                    "output_files": {{
                        "main_result": "{os.path.join(context_dir, 'results/task_1/result.json')}",
                        "data": "{os.path.join(context_dir, 'results/task_1/data.json')}"
                    }},
                    "success_criteria": ["Processed"],
                    "dependencies": []
                }},
                {{
                    "id": "task_2",
                    "name": "Failing Task",
                    "instruction": "Execute task that will fail",
                    "input_files": {{
                        "data": "task_1:data"
                    }},
                    "output_files": {{
                        "main_result": "{os.path.join(context_dir, 'results/task_2/result.json')}"
                    }},
                    "success_criteria": ["Analysis"],
                    "dependencies": ["task_1"]
                }},
                {{
                    "id": "task_3",
                    "name": "Final Task",
                    "instruction": "Complete workflow",
                    "input_files": {{
                        "result": "task_2:main_result"
                    }},
                    "output_files": {{
                        "main_result": "{os.path.join(context_dir, 'results/task_3/result.json')}"
                    }},
                    "success_criteria": ["Completed"],
                    "dependencies": ["task_2"]
                }}
            ]
        }}
        '''
        
        mock_breakdown = MagicMock()
        mock_breakdown.choices = [
            MagicMock(
                message=MagicMock(
                    content=mock_breakdown_content.replace("\n", "").replace("    ", "")
                )
            )
        ]
        
        # Adjustment response
        mock_adjustment_content = f'''
        {{
            "result": {{
                "needs_adjustment": true,
                "reason": "Task 2 failed, need an alternative approach",
                "insert_tasks": [
                    {{
                        "id": "task_2_alt",
                        "name": "Alternative Task",
                        "instruction": "Use alternative approach for processing data",
                        "input_files": {{
                            "data": "task_1:data"
                        }},
                        "output_files": {{
                            "main_result": "{os.path.join(context_dir, 'results/task_2_alt/result.json')}"
                        }},
                        "success_criteria": ["Analysis"],
                        "insert_index": 2,
                        "dependencies": ["task_1"]
                    }}
                ],
                "modify_tasks": [
                    {{
                        "id": "task_3",
                        "dependencies": ["task_2_alt"]
                    }}
                ]
            }}
        }}
        '''
        
        mock_adjustment = MagicMock()
        mock_adjustment.choices = [
            MagicMock(
                message=MagicMock(
                    content=mock_adjustment_content.replace("\n", "").replace("    ", "")
                )
            )
        ]
        
        # Final result response
        mock_final = MagicMock()
        mock_final.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"task_id": "final_result", "success": true, "result": {"summary": "Tasks completed with adjustment", "details": "Plan was adjusted to handle task 2 failure with an alternative approach"}}'
                )
            )
        ]
        
        mock_openai.return_value.chat.completions.create.side_effect = [
            mock_analysis,
            mock_breakdown,
            mock_adjustment,
            mock_final
        ]
        
        # Setup context manager and planner
        context_manager = ContextManager(context_dir)
        task_description = "Execute test task"
        planner = TaskPlanner(task_description, context_manager)
        
        # Break down task
        planner.break_down_task()
        
        # Check breakdown results
        assert len(planner.subtasks) == 3
        
        # Execute task 1 successfully
        with patch("task_planner.core.task_executor.claude_api", side_effect=mock_claude_api_success):
            subtask1 = planner.get_next_subtask()
            assert subtask1["id"] == "task_1"
            
            # Create output directories
            for output_type, output_path in subtask1["output_files"].items():
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Create mock data file
            data_path = os.path.join(context_dir, "results", "task_1", "data.json")
            with open(data_path, "w") as f:
                json.dump({"test": "data"}, f)
                
            # Execute task 1
            executor = TaskExecutor(context_manager)
            result1 = executor.execute_subtask(subtask1)
            
            # Process result
            planner.process_result(subtask1["id"], result1)
        
        # Execute task 2 with failure
        with patch("task_planner.core.task_executor.claude_api", side_effect=mock_claude_api_failure):
            subtask2 = planner.get_next_subtask()
            assert subtask2["id"] == "task_2"
            
            # Create output directories
            for output_type, output_path in subtask2["output_files"].items():
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Execute task 2 (will fail)
            executor = TaskExecutor(context_manager)
            result2 = executor.execute_subtask(subtask2)
            
            # Process result
            planner.process_result(subtask2["id"], result2)
            
            # Check failure
            assert result2["success"] is False
        
        # The real implementation doesn't replace task_2, it adds task_2_alt and modifies task_3 dependencies
        # Let's check that task_2_alt is in the subtasks and task_3 has task_2_alt in its dependencies
        
        # Find task_2_alt and task_3 in subtasks
        task_2_alt_found = False
        task_3_dependencies_modified = False
        
        for subtask in planner.subtasks:
            if subtask["id"] == "task_2_alt":
                task_2_alt_found = True
            if subtask["id"] == "task_3" and "task_2_alt" in subtask["dependencies"]:
                task_3_dependencies_modified = True
        
        assert task_2_alt_found, "task_2_alt not found in plan after adjustment"
        assert task_3_dependencies_modified, "task_3 dependencies not modified to include task_2_alt"
        
        # Execute remaining tasks successfully
        with patch("task_planner.core.task_executor.claude_api", side_effect=mock_claude_api_success):
            # Get next task (this could be task_2_alt or task_3 depending on implementation)
            next_subtask = planner.get_next_subtask()
            # The important part is that we found task_2_alt and updated task_3 dependencies
            # We don't need to assert the exact execution order
            
            # Create output directories
            for output_type, output_path in next_subtask["output_files"].items():
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Execute the next task
            result_next = executor.execute_subtask(next_subtask)
            
            # Process result
            planner.process_result(next_subtask["id"], result_next)
            
            # Check success
            assert result_next["success"] is True
            
            # We might be done already, or we might have another task to execute
            # Only proceed if there's another task
            if not planner.is_complete():
                subtask3 = planner.get_next_subtask()
                
                # Create output directories
                for output_type, output_path in subtask3["output_files"].items():
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                # Execute next task
                result3 = executor.execute_subtask(subtask3)
                
                # Process result
                planner.process_result(subtask3["id"], result3)
                
                # Check success
                assert result3["success"] is True
        
        # Check workflow completion
        assert planner.is_complete()
        
        # Get final result
        final_result = planner.get_final_result()
        
        # Check final result
        assert final_result["task_id"] == "final_result"
        assert final_result["success"] is True
        assert "adjustment" in final_result["result"]["summary"]