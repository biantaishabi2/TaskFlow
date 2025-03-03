import asyncio
import re
import sys
import os
from enum import Enum
import time

class ClaudeInteractionState(Enum):
    INITIALIZED = 0
    WAITING_FOR_CLAUDE = 1
    PROCESSING_OUTPUT = 2
    NEEDS_CONFIRMATION = 3
    WAITING_FOR_MODEL = 4
    SENDING_TO_CLAUDE = 5
    COMPLETED = 6
    ERROR = 7

class MockLLMApi:
    """模拟大模型API，用于测试"""
    
    async def get_decision(self, context):
        """
        根据上下文返回决策
        
        参数:
            context (str): Claude输出的上下文
            
        返回:
            str: 决策，如 "y", "n", 空行等
        """
        print("\n大模型收到上下文:")
        print("-" * 40)
        print(context)
        print("-" * 40)
        
        # 简单模式匹配
        if re.search(r'\[y/n\]', context):
            decision = "y"
        elif re.search(r'press enter', context, re.IGNORECASE):
            decision = ""
        elif re.search(r'provide a.*path', context, re.IGNORECASE):
            decision = "/tmp/example.txt"
        else:
            # 默认响应
            decision = "y"
            
        print(f"大模型决策: '{decision}'")
        return decision

async def parse_claude_output(output):
    """解析Claude输出，检测是否需要用户确认"""
    # 检测需要用户确认的模式
    confirmation_patterns = [
        r'Do you want to proceed\?',
        r'Shall I continue\?',
        r'\[y/n\]',
        r'Press Enter to continue',
        r'确认.*\?',
        r'您想要.*吗\?'
    ]
    
    # 检测命令完成的模式
    completion_patterns = [
        r'执行完成',
        r'任务已完成',
        r'Done',
        r'Completed'
    ]
    
    # 检测错误模式
    error_patterns = [
        r'Error:',
        r'错误:',
        r'Failed to',
        r'无法.*'
    ]
    
    for pattern in confirmation_patterns:
        if re.search(pattern, output):
            return {"state": "needs_confirmation", "message": output}
    
    for pattern in completion_patterns:
        if re.search(pattern, output):
            return {"state": "completed", "message": output}
            
    for pattern in error_patterns:
        if re.search(pattern, output):
            return {"state": "error", "message": output}
    
    return {"state": "waiting", "message": output}

async def create_claude_process():
    """创建Claude命令行进程"""
    process = await asyncio.create_subprocess_exec(
        'claude',
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    return process

async def interact_with_claude(initial_prompt, model_api=None, timeout=300):
    """
    与Claude交互的主函数
    
    参数:
        initial_prompt (str): 初始提示
        model_api: 大模型API对象，用于决策
        timeout (int): 超时时间（秒）
        
    返回:
        dict: 包含状态、输出和最终状态的字典
    """
    if model_api is None:
        model_api = MockLLMApi()
        
    # 启动Claude进程
    print("启动Claude进程...")
    process = await create_claude_process()
    state = ClaudeInteractionState.SENDING_TO_CLAUDE
    
    # 发送初始提示
    print(f"发送初始提示: {initial_prompt}")
    process.stdin.write(f"{initial_prompt}\n".encode())
    await process.stdin.drain()
    
    buffer = ""
    output_collector = []
    
    # 设置超时
    start_time = time.time()
    
    try:
        while time.time() - start_time < timeout:
            if state == ClaudeInteractionState.WAITING_FOR_CLAUDE or state == ClaudeInteractionState.SENDING_TO_CLAUDE:
                # 读取Claude输出
                try:
                    # 使用异步读取一行，超时1秒
                    line_bytes = await asyncio.wait_for(process.stdout.readline(), 1.0)
                    line = line_bytes.decode('utf-8')
                    
                    if not line:
                        # 没有更多输出，等待一下
                        await asyncio.sleep(0.1)
                        continue
                        
                    # 处理输出
                    buffer += line
                    cleaned_line = line.strip()
                    if cleaned_line:  # 只保存非空行
                        output_collector.append(cleaned_line)
                    print(f"Claude: {cleaned_line}")
                    
                    # 分析输出
                    result = await parse_claude_output(buffer)
                    
                    if result["state"] == "needs_confirmation":
                        state = ClaudeInteractionState.NEEDS_CONFIRMATION
                        # 保存最近的上下文
                        recent_context = "\n".join(output_collector[-10:]) if output_collector else buffer
                        
                        # 调用大模型决策
                        print("需要用户确认，正在调用大模型...")
                        decision = await model_api.get_decision(recent_context)
                        
                        # 发送决策回Claude
                        print(f"向Claude发送: {repr(decision)}")
                        process.stdin.write(f"{decision}\n".encode())
                        await process.stdin.drain()
                        
                        # 重置状态
                        state = ClaudeInteractionState.WAITING_FOR_CLAUDE
                        
                    elif result["state"] == "completed":
                        print("检测到任务完成")
                        return {
                            "status": "completed",
                            "output": "\n".join(output_collector),
                            "final_state": buffer
                        }
                        
                    elif result["state"] == "error":
                        print("检测到错误")
                        return {
                            "status": "error",
                            "output": "\n".join(output_collector),
                            "final_state": buffer
                        }
                    
                except asyncio.TimeoutError:
                    # 读取超时，继续尝试
                    await asyncio.sleep(0.1)
                    
                # 检查进程是否仍在运行
                if process.returncode is not None:
                    print(f"Claude进程已退出，返回码: {process.returncode}")
                    break
                    
            else:
                # 其他状态，等待一下
                await asyncio.sleep(0.1)
                
        # 超时
        print(f"与Claude交互超时 ({timeout}秒)")
        return {
            "status": "timeout",
            "output": "\n".join(output_collector),
            "final_state": buffer
        }
        
    finally:
        # 确保进程正确关闭
        if process.returncode is None:
            print("正在关闭Claude进程...")
            try:
                process.stdin.write(b"/exit\n")
                await process.stdin.drain()
                try:
                    await asyncio.wait_for(process.wait(), 2.0)
                except asyncio.TimeoutError:
                    process.kill()
            except:
                process.kill()
                
        print("Claude交互结束")

async def main():
    """主函数"""
    # 使用模拟的大模型API
    model_api = MockLLMApi()
    
    # 与Claude交互
    result = await interact_with_claude(
        "写一个Python函数，使用递归方式计算斐波那契数列的第n项",
        model_api,
        timeout=60
    )
    
    # 打印结果
    print("\n" + "="*50)
    print("交互结果:")
    print(f"状态: {result['status']}")
    print("输出摘要:")
    output_lines = result['output'].split("\n")
    if len(output_lines) > 10:
        # 只显示前5行和后5行
        print("\n".join(output_lines[:5]))
        print("\n... (省略中间内容) ...\n")
        print("\n".join(output_lines[-5:]))
    else:
        print(result['output'])
    
if __name__ == "__main__":
    asyncio.run(main())