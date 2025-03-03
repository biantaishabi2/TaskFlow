"""
增强型Claude客户端

基于原ClaudeClient的功能增强版，集成了任务完成状态分析和自动跟进交互功能。
可以自动判断任务是否完成，并在需要时继续对话直到任务完成。
"""

import sys
import time
import asyncio
from typing import List, Tuple, Dict, Any, Optional
from enum import Enum

# 导入原始的ClaudeInteraction类
from pexpect_claude import ClaudeInteraction

# 导入agent_tools包中的工具
from agent_tools import (
    RuleBasedAnalyzer, 
    get_default_analyzer,
    FollowupGenerator, 
    get_default_generator
)

class EnhancedClaudeClient:
    """增强型Claude客户端
    
    在原有ClaudeClient基础上，增加了任务完成状态分析和自动跟进交互功能。
    
    特点：
    - 支持外部传入请求而非硬编码
    - 能够分析任务是否完成
    - 支持自动跟进问题直到任务完成
    - 记录完整对话历史
    
    Args:
        analyzer: 任务分析器，默认使用规则分析器
        followup_generator: 跟进问题生成器，默认使用规则生成器
        debug: 是否启用调试模式
        timeout: 等待Claude响应的超时时间（秒）
    """
    
    def __init__(self, 
                 analyzer=None, 
                 followup_generator=None,
                 debug=False, 
                 timeout=60):
        """初始化增强型Claude客户端"""
        self.debug = debug
        self.timeout = timeout
        
        # Claude交互器，保持原有功能
        self.claude = None
        
        # 任务分析器，用于判断任务是否完成
        self.analyzer = analyzer or get_default_analyzer()
        
        # 跟进问题生成器，用于生成后续问题
        self.generator = followup_generator or get_default_generator()
        
        # 对话历史记录列表，每项为(问题, 回答)对
        self.conversation_history = []
        
        # 是否已初始化
        self.initialized = False
        
    def start(self):
        """启动Claude进程并准备接收请求
        
        Returns:
            bool: 启动是否成功
        """
        try:
            # 创建ClaudeInteraction实例
            self.claude = ClaudeInteraction(debug=self.debug)
            
            # 检测初始状态
            self.claude.detect_initial_state()
            
            # 如果是错误状态，则返回失败
            if self.claude.state == self.claude.state.ERROR:
                return False
                
            # 等待进入输入状态
            if self.claude.state == self.claude.state.WAIT_CONFIRM:
                self._confirm_and_wait_for_input()
            elif self.claude.state == self.claude.state.WORKING:
                self._wait_for_work_completion_and_input()
            
            self.initialized = True
            return True
            
        except Exception as e:
            if self.debug:
                print(f"启动增强型Claude客户端时出错: {str(e)}")
            return False
    
    def send_request(self, 
                     request_text, 
                     auto_continue=True, 
                     max_iterations=3):
        """发送请求并等待响应，可选择自动继续对话直到任务完成
        
        Args:
            request_text (str): 请求文本
            auto_continue (bool): 是否自动继续对话直到任务完成
            max_iterations (int): 最大自动交互次数
            
        Returns:
            str: Claude的响应文本
            list: 完整的对话历史记录
        """
        if not self.initialized or self.claude is None or not self.claude.child.isalive():
            raise RuntimeError("Claude进程不存在或未初始化")
        
        # 清空输出缓冲区
        self.claude.output_buffer = []
        
        # 确保我们在输入状态
        if self.claude.state != self.claude.state.WAIT_INPUT:
            # 如果不是输入状态，尝试重置到输入状态
            self._reset_to_input_state()
        
        # 发送请求
        if self.debug:
            print(f"发送请求: {request_text}")
        
        # 发送消息
        self.claude.child.send('\x1b')  # Escape键
        time.sleep(0.2)
        self.claude.child.sendcontrol('u')  # 清除当前输入
        time.sleep(0.2)
        self.claude.child.send(request_text)
        time.sleep(0.5)
        self.claude.child.sendcontrol('m')  # 回车
        
        # 等待消息发送
        time.sleep(0.5)
        
        # 切换到工作状态
        self.claude.state = self.claude.state.WORKING
        
        # 等待工作完成并获取输出
        response = self._wait_for_response()
        
        # 记录对话历史
        self.conversation_history.append((request_text, response))
        
        # 如果不需要自动继续，直接返回
        if not auto_continue:
            return response, self.conversation_history
        
        # 自动继续对话直到任务完成或达到最大交互次数
        iteration = 0
        while iteration < max_iterations:
            # 分析任务是否完成
            task_status = self.analyze_completion(response)
            
            # 如果任务已完成，结束交互
            if task_status == "COMPLETED":
                break
                
            # 生成跟进问题
            followup = self.generate_followup(task_status, self.conversation_history, response)
            
            # 如果没有生成跟进问题，结束交互
            if not followup:
                break
                
            # 发送跟进问题
            if self.debug:
                print(f"发送跟进问题: {followup}")
                
            # 重置到输入状态
            self._reset_to_input_state()
                
            # 发送跟进问题
            self.claude.child.send('\x1b')  # Escape键
            time.sleep(0.2)
            self.claude.child.sendcontrol('u')  # 清除当前输入
            time.sleep(0.2)
            self.claude.child.send(followup)
            time.sleep(0.5)
            self.claude.child.sendcontrol('m')  # 回车
            
            # 等待消息发送
            time.sleep(0.5)
            
            # 切换到工作状态
            self.claude.state = self.claude.state.WORKING
            
            # 等待工作完成并获取输出
            response = self._wait_for_response()
            
            # 记录对话历史
            self.conversation_history.append((followup, response))
            
            # 增加迭代计数
            iteration += 1
        
        # 返回最后的响应和完整的对话历史
        return response, self.conversation_history
    
    def analyze_completion(self, response):
        """分析任务是否完成
        
        Args:
            response (str): Claude的响应文本
            
        Returns:
            str: 任务状态，可能的值:
                - "COMPLETED": 任务已完成
                - "NEEDS_MORE_INFO": 需要更多信息
                - "CONTINUE": 任务进行中
        """
        # 检查分析器是否支持异步
        if hasattr(self.analyzer, 'analyze') and callable(self.analyzer.analyze):
            # 如果支持异步，转为同步调用
            if asyncio.iscoroutinefunction(self.analyzer.analyze):
                # 创建事件循环运行异步函数
                loop = asyncio.new_event_loop()
                try:
                    result = loop.run_until_complete(
                        self.analyzer.analyze(self.conversation_history, response)
                    )
                    return result
                finally:
                    loop.close()
            else:
                # 同步调用
                return self.analyzer.analyze(self.conversation_history, response)
        
        # 默认认为已完成
        return "COMPLETED"
    
    def generate_followup(self, task_status, conversation_history, last_response):
        """生成跟进问题
        
        Args:
            task_status (str): 任务状态
            conversation_history (list): 对话历史
            last_response (str): 最新回复
            
        Returns:
            str: 生成的跟进问题，如果不需要跟进则返回None
        """
        # 检查生成器是否支持异步
        if hasattr(self.generator, 'generate_followup') and callable(self.generator.generate_followup):
            # 如果支持异步，转为同步调用
            if asyncio.iscoroutinefunction(self.generator.generate_followup):
                # 创建事件循环运行异步函数
                loop = asyncio.new_event_loop()
                try:
                    result = loop.run_until_complete(
                        self.generator.generate_followup(task_status, conversation_history, last_response)
                    )
                    return result
                finally:
                    loop.close()
            else:
                # 同步调用
                return self.generator.generate_followup(task_status, conversation_history, last_response)
        
        # 默认跟进问题
        if task_status == "NEEDS_MORE_INFO":
            return "请提供更多信息，以便我继续帮助您。"
        elif task_status == "CONTINUE":
            return "请继续完成您的解释。"
        
        return None
    
    def close(self):
        """关闭Claude进程并释放资源"""
        if self.claude:
            self.claude.close()
            self.claude = None
            self.initialized = False
    
    def _confirm_and_wait_for_input(self):
        """处理确认提示并等待进入输入状态"""
        # 模拟处理确认的步骤
        self.claude.child.send(" ")  # 空格键
        time.sleep(1)
        
        # 检查是否已经切换到其他状态
        if self.claude.detect_working_state():
            self.claude.state = self.claude.state.WORKING
            self._wait_for_work_completion_and_input()
            return
            
        # 如果空格键失败，尝试回车键
        self.claude.child.sendcontrol('m')
        time.sleep(1)
        
        # 再次检查状态
        if self.claude.detect_working_state():
            self.claude.state = self.claude.state.WORKING
            self._wait_for_work_completion_and_input()
            return
        
        # 如果还是失败，尝试y+回车
        self.claude.child.send("y")
        time.sleep(0.2)
        self.claude.child.sendcontrol('m')
        time.sleep(1)
        
        # 最后检查一次
        if self.claude.detect_working_state():
            self.claude.state = self.claude.state.WORKING
            self._wait_for_work_completion_and_input()
            return
            
        # 如果所有方法都失败，强制设置为输入状态
        self.claude.state = self.claude.state.WAIT_INPUT
    
    def _wait_for_work_completion_and_input(self):
        """等待工作完成并进入输入状态"""
        start_time = time.time()
        
        # 等待工作完成
        while time.time() - start_time < self.timeout:
            is_working = self.claude.is_working_state()
            
            # 如果不再是工作状态，工作可能已完成
            if not is_working:
                break
                
            # 短暂休眠
            time.sleep(0.5)
        
        # 如果超时，抛出异常
        if time.time() - start_time >= self.timeout:
            raise TimeoutError(f"等待Claude响应超时（{self.timeout}秒）")
            
        # 等待一段时间，以确保完全进入输入状态
        time.sleep(1)
        
        # 检查是否进入了等待确认状态
        if self.claude.detect_wait_confirm_state():
            self.claude.state = self.claude.state.WAIT_CONFIRM
            self._confirm_and_wait_for_input()
            return
            
        # 强制设置为输入状态
        self.claude.state = self.claude.state.WAIT_INPUT
    
    def _reset_to_input_state(self):
        """尝试重置到输入状态"""
        # 发送ESC键
        self.claude.child.send('\x1b')
        time.sleep(0.5)
        
        # 检查当前状态
        if self.claude.detect_wait_confirm_state():
            self.claude.state = self.claude.state.WAIT_CONFIRM
            self._confirm_and_wait_for_input()
            return
            
        if self.claude.detect_working_state():
            self.claude.state = self.claude.state.WORKING
            self._wait_for_work_completion_and_input()
            return
            
        # 强制设置为输入状态
        self.claude.state = self.claude.state.WAIT_INPUT
    
    def _wait_for_response(self):
        """等待Claude的响应并返回"""
        start_time = time.time()
        
        # 等待工作完成
        while time.time() - start_time < self.timeout:
            is_working = self.claude.is_working_state()
            
            # 如果不再是工作状态，工作可能已完成
            if not is_working:
                break
                
            # 尝试读取输出
            try:
                output = self.claude.child.read_nonblocking(size=1000, timeout=0.5)
                if output:
                    self.claude.output_buffer.append(output)
            except:
                pass
                
            # 短暂休眠
            time.sleep(0.5)
        
        # 如果超时，抛出异常
        if time.time() - start_time >= self.timeout:
            raise TimeoutError(f"等待Claude响应超时（{self.timeout}秒）")
            
        # 再次尝试读取所有剩余输出
        try:
            output = self.claude.child.read_nonblocking(size=10000, timeout=1)
            if output:
                self.claude.output_buffer.append(output)
        except:
            pass
            
        # 获取完整输出
        full_output = "".join(self.claude.output_buffer)
        
        # 如果进入了等待确认状态，处理它
        if self.claude.detect_wait_confirm_state(full_output):
            self.claude.state = self.claude.state.WAIT_CONFIRM
            self._confirm_and_wait_for_input()
        else:
            # 否则设置为输入状态
            self.claude.state = self.claude.state.WAIT_INPUT
        
        return full_output


