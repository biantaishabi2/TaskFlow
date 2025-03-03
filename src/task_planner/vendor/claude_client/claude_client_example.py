#!/usr/bin/env python3
"""
Claude客户端使用示例

这个示例展示了如何使用ClaudeClient来与Claude进行交互，
包括基本调用、连续对话、错误处理等场景。
"""

import time
import sys
from claude_client import ClaudeClient


def basic_example():
    """基本使用示例"""
    print("\n=== 基本使用示例 ===")
    
    client = ClaudeClient()
    
    try:
        # 启动Claude客户端
        print("启动Claude客户端...")
        if not client.start():
            print("启动失败，退出")
            return
        
        # 发送一个简单请求
        print("发送请求: '请介绍一下自己'")
        response = client.send_request("请介绍一下自己")
        print(f"Claude响应:\n{response}\n")
        
    except Exception as e:
        print(f"发生错误: {str(e)}")
    finally:
        # 确保关闭客户端
        client.close()
        print("客户端已关闭")


def conversation_example():
    """连续对话示例"""
    print("\n=== 连续对话示例 ===")
    
    client = ClaudeClient()
    
    try:
        # 启动Claude客户端
        print("启动Claude客户端...")
        if not client.start():
            print("启动失败，退出")
            return
        
        # 第一个请求
        print("发送请求1: '请给我一个Python函数来计算斐波那契数列'")
        response1 = client.send_request("请给我一个Python函数来计算斐波那契数列")
        print(f"Claude响应1:\n{response1}\n")
        
        # 等待一下，让用户看清输出
        time.sleep(1)
        
        # 第二个请求，基于第一个请求的上下文
        print("发送请求2: '如何优化这个函数？'")
        response2 = client.send_request("如何优化这个函数？")
        print(f"Claude响应2:\n{response2}\n")
        
    except Exception as e:
        print(f"发生错误: {str(e)}")
    finally:
        # 确保关闭客户端
        client.close()
        print("客户端已关闭")


def timeout_example():
    """超时处理示例"""
    print("\n=== 超时处理示例 ===")
    
    # 创建一个超时时间很短的客户端
    client = ClaudeClient(timeout=5)  # 只等待5秒
    
    try:
        # 启动Claude客户端
        print("启动Claude客户端...")
        if not client.start():
            print("启动失败，退出")
            return
        
        # 发送一个需要较长时间处理的复杂请求
        print("发送复杂请求: '请写一个详细的机器学习模型来预测股票价格，包括数据预处理、特征工程、模型选择和评估'")
        print("由于设置了5秒超时，这个请求可能会超时...")
        
        response = client.send_request("请写一个详细的机器学习模型来预测股票价格，包括数据预处理、特征工程、模型选择和评估")
        print(f"Claude响应:\n{response}\n")
        
    except TimeoutError:
        print("请求超时，这是预期的行为")
    except Exception as e:
        print(f"发生其他错误: {str(e)}")
    finally:
        # 确保关闭客户端
        client.close()
        print("客户端已关闭")


def integration_example():
    """集成到其他程序的示例"""
    print("\n=== 集成到其他程序的示例 ===")
    
    # 模拟一个简单的文本处理程序
    texts = [
        "什么是机器学习？",
        "什么是深度学习？",
        "什么是自然语言处理？"
    ]
    
    client = ClaudeClient()
    results = {}
    
    try:
        # 启动Claude客户端
        print("启动Claude客户端...")
        if not client.start():
            print("启动失败，退出")
            return
        
        # 批量处理多个文本请求
        for i, text in enumerate(texts):
            print(f"处理文本 {i+1}/{len(texts)}: '{text}'")
            
            # 发送请求给Claude
            response = client.send_request(f"请用一句话回答: {text}")
            
            # 存储结果
            results[text] = response.strip()
            
            # 简单的进度显示
            print(f"已完成: {i+1}/{len(texts)}")
        
        # 显示所有结果
        print("\n处理结果:")
        for question, answer in results.items():
            print(f"问: {question}")
            print(f"答: {answer}")
            print("-" * 40)
        
    except Exception as e:
        print(f"发生错误: {str(e)}")
    finally:
        # 确保关闭客户端
        client.close()
        print("客户端已关闭")


def main():
    """主函数，运行所有示例"""
    print("Claude客户端使用示例")
    
    # 检查命令行参数
    if len(sys.argv) > 1:
        example_name = sys.argv[1]
        if example_name == "basic":
            basic_example()
        elif example_name == "conversation":
            conversation_example()
        elif example_name == "timeout":
            timeout_example()
        elif example_name == "integration":
            integration_example()
        else:
            print(f"未知的示例: {example_name}")
            print("可用的示例: basic, conversation, timeout, integration")
    else:
        # 如果没有指定示例，运行基本示例
        basic_example()


if __name__ == "__main__":
    main()