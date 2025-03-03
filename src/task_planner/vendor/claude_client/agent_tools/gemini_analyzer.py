"""
Gemini任务分析器

使用Google的Gemini 2.0 Flash模型分析对话状态，
判断任务是否已完成或需要继续。
"""

import os
import json
import asyncio
import google.generativeai as genai
from typing import List, Tuple, Dict, Any, Optional

from .task_analyzer import BaseTaskAnalyzer

class GeminiTaskAnalyzer(BaseTaskAnalyzer):
    """基于Google Gemini模型的任务分析器
    
    使用Gemini 2.0 Flash模型来分析对话状态，判断任务是否已完成。
    
    Args:
        api_key (str, optional): Gemini API密钥
        model_name (str, optional): Gemini模型名称，默认为'gemini-2.0-flash'
    """
    
    def __init__(self, api_key=None, model_name='gemini-2.0-flash'):
        """初始化Gemini任务分析器"""
        # 获取API密钥（优先使用参数传入的值，其次使用环境变量）
        self.api_key = api_key or os.environ.get('GEMINI_API_KEY')
        if not self.api_key:
            print("警告: 未提供Gemini API Key，使用伪判断功能")
            self.use_mock = True
        else:
            self.use_mock = False
            # 配置Gemini API
            genai.configure(api_key=self.api_key)
            
        self.model_name = model_name
        
        # 设置模型参数
        self.generation_config = {
            "temperature": 0,  # 无创造性，确保一致性
            "top_p": 0.95,
            "top_k": 0,
            "max_output_tokens": 100,  # 限制输出长度，我们只需要简短判断
        }
        
        # 为不同类型的请求设置不同的权重
        self.task_weights = {
            "code": 1.2,       # 代码请求通常需要更多交互
            "explanation": 1.0, # 解释性请求标准权重
            "factual": 0.8,    # 事实性请求更容易一次性完成
            "creative": 1.5,   # 创意性请求通常需要更多交互
        }
    
    def analyze(self, 
                conversation_history: List[Tuple[str, str]], 
                last_response: str) -> str:
        """同步分析任务是否完成（使用asyncio运行异步方法）"""
        # 如果没有API密钥，使用伪判断逻辑
        if self.use_mock:
            return self._mock_analyze(conversation_history, last_response)
            
        # 使用asyncio创建一个事件循环来运行异步方法
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                self._async_analyze(conversation_history, last_response)
            )
            return result
        finally:
            loop.close()
    
    async def _async_analyze(self, 
                           conversation_history: List[Tuple[str, str]], 
                           last_response: str) -> str:
        """使用Gemini模型分析任务是否完成"""
        # 构建分析提示
        prompt = self._build_analyzer_prompt(conversation_history, last_response)
        
        try:
            # 获取模型
            model = genai.GenerativeModel(model_name=self.model_name,
                                         generation_config=self.generation_config)
            
            # 发送请求到Gemini
            response = await asyncio.to_thread(
                model.generate_content, prompt
            )
            
            # 解析返回结果
            result = response.text.strip()
            
            # 解析结果
            return self._parse_response(result)
            
        except Exception as e:
            print(f"Gemini API调用出错: {str(e)}")
            # 出错时使用保守策略，认为任务未完成
            return "CONTINUE"
    
    def _build_analyzer_prompt(self, 
                              conversation_history: List[Tuple[str, str]], 
                              last_response: str) -> str:
        """构建分析提示"""
        # 获取原始请求
        original_request = conversation_history[0][0] if conversation_history else "无"
        
        # 构建对话历史摘要
        history_summary = "\n".join([
            f"用户: {q}\nAI: {a[:100]}..." 
            for q, a in conversation_history[:-1]
        ]) if len(conversation_history) > 1 else "无之前对话"
        
        # 检测任务类型
        task_type = self._detect_task_type(original_request)
        
        # 创建提示
        prompt = f"""
        分析下面AI回复是否完成了用户的请求。

        原始请求: {original_request}
        
        任务类型: {task_type}
        
        对话历史摘要:
        {history_summary}
        
        最新AI回复:
        {last_response[:500]}...
        
        根据以下标准分析AI回复:
        1. 回复是否直接且完整地回答了用户的请求
        2. 回复是否包含所有必要的细节和信息
        3. 回复是否存在需要继续解释或展开的内容
        4. 回复是否提出了需要用户提供更多信息的问题
        
        只返回以下三种状态之一（不要解释你的选择）:
        COMPLETED - 任务已经完成，无需进一步交互
        NEEDS_MORE_INFO - 需要用户提供更多信息才能继续
        CONTINUE - 任务进行中但尚未完成，AI应该继续
        """
        
        return prompt
        
    def _parse_response(self, response: str) -> str:
        """解析Gemini的响应"""
        # 尝试直接匹配状态关键词
        if "COMPLETED" in response:
            return "COMPLETED"
        elif "NEEDS_MORE_INFO" in response:
            return "NEEDS_MORE_INFO"
        elif "CONTINUE" in response:
            return "CONTINUE"
            
        # 如果没有明确匹配，分析响应文本
        response_lower = response.lower()
        if "完成" in response_lower or "完整" in response_lower or "足够" in response_lower:
            return "COMPLETED"
        elif "更多信息" in response_lower or "提供" in response_lower or "问题" in response_lower:
            return "NEEDS_MORE_INFO"
        else:
            # 默认继续
            return "CONTINUE"
            
    def _detect_task_type(self, request: str) -> str:
        """检测任务类型"""
        request_lower = request.lower()
        
        # 代码相关任务
        if any(kw in request_lower for kw in ["代码", "编程", "程序", "函数", "脚本", "code", "programming"]):
            return "code"
            
        # 解释性任务
        if any(kw in request_lower for kw in ["解释", "说明", "介绍", "描述", "explain", "describe", "introduction"]):
            return "explanation"
            
        # 事实性任务
        if any(kw in request_lower for kw in ["什么是", "定义", "列出", "when", "where", "what", "who", "list"]):
            return "factual"
            
        # 创意性任务
        if any(kw in request_lower for kw in ["创意", "创作", "故事", "写一个", "想象", "creative", "story", "imagine"]):
            return "creative"
            
        # 默认为解释性任务
        return "explanation"
        
    def _mock_analyze(self, 
                     conversation_history: List[Tuple[str, str]], 
                     last_response: str) -> str:
        """没有API密钥时的伪判断逻辑"""
        # 基本规则判断
        
        # 1. 检查最新回复的长度
        if len(last_response) < 100:
            # 短回复可能是在询问更多信息
            return "NEEDS_MORE_INFO"
            
        # 2. 检查是否包含常见的完成指示词
        completion_indicators = [
            "希望这对你有帮助",
            "希望这解答了你的问题",
            "如有其他问题",
            "希望对你有所帮助",
            "总结一下",
            "总而言之"
        ]
        
        for indicator in completion_indicators:
            if indicator in last_response:
                return "COMPLETED"
                
        # 3. 检查是否列表回复（通常是完整回答）
        list_pattern_count = last_response.count("- ")
        if list_pattern_count > 3:
            # 包含多个列表项的回复通常是完整的
            return "COMPLETED"
            
        # 4. 检查请求类型
        request = conversation_history[0][0] if conversation_history else ""
        task_type = self._detect_task_type(request)
        
        # 5. 根据任务类型和回复长度评估完成状态
        if task_type == "factual" and len(last_response) > 300:
            return "COMPLETED"
        elif task_type == "explanation" and len(last_response) > 500:
            return "COMPLETED"
        elif task_type == "code" and "```" in last_response and len(last_response) > 600:
            return "COMPLETED"
            
        # 默认继续
        return "CONTINUE"