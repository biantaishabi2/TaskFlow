#!/usr/bin/env python3
"""
Swarm模式示例 - 演示如何使用AG2引擎的Swarm模式实现任务分解和协作
"""

import sys
import os
import logging
import asyncio
from typing import Dict, Any, List, Optional

# Add the parent directory to sys.path to import the package
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from ag2_engine.ag2_executor import AG2Executor

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# 监控回调函数
def log_task_progress(data):
    """记录任务进度"""
    print(f"进度更新: {data}")

# 显示消息回调
def print_message(data):
    """打印消息"""
    sender = data.get('sender', 'Unknown')
    message = data.get('message', '')
    print(f"\n💬 {sender}: {message}")
    print("-" * 50)

async def main():
    """主函数"""
    try:
        print("=== Swarm模式示例 - 数据分析项目 ===\n")
        
        # 从环境变量读取API密钥
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            print("错误: 未设置OPENROUTER_API_KEY环境变量")
            print("请使用: export OPENROUTER_API_KEY=your_api_key 设置环境变量")
            return
        
        # 创建AG2Executor配置
        config = {
            "agents": {
                "coordinator": {
                    "name": "协调专家",
                    "type": "llm",
                    "system_message": "你是一位项目协调专家，专长于将复杂问题分解为可管理的子任务，并确保子任务之间的依赖关系正确。请使用中文回复。",
                    "llm_config": {
                        "config_list": [
                            {
                                "api_type": "openai",
                                "model": "google/gemini-2.0-flash-lite-001",
                                "temperature": 0.7,
                                "api_key": "${OPENROUTER_API_KEY}",
                                "base_url": "https://openrouter.ai/api/v1",
                                "extra_headers": {
                                    "HTTP-Referer": "https://github.com/anthropics/claude-code",
                                    "X-Title": "AG2-Agent-Swarm",
                                }
                            }
                        ]
                    }
                },
                "data_collector": {
                    "name": "数据收集专家",
                    "type": "llm",
                    "system_message": "你是数据收集专家，专注于确定分析所需的数据，以及如何收集和准备这些数据。请使用中文回复。",
                    "llm_config": {
                        "config_list": [
                            {
                                "api_type": "openai",
                                "model": "google/gemini-2.0-flash-lite-001",
                                "temperature": 0.7,
                                "api_key": "${OPENROUTER_API_KEY}",
                                "base_url": "https://openrouter.ai/api/v1",
                                "extra_headers": {
                                    "HTTP-Referer": "https://github.com/anthropics/claude-code",
                                    "X-Title": "AG2-Agent-Swarm",
                                }
                            }
                        ]
                    }
                },
                "data_analyst": {
                    "name": "数据分析专家",
                    "type": "llm",
                    "system_message": "你是数据分析专家，擅长使用统计技术和分析方法从数据中提取有价值的见解。请使用中文回复。",
                    "llm_config": {
                        "config_list": [
                            {
                                "api_type": "openai",
                                "model": "google/gemini-2.0-flash-lite-001",
                                "temperature": 0.7,
                                "api_key": "${OPENROUTER_API_KEY}",
                                "base_url": "https://openrouter.ai/api/v1",
                                "extra_headers": {
                                    "HTTP-Referer": "https://github.com/anthropics/claude-code",
                                    "X-Title": "AG2-Agent-Swarm",
                                }
                            }
                        ]
                    }
                },
                "visualization_expert": {
                    "name": "可视化专家",
                    "type": "llm",
                    "system_message": "你是数据可视化专家，擅长创建有效的图表、图形和仪表板来展示数据分析结果。请使用中文回复。",
                    "llm_config": {
                        "config_list": [
                            {
                                "api_type": "openai",
                                "model": "google/gemini-2.0-flash-lite-001",
                                "temperature": 0.7,
                                "api_key": "${OPENROUTER_API_KEY}",
                                "base_url": "https://openrouter.ai/api/v1",
                                "extra_headers": {
                                    "HTTP-Referer": "https://github.com/anthropics/claude-code",
                                    "X-Title": "AG2-Agent-Swarm",
                                }
                            }
                        ]
                    }
                },
                "report_writer": {
                    "name": "报告撰写专家",
                    "type": "llm",
                    "system_message": "你是报告撰写专家，善于将技术分析结果转化为清晰、引人入胜的书面报告。请使用中文回复。",
                    "llm_config": {
                        "config_list": [
                            {
                                "api_type": "openai",
                                "model": "google/gemini-2.0-flash-lite-001",
                                "temperature": 0.7,
                                "api_key": "${OPENROUTER_API_KEY}",
                                "base_url": "https://openrouter.ai/api/v1",
                                "extra_headers": {
                                    "HTTP-Referer": "https://github.com/anthropics/claude-code",
                                    "X-Title": "AG2-Agent-Swarm",
                                }
                            }
                        ]
                    }
                }
            },
            "chat_settings": {
                "mode": "swarm",
                "config": {
                    "coordinator": "coordinator",  # 指定协调者
                    "synthesizer": "coordinator",  # 指定结果综合者
                    "max_subtasks": 10,  # 最大子任务数
                    "parallel_execution": True  # 允许并行执行
                }
            }
        }
        
        # 创建AG2Executor实例
        executor = AG2Executor(config)
        
        # 主任务
        main_task = """
        需要对一家电子商务网站的客户行为进行分析，目标是提高转化率和客户留存率。
        有三个月的数据可用，包括：用户浏览行为、购买历史、用户人口统计信息和营销活动数据。
        请分析这些数据，找出影响客户转化和留存的关键因素，并提出改进策略。
        最终需要一份完整的分析报告，包括数据见解和建议。
        请使用中文完成所有分析和报告。
        """
        
        print("启动Swarm执行任务...")
        print(f"任务说明: {main_task}\n")
        
        # 执行Swarm任务
        result = await executor.execute_async(
            main_task,
            mode="swarm",
            agents={
                "coordinator": "coordinator",
                "data_collector": "data_collector",
                "data_analyst": "data_analyst", 
                "visualization_expert": "visualization_expert",
                "report_writer": "report_writer"
            },
            callbacks={
                'message_sent': print_message,
                'response_received': print_message,
                'task_received': log_task_progress,
                'tasks_decomposed': log_task_progress,
                'subtask_started': log_task_progress,
                'subtask_completed': log_task_progress,
                'results_synthesized': log_task_progress
            }
        )
        
        # 显示执行结果
        print("\n=== Swarm执行结果 ===")
        print(f"状态: {result.get('status', '未知')}")
        
        if 'subtasks' in result:
            print(f"\n完成的子任务数量: {len(result['subtasks'])}")
            for i, subtask in enumerate(result['subtasks']):
                print(f"\n子任务 {i+1}: {subtask.get('description', '无描述')}")
                print(f"执行者: {subtask.get('assigned_to', '未分配')}")
                print(f"状态: {'完成' if subtask.get('complete', False) else '未完成'}")
        
        if 'final_result' in result:
            print("\n最终综合结果:")
            print(result['final_result'])
        
        print("\n=== Swarm示例完成 ===")
        
    except Exception as e:
        logger.error(f"错误: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())