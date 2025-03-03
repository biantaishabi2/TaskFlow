#!/usr/bin/env python3
"""
Claude命令行与大模型桥接程序 - 简化版
基于事件驱动，按需调用大模型
"""

import pexpect
import sys
import time
import re
import os
import json
import argparse
import signal
from enum import Enum

class LLMBridge:
    """大模型API桥接"""
    
    def __init__(self, model="gpt-4"):
        """初始化大模型桥接"""
        self.model = model
        self.conversation_history = []
        
    def add_message(self, role, content):
        """添加消息到历史"""
        self.conversation_history.append({
            "role": role,
            "content": content
        })
        
    def get_decision(self, claude_output):
        """
        请求大模型做出决策
        
        参数:
            claude_output (str): Claude的输出内容
            
        返回:
            str: 大模型的决策
        """
        # 构建提示
        system_prompt = """
你是Claude命令行工具的智能助手。你需要分析Claude命令行的输出并做出决策。
当Claude在等待用户输入时，你需要决定应该输入什么。

1. 如果Claude在提问或需要确认(如[y/n])，通常回答"y"确认继续
2. 如果Claude要求按回车继续，提供一个空行
3. 如果Claude请求特定信息，根据上下文提供相关信息
4. 如果Claude显示错误，分析是否需要重试或提供不同输入

只返回你决定的输入内容，不要有任何解释或额外文本。输入应该简短、明确。
"""
        # 添加系统消息
        messages = [{"role": "system", "content": system_prompt}]
        
        # 添加历史消息（只保留最近的几条）
        messages.extend(self.conversation_history[-5:])
        
        # 添加当前Claude输出
        user_message = f"Claude输出如下，请决定如何回应:\n\n{claude_output}\n\n只返回你的决定，不要解释原因。"
        messages.append({"role": "user", "content": user_message})
        
        try:
            # 这里使用模拟函数，实际使用时替换为真实API调用
            response = self._mock_call_api(messages)
            
            # 添加到历史
            self.add_message("user", user_message)
            self.add_message("assistant", response)
            
            return response
        except Exception as e:
            print(f"大模型API调用失败: {str(e)}")
            # 返回默认响应
            return "y"
            
    def _mock_call_api(self, messages):
        """模拟调用API的函数，用于测试"""
        print("\n==== 大模型API调用 ====")
        print(f"最后的用户消息: {messages[-1]['content'][:150]}...")
        
        # 简单的规则模拟大模型决策
        last_message = messages[-1]['content']
        
        if re.search(r'\[y/n\]', last_message, re.IGNORECASE):
            decision = "y"
        elif re.search(r'press enter|按回车|按enter', last_message, re.IGNORECASE):
            decision = ""
        elif re.search(r'file path|文件路径', last_message, re.IGNORECASE):
            decision = "/tmp/example.txt"
        elif re.search(r'请提供|please provide|enter the', last_message, re.IGNORECASE):
            # 尝试从消息中提取所需信息类型
            if re.search(r'name|名称|姓名', last_message, re.IGNORECASE):
                decision = "测试用户"
            elif re.search(r'email|邮箱', last_message, re.IGNORECASE):
                decision = "test@example.com"
            else:
                decision = "示例输入"
        else:
            # 默认响应
            decision = "y"
            
        print(f"大模型决策: '{decision}'")
        print("==== API调用结束 ====\n")
        
        # 模拟延迟
        time.sleep(0.5)
        
        return decision

