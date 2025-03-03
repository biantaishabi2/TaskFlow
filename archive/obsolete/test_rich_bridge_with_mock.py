#!/usr/bin/env python3
"""
使用模拟环境测试claude_llm_bridge_rich.py
替换pexpect.spawn为使用我们的mock_claude_for_test.py脚本
"""

import sys
import os
import time
import json
import tempfile
import subprocess
from claude_llm_bridge_rich import LLMBridge, ClaudeOutputType, ClaudeBridge
from rich.console import Console

# 创建控制台
console = Console()

class MockClaudeBridge(ClaudeBridge):
    """使用模拟环境的Claude桥接器"""
    
    def start(self):
        """启动模拟Claude进程代替真实Claude CLI"""
        console.print("[bold yellow]启动模拟Claude环境...[/]")
        
        # 获取模拟脚本路径
        mock_script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                        "mock_claude_for_test.py")
        
        # 确保模拟脚本存在
        if not os.path.exists(mock_script_path):
            console.print(f"[bold red]错误: 模拟脚本不存在: {mock_script_path}[/]")
            return False
        
        # 创建临时文件用于记录输出
        self.temp_output = tempfile.NamedTemporaryFile(delete=False, mode='w+')
        
        try:
            # 使用subprocess启动模拟脚本
            self.process = subprocess.Popen(
                [sys.executable, mock_script_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            console.print("[bold green]模拟Claude环境已启动[/]")
            return True
            
        except Exception as e:
            console.print(f"[bold red]启动模拟脚本出错: {str(e)}[/]")
            return False
    
    def send_message(self, message):
        """发送消息到模拟Claude环境"""
        if not hasattr(self, 'process') or self.process.poll() is not None:
            console.print("[bold red]错误: 模拟Claude进程未运行[/]")
            return False
            
        console.print(f"发送到Claude: [bold cyan]{message}[/]")
        
        try:
            # 发送消息到进程stdin
            self.process.stdin.write(message + "\n")
            self.process.stdin.flush()
            return True
        except Exception as e:
            console.print(f"[bold red]发送消息错误: {str(e)}[/]")
            return False
    
    def read_output(self):
        """读取模拟Claude环境的输出"""
        if not hasattr(self, 'process') or self.process.poll() is not None:
            return None
            
        # 非阻塞读取输出
        output = ""
        try:
            # 尝试读取所有可用输出
            while True:
                line = self.process.stdout.readline()
                if not line:
                    break
                output += line
                
                # 写入临时文件以便调试
                self.temp_output.write(line)
                self.temp_output.flush()
                
        except Exception as e:
            console.print(f"[bold red]读取输出错误: {str(e)}[/]")
        
        return output
        
    def run_session(self, initial_prompt):
        """
        使用模拟环境运行Claude会话
        
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
            "version": "claude_llm_bridge_rich_mock_test v1.0"
        }
        interactions.append(session_start)
        
        try:
            # 等待初始提示出现
            time.sleep(1)
            output = self.read_output()
            
            if not output:
                console.print("[bold red]错误: 无法获取初始输出[/]")
                return interactions
                
            # 解析输出
            output_type, cleaned_output = self.analyze_output(output)
            
            # 显示输出
            self.display_claude_output(cleaned_output, output_type)
            
            # 记录Claude初始输出
            interactions.append({
                "role": "claude",
                "content": cleaned_output,
                "output_type": output_type.value,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            })
            
            # 发送初始提示
            if not self.send_message(initial_prompt):
                return interactions
                
            # 记录用户输入
            interactions.append({
                "role": "user",
                "content": initial_prompt,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            })
            
            # 主交互循环 - 最多进行3轮交互
            for _ in range(3):
                # 等待输出
                time.sleep(2)
                output = self.read_output()
                
                if not output:
                    break
                    
                # 解析输出
                output_type, cleaned_output = self.analyze_output(output)
                
                # 显示输出
                self.display_claude_output(cleaned_output, output_type)
                
                # 记录Claude响应
                interactions.append({
                    "role": "claude",
                    "content": cleaned_output,
                    "output_type": output_type.value,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                })
                
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
            
            # 记录会话结束
            interactions.append({
                "event": "session_end",
                "reason": "completed",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            })
            
            return interactions
            
        finally:
            # 确保进程被终止
            self.close()
            
            # 关闭并删除临时文件
            if hasattr(self, 'temp_output'):
                self.temp_output.close()
                try:
                    os.unlink(self.temp_output.name)
                except:
                    pass
    
    def close(self):
        """关闭模拟Claude进程"""
        if hasattr(self, 'process') and self.process.poll() is None:
            console.print("[bold yellow]正在关闭模拟Claude进程...[/]")
            
            try:
                # 发送Ctrl+C信号
                self.process.terminate()
                self.process.wait(timeout=5)
            except:
                # 如果失败，强制终止
                try:
                    self.process.kill()
                except:
                    pass
                
            console.print("[bold green]模拟Claude进程已关闭[/]")

def main():
    """主函数"""
    console.print("[bold cyan]测试Claude LLM桥接增强版 (使用模拟环境)[/]")
    
    # 创建大模型桥接
    llm_bridge = LLMBridge()
    
    # 创建使用模拟环境的Claude桥接
    claude_bridge = MockClaudeBridge(llm_bridge=llm_bridge, debug=True)
    
    # 运行大模型控制的会话
    initial_prompt = "请介绍一下斐波那契数列及其Python实现"
    console.print(f"初始提示: [bold]{initial_prompt}[/]")
    
    start_time = time.time()
    interactions = claude_bridge.run_session(initial_prompt)
    end_time = time.time()
    
    # 打印交互统计
    console.print("\n[bold cyan]会话统计:[/]")
    console.print(f"总交互次数: [bold]{len(interactions)}[/]")
    console.print(f"总耗时: [bold]{end_time - start_time:.2f}秒[/]")
    
    # 保存交互记录
    try:
        with open('rich_bridge_test_interactions.json', 'w', encoding='utf-8') as f:
            json.dump(interactions, f, ensure_ascii=False, indent=2)
        console.print("[bold green]交互记录已保存到: rich_bridge_test_interactions.json[/]")
    except Exception as e:
        console.print(f"[bold red]保存交互记录失败: {str(e)}[/]")

if __name__ == "__main__":
    main()