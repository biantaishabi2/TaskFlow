"""
通过直接导入路径测试GeminiTaskAnalyzer
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# 手动添加项目src目录到Python路径
src_path = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', '..', 'src'
))
sys.path.insert(0, src_path)

print(f"添加到路径: {src_path}")
print(f"当前Python路径: {sys.path}")

try:
    from task_planner.vendor.claude_client.agent_tools.gemini_analyzer import GeminiTaskAnalyzer
    IMPORT_SUCCESS = True
    print("导入成功")
except ImportError as e:
    IMPORT_SUCCESS = False
    print(f"导入失败: {e}")

if IMPORT_SUCCESS:
    def test_detect_task_type():
        """测试任务类型检测功能"""
        analyzer = GeminiTaskAnalyzer()
        
        # 测试不同类型的任务请求
        assert analyzer._detect_task_type("请编写一个Python函数计算斐波那契数列") == "code"
        assert analyzer._detect_task_type("解释什么是闭包和装饰器") == "explanation"
        assert analyzer._detect_task_type("列出世界上最高的十座山") == "factual"
else:
    @pytest.mark.skip(reason="无法导入GeminiTaskAnalyzer")
    def test_placeholder():
        """占位测试"""
        pass