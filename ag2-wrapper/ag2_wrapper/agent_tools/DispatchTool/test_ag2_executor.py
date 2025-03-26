"""
测试 AG2 执行器
"""

import asyncio
import os
from pathlib import Path
import sys
import logging
from typing import Dict, Any
import warnings

# 抑制pydantic的警告
warnings.filterwarnings("ignore", message="Valid config keys have changed in V2")

# 设置root logger级别
logging.getLogger().setLevel(logging.WARNING)

# 抑制httpx和urllib3的INFO日志
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('LiteLLM').setLevel(logging.WARNING)
logging.getLogger('litellm').setLevel(logging.WARNING)
logging.getLogger('autogen').setLevel(logging.ERROR)
logging.getLogger('ag2_wrapper').setLevel(logging.WARNING)

# 配置日志级别
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 添加项目根目录到 Python 路径
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent.parent.parent  # task_planner 目录
sys.path.append(str(project_root))

from ag2_wrapper.core.ag2_two_agent_executor import AG2TwoAgentExecutor
from ag2_wrapper.core.config import ConfigManager
from task_planner.core.context_management import TaskContext

async def main():
    # 确保设置了必要的环境变量
    if not os.environ.get("OPENROUTER_API_KEY"):
        raise ValueError("请先设置 OPENROUTER_API_KEY 环境变量")

    # 设置测试环境变量
    os.environ["NODE_ENV"] = "test"
    
    # 初始化配置
    config = ConfigManager()
    
    # 创建并初始化执行器
    executor = await AG2TwoAgentExecutor.create(config=config)
    
    print("执行器初始化成功！")
    
    # 打印系统提示词
    print("\n=== 系统提示词 ===")
    print(executor.assistant.system_message)
    print("\n=== 工具列表 ===")
    print(executor.tool_manager._tools)
    
    # 创建一个简单的测试任务
    test_task = {
        "id": "test_task_001",
        "name": "测试任务",
        "description": "这是一个简单的测试任务",
        "success_criteria": [
            "成功执行命令",
            "返回预期结果"
        ]
    }
    
    # 创建任务上下文
    task_context = TaskContext("test_task")
    
    print("\n=== 开始执行测试任务 ===")
    # 执行一个简单的测试命令
    result = executor.execute(
        prompt="请列出当前目录下的文件和子目录。",
        task_definition=test_task,
        task_context=task_context
    )
    
    print("\n=== 任务执行结果 ===")
    print(f"状态: {result.get('status', 'unknown')}")
    print(f"成功: {result.get('success', False)}")
    if result.get('success', False):
        print("\n输出:")
        print(result.get('output', '无输出'))
    else:
        print("\n错误信息:")
        print(result.get('error_msg', '未知错误'))

if __name__ == "__main__":
    asyncio.run(main())