"""
Test configuration and fixtures
"""

import pytest
import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing"""
    tmp_dir = tempfile.mkdtemp()
    yield tmp_dir
    # Clean up after test
    shutil.rmtree(tmp_dir)

@pytest.fixture
def test_data_dir(temp_dir):
    """Create test data directory structure"""
    data_dir = os.path.join(temp_dir, "test_data")
    os.makedirs(data_dir, exist_ok=True)
    
    # Create subdirectories
    for subdir in ["subtasks", "results", "logs"]:
        os.makedirs(os.path.join(data_dir, subdir), exist_ok=True)
    
    yield data_dir

@pytest.fixture(autouse=True)
def mock_openai():
    """自动为所有测试模拟OpenAI，避免API调用"""
    with patch('task_planner.core.task_planner.OpenAI') as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        
        # 模拟chat.completions接口
        mock_instance.chat = MagicMock()
        mock_instance.chat.completions = MagicMock()
        mock_instance.chat.completions.create = MagicMock()
        
        yield mock