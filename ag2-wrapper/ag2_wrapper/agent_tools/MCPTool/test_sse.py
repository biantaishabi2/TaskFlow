#!/usr/bin/env python3
"""
SSE连接测试

测试MCP客户端的SSE连接功能，验证SDK版本的SSE支持是否正常工作。
使用python-sdk示例中的SSE服务器进行测试。
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
logger = logging.getLogger("test_sse")

# 强制将日志直接输出到控制台
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)
logger.setLevel(logging.DEBUG)

# 设置MCP客户端日志级别
logging.getLogger("MCPClient_SDK").setLevel(logging.DEBUG)
logging.getLogger("MCPClient_SDK").addHandler(console_handler)

# 导入客户端组件
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ag2_wrapper.agent_tools.MCPTool import MCPClient
from ag2_wrapper.agent_tools.MCPTool.config import add_server, remove_server

# SSE服务器配置
SSE_PORT = 8766  # 使用新端口与echo服务器匹配
SSE_SERVER_CONFIG = {
    "name": "test_sse_server",
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


async def start_sse_server():
    """启动SSE服务器进程"""
    global server_process
    
    logger.info("启动SSE测试服务器...")
    
    # 使用本地的echo服务器
    current_dir = os.path.dirname(os.path.abspath(__file__))
    server_script = os.path.join(current_dir, "test_echo_server.py")
    
    # 检查脚本是否存在
    if not os.path.exists(server_script):
        logger.error(f"找不到echo服务器脚本: {server_script}")
        return False
    
    # 构建命令
    cmd = [
        sys.executable, server_script
    ]
    
    # 启动服务器
    try:
        # 打印完整命令以便调试
        cmd_str = " ".join(cmd)
        logger.info(f"执行命令: {cmd_str}")
        
        # 不捕获输出，让输出直接显示在控制台
        server_process = subprocess.Popen(
            cmd,
            cwd=current_dir,
            # 不捕获输出，让它直接显示在控制台
            # stderr=subprocess.PIPE,
            # stdout=subprocess.PIPE,
            text=True
        )
        
        # 给服务器一些启动时间
        logger.info(f"等待SSE服务器启动 (PID: {server_process.pid})...")
        time.sleep(3)  # 稍微延长等待时间
        
        # 检查服务器是否成功启动
        if server_process.poll() is not None:
            logger.error(f"SSE服务器进程已退出，退出码: {server_process.returncode}")
            raise RuntimeError(f"SSE服务器启动失败，退出码: {server_process.returncode}")
        
        logger.info("SSE服务器启动成功")
        return True
    
    except Exception as e:
        logger.error(f"启动SSE服务器失败: {str(e)}")
        return False


def stop_sse_server():
    """停止SSE服务器进程"""
    global server_process
    
    if server_process:
        logger.info(f"停止SSE服务器 (PID: {server_process.pid})...")
        
        try:
            # 尝试正常终止
            server_process.terminate()
            
            try:
                # 等待最多3秒让进程自行退出
                server_process.wait(timeout=3.0)
                logger.info("SSE服务器已正常终止")
            except subprocess.TimeoutExpired:
                # 强制终止
                logger.warning("SSE服务器未响应，强制终止...")
                server_process.kill()
                server_process.wait(timeout=2.0)
                logger.info("SSE服务器已强制终止")
        
        except Exception as e:
            logger.error(f"停止SSE服务器时出错: {str(e)}")
        
        finally:
            server_process = None


async def setup():
    """设置测试环境，添加配置（不启动服务器）"""
    global client
    
    logger.info("开始设置测试环境")
    
    # 不再尝试启动服务器，假设服务器已经在运行
    logger.info("连接到已运行的SSE服务器...")
    
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
    logger.info(f"SSE服务器配置: {SSE_SERVER_CONFIG}")
    
    try:
        # 连接服务器
        server_name = SSE_SERVER_CONFIG["name"]
        logger.info(f"连接服务器: {server_name}")
        
        # 添加详细调试
        logger.debug("获取服务器配置...")
        from ag2_wrapper.agent_tools.MCPTool.config import get_server
        server_config = get_server(server_name)
        logger.debug(f"配置详情: {server_config}")
        
        logger.debug("调用client.connect_server...")
        server = await client.connect_server(server_name)
        logger.info(f"服务器连接成功: {server_name}")
        
        # 获取工具列表
        logger.info("获取工具列表")
        try:
            logger.debug("调用server.list_tools...")
            tools = await server.list_tools()
            logger.debug(f"工具列表原始结果: {tools}")
            
            # 显示找到的工具
            logger.info(f"发现 {len(tools)} 个工具:")
            for tool in tools:
                logger.info(f"  - {tool['name']}: {tool.get('description', '无描述')}")
                logger.debug(f"    参数: {tool.get('parameters', {})}")
            
            # 尝试调用echo工具
            if tools and any(tool["name"] == "echo" for tool in tools):
                logger.info("尝试调用echo工具")
                
                # 调用echo工具发送测试消息
                test_message = "Hello from SSE client test!"
                logger.debug(f"调用server.execute_tool, 工具='echo', 参数={{'message': '{test_message}'}}")
                result = await server.execute_tool("echo", {
                    "message": test_message
                })
                
                # 验证结果
                logger.debug(f"工具执行原始结果: {result}")
                if isinstance(result, dict) and "content" in result:
                    content_text = result["content"][0]["text"] if result["content"] else ""
                    logger.info(f"工具执行结果: {content_text}")
                    
                    # 验证响应是否包含我们的测试消息
                    if test_message in content_text:
                        logger.info("Echo响应验证通过!")
                    else:
                        logger.warning(f"Echo响应验证失败，期望包含: {test_message}")
                else:
                    logger.info(f"工具执行结果: {result}")
            else:
                logger.warning("服务器中没有找到echo工具，跳过工具调用测试")
        except Exception as sub_e:
            logger.error(f"执行工具操作时出错: {str(sub_e)}")
            logger.exception("详细错误信息:")
            raise
            
        # 测试成功
        logger.info("SSE连接测试成功")
        return True
    
    except Exception as e:
        logger.error(f"SSE连接测试失败: {str(e)}")
        logger.exception("详细错误信息:")
        return False


async def cleanup():
    """清理测试环境（不停止服务器）"""
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
    
    # 不再停止服务器，因为它是单独启动的
    
    logger.info("测试环境清理完成")


async def main():
    """主测试流程"""
    # 使用AsyncExitStack确保资源清理
    async with AsyncExitStack() as stack:
        # 注册清理函数
        stack.push_async_callback(cleanup)
        
        # 设置测试环境
        await setup()
        
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
        stop_sse_server()  # 确保服务器进程被终止
        sys.exit(1)
    except Exception as e:
        logger.critical(f"测试过程中出现严重错误: {str(e)}")
        stop_sse_server()  # 确保服务器进程被终止
        sys.exit(1)