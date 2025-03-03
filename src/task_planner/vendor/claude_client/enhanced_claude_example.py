#!/usr/bin/env python3
"""
增强型Claude客户端使用示例

这个示例展示了如何使用增强型Claude客户端与Claude进行交互，
特别是它的自动继续对话功能，可以智能判断任务是否完成，并自动跟进直到任务完成。
"""

import sys
import time
from enhanced_claude_client import EnhancedClaudeClient


def basic_example():
    """基本使用示例"""
    print("\n=== 基本使用示例 ===")
    
    client = EnhancedClaudeClient(debug=True)
    
    try:
        # 启动Claude客户端
        print("启动Claude客户端...")
        if not client.start():
            print("启动失败，退出")
            return
        
        # 发送一个简单请求
        print("\n发送请求: '请介绍一下Python语言的主要特点'")
        response, history = client.send_request(
            "请介绍一下Python语言的主要特点", 
            auto_continue=False  # 不自动继续对话
        )
        
        print("\n响应:")
        print("-" * 80)
        print(response)
        print("-" * 80)
        
    except Exception as e:
        print(f"发生错误: {str(e)}")
    finally:
        # 确保关闭客户端
        client.close()
        print("客户端已关闭")


def auto_continue_example():
    """自动继续对话示例"""
    print("\n=== 自动继续对话示例 ===")
    
    client = EnhancedClaudeClient(debug=True)
    
    try:
        # 启动Claude客户端
        print("启动Claude客户端...")
        if not client.start():
            print("启动失败，退出")
            return
        
        # 发送一个复杂请求，可能需要多次交互完成
        print("\n发送请求: '请写一个Python程序，包含以下功能：\n1. 读取CSV文件\n2. 分析数据\n3. 生成报表\n请分步骤详细说明'")
        
        response, history = client.send_request(
            "请写一个Python程序，包含以下功能：\n1. 读取CSV文件\n2. 分析数据\n3. 生成报表\n请分步骤详细说明", 
            auto_continue=True,  # 自动继续对话直到任务完成
            max_iterations=3     # 最多进行3次自动交互
        )
        
        print("\n最终响应:")
        print("-" * 80)
        print(response)
        print("-" * 80)
        
        # 打印完整对话历史
        print("\n完整对话历史:")
        for i, (q, a) in enumerate(history):
            print(f"\n[对话 {i+1}]")
            print(f"用户: {q}")
            print(f"Claude: {a[:100]}...")  # 只显示回答的前100个字符
        
    except Exception as e:
        print(f"发生错误: {str(e)}")
    finally:
        # 确保关闭客户端
        client.close()
        print("客户端已关闭")


def interactive_example():
    """交互式使用示例"""
    print("\n=== 交互式使用示例 ===")
    
    client = EnhancedClaudeClient(debug=True)
    
    try:
        # 启动Claude客户端
        print("启动Claude客户端...")
        if not client.start():
            print("启动失败，退出")
            return
        
        print("\n增强型Claude客户端已启动，输入空行退出")
        while True:
            try:
                request = input("> ")
                if not request:
                    break
                
                response, history = client.send_request(
                    request, 
                    auto_continue=True,
                    max_iterations=2
                )
                
                print("\n响应:")
                print("-" * 80)
                print(response)
                print("-" * 80)
                
                # 如果有自动跟进，显示交互次数
                if len(history) > 1:
                    print(f"\n(进行了 {len(history)} 次交互完成任务)")
                    
            except KeyboardInterrupt:
                print("\n收到中断信号，退出...")
                break
            except Exception as e:
                print(f"发生错误: {str(e)}")
                break
                
    except Exception as e:
        print(f"发生错误: {str(e)}")
    finally:
        # 确保关闭客户端
        client.close()
        print("客户端已关闭")


def needs_more_info_example():
    """需要更多信息示例"""
    print("\n=== 需要更多信息示例 ===")
    
    client = EnhancedClaudeClient(debug=True)
    
    try:
        # 启动Claude客户端
        print("启动Claude客户端...")
        if not client.start():
            print("启动失败，退出")
            return
        
        # 发送一个不完整请求，可能需要更多信息
        print("\n发送请求: '我需要解决一个问题'")
        
        response, history = client.send_request(
            "我需要解决一个问题", 
            auto_continue=False  # 这里关闭自动继续，因为用户需要提供更多信息
        )
        
        print("\n响应:")
        print("-" * 80)
        print(response)
        print("-" * 80)
        
        # 模拟用户提供更多信息
        print("\n提供更多信息: '我的Python程序需要定期备份数据库'")
        
        response2, history = client.send_request(
            "我的Python程序需要定期备份数据库", 
            auto_continue=True,
            max_iterations=2
        )
        
        print("\n最终响应:")
        print("-" * 80)
        print(response2)
        print("-" * 80)
        
    except Exception as e:
        print(f"发生错误: {str(e)}")
    finally:
        # 确保关闭客户端
        client.close()
        print("客户端已关闭")


def main():
    """主函数，运行所有示例"""
    print("增强型Claude客户端使用示例")
    
    # 检查命令行参数
    if len(sys.argv) > 1:
        example_name = sys.argv[1]
        if example_name == "basic":
            basic_example()
        elif example_name == "auto":
            auto_continue_example()
        elif example_name == "interactive":
            interactive_example()
        elif example_name == "more_info":
            needs_more_info_example()
        else:
            print(f"未知的示例: {example_name}")
            print("可用的示例: basic, auto, interactive, more_info")
    else:
        # 如果没有指定示例，运行基本示例
        basic_example()


if __name__ == "__main__":
    main()