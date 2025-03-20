"""
LLM响应代理简单测试示例
"""
from llm_response_agent import LLMResponseAgent, ResponseType
from agent_tools.llm_service import LLMService
from llm_response_agent import call_llm
import litellm
import asyncio

# 简单测试函数
def test_agent():
    # 角色配置
    roles = {"default": {"system_prompt": "你是判断型助手"}}
    
    # 创建LLM服务和响应代理
    llm_service = LLMService(call_llm=call_llm, roles=roles)
    response_agent = LLMResponseAgent(llm_service)
    
    # 测试聊天记录
    chat_history = [
        {"sender": "自动用户", "content": "我想创建一个Python程序来分析数据"},
        {"sender": "程序员助手", "content": "好的，这是一个简单的分析程序:\n```python\nimport pandas as pd\n...\n```"},
        {"sender": "自动用户", "content": "请帮我运行这段代码"}
    ]
    
    # 任务描述
    task_description = "创建并运行数据分析程序"
    
    # 直接使用get_response方法
    response = response_agent.get_response(chat_history, task_description)
    
    # 输出结果
    print(f"响应类型: {response['type']}")
    print(f"消息: {response['message']}")
    print(f"理由: {response['reasoning']}")

if __name__ == "__main__":
    test_agent() 