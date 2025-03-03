#!/usr/bin/env python3
"""
Gemini 调用 Claude CLI 集成测试

这个脚本演示了使用Gemini 2.0 Flash API控制Claude CLI的完整交互过程。
Gemini模型作为决策者，解析Claude的输出并决定如何回应。
"""

import os
import sys
import time
import json
import signal
import pexpect
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.live import Live
from rich.table import Table

# 添加父目录到路径以导入必要模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from claude_llm_bridge_rich import ClaudeBridge
from tests.gemini_bridge_test import GeminiAPIBridge  # 复用已有的Gemini桥接实现

# 创建控制台
console = Console()

def signal_handler(sig, frame):
    """处理Ctrl+C信号"""
    console.print("\n[bold red]用户中断，正在优雅退出...[/]")
    # 在后续代码中检查这个标志
    signal_handler.interrupted = True
    
# 为handler添加interrupted属性
signal_handler.interrupted = False
signal.signal(signal.SIGINT, signal_handler)

def format_interaction(interaction):
    """格式化交互记录为富文本表格"""
    table = Table(title="交互记录", expand=True)
    table.add_column("时间", style="cyan", no_wrap=True)
    table.add_column("角色", style="green")
    table.add_column("内容", style="white", max_width=80)
    
    for item in interaction:
        timestamp = item.get("timestamp", "")
        
        if "event" in item:
            table.add_row(
                timestamp, 
                "事件", 
                f"[yellow]{item['event']}[/]"
            )
        else:
            role = item.get("role", "")
            content = item.get("content", "")
            output_type = item.get("output_type", "")
            
            if len(content) > 300:
                content = content[:150] + "\n...\n" + content[-150:]
                
            role_display = role.upper()
            if output_type:
                role_display += f" ({output_type})"
                
            table.add_row(timestamp, role_display, content)
    
    return table

