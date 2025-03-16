"""
模块名称：文件操作代理核心服务
模块职责：
    ① 文件操作工具调用封装
    ② 根据用户需求生成符合文件操作工具调用规范的 JSON 指令，以便自动化执行文件的创建、读取与修改操作

依赖说明：
    - 使用 litellm 作为 LLM 抽象层，请确保已安装 litellm 库 (pip install litellm)
    - 文件操作工具调用规范参见 poe_server/core/file_operation_tool.py
"""

import os
import json
import logging
import traceback
import re
from typing import Union, AsyncGenerator, List
from litellm import acompletion

# 配置日志输出
logging.basicConfig(level=logging.INFO)

# 默认使用的模型（可根据实际情况调整）
# DEFAULT_MODEL = "groq/deepseek-r1-distill-llama-70b-specdec"
DEFAULT_MODEL = "gemini/gemini-2.0-flash"
# 定义文件操作代理的角色及其系统提示词
ROLES = {
    "file_ops_agent": {
        "system_prompt": """你是一个专业的文件操作专家。你的任务是根据用户需求生成符合文件操作工具调用规范的 JSON 指令，用于自动化地进行文件的创建、读取与修改操作。

请严格按照以下格式生成 JSON 指令，这个指令用json代码块包裹，分行请严格遵守下面的例子，请仅输出如下格式的代码块：```json\n{...}\n``，且不要包含任何解释性文字或额外内容：
{
    "tool_calls": [
        {
            "tool_name": "file_operation",  // 固定值，不可修改
            "parameters": {
                "operation": "操作类型",       // 取值："create"、"read" 或 "modify"
                "path": "文件路径",            // 必填，路径相对于项目根目录
                // 当 operation 为 "create" 时，必须提供：
                "content": "文件内容",
                // 当 operation 为 "modify" 时，必须提供：
                "original_snippet": "原始内容片段",
                "new_snippet": "新的内容片段"
            }
        }
    ]
}

示例1：创建文件
{
    "tool_calls": [{
        "tool_name": "file_operation",
        "parameters": {
            "operation": "create",
            "path": "example.txt",
            "content": "Hello, world!"
        }
    }]
}

示例2：读取文件
{
    "tool_calls": [{
        "tool_name": "file_operation",
        "parameters": {
            "operation": "read",
            "path": "example.txt"
        }
    }]
}

示例3：修改文件
{
    "tool_calls": [{
        "tool_name": "file_operation",
        "parameters": {
            "operation": "modify",
            "path": "example.txt",
            "original_snippet": "old content",
            "new_snippet": "new content"
        }
    }]
}

请确保输出严格为 JSON 格式，并且 JSON 中仅包含上述字段。
""",
        "response_template": {
            "tool_calls": [{
                "tool_name": "file_operation",
                "parameters": {
                    "operation": "str",
                    "path": "str"
                    # 注意：字段 "content"、"original_snippet"、"new_snippet" 根据 operation 类型可选
                }
            }]
        }
    }
}

async def call_file_ops_llm(
    prompt: str,
    model: str = DEFAULT_MODEL,
    system_prompt: str = "",
    messages: List[dict] = None,
    stream: bool = False
) -> Union[str, AsyncGenerator[str, None]]:
    """
    异步调用 LLM 生成文件操作工具调用 JSON 指令。
    
    参数说明：
    - prompt: 用户输入的请求信息
    - model: 使用的语言模型（默认采用全局 DEFAULT_MODEL）
    - system_prompt: 系统提示词，如果为空，则自动采用 ROLES 中 file_ops_agent 的提示词
    - messages: 历史消息记录列表，可用于上下文续传
    - stream: 是否启用流式响应

    返回：
    - 如果 stream 为 False，则返回完整的响应内容 (JSON 字符串)
    - 如果 stream 为 True，则返回一个异步生成器，用于逐步读取响应内容
    """
    if not system_prompt:
        system_prompt = ROLES["file_ops_agent"]["system_prompt"]
    
    try:
        # 构建完整的消息列表
        full_messages = []
        full_messages.append({"role": "system", "content": system_prompt})
        if messages:
            full_messages.extend(messages)
        full_messages.append({"role": "user", "content": prompt})
        
        # 使用异步调用 LLM
        response = await acompletion(
            model=model,
            messages=full_messages,
            temperature=0.7,
            max_tokens=8192,
            stream=stream
        )
        
        # 输出调试日志
        logging.info(f"原始响应内容：\n{response}")
        if hasattr(response, 'choices'):
            logging.info(f"响应文本：{response.choices[0].message.content}")
        
        if stream:
            async def response_generator():
                async for chunk in response:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
            return response_generator()
        
        # 修改后的代码
        message_content = (
            response.choices[0].message.content
            if hasattr(response, 'choices') and response.choices else str(response)
        )
        if not re.search(r'```json\n?\{.*?\}\n?```', message_content, re.DOTALL):
            # 尝试提取任何 JSON 内容
            json_match = re.search(r'\{.*\}', message_content, re.DOTALL)
            if json_match:
                return json_match.group()
            
            logging.error("生成的响应不符合 JSON 格式要求")
            logging.debug(f"实际响应内容: {message_content[:200]}...")  # 记录部分响应内容用于调试
            return {"status": "error", "message": "LLM 响应格式错误"}
        
        return message_content
        
    except Exception as e:
        logging.error(f"LLM 调用异常: {str(e)}")
        return {"status": "error", "message": f"LLM 服务异常: {str(e)}"} 