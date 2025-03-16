#!/usr/bin/env python3
"""
测试ToolManager的继续功能
"""

import os
import sys
import json
import logging
from unittest.mock import patch, MagicMock, AsyncMock

# 配置日志
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('test_continue')

# 添加项目路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def setup_mocks():
    """设置所需的mock对象"""
    # 创建claude_api的mock
    claude_api_mock = MagicMock()
    
    # 第一次调用返回CONTINUE状态
    first_call = {
        "status": "success", 
        "output": "我开始处理任务，但需要继续...",
        "error_msg": "",
        "task_status": "CONTINUE"
    }
    
    # 第二次调用返回完成状态
    second_call = {
        "status": "success",
        "output": "任务已完成，这是结果",
        "error_msg": "",
        "task_status": "COMPLETED"
    }
    
    # 设置mock的side_effect，使第一次调用返回first_call，第二次返回second_call
    claude_api_mock.side_effect = [first_call, second_call]
    
    return claude_api_mock

def test_tool_manager_continue():
    """测试ToolManager的继续功能"""
    try:
        # 导入需要的模块
        from task_planner.core.task_executor import TaskExecutor
        from task_planner.vendor.claude_client.agent_tools.tool_manager import ToolManager
        from task_planner.core.tools.claude_tools import ClaudeInputTool
        from task_planner.vendor.claude_client.agent_tools.parser import DefaultResponseParser
    except ImportError as e:
        logger.error(f"导入模块失败: {e}")
        return False
    
    logger.info("开始测试ToolManager的继续功能")
    
    # 创建Claude API的mock
    claude_api_mock = setup_mocks()
    
    # 创建任务
    task = {
        "id": "continue_test",
        "name": "自动继续测试",
        "instruction": "测试使用ToolManager的继续功能",
        "output_files": {
            "main_result": os.path.join(os.getcwd(), "output/logs/subtasks_execution/continue_test_result.json")
        }
    }
    
    # 使用mock替换claude_api
    with patch('task_planner.core.task_executor.claude_api', claude_api_mock):
        # 创建执行器
        executor = TaskExecutor(verbose=True)
        
        # 运行任务
        with patch.object(executor, '_verify_output_files', return_value=[]):
            result = executor.execute_subtask(task)
        
    # 验证结果
    logger.info(f"执行结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
    
    # 验证claude_api被调用次数
    logger.info(f"Claude API被调用了 {claude_api_mock.call_count} 次")
    assert claude_api_mock.call_count == 2, f"Claude API应该被调用两次，但实际调用了 {claude_api_mock.call_count} 次"
    
    # 验证任务ID和状态
    assert result["task_id"] == "continue_test", f"任务ID应为continue_test，但实际为 {result.get('task_id')}"
    
    logger.info("测试完成")
    return True

if __name__ == "__main__":
    success = test_tool_manager_continue()
    sys.exit(0 if success else 1)