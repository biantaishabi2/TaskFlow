"""
Test TaskContext class functionality
"""

import pytest
import os
import json
import tempfile
from datetime import datetime
from task_planner.core.context_management import TaskContext

class TestTaskContext:
    
    def test_init(self):
        """Test TaskContext initialization"""
        context = TaskContext("test_task")
        assert context.task_id == "test_task"
        assert context.global_context == {}
        assert context.local_context == {}
        assert context.file_paths == {}
        assert context.execution_history == []
        assert context.base_dir is None
        
        # Test init with global_context and base_dir
        global_context = {"key": "value"}
        base_dir = "/test/dir"
        context = TaskContext("test_task", global_context, base_dir)
        assert context.global_context == global_context
        assert context.base_dir == base_dir
    
    def test_update_context(self):
        """Test update context methods"""
        context = TaskContext("test_task")
        
        # Test update global context
        context.update_global("global_key", "global_value")
        assert context.global_context["global_key"] == "global_value"
        
        # Test update local context
        context.update_local("local_key", "local_value")
        assert context.local_context["local_key"] == "local_value"
    
    def test_add_file_reference(self, temp_dir):
        """Test adding file reference functionality"""
        context = TaskContext("test_task")
        
        # Create test files
        test_files = {
            "python_file.py": "code",
            "data_file.json": "data",
            "text_file.md": "text",
            "image_file.png": "image",
            "unknown_file.xyz": "unknown"
        }
        
        for file_name, expected_type in test_files.items():
            file_path = os.path.join(temp_dir, file_name)
            with open(file_path, "w") as f:
                f.write("test content")
            
            # Test auto type inference
            ref_name = f"ref_{file_name}"
            context.add_file_reference(ref_name, file_path)
            
            assert ref_name in context.file_paths
            assert context.file_paths[ref_name]["path"] == file_path
            assert context.file_paths[ref_name]["metadata"]["type"] == expected_type
            
            # Test setting custom metadata
            metadata = {"type": "custom_type", "custom_key": "custom_value"}
            custom_ref_name = f"custom_{file_name}"
            context.add_file_reference(custom_ref_name, file_path, metadata)
            
            assert custom_ref_name in context.file_paths
            assert context.file_paths[custom_ref_name]["metadata"] == metadata
    
    def test_add_execution_record(self):
        """Test adding execution record functionality"""
        context = TaskContext("test_task")
        
        # Add execution record
        action = "test_action"
        result = "test_result"
        metadata = {"key": "value"}
        
        context.add_execution_record(action, result, metadata)
        
        assert len(context.execution_history) == 1
        record = context.execution_history[0]
        assert record["action"] == action
        assert record["result"] == result
        assert record["metadata"] == metadata
        assert "timestamp" in record
    
    def test_get_file_content(self, temp_dir):
        """Test getting file content functionality"""
        context = TaskContext("test_task")
        
        # Create test text file
        text_file_path = os.path.join(temp_dir, "test.txt")
        text_content = "test text content"
        with open(text_file_path, "w") as f:
            f.write(text_content)
        
        # Create test JSON file
        json_file_path = os.path.join(temp_dir, "test.json")
        json_content = {"key": "value"}
        with open(json_file_path, "w") as f:
            json.dump(json_content, f)
        
        # Add file references
        context.add_file_reference("text_file", text_file_path, {"type": "text"})
        context.add_file_reference("json_file", json_file_path, {"type": "data"})
        
        # Test getting text file content
        assert context.get_file_content("text_file") == text_content
        
        # Test getting JSON file content
        assert context.get_file_content("json_file") == json_content
        
        # Test getting non-existent file reference
        assert context.get_file_content("non_existent") is None
    
    def test_serialize_deserialize(self):
        """Test serialization and deserialization functionality"""
        # Create and populate context
        context = TaskContext("test_task", {"global_key": "global_value"}, "/test/base_dir")
        context.update_local("local_key", "local_value")
        context.add_file_reference("test_file", "/test/file.txt", {"type": "text"})
        context.add_execution_record("test_action", "test_result", {"meta_key": "meta_value"})
        
        # Serialize
        serialized = context.serialize()
        
        # Verify serialization result
        assert serialized["task_id"] == "test_task"
        assert serialized["global_context"] == {"global_key": "global_value"}
        assert serialized["local_context"] == {"local_key": "local_value"}
        assert "test_file" in serialized["file_paths"]
        assert len(serialized["execution_history"]) == 1
        assert serialized["base_dir"] == "/test/base_dir"
        
        # Deserialize
        deserialized = TaskContext.deserialize(serialized)
        
        # Verify deserialization result
        assert deserialized.task_id == context.task_id
        assert deserialized.global_context == context.global_context
        assert deserialized.local_context == context.local_context
        assert "test_file" in deserialized.file_paths
        assert deserialized.file_paths["test_file"]["path"] == context.file_paths["test_file"]["path"]
        assert len(deserialized.execution_history) == len(context.execution_history)
    
    def test_save_load_file(self, temp_dir):
        """Test saving to file and loading from file functionality"""
        # Create and populate context
        context = TaskContext("test_task", {"global_key": "global_value"}, "/test/base_dir")
        context.update_local("local_key", "local_value")
        context.add_file_reference("test_file", "/test/file.txt", {"type": "text"})
        context.add_execution_record("test_action", "test_result", {"meta_key": "meta_value"})
        
        # Save to file
        file_path = os.path.join(temp_dir, "context.json")
        context.save_to_file(file_path)
        
        # Verify file exists
        assert os.path.exists(file_path)
        
        # Load from file
        loaded_context = TaskContext.load_from_file(file_path)
        
        # Verify loaded result
        assert loaded_context.task_id == context.task_id
        assert loaded_context.global_context == context.global_context
        assert loaded_context.local_context == context.local_context
        assert "test_file" in loaded_context.file_paths
        assert loaded_context.file_paths["test_file"]["path"] == context.file_paths["test_file"]["path"]
        assert len(loaded_context.execution_history) == len(context.execution_history)