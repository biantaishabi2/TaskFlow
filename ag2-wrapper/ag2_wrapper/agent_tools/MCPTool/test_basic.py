"""
MCPTool 基础测试脚本

这个脚本提供了一个简单的测试，用于验证MCPTool的基本功能。
它不依赖于外部服务器，只测试配置加载和对象创建。
"""

import asyncio
import logging
import sys
from pathlib import Path

# 添加父目录到导入路径
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from ag2_wrapper.agent_tools.MCPTool import (
    MCPTool, 
    MCPClient, 
    add_server, 
    remove_server, 
    list_servers,
    get_server
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]  # 确保日志输出到控制台
)
logger = logging.getLogger("MCPTool_Test")
logger.setLevel(logging.INFO)  # 确保日志级别设置正确


async def test_config():
    """测试配置管理"""
    print("* 开始测试配置管理")
    
    # 清理配置
    remove_server("test1")
    remove_server("test2")
    print("* 已清理旧配置")
    
    # 添加测试配置
    add_server("test1", {
        "type": "stdio",
        "command": "echo",
        "args": ["Hello World"]
    })
    print("* 添加测试服务器1: stdio类型")
    
    add_server("test2", {
        "type": "sse",
        "url": "http://localhost:3000/api"
    })
    print("* 添加测试服务器2: sse类型")
    
    # 获取配置
    servers = list_servers()
    print(f"* 配置的服务器数量: {len(servers)}")
    logger.info(f"配置的服务器数量: {len(servers)}")
    
    for name, config in servers.items():
        server_info = f"服务器: {name}, 类型: {config['type']}"
        print(f"* {server_info}")
        logger.info(server_info)
        
        for key, value in config.items():
            if key != "type":
                detail = f"  - {key}: {value}"
                print(f"* {detail}")
                logger.info(detail)
    
    return len(servers) > 0


async def test_client_creation():
    """测试客户端创建"""
    print("* 开始测试客户端创建")
    
    # 创建客户端
    client = MCPClient()
    print("* 客户端对象已创建")
    
    # 初始化客户端
    await client.initialize()
    msg = "客户端初始化成功"
    print(f"* {msg}")
    logger.info(msg)
    
    # 创建工具适配器
    tool = MCPTool(client)
    msg = "工具适配器创建成功"
    print(f"* {msg}")
    logger.info(msg)
    
    return True


async def test_client_configuration():
    """测试客户端配置和对象初始化，不尝试实际连接"""
    print("* 开始测试客户端配置")
    
    # 清理配置
    remove_server("mock_server")
    print("* 已清理mock_server配置")
    
    # 添加模拟服务器配置
    add_server("mock_server", {
        "type": "stdio",
        "command": "echo",
        "args": ["'{\"result\": {\"status\": \"ok\"}}'"]
    })
    print("* 已添加mock_server配置")
    
    # 创建客户端
    client = MCPClient()
    tool = MCPTool(client)
    print("* 已创建MCPClient和MCPTool对象")
    
    # 检查配置是否加载成功
    config = get_server("mock_server")
    if not config:
        error_msg = "无法获取服务器配置"
        print(f"* 错误: {error_msg}")
        logger.error(error_msg)
        return False
    
    msg = f"成功加载服务器配置: {config}"
    print(f"* {msg}")
    logger.info(msg)
    
    # 验证MCPTool对象创建
    msg = f"MCPTool对象: {tool}"
    print(f"* {msg}")
    logger.info(msg)
    
    return True


