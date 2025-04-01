"""
MCPTool 基础测试脚本

这个脚本提供了一个简单的测试，用于验证MCPTool的基本功能。
它不依赖于外部服务器，只测试配置加载和对象创建。
"""

import asyncio
import logging
import sys
from pathlib import Path
import psutil

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

# 全局测试结果字典 (在函数外部定义)
test_results = {}

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
    
    注意：设置5秒超时保护，避免测试卡住
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
    
    # 创建客户端对象
    client = MCPClient()
    server = None
    
    try:
        # 使用超时保护整个测试流程
        async with asyncio.timeout(10.0):  # 10秒超时，避免测试卡住
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
            
    except asyncio.TimeoutError:
        print("\n* 测试超时！可能有资源清理问题")
        return False
    except Exception as e:
        print(f"* 服务器测试失败: {str(e)}")
        print("* 这可能是正常的，如果npx或everything服务器未安装")
        return False
    
    finally:
        # 确保断开连接 - 使用更简单的方式
        try:
            print("\n* 断开服务器连接...")
            # 强制终止子进程而不是依赖资源释放机制
            kill_child_processes()
            
            # 如果client已创建，尝试断开连接
            if client:
                try:
                    # 使用超时保护
                    async with asyncio.timeout(3.0):
                        await client.disconnect_all()
                except (asyncio.TimeoutError, Exception) as e:
                    print(f"* 断开连接超时或出错: {str(e)}")
                    # 不影响测试结果
            
            print("* 连接已断开")
        except Exception as e:
            print(f"* 断开连接时出错: {str(e)}")
        
        return True


