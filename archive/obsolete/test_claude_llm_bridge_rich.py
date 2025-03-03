#!/usr/bin/env python3
"""
测试claude_llm_bridge_rich.py的功能
使用mock对象模拟Claude CLI进程
"""

import sys
import unittest
from unittest.mock import patch, MagicMock
import io
from claude_llm_bridge_rich import ClaudeOutputType, LLMBridge, ClaudeBridge

class TestLLMBridge(unittest.TestCase):
    """测试LLM桥接功能"""
    
    def setUp(self):
        """设置测试环境"""
        self.llm_bridge = LLMBridge()
        
    def test_add_message(self):
        """测试添加消息到历史"""
        self.llm_bridge.add_message("user", "测试消息")
        self.assertEqual(len(self.llm_bridge.conversation_history), 1)
        self.assertEqual(self.llm_bridge.conversation_history[0]["role"], "user")
        self.assertEqual(self.llm_bridge.conversation_history[0]["content"], "测试消息")
        
    def test_get_decision(self):
        """测试获取决策"""
        # 测试确认决策
        decision = self.llm_bridge.get_decision("是否继续? [y/n]", ClaudeOutputType.CONFIRMATION)
        self.assertEqual(decision, "y")
        
        # 测试继续决策
        decision = self.llm_bridge.get_decision("按Enter继续", ClaudeOutputType.CONTINUE)
        self.assertEqual(decision, "")
        
        # 测试错误决策
        decision = self.llm_bridge.get_decision("出现错误，是否重试?", ClaudeOutputType.ERROR)
        self.assertIn(decision, ["n", "retry"])
        
        # 测试输入提示决策
        decision = self.llm_bridge.get_decision("请提供文件路径", ClaudeOutputType.INPUT_PROMPT)
        self.assertEqual(decision, "/tmp/example.txt")

class MockPexpect:
    """模拟pexpect子进程"""
    
    def __init__(self, expected_responses):
        """
        初始化模拟对象
        
        参数:
            expected_responses: 预期响应列表，每项是(pattern, response)元组
        """
        self.expected_responses = expected_responses
        self.current_index = 0
        self.before = ""
        self.after = ""
        self.isalive_flag = True
        self.encoding = 'utf-8'
        self.mock_logs = []
        
    def expect(self, patterns, timeout=None):
        """模拟expect方法"""
        if self.current_index >= len(self.expected_responses):
            raise EOFError("模拟进程已结束")
            
        # 获取当前响应
        pattern_index, response = self.expected_responses[self.current_index]
        self.current_index += 1
        
        # 设置before和after
        if isinstance(response, tuple):
            self.before, self.after = response
        else:
            self.before = response
            self.after = patterns[pattern_index] if isinstance(patterns, list) else patterns
            
        # 记录日志
        self.mock_logs.append({
            "event": "expect",
            "patterns": patterns,
            "matched_index": pattern_index,
            "before": self.before,
            "after": self.after
        })
        
        return pattern_index
        
    def sendline(self, line):
        """模拟sendline方法"""
        self.mock_logs.append({
            "event": "sendline",
            "line": line
        })
        
    def isalive(self):
        """模拟isalive方法"""
        return self.isalive_flag
        
    def close(self, force=False):
        """模拟close方法"""
        self.isalive_flag = False
        self.mock_logs.append({
            "event": "close",
            "force": force
        })
        
    def setwinsize(self, rows, cols):
        """模拟setwinsize方法"""
        pass

