#!/usr/bin/env python3
"""
测试AG2执行器配置和适配器
"""

import os
import sys
import unittest
import asyncio
from unittest.mock import patch, AsyncMock

# 添加项目根目录到sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ag2_engine.adapters.standard_llm_agent import StandardLLMAgent
from ag2_engine.adapters.llm_config_adapter import ExternalLLMConfig

class TestStandardLLMAgent(unittest.TestCase):
    """测试StandardLLMAgent实现"""
    
    def test_init(self):
        """测试初始化"""
        # 创建标准配置
        llm_config = {
            "config_list": [
                {
                    "api_type": "openai",
                    "model": "gpt-4o",
                    "api_key": "test_key"
                }
            ]
        }
        
        # 创建agent
        agent = StandardLLMAgent(
            name="TestAgent",
            llm_config=llm_config,
            system_message="Test system message"
        )
        
        # 验证
        self.assertEqual(agent.name, "TestAgent")
        self.assertEqual(agent._system_message, "Test system message")
        self.assertTrue(agent._validate_config())
    
    def test_validate_config(self):
        """测试配置验证"""
        # 有效配置
        valid_config = {
            "config_list": [
                {
                    "api_type": "openai",
                    "model": "gpt-4o",
                    "api_key": "test_key"
                }
            ]
        }
        
        # 无效配置
        invalid_config = {
            "config_list": []
        }
        
        # 测试有效配置
        agent = StandardLLMAgent("Test", valid_config)
        self.assertTrue(agent._validate_config())
        
        # 测试无效配置
        agent = StandardLLMAgent("Test", invalid_config)
        self.assertFalse(agent._validate_config())
    
    @patch('ag2_engine.adapters.standard_llm_agent.AsyncOpenAI')
    @unittest.skip("需要网络连接")
    async def test_call_openai_api(self, mock_openai):
        """测试OpenAI API调用"""
        # 模拟AsyncOpenAI客户端
        mock_client = AsyncMock()
        mock_openai.return_value = mock_client
        
        # 模拟响应
        mock_response = AsyncMock()
        mock_response.choices = [AsyncMock()]
        mock_response.choices[0].message.content = "Mock response"
        mock_client.chat.completions.create.return_value = mock_response
        
        # 创建agent
        llm_config = {
            "config_list": [
                {
                    "api_type": "openai",
                    "model": "gpt-4o",
                    "api_key": "test_key"
                }
            ]
        }
        agent = StandardLLMAgent("Test", llm_config)
        
        # 测试API调用
        config = llm_config["config_list"][0]
        messages = [{"role": "user", "content": "Hello"}]
        result = await agent._call_openai_api(config, messages)
        
        # 验证
        self.assertEqual(result, "Mock response")
        mock_client.chat.completions.create.assert_called_once()

class TestExternalLLMConfig(unittest.TestCase):
    """测试ExternalLLMConfig实现"""
    
    def test_init(self):
        """测试初始化"""
        # 模拟LLM服务
        mock_service = AsyncMock()
        
        # 创建ExternalLLMConfig
        config = ExternalLLMConfig(
            llm_service=mock_service,
            model_name="test-model",
            temperature=0.5,
            max_tokens=1000
        )
        
        # 验证
        self.assertEqual(config.model_name, "test-model")
        self.assertEqual(config.temperature, 0.5)
        self.assertEqual(config.max_tokens, 1000)
    
    @patch('ag2_engine.adapters.llm_config_adapter.asyncio.iscoroutinefunction')
    async def test_generate(self, mock_iscoro):
        """测试生成响应"""
        # 模拟LLM服务
        mock_service = AsyncMock()
        mock_service.generate.return_value = {"content": "Generated response"}
        mock_iscoro.return_value = True
        
        # 创建ExternalLLMConfig
        config = ExternalLLMConfig(llm_service=mock_service)
        
        # 测试生成响应
        messages = [
            {"role": "system", "content": "System message"},
            {"role": "user", "content": "User message"}
        ]
        
        result = await config.generate(messages)
        
        # 验证
        self.assertEqual(result["content"], "Generated response")
        self.assertEqual(result["role"], "assistant")
        mock_service.generate.assert_called_once()

if __name__ == '__main__':
    unittest.main()