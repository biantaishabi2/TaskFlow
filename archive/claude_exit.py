#!/usr/bin/env python3
"""
用于直接关闭Claude会话的简单脚本
当交互失控或无法正常退出时使用
"""

import pexpect
import time
import sys

def exit_claude():
    """启动Claude并立即发送退出命令"""
    try:
        # 启动Claude进程
        child = pexpect.spawn('claude', encoding='utf-8')
        print("正在尝试退出Claude进程...")
        
        # 尝试多种退出方式
        for exit_cmd in ['/exit', '/quit', 'exit', 'quit', '\x03']:
            try:
                # 等待提示出现
                child.expect(['Welcome to Claude Code', r'╭─+╮.*>.*╰─+╯'], timeout=5)
                print(f"发送退出命令: {exit_cmd}")
                child.sendline(exit_cmd)
                time.sleep(1)
                
                # 检查是否还在运行
                if not child.isalive():
                    print("Claude进程已成功退出")
                    return True
            except Exception as e:
                print(f"尝试退出时出错: {e}")
                
        # 如果正常退出失败，强制终止
        if child.isalive():
            print("正常退出失败，强制终止进程")
            child.close(force=True)
            return True
            
    except Exception as e:
        print(f"启动或退出Claude时出错: {e}")
        return False

def kill_all_claude():
    """杀死所有Claude进程"""
    try:
        import subprocess
        print("尝试强制终止所有Claude进程...")
        subprocess.run(['pkill', '-f', 'claude'], check=False)
        print("已发送终止信号")
        return True
    except Exception as e:
        print(f"终止进程出错: {e}")
        return False

if __name__ == "__main__":
    success = exit_claude()
    if not success:
        print("尝试杀死所有Claude进程...")
        kill_all_claude()
    print("完成")