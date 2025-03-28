#!/usr/bin/env python3
"""
使用SDK示例服务器测试SSE连接

这个测试脚本使用python-sdk中的simple-tool示例服务器来测试我们的SSE客户端实现。
simple-tool服务器提供一个fetch工具，可以获取网页内容。
"""

import asyncio
import logging
import os
import subprocess
import sys
import time
from contextlib import AsyncExitStack
from typing import Optional

# 确保使用SDK版本的客户端
os.environ["MCP_USE_SDK_CLIENT"] = "1"

# 先设置日志级别，以便看到详细日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_sdk_example")

# 导入客户端组件
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ag2_wrapper.agent_tools.MCPTool import MCPClient
from ag2_wrapper.agent_tools.MCPTool.config import add_server, remove_server

# SSE服务器配置
SSE_PORT = 8777  # 使用不常用端口避免冲突
SSE_SERVER_CONFIG = {
    "name": "sdk_example_server",
    "config": {
        "type": "sse",
        "url": f"http://localhost:{SSE_PORT}/sse",  # SSE服务器URL
        "timeout": 10.0,  # 连接超时(秒)
        "sse_read_timeout": 300.0  # SSE读取超时(秒)
    }
}

# 全局变量
client: Optional[MCPClient] = None
server_process: Optional[subprocess.Popen] = None


async def start_sdk_example_server():
    """启动SDK示例服务器进程"""
    global server_process
    
    logger.info("启动SDK示例服务器...")
    
    # 构建服务器路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    server_module_path = os.path.join(current_dir, "python-sdk", "examples", "servers", "simple-tool")
    
    # 确认路径存在
    if not os.path.exists(server_module_path):
        logger.error(f"找不到SDK示例服务器目录: {server_module_path}")
        return False
    
    # 使用Python模块导入方式运行
    mcp_simple_tool_path = os.path.join(server_module_path, "mcp_simple_tool")
    if not os.path.exists(mcp_simple_tool_path):
        logger.error(f"找不到mcp_simple_tool目录: {mcp_simple_tool_path}")
        return False
    
    # 构建命令
    cmd = [
        sys.executable,
        "-m", "mcp_simple_tool.server",
        "--transport", "sse",
        "--port", str(SSE_PORT)
    ]
    
    # 检查Python模块路径
    logger.info(f"Python模块路径: {sys.path}")
    logger.info(f"当前工作目录: {os.getcwd()}")
    logger.info(f"服务器目录: {server_module_path}")
    logger.info(f"目录内容: {os.listdir(server_module_path)}")
    mcp_dir = os.path.join(server_module_path, "mcp_simple_tool")
    if os.path.exists(mcp_dir):
        logger.info(f"mcp_simple_tool目录内容: {os.listdir(mcp_dir)}")
    
    # 启动服务器 - 改用直接运行服务器脚本
    try:
        # 打印完整命令以便调试
        cmd_str = " ".join(cmd)
        logger.info(f"执行命令: {cmd_str}")
        
        # 启动进程并捕获输出 - 使用shell=True可能解决模块导入问题
        server_process = subprocess.Popen(
            cmd,
            cwd=server_module_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=dict(os.environ, PYTHONPATH=server_module_path + os.pathsep + os.environ.get('PYTHONPATH', ''))
        )
        
        # 给服务器一些启动时间
        logger.info(f"等待SDK示例服务器启动 (PID: {server_process.pid})...")
        time.sleep(2)  # 稍微延长等待时间
        
        # 尝试从标准错误流读取一些数据看看是否有错误发生
        if server_process.stderr and server_process.stderr.fileno() > 0:
            stderr_data = server_process.stderr.readline()
            if stderr_data:
                logger.warning(f"服务器启动时的错误输出: {stderr_data}")
        
        # 检查服务器是否成功启动
        if server_process.poll() is not None:
            # 读取输出和错误
            stdout, stderr = server_process.communicate()
            logger.error(f"SDK示例服务器进程已退出，退出码: {server_process.returncode}")
            logger.error(f"标准输出: {stdout}")
            logger.error(f"错误输出: {stderr}")
            
            # 尝试直接运行脚本而不是模块
            logger.info("尝试直接运行服务器脚本...")
            server_script = os.path.join(mcp_dir, "server.py")
            if os.path.exists(server_script):
                logger.info(f"找到服务器脚本: {server_script}")
                direct_cmd = [sys.executable, server_script, "--transport", "sse", "--port", str(SSE_PORT)]
                logger.info(f"尝试直接命令: {' '.join(direct_cmd)}")
                try:
                    direct_process = subprocess.Popen(direct_cmd, cwd=server_module_path)
                    time.sleep(3)
                    if direct_process.poll() is not None:
                        direct_stdout, direct_stderr = direct_process.communicate()
                        logger.error(f"直接运行也失败，退出码: {direct_process.returncode}")
                        if direct_stdout:
                            logger.error(f"直接运行输出: {direct_stdout}")
                        if direct_stderr:
                            logger.error(f"直接运行错误: {direct_stderr}")
                    else:
                        # 如果直接运行成功，使用这个进程
                        logger.info("直接运行服务器脚本成功")
                        server_process = direct_process
                        return True
                except Exception as e:
                    logger.error(f"直接运行服务器脚本异常: {str(e)}")
            
            return False
        
        logger.info("SDK示例服务器启动成功")
        return True
    
    except Exception as e:
        logger.error(f"启动SDK示例服务器失败: {str(e)}")
        return False


