#!/usr/bin/env python3
"""
使用简化模拟环境测试claude_llm_bridge_rich.py
一个更简单的测试脚本，保证可以工作
"""

import sys
import os
import time
import json
import subprocess
from claude_llm_bridge_rich import LLMBridge, ClaudeOutputType
from rich.console import Console

# 创建控制台
console = Console()

def main():
    """主函数-直接测试LLMBridge"""
    console.print("[bold cyan]测试Claude LLM桥接增强版 (简化测试)[/]")
    
    # 创建大模型桥接
    llm_bridge = LLMBridge()
    
    # 测试添加消息
    llm_bridge.add_message("user", "测试消息")
    console.print(f"已添加消息到历史，当前历史数量: [bold]{len(llm_bridge.conversation_history)}[/]")
    
    # 测试获取决策
    test_cases = [
        ("是否继续? [y/n]", ClaudeOutputType.CONFIRMATION),
        ("按Enter继续", ClaudeOutputType.CONTINUE),
        ("出现错误，是否重试?", ClaudeOutputType.ERROR),
        ("请提供文件路径", ClaudeOutputType.INPUT_PROMPT)
    ]
    
    console.print("\n[bold cyan]测试大模型决策:[/]")
    for text, output_type in test_cases:
        decision = llm_bridge.get_decision(text, output_type)
        console.print(f"输入: [dim]{text}[/]")
        console.print(f"输出类型: [bold]{output_type.value}[/]")
        console.print(f"决策: [bold green]{decision}[/]")
        console.print("---")
    
    # 记录测试结果
    test_results = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "test_cases": [
            {
                "input": text,
                "output_type": output_type.value,
                "decision": llm_bridge.get_decision(text, output_type)
            }
            for text, output_type in test_cases
        ]
    }
    
    # 保存测试结果
    try:
        with open('rich_bridge_simple_test.json', 'w', encoding='utf-8') as f:
            json.dump(test_results, f, ensure_ascii=False, indent=2)
        console.print("[bold green]测试结果已保存到: rich_bridge_simple_test.json[/]")
    except Exception as e:
        console.print(f"[bold red]保存测试结果失败: {str(e)}[/]")
    
    # 运行模拟Claude测试
    try:
        console.print("\n[bold cyan]运行模拟Claude环境测试:[/]")
        
        # 获取模拟脚本路径
        mock_script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                      "mock_claude_for_test_simple.py")
        
        # 确保模拟脚本存在
        if not os.path.exists(mock_script_path):
            console.print(f"[bold red]错误: 模拟脚本不存在: {mock_script_path}[/]")
            return
            
        # 运行测试
        console.print("[bold yellow]启动模拟Claude环境...[/]")
        
        # 确保文件有执行权限
        os.chmod(mock_script_path, 0o755)
        
        # 启动进程
        result = subprocess.run(
            [sys.executable, mock_script_path],
            input="请介绍斐波那契数列\ny\n\n",
            text=True,
            capture_output=True
        )
        
        # 显示测试结果
        if result.returncode == 0:
            console.print("[bold green]模拟Claude测试成功[/]")
            
            # 显示输出
            console.print("\n[bold cyan]模拟Claude输出:[/]")
            console.print(result.stdout)
        else:
            console.print("[bold red]模拟Claude测试失败[/]")
            console.print(f"错误信息: {result.stderr}")
            
    except Exception as e:
        console.print(f"[bold red]运行模拟测试出错: {str(e)}[/]")

if __name__ == "__main__":
    main()