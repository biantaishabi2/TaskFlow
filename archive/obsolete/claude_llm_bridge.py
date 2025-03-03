#!/usr/bin/env python3
"""
Claude命令行与大模型桥接程序 - 使用pexpect
让大模型能够控制Claude命令行工具并与之交互
"""

import pexpect
import sys
import time
import re
import os
import json
import argparse
import signal
import threading
import requests
from enum import Enum
from anthropic import Anthropic

# 配置您实际使用的大模型API
LLM_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "your_api_key_here")  # 从环境变量获取或使用默认值
LLM_API_URL = "https://api.openrouter.ai/api/v1/chat/completions"  # OpenRouter API端点

class ClaudeState(Enum):
    """Claude命令行可能的状态"""
    STARTING = 0
    READY = 1
    THINKING = 2
    AWAITING_INPUT = 3
    TOOL_USING = 4
    ERROR = 5
    EXITING = 6
    UNKNOWN = 7

class LLMBridge:
    """大模型API桥接"""
    
    def __init__(self, api_key=None, api_url=None, model="anthropic/claude-3-7-sonnet-20250201"):
        """初始化大模型桥接"""
        self.api_key = api_key or LLM_API_KEY
        self.api_url = api_url or LLM_API_URL
        self.model = model
        self.conversation_history = []
        self.client = Anthropic(api_key=self.api_key)
        
    def add_message(self, role, content):
        """添加消息到历史"""
        self.conversation_history.append({
            "role": role,
            "content": content
        })
        
    def get_decision(self, claude_output, max_tokens=100):
        """
        请求大模型做出决策
        
        参数:
            claude_output (str): Claude的输出内容
            max_tokens (int): 响应的最大令牌数
            
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
        # 添加当前Claude输出
        user_message = f"Claude输出如下，请决定如何回应:\n\n{claude_output}\n\n只返回你的决定，不要解释原因。"
        
        try:
            # 使用Anthropic Python SDK调用Claude
            response = self.client.messages.create(
                model=self.model,
                system=system_prompt,
                messages=[
                    *[{"role": m["role"], "content": m["content"]} for m in self.conversation_history[-5:]],
                    {"role": "user", "content": user_message}
                ],
                max_tokens=max_tokens
            )
            
            # 提取决策
            decision = response.content[0].text
            
            # 添加到历史
            self.add_message("user", user_message)
            self.add_message("assistant", decision)
            
            print(f"大模型决策: '{decision}'")
            return decision
            
        except Exception as e:
            print(f"大模型API调用失败: {str(e)}")
            # 失败时使用OpenRouter API作为备选
            try:
                return self._call_openrouter_api(system_prompt, user_message, max_tokens)
            except Exception as e2:
                print(f"备选API调用也失败: {str(e2)}")
                # 返回默认响应
                return "y"
    
    def _call_openrouter_api(self, system_prompt, user_message, max_tokens):
        """使用OpenRouter API作为备选"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                *[{"role": m["role"], "content": m["content"]} for m in self.conversation_history[-5:]],
                {"role": "user", "content": user_message}
            ],
            "max_tokens": max_tokens
        }
        
        response = requests.post(self.api_url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        
        decision = result["choices"][0]["message"]["content"]
        print(f"OpenRouter API决策: '{decision}'")
        return decision

class ClaudeBridge:
    """
    Claude命令行桥接器
    实现大模型控制Claude命令行工具的能力
    """
    
    def __init__(self, llm_bridge=None, debug=False):
        """初始化桥接器"""
        self.debug = debug
        self.child = None
        self.output_buffer = []
        self.state = ClaudeState.UNKNOWN
        self.llm_bridge = llm_bridge or LLMBridge()
        
    def start(self):
        """启动Claude进程"""
        print("启动Claude进程...")
        self.state = ClaudeState.STARTING
        
        # 创建pexpect子进程
        self.child = pexpect.spawn('claude', encoding='utf-8')
        
        # 设置终端大小 (行，列)
        self.child.setwinsize(40, 120)
        
        # 如果需要debug，将输出重定向到stdout
        if self.debug:
            self.child.logfile = sys.stdout
            
        # 等待Claude启动完成
        try:
            # 等待欢迎消息出现
            self.child.expect('Welcome to Claude Code', timeout=10)
            print("Claude已启动")
            self.state = ClaudeState.READY
            return True
        except Exception as e:
            print(f"启动Claude出错: {str(e)}")
            self.state = ClaudeState.ERROR
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
    
    def detect_claude_state(self):
        """
        检测Claude的当前状态
        
        返回:
            ClaudeState: 检测到的状态
        """
        if not self.child or not self.child.isalive():
            return ClaudeState.ERROR
        
        # 获取当前的输出缓冲区
        # 注意：这不会消耗输出，只是观察
        curr_buffer = self.child.before + (self.child.after or "")
        
        # 检查各种状态模式
        if re.search(r'Hustling', curr_buffer):
            return ClaudeState.THINKING
            
        if re.search(r'╭─+╮.*>.*╰─+╯', curr_buffer, re.DOTALL):
            return ClaudeState.AWAITING_INPUT
            
        if re.search(r'using tool|正在使用工具', curr_buffer, re.IGNORECASE):
            return ClaudeState.TOOL_USING
            
        if re.search(r'error|错误', curr_buffer, re.IGNORECASE):
            return ClaudeState.ERROR
            
        return ClaudeState.UNKNOWN
    
    def wait_for_input_prompt(self, timeout=60):
        """
        等待Claude输入提示出现
        
        参数:
            timeout (int): 超时时间(秒)
            
        返回:
            str: 等待期间收集的输出
        """
        try:
            # 等待输入提示符模式
            # 这是一个简化版本，可能需要更复杂的模式匹配
            input_pattern = r'╭─+╮.*>.*╰─+╯'
            self.child.expect(input_pattern, timeout=timeout, searchwindowsize=10000)
            
            # 提取缓冲区中的内容(Claude的响应)
            content = self.child.before
            
            # 清理ANSI控制字符
            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            cleaned_content = ansi_escape.sub('', content)
            
            return cleaned_content
        except pexpect.TIMEOUT:
            print("等待Claude输入提示超时")
            return None
        except Exception as e:
            print(f"等待输入提示错误: {str(e)}")
            return None
    
    def llm_controlled_session(self, initial_prompt, max_turns=10, timeout=300):
        """
        运行由大模型控制的Claude会话
        
        参数:
            initial_prompt (str): 初始提示
            max_turns (int): 最大交互轮次
            timeout (int): 总超时时间(秒)
            
        返回:
            list: 交互记录
        """
        if not self.start():
            return False
            
        # 交互记录
        interactions = []
        
        # 总计时开始
        start_time = time.time()
        
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
            
            # 主交互循环
            turn = 0
            while turn < max_turns and (time.time() - start_time) < timeout:
                # 等待Claude响应
                claude_output = self.wait_for_input_prompt(timeout=60)
                
                if not claude_output:
                    print("未收到Claude响应，结束会话")
                    break
                    
                # 记录Claude响应
                interactions.append({
                    "role": "claude",
                    "content": claude_output,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                })
                
                print("\n==== Claude响应 ====")
                print(f"{claude_output[:300]}..." if len(claude_output) > 300 else claude_output)
                print("=====================\n")
                
                # 检查是否需要大模型决策
                state = self.detect_claude_state()
                
                if state == ClaudeState.AWAITING_INPUT:
                    # 请求大模型做出决策
                    llm_decision = self.llm_bridge.get_decision(claude_output)
                    
                    # 发送决策到Claude
                    self.send_message(llm_decision)
                    
                    # 记录该交互
                    interactions.append({
                        "role": "llm",
                        "content": llm_decision,
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                    })
                    
                    # 增加交互计数
                    turn += 1
                else:
                    # 其他状态处理
                    print(f"检测到Claude状态: {state}")
                    
                    if state == ClaudeState.ERROR:
                        print("检测到错误状态，尝试恢复...")
                        # 可以发送一些恢复命令
                        self.send_message("/help")
                    
                    # 等待一下再继续
                    time.sleep(2)
                    
            # 检查是否达到最大轮次
            if turn >= max_turns:
                print(f"达到最大交互轮次 ({max_turns})")
            
            # 检查是否超时
            if (time.time() - start_time) >= timeout:
                print(f"会话总时间超过限制 ({timeout}秒)")
                
            return interactions
                
        finally:
            # 确保进程被终止
            self.close()
    
    def close(self):
        """关闭Claude进程"""
        if self.child and self.child.isalive():
            print("正在关闭Claude进程...")
            self.state = ClaudeState.EXITING
            
            try:
                # 尝试优雅退出
                self.child.sendline("/exit")
                self.child.expect(pexpect.EOF, timeout=5)
            except:
                # 如果失败，强制终止
                self.child.close(force=True)
                
            print("Claude进程已关闭")
            self.state = ClaudeState.UNKNOWN

def main():
    """主函数"""
    # 注册信号处理器
    def signal_handler(sig, frame):
        print("\n程序被用户中断，正在退出...")
        sys.exit(0)
        
    signal.signal(signal.SIGINT, signal_handler)
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="Claude命令行与大模型桥接程序")
    parser.add_argument("prompt", nargs="?", default="写一个Python函数计算斐波那契数列", help="初始提示 (可选)")
    parser.add_argument("--debug", action="store_true", help="启用调试模式")
    parser.add_argument("--turns", type=int, default=5, help="最大交互轮次")
    parser.add_argument("--timeout", type=int, default=300, help="会话超时时间(秒)")
    parser.add_argument("--output", help="保存交互记录的文件路径")
    args = parser.parse_args()
    
    # 创建大模型桥接
    llm_bridge = LLMBridge()
    
    # 创建Claude桥接
    claude_bridge = ClaudeBridge(llm_bridge=llm_bridge, debug=args.debug)
    
    # 运行大模型控制的会话
    print(f"开始大模型控制的Claude会话，初始提示: {args.prompt}")
    interactions = claude_bridge.llm_controlled_session(
        args.prompt,
        max_turns=args.turns,
        timeout=args.timeout
    )
    
    # 打印交互统计
    print("\n会话统计:")
    print(f"总交互次数: {len(interactions)}")
    
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