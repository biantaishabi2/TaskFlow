#!/usr/bin/env python3
"""
使用真实的Gemini API测试claude_llm_bridge_rich.py
替换模拟LLM API调用为真实的Gemini API调用
"""

import os
import sys
import time
import json
import requests
from rich.console import Console
from rich.panel import Panel

# 添加父目录到路径以导入必要模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from claude_llm_bridge_rich import ClaudeOutputType, ClaudeBridge

# 创建控制台
console = Console()

class GeminiAPIBridge:
    """使用Gemini API的大模型桥接"""
    
    def __init__(self, api_key=None, model="gemini-2.0-flash"):
        """初始化Gemini API桥接"""
        self.model = model
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("Gemini API密钥未设置，请设置GEMINI_API_KEY环境变量")
            
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        self.conversation_history = []
        self.console = Console(highlight=False)
        
    def add_message(self, role, content):
        """添加消息到历史"""
        self.conversation_history.append({
            "role": role,
            "content": content
        })
        
    def get_decision(self, claude_output, output_type=ClaudeOutputType.UNKNOWN, prompt=""):
        """
        请求Gemini做出决策
        
        参数:
            claude_output (str): Claude的输出内容
            output_type (ClaudeOutputType): 检测到的输出类型
            prompt (str): 当前执行的任务提示
            
        返回:
            str: Gemini的决策
        """
        # 构建提示
        system_prompt = """
你是Claude命令行工具的简单控制助手。你的任务是根据当前Claude界面的状态给出最佳操作。

当Claude等待用户输入时，请遵循这些简单规则:

1. 对于确认提示(如[y/n])，回答"y"
2. 对于"按Enter继续"的提示，返回空字符串""
3. 对于空白输入框:
   - 如果这是第一次交互，输入原始问题: "{prompt}"
   - 如果不是第一次交互，返回空字符串""
4. 如果Claude正在思考(显示 "*   (数字s)" 格式的计时器)，返回空字符串""

你的回答应该只包含指令本身，没有任何解释。
例如:
- "y"
- ""
- "{prompt}"

不要提供代码或任务解决方案，只负责界面控制。
""".format(prompt=prompt)
        # 准备消息
        messages = [
            {"role": "user", "parts": [{"text": system_prompt}]}
        ]
        
        # 添加历史消息（只保留最近的几条）
        for msg in self.conversation_history[-5:]:
            role = "model" if msg["role"] == "assistant" else "user"
            if msg["content"]:  # 确保消息内容不为空
                messages.append({"role": role, "parts": [{"text": msg["content"]}]})
        
        # 添加当前Claude输出
        user_message = f"Claude输出如下，检测到的输出类型: {output_type.value}\n\n{claude_output}\n\n只返回你的决定，不要解释原因。"
        messages.append({"role": "user", "parts": [{"text": user_message}]})
        
        try:
            # 调用Gemini API
            self.console.print(Panel("[bold cyan]调用Gemini API[/]", expand=False))
            self.console.print(f"输出类型: [bold]{output_type.value}[/]")
            
            # 准备API请求
            headers = {
                "Content-Type": "application/json",
            }
            
            params = {
                "key": self.api_key
            }
            
            data = {
                "contents": messages,
                "generationConfig": {
                    "temperature": 0.2,
                    "topP": 0.8,
                    "topK": 40,
                    "maxOutputTokens": 150,
                }
            }
            
            # 发送请求
            response = requests.post(
                self.api_url, 
                headers=headers, 
                params=params,
                json=data
            )
            
            if response.status_code != 200:
                self.console.print(f"[bold red]API调用失败: {response.status_code} - {response.text}[/]")
                raise Exception(f"API调用失败: {response.status_code}")
                
            response_data = response.json()
            
            # 提取生成的文本
            try:
                result = response_data["candidates"][0]["content"]["parts"][0]["text"].strip()
                
                # 添加到历史
                self.add_message("user", user_message)
                self.add_message("assistant", result)
                
                self.console.print(f"Gemini决策: [bold green]'{result}'[/]")
                return result
                
            except (KeyError, IndexError) as e:
                self.console.print(f"[bold red]解析API响应失败: {str(e)}[/]")
                self.console.print(f"原始响应: {json.dumps(response_data, indent=2)}")
                raise
            
        except Exception as e:
            self.console.print(f"[bold red]Gemini API调用失败: {str(e)}[/]")
            # 根据输出类型返回默认响应
            if output_type == ClaudeOutputType.CONFIRMATION:
                return "y"
            elif output_type == ClaudeOutputType.CONTINUE:
                return ""
            else:
                return "y"

def main():
    """主函数"""
    console.print("[bold cyan]测试Claude LLM桥接增强版 (使用Gemini API)[/]")
    
    # 创建Gemini API桥接
    try:
        gemini_bridge = GeminiAPIBridge()
        console.print(f"[bold green]成功初始化Gemini API (model: {gemini_bridge.model})[/]")
    except ValueError as e:
        console.print(f"[bold red]错误: {str(e)}[/]")
        return
    
    # 测试基本功能
    test_cases = [
        ("是否继续? [y/n]", ClaudeOutputType.CONFIRMATION),
        ("按Enter继续", ClaudeOutputType.CONTINUE),
        ("出现错误，是否重试?", ClaudeOutputType.ERROR),
        ("请提供文件路径", ClaudeOutputType.INPUT_PROMPT),
        ("请输入您想要了解的Python主题", ClaudeOutputType.INPUT_PROMPT)
    ]
    
    console.print("\n[bold cyan]Gemini API决策测试:[/]")
    results = []
    
    for text, output_type in test_cases:
        console.print(f"\n测试用例: [bold yellow]{text}[/] (类型: {output_type.value})")
        
        start_time = time.time()
        decision = gemini_bridge.get_decision(text, output_type)
        end_time = time.time()
        
        console.print(f"耗时: [bold]{(end_time - start_time):.2f}秒[/]")
        
        results.append({
            "input": text,
            "output_type": output_type.value,
            "decision": decision,
            "time": round(end_time - start_time, 2)
        })
    
    # 保存测试结果
    result_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gemini_test_results.json")
    try:
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "model": gemini_bridge.model,
                "test_cases": results
            }, f, ensure_ascii=False, indent=2)
        console.print(f"[bold green]测试结果已保存到: {result_file}[/]")
    except Exception as e:
        console.print(f"[bold red]保存测试结果失败: {str(e)}[/]")
    
    # 创建Claude桥接
    console.print("\n[bold cyan]创建使用Gemini API的Claude桥接[/]")
    claude_bridge = ClaudeBridge(llm_bridge=gemini_bridge, debug=True)
    console.print("[bold green]Claude桥接创建成功，可以通过以下方式使用:[/]")
    console.print("""
```python
# 使用示例
from claude_llm_bridge_rich import ClaudeBridge
from gemini_bridge_test import GeminiAPIBridge

# 创建Gemini API桥接
gemini_bridge = GeminiAPIBridge()

# 创建Claude桥接
claude_bridge = ClaudeBridge(llm_bridge=gemini_bridge)

# 运行会话
interactions = claude_bridge.run_session("写一个Python函数计算斐波那契数列")
```
""")

if __name__ == "__main__":
    main()