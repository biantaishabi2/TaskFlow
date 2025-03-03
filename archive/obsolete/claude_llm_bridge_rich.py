#!/usr/bin/env python3
"""
Claude命令行与大模型桥接程序 - 增强版
使用rich库处理ANSI控制序列，提高交互识别准确性
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
from rich.console import Console
from rich.text import Text
from rich.markdown import Markdown
from rich.panel import Panel
from rich import print as rprint

class ClaudeOutputType(Enum):
    """Claude输出类型"""
    THINKING = "thinking"       # 思考中
    INPUT_PROMPT = "prompt"     # 输入提示
    CONFIRMATION = "confirm"    # 确认请求
    CONTINUE = "continue"       # 按键继续
    ERROR = "error"             # 错误信息
    TOOL_USAGE = "tool"         # 工具使用
    COMPLETE = "complete"       # 完成
    UNKNOWN = "unknown"         # 未知

class LLMBridge:
    """大模型API桥接"""
    
    def __init__(self, model="gpt-4"):
        """初始化大模型桥接"""
        self.model = model
        self.conversation_history = []
        self.console = Console(highlight=False)
        
    def add_message(self, role, content):
        """添加消息到历史"""
        self.conversation_history.append({
            "role": role,
            "content": content
        })
        
    def get_decision(self, claude_output, output_type=ClaudeOutputType.UNKNOWN):
        """
        请求大模型做出决策
        
        参数:
            claude_output (str): Claude的输出内容
            output_type (ClaudeOutputType): 检测到的输出类型
            
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
        user_message = f"Claude输出如下，检测到的输出类型: {output_type.value}\n\n{claude_output}\n\n只返回你的决定，不要解释原因。"
        messages.append({"role": "user", "content": user_message})
        
        try:
            # 这里使用模拟函数，实际使用时替换为真实API调用
            response = self._mock_call_api(messages, output_type)
            
            # 添加到历史
            self.add_message("user", user_message)
            self.add_message("assistant", response)
            
            return response
        except Exception as e:
            self.console.print(f"[bold red]大模型API调用失败: {str(e)}[/]")
            # 根据输出类型返回默认响应
            if output_type == ClaudeOutputType.CONFIRMATION:
                return "y"
            elif output_type == ClaudeOutputType.CONTINUE:
                return ""
            else:
                return "y"
            
    def _mock_call_api(self, messages, output_type):
        """模拟调用API的函数，用于测试"""
        self.console.print(Panel("[bold cyan]大模型API调用[/]", expand=False))
        self.console.print(f"输出类型: [bold]{output_type.value}[/]")
        self.console.print(f"用户消息: [dim]{messages[-1]['content'][:150]}...[/]")
        
        # 根据输出类型做出更智能的决策
        last_message = messages[-1]['content']
        
        if output_type == ClaudeOutputType.CONFIRMATION:
            decision = "y"
        elif output_type == ClaudeOutputType.CONTINUE:
            decision = ""
        elif output_type == ClaudeOutputType.ERROR:
            # 对于错误，可能需要取消或重试
            if re.search(r'retry|重试|再试一次', last_message, re.IGNORECASE):
                decision = "retry"
            else:
                decision = "n" 
        elif output_type == ClaudeOutputType.INPUT_PROMPT:
            # 尝试从上下文中提取需要输入的内容类型
            if re.search(r'file path|文件路径', last_message, re.IGNORECASE):
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
                decision = "继续"
        else:
            # 默认响应
            decision = "y"
            
        self.console.print(f"大模型决策: [bold green]'{decision}'[/]")
        
        # 模拟延迟
        time.sleep(0.5)
        
        return decision

