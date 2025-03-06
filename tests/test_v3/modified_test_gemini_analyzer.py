"""
Tests for the GeminiTaskAnalyzer with task definition support (simplified version)
"""

import pytest
from unittest.mock import patch, MagicMock

def test_detect_task_type():
    """测试任务类型检测功能"""
    try:
        from task_planner.vendor.claude_client.agent_tools.gemini_analyzer import GeminiTaskAnalyzer
    except ImportError:
        pytest.skip("GeminiTaskAnalyzer不可用")
    
    # 创建分析器实例
    analyzer = GeminiTaskAnalyzer()
    
    # 测试不同类型的任务请求
    assert analyzer._detect_task_type("请编写一个Python函数计算斐波那契数列") in ["code"]
    assert analyzer._detect_task_type("解释什么是闭包和装饰器") in ["explanation"]
    assert analyzer._detect_task_type("创建一个数据分析报告") in ["creative"]

def test_mock_analyze():
    """测试模拟分析函数"""
    try:
        from task_planner.vendor.claude_client.agent_tools.gemini_analyzer import GeminiTaskAnalyzer
    except ImportError:
        pytest.skip("GeminiTaskAnalyzer不可用")
    
    # 创建分析器实例
    analyzer = GeminiTaskAnalyzer()
    
    # 测试小的响应
    short_response = "有什么问题吗？"
    conversation = [("你好", "我是Claude")]
    result = analyzer._mock_analyze(conversation, short_response)
    assert result == "NEEDS_MORE_INFO"
    
    # 测试包含完成指示词的响应
    complete_response = "以上就是完整解答。希望这对你有帮助。"
    result = analyzer._mock_analyze(conversation, complete_response)
    assert result == "COMPLETED"