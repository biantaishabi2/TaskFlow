#!/usr/bin/env python3
"""
AG2执行器示例 - 展示如何使用标准config_list格式配置LLM并执行任务
"""

import os
import sys
import logging
import asyncio

# 添加项目根目录到sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ag2_engine.ag2_executor import AG2Executor

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_example():
    """运行AG2执行器示例"""
    # 设置API密钥
    if "OPENROUTER_API_KEY" not in os.environ:
        print("请设置OPENROUTER_API_KEY环境变量来运行此示例")
        print("使用: export OPENROUTER_API_KEY=your_api_key")
        return
    
    print("\n=== AG2执行器示例 - 使用标准LLM配置 ===\n")
    
    # 创建AG2执行器 - 使用配置文件
    executor = AG2Executor(
        config_path="configs/ag2_config.yaml",
        mode="sequential"  # 使用顺序模式
    )
    
    # 显示配置的代理
    print("已加载的代理:")
    for name, agent_config in executor.config.get('agents', {}).items():
        print(f"  {name}: {agent_config.get('name')}")
    
    # 测试简单任务
    task = {
        "description": "请分析以下数据集并提供洞见：销售额同比增长15%，但客户满意度下降5%。"
    }
    
    print("\n执行任务:")
    print(f"  {task['description']}")
    print("\n正在处理...\n")
    
    # 执行任务
    result = executor.execute(task)
    
    # 显示结果
    print("执行结果:")
    print(f"  状态: {result['status']}")
    print("\n分析:")
    print(result['result'])
    
    # 使用不同模式执行
    print("\n\n=== 使用群组对话模式 ===\n")
    
    group_executor = AG2Executor(
        config_path="configs/ag2_config.yaml",
        mode="group"  # 使用群组模式
    )
    
    task = {
        "description": "针对电子商务网站的功能降级，制定一个风险缓解计划。"
    }
    
    print("执行任务:")
    print(f"  {task['description']}")
    print("\n正在处理...\n")
    
    # 执行任务
    result = group_executor.execute(task)
    
    # 显示结果
    print("执行结果:")
    print(f"  状态: {result['status']}")
    print("\n计划:")
    print(result['result'])
    
    print("\n=== 示例完成 ===")

if __name__ == "__main__":
    run_example()