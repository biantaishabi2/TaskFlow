"""
LLM驱动的自动响应代理

通过LLM判断对话状态，确定是否执行工具调用、命令执行、
任务完成或生成文本回复。

使用示例:
```python
from agent_tools.llm_response_agent import create_llm_response_agent
from agent_tools.llm_service import LLMService  # 假设已存在的LLM服务

# 初始化LLM服务和响应代理
llm_service = LLMService(call_llm=your_llm_function, roles=your_roles)
agent = create_llm_response_agent(llm_service)

# 准备最近的聊天记录
chat_history = [
    {"sender": "自动用户", "content": "我想创建一个Python程序来分析数据"},
    {"sender": "程序员助手", "content": "好的，我可以帮你写一个数据分析程序"},
    {"sender": "程序员助手", "content": "以下是代码:\n```python\nimport pandas as pd\n# 数据分析代码\n```"},
    {"sender": "自动用户", "content": "请帮我运行这段代码"}
]

# 设置任务描述
task_description = "创建并运行一个数据分析程序"

# 获取LLM判断的响应
response = agent.get_response(chat_history, task_description)

# 处理响应
if response["type"] == "TOOL_APPROVED":
    print("执行工具调用")
    # 这里执行工具调用的代码
elif response["type"] == "TASK_COMPLETED":
    print("任务已完成，结束对话")
else:
    print(f"响应消息: {response['message']}")
"""

import json
import logging
from typing import List, Dict, Any
import litellm

# 配置日志
logger = logging.getLogger(__name__)

class ResponseType:
    """响应类型常量"""
    TOOL_APPROVED = "TOOL_APPROVED"       # 工具/命令执行批准
    TOOL_REJECTED = "TOOL_REJECTED"       # 工具/命令执行拒绝
    TASK_COMPLETED = "TASK_COMPLETED"     # 任务已完成
    TEXT_RESPONSE = "TEXT_RESPONSE"       # 普通文本回复

