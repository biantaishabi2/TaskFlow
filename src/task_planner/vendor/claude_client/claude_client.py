import sys
import time
from enum import Enum
from pexpect_claude import ClaudeInteraction

class ClaudeClient:
    """Claude命令行工具的客户端封装
    
    提供了一个简单的接口，允许其他程序通过发送请求与Claude交互，
    并获取Claude的响应输出。
    """
    
    def __init__(self, debug=False, timeout=60):
        """初始化Claude客户端
        
        Args:
            debug (bool): 是否启用调试模式
            timeout (int): 等待Claude响应的超时时间（秒）
        """
        self.debug = debug
        self.timeout = timeout
        self.claude = None
        
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
                
            return True
            
        except Exception as e:
            if self.debug:
                print(f"启动Claude客户端时出错: {str(e)}")
            return False

    def send_request(self, request_text):
        """发送请求到Claude并等待响应
        
        Args:
            request_text (str): 要发送给Claude的请求文本
            
        Returns:
            str: Claude的响应文本（最后2000个字符）
            
        Raises:
            RuntimeError: Claude进程不存在或已终止
            TimeoutError: 等待响应超时
        """
        if self.claude is None or not self.claude.child.isalive():
            raise RuntimeError("Claude进程不存在或已终止")
        
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
        output = self._wait_for_response()
        
        # 返回最后2000个字符
        if len(output) > 2000:
            return output[-2000:]
        return output
    
    def close(self):
        """关闭Claude进程并释放资源"""
        if self.claude:
            self.claude.close()
            self.claude = None
    
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
    
    parser = argparse.ArgumentParser(description="Claude命令行客户端")
    parser.add_argument("--debug", action="store_true", help="启用调试模式")
    parser.add_argument("--timeout", type=int, default=60, help="响应超时时间（秒）")
    parser.add_argument("request", nargs="?", help="要发送给Claude的请求")
    args = parser.parse_args()
    
    client = ClaudeClient(debug=args.debug, timeout=args.timeout)
    
    try:
        # 启动客户端
        if not client.start():
            print("启动Claude客户端失败")
            sys.exit(1)
            
        # 如果提供了请求，发送请求并打印响应
        if args.request:
            response = client.send_request(args.request)
            print(response)
        else:
            # 否则进入交互模式
            print("Claude客户端已启动，输入空行退出")
            while True:
                try:
                    request = input("> ")
                    if not request:
                        break
                    response = client.send_request(request)
                    print(response)
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    print(f"发生错误: {str(e)}")
                    break
    finally:
        # 关闭客户端
        client.close()