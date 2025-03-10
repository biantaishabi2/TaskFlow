#!/usr/bin/env python3
"""
Example demonstrating the sequential chat mode in AG2-Engine using real LLM APIs.

This example shows how to create and use a sequential chat where multiple agents
process a task in sequence, with each agent building on the work of previous agents.
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

# Custom context handler for processing responses between agents
def extract_task_info(previous_context: Dict[str, Any], current_info: Dict[str, Any]) -> Dict[str, Any]:
    """Extract and organize information from agent responses."""
    updated_context = previous_context.copy()
    
    # Store agent responses in structured format
    if 'agent' in current_info and 'response' in current_info:
        agent_role = current_info['agent']
        response = current_info['response']
        
        # Initialize the sections dict if it doesn't exist
        if 'sections' not in updated_context:
            updated_context['sections'] = {}
        
        # Store responses by role with specific processing for each role
        if agent_role == 'planner':
            updated_context['plan'] = response
            updated_context['sections']['plan'] = response
        elif agent_role == 'coder':
            updated_context['code'] = response
            updated_context['sections']['code'] = response
        elif agent_role == 'reviewer':
            updated_context['review'] = response
            updated_context['sections']['review'] = response
        
        # Always track the latest agent and response
        updated_context['last_agent'] = agent_role
        updated_context['last_response'] = response
    
    # Add all remaining information
    for key, value in current_info.items():
        if key not in ['agent']:  # Skip keys that are handled specially
            updated_context[key] = value
    
    return updated_context


async def main():
    # Check for OpenRouter API key
    if not os.environ.get("OPENROUTER_API_KEY"):
        print("⚠️ OpenRouter API key not found in environment. You can set it with:")
        print("export OPENROUTER_API_KEY='your-api-key-here'")
        return
    
    # Configuration for the AG2Executor
    config = {
        "agents": {
            "planner": {
                "name": "规划专家",
                "type": "llm",
                "system_message": "You are a planning expert. Break down tasks into clear, logical steps. Be thorough but concise.",
                "llm_config": {
                    "config_list": [
                        {
                            "api_type": "openai",
                            "model": "google/gemini-2.0-flash-lite-001",
                            "api_key": "${OPENROUTER_API_KEY}",
                            "base_url": "https://openrouter.ai/api/v1",
                            "temperature": 0.7,
                            "extra_headers": {
                                "HTTP-Referer": "https://github.com/anthropics/claude-code",
                                "X-Title": "AG2-Agent-Sequential-Chat",
                            }
                        },
                        {
                            "api_type": "openai",
                            "model": "anthropic/claude-3-haiku-20240307",
                            "api_key": "${OPENROUTER_API_KEY}",
                            "base_url": "https://openrouter.ai/api/v1",
                            "temperature": 0.7,
                            "extra_headers": {
                                "HTTP-Referer": "https://github.com/anthropics/claude-code",
                                "X-Title": "AG2-Agent-Sequential-Chat",
                            }
                        }
                    ]
                }
            },
            "coder": {
                "name": "编程专家",
                "type": "llm",
                "system_message": "You are a coding expert. Implement clean, efficient code based on plans. Include comments and handle edge cases.",
                "llm_config": {
                    "config_list": [
                        {
                            "api_type": "openai",
                            "model": "google/gemini-2.0-flash-lite-001",
                            "api_key": "${OPENROUTER_API_KEY}",
                            "base_url": "https://openrouter.ai/api/v1",
                            "temperature": 0.7,
                            "extra_headers": {
                                "HTTP-Referer": "https://github.com/anthropics/claude-code",
                                "X-Title": "AG2-Agent-Sequential-Chat",
                            }
                        }
                    ]
                }
            },
            "reviewer": {
                "name": "代码审核员",
                "type": "llm",
                "system_message": "You are a code reviewer. Check code for bugs, edge cases, performance issues, and suggest improvements.",
                "llm_config": {
                    "config_list": [
                        {
                            "api_type": "openai",
                            "model": "google/gemini-2.0-flash-lite-001",
                            "api_key": "${OPENROUTER_API_KEY}",
                            "base_url": "https://openrouter.ai/api/v1",
                            "temperature": 0.7,
                            "extra_headers": {
                                "HTTP-Referer": "https://github.com/anthropics/claude-code",
                                "X-Title": "AG2-Agent-Sequential-Chat",
                            }
                        }
                    ]
                }
            }
        },
        "chat_settings": {
            "mode": "sequential",
            "config": {
                "context_handler": extract_task_info,
                "max_turns": 5
            }
        }
    }
    
    # Create AG2Executor instance
    executor = AG2Executor(config)
    
    # Start the sequential process with a task description
    task = "Create a Python function that calculates the factorial of a number recursively, with proper error handling for negative numbers and non-integer inputs."
    print(f"\n🔄 Starting sequential chat with task: {task}\n")
    
    # Execute the task with sequential chat
    result = await executor.execute_async(
        task,
        mode="sequential",
        agents={"planner": "planner", "coder": "coder", "reviewer": "reviewer"}
    )
    
    # Display results
    if result and 'context' in result and 'sections' in result['context']:
        for section, content in result['context']['sections'].items():
            print(f"\n--- {section.upper()} ---")
            print(content)
    
    print("\n✅ Sequential chat example completed.\n")


if __name__ == "__main__":
    asyncio.run(main())