async def test_time_server():
    """单独测试与 time 服务器的连接和工具调用"""
    print("\n----- 测试 time 服务器连接 ----- ('test_time_server' function)")
    
    client = MCPClient() # Create a new client instance for this test
    server = None
    test_succeeded = False
    test_attempted = False
    
    try:
        # 确保客户端初始化 (加载配置)
        await client.initialize()

        if "time" not in client.servers:
             logger.warning("'time' 服务器未在配置中找到，跳过测试。确保 MCPTool/.mcp/config.json 正确。")
             test_results["time_server_connection"] = "skipped_config_missing"
             return False # Indicate test was skipped/failed
        
        logger.info(f"* 尝试连接服务器 'time'...")
        test_attempted = True
        # 使用超时确保连接不会无限挂起
        try:
            async with asyncio.timeout(10): # 10秒连接超时
                 server = await client.connect_server("time")
            logger.info(f"* 连接服务器 'time' 成功")
        except asyncio.TimeoutError:
            logger.error("* 连接 'time' 服务器超时！(10s)")
            raise # Re-raise to be caught by the outer try block
        except Exception as conn_e:
             logger.error(f"* 连接 'time' 服务器时发生意外错误: {conn_e}", exc_info=True)
             raise # Re-raise

        logger.info(f"* 获取 'time' 工具列表...")
        try:
            async with asyncio.timeout(5): # 5秒获取列表超时
                tools = await server.list_tools()
            logger.info(f"* 获取到 {len(tools)} 个工具")
            if not tools:
                 logger.warning("警告：获取到的工具列表为空！")
            for i, tool in enumerate(tools):
                tool_name = tool.get('name', 'N/A')
                tool_desc = tool.get('description', 'N/A')
                logger.info(f"* 工具 {i+1}: {tool_name} - {tool_desc}")
        except asyncio.TimeoutError:
             logger.error("* 获取 'time' 工具列表超时！(5s)")
             raise
        except Exception as list_e:
             logger.error(f"* 获取 'time' 工具列表时发生意外错误: {list_e}", exc_info=True)
             raise

        # 尝试执行 get_current_time 工具
        if any(t.get("name") == "get_current_time" for t in tools):
            logger.info(f"* 测试 'time' 的 get_current_time 工具...")
            try:
                exec_args = {"timezone": "Asia/Tokyo"} # 使用一个具体的时区
                logger.info(f"  执行参数: {exec_args}")
                async with asyncio.timeout(10): # 10秒执行超时
                    # --- 核心调用 --- 
                    result = await server.execute_tool("get_current_time", exec_args)
                    # ----------------
                logger.info(f"* Time工具执行成功")
                content_list = result.get('content', [])
                if content_list and isinstance(content_list, list):
                     content_text = content_list[0].get('text', 'N/A') if content_list else 'N/A'
                     logger.info(f"  结果内容 (前100字符): {content_text[:100]}")
                else:
                     logger.info(f"  结果: {result}")
            except asyncio.TimeoutError:
                 logger.error("* 执行 'get_current_time' 超时！(10s)")
                 raise # Re-raise timeout error
            except Exception as exec_e:
                logger.error(f"* 执行 'get_current_time' 失败: {exec_e}", exc_info=True)
                # Don't re-raise, but mark test as failed
                test_succeeded = False 
        else:
            logger.warning(f"* 未在列表中找到 'get_current_time' 工具，跳过执行测试")
            # If listing worked but tool not found, test is still considered 'successful' in terms of connection
            test_succeeded = True 

        # 如果执行没有抛出异常（或者被跳过），标记为成功
        if test_succeeded is None: # Check if not set to False by execute failure
             test_succeeded = True

    except Exception as e:
        logger.error(f"* Time 服务器测试过程中失败: {e}", exc_info=False) # Don't log full traceback for expected errors like timeout
        test_succeeded = False
    
    finally:
        # 确保断开连接
        if server and server._connected: # Check if connection was established
            logger.info(f"* (Finally) 尝试断开 'time' 服务器连接...")
            try:
                 async with asyncio.timeout(5): # 5秒断开超时
                     await server.disconnect()
                 logger.info(f"* (Finally) 'time' 连接已断开")
            except asyncio.TimeoutError:
                 logger.error("* (Finally) 断开 'time' 连接超时 (5s)")
            except Exception as disconn_e:
                 logger.error(f"* (Finally) 断开 'time' 时出错: {disconn_e}")
        # 清理客户端资源
        await client.disconnect_all() # Ensure client resources are cleaned up
        logger.info("* (Finally) MCPClient 资源已清理")

    # 更新全局测试结果
    if test_attempted:
        test_results["time_server_connection"] = test_succeeded
        result_str = "成功" if test_succeeded else "失败"
        logger.info(f"Time 服务器连接测试: {result_str}")
    # Return status
    return test_succeeded

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
        
        # --- 调用 time 服务器测试 --- 
        logger.info("运行 Time 服务器测试...") # Add log statement
        time_ok = await test_time_server()
        # The test_results["time_server_connection"] is updated inside test_time_server now
        
        # --- 可以选择性地运行 everything 测试 --- 
        # logger.info("运行 Everything 服务器测试 (可能需要 npx 安装)...")
        
        return success
        
    finally:
        # 使用简单的清理流程，避免复杂的任务管理
        print("\n清理所有资源...")
        logger.info("基础测试清理阶段")
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
    import signal
    import atexit
    
    # 注册SIGINT处理器（Ctrl+C）提前终止进程
    def sigint_handler(sig, frame):
        print("\n强制终止测试（SIGINT）")
        kill_child_processes()
        # 使用os._exit强制退出，避免等待事件循环
        import os
        os._exit(1)
    
    # 注册15秒后的超时处理，避免无限等待
    def timeout_handler():
        print("\n测试超时 - 强制终止")
        kill_child_processes()
        # 强制退出
        import os
        os._exit(2)
    
    # 注册信号处理器和超时处理
    signal.signal(signal.SIGINT, sigint_handler)
    signal.signal(signal.SIGTERM, sigint_handler)
    
    # 注册强制退出函数
    atexit.register(kill_child_processes)
    
    # 设置主线程超时，防止卡住
    import threading
    timer = threading.Timer(15.0, timeout_handler)
    timer.daemon = True
    timer.start()
    
    # 使用更简单的方式运行测试
    try:
        asyncio.run(run_test())
        # 取消超时定时器
        timer.cancel()
    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except Exception as e:
        print(f"\n测试遇到异常: {e}")
    finally:
        # 确保清理
        kill_child_processes()
    
    print("\n===== 测试完全结束 =====")