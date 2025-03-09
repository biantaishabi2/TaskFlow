from typing import Dict, Any, Optional, List, AsyncGenerator
import asyncio
from abc import ABC, abstractmethod

class BaseLLMAdapter(ABC):
    """LLM服务适配器基类"""
    
    @abstractmethod
    async def generate(self, messages: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """生成回复
        
        Args:
            messages: 消息列表
            **kwargs: 其他参数
            
        Returns:
            生成的回复
        """
        pass
    
    @abstractmethod
    async def generate_stream(self, messages: List[Dict[str, Any]], **kwargs) -> AsyncGenerator[Dict[str, Any], None]:
        """生成流式回复
        
        Args:
            messages: 消息列表
            **kwargs: 其他参数
            
        Yields:
            生成的回复片段
        """
        pass

class ClaudeLLMAdapter(BaseLLMAdapter):
    """Claude LLM服务适配器"""
    
    def __init__(self, model_name: str = "claude-3-5-sonnet", **kwargs):
        """初始化Claude适配器
        
        Args:
            model_name: 模型名称
            **kwargs: 其他参数
        """
        self.model_name = model_name
        self.config = kwargs
    
    async def generate(self, messages: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """使用Claude生成回复
        
        Args:
            messages: 消息列表
            **kwargs: 其他参数
            
        Returns:
            生成的回复
        """
        # 实际实现中，这里需要调用Claude API
        # 简化实现
        return {"content": "这是Claude生成的回复", "role": "assistant"}
    
    async def generate_stream(self, messages: List[Dict[str, Any]], **kwargs) -> AsyncGenerator[Dict[str, Any], None]:
        """使用Claude生成流式回复
        
        Args:
            messages: 消息列表
            **kwargs: 其他参数
            
        Yields:
            生成的回复片段
        """
        # 简化实现
        chunks = ["这是", "Claude", "生成的", "流式", "回复"]
        for chunk in chunks:
            yield {"content": chunk, "role": "assistant"}
            await asyncio.sleep(0.1)

# 根据需要添加其他LLM适配器