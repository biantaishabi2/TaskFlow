#!/usr/bin/env python3
"""
AG2 Executor与MCPTool集成示例

这个示例演示如何在AG2 Executor中集成MCPTool，使AG2能够调用MCP服务器的工具。
"""

import asyncio
import logging
import os
import sys
import json
from typing import Optional, Dict, Any, List

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ag2_mcp_integration")

# 确保能导入需要的模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

# 导入AG2 Executor和MCPTool
from ag2_wrapper.core.ag2_two_agent_executor import AG2TwoAgentExecutor
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
    
    # 注释掉echo服务器配置，因为没有运行中的echo服务器
    # add_server("echo", {
    #     "type": "sse",
    #     "url": "http://localhost:8765/sse",  # echo服务器URL
    # })
    
    logger.info("服务器配置完成")


async def demo_execute_time_tool():
    """演示调用时间服务器工具"""
    # 配置服务器
    await configure_mcp_servers()
    
    # 创建AG2 Executor
    logger.info("创建AG2 Executor...")
    
    # 创建配置管理器
    from ag2_wrapper.core.config import ConfigManager
    config = ConfigManager()
    
    # 使用create_llm_config方法创建LLM配置，明确指示使用MCP工具
    llm_config = config.create_llm_config(
        model="claude-3-haiku-20240307",
        system_message="""你是一个助手，必须严格按照以下规则操作：

1. 直接使用mcp__time__get_current_time工具获取时间，参数格式为{"timezone": "Asia/Tokyo"}
2. 禁止使用任何shell命令（如ls、date、pwd、echo等），即使你认为它们可能有用
3. 不要先尝试查看环境、检查文件或列出目录
4. 不要解释你将要做什么，直接执行工具调用
5. 当用户要求获取时间信息时，立即调用mcp__time__get_current_time工具

示例:
用户: "获取东京的当前时间"
你的回应: [直接调用mcp__time__get_current_time工具]

记住：不要思考其他方法，不要列出选项，不要解释为什么或如何使用工具，只需立即使用mcp__time__get_current_time工具。
"""
    )
    
    # 将创建的配置设置到config对象
    config.set_config("llm", {"default_config_list": llm_config["config_list"]})
    
    # 创建工具管理器 - 这是关键步骤，必须先创建
    from ag2_wrapper.core.ag2tools import AG2ToolManager
    tool_manager = AG2ToolManager()
    
    # 创建上下文管理器
    from ag2_wrapper.core.ag2_context import ContextManager
    context_manager = ContextManager()
    
    # **** 重要 ****
    # 先注册MCP工具到工具管理器，再创建executor
    logger.info("先注册MCP工具到工具管理器...")
    mcp_tool = await get_mcp_tool()
    
    # 获取所有可用工具
    logger.info("获取MCP工具列表...")
    tools = await mcp_tool.get_tools()
    
    # 打印工具的提示词信息
    logger.info("======== 工具提示词信息 ========")
    for tool in tools:
        tool_name = tool["name"]
        description = tool.get("description", "无描述")
        parameters = tool.get("parameters", {})
        
        print(f"\n===== 工具: {tool_name} =====")
        print(f"描述: {description}")
        print(f"参数: {json.dumps(parameters, indent=2, ensure_ascii=False)}")
    logger.info("======== 提示词信息结束 ========")
    
    # 注册工具
    registered_tools = []
    from ag2_wrapper.core.base_tool import BaseTool
    
    # 创建每个工具的类定义
    for tool in tools:
        tool_name = tool["name"]
        logger.info(f"准备注册工具: {tool_name}")
        
        # 创建MCP工具类
        class MCPToolWrapper(BaseTool):
            """MCP工具包装器"""
            
            def __init__(self):
                # 初始化基类
                super().__init__()
                # 设置工具属性
                self._mcp_tool = mcp_tool
                self._mcp_tool_name = tool_name
                self._description = tool.get("description", "")
                self._parameters = tool.get("parameters", {})
                
            @property
            def name(self) -> str:
                return tool_name
            
            @property
            def description(self) -> str:
                return self._description
                
            @property
            def parameters(self) -> dict:
                return self._parameters
            
            async def execute(self, **kwargs):
                """执行工具调用"""
                logger.info(f"执行MCP工具: {self._mcp_tool_name}，参数: {kwargs}")
                return await self._mcp_tool.execute(self._mcp_tool_name, kwargs)
        
        # 创建更详细和明确的工具提示词
        detailed_prompt = f"""
这是一个专用工具，用于获取或转换时间信息。

使用说明:
1. 直接使用此工具，不要使用shell命令
2. 参数格式: {json.dumps(tool.get('parameters', {}), indent=2)}
3. 如需时区参数，使用标准格式如 "timezone": "Asia/Tokyo"

示例:
如用户要求"获取东京时间"，直接调用此工具，参数为 {{"timezone": "Asia/Tokyo"}}

禁止:
- 不要使用ls、date或其他shell命令
- 不要先尝试查看目录
- 直接调用此工具获取结果
"""
        
        # 注册工具类
        try:
            # 在执行器的工具管理器中注册工具
            tool_manager.register_tool(
                tool_class=MCPToolWrapper,  # 工具类
                prompt=detailed_prompt,  # 更详细的工具提示词
                context=None  # 没有特殊上下文
            )
            registered_tools.append(tool_name)
            logger.info(f"成功预注册工具: {tool_name}")
        except Exception as e:
            logger.error(f"预注册工具 {tool_name} 失败: {str(e)}")
    
    logger.info(f"共预注册了 {len(registered_tools)} 个MCP工具")
    
    # 现在创建executor，它会自动包含我们注册的工具
    executor = await AG2TwoAgentExecutor.create(
        config=config,
        tool_manager=tool_manager,  # 传入已经包含MCP工具的工具管理器
        context_manager=context_manager,
        task_context="使用工具获取信息，优先使用MCP工具而不是shell命令"
    )
    
    logger.info("AG2 Executor已创建，并包含预注册的MCP工具")
    
    # 返回executor和注册的工具列表
    return executor, registered_tools


