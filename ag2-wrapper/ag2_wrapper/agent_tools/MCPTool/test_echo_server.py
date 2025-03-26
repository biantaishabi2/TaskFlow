#!/usr/bin/env python3
"""
简单的MCP Echo服务器 - 用于测试SSE连接

这是一个简单的MCP服务器，它通过SSE连接提供一个简单的echo工具。
用于测试SSE连接功能。
"""

import asyncio
import json
import logging
import os
import sys
import traceback
from typing import Any, List, Sequence

# 设置日志级别
logging.basicConfig(
    level=logging.DEBUG, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("echo-server")

# 打印系统信息
logger.info(f"Python版本: {sys.version}")
logger.info(f"当前工作目录: {os.getcwd()}")
logger.info(f"PYTHONPATH: {os.environ.get('PYTHONPATH', '未设置')}")
logger.info(f"sys.path: {sys.path}")

# 尝试导入必要的模块
try:
    import uvicorn
    from starlette.applications import Starlette
    from starlette.routing import Mount, Route
    
    logger.info("成功导入web框架")
except ImportError as e:
    logger.error(f"导入web框架失败: {e}")
    print(f"错误: 请先安装web框架: pip install uvicorn starlette")
    sys.exit(1)

# 导入MCP SDK组件
try:
    import mcp.types as types
    from mcp.server.lowlevel import Server
    from mcp.server.sse import SseServerTransport
    
    logger.info("成功导入MCP SDK组件")
except ImportError as e:
    logger.error(f"导入MCP SDK失败: {e}")
    print(f"错误: 请先安装MCP SDK: pip install mcp-sdk")
    sys.exit(1)

# 设置服务器端口
SSE_PORT = 8766  # 修改为新端口
logger.info(f"使用端口: {SSE_PORT}")


def create_server():
    """创建一个简单的MCP服务器，提供echo工具"""
    app = Server("mcp-echo-test")

    @app.call_tool()
    async def call_tool(
        name: str, arguments: dict
    ) -> Sequence[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        """处理工具调用"""
        logger.info(f"收到工具调用: {name}, 参数: {arguments}")
        
        if name != "echo":
            raise ValueError(f"未知工具: {name}")
        
        message = arguments.get("message", "未提供消息")
        logger.info(f"Echo消息: {message}")
        
        return [types.TextContent(type="text", text=f"Echo: {message}")]

    @app.list_tools()
    async def list_tools() -> List[types.Tool]:
        """列出可用工具"""
        logger.info("收到工具列表请求")
        return [
            types.Tool(
                name="echo",
                description="回显提供的消息",
                inputSchema={
                    "type": "object",
                    "required": ["message"],
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "要回显的消息",
                        }
                    },
                },
            )
        ]
    
    return app


def start_sse_server():
    """启动SSE服务器"""
    try:
        logger.info("创建MCP服务器...")
        app = create_server()
        
        logger.info("创建SSE传输...")
        sse = SseServerTransport("/messages/")
        
        async def handle_sse(request):
            """处理SSE连接请求"""
            try:
                client_info = getattr(request, 'client', 'Unknown')
                logger.info(f"收到SSE连接请求: {client_info}")
                
                logger.info("建立SSE连接...")
                async with sse.connect_sse(
                    request.scope, request.receive, request._send
                ) as streams:
                    logger.info("SSE连接已建立，运行MCP服务器...")
                    options = app.create_initialization_options()
                    logger.debug(f"初始化选项: {options}")
                    await app.run(streams[0], streams[1], options)
            except Exception as e:
                logger.error(f"处理SSE连接时出错: {str(e)}")
                logger.error(traceback.format_exc())
                raise
        
        logger.info("创建Starlette应用...")
        starlette_app = Starlette(
            debug=True,
            routes=[
                Route("/sse", endpoint=handle_sse),
                Mount("/messages/", app=sse.handle_post_message),
            ],
        )
        
        logger.info(f"启动SSE服务器在端口 {SSE_PORT}")
        uvicorn.run(starlette_app, host="0.0.0.0", port=SSE_PORT, log_level="debug")
    
    except Exception as e:
        logger.error(f"启动SSE服务器时出错: {str(e)}")
        logger.error(traceback.format_exc())
        raise


if __name__ == "__main__":
    try:
        logger.info("======= 启动MCP Echo服务器 =======")
        start_sse_server()
    except KeyboardInterrupt:
        logger.info("服务器被用户中断")
        sys.exit(0)
    except Exception as e:
        logger.error(f"服务器出错: {str(e)}")
        logger.error(traceback.format_exc())
        sys.exit(1)