class LLMResponseAgent:
    """LLM驱动的自动响应代理
    
    使用LLM判断对话状态，生成适当的响应。
    """
    
    def __init__(self):
        """初始化LLM响应代理"""
        pass
    
    def get_response(self, 
                    chat_history: List[Dict[str, str]], 
                    task_description: str = None) -> Dict[str, Any]:
        """获取LLM判断的响应
        
        Args:
            chat_history: 最近的聊天记录
            task_description: 任务描述，如果不提供则从聊天历史中提取
            
        Returns:
            包含响应类型、消息和判断理由的字典
        """
        # 如果没有提供任务描述，尝试从聊天历史中提取
        if not task_description and chat_history:
            task_description = chat_history[0].get("content", "") if chat_history else ""
        
        # 构建提示词
        prompt = self._build_prompt(chat_history, task_description)
        
        # 直接同步调用 LLM
        try:
            response = litellm.completion(
                model="openrouter/google/gemini-2.0-flash-lite-001",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=100
            )
            llm_response = response.choices[0].message.content
            
            # 解析LLM响应
            parsed_response = self._parse_llm_response(llm_response)
            
            return parsed_response
            
        except Exception as e:
            logger.error(f"LLM调用失败: {str(e)}")
            # 返回默认响应
            return {
                "type": ResponseType.TEXT_RESPONSE,
                "message": "继续对话",
                "reasoning": "LLM调用失败，默认继续对话"
            }
    
    def _build_prompt(self, chat_history: List[Dict[str, str]], task_description: str) -> str:
        """构建提示词"""
        # 将聊天记录格式化为字符串
        chat_history_str = ""
        for i, msg in enumerate(chat_history):
            sender = msg.get("sender", "未知")
            content = msg.get("content", "")
            chat_history_str += f"{i+1}. [{sender}]: {content}\n\n"
        
        # 构建完整提示词
        prompt = f"""作为一个自动判断的用户代理，你的任务是分析以下对话内容中助手的行为，并根据当前上下文判断应该做出什么响应。

任务描述: {task_description}

最近的对话历史:
{chat_history_str}

请判断当前应该采取的行动类型，并给出结构化的JSON响应。响应类型包括:

1. TOOL_APPROVED: 助手请求执行工具或命令，你同意执行
2. TOOL_REJECTED: 助手请求执行工具或命令，但你拒绝执行
3. TASK_COMPLETED: 任务已经完成，对话可以结束
4. TEXT_RESPONSE: 普通文本回复，继续对话

明确指示：当助手提供了工具调用的建议（具体的格式下面有），或当助手提供代码并要求执行、保存或运行时，如果没有rm命令的话，你应该总是选择TOOL_APPROVED。如果有rm命令你应该拒绝，告诉他可以mv这个文件，而不是使用危险的删除。

具体判断标准：
- 如果消息中包含"suggested tool call"或类似结构化工具调用格式，请选择TOOL_APPROVED
- 如果助手提供了Python代码块(```python)，请选择TOOL_APPROVED
- 如果助手提供了Shell命令(```sh)，请选择TOOL_APPROVED
- 如果助手使用了诸如"请执行"、"请运行"、"请保存"这类指令，请选择TOOL_APPROVED
- 如果助手提供了操作步骤并期望你执行，请选择TOOL_APPROVED
- 如果消息中包含诸如"function_call"、"tool_call"或类似格式的函数调用建议，请选择TOOL_APPROVED

工具调用格式示例（以下形式出现时都应选择TOOL_APPROVED）：
```
suggested tool call: search_web(query="Python数据分析库")
```
或
```
function call: execute_code(language="python", code="print('Hello world')")
```

在判断出现了工具调用或者代码执行的时候，你同意的时候总是要选择TOOL_APPROVED，永远不要在text response中回答同意，请继续。（这样会拒绝工具的执行）
只有在以下情况才返回 TASK_COMPLETED：
1. 工具调用已经成功执行完毕，你不能在助手提出要求之后不帮他执行就返回TASK_COMPLETED
2. 助手明确表示任务已完成，并且他还要实际确认这一点，而不是在执行之前就宣称任务已经完成
3. 没有更多需要执行的操作

你的响应必须是一个符合以下格式的JSON对象:
{{
  "action_type": "TOOL_APPROVED|TOOL_REJECTED|TASK_COMPLETED|TEXT_RESPONSE",
  "message": "简短说明或回复内容",
  "reasoning": "你的判断理由"
}}

注意:
- 如果同意执行工具或命令(TOOL_APPROVED)，message字段应为空字符串
- 仅在任务已明确完成时才返回TASK_COMPLETED
- 请基于整个对话历史和任务描述做出判断

请直接返回JSON对象，不要有其他文字。
"""
        return prompt
    
    def _parse_llm_response(self, llm_response: str) -> Dict[str, Any]:
        """解析LLM的响应
        
        Args:
            llm_response: LLM返回的文本
            
        Returns:
            解析后的响应字典
        """
        try:
            # 尝试提取JSON部分
            json_str = llm_response
            
            # 如果响应包含markdown格式的代码块，提取其中的JSON
            if "```json" in llm_response:
                json_str = llm_response.split("```json")[1].split("```")[0].strip()
            elif "```" in llm_response:
                json_str = llm_response.split("```")[1].split("```")[0].strip()
            
            # 解析JSON
            response_data = json.loads(json_str)
            
            # 转换为标准格式
            return {
                "type": response_data.get("action_type", ResponseType.TEXT_RESPONSE),
                "message": response_data.get("message", ""),
                "reasoning": response_data.get("reasoning", "")
            }
        except Exception as e:
            logger.error(f"解析LLM响应时出错: {str(e)}")
            logger.error(f"原始响应: {llm_response}")
            
            # 返回默认响应
            return {
                "type": ResponseType.TEXT_RESPONSE,
                "message": "继续对话",
                "reasoning": "解析LLM响应失败，默认继续对话"
            } 