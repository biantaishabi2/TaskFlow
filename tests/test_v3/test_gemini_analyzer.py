"""
Tests for the GeminiTaskAnalyzer with task definition support
"""

import pytest
from unittest.mock import patch, MagicMock
import os
import tempfile
import json

def test_gemini_analyzer_with_task_definition(mock_gemini):
    """测试Gemini分析器在有任务定义时的行为"""
    try:
        from task_planner.vendor.claude_client.agent_tools.gemini_analyzer import GeminiTaskAnalyzer
    except ImportError:
        pytest.skip("GeminiTaskAnalyzer不可用")
    
    # 创建分析器实例
    analyzer = GeminiTaskAnalyzer()
    
    # 创建模拟任务定义
    task_definition = {
        "id": "test_task_1",
        "name": "测试任务",
        "description": "这是一个测试任务",
        "output_files": {
            "main_result": "/tmp/test_result.json"
        },
        "success_criteria": ["创建输出文件"]
    }
    
    # 设置任务定义
    analyzer.task_definition = task_definition
    
    # 构建测试对话历史
    conversation_history = [
        ("请创建一个JSON文件", "我将为您创建JSON文件")
    ]
    
    # 模拟响应
    last_response = "我已经创建了文件: /tmp/test_result.json，内容为{...}"
    
    # 分析结果
    result = analyzer.analyze(conversation_history, last_response)
    
    # 验证结果
    assert result in ["COMPLETED", "NEEDS_MORE_INFO", "CONTINUE"]
    assert result == "COMPLETED"  # 因为我们的mock返回COMPLETED

def test_gemini_analyzer_build_prompt(mock_gemini):
    """测试带有任务定义的提示词构建"""
    try:
        from task_planner.vendor.claude_client.agent_tools.gemini_analyzer import GeminiTaskAnalyzer
    except ImportError:
        pytest.skip("GeminiTaskAnalyzer不可用")
    
    # 创建分析器实例
    analyzer = GeminiTaskAnalyzer()
    
    # 创建模拟任务定义
    task_definition = {
        "id": "test_build_prompt",
        "name": "测试提示构建",
        "description": "测试_build_analyzer_prompt方法",
        "output_files": {
            "test_file": "/tmp/test_file.txt"
        },
        "success_criteria": ["创建测试文件", "文件内容符合要求"]
    }
    
    # 设置任务定义
    analyzer.task_definition = task_definition
    
    # 构建测试对话
    conversation_history = [("创建一个测试文件", "好的，我将创建测试文件")]
    last_response = "我已经创建了测试文件: /tmp/test_file.txt"
    
    # 获取提示词
    prompt = analyzer._build_analyzer_prompt(conversation_history, last_response)
    
    # 验证提示词中包含任务定义相关信息
    assert "任务ID: test_build_prompt" in prompt
    assert "任务名称: 测试提示构建" in prompt
    assert "任务描述: 测试_build_analyzer_prompt方法" in prompt
    assert "test_file: /tmp/test_file.txt" in prompt
    assert "创建测试文件" in prompt
    assert "文件内容符合要求" in prompt

def test_detect_task_type():
    """测试任务类型检测功能"""
    try:
        from task_planner.vendor.claude_client.agent_tools.gemini_analyzer import GeminiTaskAnalyzer
    except ImportError:
        pytest.skip("GeminiTaskAnalyzer不可用")
    
    analyzer = GeminiTaskAnalyzer()
    
    # 测试不同类型的任务请求
    assert analyzer._detect_task_type("请编写一个Python函数计算斐波那契数列") in ["编码任务", "代码任务"]
    assert analyzer._detect_task_type("解释什么是闭包和装饰器") in ["知识解释任务", "教育任务"]
    assert analyzer._detect_task_type("创建一个数据分析报告") in ["创意任务", "分析任务"]

def test_gemini_analyzer_without_task_definition(mock_gemini):
    """测试没有任务定义时的行为"""
    try:
        from task_planner.vendor.claude_client.agent_tools.gemini_analyzer import GeminiTaskAnalyzer
    except ImportError:
        pytest.skip("GeminiTaskAnalyzer不可用")
    
    # 创建分析器实例
    analyzer = GeminiTaskAnalyzer()
    
    # 未设置任务定义
    # 构建测试对话历史
    conversation_history = [
        ("请创建一个JSON文件", "我将为您创建JSON文件")
    ]
    
    # 模拟响应
    last_response = "我已经创建了文件，内容为{...}"
    
    # 分析结果
    result = analyzer.analyze(conversation_history, last_response)
    
    # 验证结果
    assert result in ["COMPLETED", "NEEDS_MORE_INFO", "CONTINUE"]

def test_gemini_unavailable_fallback():
    """测试Gemini不可用时的降级处理"""
    with patch('task_planner.vendor.claude_client.agent_tools.gemini_analyzer.genai', None):
        try:
            from task_planner.vendor.claude_client.agent_tools.gemini_analyzer import GeminiTaskAnalyzer
        except ImportError:
            pytest.skip("GeminiTaskAnalyzer不可用")
        
        # 创建分析器实例
        analyzer = GeminiTaskAnalyzer()
        
        # 构建测试对话历史
        conversation_history = [
            ("请创建一个JSON文件", "我将为您创建JSON文件")
        ]
        
        # 模拟响应
        last_response = "我已经创建了文件，内容为{...}"
        
        # 分析结果
        result = analyzer.analyze(conversation_history, last_response)
        
        # 验证结果 - 应该有一个默认值
        assert result in ["COMPLETED", "NEEDS_MORE_INFO", "CONTINUE"]