class ClaudeBridge:
    """Claude命令行桥接器 - 简化版，事件驱动"""
    
    def __init__(self, llm_bridge=None, debug=False):
        """初始化桥接器"""
        self.debug = debug
        self.child = None
        self.output_buffer = []
        self.llm_bridge = llm_bridge or LLMBridge()
        
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
            
        print(f"发送到Claude: {message}")
        
        # 发送消息
        self.child.sendline(message)
        return True
    
    def detect_input_required(self):
        """
        检测Claude是否需要输入
        返回:
            bool: 是否需要输入
            str: 需要输入的类型 ('prompt', 'confirm', 'continue', 'none')
            str: 输出内容
        """
        if not self.child or not self.child.isalive():
            return False, 'none', "Claude进程未运行"
            
        # 定义输入模式
        patterns = [
            (r'╭─+╮.*>.*╰─+╯', 'prompt'),       # 输入提示框
            (r'\[y/n\]', 'confirm'),            # 确认请求
            (r'Press Enter to continue', 'continue'),  # 按键继续
            (r'请按.*继续', 'continue'),           # 中文按键继续
            (r'请输入', 'prompt'),                # 中文输入提示
            (r'Enter.*:', 'prompt'),            # 英文输入提示
            (r'Hustling', 'thinking'),          # 思考中
            (r'error|错误', 'error')             # 错误信息
        ]
            
        # 获取当前缓冲区
        current_buffer = self.child.before + (self.child.after or "")
        
        # 检查各种模式
        for pattern, input_type in patterns:
            if re.search(pattern, current_buffer, re.IGNORECASE | re.DOTALL):
                # 清理ANSI控制字符
                ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
                cleaned_output = ansi_escape.sub('', current_buffer)
                
                # 提取有意义的内容
                return True, input_type, cleaned_output
                
        # 没有检测到输入请求
        return False, 'none', current_buffer
    
    def run_session(self, initial_prompt):
        """
        运行Claude会话，自动处理交互
        
        参数:
            initial_prompt (str): 初始提示
            
        返回:
            list: 交互记录
        """
        if not self.start():
            return []
            
        # 交互记录
        interactions = []
        
        try:
            # 发送初始提示
            if not self.send_message(initial_prompt):
                return interactions
                
            # 记录该交互
            interactions.append({
                "role": "user",
                "content": initial_prompt,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            })
            
            # 等待模式列表 - 改进以更好地检测Claude输入提示
            wait_patterns = [
                # 识别完整的输入框（包括边框和提示符）
                r'╭─+╮.*>.*╰─+╯',        # 输入提示框
                # 识别具体的命令提示行（不需要框）
                r'! for bash mode.*for newline',  # 命令提示行
                # 其他交互模式
                r'\[y/n\]',                 # 确认请求
                r'Press Enter to continue',  # 按键继续
                r'请按.*继续',               # 中文按键继续
                r'请输入',                   # 中文输入提示
                r'Enter.*:',                # 英文输入提示
                # 特殊状态
                r'Hustling|Synthesizing',   # 思考中状态
                pexpect.EOF,                # 进程结束
                pexpect.TIMEOUT             # 超时(用于检查)
            ]
            
            # 主交互循环
            while True:
                # 等待Claude需要输入
                try:
                    index = self.child.expect(wait_patterns, timeout=None)  # 无超时，一直等待
                except pexpect.EOF:
                    print("Claude进程已结束")
                    break
                except Exception as e:
                    print(f"等待Claude输入请求时出错: {str(e)}")
                    break
                
                # 检查匹配结果
                if index == len(wait_patterns) - 1:  # TIMEOUT
                    # 检查Claude是否需要输入(这通常不会触发，因为我们设置了无限超时)
                    needs_input, input_type, output = self.detect_input_required()
                    if not needs_input:
                        continue
                elif index == len(wait_patterns) - 2:  # EOF
                    print("Claude进程已结束")
                    break
                elif index == 7:  # 思考中状态
                    print("Claude正在思考中，等待...")
                    # 继续等待输入提示出现
                    continue
                else:
                    # 获取Claude的输出
                    output = self.child.before
                    
                    # 清理ANSI控制字符
                    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
                    cleaned_output = ansi_escape.sub('', output)
                    
                    # 记录Claude响应
                    interactions.append({
                        "role": "claude",
                        "content": cleaned_output,
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                    })
                    
                    print("\n==== Claude响应 ====")
                    print(f"{cleaned_output[:300]}..." if len(cleaned_output) > 300 else cleaned_output)
                    print("=====================\n")
                    
                    # 调用大模型做出决策
                    llm_decision = self.llm_bridge.get_decision(cleaned_output)
                    
                    # 发送决策到Claude
                    self.send_message(llm_decision)
                    
                    # 记录该交互
                    interactions.append({
                        "role": "llm",
                        "content": llm_decision,
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                    })
                    
            return interactions
                
        finally:
            # 确保进程被终止
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
    # 注册信号处理器
    def signal_handler(sig, frame):
        print("\n程序被用户中断，正在退出...")
        sys.exit(0)
        
    signal.signal(signal.SIGINT, signal_handler)
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="Claude命令行与大模型桥接程序 - 简化版")
    parser.add_argument("prompt", nargs="?", default="写一个Python函数计算斐波那契数列", help="初始提示 (可选)")
    parser.add_argument("--debug", action="store_true", help="启用调试模式")
    parser.add_argument("--output", help="保存交互记录的文件路径")
    args = parser.parse_args()
    
    # 创建大模型桥接
    llm_bridge = LLMBridge()
    
    # 创建Claude桥接
    claude_bridge = ClaudeBridge(llm_bridge=llm_bridge, debug=args.debug)
    
    # 运行大模型控制的会话
    print(f"开始大模型控制的Claude会话，初始提示: {args.prompt}")
    start_time = time.time()
    interactions = claude_bridge.run_session(args.prompt)
    end_time = time.time()
    
    # 打印交互统计
    print("\n会话统计:")
    print(f"总交互次数: {len(interactions)}")
    print(f"总耗时: {end_time - start_time:.2f}秒")
    
    # 保存交互记录
    if args.output:
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(interactions, f, ensure_ascii=False, indent=2)
            print(f"交互记录已保存到: {args.output}")
        except Exception as e:
            print(f"保存交互记录失败: {str(e)}")

if __name__ == "__main__":
    main()