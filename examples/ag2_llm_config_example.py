#!/usr/bin/env python3
"""
Example demonstrating the use of standard LLM configurations with AG2-Agent

This example shows how to use the StandardLLMAgent with AG2-compatible config_list format,
which is the recommended approach for configuring LLM agents in AG2-Agent.
"""

import sys
import os
import logging
import asyncio
from typing import Dict, Any

# Add the parent directory to sys.path to import the ag2_agent package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# This will be used to add the claude_client path
claude_client_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..', 'claude_client'))
sys.path.insert(0, claude_client_path)

# Import AG2-Agent modules
from ag2_agent import create_orchestration_manager
from ag2_agent.utils.standard_llm_agent import StandardLLMAgent

# For backwards compatibility example
from ag2_agent.utils.llm_config_adapter import ExternalLLMConfig, GeminiAnalyzerConfig

# Import the agent_tools modules
from agent_tools.llm_service import LLMService
from agent_tools.gemini_analyzer import GeminiTaskAnalyzer

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


# Legacy custom agent using the deprecated ExternalLLMConfig (for comparison)
class CustomAssistantAgent:
    """
    Custom assistant agent that uses the external LLM configuration.
    
    NOTE: This is using the deprecated ExternalLLMConfig for backwards compatibility.
    New applications should use StandardLLMAgent instead.
    """
    
    def __init__(self, name: str, llm_config):
        """
        Initialize the custom assistant.
        
        Args:
            name: Agent name
            llm_config: LLM configuration to use
        """
        self.name = name
        self.llm_config = llm_config
        self.system_message = "You are a helpful assistant."
    
    async def generate_response(self, message: str, chat_history: list = None) -> str:
        """
        Generate a response using the LLM configuration.
        
        Args:
            message: The message to respond to
            chat_history: Optional chat history
            
        Returns:
            The generated response
        """
        # Prepare the messages in the format expected by the LLM config
        messages = []
        
        # Add system message
        messages.append({
            'role': 'system',
            'content': self.system_message
        })
        
        # Add chat history if provided
        if chat_history:
            for entry in chat_history:
                role = 'user' if entry.get('sender') == 'user' else 'assistant'
                messages.append({
                    'role': role,
                    'content': entry.get('message', '')
                })
        
        # Add the current message
        messages.append({
            'role': 'user',
            'content': message
        })
        
        # Generate the response
        try:
            result = await self.llm_config.generate(messages)
            return result.get('content', 'No response generated')
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return f"Error generating response: {str(e)}"
    
    def bind_tools(self, tools: Dict[str, Any]) -> None:
        """Bind tools to this agent (implementing AG2-Agent interface)."""
        # This example doesn't use tools
        pass


async def setup_llm_service():
    """Set up a mock LLM service for demonstration."""
    # Dummy LLM call function
    async def call_llm(prompt, system_prompt, messages, stream=False):
        # This is a simple mock for demonstration
        return f"I've processed your request: '{prompt}'. Here's a simulated response based on your question."
    
    # Define roles
    roles = {
        "default": {
            "system_prompt": "You are a helpful assistant."
        },
        "expert": {
            "system_prompt": "You are an expert in various subjects."
        }
    }
    
    # Create LLM service
    llm_service = LLMService(call_llm=call_llm, roles=roles)
    
    return llm_service


