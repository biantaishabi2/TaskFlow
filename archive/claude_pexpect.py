import pexpect
import time
import re
import sys
import os
from enum import Enum

class ClaudeInteractionState(Enum):
    INITIALIZED = 0
    WAITING_FOR_CLAUDE = 1
    NEEDS_CONFIRMATION = 2
    COMPLETED = 3
    ERROR = 4

class MockLLMApi:
    """模拟大模型API，用于测试"""
    
    def get_decision(self, context):
        """
        根据上下文返回决策
        
        参数:
            context (str): Claude输出的上下文
            
        返回:
            str: 决策，如 "y", "n", 空行等
        """
        print("\n大模型收到上下文:")
        print("-" * 40)
        print(context)
        print("-" * 40)
        
        # 简单模式匹配
        if re.search(r'\[y/n\]', context):
            decision = "y"
        elif re.search(r'press enter', context, re.IGNORECASE):
            decision = "\r"  # 回车
        elif re.search(r'provide a.*path', context, re.IGNORECASE):
            decision = "/tmp/example.txt"
        else:
            # 默认响应
            decision = "y"
            
        print(f"大模型决策: '{decision}'")
        return decision

def interact_with_claude_pexpect(initial_prompt, model_api=None, timeout=None, debug=False):
    """
    使用pexpect与Claude进行交互
    
    参数:
        initial_prompt (str): 初始提示
        model_api: 大模型API对象，用于决策
        timeout (int): 命令超时时间（秒），None表示无超时
        debug (bool): 是否启用调试模式
        
    返回:
        dict: 包含状态、输出和最终状态的字典
    """
    if model_api is None:
        model_api = MockLLMApi()
    
    # 定义可能需要交互的模式
    interaction_patterns = [
        r'Do you want to proceed\?',
        r'Shall I continue\?',
        r'\[y/n\]',
        r'Press Enter to continue',
        r'确认.*\?',
        r'您想要.*吗\?',
        r'请选择',
        r'你想.*吗\?',
        r'请输入',
        r'Enter.*:',
        r'Input.*:',
        r'>',  # 简单提示符
        r'请按.*继续',
        r'Press any key to continue'
    ]
    
    # 启动Claude进程
    print("启动Claude进程...")
    
    # 创建pexpect子进程
    child = pexpect.spawn('claude', encoding='utf-8')
    
    # 设置终端大小 (行，列)
    child.setwinsize(40, 120)
    
    # 如果需要debug，设置日志
    if debug:
        child.logfile = sys.stdout
    
    # 保存全部输出
    output_buffer = []
    
    # 向Claude发送初始提示
    print(f"发送初始提示: {initial_prompt}")
    
    # 等待Claude准备好
    try:
        # 等待Claude提示符出现
        index = child.expect([r'Claude Code$', pexpect.TIMEOUT, pexpect.EOF], timeout=10)
        if index != 0:
            print("无法连接到Claude或Claude未准备好")
            return {"status": "error", "output": "无法连接到Claude"}
    except Exception as e:
        print(f"等待Claude准备出错: {str(e)}")
        return {"status": "error", "output": f"连接错误: {str(e)}"}
    
    # 发送提示
    child.sendline(initial_prompt)
    output_buffer.append(f"User: {initial_prompt}")
    
    # 主交互循环
    interaction_count = 0
    state = ClaudeInteractionState.WAITING_FOR_CLAUDE
    
    try:
        while True:
            # 创建期望模式列表，包括所有交互模式和超时
            expect_patterns = interaction_patterns + [pexpect.TIMEOUT, pexpect.EOF]
            
            # 等待Claude响应或交互请求
            index = child.expect(expect_patterns, timeout=timeout)
            
            # 保存当前输出
            current_output = child.before + child.after
            output_buffer.append(current_output)
            
            # 检查是否超时或结束
            if index == len(expect_patterns) - 2:  # TIMEOUT
                print("Claude响应超时")
                # 这可能不是错误，Claude可能只是在思考
                # 在这种情况下，我们可以继续等待
                continue
                
            elif index == len(expect_patterns) - 1:  # EOF
                print("Claude会话结束")
                break
                
            else:  # 匹配到交互模式
                # 记录交互次数
                interaction_count += 1
                print(f"检测到需要交互 #{interaction_count}: {child.match.group(0)}")
                
                # 获取上下文供模型决策
                context = "\n".join(output_buffer[-5:])  # 最近5条记录
                
                # 调用模型获取决策
                decision = model_api.get_decision(context)
                
                # 向Claude发送决策
                print(f"向Claude发送决策: {repr(decision)}")
                
                # 对于不同类型的决策，可能需要不同的发送方式
                if decision == "\r":  # 回车
                    child.sendline("")
                else:
                    child.sendline(decision)
                
                # 记录发送的决策
                output_buffer.append(f"Decision: {decision}")
                
                # 等待一下让Claude处理
                time.sleep(0.5)
    
    except Exception as e:
        print(f"交互过程出错: {str(e)}")
        return {
            "status": "error", 
            "output": "\n".join(output_buffer),
            "error": str(e)
        }
    
    finally:
        # 尝试退出Claude
        try:
            child.sendline("/exit")
            child.expect(pexpect.EOF, timeout=5)
        except:
            # 如果正常退出失败，强制关闭
            child.close(force=True)
    
    # 返回结果
    return {
        "status": "completed",
        "output": "\n".join(output_buffer),
        "interaction_count": interaction_count
    }

if __name__ == "__main__":
    # 使用模拟的大模型API
    model_api = MockLLMApi()
    
    # 解析命令行参数
    import argparse
    parser = argparse.ArgumentParser(description="使用pexpect与Claude命令行工具交互")
    parser.add_argument("prompt", nargs="?", default="写一个Python函数计算斐波那契数列", help="发送给Claude的提示")
    parser.add_argument("--debug", action="store_true", help="启用调试模式")
    parser.add_argument("--timeout", type=int, default=None, help="设置超时时间(秒)")
    args = parser.parse_args()
    
    # 与Claude交互
    result = interact_with_claude_pexpect(
        args.prompt,
        model_api=model_api,
        timeout=args.timeout,
        debug=args.debug
    )
    
    # 打印结果
    print("\n" + "="*50)
    print("交互结果:")
    print(f"状态: {result['status']}")
    print(f"交互次数: {result.get('interaction_count', 0)}")
    
    # 如果输出太长，只显示部分
    output_lines = result['output'].split("\n")
    if len(output_lines) > 20:
        print("\n输出摘要 (前10行):")
        print("\n".join(output_lines[:10]))
        print("\n... (省略中间内容) ...\n")
        print("\n输出摘要 (后10行):")
        print("\n".join(output_lines[-10:]))
    else:
        print("\n完整输出:")
        print(result['output'])