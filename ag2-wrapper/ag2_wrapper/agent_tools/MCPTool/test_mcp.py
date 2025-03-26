"""
MCPTool 测试脚本 - 简化版

专门用于测试add和printEnv工具，确保资源正确清理。
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# 添加父目录到导入路径
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from ag2_wrapper.agent_tools.MCPTool import (
    MCPTool, 
    MCPClient, 
    add_server
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("MCPTool_Simple_Test")

async def test_everything_tools():
    """测试everything服务器的工具调用，特别是add和printEnv工具"""
    print("===== 测试 everything 服务器工具 =====")
    
    # 创建服务器配置
    add_server("everything", {
        "type": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-everything"]
    })
    print("* 已配置everything服务器")
    
    # 创建客户端
    client = None
    
    try:
        # 使用上下文管理器创建客户端
        client = MCPClient()
        print("* 创建客户端成功")
        
        # 连接服务器
        server = await client.connect_server("everything")
        print("* 连接服务器成功")
        
        # 获取工具列表
        tools = await server.list_tools()
        print(f"* 发现 {len(tools)} 个工具")
        
        # 测试add工具
        print("\n* 测试add工具...");
        add_result = await server.execute_tool("add", {"a": 40, "b": 2})
        print(f"* Add工具返回: {add_result}")
        
        # 测试printEnv工具
        print("\n* 测试printEnv工具...");
        env_result = await server.execute_tool("printEnv", {})
        
        if 'content' in env_result and isinstance(env_result['content'], list):
            first_item = env_result['content'][0] if env_result['content'] else {}
            if first_item.get('type') == 'text':
                text = first_item.get('text', '')
                lines = text.split('\n')
                line_count = min(5, len(lines))
                print(f"* PrintEnv响应示例 (前{line_count}行):")
                for i in range(line_count):
                    print(f"*   {lines[i]}")
            print(f"* PrintEnv工具测试成功")
        
        print("\n* 工具测试成功完成")
        return True
        
    except Exception as e:
        print(f"* 测试失败: {str(e)}")
        return False
        
    finally:
        # 确保资源清理
        if client:
            print("\n* 清理客户端资源...")
            try:
                # 使用超时保护
                await asyncio.wait_for(client.disconnect_all(), timeout=5.0)
                print("* 资源清理成功")
            except asyncio.TimeoutError:
                print("* 资源清理超时")
            except Exception as e:
                print(f"* 资源清理出错: {str(e)}")

def kill_child_processes():
    """终止所有子进程，确保清理完毕"""
    try:
        import psutil
        current_process = psutil.Process()
        children = current_process.children(recursive=True)
        
        if children:
            print(f"发现 {len(children)} 个子进程，正在终止...")
            for child in children:
                try:
                    print(f"终止进程 {child.pid} ({child.name()})")
                    child.terminate()
                except Exception as e:
                    print(f"终止进程时出错: {str(e)}")
            
            # 等待进程终止
            gone, alive = psutil.wait_procs(children, timeout=3)
            print(f"已终止 {len(gone)} 个进程，剩余 {len(alive)} 个")
            
            # 强制终止剩余进程
            for proc in alive:
                try:
                    proc.kill()
                    print(f"强制终止进程 {proc.pid}")
                except:
                    pass
            
            # 再次等待
            psutil.wait_procs(alive, timeout=1)
            
    except ImportError:
        print("psutil模块未安装，无法完全清理子进程")
    except Exception as e:
        print(f"清理子进程时出错: {str(e)}")

if __name__ == "__main__":
    try:
        # 直接运行测试，不使用复杂的取消机制
        success = asyncio.run(test_everything_tools())
        print(f"\n测试结果: {'成功' if success else '失败'}")
    except KeyboardInterrupt:
        print("\n测试被用户中断")
    finally:
        print("\n===== 清理资源 =====")
        kill_child_processes()
        print("\n===== 测试完成 =====")