class ClaudeBridge:
    """Claude命令行桥接器 - 使用rich库增强ANSI处理"""
    
    def __init__(self, llm_bridge=None, debug=False):
        """初始化桥接器"""
        self.debug = debug
        self.child = None
        self.output_buffer = []
        self.llm_bridge = llm_bridge or LLMBridge()
        self.console = Console(highlight=False)
        
    def start(self, initial_context=None):
        """
        启动Claude进程
        
        参数:
            initial_context (str): 可选的初始化上下文
        """
        self.console.print("[bold yellow]启动Claude进程...[/]")
        
        # 创建pexpect子进程
        self.child = pexpect.spawn('claude', encoding='utf-8')
        self.initial_context = initial_context  # 保存初始上下文，稍后在启动后发送
        
        # 设置终端大小 (行，列) - 使用更大的窗口以便捕获更多输出内容
        self.child.setwinsize(60, 160)
        
        # 如果需要debug，将输出重定向到stdout
        if self.debug:
            self.child.logfile = sys.stdout
            
        # 等待Claude启动完成
        try:
            # 等待欢迎消息或输入提示符出现
            index = self.child.expect(['Welcome to Claude Code', r'╭─+╮.*>.*╰─+╯'], timeout=15)
            self.console.print("[bold green]Claude已启动[/]")
            
            # 如果有初始上下文，先发送一个消息来设置任务
            if hasattr(self, 'initial_context') and self.initial_context:
                # 等待输入提示出现
                self.child.expect(r'╭─+╮.*>.*╰─+╯', timeout=5)
                # 发送初始上下文作为第一条消息
                self.child.sendline(self.initial_context)
                self.console.print("[bold green]初始上下文已发送[/]")
                
            return True
        except Exception as e:
            self.console.print(f"[bold red]启动Claude出错: {str(e)}[/]")
            return False
    
    def send_message(self, message):
        """发送消息到Claude"""
        if not self.child or not self.child.isalive():
            self.console.print("[bold red]错误: Claude进程未运行[/]")
            return False
            
        self.console.print(f"发送到Claude: [bold cyan]{message}[/]")
        
        # 使用简单直接的方式发送消息
        if not message:
            # 如果消息为空，只发送回车（适用于"按回车继续"的情况）
            self.child.sendline()
        else:
            # 否则发送消息后跟回车
            self.child.sendline(message)
            
        # 等待一小段时间确保消息被处理
        time.sleep(0.5)
        return True
    
    def analyze_output(self, ansi_output):
        """
        使用rich库分析Claude的ANSI输出
        
        参数:
            ansi_output (str): 包含ANSI转义序列的Claude输出
            
        返回:
            tuple: (ClaudeOutputType, str) - 输出类型和清理后的文本
        """
        # 使用rich解析ANSI文本
        try:
            text = Text.from_ansi(ansi_output)
            
            # 获取纯文本内容
            plain_text = text.plain
            
            # 分析格式信息查找特定模式
            # 兼容不同版本的rich库
            try:
                styled_ranges = list(text.get_style_ranges())
                # 检查是否有错误（通常是红色文本）
                has_error = any(style and getattr(style, 'color', None) == "red" 
                               for _, style, _ in styled_ranges)
            except AttributeError:
                # 如果get_style_ranges不可用，退回到基本文本分析
                styled_ranges = []
                has_error = "error" in plain_text.lower() or "错误" in plain_text
            
            # 检查Claude是否处于思考状态（有星型符号和计时器）
            # 例如 "*   (158s)"
            if re.search(r'\*\s+\(\d+s\)', plain_text):
                return ClaudeOutputType.THINKING, plain_text
                
            # 检查是否有Hustling状态
            if re.search(r'Hustling', plain_text):
                return ClaudeOutputType.THINKING, plain_text
                
            # 检查输入提示框，但要确保没有思考状态的星型符号和计时器
            if re.search(r'╭─+╮.*>.*╰─+╯', plain_text, re.DOTALL) and not re.search(r'\*\s+\(\d+s\)', plain_text):
                return ClaudeOutputType.INPUT_PROMPT, plain_text
                
            if re.search(r'\[y/n\]', plain_text) or re.search(r'Okay to use this session\?|是否使用此会话', plain_text):
                return ClaudeOutputType.CONFIRMATION, plain_text
                
            if re.search(r'Press Enter to continue|请按.*继续', plain_text, re.IGNORECASE):
                return ClaudeOutputType.CONTINUE, plain_text
                
            if has_error or re.search(r'error|错误', plain_text, re.IGNORECASE):
                return ClaudeOutputType.ERROR, plain_text
                
            if re.search(r'using tool|正在使用工具', plain_text, re.IGNORECASE):
                return ClaudeOutputType.TOOL_USAGE, plain_text
                
            if re.search(r'完成|finished|done|completed', plain_text, re.IGNORECASE):
                return ClaudeOutputType.COMPLETE, plain_text
                
            # 默认为未知类型
            return ClaudeOutputType.UNKNOWN, plain_text
            
        except Exception as e:
            self.console.print(f"[bold red]分析输出错误: {str(e)}[/]")
            return ClaudeOutputType.UNKNOWN, ansi_output
    
    def display_claude_output(self, output, output_type):
        """美化显示Claude输出"""
        if not output:
            return
            
        # 根据输出类型使用不同颜色
        color_map = {
            ClaudeOutputType.THINKING: "yellow",
            ClaudeOutputType.INPUT_PROMPT: "cyan",
            ClaudeOutputType.CONFIRMATION: "magenta",
            ClaudeOutputType.CONTINUE: "blue", 
            ClaudeOutputType.ERROR: "red",
            ClaudeOutputType.TOOL_USAGE: "green",
            ClaudeOutputType.COMPLETE: "green",
            ClaudeOutputType.UNKNOWN: "white"
        }
        
        color = color_map.get(output_type, "white")
        
        # 裁剪过长输出
        display_text = output
        if len(display_text) > 500:
            display_text = display_text[:250] + "\n...\n" + display_text[-250:]
        
        # 显示输出类型和内容
        self.console.print(f"\n[bold {color}]--- Claude输出 ({output_type.value}) ---[/]")
        
        try:
            # 尝试渲染为Markdown
            if "```" in display_text:
                self.console.print(Markdown(display_text))
            else:
                self.console.print(display_text)
        except:
            # 如果渲染失败，使用普通文本
            self.console.print(display_text)
            
        self.console.print(f"[bold {color}]--- 输出结束 ---[/]")
    
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
        
        # 记录会话开始
        session_start = {
            "event": "session_start",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "version": "claude_llm_bridge_rich v1.0"
        }
        interactions.append(session_start)
        
        try:
            # 发送初始提示
            if not self.send_message(initial_prompt):
                return interactions
                
            # 记录用户输入
            interactions.append({
                "role": "user",
                "content": initial_prompt,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            })
            
            # 等待模式列表
            wait_patterns = [
                r'╭─+╮.*>.*╰─+╯',  # 输入提示框
                r'\[y/n\]',         # 确认请求
                r'Press Enter to continue',  # 按键继续
                r'请按.*继续',        # 中文按键继续
                r'请输入',           # 中文输入提示
                r'Enter.*:',        # 英文输入提示
                pexpect.EOF,        # 进程结束
                pexpect.TIMEOUT     # 超时(用于检查)
            ]
            
            # 主交互循环
            while True:
                # 等待Claude需要输入
                try:
                    index = self.child.expect(wait_patterns, timeout=None)  # 无超时，一直等待
                except pexpect.EOF:
                    self.console.print("[bold red]Claude进程已结束[/]")
                    
                    # 记录会话结束
                    interactions.append({
                        "event": "session_end",
                        "reason": "eof",
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                    })
                    break
                except Exception as e:
                    self.console.print(f"[bold red]等待Claude输入请求时出错: {str(e)}[/]")
                    
                    # 记录错误
                    interactions.append({
                        "event": "error",
                        "error": str(e),
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                    })
                    break
                
                # 检查匹配结果
                if index == len(wait_patterns) - 1:  # TIMEOUT
                    # 这通常不会触发，因为我们设置了无限超时
                    continue
                elif index == len(wait_patterns) - 2:  # EOF
                    self.console.print("[bold red]Claude进程已结束[/]")
                    break
                else:
                    # 获取Claude的输出
                    raw_output = self.child.before + self.child.after
                    
                    # 使用rich分析输出
                    output_type, cleaned_output = self.analyze_output(raw_output)
                    
                    # 显示Claude输出
                    self.display_claude_output(cleaned_output, output_type)
                    
                    # 记录Claude响应
                    interactions.append({
                        "role": "claude",
                        "content": cleaned_output,
                        "output_type": output_type.value,
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                    })
                    
                    # 检查是否仍处于思考状态（有计时器），若是则等待完成
                    if re.search(r'\*\s+\(\d+s\)', raw_output):
                        self.console.print("[yellow]Claude仍在思考中，等待完成后再继续...[/]")
                        
                        # 等待思考完成
                        max_wait = 600  # 秒
                        start_time = time.time()
                        
                        while time.time() - start_time < max_wait:
                            # 刷新屏幕（发送空格然后退格）
                            self.child.send(' \b')
                            time.sleep(0.1)
                            
                            # 获取最新输出
                            current_output = self.child.before + (self.child.after or "")
                            
                            # 检查是否仍在思考
                            timer_match = re.search(r'\*\s+\((\d+)s\)', current_output)
                            if timer_match:
                                # 显示进度
                                timer_value = timer_match.group(1)
                                elapsed = time.time() - start_time
                                self.console.print(f"[dim]等待思考完成: {timer_value}秒 (已等待: {elapsed:.1f}秒)[/]", end="\r")
                            else:
                                # 思考完成
                                self.console.print("\n[bold green]Claude思考完成，继续交互[/]")
                                # 更新输出分析结果
                                output_type, cleaned_output = self.analyze_output(current_output)
                                break
                            
                            time.sleep(1)
                    
                    # 调用大模型做出决策
                    llm_decision = self.llm_bridge.get_decision(cleaned_output, output_type)
                    
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
    
    def get_current_output(self):
        """获取当前Claude进程的完整输出"""
        if not self.child or not self.child.isalive():
            self.console.print("[bold red]错误: Claude进程未运行[/]")
            return ""
            
        try:
            # 获取当前缓冲区内容
            output = self.child.before + (self.child.after or "")
            
            # 检查是否仍在思考（有星号和计时器）
            if re.search(r'\*\s+\(\d+s\)', output):
                self.console.print("[yellow]Claude正在思考中，等待直到完成...[/]")
                
                # 设置一个非常长的最大等待时间（10分钟）
                max_wait = 600  # 秒
                start_time = time.time()
                
                # 每秒检查一次Claude的状态，直到思考指示器消失
                while time.time() - start_time < max_wait:
                    # 刷新输出（发送一个空格然后退格键，不影响输入）
                    self.child.send(' \b')
                    time.sleep(0.1)
                    
                    # 获取当前输出
                    current_output = self.child.before + (self.child.after or "")
                    
                    # 提取当前计时器值（用于日志）
                    timer_match = re.search(r'\*\s+\((\d+)s\)', current_output)
                    if timer_match:
                        timer_value = timer_match.group(1)
                        elapsed = time.time() - start_time
                        self.console.print(f"[dim]Claude思考中: {timer_value}秒 (已等待: {elapsed:.1f}秒)[/]", end="\r")
                    
                    # 检查思考指示器是否已消失
                    if not re.search(r'\*\s+\(\d+s\)', current_output):
                        self.console.print("\n[bold green]Claude思考完成![/]")
                        output = current_output
                        break
                    
                    # 等待1秒再检查
                    time.sleep(1)
                
                # 如果超过最大等待时间
                if time.time() - start_time >= max_wait:
                    self.console.print("\n[bold yellow]等待Claude思考超时(10分钟)，强制继续...[/]")
                    output = self.child.before + (self.child.after or "")
            
            return output
        except Exception as e:
            self.console.print(f"[bold red]获取当前输出时出错: {str(e)}[/]")
            return ""
    
    def close(self):
        """关闭Claude进程"""
        if self.child and self.child.isalive():
            self.console.print("[bold yellow]正在关闭Claude进程...[/]")
            
            try:
                # 尝试优雅退出
                self.child.sendline("/exit")
                self.child.expect(pexpect.EOF, timeout=5)
            except:
                # 如果失败，强制终止
                self.child.close(force=True)
                
            self.console.print("[bold green]Claude进程已关闭[/]")