def run_integration_test(prompt, max_interactions=30, force_attempt_completion=True):
    """
    运行完整的Gemini控制Claude的集成测试
    
    参数:
        prompt (str): 发送给Claude的初始提示
        max_interactions (int): 最大交互次数，防止无限循环
        force_attempt_completion (bool): 是否强制尝试获取Claude的完整回复
    """
    # 确保re模块已导入
    import re
    
    # 不清除环境变量，这样不会影响API密钥的获取
    # os.environ["PYTHONPATH"] = ""
    console.print(Panel(f"[bold cyan]Gemini 2.0 Flash 控制 Claude CLI 集成测试[/]", 
                        subtitle=f"初始提示: {prompt}"))
    
    # 获取环境变量中的API密钥
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        console.print("[bold red]错误: 未设置GEMINI_API_KEY环境变量[/]")
        return
        
    # 打印密钥长度，验证是否正确获取（不打印实际密钥）
    console.print(f"[dim]API密钥长度: {len(api_key)}字符[/]")
    
    # 创建Gemini API桥接
    try:
        gemini_bridge = GeminiAPIBridge(api_key=api_key)
        console.print(f"[bold green]成功初始化Gemini API (model: {gemini_bridge.model})[/]")
    except Exception as e:
        console.print(f"[bold red]初始化Gemini API失败: {str(e)}[/]")
        return
    
    # 创建Claude桥接
    try:
        # 设置debug=True显示更多日志，以便调试
        claude_bridge = ClaudeBridge(llm_bridge=gemini_bridge, debug=True)
        console.print("[bold green]成功创建Claude桥接[/]")
    except Exception as e:
        console.print(f"[bold red]创建Claude桥接失败: {str(e)}[/]")
        return
    
    # 创建实时显示区域
    live_display = None
    interactions = []
    interaction_count = 0  # 初始化交互计数
    
    # 记录会话开始
    start_time = time.time()
    interactions.append({
        "event": "session_start",
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "prompt": prompt
    })
    
    try:
        with Live(format_interaction(interactions), refresh_per_second=4) as live:
            live_display = live
            
            # 使用初始提示启动Claude进程
            initial_context = f"这次会话的任务是：{prompt}\n请专注于完成这一任务，忽略任何无关内容。"
            if not claude_bridge.start(initial_context=initial_context):
                console.print("[bold red]启动Claude进程失败[/]")
                return
            
            interactions.append({
                "event": "claude_started",
                "timestamp": datetime.now().strftime("%H:%M:%S")
            })
            live.update(format_interaction(interactions))
            
            # 不立即发送初始提示，而是在初始上下文设置后等待一段时间
            # 这样Claude有更多时间处理上下文
            time.sleep(3)  # 等待3秒
            
            interactions.append({
                "role": "user",
                "content": prompt,
                "timestamp": datetime.now().strftime("%H:%M:%S")
            })
            
            # 短暂延迟，让Claude开始处理
            time.sleep(2)
            
            # 检查是否已开始思考，如果没有则尝试多种方法激活Claude
            try:
                current_output = claude_bridge.get_current_output()
                if not re.search(r'\*\s+\(\d+s\)', current_output):
                    console.print("[bold yellow]尝试多种方法启动Claude思考...[/]")
                    
                    # 尝试方式1: 发送回车
                    console.print("[dim]尝试方式1: 发送回车[/]")
                    claude_bridge.child.sendline()
                    time.sleep(2)
                    
                    # 再次检查是否开始思考
                    current_output = claude_bridge.get_current_output()
                    if not re.search(r'\*\s+\(\d+s\)', current_output):
                        # 尝试方式2: 发送空格和退格，模拟用户活动
                        console.print("[dim]尝试方式2: 发送空格和退格[/]")
                        claude_bridge.child.send(' \b')
                        time.sleep(1)
                        
                        # 尝试方式3: 发送ESC键然后回车，清除当前行
                        console.print("[dim]尝试方式3: 发送ESC键和回车[/]")
                        claude_bridge.child.send('\x1b')  # ESC
                        time.sleep(0.5)
                        claude_bridge.child.sendline()
                        time.sleep(1)
                        
                        # 尝试方式4: 重新发送原始提示但添加问号
                        console.print("[dim]尝试方式4: 重新发送修改的提示[/]")
                        if prompt.endswith('?'):
                            claude_bridge.send_message(prompt[:-1])
                        else:
                            claude_bridge.send_message(prompt + "?")
                        time.sleep(2)
            except Exception as e:
                console.print(f"[bold yellow]启动思考检查时出错: {str(e)}[/]")
            live.update(format_interaction(interactions))
            
            # 主交互循环
            interaction_count = 0
            wait_patterns = [
                r'╭─+╮.*>.*╰─+╯',  # 输入提示框
                r'\[y/n\]',         # 确认请求
                r'Press Enter to continue',  # 按键继续
                r'请按.*继续',        # 中文按键继续
                r'请输入',           # 中文输入提示
                r'Enter.*:',        # 英文输入提示
                r'```python',       # Python代码块开始（捕获Claude的实际输出）
                r'很高兴帮助你',      # Claude回答开始
                r'下面是一个简单的Python计算器',  # 典型的回答开始
                r'我将实现一个简单的计算器',  # 另一种典型回答开始
                r'以下是一个支持加减乘除的Python计算器'  # 另一种典型回答开始
            ]
            
            while interaction_count < max_interactions and not signal_handler.interrupted:
                # 等待Claude需要输入
                try:
                    import pexpect
                    index = claude_bridge.child.expect(wait_patterns + [pexpect.EOF], timeout=30)
                    
                    if index == len(wait_patterns):  # EOF
                        console.print("[bold yellow]Claude进程结束[/]")
                        interactions.append({
                            "event": "claude_eof",
                            "timestamp": datetime.now().strftime("%H:%M:%S")
                        })
                        live.update(format_interaction(interactions))
                        break
                    
                    # 检查当前输出中是否包含思考中的标记（星型符号和计时器）
                    current_output = claude_bridge.child.before + claude_bridge.child.after
                    if re.search(r'\*\s+\(\d+s\)', current_output):
                        console.print("[bold yellow]Claude仍在思考中，等待完成...[/]")
                        
                        # 设置更长的最大等待时间（最多等待10分钟）
                        max_wait = 600  # 秒
                        start_time = time.time()
                        
                        # 每秒检查一次思考状态，直到指示器消失
                        while time.time() - start_time < max_wait:
                            # 刷新屏幕（发送空格然后退格）
                            claude_bridge.child.send(' \b')
                            time.sleep(0.1)
                            
                            # 获取最新输出
                            latest_output = claude_bridge.child.before + claude_bridge.child.after
                            
                            # 显示计时器状态
                            timer_match = re.search(r'\*\s+\((\d+)s\)', latest_output)
                            if timer_match:
                                timer_value = timer_match.group(1)
                                elapsed = time.time() - start_time
                                console.print(f"[dim]等待Claude思考: {timer_value}秒 (已等待: {elapsed:.1f}秒)[/]", end="\r")
                            
                            # 检查思考指示器是否已消失
                            if not re.search(r'\*\s+\(\d+s\)', latest_output):
                                console.print("\n[bold green]Claude思考完成，可以输入[/]")
                                break
                                
                            # 等待1秒再检查
                            time.sleep(1)
                            
                        # 如果超过最大等待时间
                        if time.time() - start_time >= max_wait:
                            console.print("\n[bold yellow]等待Claude思考超时(10分钟)，强制继续...[/]")
                    
                    # 如果匹配到Python代码块或Claude回答开始，给它额外10秒生成完整回答
                    if index in [6, 7, 8]:  # Python代码块或Claude回答开始的索引
                        console.print("[bold green]检测到Claude开始给出实际答案，等待10秒让它生成完整回复...[/]")
                        time.sleep(10)
                        
                    # 获取Claude的输出
                    raw_output = claude_bridge.child.before + claude_bridge.child.after
                    
                    # 使用rich分析输出
                    output_type, cleaned_output = claude_bridge.analyze_output(raw_output)
                    
                    # 记录Claude响应
                    interactions.append({
                        "role": "claude",
                        "content": cleaned_output,
                        "output_type": output_type.value,
                        "timestamp": datetime.now().strftime("%H:%M:%S")
                    })
                    live.update(format_interaction(interactions))
                    
                    # 检查是否仍在思考状态（有计时器），如果是则等待思考完成再调用Gemini
                    current_output = claude_bridge.child.before + claude_bridge.child.after
                    if re.search(r'\*\s+\(\d+s\)', current_output):
                        console.print("[bold yellow]Claude仍在思考中，等待完成后再决策...[/]")
                        
                        # 等待思考完成（最多10分钟）
                        max_wait = 600  # 秒
                        start_time = time.time()
                        
                        while time.time() - start_time < max_wait:
                            # 刷新屏幕
                            claude_bridge.child.send(' \b')
                            time.sleep(0.1)
                            
                            # 获取最新输出
                            current_output = claude_bridge.child.before + claude_bridge.child.after
                            
                            # 检查是否仍在思考
                            timer_match = re.search(r'\*\s+\((\d+)s\)', current_output)
                            if timer_match:
                                # 显示进度
                                timer_value = timer_match.group(1)
                                elapsed = time.time() - start_time
                                console.print(f"[dim]等待思考完成: {timer_value}秒 (已等待: {elapsed:.1f}秒)[/]", end="\r")
                            else:
                                # 思考完成
                                console.print("\n[bold green]Claude思考完成，可以决策[/]")
                                # 更新输出供决策使用
                                _, cleaned_output = claude_bridge.analyze_output(current_output)
                                output_type = ClaudeOutputType.INPUT_PROMPT  # 思考完成后通常是输入状态
                                break
                            
                            time.sleep(1)
                    
                    # 调用Gemini做出决策
                    decision_start = time.time()
                    llm_decision = gemini_bridge.get_decision(cleaned_output, output_type, prompt=prompt)
                    decision_time = time.time() - decision_start
                    
                    # 记录Gemini决策
                    interactions.append({
                        "role": "gemini",
                        "content": llm_decision,
                        "decision_time": f"{decision_time:.2f}s",
                        "timestamp": datetime.now().strftime("%H:%M:%S")
                    })
                    live.update(format_interaction(interactions))
                    
                    # 检查是否为空决策，如果为空但是第一次交互，使用原始提示
                    if not llm_decision and interaction_count == 0:
                        llm_decision = prompt
                        console.print("[bold cyan]首次交互使用原始提示[/]")
                    
                    # 简单检查是否有特殊情况
                    has_session_confirm = "Okay to use this session?" in cleaned_output or "是否使用此会话" in cleaned_output
                    
                    # 处理会话确认
                    if has_session_confirm:
                        console.print("[bold yellow]检测到会话确认请求，选择'y'选项...[/]")
                        claude_bridge.send_message("y")
                    elif output_type.value == "confirm":
                        # 对于确认请求，总是回答"y"
                        console.print("[bold yellow]检测到确认请求，回答'y'...[/]")
                        claude_bridge.send_message("y")
                    else:
                        # 其他情况正常发送决策
                        claude_bridge.send_message(llm_decision)
                    interaction_count += 1
                    
                    # 小延迟，让输出更易读
                    time.sleep(0.5)
                    
                except Exception as e:
                    console.print(f"[bold red]交互过程中出错: {str(e)}[/]")
                    interactions.append({
                        "event": "error",
                        "error": str(e),
                        "timestamp": datetime.now().strftime("%H:%M:%S")
                    })
                    live.update(format_interaction(interactions))
                    break
    finally:
        # 如果强制尝试获取Claude的完整回复
        if force_attempt_completion and interaction_count > 0:
            console.print("\n[bold yellow]尝试强制等待Claude完成回复...[/]")
            
            try:
                # 清除当前行
                claude_bridge.child.send('\x15')  # Ctrl+U
                time.sleep(0.2)
                
                # 按3次回车，尝试促使Claude完成任务
                for _ in range(3):
                    claude_bridge.child.sendline("")
                    time.sleep(1)
                
                # 等待Claude完成生成（最多10分钟）
                console.print("[bold yellow]等待Claude完成生成（最多10分钟）...[/]")
                
                # 等待直到思考指示器消失
                max_wait = 600  # 秒
                start_time = time.time()
                
                while time.time() - start_time < max_wait:
                    # 刷新屏幕
                    claude_bridge.child.send(' \b')
                    time.sleep(0.1)
                    
                    # 获取当前输出
                    current = claude_bridge.child.before + (claude_bridge.child.after or "")
                    
                    # 检查思考指示器
                    timer_match = re.search(r'\*\s+\((\d+)s\)', current)
                    if timer_match:
                        # 显示进度
                        elapsed = time.time() - start_time
                        console.print(f"[dim]等待Claude生成: {timer_match.group(1)}秒 (已等待: {elapsed:.1f}秒)[/]", end="\r")
                    else:
                        # 思考指示器消失，完成生成
                        console.print("\n[bold green]Claude已完成生成![/]")
                        break
                    
                    # 等待1秒
                    time.sleep(1)
                
                # 获取当前输出
                raw_output = claude_bridge.get_current_output()
                console.print(Panel(raw_output, title="最终Claude输出", border_style="cyan"))
                
                # 尝试查找Python代码
                import re
                code_match = re.search(r'```python(.*?)```', raw_output, re.DOTALL)
                if code_match:
                    console.print(Panel(code_match.group(1), title="提取的Python代码", border_style="green"))
                
                # 记录最终输出
                interactions.append({
                    "role": "claude_final",
                    "content": raw_output,
                    "timestamp": datetime.now().strftime("%H:%M:%S")
                })
            except Exception as e:
                console.print(f"[bold red]尝试获取最终输出时出错: {str(e)}[/]")
        
        # 关闭Claude进程
        claude_bridge.close()
        
        # 不需要恢复目录
        
        # 记录会话结束
        end_time = time.time()
        interactions.append({
            "event": "session_end",
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "duration": f"{end_time - start_time:.2f}秒",
            "interaction_count": interaction_count
        })
        
        if live_display:
            live_display.update(format_interaction(interactions))
    
    # 保存交互记录
    try:
        record_file = f"gemini_claude_interaction_{int(time.time())}.json"
        file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), record_file)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(interactions, f, ensure_ascii=False, indent=2)
            
        console.print(f"\n[bold green]交互记录已保存到: {file_path}[/]")
        
        # 显示统计信息
        console.print("\n[bold cyan]会话统计:[/]")
        console.print(f"总交互次数: [bold]{interaction_count}[/]")
        console.print(f"总耗时: [bold]{end_time - start_time:.2f}秒[/]")
        
        # 计算Gemini平均决策时间
        decision_times = []
        for item in interactions:
            if item.get("role") == "gemini" and "decision_time" in item:
                try:
                    time_value = float(item["decision_time"].replace("s", ""))
                    decision_times.append(time_value)
                except:
                    pass
                    
        if decision_times:
            avg_decision_time = sum(decision_times) / len(decision_times)
            console.print(f"Gemini平均决策时间: [bold]{avg_decision_time:.2f}秒[/]")
            
    except Exception as e:
        console.print(f"[bold red]保存交互记录失败: {str(e)}[/]")