# 示例用法
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="增强型Claude命令行客户端")
    parser.add_argument("--debug", action="store_true", help="启用调试模式")
    parser.add_argument("--timeout", type=int, default=60, help="响应超时时间（秒）")
    parser.add_argument("--no-auto", action="store_true", help="禁用自动继续对话")
    parser.add_argument("--max-iter", type=int, default=3, help="最大自动交互次数")
    parser.add_argument("request", nargs="?", help="要发送给Claude的请求")
    args = parser.parse_args()
    
    client = EnhancedClaudeClient(debug=args.debug, timeout=args.timeout)
    
    try:
        # 启动客户端
        if not client.start():
            print("启动Claude客户端失败")
            sys.exit(1)
            
        # 如果提供了请求，发送请求并打印响应
        if args.request:
            response, history = client.send_request(
                args.request, 
                auto_continue=not args.no_auto,
                max_iterations=args.max_iter
            )
            print("\n最终响应:")
            print("-" * 80)
            print(response)
            print("-" * 80)
            
            # 打印完整对话历史
            if args.debug:
                print("\n完整对话历史:")
                for i, (q, a) in enumerate(history):
                    print(f"\n[对话 {i+1}]")
                    print(f"用户: {q}")
                    print(f"Claude: {a[:100]}...")
        else:
            # 否则进入交互模式
            print("增强型Claude客户端已启动，输入空行退出")
            while True:
                try:
                    request = input("> ")
                    if not request:
                        break
                    response, _ = client.send_request(
                        request, 
                        auto_continue=not args.no_auto,
                        max_iterations=args.max_iter
                    )
                    print(response)
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    print(f"发生错误: {str(e)}")
                    break
    finally:
        # 关闭客户端
        client.close()