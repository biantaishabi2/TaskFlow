#!/usr/bin/env python3
"""
模拟Claude CLI进程用于测试claude_llm_bridge_rich.py
使用伪装的Claude CLI输出进行交互测试
"""

import sys
import time
import re
import json
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

console = Console()

def main():
    """主函数，模拟Claude CLI的行为"""
    
    # 显示欢迎信息
    console.print(Panel("[bold cyan]模拟 Claude CLI 环境[/]", subtitle="用于测试claude_llm_bridge_rich.py"))
    
    # 模拟Claude CLI的启动消息
    print("\033[1;32mWelcome to Claude Code\033[0m")
    print("This is a simulated environment.")
    time.sleep(1)
    
    # 模拟提示符
    print("\033[1;36m╭────────────────────────────────╮\n│ > █                            │\n╰────────────────────────────────╯\033[0m")
    
    # 读取用户输入
    user_input = input()
    console.print(f"[bold]收到输入: {user_input}[/]")
    
    # 模拟思考
    print("\033[1;33mHustling to answer your question...\033[0m")
    time.sleep(2)
    
    # 模拟一段Markdown格式的回复
    response = """Sure, I'd be happy to help! Here's an example of a Python function that calculates Fibonacci numbers:

```python
def fibonacci(n):
    """Calculate the nth Fibonacci number."""
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    else:
        return fibonacci(n-1) + fibonacci(n-2)
```

This is a simple recursive implementation. However, it's not very efficient for large values of n due to repeated calculations.

Would you like me to show you a more efficient implementation?"""
    
    print(response)
    time.sleep(1)
    
    # 模拟确认请求
    print("\033[1;35mWould you like to see a more efficient implementation? [y/n]\033[0m")
    
    # 读取用户确认
    confirm = input()
    console.print(f"[bold]收到确认: {confirm}[/]")
    
    # 根据确认响应
    if confirm.lower() == 'y':
        # 模拟更多输出
        more_response = """Great! Here's a more efficient implementation using dynamic programming:

```python
def fibonacci_efficient(n):
    """Calculate the nth Fibonacci number efficiently."""
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    
    # Initialize array to store Fibonacci numbers
    fib = [0] * (n + 1)
    fib[1] = 1
    
    # Fill the array using bottom-up approach
    for i in range(2, n + 1):
        fib[i] = fib[i-1] + fib[i-2]
    
    return fib[n]
```

This implementation has O(n) time complexity and O(n) space complexity."""
        
        print(more_response)
    else:
        print("Okay, let me know if you need anything else!")
    
    time.sleep(1)
    
    # 模拟按键继续
    print("\033[1;34mPress Enter to continue\033[0m")
    
    # 读取用户输入
    input()
    
    # 模拟工具使用
    print("\033[1;32mUsing tool to check performance...\033[0m")
    time.sleep(2)
    
    # 模拟函数执行结果
    performance = """Performance comparison for n=30:

| Implementation | Time (ms) |
|----------------|-----------|
| Recursive      | 832.7     |
| Dynamic        | 0.023     |

As you can see, the dynamic programming approach is significantly faster."""
    
    print(performance)
    time.sleep(1)
    
    # 模拟结束会话
    print("\033[1;32mTask completed successfully.\033[0m")
    print("\033[1;36m╭────────────────────────────────╮\n│ > █                            │\n╰────────────────────────────────╯\033[0m")
    
    # 记录交互日志
    interactions = [
        {"prompt": user_input, "response": response},
        {"prompt": confirm, "response": more_response if confirm.lower() == 'y' else "Okay, let me know if you need anything else!"},
        {"prompt": "", "response": performance}
    ]
    
    # 保存交互日志
    try:
        with open('mock_claude_interactions.json', 'w', encoding='utf-8') as f:
            json.dump(interactions, f, indent=2, ensure_ascii=False)
        console.print("[bold green]交互记录已保存到: mock_claude_interactions.json[/]")
    except Exception as e:
        console.print(f"[bold red]保存交互记录失败: {str(e)}[/]")
    
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[bold red]程序被用户中断[/]")
        sys.exit(0)