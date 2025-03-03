"""
Agent Tools 包

提供LLM工具调用、响应解析和服务管理的组件集合。
该包从poe_server/core复制而来，经过简化以适应Claude客户端增强需求。

主要组件:
- llm_service: LLM服务统一接口
- parser: LLM响应解析器
- tool_manager: 工具调用管理系统
- tools: 基础工具实现
- task_analyzer: 任务完成状态分析器
- gemini_analyzer: 基于Gemini的任务分析器
- followup_generator: 自动跟进问题生成器
"""

from .llm_service import LLMService
from .parser import ParsedResponse, BaseResponseParser, ApiCallResponseParser, DefaultResponseParser
from .tool_manager import ToolManager
from .tools import BaseTool, ToolCallResult
from .task_analyzer import BaseTaskAnalyzer, RuleBasedAnalyzer, LLMTaskAnalyzer, get_default_analyzer
from .followup_generator import FollowupGenerator, LLMFollowupGenerator, get_default_generator

# 条件导入Gemini分析器，如果导入失败不会中断整个模块加载
try:
    from .gemini_analyzer import GeminiTaskAnalyzer
except ImportError:
    print("注意: 未能加载GeminiTaskAnalyzer (google.generativeai可能未安装)")
    
    # 创建一个占位类，以免导入失败时代码报错
    class GeminiTaskAnalyzer(BaseTaskAnalyzer):
        def __init__(self, *args, **kwargs):
            print("警告: GeminiTaskAnalyzer需要安装google-generativeai包")
            
        def analyze(self, conversation_history, last_response):
            print("警告: GeminiTaskAnalyzer未正确加载，使用默认完成状态")
            return "COMPLETED"