def main():
    """主函数"""
    # 创建控制台
    console = Console()
    
    # 注册信号处理器
    def signal_handler(sig, frame):
        console.print("\n[bold red]程序被用户中断，正在退出...[/]")
        sys.exit(0)
        
    signal.signal(signal.SIGINT, signal_handler)
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="Claude命令行与大模型桥接程序 - 增强版")
    parser.add_argument("prompt", nargs="?", default="写一个Python函数计算斐波那契数列", help="初始提示 (可选)")
    parser.add_argument("--debug", action="store_true", help="启用调试模式")
    parser.add_argument("--output", help="保存交互记录的文件路径")
    args = parser.parse_args()
    
    # 显示欢迎信息
    console.print(Panel.fit(
        "[bold cyan]Claude 命令行与大模型桥接程序[/] - [yellow]增强版[/]",
        subtitle="使用rich库增强ANSI处理"
    ))
    
    # 创建大模型桥接
    llm_bridge = LLMBridge()
    
    # 创建Claude桥接
    claude_bridge = ClaudeBridge(llm_bridge=llm_bridge, debug=args.debug)
    
    # 运行大模型控制的会话
    with console.status("[bold yellow]启动Claude会话...[/]"):
        console.print(f"初始提示: [bold]{args.prompt}[/]")
        start_time = time.time()
        interactions = claude_bridge.run_session(args.prompt)
        end_time = time.time()
    
    # 打印交互统计
    console.print("\n[bold cyan]会话统计:[/]")
    console.print(f"总交互次数: [bold]{len(interactions)}[/]")
    console.print(f"总耗时: [bold]{end_time - start_time:.2f}秒[/]")
    
    # 计算每种输出类型的次数
    output_types = {}
    for interaction in interactions:
        if interaction.get("role") == "claude" and "output_type" in interaction:
            output_type = interaction["output_type"]
            output_types[output_type] = output_types.get(output_type, 0) + 1
            
    if output_types:
        console.print("[bold]输出类型统计:[/]")
        for output_type, count in output_types.items():
            console.print(f"  {output_type}: [bold]{count}[/]")
    
    # 保存交互记录
    if args.output:
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(interactions, f, ensure_ascii=False, indent=2)
            console.print(f"[bold green]交互记录已保存到: {args.output}[/]")
        except Exception as e:
            console.print(f"[bold red]保存交互记录失败: {str(e)}[/]")

if __name__ == "__main__":
    main()