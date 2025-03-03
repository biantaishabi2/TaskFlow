import sys
import time
from enum import Enum
import os

# 导入claude_client中的ClaudeClient类
try:
    # 首先尝试从项目内部vendor目录导入
    from task_planner.vendor.claude_client.claude_client import ClaudeClient
except ImportError:
    # 备选：外部依赖路径
    sys.path.insert(0, '/home/wangbo/document/wangbo/claude_client')
    from claude_client import ClaudeClient

class ClaudeState(Enum):
    """Claude状态枚举"""
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"

def claude_api(prompt, verbose=False, timeout=300, use_gemini=False, conversation_history=None):
    """
    向Claude发送一个问题并获取回答。
    这是从Python代码中调用Claude命令行工具的主要函数。
    
    Args:
        prompt (str): 要发送给Claude的问题
        verbose (bool): 是否打印详细信息
        timeout (int): 命令执行超时时间(秒)
        use_gemini (bool): 是否使用Gemini来判断任务完成状态
        conversation_history (list): 对话历史，适用于继续之前的对话
        
    Returns:
        dict: 包含结果的字典，包括status、output、error_msg和task_status
    """
    if verbose:
        print(f"发送到Claude: {prompt}")
    
    try:
        if use_gemini:
            # 尝试导入所需的模块
            try:
                try:
                    # 首先尝试从项目内部vendor目录导入
                    from task_planner.vendor.claude_client.enhanced_claude_client import EnhancedClaudeClient
                    from task_planner.vendor.claude_client.agent_tools.gemini_analyzer import GeminiTaskAnalyzer
                except ImportError:
                    # 备选：外部依赖路径
                    sys.path.insert(0, '/home/wangbo/document/wangbo/claude_client')
                    from enhanced_claude_client import EnhancedClaudeClient
                    from agent_tools.gemini_analyzer import GeminiTaskAnalyzer
            except ImportError as e:
                if verbose:
                    print(f"导入增强型客户端失败: {str(e)}，将使用标准客户端")
                # 回退到标准客户端
                use_gemini = False
            
        if use_gemini:
            # 使用增强型客户端，带有Gemini分析器
            analyzer = GeminiTaskAnalyzer()  # 可以通过环境变量GEMINI_API_KEY设置API密钥
            client = EnhancedClaudeClient(analyzer=analyzer, debug=verbose, timeout=timeout)
            
            # 启动客户端
            if not client.start():
                if verbose:
                    print("启动增强型Claude客户端失败")
                return {
                    "status": "error",
                    "output": "",
                    "error_msg": "启动增强型Claude客户端失败",
                    "task_status": "ERROR"
                }
                
            # 如果提供了对话历史，恢复历史状态
            if conversation_history:
                client.conversation_history = conversation_history
                
            # 发送请求并获取响应，不自动生成后续提问
            response, history = client.send_request(prompt, auto_continue=False)
            
            # 获取任务状态
            task_status = client.analyze_completion(response)
            
            # 关闭客户端
            client.close()
            
            # 返回成功结果，包含任务状态和对话历史
            return {
                "status": "success",
                "output": response,
                "error_msg": "",
                "task_status": task_status,
                "conversation_history": history
            }
        else:
            # 使用原始客户端
            client = ClaudeClient(debug=verbose, timeout=timeout)
            
            # 启动客户端
            if not client.start():
                if verbose:
                    print("启动Claude客户端失败")
                return {
                    "status": "error",
                    "output": "",
                    "error_msg": "启动Claude客户端失败",
                    "task_status": "UNKNOWN"
                }
            
            # 发送请求并获取响应
            response = client.send_request(prompt)
            
            # 关闭客户端
            client.close()
            
            # 返回成功结果
            return {
                "status": "success",
                "output": response,
                "error_msg": "",
                "task_status": "COMPLETED"  # 默认假设完成
            }
    except TimeoutError:
        # 超时
        return {
            "status": "timeout",
            "output": "",
            "error_msg": f"等待Claude响应超时（{timeout}秒）",
            "task_status": "ERROR"
        }
    except Exception as e:
        # 其他错误
        return {
            "status": "error",
            "output": "",
            "error_msg": f"执行错误: {str(e)}",
            "task_status": "ERROR"
        }

if __name__ == "__main__":
    # 简单的命令行测试
    if len(sys.argv) > 1:
        # 如果有命令行参数，将它们作为查询发送给Claude
        prompt = " ".join(sys.argv[1:])
        response_dict = claude_api(prompt, verbose=True)
        
        # 输出状态和结果
        print(f"\n执行状态: {response_dict['status']}")
        if response_dict['error_msg']:
            print(f"错误信息: {response_dict['error_msg']}")
            
        if response_dict['output']:
            print("\n回答:")
            print(response_dict['output'])
    else:
        # 如果没有命令行参数，显示使用说明
        print("Claude命令行工具 - Python API")
        print("\n使用方法:")
        print("  1. 作为库导入: from task_planner.util.claude_cli import claude_api")
        print("  2. 在代码中调用: response = claude_api('你的问题')")
        print("  3. 直接运行: python claude_cli.py '你的问题'")
        print("\n示例:")
        print("  python claude_cli.py '什么是Python?'")
        print("  python claude_cli.py '写一个快速排序算法'")
        print("\n返回值:")
        print("  claude_api函数返回一个包含以下字段的字典:")
        print("    - status: 'success', 'error', 或 'timeout'")
        print("    - output: Claude的输出内容")
        print("    - error_msg: 如果有错误，包含错误信息")