#!/usr/bin/env python3
"""
Gemini增强版Claude客户端示例

这个示例展示了如何使用Gemini 2.0 Flash模型作为任务分析器，
与增强型Claude客户端集成，智能判断任务是否完成。
"""

import os
import sys
import time
from enhanced_claude_client import EnhancedClaudeClient
from agent_tools import GeminiTaskAnalyzer

def set_api_key():
    """设置Gemini API密钥
    
    如果环境变量中没有API密钥，提示用户输入
    """
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        print("未找到GEMINI_API_KEY环境变量")
        api_key = input("请输入Gemini API密钥 (或直接按回车使用伪判断功能): ")
        if api_key:
            os.environ['GEMINI_API_KEY'] = api_key
        else:
            print("没有提供API密钥，将使用伪判断功能")
    return api_key


def python_features_example():
    """Python特点分析示例
    
    使用Gemini分析器判断Python特点列表回复是否为完整回答
    """
    print("\n=== Python特点分析示例 ===")
    
    # 创建Gemini分析器
    api_key = set_api_key()
    analyzer = GeminiTaskAnalyzer(api_key=api_key)
    
    # 创建增强型客户端，使用Gemini分析器
    client = EnhancedClaudeClient(
        analyzer=analyzer,
        debug=True
    )
    
    try:
        # 启动Claude客户端
        print("启动Claude客户端...")
        if not client.start():
            print("启动失败，退出")
            return
        
        # 发送请求并获取响应
        print("\n发送请求: '请介绍一下Python语言的主要特点'")
        response, history = client.send_request(
            "请介绍一下Python语言的主要特点", 
            auto_continue=True,   # 启用自动继续
            max_iterations=2      # 最多2次自动交互
        )
        
        # 打印响应
        print("\n最终响应:")
        print("-" * 80)
        print(response)
        print("-" * 80)
        
        # 输出交互历史
        print(f"\n共进行了 {len(history)} 次交互")
        for i, (q, a) in enumerate(history):
            print(f"\n[对话 {i+1}]")
            print(f"用户/跟进: {q}")
            print(f"Claude (前100字符): {a[:100]}...")
            
            # 如果不是最后一次交互，显示Gemini的分析结果
            if i < len(history) - 1:
                status = analyzer.analyze([history[i]], a)
                print(f"Gemini分析结果: {status}")
        
    except Exception as e:
        print(f"发生错误: {str(e)}")
    finally:
        # 确保关闭客户端
        client.close()
        print("客户端已关闭")


def code_example():
    """代码编写示例
    
    使用Gemini分析器判断代码回复是否完整
    """
    print("\n=== 代码编写示例 ===")
    
    # 创建Gemini分析器
    api_key = set_api_key()
    analyzer = GeminiTaskAnalyzer(api_key=api_key)
    
    # 创建增强型客户端，使用Gemini分析器
    client = EnhancedClaudeClient(
        analyzer=analyzer,
        debug=True
    )
    
    try:
        # 启动Claude客户端
        print("启动Claude客户端...")
        if not client.start():
            print("启动失败，退出")
            return
        
        # 发送一个复杂代码请求
        print("\n发送请求: '请写一个Python函数，解析CSV文件并计算每列的统计数据'")
        
        response, history = client.send_request(
            "请写一个Python函数，解析CSV文件并计算每列的统计数据", 
            auto_continue=True,
            max_iterations=3
        )
        
        # 打印最终响应和交互历史
        print("\n最终响应:")
        print("-" * 80)
        print(response)
        print("-" * 80)
        
        # 输出交互历史
        print(f"\n共进行了 {len(history)} 次交互")
        for i, (q, a) in enumerate(history):
            print(f"\n[对话 {i+1}]")
            print(f"用户/跟进: {q}")
            print(f"Claude (前100字符): {a[:100]}...")
            
            # 如果不是最后一次交互，显示Gemini的分析结果
            if i < len(history) - 1:
                status = analyzer.analyze([history[i]], a)
                print(f"Gemini分析结果: {status}")
        
    except Exception as e:
        print(f"发生错误: {str(e)}")
    finally:
        # 确保关闭客户端
        client.close()
        print("客户端已关闭")


