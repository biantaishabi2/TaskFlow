#!/usr/bin/env python3
"""
测试MCPTool导入和基本功能
"""

import os
import sys

# 确保环境变量设置
os.environ["MCP_USE_SDK_CLIENT"] = "1"

# 添加包路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    # 尝试导入
    from ag2_wrapper.agent_tools.MCPTool import MCPClient, MCPTool, MCPError, TransportError
    from ag2_wrapper.agent_tools.MCPTool.config import add_server, remove_server, list_servers
    
    print("导入成功!")
    print(f"MCPTool类型: {type(MCPTool).__name__}")
    print(f"MCPClient类型: {type(MCPClient).__name__}")
    print(f"MCPError类型: {type(MCPError).__name__}")
    print(f"TransportError类型: {type(TransportError).__name__}")
    
    # 测试配置功能
    print("\n测试配置功能:")
    add_server("test_server", {
        "type": "stdio",
        "command": "echo",
        "args": ["Hello"]
    })
    
    servers = list_servers()
    print(f"服务器列表: {list(servers.keys())}")
    
    remove_server("test_server")
    servers = list_servers()
    print(f"移除后服务器列表: {list(servers.keys())}")
    
    print("\n所有测试通过!")
    
except Exception as e:
    print(f"测试失败: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)