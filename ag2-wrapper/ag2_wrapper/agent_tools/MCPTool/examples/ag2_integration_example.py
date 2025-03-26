#!/usr/bin/env python3
"""
AG2 Executor与MCPTool集成示例

这个示例演示如何在AG2 Executor中集成MCPTool，使AG2能够调用MCP服务器的工具。
"""

import asyncio
import logging
import os
import sys
from typing import Optional, Dict, Any, List

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ag2_mcp_integration")

# 确保能导入需要的模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

# 导入AG2 Executor和MCPTool
from ag2_wrapper.core.ag2_executor import AG2TwoAgentExecutor
from ag2_wrapper.agent_tools.MCPTool import MCPTool, MCPClient
from ag2_wrapper.agent_tools.MCPTool.config import add_server, remove_server, list_servers

# 提供一个MCP客户端和工具的单例
_mcp_client: Optional[MCPClient] = None
_mcp_tool: Optional[MCPTool] = None


async def get_mcp_tool() -> MCPTool:
    """获取MCPTool实例（单例模式）"""
    global _mcp_client, _mcp_tool
    
    if _mcp_tool is None:
        logger.info("初始化MCPTool...")
        
        # 初始化客户端
        _mcp_client = MCPClient()
        
        # 初始化工具
        _mcp_tool = MCPTool(_mcp_client)
        
        # 确保客户端初始化
        await _mcp_client.initialize()
        logger.info("MCPTool初始化完成")
    
    return _mcp_tool


async def cleanup_mcp_resources():
    """清理MCP资源"""
    global _mcp_client
    
    if _mcp_client:
        logger.info("清理MCP客户端资源...")
        await _mcp_client.disconnect_all()
        logger.info("MCP资源清理完成")


async def configure_mcp_servers():
    """配置MCP服务器示例"""
    # 删除任何现有的服务器配置（仅用于示例）
    existing_servers = list_servers()
    for name in existing_servers:
        remove_server(name)
    
    logger.info("添加MCP服务器配置...")
    
    # 添加time服务器（stdio连接）
    add_server("time", {
        "type": "stdio",
        "command": "python",
        "args": ["-m", "mcp_server_time"],  # 假设已安装时间服务器
        "env": {"TZ": "UTC"}  # 可选环境变量
    })
    
    # 添加echo服务器（SSE连接）
    add_server("echo", {
        "type": "sse",
        "url": "http://localhost:8765/sse",  # echo服务器URL
    })
    
    logger.info("服务器配置完成")


async def register_mcp_tools_to_executor(executor: AG2TwoAgentExecutor) -> List[str]:
    """将MCP工具注册到AG2 Executor
    
    Args:
        executor: AG2 Executor实例
        
    Returns:
        已注册的工具名称列表
    """
    # 获取MCPTool
    mcp_tool = await get_mcp_tool()
    
    # 获取所有可用工具
    logger.info("获取MCP工具列表...")
    tools = await mcp_tool.get_tools()
    
    # 注册工具
    registered_tools = []
    for tool in tools:
        tool_name = tool["name"]
        logger.info(f"注册工具: {tool_name}")
        executor.register_tool(tool)
        registered_tools.append(tool_name)
    
    logger.info(f"共注册了 {len(registered_tools)} 个MCP工具")
    return registered_tools


async def demo_execute_time_tool():
    """演示调用时间服务器工具"""
    try:
        # 配置服务器
        await configure_mcp_servers()
        
        # 创建AG2 Executor
        logger.info("创建AG2 Executor...")
        executor = await AG2TwoAgentExecutor.create(
            model="claude-3-haiku-20240307",
            system_prompt="你是一个有用的助手",
            tools_prompt="使用工具获取信息"
        )
        
        # 注册MCP工具
        registered_tools = await register_mcp_tools_to_executor(executor)
        
        if any("time" in tool for tool in registered_tools):
            # 执行带时间工具的查询
            logger.info("执行带时间工具的查询...")
            
            time_tool = next(t for t in registered_tools if "time" in t and "current" in t)
            result = await executor.execute(
                "获取东京的当前时间",
                tools=[time_tool]
            )
            
            logger.info(f"执行结果: {result}")
        else:
            logger.warning("未找到时间工具，跳过执行")
        
    except Exception as e:
        logger.error(f"执行出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
    
    finally:
        # 清理资源
        await cleanup_mcp_resources()


async def main():
    """主函数"""
    logger.info("=== AG2 Executor与MCPTool集成示例 ===")
    
    # 运行演示
    await demo_execute_time_tool()
    
    logger.info("=== 示例结束 ===")


if __name__ == "__main__":
    asyncio.run(main())