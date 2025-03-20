"""
AG2Wrapper核心模块 - 对官方AG2框架的封装

这个模块提供AG2Wrapper核心类，它封装了官方AG2/AutoGen框架的主要功能，
简化了多Agent对话系统的创建和使用流程。

使用环境要求：
- conda环境'ag2'中已安装官方AutoGen框架(可通过`conda activate ag2`激活)
- 当前版本支持AutoGen 0.7.5
"""

import os
import sys
import yaml
import json
import logging
from typing import Dict, Any, List, Optional, Callable, Union, Type

# 依赖检查和导入
try:
    import autogen
    logging.debug(f"已导入 autogen {autogen.__version__}")
except ImportError:
    raise ImportError(
        "未找到autogen包。请确保已正确安装:\n"
        "$ pip install ag2[openai]\n"
        "或者\n"
        "$ pip install pyautogen\n"
    )

# 设置日志
logger = logging.getLogger(__name__)

# 使用相对导入
from .tools import AG2ToolManager
from ..agent_tools.file_operation_tool import FileOperationTool

class AG2Wrapper:
    """
    AG2Wrapper - 官方AG2/AutoGen框架的核心封装类
    
    AG2Wrapper提供一个简化的接口，用于创建和管理基于AG2的多Agent对话系统。
    主要功能包括：
    - 创建不同类型的对话模式(TwoAgentChat, SequentialChat, GroupChat等)
    - 管理LLM配置
    - 注册和管理工具
    - 简化Agent创建和配置
    
    基本使用示例:
    ```python
    wrapper = AG2Wrapper()
    
    # 创建两Agent对话
    chat = wrapper.create_two_agent_chat(
        assistant_config={"llm_config": llm_config},
        human_config={"code_execution": True}
    )
    
    # 启动对话
    chat.start("请帮我创建一个简单的Python爬虫")
    ```
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化AG2Wrapper实例
        
        Args:
            config_path: 可选的配置文件路径(.yaml或.json)
        """
        # 初始化内部状态
        self.agents = {}
        self.tools = {}
        self.tool_manager = None
        
        # 加载配置(如果提供)
        self.config = {}
        if config_path:
            self._load_config(config_path)
            
        # 记录版本信息
        self.autogen_version = getattr(autogen, "__version__", "unknown")
        logger.info(f"AG2Wrapper已初始化，使用AutoGen版本: {self.autogen_version}")
    
    def _load_config(self, config_path: str) -> None:
        """
        从文件加载配置
        
        Args:
            config_path: 配置文件路径(.yaml或.json)
        
        Raises:
            ValueError: 如果配置格式不支持或文件不存在
        """
        if not os.path.exists(config_path):
            raise ValueError(f"配置文件不存在: {config_path}")
        
        _, ext = os.path.splitext(config_path)
        ext = ext.lower()
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                if ext in ('.yaml', '.yml'):
                    self.config = yaml.safe_load(f)
                elif ext == '.json':
                    self.config = json.load(f)
                else:
                    raise ValueError(f"不支持的配置文件格式: {ext}")
        except Exception as e:
            raise ValueError(f"加载配置文件失败: {str(e)}")
    
    def register_tool(self, name: str, function: Callable, description: str = None, parameters: Dict = None) -> None:
        """
        注册工具函数
        
        Args:
            name: 工具名称
            function: 工具函数
            description: 工具描述(用于LLM理解)
            parameters: 工具参数定义
        """
        self.tools[name] = {
            'function': function,
            'description': description,
            'parameters': parameters
        }
        logger.debug(f"已注册工具: {name}")
    
    def integrate_tool_manager(self, tool_manager) -> None:
        """
        集成外部工具管理器
        
        Args:
            tool_manager: 外部工具管理器实例(如agent_tools.tool_manager.ToolManager)
        """
        self.tool_manager = tool_manager
        logger.debug("已集成外部工具管理器")
    
    def create_two_agent_chat(self,
                             assistant_config: Dict[str, Any],
                             human_config: Optional[Dict[str, Any]] = None,
                             llm_driven_proxy: bool = False,
                             task_description: Optional[str] = None,
                             system_prompt: Optional[str] = None,
                             llm_config: Optional[Dict[str, Any]] = None):
        """创建两Agent对话
        
        直接创建并返回配置好的助手代理和用户代理，可用于对话
        
        Args:
            assistant_config: 助手Agent配置
            human_config: 人类/用户Agent配置
            llm_driven_proxy: 是否使用LLM驱动的用户代理
            task_description: 任务描述
            system_prompt: 系统提示词
            llm_config: LLM配置
        
        Returns:
            配置好的代理字典，包含"assistant"和"human"两个键
        """
        # 合并工具配置到LLM配置
        merged_llm_config = llm_config.copy() if llm_config else {}
        if self.tool_manager:
            merged_llm_config.setdefault("tools", []).extend(
                self.tool_manager.create_openai_tools_spec()
            )

        # 创建助手代理
        assistant = self._create_assistant_agent(
            assistant_config, 
            merged_llm_config  # 使用合并后的配置
        )
        
        # 创建用户代理
        human = self._create_human_agent(
            human_config or {},
            llm_driven_proxy,
            task_description,
            system_prompt,
            merged_llm_config  # 使用合并后的配置
        )
        
        return {
            "assistant": assistant, 
            "human": human
        }

    def _create_assistant_agent(self, config: Dict[str, Any], llm_config: Optional[Dict[str, Any]] = None):
        """创建助手Agent"""
        # 提取必要参数
        name = config.pop('name', 'Assistant')
        
        # 如果配置中没有llm_config，才使用传入的llm_config
        if 'llm_config' not in config and llm_config is not None:
            config['llm_config'] = llm_config
        
        # 使用配置创建助手代理
        return autogen.AssistantAgent(
            name=name,
            **config  # 传递剩余配置，包括llm_config
        )

    def _create_human_agent(self, 
                          config: Dict[str, Any],
                          llm_driven_proxy: bool,
                          task_description: Optional[str],
                          system_prompt: Optional[str],
                          llm_config: Optional[Dict[str, Any]]):
        """创建人类/用户Agent"""
        # 提取必要参数
        name = config.pop('name', 'User')
        
        # 判断是否使用LLM驱动的用户代理
        if llm_driven_proxy:
            # 确保有LLM配置
            if not llm_config:
                raise ValueError("使用LLM驱动用户代理时必须提供llm_config")
                
            # 导入LLM驱动用户代理
            from ag2_wrapper.chat_modes.llm_driven_agent import LLMDrivenUserProxy
            
            # 创建LLM驱动的用户代理（不传递task_description）
            human_agent = LLMDrivenUserProxy(
                name=name,
                llm_config=llm_config,
                **config  # 传递剩余配置
            )
        else:
            # 创建普通用户代理
            human_agent = autogen.UserProxyAgent(
                name=name,
                system_message=system_prompt,
                **config  # 传递剩余配置
            )
        
        return human_agent
    
    def create_sequential_chat(self,
                             agents_config: Dict[str, Dict[str, Any]],
                             order: List[str],
                             initial_message: Optional[str] = None) -> 'SequentialChat':
        """
        创建顺序执行的多Agent对话
        
        Args:
            agents_config: 多个Agent的配置字典
            order: Agent执行顺序列表
            initial_message: 可选的初始消息
            
        Returns:
            配置好的SequentialChat实例
        """
        # 导入需要的模块
        from ag2_wrapper.chat_modes.sequential import SequentialChat
        
        # 返回对话实例
        return SequentialChat(
            agents_config=agents_config,
            order=order,
            initial_message=initial_message,
            tools=self.tools,
            tool_manager=self.tool_manager
        )
    
    def create_group_chat(self,
                        agents_config: Dict[str, Dict[str, Any]],
                        facilitator_name: Optional[str] = None,
                        initial_message: Optional[str] = None) -> 'GroupChat':
        """
        创建群聊对话
        
        Args:
            agents_config: 多个Agent的配置字典
            facilitator_name: 可选的主持人Agent名称
            initial_message: 可选的初始消息
            
        Returns:
            配置好的GroupChat实例
        """
        # 导入需要的模块
        from ag2_wrapper.chat_modes.group_chat import GroupChat
        
        # 返回对话实例
        return GroupChat(
            agents_config=agents_config,
            facilitator_name=facilitator_name,
            initial_message=initial_message,
            tools=self.tools,
            tool_manager=self.tool_manager
        )
    
    def create_nested_chat(self,
                         main_agent_config: Dict[str, Any],
                         sub_agents_config: Dict[str, Dict[str, Any]],
                         initial_message: Optional[str] = None) -> 'NestedChat':
        """
        创建嵌套对话
        
        Args:
            main_agent_config: 主Agent配置
            sub_agents_config: 子Agent配置字典
            initial_message: 可选的初始消息
            
        Returns:
            配置好的NestedChat实例
        """
        # 导入需要的模块
        from ag2_wrapper.chat_modes.nested import NestedChat
        
        # 返回对话实例
        return NestedChat(
            main_agent_config=main_agent_config,
            sub_agents_config=sub_agents_config,
            initial_message=initial_message,
            tools=self.tools,
            tool_manager=self.tool_manager
        )
    
    def create_swarm(self,
                   coordinator_config: Dict[str, Any],
                   experts_config: Dict[str, Dict[str, Any]],
                   initial_message: Optional[str] = None) -> 'Swarm':
        """
        创建Swarm协作模式
        
        Args:
            coordinator_config: 协调者Agent配置
            experts_config: 专家Agent配置字典
            initial_message: 可选的初始消息
            
        Returns:
            配置好的Swarm实例
        """
        # 导入需要的模块
        from ag2_wrapper.chat_modes.swarm import Swarm
        
        # 返回对话实例
        return Swarm(
            coordinator_config=coordinator_config,
            experts_config=experts_config,
            initial_message=initial_message,
            tools=self.tools,
            tool_manager=self.tool_manager
        )
    
    def get_version_info(self) -> Dict[str, str]:
        """
        获取版本信息
        
        Returns:
            包含版本信息的字典
        """
        return {
            "ag2_wrapper_version": "0.1.0",
            "autogen_version": self.autogen_version
        }