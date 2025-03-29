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
import os
from datetime import datetime
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
        if not chat_history:
            return None

        # --- 直接记录传入的 chat_history ---
        try:
            logger.info("Received chat history:")
            logger.info(json.dumps(chat_history, indent=2, ensure_ascii=False, default=lambda o: f'<object of type {type(o).__name__} not serializable>'))
        except Exception as e:
            logger.error(f"Failed to log chat_history: {e}", exc_info=True)
        # --- 记录结束 ---

        task_description = chat_history[0].get("content", "") if chat_history else ""
        
        # --- 添加日志记录 ---
        logger.info(f"LLMResponseAgent received chat_history: {json.dumps(chat_history, indent=2, ensure_ascii=False, default=lambda o: f'<object of type {type(o).__name__} not serializable>')}")
        # --- 日志记录结束 ---
        
        # 构建提示词
        prompt = self._build_prompt(chat_history, task_description)
        
        # 直接同步调用 LLM
        try:
            response = litellm.completion(
                model="gemini/gemini-2.5-pro-exp-03-25",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=2048
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
    
    def _build_prompt(self, chat_history: List[Dict[str, Any]], task_description: str) -> str:
        """构建提示词 (处理包含 sender_name 的 JSON 消息表示)"""
        chat_history_str = ""
        for i, msg in enumerate(chat_history):
            # 直接使用 "sender_name" (因为 get_human_input 已经处理了)
            sender_name = msg.get("sender_name", "未知")
            
            # 构建一个可序列化的消息表示 (现在 msg 已经是基本类型了)
            serializable_msg = msg # 直接使用传入的 msg 字典
            
            # 将这个字典转换为JSON字符串
            try:
                # 移除 sender_name 键，因为它已经在外面显示了
                msg_to_serialize = serializable_msg.copy()
                msg_to_serialize.pop('sender_name', None) 
                msg_json_str = json.dumps(msg_to_serialize, indent=2, ensure_ascii=False)
            except Exception as e:
                logger.error(f"无法将消息字典序列化为JSON: {serializable_msg}, 错误: {e}")
                msg_json_str = f"{{{{ 'error': '无法序列化消息字典', 'keys': {list(serializable_msg.keys())} }}}}"

            # 格式化输出，将JSON放入代码块
            # 使用三引号来处理多行 f-string
            chat_history_str += f"""{i+1}. 发送者: [{sender_name}]
消息 JSON:
```json
{msg_json_str}
```

"""

        # 构建完整提示词 (提示词主体保持不变)
        prompt = f"""作为一个自动判断的用户代理，你的任务是分析以下对话中 **助手代理** 发送的 **最后一条消息** 的JSON结构和内容，并根据对话历史和任务描述判断应该做出什么响应。

任务描述: {task_description}

最近的对话历史 (每条消息都以JSON对象呈现):
{chat_history_str}

请重点分析 **最后一条来自 [助手代理] 或角色为 [assistant]** 的消息JSON对象。判断当前应该采取的行动类型，并给出结构化的JSON响应。响应类型包括:

1. TOOL_APPROVED: **判断依据 (满足任一即可，除非含危险操作):**
    a) 消息JSON中明确包含 `tool_calls` (一个列表) 或 `function_call` (一个字典) 键。
    b) 消息JSON的 `content` 字段 (如果存在且为字符串) 包含可执行的代码块 (标记为 ```python ...``` 或 ```sh ...```)。
2. TOOL_REJECTED: 满足 `TOOL_APPROVED` 的条件 a) 或 b)，但包含危险操作（如 `rm` 命令）。
3. TASK_COMPLETED: 任务目标已明确达成，并且 **助手代理** 的最后一条消息JSON中 **没有** 包含任何 `tool_calls`、`function_call` 或可执行代码块 (```python ...``` 或 ```sh ...```)。
4. TEXT_RESPONSE: 不符合以上任何条件，通常是简单的文本交流，需要继续对话。

明确指示：
- 仔细检查 **助手代理** 的最后一条消息JSON对象。
- **首要检查** JSON中是否存在 `tool_calls` (列表) 或 `function_call` (字典) 键。如果存在，通常应选择 `TOOL_APPROVED`。
- **同时检查** JSON中 `content` 字段是否包含 ```python ...``` 或 ```sh ...``` 代码块。如果存在，通常也应选择 `TOOL_APPROVED`。
- ***重要***：**只要满足以上任一条件 (存在 `tool_calls`/`function_call` 或 `content` 中存在代码块)，就必须判断为 `TOOL_APPROVED`** (除非含危险操作，则为 `TOOL_REJECTED`)。**即使消息文本中包含"完成任务"或类似的表述，也不能将其判断为 `TASK_COMPLETED`！**
- **永远不要** 在 TEXT_RESPONSE 中回复"同意"或"请继续执行"，如果需要执行工具/代码，必须选择 `TOOL_APPROVED`。
- 如果检测到 `rm` 命令或其他潜在危险操作，应选择 `TOOL_REJECTED` 并建议替代方案（如 `mv`）。
- **只有当任务目标看起来已完成，并且** 助手最后的消息JSON中 **绝对没有** `tool_calls`、`function_call` 或任何 ```...``` 代码块时，才能返回 `TASK_COMPLETED`。

你的响应必须是一个符合以下格式的JSON对象:
{{
  "action_type": "TOOL_APPROVED|TOOL_REJECTED|TASK_COMPLETED|TEXT_RESPONSE",
  "message": "简短说明或回复内容 (仅在TOOL_REJECTED或TEXT_RESPONSE时填写)",
  "reasoning": "你的判断理由 (基于对最后助手消息JSON的分析，明确说明是基于 tool_calls/function_call 还是代码块)"
}}

注意:
- 如果选择 `TOOL_APPROVED` 或 `TASK_COMPLETED`，message字段应为空字符串 `""`。
- 请基于对 **最后一条助手消息JSON结构和内容** 的分析做出判断。

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
            # Ensure action_type exists and maps correctly, default to TEXT_RESPONSE
            action_type = response_data.get("action_type")
            # Simple validation, could be more robust checking against ResponseType enum values if imported
            valid_types = ["TOOL_APPROVED", "TOOL_REJECTED", "TASK_COMPLETED", "TEXT_RESPONSE"]
            if action_type not in valid_types:
                 logger.warning(f"LLM returned unknown action_type '{action_type}'. Defaulting to TEXT_RESPONSE.")
                 action_type = "TEXT_RESPONSE" # Default to TEXT_RESPONSE if invalid type

            return {
                "type": action_type,
                "message": response_data.get("message", ""),
                "reasoning": response_data.get("reasoning", "")
            }
        except Exception as e:
            logger.error(f"解析LLM响应JSON时出错: {str(e)}")
            logger.error(f"原始响应: {llm_response}")

            # --- Fallback Logic: Parse raw string ---
            logger.info("JSON解析失败，尝试从原始响应文本中解析关键词...")
            raw_response_upper = llm_response.upper() # Case-insensitive check

            # 优先检查更明确的带引号的关键词
            if "\"TOOL_APPROVED\"" in raw_response_upper:
                 logger.warning("Fallback: 检测到 '\"TOOL_APPROVED\"' 关键词。")
                 return {
                     "type": "TOOL_APPROVED",
                     "message": "",
                     "reasoning": "Fallback: Parsed 'TOOL_APPROVED' keyword from raw text after JSON failure."
                 }
            elif "\"TOOL_REJECTED\"" in raw_response_upper:
                 logger.warning("Fallback: 检测到 '\"TOOL_REJECTED\"' 关键词。")
                 return {
                     "type": "TOOL_REJECTED",
                     "message": "Fallback: Rejected tool use based on raw text.", # Provide a generic message
                     "reasoning": "Fallback: Parsed 'TOOL_REJECTED' keyword from raw text after JSON failure."
                 }
            elif "\"TASK_COMPLETED\"" in raw_response_upper:
                 logger.warning("Fallback: 检测到 '\"TASK_COMPLETED\"' 关键词。")
                 return {
                     "type": "TASK_COMPLETED",
                     "message": "",
                     "reasoning": "Fallback: Parsed 'TASK_COMPLETED' keyword from raw text after JSON failure."
                 }
            # 如果带引号的找不到，尝试不带引号的（降低可靠性，但增加找到的可能性）
            elif "TOOL_APPROVED" in raw_response_upper:
                 logger.warning("Fallback: 检测到 'TOOL_APPROVED' (无引号) 关键词。")
                 return {
                     "type": "TOOL_APPROVED",
                     "message": "",
                     "reasoning": "Fallback: Parsed 'TOOL_APPROVED' keyword (no quotes) from raw text after JSON failure."
                 }
            elif "TOOL_REJECTED" in raw_response_upper:
                 logger.warning("Fallback: 检测到 'TOOL_REJECTED' (无引号) 关键词。")
                 return {
                     "type": "TOOL_REJECTED",
                     "message": "Fallback: Rejected tool use based on raw text (no quotes).",
                     "reasoning": "Fallback: Parsed 'TOOL_REJECTED' keyword (no quotes) from raw text after JSON failure."
                 }
            elif "TASK_COMPLETED" in raw_response_upper:
                 logger.warning("Fallback: 检测到 'TASK_COMPLETED' (无引号) 关键词。")
                 return {
                     "type": "TASK_COMPLETED",
                     "message": "",
                     "reasoning": "Fallback: Parsed 'TASK_COMPLETED' keyword (no quotes) from raw text after JSON failure."
                 }
            else:
                 # --- 如果连关键词都找不到，才返回默认的 TEXT_RESPONSE ---
                 logger.warning("Fallback: 无法从原始响应中解析JSON或识别任何操作关键词。")
                 return {
                     "type": "TEXT_RESPONSE",
                     "message": "继续对话",
                     "reasoning": "Fallback: Could not parse JSON or find action keywords in raw text."
                 }
            # --- Fallback Logic End --- 