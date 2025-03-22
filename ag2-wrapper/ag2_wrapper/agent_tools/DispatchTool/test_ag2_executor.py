"""
测试 AG2 Two Agent Executor
用于验证 AG2 Executor 的基本功能和工具调用
"""
import os
import sys
import logging
from pathlib import Path
import asyncio
from typing import Dict, Any

# 配置日志级别
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.append(str(project_root))

from ag2_wrapper.core.ag2_two_agent_executor import AG2TwoAgentExecutor
from task_planner.core.context_management import TaskContext

async def main():
    # 确保设置了必要的环境变量
    if not os.environ.get("OPENROUTER_API_KEY"):
        raise ValueError("请先设置 OPENROUTER_API_KEY 环境变量")

    # 设置测试环境变量
    os.environ["NODE_ENV"] = "test"
    
    # 初始化执行器和上下文
    executor = AG2TwoAgentExecutor()
    task_context = TaskContext("test_ag2")
    
    # 设置文件读取时间戳记录
    read_timestamps = {}
    
    # 定义综合测试任务
    task_definition = {
        "id": "test_ag2_001",
        "name": "AG2执行器综合测试",
        "description": "测试AG2执行器的各项基本功能",
        "success_criteria": [
            "成功执行所有工具调用",
            "工具之间正确配合",
            "返回预期的结果"
        ]
    }

    try:
        # 执行测试任务
        prompt = """
        请帮我测试以下功能：

        1. 列出该目录/home/wangbo/document/wangbo/dev/webhook下的文件
        2. 用grep命令搜索README.md文件中包含"test"的行
        3. 读取README.md文件内容
        4. 在README.md文件最后添加一行内容："test"

        请执行每个步骤并告诉我执行结果。
        """

        result = executor.execute(
            prompt=prompt,
            task_definition=task_definition,
            task_context=task_context
        )
        
        # 打印测试结果
        if result.get("success", False):
            logging.info("\n=== 测试执行成功 ===")
            logging.info(result.get("result", "无详细结果"))
        else:
            logging.error("\n=== 测试执行失败 ===")
            logging.error(f"错误信息: {result.get('error_msg', '未知错误')}")
            
    except Exception as e:
        logging.error(f"测试执行过程中发生错误: {str(e)}")
        raise

if __name__ == "__main__":
    # 运行测试
    asyncio.run(main())