def simple_claude_test():
    """运行简化版Claude测试，直接发送指令并等待"""
    console = Console()
    console.print("[bold yellow]运行简化版Claude测试[/]")
    
    # 启动Claude进程
    try:
        child = pexpect.spawn('claude', encoding='utf-8')
        child.setwinsize(60, 160)
        
        # 等待欢迎消息
        try:
            child.expect('Welcome to Claude Code', timeout=10)
            console.print("[bold green]Claude已启动[/]")
        except pexpect.TIMEOUT:
            # 如果超时，检查是否已经显示输入提示
            # 在TIMEOUT异常时，child.after不是字符串，所以只检查before
            if r'╭─+╮.*>.*╰─+╯' in child.before:
                console.print("[bold yellow]未找到欢迎消息，但检测到输入提示[/]")
            else:
                # 尝试使用正则表达式匹配输入框，避免使用精确匹配
                import re
                if re.search(r'╭.*╮|│.*│|╰.*╯', child.before):
                    console.print("[bold yellow]未找到欢迎消息，但检测到类似输入框的内容[/]")
                else:
                    console.print("[bold yellow]等待Claude启动超时，尝试继续...[/]")
        except Exception as e:
            console.print(f"[bold yellow]等待Claude启动时出现异常: {str(e)}，尝试继续...[/]")
        
        # 等待输入提示符
        child.expect(r'╭─+╮.*>.*╰─+╯', timeout=5)
        
        # 发送提示
        prompt = "写一个简单的Python计算器，支持加减乘除"
        child.sendline(prompt)
        console.print(f"[bold cyan]已发送提示: {prompt}[/]")
        
        # 等待Claude正在生成的提示
        try:
            # 导入正则表达式模块
            import re
            
            # 等待Claude开始生成回复
            console.print("[bold yellow]等待Claude生成回复...[/]")
            
            # 尝试检测Claude开始生成回复的特定文本
            try:
                child.expect("I'll create a simple Python calculator", timeout=10)
                console.print("[bold green]检测到Claude正在生成回复...[/]")
            except:
                console.print("[yellow]未检测到特定文本回复开始，继续等待...[/]")
            
            # 检查是否有思考指示器（星号和计时器）
            try:
                current = child.before + (child.after or "")
            except TypeError:
                # 如果child.after不是字符串，只使用before
                current = child.before
            
            if re.search(r'\*\s+\(\d+s\)', current):
                console.print("[bold yellow]检测到Claude正在思考，等待完成...[/]")
                
                # 等待思考指示器消失（最多10分钟）
                max_wait = 600  # 秒
                start_time = time.time()
                
                while time.time() - start_time < max_wait:
                    # 刷新屏幕（发送空格然后退格）
                    child.send(' \b')
                    time.sleep(0.1)
                    
                    # 获取当前输出
                    try:
                        current = child.before + (child.after or "")
                    except TypeError:
                        # 如果child.after不是字符串，只使用before
                        current = child.before
                    
                    # 检查是否仍在思考
                    timer_match = re.search(r'\*\s+\((\d+)s\)', current)
                    if timer_match:
                        # 显示进度
                        elapsed = time.time() - start_time
                        console.print(f"[dim]等待Claude思考: {timer_match.group(1)}秒 (已等待: {elapsed:.1f}秒)[/]", end="\r")
                    else:
                        # 思考完成
                        console.print("\n[bold green]Claude思考完成![/]")
                        break
                    
                    # 等待1秒再检查
                    time.sleep(1)
            else:
                # 没有检测到思考指示器，等待一个固定时间
                console.print("[yellow]未检测到思考指示器，等待30秒让Claude生成回复...[/]")
                time.sleep(30)
        except Exception as e:
            console.print(f"[bold yellow]等待Claude回复过程中出错: {str(e)}[/]")
            # 保险起见等待一个固定时间
            console.print("[yellow]等待30秒让Claude生成回复...[/]")
            time.sleep(30)
        
        # 获取输出
        try:
            output = child.before + (child.after or "")
        except TypeError:
            # 如果child.after不是字符串，只使用before
            output = child.before
        
        # 尝试查找Python代码
        import re
        code_match = re.search(r'```python(.*?)```', output, re.DOTALL)
        if code_match:
            console.print(Panel(code_match.group(1), title="提取的Python代码", border_style="green"))
        
        # 显示输出
        console.print(Panel(output, title="Claude输出", border_style="cyan"))
        
        # 关闭进程
        child.sendline("/exit")
        try:
            child.expect(pexpect.EOF, timeout=5)
        except:
            child.close(force=True)
            
        console.print("[bold green]Claude进程已关闭[/]")
        
    except Exception as e:
        import traceback
        console.print(f"[bold red]错误: {str(e)}[/]")
        console.print(f"[bold red]错误详情:\n{traceback.format_exc()}[/]")
        try:
            child.close(force=True)
        except:
            pass

def main():
    """主函数"""
    # 如果有-s参数，运行简化版测试
    if "-s" in sys.argv:
        simple_claude_test()
        return
        
    # 处理命令行参数
    prompt = "写一个简单的Python计算器，支持加减乘除"
    for arg in sys.argv[1:]:
        if not arg.startswith("-"):
            prompt = arg
            break
    
    # 设置最大交互次数
    max_interactions = 30
    
    # 在提示中添加一个明确的英文指令前缀，以帮助激活Claude的思考
    enhanced_prompt = f"Please write a simple Python calculator that supports addition, subtraction, multiplication, and division. The implementation should be straightforward to understand. Here is the specific request: {prompt}"
    
    # 运行集成测试
    run_integration_test(enhanced_prompt, max_interactions, force_attempt_completion=True)

if __name__ == "__main__":
    main()