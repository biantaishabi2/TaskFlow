"""
自动跟进问题生成器

根据对话状态和历史自动生成适当的跟进问题，
用于维持与Claude的交互直到任务完成。
"""

from typing import List, Tuple, Dict, Any, Optional

class FollowupGenerator:
    """跟进问题生成器
    
    根据对话状态和内容生成后续问题以继续任务。
    """
    
    def __init__(self):
        # 不同状态的默认跟进问题
        self.default_followups = {
            "NEEDS_MORE_INFO": "我需要更多关于您的问题的信息。请提供更多详细内容，以便我能更好地帮助您。",
            "CONTINUE": "请继续完成您刚才的解释。"
        }
        
        # 特定场景的跟进提示
        self.context_followups = {
            "code": "继续提供剩余代码，请确保解释完整的解决方案。",
            "explanation": "请继续您的解释，确保覆盖之前提到的所有要点。",
            "comparison": "请继续比较这些选项的优缺点。",
            "example": "请继续提供具体的使用示例。",
            "implementation": "请继续说明实现细节和步骤。"
        }
        
    def generate_followup(self, 
                          task_status: str, 
                          conversation_history: List[Tuple[str, str]],
                          last_response: str) -> Optional[str]:
        """根据当前任务状态和对话历史生成跟进问题
        
        Args:
            task_status: 由任务分析器确定的状态
            conversation_history: 对话历史记录
            last_response: Claude的最新回复
            
        Returns:
            生成的跟进问题，如果不需要跟进则返回None
        """
        # 如果任务已完成，不需要跟进
        if task_status == "COMPLETED":
            return None
            
        # 尝试根据上下文生成更具体的跟进问题
        if task_status == "CONTINUE":
            # 检查是否有特定的上下文线索
            context_type = self._detect_context_type(last_response)
            if context_type and context_type in self.context_followups:
                return self.context_followups[context_type]
        
        # 如果没有特定上下文，使用默认跟进
        return self.default_followups.get(task_status)
    
    def _detect_context_type(self, response: str) -> Optional[str]:
        """检测回复中的上下文类型"""
        
        # 代码相关
        if "```" in response or "代码" in response or "function" in response or "class" in response:
            return "code"
            
        # 解释说明相关
        if "解释" in response or "说明" in response or "首先" in response:
            return "explanation"
            
        # 比较相关
        if "比较" in response or "优点" in response or "缺点" in response or "区别" in response:
            return "comparison"
            
        # 示例相关
        if "例如" in response or "示例" in response or "案例" in response:
            return "example"
            
        # 实现相关
        if "实现" in response or "步骤" in response or "流程" in response:
            return "implementation"
            
        # 无法确定具体类型
        return None
        
        
class LLMFollowupGenerator(FollowupGenerator):
    """基于LLM的跟进问题生成器
    
    使用LLM生成更自然和上下文相关的跟进问题。
    
    Args:
        llm_service: LLM服务实例，用于调用LLM
    """
    
    def __init__(self, llm_service):
        super().__init__()
        self.llm_service = llm_service
        
    async def generate_followup(self, 
                               task_status: str, 
                               conversation_history: List[Tuple[str, str]],
                               last_response: str) -> Optional[str]:
        """使用LLM生成跟进问题"""
        
        # 如果任务已完成，不需要跟进
        if task_status == "COMPLETED":
            return None
            
        # 使用LLM生成跟进问题
        prompt = self._build_generator_prompt(
            task_status, conversation_history, last_response)
            
        # 构建请求对象
        request = type('Request', (), {})()
        request.messages = [type('Message', (), {'content': prompt})]
        
        # 调用LLM
        result = await self.llm_service.process_chat_request(request)
        
        # 获取生成的跟进问题
        followup = result["raw_response"].strip()
        
        return followup
        
    def _build_generator_prompt(self, task_status, conversation_history, last_response):
        """构建生成器提示"""
        
        # 获取原始请求
        original_request = conversation_history[0][0] if conversation_history else "无"
        
        # 构建简洁的对话历史
        history_str = "\n".join([
            f"用户: {q}\nAI: {a[:100]}..." 
            for q, a in conversation_history[-2:] if len(conversation_history) >= 2
        ])
        
        status_descriptions = {
            "NEEDS_MORE_INFO": "AI需要用户提供更多信息来完成任务。",
            "CONTINUE": "AI已经开始回答，但任务尚未完成，需要继续。"
        }
        
        return f"""
        作为对话助手，请为下列AI回复生成一个简短的跟进问题，以便继续完成用户的任务。
        
        原始请求:
        {original_request}
        
        最近的对话:
        {history_str}
        
        最新AI回复:
        {last_response}
        
        当前状态: {task_status}
        说明: {status_descriptions.get(task_status, "")}
        
        请根据当前状态生成一个自然、有帮助的跟进问题，限制在30字以内。这个问题将自动发送给AI以继续任务。
        如果是NEEDS_MORE_INFO状态，请询问用户提供更多信息。
        如果是CONTINUE状态，请要求AI继续完成未完成的任务。
        不要解释为什么生成这个问题，直接给出问题文本。
        """


def get_default_generator() -> FollowupGenerator:
    """获取默认跟进问题生成器"""
    return FollowupGenerator()