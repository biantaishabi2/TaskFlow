 # minimal_ag2_mcp_test.py
import asyncio
import logging
import os
import sys
from pathlib import Path

# Ensure necessary modules can be imported
script_dir = Path(__file__).parent
root_dir = script_dir.parent.parent.parent.parent # Adjust based on actual structure
sys.path.append(str(root_dir))

# Imports
from ag2_wrapper.core.ag2_two_agent_executor import AG2TwoAgentExecutor
from ag2_wrapper.agent_tools.MCPTool import MCPTool, MCPClient
from ag2_wrapper.core.config import ConfigManager
from ag2_wrapper.core.ag2tools import AG2ToolManager
from ag2_wrapper.core.ag2_context import ContextManager

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MinimalAG2MCPTest")

async def run_minimal_test():
    """Runs a minimal test using AG2TwoAgentExecutor with MCPTool."""
    logger.info("--- Starting Minimal AG2 MCP Test ---")
    
    mcp_client = None
    executor = None
    
    try:
        # 1. Initialize MCP Client and Tool
        logger.info("Initializing MCPClient and MCPTool...")
        mcp_client = MCPClient() # Assumes config is in default location
        mcp_tool = MCPTool(mcp_client)
        await mcp_client.initialize() # Loads config, finds 'time' server
        logger.info("MCP Components Initialized.")

        # 2. Create basic AG2 Managers
        logger.info("Creating AG2 Managers...")
        config_manager = ConfigManager()
        tool_manager = AG2ToolManager()
        ag2_context_manager = ContextManager(cwd=os.getcwd())
        logger.info("AG2 Managers Created.")

        # 3. Create AG2 Executor, passing MCPTool
        # This implicitly calls _initialize_tools and _build_tools_prompt
        logger.info("Creating AG2TwoAgentExecutor...")
        try:
            executor = await AG2TwoAgentExecutor.create(
                config=config_manager,
                tool_manager=tool_manager,
                context_manager=ag2_context_manager,
                mcp_tool=mcp_tool,
                task_context="Minimal test context"
            )
            logger.info("AG2TwoAgentExecutor created successfully.")
        except Exception as create_e:
             logger.error(f"Failed to create AG2TwoAgentExecutor: {create_e}", exc_info=True)
             return # Stop if executor creation fails

        # 4. Initiate Chat
        if executor and executor.executor and executor.assistant:
            message = "获取 UTC 时间" # Simple task using the 'time' tool
            logger.info(f"Initiating chat with message: '{message}'")
            try:
                chat_result = await executor.executor.initiate_chat(
                    executor.assistant,
                    message=message
                )
                logger.info("Chat initiated and completed.")
                # Log the result briefly
                if hasattr(chat_result, 'summary'):
                    logger.info(f"Chat Summary: {chat_result.summary}")
                if hasattr(chat_result, 'chat_history') and chat_result.chat_history:
                    logger.info(f"Last message: {chat_result.chat_history[-1]}")
                else:
                    logger.info(f"Chat result object: {chat_result}")

            except Exception as chat_e:
                 logger.error(f"Error during initiate_chat: {chat_e}", exc_info=True)
        else:
            logger.error("Executor or its internal agents are not available.")

    except Exception as e:
        logger.error(f"An error occurred during the test setup: {e}", exc_info=True)
    finally:
        # 5. Cleanup
        if mcp_client:
            logger.info("Cleaning up MCP resources...")
            try:
                await mcp_client.disconnect_all()
                logger.info("MCP cleanup complete.")
            except Exception as clean_e:
                logger.error(f"Error during MCP cleanup: {clean_e}", exc_info=True)
        else:
             logger.info("No MCP client to clean up.")

    logger.info("--- Minimal AG2 MCP Test Finished ---")

if __name__ == "__main__":
    # Make sure the script is run from a location where imports work
    # and where '.mcp/config.json' can be found by MCPClient
    # Typically run from the 'MCPTool' directory or similar.
    logger.info(f"Running script from: {os.getcwd()}")
    logger.info(f"Python executable: {sys.executable}")
    logger.info("Ensure '.mcp/config.json' with the 'time' server is accessible.")
    
    asyncio.run(run_minimal_test())