class TestClaudeBridge(unittest.TestCase):
    """测试Claude桥接功能"""
    
    @patch('claude_llm_bridge_rich.pexpect')
    def test_start(self, mock_pexpect):
        """测试启动Claude进程"""
        # 设置mock
        mock_pexpect.spawn.return_value = MockPexpect([
            (0, "Welcome to Claude Code")
        ])
        
        # 创建桥接器
        bridge = ClaudeBridge(debug=True)
        
        # 测试启动
        result = bridge.start()
        self.assertTrue(result)
        self.assertTrue(mock_pexpect.spawn.called)
        
    @patch('claude_llm_bridge_rich.pexpect')
    def test_send_message(self, mock_pexpect):
        """测试发送消息"""
        # 设置mock
        mock_child = MockPexpect([])
        mock_pexpect.spawn.return_value = mock_child
        
        # 创建桥接器
        bridge = ClaudeBridge()
        bridge.child = mock_child
        
        # 测试发送消息
        result = bridge.send_message("测试消息")
        self.assertTrue(result)
        self.assertEqual(mock_child.mock_logs[-1]["event"], "sendline")
        self.assertEqual(mock_child.mock_logs[-1]["line"], "测试消息")
        
    def test_analyze_output(self):
        """测试分析输出"""
        bridge = ClaudeBridge()
        
        # 测试思考中
        output_type, _ = bridge.analyze_output("Hustling to answer your question...")
        self.assertEqual(output_type, ClaudeOutputType.THINKING)
        
        # 测试输入提示
        output_type, _ = bridge.analyze_output("╭──────────╮\n│ > │\n╰──────────╯")
        self.assertEqual(output_type, ClaudeOutputType.INPUT_PROMPT)
        
        # 测试确认请求
        output_type, _ = bridge.analyze_output("是否继续? [y/n]")
        self.assertEqual(output_type, ClaudeOutputType.CONFIRMATION)
        
        # 测试继续
        output_type, _ = bridge.analyze_output("Press Enter to continue")
        self.assertEqual(output_type, ClaudeOutputType.CONTINUE)
        
        # 测试错误
        output_type, _ = bridge.analyze_output("Error: Failed to process your request")
        self.assertEqual(output_type, ClaudeOutputType.ERROR)
        
        # 测试工具使用
        output_type, _ = bridge.analyze_output("using tool to find information")
        self.assertEqual(output_type, ClaudeOutputType.TOOL_USAGE)
        
        # 测试完成
        output_type, _ = bridge.analyze_output("Task completed successfully")
        self.assertEqual(output_type, ClaudeOutputType.COMPLETE)
        
    @patch('claude_llm_bridge_rich.pexpect')
    def test_run_session_basic(self, mock_pexpect):
        """测试基本会话运行"""
        # 设置mock
        mock_pexpect.EOF = EOFError
        mock_pexpect.TIMEOUT = TimeoutError
        mock_child = MockPexpect([
            # 启动
            (0, "Welcome to Claude Code"),
            # 输入提示
            (0, ("Claude 正在思考...", "╭──────────╮\n│ > │\n╰──────────╯")),
            # 确认请求
            (1, ("这是一个示例输出", "是否继续? [y/n]")),
            # 处理继续
            (2, ("正在生成代码...", "Press Enter to continue")),
            # 结束
            (6, EOFError)
        ])
        mock_pexpect.spawn.return_value = mock_child
        
        # 创建桥接器和LLM桥接
        llm_bridge = LLMBridge()
        bridge = ClaudeBridge(llm_bridge=llm_bridge)
        
        # 运行会话
        interactions = bridge.run_session("测试提示")
        
        # 检查交互记录
        self.assertGreater(len(interactions), 0)
        self.assertEqual(interactions[0]["event"], "session_start")
        self.assertEqual(interactions[1]["role"], "user")
        self.assertEqual(interactions[1]["content"], "测试提示")
        
        # 检查Claude响应和LLM决策
        has_claude_response = False
        has_llm_decision = False
        
        for item in interactions:
            if item.get("role") == "claude":
                has_claude_response = True
            if item.get("role") == "llm":
                has_llm_decision = True
                
        self.assertTrue(has_claude_response)
        self.assertTrue(has_llm_decision)
        
    @patch('claude_llm_bridge_rich.pexpect')
    def test_close(self, mock_pexpect):
        """测试关闭进程"""
        # 设置mock
        mock_pexpect.EOF = EOFError
        mock_child = MockPexpect([])
        
        # 创建桥接器
        bridge = ClaudeBridge()
        bridge.child = mock_child
        
        # 测试关闭
        bridge.close()
        self.assertFalse(mock_child.isalive())
        self.assertEqual(mock_child.mock_logs[-1]["event"], "close")

if __name__ == "__main__":
    unittest.main()