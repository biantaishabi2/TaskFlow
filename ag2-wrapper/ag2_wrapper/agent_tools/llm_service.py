"""
LLM 服务统一接口层
职责：
1. 管理对话上下文和角色配置
2. 执行标准化LLM调用
3. 返回原始响应供后续处理

依赖注入要求：
- call_llm: LLM调用器实现，需实现 async def (prompt, system_prompt, messages, stream) 接口
- roles: 角色配置字典，需包含各角色的系统提示配置
"""
class LLMService:
    def __init__(self, call_llm, roles):  # 核心依赖注入点
        """
        :param call_llm: 必须注入的LLM调用实现
        :param roles: 必须注入的角色配置字典
        """
        self.call_llm = call_llm
        self.roles = roles  # 保留角色配置
        self.current_role = "default"  # 当前角色标识

    async def process_chat_request(self, request):
        # 构建包含系统提示的消息结构
        # 维护对话上下文（当前实现为全量历史）
        # 执行LLM调用并处理响应解析
        # 返回原始响应和结构化响应
        
        # 构建消息列表
        messages = [{
            "role": "system",
            "content": self.roles[self.current_role]["system_prompt"]
        }]
        for msg in request.messages:
            messages.append({"role": "user", "content": msg.content})
        
        llm_response = await self.call_llm(
            prompt=messages[-1]["content"],
            system_prompt=self.roles[self.current_role]["system_prompt"],
            messages=messages,
            stream=False
        )
        
        # 保持两次prompt注入（消息列表+独立参数）确保模型遵循角色设定
        # 使用当前实例的角色名称
        # 直接返回原始响应，解析和工具调用交给专门模块
        return {
            "raw_response": llm_response  # 仅返回原始响应
        }

    # 完全移除与解析/工具相关的方法
