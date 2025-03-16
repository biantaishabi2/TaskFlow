#!/usr/bin/env python3
"""
OpenRouter API 测试示例 - 使用标准配置格式与OpenRouter API交互

这个示例展示如何使用AG2-Agent兼容的config_list格式调用OpenRouter API，
并实现多模型的自动回退机制。
"""

import sys
import os
import logging
import asyncio
from typing import Dict, Any, List

# 添加项目根目录到sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 导入OpenAI库和StandardLLMAgent
from openai import AsyncOpenAI
from ag2_agent.utils.standard_llm_agent import StandardLLMAgent

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_openrouter_api_direct():
    """使用直接API调用测试OpenRouter API基本功能"""
    print("\n=== 测试1：直接调用OpenRouter API ===")
    
    # 从环境变量读取API密钥
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        logger.error("未设置OPENROUTER_API_KEY环境变量")
        print("请使用: export OPENROUTER_API_KEY=your_api_key 设置环境变量")
        return False
        
    # 创建OpenAI客户端，连接到OpenRouter
    client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key
    )
    
    # 定义测试消息
    messages = [
        {"role": "system", "content": "你是一个有帮助的AI助手。"},
        {"role": "user", "content": "你好，请简单介绍一下你自己。"}
    ]
    
    # 测试Gemini模型
    model = "google/gemini-2.0-flash-lite-001"
    try:
        logger.info(f"测试模型: {model}")
        
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,
            max_tokens=150,
            extra_headers={
                "HTTP-Referer": "https://github.com/anthropics/claude-code", 
                "X-Title": "AG2-Agent-Test",
            }
        )
        
        content = response.choices[0].message.content
        print(f"问题: 你好，请简单介绍一下你自己。")
        print(f"回答 ({model}): {content[:150]}...\n")
        return True
        
    except Exception as e:
        logger.error(f"模型 {model} 测试失败: {str(e)}")
        print(f"错误: {str(e)}")
        return False

async def test_standard_llm_agent():
    """使用StandardLLMAgent测试OpenRouter API集成和回退机制"""
    print("\n=== 测试2：使用StandardLLMAgent和config_list配置测试OpenRouter API ===")
    
    # 从环境变量读取API密钥
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        logger.error("未设置OPENROUTER_API_KEY环境变量")
        print("请使用: export OPENROUTER_API_KEY=your_api_key 设置环境变量")
        return
    
    # 创建标准config_list配置（包含多个模型用于回退）
    llm_config = {
        "config_list": [
            # 主要配置 - 使用Gemini模型
            {
                "api_type": "openai",  # 使用OpenAI格式的API
                "model": "google/gemini-2.0-flash-lite-001",  # 通过OpenRouter使用Gemini模型
                "api_key": api_key,
                "base_url": "https://openrouter.ai/api/v1",
                "system_message": "你是一个友好、有帮助的AI助手，专长于提供简洁明了的回答。",
                "extra_headers": {
                    "HTTP-Referer": "https://github.com/anthropics/claude-code",
                    "X-Title": "AG2-Agent-Test",
                }
            },
            # 回退配置 - 使用Claude模型
            {
                "api_type": "openai",
                "model": "anthropic/claude-3-haiku-20240307",  # 回退到更小的Claude模型
                "api_key": api_key,
                "base_url": "https://openrouter.ai/api/v1",
                "extra_headers": {
                    "HTTP-Referer": "https://github.com/anthropics/claude-code",
                    "X-Title": "AG2-Agent-Test",
                }
            },
            # 第二回退配置 - 使用GPT-3.5
            {
                "api_type": "openai",
                "model": "openai/gpt-3.5-turbo",  # 第二回退选项
                "api_key": api_key,
                "base_url": "https://openrouter.ai/api/v1",
                "extra_headers": {
                    "HTTP-Referer": "https://github.com/anthropics/claude-code",
                    "X-Title": "AG2-Agent-Test",
                }
            }
        ]
    }
    
    # 创建StandardLLMAgent实例
    agent = StandardLLMAgent(
        name="OpenRouterAgent",
        llm_config=llm_config
    )
    
    print(f"已创建StandardLLMAgent，配置了以下模型：")
    for i, config in enumerate(llm_config["config_list"]):
        print(f"  {i+1}. {config['model']} (优先级: {'主要' if i==0 else '回退'+str(i)})")
    
    # 测试一系列问题
    test_questions = [
        "简单介绍一下量子计算的基本原理",
        "写一首关于人工智能的五言绝句",
        "如何使用Python实现快速排序算法？"
    ]
    
    print("\n开始测试问答...")
    for i, question in enumerate(test_questions):
        print(f"\n问题 {i+1}: {question}")
        try:
            # 使用agent生成回答
            response = await agent.generate_response(question)
            print(f"回答: {response[:150]}..." if len(response) > 150 else f"回答: {response}")
        except Exception as e:
            logger.error(f"生成回答时出错: {str(e)}")
            print(f"错误: {str(e)}")

async def main():
    """主函数"""
    print("=== OpenRouter API 测试示例 (使用StandardLLMAgent) ===\n")
    
    # 测试1：直接API调用测试
    api_test_success = await test_openrouter_api_direct()
    
    # 测试2：使用StandardLLMAgent测试（如果直接API调用成功）
    if api_test_success:
        await test_standard_llm_agent()
    else:
        print("\n直接API调用失败，跳过StandardLLMAgent测试")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    asyncio.run(main())