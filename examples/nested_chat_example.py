#!/usr/bin/env python3
"""
NestedChat模式示例 - 演示如何使用AG2引擎的嵌套对话模式实现层次化对话
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
        print("=== NestedChat模式示例 - 嵌套对话演示 ===\n")
        
        # 从环境变量读取API密钥
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            print("错误: 未设置OPENROUTER_API_KEY环境变量")
            print("请使用: export OPENROUTER_API_KEY=your_api_key 设置环境变量")
            return
        
        # AG2Executor配置
        config = {
            "agents": {
                "planner": {
                    "name": "规划专家",
                    "type": "llm",
                    "system_message": "你是一位项目规划专家，专注于分解复杂问题。当你需要深入解决某个子问题时，你会创建子任务，要求'请创建一个子对话来解决这个问题'。",
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
                                    "X-Title": "AG2-Agent-NestedChat",
                                }
                            }
                        ]
                    }
                },
                "developer": {
                    "name": "开发专家",
                    "type": "llm",
                    "system_message": "你是一位经验丰富的开发人员，专注于编写高质量代码。你会详细解释你的实现方案。",
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
                                    "X-Title": "AG2-Agent-NestedChat",
                                }
                            }
                        ]
                    }
                },
                "reviewer": {
                    "name": "质量专家",
                    "type": "llm",
                    "system_message": "你是一位代码审查和质量保证专家。你会仔细审查解决方案，提出改进建议。",
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
                                    "X-Title": "AG2-Agent-NestedChat",
                                }
                            }
                        ]
                    }
                }
            },
            "chat_settings": {
                "mode": "nested_chat",
                "config": {
                    "max_depth": 2,  # 最大嵌套深度
                    "context_sharing": "bidirectional"  # 双向上下文共享
                }
            }
        }
        
        # 创建AG2Executor实例
        executor = AG2Executor(config)
        
        # 启动主对话
        print("启动主对话...")
        main_task = "我需要开发一个简单的待办事项应用，包括添加、完成和删除任务功能。请帮我规划一下。"
        
        # 执行嵌套对话
        result = await executor.execute_async(
            main_task,
            mode="nested_chat",
            agents={
                "parent": "planner",
                "child_agents": {
                    "developer": "developer",
                    "reviewer": "reviewer"
                }
            },
            callbacks={
                'message_sent': print_message,
                'response_received': print_message
            }
        )
        
        # 显示嵌套对话结果
        print("\n=== 嵌套对话结果 ===")
        print(f"状态: {result.get('status', '未知')}")
        
        if 'child_chats' in result:
            print(f"子对话数量: {len(result['child_chats'])}")
            
        if 'final_result' in result:
            print("\n最终结果:")
            print(result['final_result'])
        
        print("\n=== 嵌套对话示例完成 ===")
        
    except Exception as e:
        logger.error(f"错误: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())