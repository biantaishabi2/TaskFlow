"""
Test configuration and fixtures for v3 refactor tests
"""

import pytest
import os
import shutil
import tempfile
import json
from unittest.mock import patch, MagicMock, AsyncMock

@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing"""
    tmp_dir = tempfile.mkdtemp()
    yield tmp_dir
    # Clean up after test
    shutil.rmtree(tmp_dir)

@pytest.fixture
def test_task_definition():
    """Create a test task definition"""
    return {
        "id": "test_task_1",
        "name": "测试任务",
        "description": "这是一个测试任务",
        "output_files": {
            "main_result": "/tmp/test_result.json"
        },
        "success_criteria": ["创建输出文件"]
    }

@pytest.fixture
def mock_gemini():
    """Mock Gemini API for testing"""
    with patch('task_planner.vendor.claude_client.agent_tools.gemini_analyzer.genai') as mock:
        # Create mock Gemini model
        mock_model = MagicMock()
        mock_model.generate_content.return_value = MagicMock(
            text="COMPLETED"
        )
        mock.GenerativeModel.return_value = mock_model
        yield mock

@pytest.fixture
def mock_claude_api():
    """Mock claude_api function"""
    with patch('task_planner.util.claude_cli.claude_api') as mock:
        mock.return_value = {
            "status": "success",
            "output": "我已经完成了任务...",
            "error_msg": "",
            "task_status": "COMPLETED"
        }
        yield mock

@pytest.fixture
def mock_tool_execution():
    """Mock tool execution methods"""
    with patch('task_planner.vendor.claude_client.agent_tools.tool_manager.ToolManager.execute_tool') as mock:
        async def async_mock(*args, **kwargs):
            return MagicMock(
                success=True,
                message="成功执行工具调用",
                response="工具调用结果"
            )
        
        mock.side_effect = AsyncMock(side_effect=async_mock)
        yield mock

@pytest.fixture
def mock_run_async_tool():
    """Mock _run_async_tool in TaskExecutor"""
    with patch('task_planner.core.task_executor.TaskExecutor._run_async_tool') as mock:
        # 设置mock返回值
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.message = "工具执行成功"
        mock_result.response = "执行结果"
        mock.return_value = mock_result
        
        yield mock