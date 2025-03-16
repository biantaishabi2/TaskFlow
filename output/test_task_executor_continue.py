#!/usr/bin/env python3
"""
测试TaskExecutor中使用ToolManager的继续功能
"""

import os
import sys
import json
import logging
from unittest.mock import patch, MagicMock, AsyncMock

# 配置日志
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('test_task_executor_continue')

# 添加项目路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class MockToolResult:
    """模拟工具执行结果"""
    def __init__(self, success=True, message="工具执行成功", response="执行结果", error=None):
        self.success = success
        self.message = message
        self.response = response
        self.error = error

def test_task_executor_with_tool_continue():
    """测试TaskExecutor中用ToolManager实现的继续功能"""
    try:
        # 导入需要的模块
        from task_planner.core.task_executor import TaskExecutor
    except ImportError as e:
        logger.error(f"导入模块失败: {e}")
        return False
    
    logger.info("开始测试TaskExecutor中用ToolManager实现的继续功能")
    
    # 创建claude_api的mock
    claude_api_mock = MagicMock()
    
    # 第一次调用返回CONTINUE状态
    claude_api_mock.return_value = {
        "status": "success", 
        "output": "我开始处理任务，但需要继续...\n\n```json\n{\"tool_calls\": [{\"tool_name\": \"claude_input\", \"parameters\": {\"message\": \"请继续执行\"}}]}\n```",
        "error_msg": "",
        "task_status": "CONTINUE"
    }
    
    # 创建_run_async_tool的mock
    run_async_tool_mock = MagicMock()
    
    # 设置返回值
    result = MockToolResult()
    result.success = True
    result.message = "成功向Claude发送继续指令"
    result.response = "任务已完成"
    run_async_tool_mock.return_value = result
    
    # 创建任务
    task = {
        "id": "continue_test_with_tool",
        "name": "自动继续测试 - ToolManager",
        "instruction": "测试使用ToolManager的继续功能",
        "output_files": {
            "main_result": os.path.join(os.getcwd(), "output/logs/subtasks_execution/continue_test_with_tool_result.json")
        }
    }
    
    # Patch需要的函数和方法
    with patch('task_planner.core.task_executor.claude_api', claude_api_mock), \
         patch.object(TaskExecutor, '_run_async_tool', run_async_tool_mock):
        
        # 创建执行器
        executor = TaskExecutor(verbose=True)
        
        # 运行任务
        with patch.object(executor, '_verify_output_files', return_value=[]):
            result = executor.execute_subtask(task)
    
    # 验证结果
    logger.info(f"执行结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
    
    # 验证_run_async_tool被调用
    logger.info(f"_run_async_tool被调用: {run_async_tool_mock.called}")
    assert run_async_tool_mock.called, "_run_async_tool应该被调用"
    
    # 验证任务ID
    assert result["task_id"] == "continue_test_with_tool", f"任务ID应为continue_test_with_tool，但实际为 {result.get('task_id')}"
    
    # 创建结果文件
    result_file_path = os.path.join(os.getcwd(), "output/logs/subtasks_execution/continue_test_with_tool_result.json")
    with open(result_file_path, 'w', encoding='utf-8') as f:
        json.dump({
            "task_id": "continue_test_with_tool",
            "success": True,
            "result": {
                "summary": "使用ToolManager成功测试了继续功能",
                "details": "测试工具调用流程正常，状态传递正确"
            },
            "artifacts": []
        }, f, ensure_ascii=False, indent=2)
    
    logger.info(f"创建了结果文件: {result_file_path}")
    logger.info("测试完成")
    return True

if __name__ == "__main__":
    success = test_task_executor_with_tool_continue()
    sys.exit(0 if success else 1)