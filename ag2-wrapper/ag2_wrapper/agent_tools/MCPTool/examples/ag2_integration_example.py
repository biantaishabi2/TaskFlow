#!/usr/bin/env python3
"""
AG2 Executor与MCPTool集成示例 (重构后)

这个示例演示如何在 AG2 Executor 中集成 MCPTool，
Executor 内部会处理 MCP 工具的发现、注册和提示词生成。
"""

import asyncio
import logging
import os
import sys
import json
from typing import Optional, Dict, Any, List
from pathlib import Path

# Set global logging level to WARNING to reduce verbosity
logging.basicConfig(level=logging.INFO) # Temporarily set back to INFO for debugging
logger = logging.getLogger("ag2_mcp_integration") # Define the logger instance
logging.getLogger("autogen.tools.function_utils").setLevel(logging.ERROR) # Suppress warnings from this specific logger

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

# 导入所需模块
from ag2_wrapper.core.ag2_two_agent_executor import AG2TwoAgentExecutor
from ag2_wrapper.agent_tools.MCPTool import MCPTool
from ag2_wrapper.core.config import ConfigManager
from ag2_wrapper.core.ag2tools import AG2ToolManager
from ag2_wrapper.core.ag2_context import ContextManager
# from task_planner.core.context_management import TaskContext # Might not be needed directly here


async def demo_create_executor():
    """创建集成了 MCPTool 的 AG2 Executor (依赖内部初始化)"""
    # 2. 创建 AG2 管理器
    logger.info("创建 AG2 管理器...")
    config_manager = ConfigManager() # Load AG2 config if needed - MUST contain mcp.servers for internal init
    tool_manager = AG2ToolManager()
    ag2_context_manager = ContextManager(cwd=os.getcwd()) # AG2 Context Manager

    # 4. LLM 配置 (Optional: Load from ConfigManager or define here)
    # System message is now primarily built inside the executor
    llm_config_list = config_manager.config.get('llm', {}).get('default_config_list', [{
        "model": "claude-3-haiku-20240307",
        "api_key": os.environ.get("OPENROUTER_API_KEY") # Ensure API key is set
    }])
    config_manager.set_config("llm", {"default_config_list": llm_config_list})

    # 5. 创建 Executor, 不再传入 MCPTool 实例
    logger.info("创建 AG2 Executor (将尝试内部初始化 MCPTool)...")
    try:
        executor = await AG2TwoAgentExecutor.create(
            config=config_manager,
            tool_manager=tool_manager,
            context_manager=ag2_context_manager, # Pass AG2 Context Manager
            task_context="使用工具获取信息，优先使用MCP工具而不是shell命令" # Example task context
            # use_human_input=False # Default
        )
        logger.info("AG2 Executor 已成功创建。")
        return executor
    except Exception as e:
        logger.error(f"创建 AG2 Executor 失败: {e}", exc_info=True)
        return None


async def main():
    """主异步执行流程"""
    logger.info("=== AG2 Executor 与 MCPTool 集成示例 (依赖内部初始化) ===")
    executor = None
    try:
        # 创建 executor (内部处理工具注册)
        logger.info("开始创建 Executor...")
        executor = await demo_create_executor()

        if executor:
            logger.info("Executor 创建成功，准备执行任务查询...")
            message = """获取东京（日本）的当前时间。"""
            logger.info(f"发送消息给 Executor: {message}")

            try:
                logger.info("尝试调用 executor.executor.a_initiate_chat()...")
                chat_result = await executor.executor.a_initiate_chat(
                    executor.assistant,
                    message=message
                )
                logger.info(f"AG2 Executor a_initiate_chat 完成.")

                # Print the chat history or summary
                if hasattr(chat_result, 'summary'):
                     logger.info(f"对话总结: {chat_result.summary}")
                if hasattr(chat_result, 'chat_history'):
                    logger.info("完整对话历史:")
                    for msg in chat_result.chat_history:
                        # Log only if level is INFO or lower (since we set ERROR globally)
                        if logger.isEnabledFor(logging.INFO):
                             logger.info(f"  - {msg.get('role')}: {msg.get('content')[:200]}...")
                else:
                    # Log only if level is INFO or lower
                    if logger.isEnabledFor(logging.INFO):
                         logger.info(f"返回结果 (无历史记录): {chat_result}")

            except Exception as e_chat:
                 logger.error(f"执行 initiate_chat 时发生错误: {e_chat}", exc_info=True)

        else:
             logger.error("未能成功创建 AG2 Executor 实例，无法执行任务。")

    except Exception as e_main:
        logger.error(f"主流程初始化或执行过程中出错: {e_main}", exc_info=True)

    finally:
        # Note: Internal MCP client cleanup is not explicitly handled here.
        # It might rely on __del__ or other mechanisms if implemented.
        logger.info("MCP 资源清理逻辑已移除 (依赖 Executor 内部处理或无显式清理)")

    logger.info("=== 示例结束 ===")


if __name__ == "__main__":
    asyncio.run(main())
