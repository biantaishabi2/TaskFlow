"""
任务分析器模块

提供分析LLM响应，判断任务是否完成的工具。
主要用于决定是否需要继续与Claude进行交互。
"""

from abc import ABC, abstractmethod
from typing import List, Tuple, Dict, Any, Optional

class BaseTaskAnalyzer(ABC):
    """任务分析器抽象基类"""
    
    @abstractmethod
    def analyze(self, 
                conversation_history: List[Tuple[str, str]], 
                last_response: str) -> str:
        """分析任务是否完成
        
        Args:
            conversation_history: 对话历史记录，每项为(问题, 回答)对
            last_response: 最新的回答
            
        Returns:
            str: 任务状态，可能的值:
                - "COMPLETED": 任务已完成，不需要继续对话
                - "NEEDS_MORE_INFO": 需要更多用户信息才能继续
                - "CONTINUE": 任务进行中，需要进一步交互
        """
        pass


class RuleBasedAnalyzer(BaseTaskAnalyzer):
    """基于规则的任务分析器
    
    使用简单的启发式规则判断任务是否完成。
    """
    
    def __init__(self):
        # 完成指示词
        self.completion_indicators = [
            "希望这对你有帮助",
            "希望这解答了你的问题",
            "如有其他问题",
            "这解决了你的问题吗",
            "有任何问题都可以继续提问",
            "如果还有其他需求",
            "祝你好运",
            "希望我的回答对你有所帮助",
            "就是这样",
            "总结一下",
            "总而言之"
        ]
        
        # 需要更多信息的指示词
        self.needs_info_indicators = [
            "你能提供更多信息吗",
            "我需要更多细节",
            "请告诉我更多关于",
            "你能澄清一下",
            "请问你想要",
            "你能具体说明",
            "需要你进一步说明",
            "请提供",
            "?",
            "？"
        ]
    
    def analyze(self, conversation_history: List[Tuple[str, str]], last_response: str) -> str:
        """使用规则判断任务状态"""
        
        # 任务刚刚开始
        if len(conversation_history) <= 1:
            return "CONTINUE"
            
        # 检查是否包含完成指示词
        for indicator in self.completion_indicators:
            if indicator in last_response:
                return "COMPLETED"
                
        # 检查是否需要更多信息
        for indicator in self.needs_info_indicators:
            if indicator in last_response:
                return "NEEDS_MORE_INFO"
                
        # 默认继续
        return "CONTINUE"


class LLMTaskAnalyzer(BaseTaskAnalyzer):
    """基于LLM的任务分析器
    
    使用另一个LLM来分析任务是否完成。
    
    Args:
        llm_service: LLM服务实例，用于调用LLM
    """
    
    def __init__(self, llm_service):
        self.llm_service = llm_service
        
    async def analyze(self, conversation_history: List[Tuple[str, str]], last_response: str) -> str:
        """使用LLM判断任务是否完成"""
        
        prompt = self._build_analyzer_prompt(conversation_history, last_response)
        
        # 构建请求对象
        request = type('Request', (), {})()
        request.messages = [type('Message', (), {'content': prompt})]
        
        # 调用LLM
        result = await self.llm_service.process_chat_request(request)
        
        # 解析结果
        raw_response = result["raw_response"]
        return self._parse_analyzer_response(raw_response)
        
    def _build_analyzer_prompt(self, conversation_history, last_response):
        """构建分析提示"""
        
        # 获取原始请求
        original_request = conversation_history[0][0] if conversation_history else "无"
        
        # 构建对话历史摘要
        history_summary = "\n".join([
            f"用户: {q}\nAI: {a[:100]}..." 
            for q, a in conversation_history[:-1]
        ]) if len(conversation_history) > 1 else "无之前对话"
        
        return f"""
        作为对话分析专家，请判断以下AI回复是否完成了用户的任务或问题。
        
        原始请求: 
        {original_request}
        
        对话历史摘要:
        {history_summary}
        
        最新AI回复:
        {last_response}
        
        请分析AI回复是否:
        1. 完全回答了用户问题并完成了任务
        2. 正在询问更多信息以便继续
        3. 已经开始回答但尚未完成，需要继续
        
        请只返回以下状态之一:
        - COMPLETED: 任务已完成，不需要继续对话
        - NEEDS_MORE_INFO: 需要用户提供更多信息
        - CONTINUE: 任务进行中，需要继续
        """
        
    def _parse_analyzer_response(self, response):
        """解析分析器响应"""
        valid_states = {"COMPLETED", "NEEDS_MORE_INFO", "CONTINUE"}
        
        # 尝试直接匹配
        for state in valid_states:
            if state in response:
                return state
        
        # 如果没有直接匹配，尝试判断
        if "完成" in response or "已完成" in response or "已解决" in response:
            return "COMPLETED"
        elif "需要更多" in response or "需要用户" in response or "需要提供" in response:
            return "NEEDS_MORE_INFO"
        else:
            # 默认继续
            return "CONTINUE"


def get_default_analyzer() -> BaseTaskAnalyzer:
    """获取默认分析器(规则分析器)"""
    return RuleBasedAnalyzer()