async def test_everything_server():
    """测试与everything服务器的连接和工具调用
    
    这是核心功能测试，验证与真实MCP服务器的连接流程和工具调用。
    由于服务器可能未安装，此测试如果失败不会影响基础功能验证。
    测试所有主要工具：echo、add、printEnv
    """
    print("\n----- 测试everything服务器连接 -----")
    
    # 清理配置
    remove_server("everything")
    print("* 已清理everything服务器配置")
    
    # 添加everything服务器配置
    add_server("everything", {
        "type": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-everything"]
    })
    print("* 已添加everything服务器配置")
    
    # 创建客户端和服务器对象
    client = MCPClient()
    
    try:
        # 1. 测试连接
        print("* 尝试连接服务器（如果失败可能是npx或服务器未安装）...")
        server = await client.connect_server("everything")
        print("* 连接服务器成功")
        
        # 2. 获取工具列表
        print("* 获取工具列表...")
        try:
            tools = await server.list_tools()
            print(f"* 获取到 {len(tools)} 个工具")
            
            # 显示前3个工具
            for i, tool_info in enumerate(tools[:3]):
                print(f"* 工具 {i+1}: {tool_info.get('name')} - {tool_info.get('description', '无描述')}")
        except Exception as e:
            print(f"* 获取工具列表失败: {str(e)}")
            tools = []  # 使用空列表继续测试
        
        # 创建适配器
        tool = MCPTool(client)
        
        # 3. 测试echo工具
        try:
            print("\n* 测试echo工具...")
            result = await server.execute_tool("echo", {"message": "Hello from echo!"})
            
            if 'content' in result and isinstance(result['content'], list):
                print(f"* Echo工具执行成功，返回了 {len(result['content'])} 条内容")
                
                for item in result['content']:
                    if item.get('type') == 'text':
                        print(f"* Echo响应: {item.get('text', '')}")
            else:
                print(f"* Echo工具执行格式异常: {result}")
        except Exception as e:
            print(f"* Echo工具测试失败: {str(e)}")
        
        # 4. 测试add工具
        try:
            print("\n* 测试add工具...")
            result = await server.execute_tool("add", {"a": 42, "b": 58})
            
            if 'content' in result and isinstance(result['content'], list):
                print(f"* Add工具执行成功，返回了 {len(result['content'])} 条内容")
                
                for item in result['content']:
                    if item.get('type') == 'text':
                        print(f"* Add响应: {item.get('text', '')}")
            else:
                print(f"* Add工具执行格式异常: {result}")
        except Exception as e:
            print(f"* Add工具测试失败: {str(e)}")
        
        # 5. 测试printEnv工具
        try:
            print("\n* 测试printEnv工具...")
            result = await server.execute_tool("printEnv", {})
            
            if 'content' in result and isinstance(result['content'], list):
                print(f"* PrintEnv工具执行成功，返回了 {len(result['content'])} 条内容")
                
                # 只显示部分内容以避免输出过多
                first_item = result['content'][0] if result['content'] else {}
                if first_item.get('type') == 'text':
                    text = first_item.get('text', '')
                    lines = text.split('\n')
                    line_count = min(5, len(lines))
                    print(f"* PrintEnv响应示例 (前{line_count}行):")
                    for i in range(line_count):
                        print(f"*   {lines[i]}")
            else:
                print(f"* PrintEnv工具执行格式异常: {result}")
        except Exception as e:
            print(f"* PrintEnv工具测试失败: {str(e)}")
        
        # 6. 测试适配层 - 使用echo工具
        try:
            print("\n* 通过AG2适配层测试echo工具...")
            ag2_result = await tool.execute("mcp__everything__echo", {"message": "Hello via AG2!"})
            
            if 'content' in ag2_result and isinstance(ag2_result['content'], list):
                print(f"* 适配层执行成功，返回了 {len(ag2_result['content'])} 条内容")
                
                for item in ag2_result['content']:
                    if item.get('type') == 'text':
                        print(f"* 适配层响应: {item.get('text', '')}")
            else:
                print(f"* 适配层执行格式异常: {ag2_result}")
        except Exception as e:
            print(f"* 适配层测试失败: {str(e)}")
            
        print("\n* Everything服务器测试完成")
        return True
    
    except Exception as e:
        print(f"* 服务器测试失败: {str(e)}")
        print("* 这可能是正常的，如果npx或everything服务器未安装")
        return False
    
    finally:
        # 确保断开连接
        try:
            print("\n* 断开服务器连接...")
            await client.disconnect_all()
            print("* 连接已断开")
        except Exception as e:
            print(f"* 断开连接时出错: {str(e)}")
            # 不影响测试结果




