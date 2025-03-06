"""
Test ContextManager class functionality
"""

import pytest
import os
import json
import shutil
from task_planner.core.context_management import TaskContext, ContextManager

class TestContextManager:
    
    def test_init(self, temp_dir):
        """Test ContextManager initialization"""
        # Test initialization without parameters
        manager = ContextManager()
        assert manager.global_context == {}
        assert manager.task_contexts == {}
        assert manager.context_history == []
        assert manager.context_dir is None
        
        # Test initialization with context_dir
        context_dir = os.path.join(temp_dir, "context")
        manager = ContextManager(context_dir)
        assert manager.context_dir == context_dir
        assert os.path.exists(context_dir)
        assert os.path.exists(os.path.join(context_dir, "subtasks"))
        assert os.path.exists(os.path.join(context_dir, "results"))
    
    def test_create_subtask_context(self, temp_dir):
        """Test creating subtask context functionality"""
        context_dir = os.path.join(temp_dir, "context")
        manager = ContextManager(context_dir)
        
        # Create parent task context
        parent_context = TaskContext("parent_task", manager.global_context)
        parent_context.update_local("parent_key", "parent_value")
        manager.task_contexts["parent_task"] = parent_context
        
        # Test default inheritance of all parent task context
        subtask_context = manager.create_subtask_context("parent_task", "subtask1")
        assert subtask_context.task_id == "subtask1"
        assert subtask_context.local_context["parent_key"] == "parent_value"
        assert subtask_context.local_context["_parent_task_id"] == "parent_task"
        
        # Verify result directory creation
        assert os.path.exists(os.path.join(context_dir, "results", "subtask1"))
        
        # Test inheriting specified context subset
        parent_context.update_local("another_key", "another_value")
        subtask_context = manager.create_subtask_context("parent_task", "subtask2", ["another_key"])
        assert subtask_context.task_id == "subtask2"
        assert "parent_key" not in subtask_context.local_context
        assert subtask_context.local_context["another_key"] == "another_value"
        
        # Verify task contexts are stored
        assert "subtask1" in manager.task_contexts
        assert "subtask2" in manager.task_contexts
    
    def test_update_task_context(self):
        """Test updating task context functionality"""
        manager = ContextManager()
        
        # Create task context
        task_context = TaskContext("test_task", manager.global_context)
        manager.task_contexts["test_task"] = task_context
        
        # Test updating only local context
        update_data = {"key1": "value1", "key2": "value2"}
        manager.update_task_context("test_task", update_data)
        
        assert task_context.local_context["key1"] == "value1"
        assert task_context.local_context["key2"] == "value2"
        assert "key1" not in manager.global_context
        
        # Test updating global context as well
        update_data = {"key3": "value3"}
        manager.update_task_context("test_task", update_data, update_global=True)
        
        assert task_context.local_context["key3"] == "value3"
        assert manager.global_context["key3"] == "value3"
        
        # Test updating non-existent context
        with pytest.raises(ValueError):
            manager.update_task_context("non_existent", {"key": "value"})
    
    def test_propagate_results(self):
        """Test result propagation functionality"""
        manager = ContextManager()
        
        # Create source task context
        source_context = TaskContext("source_task", manager.global_context)
        source_context.update_local("result", {"success": True, "data": "test_data"})
        source_context.update_local("metrics", {"accuracy": 0.95})
        source_context.add_file_reference("output1", "/test/output1.txt", {"type": "text"})
        source_context.add_file_reference("output2", "/test/output2.json", {"type": "data"})
        manager.task_contexts["source_task"] = source_context
        
        # Create target task contexts
        target1_context = TaskContext("target1", manager.global_context)
        target2_context = TaskContext("target2", manager.global_context)
        manager.task_contexts["target1"] = target1_context
        manager.task_contexts["target2"] = target2_context
        
        # Test propagating all results and file references
        # Include file_reference_keys parameter explicitly since file_paths is not included in default keys
        manager.propagate_results("source_task", ["target1"], file_reference_keys=["output1", "output2"])
        
        assert "result" in target1_context.local_context
        assert "metrics" in target1_context.local_context
        assert "output1" in target1_context.file_paths
        assert "output2" in target1_context.file_paths
        
        # Test propagating only specified context keys and file references
        manager.propagate_results("source_task", ["target2"], 
                                 keys=["result"], 
                                 file_reference_keys=["output1"])
        
        assert "result" in target2_context.local_context
        assert "metrics" not in target2_context.local_context
        assert "output1" in target2_context.file_paths
        assert "output2" not in target2_context.file_paths
        
        # Verify source task information added to file reference
        assert "references" in target2_context.file_paths["output1"]["metadata"]
        reference = target2_context.file_paths["output1"]["metadata"]["references"][0]
        assert reference["source_task"] == "source_task"
        
        # Test propagating non-existent source task
        with pytest.raises(ValueError):
            manager.propagate_results("non_existent", ["target1"])
    
    def test_get_execution_summary(self):
        """Test getting execution summary functionality"""
        manager = ContextManager()
        
        # Create task context and add data
        task_context = TaskContext("test_task", manager.global_context)
        task_context.update_local("success", True)
        task_context.update_local("output", "Test output")
        task_context.update_local("metrics", {"precision": 0.9, "recall": 0.85})
        task_context.add_execution_record("start", "Task started")
        task_context.add_execution_record("complete", "Task completed")
        manager.task_contexts["test_task"] = task_context
        
        # Test getting execution summary
        summary = manager.get_execution_summary("test_task")
        
        assert summary["task_id"] == "test_task"
        assert summary["success"] is True
        assert summary["output"] == "Test output"
        assert summary["key_metrics"]["precision"] == 0.9
        assert summary["execution_events"] == 2  # execution_events is the count, not the actual events
        assert summary["last_event"]["action"] == "complete"
        
        # Test getting non-existent task summary
        with pytest.raises(ValueError):
            manager.get_execution_summary("non_existent")
    
    def test_create_output_directories(self, temp_dir):
        """Test creating output directories functionality"""
        context_dir = os.path.join(temp_dir, "context")
        manager = ContextManager(context_dir)
        
        # Define test subtasks
        subtasks = [
            {
                "id": "task1",
                "name": "Task 1",
                "output_files": {
                    "main_result": "results/task1/result.json",
                    "report": "results/task1/report.md"
                }
            },
            {
                "id": "task2",
                "name": "Task 2",
                "output_files": {
                    "main_result": "results/task2/result.json",
                    "models": "results/task2/models/"
                }
            }
        ]
        
        # Test creating output directories
        manager.create_output_directories(subtasks)
        
        # Verify directory and subtask definition file creation
        assert os.path.exists(os.path.join(context_dir, "results", "task1"))
        assert os.path.exists(os.path.join(context_dir, "results", "task2"))
        assert os.path.exists(os.path.join(context_dir, "results", "task2", "models"))
        assert os.path.exists(os.path.join(context_dir, "subtasks", "task1.json"))
        assert os.path.exists(os.path.join(context_dir, "subtasks", "task2.json"))
        
        # Verify subtask definition file content
        with open(os.path.join(context_dir, "subtasks", "task1.json"), "r") as f:
            task1_def = json.load(f)
            assert task1_def["id"] == "task1"
            assert task1_def["name"] == "Task 1"
    
    def test_save_load_all_contexts(self, temp_dir):
        """Test saving and loading all contexts functionality"""
        context_dir = os.path.join(temp_dir, "context")
        manager = ContextManager(context_dir)
        
        # Add global context data
        manager.global_context["global_key"] = "global_value"
        
        # Create task contexts
        task1_context = TaskContext("task1", manager.global_context)
        task1_context.update_local("key1", "value1")
        manager.task_contexts["task1"] = task1_context
        
        task2_context = TaskContext("task2", manager.global_context)
        task2_context.update_local("key2", "value2")
        manager.task_contexts["task2"] = task2_context
        
        # Add context history records
        manager._log_context_event("create", "task1")
        manager._log_context_event("update", "task2", data={"key": "value"})
        
        # Save all contexts
        manager.save_all_contexts()
        
        # Verify file creation
        assert os.path.exists(os.path.join(context_dir, "global_context.json"))
        assert os.path.exists(os.path.join(context_dir, "task_task1.json"))
        assert os.path.exists(os.path.join(context_dir, "task_task2.json"))
        assert os.path.exists(os.path.join(context_dir, "context_history.json"))
        
        # Create new manager and load contexts
        new_manager = ContextManager(context_dir)
        new_manager.load_all_contexts()
        
        # Verify loaded result
        assert new_manager.global_context["global_key"] == "global_value"
        assert "task1" in new_manager.task_contexts
        assert "task2" in new_manager.task_contexts
        assert new_manager.task_contexts["task1"].local_context["key1"] == "value1"
        assert len(new_manager.context_history) == 2
        
    def test_log_context_event(self):
        """Test logging context event functionality"""
        manager = ContextManager()
        
        # Test logging various events
        manager._log_context_event("create", "task1")
        manager._log_context_event("update", "task2", "secondary", {"key": "value"})
        
        # Verify event logging
        assert len(manager.context_history) == 2
        assert manager.context_history[0]["event_type"] == "create"
        assert manager.context_history[0]["primary_id"] == "task1"
        assert manager.context_history[1]["event_type"] == "update"
        assert manager.context_history[1]["secondary_id"] == "secondary"
        assert manager.context_history[1]["data"] == {"key": "value"}