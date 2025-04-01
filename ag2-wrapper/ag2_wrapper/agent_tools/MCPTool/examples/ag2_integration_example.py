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
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger("ag2_mcp_integration") # Define the logger instance

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

# 导入所需模块
from ag2_wrapper.core.ag2_two_agent_executor import AG2TwoAgentExecutor
from ag2_wrapper.agent_tools.MCPTool import MCPTool, MCPClient
from ag2_wrapper.agent_tools.MCPTool.config import add_server, remove_server, list_servers
from ag2_wrapper.core.config import ConfigManager
from ag2_wrapper.core.ag2tools import AG2ToolManager
from ag2_wrapper.core.ag2_context import ContextManager
# from task_planner.core.context_management import TaskContext # Might not be needed directly here


# 提供一个MCP客户端和工具的单例
_mcp_client: Optional[MCPClient] = None
_mcp_tool: Optional[MCPTool] = None


async def get_mcp_tool() -> MCPTool:
    """获取MCPTool实例（单例模式）"""
    global _mcp_client, _mcp_tool
    
    if _mcp_tool is None:
        logger.info("初始化MCPTool...")
        _mcp_client = MCPClient()
        _mcp_tool = MCPTool(_mcp_client)
        # 初始化 MCPClient (加载服务器配置等)
        try:
             await _mcp_client.initialize()
             logger.info("MCPClient 初始化完成")
        except Exception as e:
             logger.error(f"MCPClient 初始化失败: {e}", exc_info=True)
             # Decide how to handle initialization failure, maybe raise?
             raise RuntimeError("MCP Client initialization failed") from e
        logger.info("MCPTool 实例准备就绪")
    return _mcp_tool


async def cleanup_mcp_resources():
    """清理MCP资源"""
    global _mcp_client
    if _mcp_client:
        logger.info("清理MCP客户端资源...")
        try:
            await _mcp_client.disconnect_all()
            logger.info("MCP资源清理完成")
        except Exception as e:
            logger.error(f"清理 MCP 资源时出错: {e}", exc_info=True)


async def configure_mcp_servers():
    """配置MCP服务器示例"""
    logger.info("配置 MCP 服务器...")
    try:
        # 删除任何现有的服务器配置（仅用于示例）
        existing_servers = list_servers()
        logger.info(f"当前服务器配置: {list(existing_servers.keys())}")
        # for name in existing_servers:
        #     logger.debug(f"移除现有服务器配置: {name}")
        #     remove_server(name) # Be careful with removing configs if persistent ones exist
    
        # 添加time服务器（stdio连接）
        logger.info("添加 'time' 服务器配置 (stdio)...")
        add_server("time", {
            "type": "stdio",
            "command": "python", # Make sure python executable is correct
            "args": ["-m", "mcp_server_time"],  # Ensure mcp_server_time is installed/accessible
            "env": {"TZ": "UTC"}
        })
        
        # 注释掉echo服务器配置
        # logger.info("确保 'echo' 服务器配置不存在...")
        # remove_server("echo") # Example: remove echo if it exists

        logger.info(f"服务器配置完成. 当前服务器: {list(list_servers().keys())}")
    except Exception as e:
        logger.error(f"配置 MCP 服务器时出错: {e}", exc_info=True)
        raise RuntimeError("Failed to configure MCP servers") from e


async def demo_create_executor():
    """创建集成了 MCPTool 的 AG2 Executor"""
    # 1. 配置服务器 (确保服务器配置正确)
    await configure_mcp_servers()
    
    # 2. 创建 AG2 管理器
    logger.info("创建 AG2 管理器...")
    config_manager = ConfigManager() # Load AG2 config if needed
    tool_manager = AG2ToolManager()
    ag2_context_manager = ContextManager(cwd=os.getcwd()) # AG2 Context Manager
    
    # 3. 获取 MCPTool 实例 (包含 MCPClient)
    mcp_tool_instance = await get_mcp_tool()
    
    # 4. LLM 配置 (Optional: Load from ConfigManager or define here)
    # System message is now primarily built inside the executor
    llm_config_list = config_manager.config.get('llm', {}).get('default_config_list', [{
        "model": "claude-3-haiku-20240307",
        "api_key": os.environ.get("OPENROUTER_API_KEY") # Ensure API key is set
    }])
    config_manager.set_config("llm", {"default_config_list": llm_config_list})

    # 5. 创建 Executor, 传入 MCPTool 实例
    logger.info("创建 AG2 Executor 并传入 MCPTool 实例...")
    try:
        executor = await AG2TwoAgentExecutor.create(
            config=config_manager,
            tool_manager=tool_manager,
            context_manager=ag2_context_manager, # Pass AG2 Context Manager
            mcp_tool=mcp_tool_instance, # Pass the MCPTool instance
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
    logger.info("=== AG2 Executor 与 MCPTool 集成示例 (异步模式) ===")
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
                        logger.info(f"  - {msg.get('role')}: {msg.get('content')[:200]}...")
                else:
                    logger.info(f"返回结果 (无历史记录): {chat_result}")

            except Exception as e_chat:
                 logger.error(f"执行 initiate_chat 时发生错误: {e_chat}", exc_info=True)

        else:
             logger.error("未能成功创建 AG2 Executor 实例，无法执行任务。")
             
    except Exception as e_main:
        logger.error(f"主流程初始化或执行过程中出错: {e_main}", exc_info=True)
    
    finally:
        logger.info("开始清理 MCP 资源...")
        await cleanup_mcp_resources()
        
    logger.info("=== 示例结束 ===")


if __name__ == "__main__":
    asyncio.run(main())
