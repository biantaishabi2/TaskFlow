import pexpect
import re
import sys
import time
from enum import Enum

class ClaudeState(Enum):
    INITIAL = 0        # 初始状态
    WAIT_CONFIRM = 1   # 等待确认状态
    WAIT_INPUT = 2     # 等待输入状态
    WORKING = 3        # 工作状态
    ERROR = 4          # 错误状态

class ClaudeInteraction:
    def __init__(self, debug=False):
        """初始化Claude交互器"""
        self.debug = debug
        self.child = None
        self.state = ClaudeState.INITIAL
        self.exit_requested = False
        self.output_buffer = []
        self.input_processed = False  # 标记是否已处理过输入
        
        # 状态匹配模式
        self.patterns = {
            # 初始状态 - 首次运行特征
            'initial_first_time': r"Do you trust the files in this folder\?.*Yes, proceed.*No, exit.*Enter to confirm · Esc to exit",
            
            # 初始状态 - 非首次运行特征 (欢迎信息)
            'initial_not_first_time': r"✻ Welcome to Claude Code.*cwd:.*",
            
            # 初始状态 - 直接显示输入框
            'initial_input_prompt': r"╭.*\n│ >",
            
            # 工作状态特征
            'working': r"∗ .+\.\.\. \(\d+s · esc to interrupt\)",
            
            # 修改的等待确认状态匹配模式
            'wait_confirm': r"Do you want to .+\?.*Yes.*No",
        }
        
        # 启动Claude进程
        self.start_claude()
        
    def start_claude(self):
        """启动Claude进程"""
        print("启动Claude进程...")
        
        try:
            # 创建pexpect子进程
            self.child = pexpect.spawn('claude', encoding='utf-8')
            
            # 设置终端大小 (行，列)
            self.child.setwinsize(40, 120)
            
            # 如果需要debug，设置日志
            if self.debug:
                self.child.logfile = sys.stdout
                
            # 等待一小段时间，确保进程启动
            time.sleep(1)
            
            # 检查进程是否成功启动
            if not self.child.isalive():
                print("Claude进程启动失败")
                self.state = ClaudeState.ERROR
                return False
                
            print("Claude进程启动成功")
            return True
            
        except Exception as e:
            print(f"启动Claude进程时出错: {str(e)}")
            self.state = ClaudeState.ERROR
            return False
    
    def detect_initial_state(self):
        """检测初始状态"""
        print("检测初始状态...")
        
        # 检查Claude进程是否存在
        if self.child is None or not self.child.isalive():
            print("Claude进程不存在或已终止")
            self.state = ClaudeState.ERROR
            return
        
        # 先等待一段时间，让Claude完全启动
        time.sleep(1)
        
        # 尝试直接读取所有可用输出
        try:
            # 使用read_nonblocking读取所有可用输出
            output = ""
            try:
                # 尝试读取最多10000个字符
                output = self.child.read_nonblocking(size=10000, timeout=1)
                print(f"读取到的输出: {output}")
                self.output_buffer.append(output)
            except pexpect.TIMEOUT:
                # 超时意味着没有更多输出可读
                print("读取超时，没有更多输出")
            except Exception as e:
                print(f"读取输出时出错: {str(e)}")
            
            # 首先检查是否处于等待确认状态
            if self.detect_wait_confirm_state(output):
                print("初始检测到等待确认状态")
                self.state = ClaudeState.WAIT_CONFIRM
                return
                
            # 然后检查是否处于工作状态
            if self.detect_working_state():
                print("初始检测到工作状态")
                self.state = ClaudeState.WORKING
                return
                
            # 如果不是上述状态，检查是否是等待输入状态
            if "Welcome to Claude" in output or ">" in output:
                print("检测到Claude欢迎信息或输入提示符，等待输入")
                self.state = ClaudeState.WAIT_INPUT
            else:
                # 如果上述都没匹配到，尝试直接进入输入状态
                print("无法在输出中检测到特定状态，假定为输入状态")
                self.state = ClaudeState.WAIT_INPUT
                
        except Exception as e:
            print(f"检测初始状态时出错: {str(e)}")
            # 即使出错，也尝试假设为输入状态
            print("出错后假定为输入状态")
            self.state = ClaudeState.WAIT_INPUT
            
        print(f"初始状态检测完成，当前状态: {self.state}")
    
    def handle_current_state(self):
        """根据当前状态执行相应操作"""
        print(f"handle_current_state: 当前状态 = {self.state}")
        
        # 无论当前状态是什么，先检测是否实际处于等待确认状态
        if self.state != ClaudeState.WAIT_CONFIRM and self.detect_wait_confirm_state():
            print("检测到等待确认状态，覆盖当前状态")
            self.state = ClaudeState.WAIT_CONFIRM
            
        # 根据状态执行相应操作
        if self.state == ClaudeState.WAIT_CONFIRM:
            print("处理等待确认状态...")
            
            # 清除缓冲区，避免旧数据影响判断
            self.output_buffer = []
            
            # 直接发送空格键选择当前高亮的Yes选项
            print("发送空格键选择Yes...")
            self.child.send(" ")  
            time.sleep(1)
            
            # 检查是否进入了工作状态
            if self.detect_working_state():
                print("确认成功，检测到工作状态")
                self.state = ClaudeState.WORKING
                self.process_working()
                return True
            
            # 如果空格键失败，尝试发送回车键确认
            print("尝试发送回车键确认...")
            self.child.sendcontrol('m')  # Ctrl+M是回车
            time.sleep(1)
            
            # 再次检查是否进入了工作状态
            if self.detect_working_state():
                print("确认成功，检测到工作状态")
                self.state = ClaudeState.WORKING
                self.process_working()
                return True
            
            # 如果上述方法都失败，尝试直接发送y确认
            print("尝试直接发送y确认...")
            self.child.send("y")  # 输入y
            time.sleep(0.2)
            self.child.sendcontrol('m')  # 发送回车
            time.sleep(1)
            
            # 再次检查是否进入了工作状态
            if self.detect_working_state():
                print("确认成功，检测到工作状态")
                self.state = ClaudeState.WORKING
                self.process_working()
                return True
                
            # 如果所有方法都失败，则切换到输入状态
            print("确认方法都失败，切换到输入状态")
            self.state = ClaudeState.WAIT_INPUT
            
        elif self.state == ClaudeState.WAIT_INPUT:
            print("处理等待输入状态...")
            print("准备调用 process_wait_input()")
            self.process_wait_input()
            print("process_wait_input() 执行完毕")
            
        elif self.state == ClaudeState.WORKING:
            print("处理工作状态...")
            print("准备调用 process_working()")
            self.process_working()
            print("process_working() 执行完毕")
            
        elif self.state == ClaudeState.ERROR:
            print("错误状态，退出交互")
            return False
        
        print(f"handle_current_state: 处理后状态 = {self.state}")
        return True
    
    def process_wait_input(self):
        """处理等待输入状态"""
        print("处理等待输入状态...")
        
        # 检查Claude进程是否存在
        if self.child is None or not self.child.isalive():
            print("Claude进程不存在或已终止")
            self.state = ClaudeState.ERROR
            return
            
        # 检查是否已经处理过输入
        if self.input_processed:
            print("已经处理过输入，退出程序")
            self.exit_requested = True
            return
            
        # 这里可以添加你的输入逻辑
        message = "请帮我创建1.txt"  # 默认测试消息
        print(f"发送消息: {message}")
        
        # 发送消息
        self.child.send('\x1b')
        time.sleep(0.2)
        self.child.sendcontrol('u')  
        time.sleep(0.2)
        self.child.send(message)  # 使用send而不是sendline
        time.sleep(0.5)
        self.child.sendcontrol('m')
        
        # 等待消息发送
        time.sleep(1)
        
        # 检测工作状态
        is_working = self.detect_working_state()
        
        # 无论检测结果如何，都设置为工作状态
        self.state = ClaudeState.WORKING
        print("设置为工作状态")
        
        # 标记已处理输入
        self.input_processed = True
        print("输入已处理，下次进入此状态将退出程序")
    
    def is_working_state(self):
        """检测是否处于工作状态"""
        # 使用detect_working_state方法并捕获任何可能的输出
        try:
            # 先尝试读取当前可用的输出
            try:
                output = self.child.read_nonblocking(size=1000, timeout=0.5)
                if output:
                    self.output_buffer.append(output)
                    if "esc to interrupt" in output:
                        print("在读取的输出中检测到工作状态标识")
                        return True
            except:
                pass
                
            # 使用封装的方法进行检测
            is_working = self.detect_working_state()
            
            # 如果封装方法检测到工作状态
            if is_working:
                return True
                
            # 如果没有检测到，尝试再次读取一些输出
            try:
                output = self.child.read_nonblocking(size=1000, timeout=0.5)
                if output:
                    self.output_buffer.append(output)
                    if "esc to interrupt" in output:
                        print("在额外读取的输出中检测到工作状态标识")
                        return True
            except:
                pass
                
            # 如果所有方法都没有检测到工作状态
            return False
            
        except Exception as e:
            print(f"is_working_state 检测出错: {str(e)}")
            return False
    
    def wait_for_work_completion(self):
        """等待工作完成"""
        print("等待工作完成...")
        
        # 设置最大尝试次数，避免无限循环
        max_attempts = 30
        attempts = 0
        
        # 设置超时时间（秒）
        timeout_seconds = 60
        start_time = time.time()
        
        # 添加延迟检查，确保我们有足够的时间捕获工作状态
        time.sleep(0.5)
        
        while attempts < max_attempts and (time.time() - start_time) < timeout_seconds:
            print(f"等待新的输出...尝试 {attempts+1}/{max_attempts}")
            
            # 检查是否仍在工作状态
            if self.is_working_state():
                print("检测到工作状态，继续等待...")
                # 仍在工作状态，继续等待，但添加延迟
                time.sleep(1)
                attempts += 1
                continue
            
            # 检查是否我们可能错过了工作状态的结束
            # 尝试读取当前输出
            try:
                # 尝试读取所有可用输出
                output = ""
                try:
                    # 非阻塞读取最多1000个字符
                    output = self.child.read_nonblocking(size=1000, timeout=1)
                except pexpect.TIMEOUT:
                    # 超时意味着没有更多输出可读
                    pass
                except Exception as e:
                    print(f"读取输出时出错: {str(e)}")
                
                # 将读取的输出添加到缓冲区
                if output:
                    self.output_buffer.append(output)
                    print(f"读取到新输出: {output[:100]}...")
                    
                    # 再次检查是否仍在工作状态
                    if "esc to interrupt" in output:
                        print("在新输出中检测到工作状态标识，继续等待...")
                        time.sleep(1)
                        attempts += 1
                        continue
            except Exception as e:
                print(f"检查输出时出错: {str(e)}")
            
            # 尝试检测是否进入了等待确认状态
            if self.detect_wait_confirm_state():
                print("检测到等待确认状态，工作已完成")
                return
            
            # 如果到这里，说明不在工作状态，也不在等待确认状态，认为工作已完成
            print("未检测到工作状态和等待确认状态，工作完成")
            return
        
        # 如果超出最大尝试次数或超时，也认为完成（可能是某种状态导致无法检测到完成）
        print(f"达到最大尝试次数({max_attempts})或超时({timeout_seconds}秒)，假定工作已完成")
        return
    
    def process_working(self):
        """处理工作状态"""
        print("处理工作状态...")
        
        try:
            # 确保处于工作状态
            if self.state != ClaudeState.WORKING:
                print("尝试重新检测工作状态...")
                is_working = self.detect_working_state()
                if not is_working:
                    print("未检测到工作状态，强制设置为工作状态")
                self.state = ClaudeState.WORKING
                
            # 等待工作完成
            self.wait_for_work_completion()
            
            # 获取完整输出
            full_output = "".join(self.output_buffer)
            print(f"工作状态完成后的完整输出: {full_output}")
            
            # 使用封装方法检测等待确认状态
            if self.detect_wait_confirm_state(full_output):
                print("检测到确认提示，切换到等待确认状态")
                self.state = ClaudeState.WAIT_CONFIRM
            else:
                print("未检测到确认提示，进入等待输入状态")
                self.state = ClaudeState.WAIT_INPUT
                
            return True
                
        except Exception as e:
            print(f"处理工作状态时出错: {str(e)}")
            self.state = ClaudeState.ERROR
            return False
    
    def run_interaction(self):
        """运行交互流程"""
        # 检测初始状态
        self.detect_initial_state()
        
        # 主交互循环
        while True:
            print(f"\n当前状态: {self.state}")  # 添加状态打印
            
            # 处理当前状态
            success = self.handle_current_state()
            
            # 如果处理失败或状态为ERROR，退出循环
            if not success or self.state == ClaudeState.ERROR:
                print("状态处理失败或遇到错误，退出循环")
                break
                
            # 如果用户要求退出，也退出循环
            if self.exit_requested:
                print("用户请求退出")
                break
                
            # 等待一小段时间，避免CPU占用过高
            time.sleep(0.1)
        
        # 退出前发送/exit命令
        print("退出交互")
        self.child.sendline("/exit")
        
        # 等待Claude退出
        try:
            self.child.expect(pexpect.EOF, timeout=5)
        except:
            # 如果等待超时，强制关闭
            self.child.close(force=True)
    
    def detect_wait_confirm_state(self, content=None):
        """检测是否处于等待确认状态，返回布尔值"""
        print("尝试检测等待确认状态...")
        
        # 定义确认提示词列表（移到方法开头，使所有代码块都能访问）
        confirm_phrases = [
            "Do you want to create",
            "Do you want to",
            "Yes/No",
            "Yes or No",
            "Yes / No"
        ]
        
        try:
            # 如果提供了内容，直接检查
            if content:
                for phrase in confirm_phrases:
                    if phrase in content:
                        print(f"在内容中检测到确认提示: '{phrase}'")
                        return True
            
            # 如果没有提供内容或内容中没有确认提示，尝试从屏幕获取
            try:
                # 获取当前屏幕内容
                before_content = str(self.child.before) if self.child.before else ""
                after_content = str(self.child.after) if self.child.after else ""
                full_content = before_content + after_content
                
                # 检查屏幕内容
                for phrase in confirm_phrases:
                    if phrase in full_content:
                        print(f"在屏幕内容中检测到确认提示: '{phrase}'")
                        return True
                
                # 尝试使用模式匹配
                try:
                    # 使用预定义的等待确认模式
                    self.child.expect(self.patterns['wait_confirm'], timeout=1)
                    print("使用模式匹配检测到等待确认状态")
                    return True
                except:
                    # 如果模式匹配失败，尝试读取更多内容
                    try:
                        output = self.child.read_nonblocking(size=1000, timeout=0.5)
                        if output:
                            self.output_buffer.append(output)  # 添加到输出缓冲区
                            for phrase in confirm_phrases:
                                if phrase in output:
                                    print(f"在额外读取的内容中检测到确认提示: '{phrase}'")
                                    return True
                    except:
                        pass
            except Exception as screen_e:
                print(f"检查屏幕内容时出错: {str(screen_e)}")
            
            # 如果所有检查都没有发现等待确认状态
            print("未检测到等待确认状态")
            return False
            
        except Exception as e:
            print(f"检测等待确认状态时出错: {str(e)}")
            return False
            
    def detect_working_state(self):
        """检测是否处于工作状态，返回布尔值"""
        print("尝试检测工作状态指示符...")
        
        try:
            # 首先输出当前的屏幕内容用于调试
            try:
                before_content = str(self.child.before) if self.child.before else ""
                after_content = str(self.child.after) if self.child.after else ""
                full_content = before_content + after_content
                print(f"当前屏幕内容(部分): {full_content[-100:] if len(full_content) > 100 else full_content}")
                
                # 检查屏幕内容是否包含目标文本，不依赖pexpect的expect
                if "esc to interrupt" in full_content:
                    print("屏幕内容中发现 'esc to interrupt'")
                    return True
            except Exception as debug_e:
                print(f"获取屏幕内容出错: {str(debug_e)}")
            
            # 尝试使用正则表达式匹配，更灵活
            import re
            self.child.expect([re.compile(r'esc.*interrupt'), re.compile(r'interrupt')], timeout=2)
            print("检测到工作状态指示符")
            return True
        except Exception as e:
            print(f"未检测到工作状态指示符: {str(e)}")
            return False
    
    def close(self):
        """关闭Claude进程"""
        if self.child:
            try:
                self.child.sendline("/exit")
                self.child.expect(pexpect.EOF, timeout=5)
            except:
                # 如果正常退出失败，强制关闭
                self.child.close(force=True)

if __name__ == "__main__":
    # 解析命令行参数
    import argparse
    parser = argparse.ArgumentParser(description="与Claude命令行工具交互")
    parser.add_argument("--debug", action="store_true", help="启用调试模式")
    args = parser.parse_args()
    
    # 创建交互对象
    interaction = ClaudeInteraction(debug=args.debug)
    
    try:
        # 运行交互
        interaction.run_interaction()
    finally:
        # 确保关闭Claude进程
        interaction.close() 
