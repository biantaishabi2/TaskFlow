import subprocess
import threading
import time
import sys
import re
import os

def read_output(process, stop_event):
    """读取Claude命令行进程的输出"""
    buffer = ""
    confirmation_patterns = [
        r'Do you want to proceed\?',
        r'Shall I continue\?',
        r'\[y/n\]',
        r'Press Enter to continue'
    ]
    
    while not stop_event.is_set():
        # 如果有可用输出
        output = process.stdout.readline()
        if output:
            buffer += output
            print(f"Claude: {output.strip()}")
            
            # 检查是否需要确认
            for pattern in confirmation_patterns:
                if re.search(pattern, output):
                    # 需要用户确认，这里可以调用大模型
                    print("\n需要确认! 调用大模型决策...")
                    # 这里模拟调用大模型，实际应该调用API
                    decision = "y"  # 简化的模拟响应
                    print(f"大模型决定: {decision}")
                    process.stdin.write(f"{decision}\n")
                    process.stdin.flush()
                    break
        
        time.sleep(0.1)  # 防止CPU占用过高

def test_claude_interactive():
    """测试Claude交互模式"""
    # 启动Claude进程 - 不使用-p选项
    process = subprocess.Popen(
        ['claude'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1  # 行缓冲
    )
    
    # 创建一个事件标志用于停止线程
    stop_event = threading.Event()
    
    # 创建并启动读取输出的线程
    output_thread = threading.Thread(target=read_output, args=(process, stop_event))
    output_thread.daemon = True
    output_thread.start()
    
    try:
        # 发送初始提示
        initial_prompt = "写一个Python递归函数计算斐波那契数列"
        print(f"\n发送初始提示: {initial_prompt}")
        process.stdin.write(f"{initial_prompt}\n")
        process.stdin.flush()
        
        # 等待一段时间让Claude处理并输出
        time.sleep(10)
        
        # 发送另一个提示演示持续对话
        second_prompt = "现在优化这个函数，使用记忆化技术"
        print(f"\n发送后续提示: {second_prompt}")
        process.stdin.write(f"{second_prompt}\n")
        process.stdin.flush()
        
        # 再等待一段时间
        time.sleep(15)
        
    except KeyboardInterrupt:
        print("\n用户中断，正在退出...")
    finally:
        # 通知线程停止
        stop_event.set()
        # 发送/exit命令退出Claude
        try:
            process.stdin.write("/exit\n")
            process.stdin.flush()
        except:
            pass
        # 等待线程结束
        output_thread.join(timeout=2)
        # 终止进程
        process.terminate()
        print("测试结束")

if __name__ == "__main__":
    test_claude_interactive()