def partial_response_example():
    """部分回复示例
    
    故意让Claude回复不完整，测试Gemini分析器能否识别并继续
    """
    print("\n=== 部分回复示例 ===")
    
    # 创建Gemini分析器
    api_key = set_api_key()
    analyzer = GeminiTaskAnalyzer(api_key=api_key)
    
    # 创建增强型客户端，使用Gemini分析器
    client = EnhancedClaudeClient(
        analyzer=analyzer,
        debug=True
    )
    
    try:
        # 启动Claude客户端
        print("启动Claude客户端...")
        if not client.start():
            print("启动失败，退出")
            return
        
        # 发送一个需要长回复的请求
        print("\n发送请求: '请详细解释机器学习中的五种主要算法，每种算法分点说明1.定义 2.原理 3.使用场景'")
        
        response, history = client.send_request(
            "请详细解释机器学习中的五种主要算法，每种算法分点说明1.定义 2.原理 3.使用场景", 
            auto_continue=True,
            max_iterations=3
        )
        
        # 打印最终响应和交互历史
        print("\n最终响应:")
        print("-" * 80)
        print(response)
        print("-" * 80)
        
        # 输出交互历史
        print(f"\n共进行了 {len(history)} 次交互")
        for i, (q, a) in enumerate(history):
            print(f"\n[对话 {i+1}]")
            print(f"用户/跟进: {q}")
            print(f"Claude (前100字符): {a[:100]}...")
            
            # 如果不是最后一次交互，显示Gemini的分析结果
            if i < len(history) - 1:
                status = analyzer.analyze([history[i]], a)
                print(f"Gemini分析结果: {status}")
        
    except Exception as e:
        print(f"发生错误: {str(e)}")
    finally:
        # 确保关闭客户端
        client.close()
        print("客户端已关闭")


def analyze_specific_text():
    """分析特定文本示例
    
    直接使用Gemini分析器分析特定文本，不调用Claude
    """
    print("\n=== 特定文本分析示例 ===")
    
    # 创建Gemini分析器
    api_key = set_api_key()
    analyzer = GeminiTaskAnalyzer(api_key=api_key)
    
    # Python特点列表文本
    python_features = """Python是一种高级解释型编程语言，其主要特点包括:
  - 简洁易读的语法
  - 动态类型系统
  - 自动内存管理
  - 丰富的标准库
  - 跨平台兼容性
  - 面向对象编程支持
  - 函数式编程特性
  - 强大的社区和生态系统"""
    
    # 创建模拟的对话历史
    conversation_history = [("请介绍一下Python语言的主要特点", python_features)]
    
    # 使用Gemini分析器分析
    result = analyzer.analyze(conversation_history, python_features)
    
    # 打印结果
    print("\nPython特点列表文本:")
    print("-" * 80)
    print(python_features)
    print("-" * 80)
    print(f"Gemini分析结果: {result}")
    
    # 说明分析结果
    if result == "COMPLETED":
        print("Gemini认为这是一个完整回答，不需要继续")
    elif result == "CONTINUE":
        print("Gemini认为回答未完成，需要继续解释")
    elif result == "NEEDS_MORE_INFO":
        print("Gemini认为需要用户提供更多信息")


def main():
    """主函数，运行示例"""
    print("Gemini增强版Claude客户端示例")
    
    # 检查命令行参数
    if len(sys.argv) > 1:
        example_name = sys.argv[1]
        if example_name == "python":
            python_features_example()
        elif example_name == "code":
            code_example()
        elif example_name == "partial":
            partial_response_example()
        elif example_name == "analyze":
            analyze_specific_text()
        else:
            print(f"未知的示例: {example_name}")
            print("可用的示例: python, code, partial, analyze")
    else:
        # 默认运行特定文本分析示例，不需要启动Claude
        analyze_specific_text()


if __name__ == "__main__":
    main()