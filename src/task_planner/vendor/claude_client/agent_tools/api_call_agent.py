# 
# 模块名称：API调用代理核心服务
# 模块职责：
# ① 大语言模型服务抽象层
#    - 基于 litellm 统一多模型接口
#    - 支持同步/异步流式响应
# ② API参数生成引擎
#    - 动态文档注入
#    - 参数格式校验
# ③ 多角色提示词管理
#    - 系统提示词版本控制
#    - 角色专属模板管理
#
# 技术规格：
# a. 模型调用规范
#    - 默认模型：groq/deepseek-r1-distill-llama-70b-specdec
#    - 温度系数：0.7（范围 0.1~1.0）
#    - 最大长度：2000 tokens
# b. 流式响应
#    - 使用 FastAPI 的 StreamingResponse
#    - 数据格式：text/event-stream
#    - 分块大小：512 tokens/秒
#
# 依赖说明：
# 1. 基础依赖
#    - litellm==1.2.3（LLM抽象层）
#    - fastapi>=0.95.0（API服务框架）
# 2. 环境配置
#    - GROQ_API_KEY 需配置在环境变量
#    - LITELLM_MODEL_ALIAS 可自定义模型映射
#

# 该文件是京东VOP API调用代理的核心实现，主要功能包括：
# 1. 大语言模型调用封装
# 2. API调用参数生成
# 3. 多角色提示词管理
# 4. 异步流式响应处理
#
# 依赖说明：
# 1. 使用 litellm 作为LLM调用抽象层，支持多模型提供商
#    - 安装: pip install litellm
#    - 核心调用参数：
#      * model: 模型标识（如"groq/deepseek-r1-distill-llama-70b-specdec"）
#      * messages: 消息列表（需包含system/user角色）
#      * temperature: 创造性系数（默认0.7）
#      * max_tokens: 最大输出长度（默认2000）
#      * stream: 是否启用流式响应
# 2. 异步流式处理需配合AsyncGenerator使用
#

import os
import json
import logging
from typing import Dict, Union, List, AsyncGenerator
from litellm import acompletion
import traceback
import re

# 配置日志
logging.basicConfig(level=logging.INFO)
SEPARATOR = "=" * 40

# 全局可选模型配置
AVAILABLE_MODELS = {
    "default": "groq/deepseek-r1-distill-llama-70b-specdec",
    "backup": "alternative-model-id"  # 替换为实际备用模型标识
}

# 默认使用的模型
DEFAULT_MODEL = AVAILABLE_MODELS["default"]

def load_jdvop_api_docs() -> Union[str, None]:
    """
    从 markdown 文件加载 JDVOP API 文档，
    用于构造 api_call_agent 的系统提示词中的 {available_apis} 字段。
    """
    try:
        with open('jdvop_index_api.md', 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logging.error(f"加载 JDVOP API 文档失败: {e}")
        return None

# 定义角色，这里将原先 "search_agent" 调整为 "api_call_agent"
ROLES = {
    "api_call_agent": {
        "system_prompt": """你是一个专业的 API 调用专家。你的任务是根据用户需求和以下 API 文档，生成完整的 API 调用信息。

API文档如下：
{available_apis}
构建接口请求时候里面的firm请用2125316313314350002
请每次只执行一个 API 工具调用，严格按以下JSON格式输出：
{
    "tool_calls": [
        {
            "tool_name": "api_call",  // 固定工具名称
            "parameters": {
                "url": "完整的 API 地址",  // 必须包含
                "method": "GET/POST/PUT/DELETE等"   // 必须包含
            }
        }
    ]
}

格式要求：
1. 必须且只能包含 url 和 method 字段
2. GET请求示例：
{{
    "tool_calls": [{{
        "tool_name": "api_call",
        "parameters": {{
            "url": "https://api.example.com/data?page=1",
            "method": "GET"
        }}
    }}]
}}

3. POST请求示例：
{{
    "tool_calls": [{{
        "tool_name": "api_call",
        "parameters": {{
            "url": "https://api.example.com/create",
            "method": "POST"
        }}
    }}]
}}

错误示例：
❌ 包含额外字段：
{{"tool_calls":[{{"tool_name":"api_call","parameters":{{"url":"...", "method":"GET", "headers":{{}}}}}}]}}
""",
        "response_template": {
            "tool_calls": [{
                "tool_name": "api_call",
                "parameters": {
                    "url": "str",
                    "method": "str"
                }
            }]
        }
    },
    
    "analysis_agent": {
        "system_prompt": """你是一个专业的商品分析专家。请用清晰的中文自然语言对搜索结果进行以下分析：

分析要求：
1. 价格分析（区间、均价、价格分布特点）
2. 品牌对比（主要品牌及其优势）
3. 性价比分析（推荐理由）
4. 推荐商品（3-5个，需包含具体价格和推荐原因）

输出要求：
- 使用 Markdown 格式
- 包含分级标题（##）
- 价格使用**加粗**显示
- 商品推荐使用有序列表
- 避免使用 JSON 等结构化格式
- 推荐的商品请附上图片，图片请用 Markdown 格式输出，例如：
  ![商品名称](图片URL)
""",
        "response_template": {}  # 无需结构化验证
    }
}

async def call_llm(
    prompt: str,
    model: str = DEFAULT_MODEL,
    system_prompt: str = "",
    messages: list = None,
    stream: bool = False
) -> Union[str, AsyncGenerator[str, None]]:
    """
    异步调用 LLM，在调用之前如果 system_prompt 中包含 {available_apis} 占位符，
    则从 load_jdvop_api_docs() 加载最新 API 文档并自动注入到系统提示中。
    """
    # 若 system_prompt 中有 {available_apis} 占位符，则自动加载 API 文档注入
    if "{available_apis}" in system_prompt:
        api_docs = load_jdvop_api_docs() or "未加载到 API 文档"
        # 先转义现有花括号
        system_prompt = system_prompt.replace("{", "{{").replace("}", "}}")
        # 然后替换目标占位符
        system_prompt = system_prompt.replace("{{available_apis}}", api_docs)

    try:
        # 构建完整的消息列表
        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
            
        # 添加历史消息（如果有）
        if messages:
            full_messages.extend(messages)
            
        # 添加当前用户消息
        full_messages.append({"role": "user", "content": prompt})
        
        # 使用异步调用
        response = await acompletion(
            model=model, 
            messages=full_messages,
            temperature=0.7,
            max_tokens=2000,
            stream=stream
        )
        
        # 新增调试输出
        logging.info(f"原始响应内容：\n{response}")  # 打印完整响应对象
        if hasattr(response, 'choices'):
            logging.info(f"响应文本：{response.choices[0].message.content}")  # 打印实际响应文本
        
        if stream:
            async def response_generator():
                async for chunk in response:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
            return response_generator()
        
        content = response.choices[0].message.content
        
        # 直接返回完整原始内容
        return content
        
    except Exception as e:
        logging.error(f"响应处理异常: {str(e)}")
        raise
