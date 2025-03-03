#!/usr/bin/env python3
"""
简化版Claude命令行交互程序 - 使用pexpect
主要用于演示和测试基本交互机制
"""

import pexpect
import sys
import time
import re
import os
import threading
import argparse
import signal

def signal_handler(sig, frame):
    print("\n程序被用户中断，正在退出...")
    sys.exit(0)

# 注册信号处理器
signal.signal(signal.SIGINT, signal_handler)

class ClaudeInteractor:
    """与Claude命令行工具交互的简化类"""
    
    def __init__(self, debug=False):
        """初始化交互器"""
        self.debug = debug
        self.child = None
        self.output_buffer = []
        
    def start(self):
        """启动Claude进程"""
        print("启动Claude进程...")
        
        # 创建pexpect子进程
        self.child = pexpect.spawn('claude', encoding='utf-8')
        
        # 设置终端大小 (行，列)
        self.child.setwinsize(40, 120)
        
        # 如果需要debug，将输出重定向到stdout
        if self.debug:
            self.child.logfile = sys.stdout
            
        # 等待Claude启动完成
        try:
            # 等待欢迎消息或输入提示符出现
            index = self.child.expect(['Welcome to Claude Code', r'╭─+╮.*>.*╰─+╯'], timeout=15)
            print("Claude已启动")
            return True
        except Exception as e:
            print(f"启动Claude出错: {str(e)}")
            return False
    
    def send_message(self, message):
        """发送消息到Claude"""
        if not self.child or not self.child.isalive():
            print("错误: Claude进程未运行")
            return False
            
        print(f"发送: {message}")
        
        # 发送消息
        self.child.sendline(message)
        return True
    
    def wait_for_response(self, timeout=30):
        """等待Claude的响应"""
        if not self.child or not self.child.isalive():
            print("错误: Claude进程未运行")
            return None
            
        print("等待Claude响应...")
        
        # 收集输出
        output = []
        
        # 尝试等待输入提示符重新出现
        try:
            # 设置多种可能的状态模式
            patterns = [
                'Hustling',                   # 思考中
                r'╭─+╮.*>.*╰─+╯',            # 输入提示
                r'\[y/n\]',                   # 确认请求
                r'Press Enter to continue',   # 按键继续
                pexpect.TIMEOUT,              # 超时
                pexpect.EOF                   # 进程结束
            ]
            
            # 首先等待任何状态变化
            index = self.child.expect(patterns, timeout=timeout/2)
            
            if index == 0:
                # 检测到"思考中"状态
                print("Claude正在思考...")
                # 继续等待输入提示出现
                self.child.expect(r'╭─+╮.*>.*╰─+╯', timeout=timeout/2)
                print("Claude已经回应")
            elif index == 1:
                # 已经是输入提示状态
                print("Claude等待输入")
            elif index == 2:
                # 需要确认 [y/n]
                print("Claude需要确认 [y/n]")
            elif index == 3:
                # 需要按回车继续
                print("Claude需要按Enter继续")
            elif index == 4:
                # 超时 - 可能Claude还在思考或生成长响应
                print("等待Claude响应超时 - 状态未知")
                return None
            elif index == 5:
                # 进程结束
                print("Claude进程已结束")
                return None
                
            # 获取所有输出 (包括ANSI控制字符)
            response = self.child.before
            
            # 尝试清理ANSI控制字符
            # 这是一个简单的清理方法，可能需要更复杂的处理
            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            cleaned_response = ansi_escape.sub('', response)
            
            # 尝试提取有意义的内容 (去除控制字符后可能还有垃圾内容)
            # 这是一个简单的方法，可能需要更复杂的处理
            lines = [line for line in cleaned_response.split('\n') if line.strip()]
            meaningful_content = '\n'.join(lines)
            
            return meaningful_content
            
        except pexpect.TIMEOUT:
            print("等待Claude响应超时")
            return None
        except pexpect.EOF:
            print("Claude进程已结束")
            return None
        except Exception as e:
            print(f"等待响应出错: {str(e)}")
            return None
    
    def interact(self):
        """进入交互模式让用户直接与Claude交互"""
        if not self.child or not self.child.isalive():
            print("错误: Claude进程未运行")
            return False
            
        print("\n进入交互模式。按Ctrl+C退出。")
        
        try:
            # 这将把控制权交给用户
            self.child.interact()
            return True
        except Exception as e:
            print(f"交互模式出错: {str(e)}")
            return False
    
    def run_session(self, initial_prompt=None):
        """运行一个简单的Claude会话"""
        if not self.start():
            return False
            
        try:
            # 如果有初始提示，发送它
            if initial_prompt:
                if self.send_message(initial_prompt):
                    response = self.wait_for_response(timeout=60)
                    if response:
                        print("\n== Claude响应 ==")
                        print(response)
                        print("== 响应结束 ==\n")
            
            # 进入交互模式
            return self.interact()
            
        finally:
            # 确保子进程被终止
            self.close()
    
    def close(self):
        """关闭Claude进程"""
        if self.child and self.child.isalive():
            print("正在关闭Claude进程...")
            
            try:
                # 尝试优雅退出
                self.child.sendline("/exit")
                self.child.expect(pexpect.EOF, timeout=5)
            except:
                # 如果失败，强制终止
                self.child.close(force=True)
                
            print("Claude进程已关闭")

def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="Claude命令行简易交互工具")
    parser.add_argument("prompt", nargs="?", help="初始提示 (可选)")
    parser.add_argument("--debug", action="store_true", help="启用调试模式")
    args = parser.parse_args()
    
    # 创建交互器
    interactor = ClaudeInteractor(debug=args.debug)
    
    # 运行会话
    try:
        interactor.run_session(initial_prompt=args.prompt)
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    finally:
        # 确保正确清理
        interactor.close()

if __name__ == "__main__":
    main()