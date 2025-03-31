"""
AG2Wrapper配置管理模块

这个模块处理AG2-Wrapper的配置管理，包括LLM配置、对话模式配置等。
提供了统一的配置接口和辅助函数，简化AutoGen配置过程。
"""

import os
import sys
import yaml
import json
import logging
from typing import Dict, Any, List, Optional, Union

logger = logging.getLogger(__name__)

class ConfigManager:
    """
    配置管理器 - 处理AG2-Wrapper的配置
    
    主要功能：
    - 加载和管理配置
    - 提供标准化LLM配置接口
    - 管理API密钥和环境变量
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_path: 可选的配置文件路径(.yaml或.json)
        """
        # 初始化默认配置
        self.config = {
            "llm": {
                "default_config_list": []
            },
            "agents": {},
            "tools": {},
            "chat_modes": {}
        }
        
        # 加载配置文件(如果提供)
        if config_path:
            self.load_config(config_path)
    
    def load_config(self, config_path: str) -> Dict[str, Any]:
        """
        从文件加载配置
        
        Args:
            config_path: 配置文件路径(.yaml或.json)
            
        Returns:
            加载的配置字典
            
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
                    loaded_config = yaml.safe_load(f)
                elif ext == '.json':
                    loaded_config = json.load(f)
                else:
                    raise ValueError(f"不支持的配置文件格式: {ext}")
            
            # 更新配置
            self._update_config(loaded_config)
            return self.config
            
        except Exception as e:
            raise ValueError(f"加载配置文件失败: {str(e)}")
    
    def _update_config(self, new_config: Dict[str, Any]) -> None:
        """
        递归更新配置字典
        
        Args:
            new_config: 新配置字典
        """
        for key, value in new_config.items():
            if (key in self.config and isinstance(self.config[key], dict) 
                and isinstance(value, dict)):
                self._update_config_dict(self.config[key], value)
            else:
                self.config[key] = value
    
    def _update_config_dict(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """
        递归更新配置子字典
        
        Args:
            target: 目标字典
            source: 源字典
        """
        for key, value in source.items():
            if (key in target and isinstance(target[key], dict) 
                and isinstance(value, dict)):
                self._update_config_dict(target[key], value)
            else:
                target[key] = value
    
    def save_config(self, config_path: str) -> None:
        """
        保存配置到文件
        
        Args:
            config_path: 配置文件路径(.yaml或.json)
            
        Raises:
            ValueError: 如果配置格式不支持
        """
        _, ext = os.path.splitext(config_path)
        ext = ext.lower()
        
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                if ext in ('.yaml', '.yml'):
                    yaml.dump(self.config, f, default_flow_style=False)
                elif ext == '.json':
                    json.dump(self.config, f, indent=2)
                else:
                    raise ValueError(f"不支持的配置文件格式: {ext}")
        except Exception as e:
            raise ValueError(f"保存配置文件失败: {str(e)}")
    
    def get_llm_config(self, config_name: Optional[str] = None) -> Dict[str, Any]:
        """
        获取LLM配置
        
        Args:
            config_name: 可选的配置名称，如果未提供则使用默认配置
            
        Returns:
            LLM配置字典，适用于AutoGen
        """
        if config_name and config_name in self.config.get("llm", {}):
            return self.config["llm"][config_name]
        
        # 返回默认配置
        default_config = {
            "config_list": self.config.get("llm", {}).get("default_config_list", [])
        }
        
        return default_config
    
    def create_llm_config(self, 
                        model: str, 
                        api_key: Optional[str] = None,
                        base_url: Optional[str] = None,
                        temperature: float = 0.7,
                        system_message: Optional[str] = None) -> Dict[str, Any]:
        """
        创建标准LLM配置
        
        Args:
            model: 模型名称
            api_key: API密钥(如果未提供则尝试从环境变量获取)
            base_url: 可选的API基础URL
            temperature: 温度参数，控制输出随机性
            system_message: 可选的系统消息
            
        Returns:
            适用于AutoGen的LLM配置字典
        """
        # 确定API密钥
        if not api_key:
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                logger.warning("未提供API密钥且环境变量OPENAI_API_KEY未设置")
        
        # 创建基本配置
        config = {
            "config_list": [
                {
                    "model": model,
                    "api_key": api_key
                }
            ],
            "temperature": temperature
        }
        
        # 添加可选参数
        if base_url:
            config["config_list"][0]["base_url"] = base_url
        
        # 如果有系统消息，添加到配置中
        if system_message:
            config["default_system_message"] = system_message
        
        return config
    
    def get_agent_config(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """
        获取Agent配置
        
        Args:
            agent_name: Agent名称
            
        Returns:
            Agent配置字典或None(如果不存在)
        """
        return self.config.get("agents", {}).get(agent_name)
    
    def get_tool_config(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        获取工具配置
        
        Args:
            tool_name: 工具名称
            
        Returns:
            工具配置字典或None(如果不存在)
        """
        return self.config.get("tools", {}).get(tool_name)
    
    def get_chat_mode_config(self, mode_name: str) -> Optional[Dict[str, Any]]:
        """
        获取对话模式配置
        
        Args:
            mode_name: 对话模式名称
            
        Returns:
            对话模式配置字典或None(如果不存在)
        """
        return self.config.get("chat_modes", {}).get(mode_name)

    def set_config(self, key: str, value: Any, section: Optional[str] = None) -> None:
        """
        设置配置项
        
        Args:
            key: 配置键
            value: 配置值
            section: 可选的配置分区名称(如'llm', 'agents', 'tools')
                    如果未提供，则直接设置顶层配置项
        """
        if section:
            if section not in self.config:
                self.config[section] = {}
            self.config[section][key] = value
        else:
            # 检查是否能内联设置LLM配置参数
            if key == 'temperature' and isinstance(value, (int, float)):
                if 'llm' not in self.config:
                    self.config['llm'] = {}
                self.config['llm']['temperature'] = value
            else:
                self.config[key] = value