async def main():
    """主测试函数"""
    try:
        # 直接打印确保输出可见
        print("======= 开始基础测试 =======")
        logger.info("开始基础测试")
        
        config_ok = await test_config()
        result_msg = f"配置测试: {'成功' if config_ok else '失败'}"
        print(result_msg)
        logger.info(result_msg)
        
        client_ok = await test_client_creation()
        result_msg = f"客户端创建测试: {'成功' if client_ok else '失败'}"
        print(result_msg)
        logger.info(result_msg)
        
        # 客户端配置测试
        print("测试客户端配置...")
        logger.info("测试客户端配置...")
        config_test_ok = await test_client_configuration()
        result_msg = f"客户端配置测试: {'成功' if config_test_ok else '失败'}"
        print(result_msg)
        logger.info(result_msg)
        
        # 服务器连接测试（可选）
        print("\n进行服务器连接测试（可选）...")
        logger.info("进行服务器连接测试（可选）...")
        server_ok = await test_everything_server()
        result_msg = f"服务器连接测试: {'成功' if server_ok else '失败（可能是服务器未安装）'}"
        print(result_msg)
        logger.info(result_msg)
        
        
        # 总结（服务器测试不影响总体成功）
        success = config_ok and client_ok and config_test_ok
        result_msg = f"基础测试总结: {'成功' if success else '失败'}"
        print("\n==============================")
        print(result_msg)
        if server_ok:
            print("服务器连接测试也成功!")
        else:
            print("服务器连接测试失败，但不影响基础功能验证")
        print("==============================")
        logger.info(result_msg)
        
        logger.info("基础测试完成")
        
    finally:
        # 清理所有剩余资源
        print("\n清理所有资源...")
        
        # 获取所有任务
        pending = asyncio.all_tasks() - {asyncio.current_task()}
        
        # 取消所有任务
        for task in pending:
            task.cancel()
            
        # 等待任务取消完成
        if pending:
            print(f"等待 {len(pending)} 个任务取消...")
            try:
                await asyncio.gather(*pending, return_exceptions=True)
                print("所有任务已取消")
            except Exception as e:
                print(f"取消任务时出错: {str(e)}")
        
        print("测试完成，正常退出")


async def run_test():
    """简单的测试运行器，确保正确清理"""
    try:
        print("===== 开始测试 =====")
        result = await main()
        print(f"\n测试结果: {'成功' if result else '失败'}")
        return result
    except Exception as e:
        print(f"\n测试异常: {e}")
        return False

def kill_child_processes():
    """杀死当前进程的所有子进程"""
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
                    print(f"终止进程出错: {e}")
            
            gone, alive = psutil.wait_procs(children, timeout=3)
            print(f"已终止 {len(gone)} 个进程, 还有 {len(alive)} 个存活")
            
            if alive:
                print(f"强制终止 {len(alive)} 个未响应进程...")
                for p in alive:
                    try:
                        p.kill()
                    except:
                        pass
                
                psutil.wait_procs(alive, timeout=2)
                print("强制终止完成")
    except ImportError:
        print("psutil模块未安装，无法终止子进程")
    except Exception as e:
        print(f"终止子进程出错: {e}")

if __name__ == "__main__":
    # 使用更简单的方式运行测试
    try:
        # 不使用asyncio.wait_for，而是直接运行
        asyncio.run(run_test())
    except KeyboardInterrupt:
        print("\n测试被用户中断")
    finally:
        print("\n===== 清理资源 =====")
        kill_child_processes()
        print("\n===== 测试完全结束 =====")