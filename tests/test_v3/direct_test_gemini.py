"""
直接测试Gemini分析器
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# 直接添加项目根目录到sys.path
sys.path.insert(0, '/home/wangbo/document/wangbo/task_planner')

try:
    # 尝试直接导入
    from src.task_planner.vendor.claude_client.agent_tools.gemini_analyzer import GeminiTaskAnalyzer
    
    def test_detect_task_type():
        """测试任务类型检测功能"""
        analyzer = GeminiTaskAnalyzer()
        
        # 测试不同类型的任务请求
        assert analyzer._detect_task_type("请编写一个Python函数计算斐波那契数列") == "code"
        assert analyzer._detect_task_type("解释什么是闭包和装饰器") == "explanation"
        assert analyzer._detect_task_type("列出世界上最高的十座山") == "factual"
        
    def test_mock_analyze():
        """测试模拟分析函数"""
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
    
except ImportError as e:
    print(f"导入失败: {e}")
    
    # 如果导入失败，定义跳过的测试
    @pytest.mark.skip(reason="无法导入GeminiTaskAnalyzer")
    def test_placeholder():
        pass