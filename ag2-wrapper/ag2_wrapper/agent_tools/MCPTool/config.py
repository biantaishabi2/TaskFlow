"""
配置管理模块

这个模块负责处理MCP服务器的配置信息，支持多作用域配置（项目/全局/mcprc）。
使用Pydantic进行配置模型定义和验证。
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Literal
from pydantic import BaseModel, Field

# 配置文件路径
CONFIG_DIR = {
    "project": Path(os.getcwd()) / ".mcp",
    "global": Path.home() / ".mcp",
}
MCPRC_PATH = Path.home() / ".mcprc"


class McpServerConfig(BaseModel):
    """MCP服务器配置模型"""
    type: Literal["stdio", "sse"]
    command: Optional[str] = None  # For stdio
    args: Optional[List[str]] = None  # For stdio
    env: Optional[Dict[str, str]] = None  # For stdio
    url: Optional[str] = None  # For SSE
    
    class Config:
        extra = "allow"  # 允许额外字段


class ConfigStore(BaseModel):
    """配置存储模型"""
    mcp_servers: Dict[str, McpServerConfig] = Field(default_factory=dict)
    
    class Config:
        extra = "allow"  # 允许额外字段


# 配置缓存
_config_cache: Dict[str, ConfigStore] = {}


def _ensure_config_dir(scope: str) -> None:
    """确保配置目录存在"""
    if scope not in CONFIG_DIR:
        raise ValueError(f"无效的配置作用域: {scope}，可用作用域: {list(CONFIG_DIR.keys())}")
    
    config_dir = CONFIG_DIR[scope]
    config_dir.mkdir(parents=True, exist_ok=True)


def _get_config_path(scope: str) -> Path:
    """获取配置文件路径"""
    if scope == "mcprc":
        return MCPRC_PATH
    return CONFIG_DIR[scope] / "config.json"


def _load_config(scope: str) -> ConfigStore:
    """加载配置"""
    if scope in _config_cache:
        return _config_cache[scope]
    
    config_path = _get_config_path(scope)
    
    if not config_path.exists():
        # 创建新的空配置
        config = ConfigStore()
        if scope != "mcprc":  # mcprc文件不自动创建
            _ensure_config_dir(scope)
            _save_config(config, scope)
        return config
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = json.load(f)
        config = ConfigStore.parse_obj(config_data)
        _config_cache[scope] = config
        return config
    except Exception as e:
        print(f"加载配置文件失败: {str(e)}")
        return ConfigStore()


def _save_config(config: ConfigStore, scope: str) -> None:
    """保存配置"""
    if scope == "mcprc" and not MCPRC_PATH.exists():
        # 不自动创建mcprc文件
        return
    
    config_path = _get_config_path(scope)
    
    if scope != "mcprc":
        _ensure_config_dir(scope)
    
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config.dict(), f, indent=2, ensure_ascii=False)
        # 更新缓存
        _config_cache[scope] = config
    except Exception as e:
        print(f"保存配置文件失败: {str(e)}")


def add_server(name: str, config: dict, scope: str = "project") -> None:
    """添加服务器配置
    
    Args:
        name: 服务器名称
        config: 服务器配置
        scope: 配置作用域，默认为project
    """
    if not name:
        raise ValueError("服务器名称不能为空")
    
    # 验证服务器类型
    if "type" not in config:
        raise ValueError("服务器配置缺少type字段")
    
    if config["type"] not in ["stdio", "sse"]:
        raise ValueError(f"不支持的服务器类型: {config['type']}")
    
    # 验证SSE类型需要URL
    if config["type"] == "sse" and "url" not in config:
        raise ValueError("SSE类型服务器需要指定url")
    
    # 验证Stdio类型需要command
    if config["type"] == "stdio" and "command" not in config:
        raise ValueError("Stdio类型服务器需要指定command")
    
    # 加载配置
    config_obj = _load_config(scope)
    
    # 转换配置为Pydantic模型
    server_config = McpServerConfig(**config)
    
    # 添加服务器配置
    config_obj.mcp_servers[name] = server_config
    
    # 保存配置
    _save_config(config_obj, scope)


def remove_server(name: str, scope: str = "project") -> None:
    """删除服务器配置
    
    Args:
        name: 服务器名称
        scope: 配置作用域，默认为project
    """
    if not name:
        raise ValueError("服务器名称不能为空")
    
    # 加载配置
    config_obj = _load_config(scope)
    
    # 检查服务器是否存在
    if name not in config_obj.mcp_servers:
        return
    
    # 删除服务器配置
    del config_obj.mcp_servers[name]
    
    # 保存配置
    _save_config(config_obj, scope)


def list_servers() -> Dict[str, dict]:
    """列出所有服务器配置
    
    返回值会合并所有作用域的配置，优先级为: project > mcprc > global
    """
    # 合并结果
    merged_servers = {}
    
    # 按优先级从低到高加载配置
    scopes = ["global", "mcprc", "project"]
    
    for scope in scopes:
        try:
            config = _load_config(scope)
            for name, server in config.mcp_servers.items():
                merged_servers[name] = server.dict()
        except Exception:
            # 忽略加载失败的配置
            pass
    
    return merged_servers


def get_server(name: str) -> Optional[dict]:
    """获取指定服务器配置"""
    servers = list_servers()
    return servers.get(name)
