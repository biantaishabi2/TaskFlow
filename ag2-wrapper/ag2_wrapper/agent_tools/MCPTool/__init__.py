# MCPTool Package
# This package provides an interface for MCP tools in AG2 Executor

import os
from .config import add_server, remove_server, list_servers, get_server

# 默认使用SDK实现，可通过环境变量切换
USE_SDK_CLIENT = os.environ.get("MCP_USE_SDK_CLIENT", "1").lower() in ("1", "true", "yes")

# 导入适当的客户端
if USE_SDK_CLIENT:
    try:
        # 尝试导入SDK版本
        from .client_sdk import MCPClient, MCPServer, MCPError, TransportError
        from .MCPTool import MCPTool
        print("使用SDK版本的MCP客户端")
    except ImportError:
        # 如果失败，回退到旧版本
        from .client import MCPClient, MCPServer, MCPError, TransportError
        from .MCPTool import MCPTool
        print("使用旧版本的MCP客户端（SDK导入失败）")
else:
    # 强制使用旧版本
    from .client import MCPClient, MCPServer, MCPError, TransportError
    from .MCPTool import MCPTool
    print("使用旧版本的MCP客户端（由环境变量指定）")

__all__ = [
    'MCPTool', 'MCPClient', 'MCPServer', 'MCPError', 'TransportError',
    'add_server', 'remove_server', 'list_servers', 'get_server'
]
