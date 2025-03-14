#!/usr/bin/env python3
"""
Example demonstrating the use of TwoAgentChat with StandardLLMAgent and config_list format.

This example shows how to use the StandardLLMAgent with AG2-compatible config_list format,
which is the recommended approach for configuring LLM agents in AG2-Agent.
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
from ag2_engine.adapters.standard_llm_agent import StandardLLMAgent

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class HumanAgent:
    """Human agent implementation that takes input from the console."""
    
    def __init__(self, name: str = "Human"):
        """Initialize a human agent.
        
        Args:
            name: The name of the agent
        """
        self.name = name
        
    async def generate_response(self, message: str, 
                               history: Optional[List[Dict[str, Any]]] = None,
                               context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get input from the human user.
        
        Args:
            message: The message to respond to
            history: Optional chat history
            context: Optional context information
            
        Returns:
            Dictionary containing the human's input with 'content' and 'role'
        """
        print(f"\nReceived: {message}")
        response = input(f"{self.name}> ")
        return {
            "content": response,
            "role": "user"
        }
        
    def bind_tools(self, tools: Dict[str, Any]) -> None:
        """Bind tools to this agent (implementing AG2-Agent interface)."""
        # Human agents don't use tools in this example
        pass


async def async_main():
    """Run a demo of TwoAgentChat with StandardLLMAgent"""
    
    # Set up detailed logging for debugging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Check API key
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("Error: OPENROUTER_API_KEY environment variable not set.")
        print("Please set it with: export OPENROUTER_API_KEY=your_api_key")
        return
    
    # Print API key status (but not the actual key for security)
    print(f"API key status: {'Valid' if api_key else 'Invalid'} (length: {len(api_key) if api_key else 0})")
    
    # Create an AG2Executor instance
    config = {
        "agents": {
            "assistant": {
                "name": "AI助手",
                "type": "llm",
                "system_message": "You are a helpful, friendly assistant. Your responses should be concise and to the point.",
                "llm_config": {
                    "config_list": [
                        # Primary configuration using OpenRouter
                        {
                            "api_type": "openai",
                            "model": "google/gemini-2.0-flash-lite-001",  # Using Gemini through OpenRouter
                            "api_key": api_key,
                            "base_url": "https://openrouter.ai/api/v1",
                            "extra_headers": {
                                "HTTP-Referer": "https://github.com/anthropics/claude-code",
                                "X-Title": "AG2-Agent-Test",
                            }
                        },
                        # Fallback configuration using a different model
                        {
                            "api_type": "openai",
                            "model": "anthropic/claude-3-haiku-20240307",  # Fallback to Claude via OpenRouter
                            "api_key": api_key,
                            "base_url": "https://openrouter.ai/api/v1",
                            "extra_headers": {
                                "HTTP-Referer": "https://github.com/anthropics/claude-code",
                                "X-Title": "AG2-Agent-Test",
                            }
                        }
                    ]
                }
            },
            "human": {
                "name": "用户",
                "type": "custom",
                "agent_instance": HumanAgent(name="Human")
            }
        },
        "chat_settings": {
            "mode": "two_agent",
            "config": {
                "max_turns": 10
            }
        }
    }
    
    executor = AG2Executor(config)
    
    # Set up a callback to print messages
    def print_message(data):
        # Ensure messages are clearly displayed
        sender = data.get('sender', 'Unknown')
        message = data.get('message', '')
        print(f"\n{sender}: {message}")
        print("-" * 50)
    
    # Create a two-agent chat
    print("\n--- Starting Two-Agent Chat with StandardLLMAgent ---")
    print("Type 'exit' to end the conversation")
    
    # Initiate the chat
    response = await executor.execute_async(
        "Hello! How can I help you today?", 
        mode="two_agent",
        agents={"user": "human", "assistant": "assistant"},
        callbacks={
            'response_received': print_message,
            'message_sent': print_message
        }
    )
    
    print("\n--- Chat Summary ---")
    print(f"Status: {response.get('status', 'unknown')}")
    print("--- End of Demo ---\n")


def main():
    """Run the async main function"""
    asyncio.run(async_main())


if __name__ == "__main__":
    main()