# 便捷函数
def create_openai_config(model: str = "gpt-3.5-turbo",
                       api_key: Optional[str] = None,
                       base_url: Optional[str] = None,
                       temperature: float = 0.7,
                       system_message: Optional[str] = None) -> Dict[str, Any]:
    """
    创建OpenAI配置的便捷函数
    
    Args:
        model: 模型名称
        api_key: API密钥(如果未提供则尝试从环境变量获取)
        base_url: 可选的API基础URL(如OpenRouter)
        temperature: 温度参数
        system_message: 可选的系统消息
        
    Returns:
        适用于AutoGen的LLM配置字典
    """
    # 确定API密钥
    if not api_key:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            logger.warning("未提供API密钥且环境变量OPENAI_API_KEY未设置")
    
    # 创建基本配置
    config = {
        "config_list": [
            {
                "model": model,
                "api_key": api_key
            }
        ],
        "temperature": temperature
    }
    
    # 添加可选参数
    if base_url:
        config["config_list"][0]["base_url"] = base_url
    
    # 如果有系统消息，添加到配置中
    if system_message:
        # 在AG2中，应该使用 default_system_message 而不是直接在 LLM 配置中使用 system_message
        config["default_system_message"] = system_message
    
    return config


def create_openrouter_config(model: str = "openrouter/google/gemini-2.0-flash-lite-001",
                           api_key: Optional[str] = None,
                           temperature: float = 0.7,
                           system_message: Optional[str] = None,
                           max_tokens: Optional[int] = None) -> Dict[str, Any]:
    """
    创建OpenRouter配置的便捷函数
    
    Args:
        model: 模型名称，已自动添加openrouter前缀。包含供应商前缀，如:
               - "openrouter/google/gemini-2.0-flash-lite-001"
               - "openrouter/openai/gpt-4o-mini"
               - "openrouter/anthropic/claude-3-opus"
               注意：如果不包含"openrouter/"前缀，系统会自动添加。
        api_key: OpenRouter API密钥(如果未提供则尝试从环境变量获取)
        temperature: 温度参数
        system_message: 可选的系统消息
        max_tokens: 可选的最大token数
        
    Returns:
        适用于LLM调用的配置字典（兼容AG2Wrapper和litellm）
    """
    # 尝试从环境变量获取API密钥
    if not api_key:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            logger.warning("未提供API密钥且环境变量OPENROUTER_API_KEY未设置")
    
    # 设置OpenRouter的环境变量 - 这是更安全的方式传递headers
    os.environ["OPENROUTER_REFERRER"] = "https://github.com/microsoft/autogen"
    os.environ["OPENROUTER_APP"] = "AG2-Wrapper"
    
    # 创建适用于litellm直接调用和AG2Wrapper的配置
    config = {
        "model": model,
        "api_key": api_key,
        "base_url": "https://openrouter.ai/api/v1",
        "temperature": temperature,
        "api_type": "openai",
    }
    
    # 添加可选的最大token数
    if max_tokens is not None:
        config["max_tokens"] = max_tokens
    
    # 如果有系统消息，添加到配置中
    if system_message:
        config["system_message"] = system_message
        
    # 修改 AG2 兼容层配置
    config["config_list"] = [
        {
            "model": model,
            "api_key": api_key,
            "base_url": "https://openrouter.ai/api/v1",
            "api_type": "openai",
        }
    ]
    
    # 在AG2中，系统消息使用 default_system_message
    if system_message:
        config["default_system_message"] = system_message
        
    return config