def stop_server():
    """停止服务器进程"""
    global server_process
    
    if server_process:
        logger.info(f"停止服务器 (PID: {server_process.pid})...")
        
        try:
            # 尝试正常终止
            server_process.terminate()
            
            try:
                # 等待最多3秒让进程自行退出
                server_process.wait(timeout=3.0)
                logger.info("服务器已正常终止")
            except subprocess.TimeoutExpired:
                # 强制终止
                logger.warning("服务器未响应，强制终止...")
                server_process.kill()
                server_process.wait(timeout=2.0)
                logger.info("服务器已强制终止")
        
        except Exception as e:
            logger.error(f"停止服务器时出错: {str(e)}")
        
        finally:
            server_process = None


async def setup():
    """设置测试环境，启动服务器并添加配置"""
    global client
    
    logger.info("开始设置测试环境")
    
    # 启动SDK示例服务器
    if not await start_sdk_example_server():
        raise RuntimeError("无法启动SDK示例服务器，测试中止")
    
    # 清理可能存在的旧配置
    try:
        remove_server(SSE_SERVER_CONFIG["name"])
    except Exception:
        pass
    
    # 添加服务器配置
    add_server(
        SSE_SERVER_CONFIG["name"],
        SSE_SERVER_CONFIG["config"]
    )
    
    # 创建客户端
    client = MCPClient()
    
    logger.info("测试环境设置完成")


async def test_sse_connection():
    """测试SSE连接和基本操作"""
    global client
    
    logger.info("===== 开始测试SSE连接 =====")
    
    try:
        # 连接服务器
        server_name = SSE_SERVER_CONFIG["name"]
        logger.info(f"连接服务器: {server_name}")
        
        server = await client.connect_server(server_name)
        logger.info(f"服务器连接成功: {server_name}")
        
        # 获取工具列表
        logger.info("获取工具列表")
        tools = await server.list_tools()
        
        # 显示找到的工具
        logger.info(f"发现 {len(tools)} 个工具:")
        for tool in tools:
            logger.info(f"  - {tool['name']}: {tool.get('description', '无描述')}")
        
        # 尝试调用fetch工具（SDK示例服务器提供的工具）
        if tools and any(tool["name"] == "fetch" for tool in tools):
            logger.info("尝试调用fetch工具")
            
            # 调用fetch工具获取一个网页
            result = await server.execute_tool("fetch", {
                "url": "https://example.com"
            })
            
            # 验证结果
            if isinstance(result, dict) and "content" in result:
                content_text = result["content"][0]["text"] if result["content"] else ""
                logger.info(f"工具执行成功，返回内容长度: {len(content_text)} 字符")
                logger.info(f"内容前100个字符: {content_text[:100]}...")
                
                # 验证是否包含example.com的一些典型内容
                if "<title>Example Domain</title>" in content_text:
                    logger.info("Fetch响应验证通过!")
                else:
                    logger.warning("Fetch响应验证失败，未找到期望的内容")
            else:
                logger.info(f"工具执行结果: {result}")
        else:
            logger.warning("服务器中没有找到fetch工具，跳过工具调用测试")
        
        # 测试成功
        logger.info("SSE连接测试成功")
        return True
    
    except Exception as e:
        logger.error(f"SSE连接测试失败: {str(e)}")
        logger.exception("详细错误信息:")
        return False


async def cleanup():
    """清理测试环境"""
    global client
    
    logger.info("开始清理测试环境")
    
    if client:
        try:
            await client.disconnect_all()
            logger.info("已断开所有服务器连接")
        except Exception as e:
            logger.error(f"断开连接时出错: {str(e)}")
    
    # 清理配置
    try:
        remove_server(SSE_SERVER_CONFIG["name"])
        logger.info(f"已删除服务器配置: {SSE_SERVER_CONFIG['name']}")
    except Exception as e:
        logger.error(f"删除服务器配置时出错: {str(e)}")
    
    # 停止服务器
    stop_server()
    
    logger.info("测试环境清理完成")


async def main():
    """主测试流程"""
    # 使用AsyncExitStack确保资源清理
    async with AsyncExitStack() as stack:
        # 注册清理函数
        stack.push_async_callback(cleanup)
        
        # 设置测试环境
        try:
            await setup()
        except Exception as e:
            logger.error(f"设置测试环境失败: {str(e)}")
            return 1
        
        # 使用超时保护防止测试卡住
        try:
            result = await asyncio.wait_for(test_sse_connection(), timeout=30.0)
            
            if result:
                logger.info("===== SSE测试通过 =====")
                return 0
            else:
                logger.error("===== SSE测试失败 =====")
                return 1
            
        except asyncio.TimeoutError:
            logger.error("===== SSE测试超时 =====")
            return 1
        except Exception as e:
            logger.error(f"===== SSE测试出现异常: {str(e)} =====")
            return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("测试被用户中断")
        stop_server()  # 确保服务器进程被终止
        sys.exit(1)
    except Exception as e:
        logger.critical(f"测试过程中出现严重错误: {str(e)}")
        stop_server()  # 确保服务器进程被终止
        sys.exit(1)