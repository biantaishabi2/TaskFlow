#!/usr/bin/env python3
"""
Example demonstrating the group chat mode in AG2-Engine.

This example shows how to create and use a group chat where multiple specialized agents
discuss a topic together, with a facilitator guiding the conversation.

The GroupChat mode supports:
- Multiple agents participating in a discussion together
- Round-robin or custom speaking order
- Facilitated discussion with a designated facilitator agent
- Multiple discussion rounds with configurable maximum
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

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def main():
    """Main example function."""
    try:
        # Check for OpenRouter API key
        if not os.environ.get("OPENROUTER_API_KEY"):
            print("⚠️ OpenRouter API key not found. Please set OPENROUTER_API_KEY environment variable.")
            return
        
        # Configuration for AG2Executor
        config = {
            "agents": {
                "tech_expert": {
                    "name": "技术专家",
                    "type": "llm",
                    "system_message": "你是一位人工智能领域的技术专家。你提供关于AI能力和局限性的事实性、技术性见解。"
                                    "请使用中文回答，保持专业且通俗易懂的语言风格。",
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
                                    "X-Title": "AG2-Agent-Group-Chat",
                                }
                            }
                        ]
                    }
                },
                "ethicist": {
                    "name": "伦理专家",
                    "type": "llm",
                    "system_message": "你是一位AI伦理专家，在偏见、公平性和AI技术的社会影响方面有专业知识。"
                                    "在讨论AI部署时，你会提出重要的伦理考量。请使用中文回答，保持专业且通俗易懂的语言风格。",
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
                                    "X-Title": "AG2-Agent-Group-Chat",
                                }
                            }
                        ]
                    }
                },
                "product_manager": {
                    "name": "产品经理",
                    "type": "llm",
                    "system_message": "你是一位专注于AI实际应用的产品经理。你思考市场需求、用户体验和商业可行性。"
                                    "请使用中文回答，保持专业且通俗易懂的语言风格。",
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
                                    "X-Title": "AG2-Agent-Group-Chat",
                                }
                            }
                        ]
                    }
                },
                "facilitator": {
                    "name": "讨论引导者",
                    "type": "llm",
                    "system_message": "你是一位技巧娴熟的讨论引导者。你的角色是总结关键点、找出意见一致/分歧的领域，"
                                    "并引导对话朝着富有成效的结果发展。请使用中文回答，保持简洁明了的引导风格。",
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
                                    "X-Title": "AG2-Agent-Group-Chat",
                                }
                            }
                        ]
                    }
                }
            },
            "chat_settings": {
                "mode": "group_chat",
                "config": {
                    "max_rounds": 3,
                    "facilitator": "facilitator",
                    "speaking_order": "round_robin"
                }
            }
        }
        
        # Create AG2Executor instance
        executor = AG2Executor(config)
        
        # Start group discussion
        print("\n🔄 开始群组讨论...\n")
        initial_message = (
            "让我们讨论在医疗保健领域部署AI系统的潜在益处和风险。"
            "请考虑诊断应用、治疗建议、行政效率、隐私问题和伦理影响等方面。"
        )
        
        # Set up a message printer
        def print_message(data):
            sender = data.get('sender', 'Unknown')
            message = data.get('message', '')
            print(f"\n💬 {sender}: {message}")
            print("-" * 50)
        
        # Execute the task with group chat mode
        context = {"topic": "AI在医疗领域：潜在益处与风险"}
        
        result = await executor.execute_async(
            initial_message,
            mode="group_chat",
            agents={
                "facilitator": "facilitator", 
                "tech_expert": "tech_expert", 
                "ethicist": "ethicist",
                "product_manager": "product_manager"
            },
            context=context,
            callbacks={
                'response_received': print_message,
                'message_sent': print_message
            }
        )
        
        # Display summary
        print("\n=== 讨论摘要 ===")
        if 'turn_count' in result:
            print(f"总回合数: {result['turn_count']}")
        if 'message_count' in result:
            print(f"总消息数: {result['message_count']}")
        
        print("\n✅ 群组讨论示例完成\n")
        
    except Exception as e:
        logger.error(f"Error in group chat example: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())