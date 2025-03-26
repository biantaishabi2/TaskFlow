# MCPTool Package
# This package provides an interface for MCP tools in AG2 Executor

from .config import add_server, remove_server, list_servers, get_server
from .client_sdk import MCPClient, MCPServer, MCPError, TransportError
from .MCPTool import MCPTool

# 客户端导入信息
print("使用MCP SDK客户端")

__all__ = [
    'MCPTool', 'MCPClient', 'MCPServer', 'MCPError', 'TransportError',
    'add_server', 'remove_server', 'list_servers', 'get_server'
]