def main_sync():
    """同步主函数，避免嵌套事件循环问题"""
    logger.info("=== AG2 Executor与MCPTool集成示例 ===")
    
    # 创建新的事件循环
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # 设置服务器和创建executor（异步部分）
        executor, registered_tools = loop.run_until_complete(demo_execute_time_tool())
        
        if any("time" in tool for tool in registered_tools):
            # 执行带时间工具的查询（同步部分）
            logger.info("执行带时间工具的查询...")
            
            # 获取时间工具名称
            time_tool_name = next(t for t in registered_tools if "time" in t and "current" in t)
            logger.info(f"找到时间工具: {time_tool_name}")
            
            # 直接使用MCPTool进行调用，绕过AG2 Executor
            logger.info("尝试直接使用MCPTool进行工具调用...")
            
            # 获取MCPTool实例
            mcp_tool = loop.run_until_complete(get_mcp_tool())
            
            # 调用工具
            params = {"timezone": "Asia/Tokyo"}
            logger.info(f"直接调用工具 {time_tool_name}，参数: {params}")
            
            # 执行工具调用
            result = loop.run_until_complete(mcp_tool.execute(time_tool_name, params))
            logger.info(f"MCPTool直接调用结果: {result}")
            
            # 现在尝试用AG2 Executor执行（可能会有事件循环问题）
            message = """获取东京（日本）的当前时间。

请直接使用mcp__time__get_current_time工具，参数为{"timezone": "Asia/Tokyo"}。
不要使用任何shell命令，不要先尝试分析环境。
"""
            logger.info(f"尝试通过AG2 Executor发送消息: {message}")
            
            try:
                # 使用executor执行
                logger.info("尝试使用executor.execute()方法...")
                result = executor.execute(message)
                logger.info(f"AG2 Executor执行结果: {result}")
            except RuntimeError as e:
                if "This event loop is already running" in str(e):
                    logger.error("检测到事件循环嵌套错误，使用executor.execute()方法失败")
                else:
                    logger.error(f"执行出错: {str(e)}")
                    
        else:
            logger.warning("未找到时间工具，跳过执行")
    
        # 清理资源（异步部分）
        loop.run_until_complete(cleanup_mcp_resources())
    
    except Exception as e:
        logger.error(f"执行出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
    
    finally:
        # 关闭事件循环
        loop.close()
        
    logger.info("=== 示例结束 ===")


if __name__ == "__main__":
    # 使用同步主函数替代异步main
    main_sync()