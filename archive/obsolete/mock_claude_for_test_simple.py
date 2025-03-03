#!/usr/bin/env python3
"""
简化版模拟Claude CLI用于测试
直接按顺序输出预设的响应
"""

import time
import sys

# 预设的响应序列
responses = [
    "\033[1;32mWelcome to Claude Code\033[0m",
    "\033[1;36m╭────────────────────────────────╮\n│ > █                            │\n╰────────────────────────────────╯\033[0m",
    "\033[1;33mHustling to answer your question...\033[0m",
    """Sure, I'd be happy to help! Here's a simple Python function for the Fibonacci sequence:

```python
def fibonacci(n):
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    else:
        return fibonacci(n-1) + fibonacci(n-2)
```

This is a recursive implementation, but it's not efficient for large values.
    """,
    "\033[1;35mWould you like to see a more efficient implementation? [y/n]\033[0m",
    """Great! Here's a more efficient implementation:

```python
def fibonacci_efficient(n):
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    
    a, b = 0, 1
    for _ in range(2, n+1):
        a, b = b, a + b
    return b
```

This has O(n) time complexity instead of O(2^n).
    """,
    "\033[1;34mPress Enter to continue\033[0m",
    "\033[1;32mTask completed successfully.\033[0m",
    "\033[1;36m╭────────────────────────────────╮\n│ > █                            │\n╰────────────────────────────────╯\033[0m"
]

def main():
    """输出预设响应并等待输入"""
    
    # 输出第一个响应（欢迎消息和提示）
    print(responses[0])
    print(responses[1])
    sys.stdout.flush()
    
    # 等待输入提示
    try:
        input_text = input()
    except EOFError:
        return
        
    # 输出思考和第一个回答
    print(responses[2])
    time.sleep(1)
    print(responses[3])
    sys.stdout.flush()
    
    # 输出确认请求
    print(responses[4])
    sys.stdout.flush()
    
    # 等待确认输入
    try:
        confirm = input()
    except EOFError:
        return
        
    # 输出更多答案
    print(responses[5])
    sys.stdout.flush()
    
    # 输出按键继续
    print(responses[6])
    sys.stdout.flush()
    
    # 等待按键
    try:
        input()
    except EOFError:
        return
        
    # 输出完成消息
    print(responses[7])
    print(responses[8])
    sys.stdout.flush()
    
    # 等待最后输入
    try:
        input()
    except EOFError:
        pass

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)