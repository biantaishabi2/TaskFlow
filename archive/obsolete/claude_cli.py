import subprocess
import sys
import os

def claude_api(prompt, verbose=False, timeout=300):
    """
    向Claude发送一个问题并获取回答。
    这是从Python代码中调用Claude命令行工具的主要函数。
    
    Args:
        prompt (str): 要发送给Claude的问题
        verbose (bool): 是否打印详细信息
        timeout (int): 命令执行超时时间(秒)
        
    Returns:
        dict: 包含结果的字典，包括status、output和error_msg
    """
    if verbose:
        print(f"发送到Claude: {prompt}")
    
    # 创建命令 - 非交互式运行选项，并添加跳过权限检查
    cmd = ['claude', '-p', '--dangerously-skip-permissions']
        
    # 添加提示内容
    cmd.append(prompt)
    
    try:
        # 执行命令
        if verbose:
            print("正在等待Claude响应...")
            
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout  # 添加超时参数
        )
        
        # 检查是否有错误
        if result.returncode != 0:
            error_msg = f"Claude命令执行失败，返回码: {result.returncode}"
            if result.stderr:
                error_msg += f"\n错误信息: {result.stderr}"
                
            if verbose:
                print(error_msg, file=sys.stderr)
                
            return {
                "status": "error",
                "output": result.stdout,
                "error_msg": error_msg
            }
            
        # 成功执行
        return {
            "status": "success",
            "output": result.stdout,
            "error_msg": None
        }
            
    except subprocess.TimeoutExpired:
        error_msg = f"Claude命令执行超时 ({timeout}秒)"
        if verbose:
            print(error_msg, file=sys.stderr)
        return {
            "status": "timeout",
            "output": "",
            "error_msg": error_msg
        }
    except Exception as e:
        error_msg = f"执行Claude命令时出错: {e}"
        if verbose:
            print(error_msg, file=sys.stderr)
        return {
            "status": "error", 
            "output": "",
            "error_msg": error_msg
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
        print("  1. 作为库导入: from claude_cli import claude_api")
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