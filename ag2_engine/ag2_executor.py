import os
import yaml
import asyncio
from typing import Dict, Any, Optional

import sys
import os

# 添加vendor目录到Python路径
vendor_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'vendor')
if vendor_dir not in sys.path:
    sys.path.append(vendor_dir)

from ag2_agent import create_orchestration_manager
from ag2_agent.factories.factory_registry import register_default_factories

class AG2Executor:
    """基于AG2-Agent的独立执行器"""
    
    def __init__(self, config_path: Optional[str] = None, mode: str = "sequential"):
        """初始化AG2执行器
        
        Args:
            config_path: AG2配置文件路径
            mode: 对话模式 (two_agent, sequential, group, nested, swarm)
        """
        self.manager = create_orchestration_manager()
        self.config = self._load_config(config_path)
        self.mode = mode
        
        # 注册默认工厂
        for name, factory in register_default_factories().items():
            self.manager.register_chat_factory(name, factory)
            
        # 设置agents和tools
        self._setup_agents()
        self._setup_tools()
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """加载配置文件
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            配置字典
        """
        if not config_path or not os.path.exists(config_path):
            return {}
            
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _setup_agents(self) -> None:
        """从配置设置agents"""
        for name, agent_config in self.config.get('agents', {}).items():
            agent_type = agent_config.get('type', 'mock')
            
            if agent_type == 'llm':
                # 使用StandardLLMAgent
                from ag2_engine.adapters.standard_llm_agent import StandardLLMAgent
                
                llm_config = agent_config.get('llm_config', {})
                system_message = agent_config.get('system_message')
                
                agent = StandardLLMAgent(
                    name=agent_config.get('name', name),
                    llm_config=llm_config,
                    system_message=system_message
                )
            elif agent_type == 'external_llm':
                # 使用已废弃的ExternalLLMConfig (仅用于兼容旧代码)
                from ag2_engine.adapters.llm_config_adapter import ExternalLLMConfig
                from ag2_engine.adapters.llm_adapters import ClaudeLLMAdapter
                
                # 创建LLM服务
                llm_service = ClaudeLLMAdapter(
                    model_name=agent_config.get('model_name', 'claude-3-5-sonnet')
                )
                
                # 创建外部LLM配置
                llm_config = ExternalLLMConfig(
                    llm_service=llm_service,
                    model_name=agent_config.get('model_name', 'claude-3-5-sonnet'),
                    temperature=agent_config.get('temperature', 0.7),
                    max_tokens=agent_config.get('max_tokens')
                )
                
                # 创建使用外部LLM的代理
                class CustomAgent:
                    def __init__(self, name, llm_config):
                        self.name = name
                        self.llm_config = llm_config
                        
                    async def generate_response(self, message, history=None, context=None):
                        # 准备消息格式
                        messages = []
                        
                        # 添加系统消息
                        if agent_config.get('system_message'):
                            messages.append({
                                'role': 'system',
                                'content': agent_config.get('system_message')
                            })
                        
                        # 添加历史消息
                        if history:
                            for item in history:
                                role = 'assistant' if item.get('sender') == self.name else 'user'
                                messages.append({
                                    'role': role,
                                    'content': item.get('message', '')
                                })
                        
                        # 添加当前消息
                        messages.append({
                            'role': 'user',
                            'content': message
                        })
                        
                        # 使用LLM配置生成响应
                        result = await self.llm_config.generate(messages)
                        return result.get('content')
                    
                    def bind_tools(self, tools):
                        # 实现bind_tools接口
                        pass
                
                agent = CustomAgent(name=agent_config.get('name', name), llm_config=llm_config)
            else:
                # 默认使用MockAgent
                from vendor.ag2_agent.utils.mock_agent import MockAgent
                agent = MockAgent(name=agent_config.get('name', name))
            
            # 注册代理
            self.manager.register_agent(name, agent)
    
    def _setup_tools(self) -> None:
        """从配置设置工具"""
        for name, tool_config in self.config.get('tools', {}).items():
            # 简化实现，实际中需要更复杂的逻辑
            self.manager.register_tool(
                name=name,
                tool_function=lambda params, tool_name=name: self._execute_tool(tool_name, params),
                description=tool_config.get('description', '')
            )
    
    def _execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """执行工具
        
        Args:
            tool_name: 工具名称
            params: 工具参数
            
        Returns:
            工具执行结果
        """
        # 实际实现中，这里需要根据配置动态调用适当的工具
        # 简化实现
        return {"result": f"执行工具 {tool_name} 完成", "params": params}
    
    def _get_agents_for_mode(self) -> Dict[str, Any]:
        """根据当前模式获取适当的agents配置
        
        Returns:
            agents配置字典
        """
        mode_config = self.config.get('modes', {}).get(self.mode, {})
        return mode_config.get('agents', {})
    
    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """执行任务
        
        Args:
            task: 任务描述字典
            
        Returns:
            执行结果
        """
        # 使用asyncio运行异步代码
        return asyncio.run(self._execute_async(task))
    
    async def _execute_async(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """异步执行任务
        
        Args:
            task: 任务描述字典
            
        Returns:
            执行结果
        """
        # 根据任务和模式创建对话
        agents = self._get_agents_for_mode()
        chat = self.manager.create_chat(
            mode=self.mode,
            agents=agents,
            initial_prompt=task.get("description", ""),
            config=self.config.get('modes', {}).get(self.mode, {}).get('config', {})
        )
        
        # 执行对话
        response = await chat.initiate_chat(task.get("description", ""))
        
        # 如果需要额外的任务处理
        if task.get("follow_up"):
            for message in task.get("follow_up"):
                response = await chat.continue_chat(message)
        
        # 结束对话并获取结果
        result = chat.end_chat()
        
        # 返回结果
        return {
            "result": response,
            "status": "completed",
            "metadata": result
        }