async def main():
    """Run the LLM configuration examples."""
    try:
        print("\n=== AG2-Agent LLM Configuration Examples ===")
        # Create an OrchestrationManager
        manager = create_orchestration_manager()
        
        # ===== PART 1: Using StandardLLMAgent with config_list (RECOMMENDED) =====
        print("\n--- Example 1: Using StandardLLMAgent with config_list (RECOMMENDED) ---")
        
        # Create a standard LLM configuration with config_list format
        standard_llm_config = {
            "config_list": [
                {
                    "api_type": "openai",
                    "model": "openai/gpt-3.5-turbo",  # Use a more affordable model for testing
                    "api_key": os.environ.get("OPENROUTER_API_KEY", "demo_key"),
                    "base_url": "https://openrouter.ai/api/v1",  # Use OpenRouter to access various models
                    "system_message": "You are a helpful, friendly assistant specialized in science topics."
                },
                # Backup configuration for fallback
                {
                    "api_type": "openai",
                    "model": "anthropic/claude-3-sonnet-20240229",
                    "api_key": os.environ.get("OPENROUTER_API_KEY", "demo_key"),
                    "base_url": "https://openrouter.ai/api/v1",
                    "temperature": 0.8
                }
            ]
        }
        
        # Create an agent using StandardLLMAgent
        standard_agent = StandardLLMAgent(
            name="StandardAgent",
            llm_config=standard_llm_config
        )
        
        # Print configuration details
        print("Standard LLM Configuration:")
        print(f"- Primary model: {standard_llm_config['config_list'][0]['model']}")
        print(f"- Fallback model: {standard_llm_config['config_list'][1]['model']}")
        print(f"- System message: {standard_agent._system_message[:50]}...")
        
        # Register the agent with the manager
        manager.register_agent("standard_agent", standard_agent)
        
        # ===== PART 2: Legacy Example (For Backward Compatibility) =====
        print("\n--- Example 2: Legacy ExternalLLMConfig (DEPRECATED) ---")
        
        # Set up the mock LLM service
        llm_service = await setup_llm_service()
        
        # Create the external LLM configuration (DEPRECATED)
        external_llm_config = ExternalLLMConfig(
            llm_service=llm_service,
            model_name="custom-llm-model",
            temperature=0.7,
            max_tokens=1000
        )
        
        # Create a Gemini analyzer for task completion detection
        mock_gemini_analyzer = GeminiTaskAnalyzer(api_key=None)  # No API key, will use mock mode
        gemini_config = GeminiAnalyzerConfig(mock_gemini_analyzer)
        
        # Register a custom assistant agent that uses the deprecated external LLM config
        legacy_assistant = CustomAssistantAgent(
            name="LegacyAssistant",
            llm_config=external_llm_config
        )
        manager.register_agent("legacy_assistant", legacy_assistant)
        
        # ===== Create a user agent for both examples =====
        class SimpleUserAgent:
            def __init__(self, name, messages):
                self.name = name
                self.messages = messages.copy()
                self.message_index = 0
                
            async def generate_response(self, message, history=None, context=None):
                response = self.messages[self.message_index]
                self.message_index = (self.message_index + 1) % len(self.messages)
                return response
                
            def bind_tools(self, tools):
                pass
                
        # Create and register user agent
        user_agent = SimpleUserAgent(
            name="User",
            messages=[
                "Hello, how are you today?",
                "Can you tell me about the solar system?",
                "Thanks for your help!"
            ]
        )
        manager.register_agent("user", user_agent)
        
        # ===== Test the StandardLLMAgent first =====
        print("\n--- Running Test with StandardLLMAgent ---")
        try:
            # Create a two-agent chat with the standard agent
            standard_chat = manager.create_chat(
                mode="two_agent",
                agents={"user": "user", "assistant": "standard_agent"},
                initial_prompt="Start a conversation about science topics.",
                config={"max_turns": 3}
            )
            
            # Set up a callback to print messages
            def print_message(data):
                print(f"\n{data['sender']}: {data['message'][:100]}...")
            
            # Register the callback
            standard_chat.register_callback('response_received', print_message)
            standard_chat.register_callback('message_sent', print_message)
            
            # Initiate the chat
            print("\nStarting chat with StandardLLMAgent...")
            response = await standard_chat.initiate_chat("Hello, how are you today?", sender="user")
            
            # Continue the conversation for a few turns
            for _ in range(1):
                response = await standard_chat.continue_chat()
                
            # End the chat
            result = standard_chat.end_chat()
            print("\n--- Standard Agent Chat Summary ---")
            print(f"Total turns: {result['turn_count']}")
            print(f"Agents: {', '.join(result['agents'])}")
            
        except Exception as e:
            logger.error(f"Error in StandardLLMAgent test: {str(e)}")
            print(f"StandardLLMAgent test failed: {str(e)}")
            print("Continuing with legacy example...")
        
        # ===== Test the Legacy Agent second =====
        print("\n--- Running Test with Legacy ExternalLLMConfig (DEPRECATED) ---")
        
        # Create a two-agent chat with the legacy agent
        legacy_chat = manager.create_chat(
            mode="two_agent",
            agents={"user": "user", "assistant": "legacy_assistant"},
            initial_prompt="Start a conversation about science topics.",
            config={"max_turns": 3}
        )
        
        # Register the callback
        legacy_chat.register_callback('response_received', print_message)
        legacy_chat.register_callback('message_sent', print_message)
        
        # Initiate the chat
        print("\nStarting chat with Legacy ExternalLLMConfig...")
        response = await legacy_chat.initiate_chat("Hello, how are you today?", sender="user")
        
        # Continue the conversation for a few turns
        for _ in range(1):
            response = await legacy_chat.continue_chat()
        
        # Demonstrate task completion analysis (legacy feature)
        messages = legacy_chat.get_chat_history()
        last_response = messages[-1]['message'] if messages else ""
        
        task_status = await gemini_config.analyze_chat(
            messages=[{'content': m['message']} for m in messages],
            last_response=last_response
        )
        
        print(f"\nTask completion status: {task_status}")
        
        # End the chat
        result = legacy_chat.end_chat()
        print("\n--- Legacy Agent Chat Summary ---")
        print(f"Total turns: {result['turn_count']}")
        print(f"Agents: {', '.join(result['agents'])}")
        
        # ===== Overall Summary =====
        print("\n=== Configuration Comparison ===")
        print("- StandardLLMAgent: Uses AG2-compatible config_list format")
        print("  * Supports multiple models with fallback")
        print("  * Works with all standard API providers")
        print("  * RECOMMENDED FOR ALL NEW APPLICATIONS")
        
        print("\n- ExternalLLMConfig: Legacy configuration adapter")
        print("  * Limited compatibility with standard APIs")
        print("  * No built-in fallback mechanism")
        print("  * DEPRECATED - Will be removed in future versions")
        
        print("\n=== End of Example ===")
        
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())