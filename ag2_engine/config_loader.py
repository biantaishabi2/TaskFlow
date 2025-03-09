import os
import yaml
from typing import Dict, Any, Optional

def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """加载AG2执行器配置
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        配置字典
    """
    if not config_path or not os.path.exists(config_path):
        return {}
        
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"加载配置错误: {e}")
        return {}