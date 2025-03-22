"""
全局时间戳字典模块
提供一个全局共享的时间戳字典，用于在工具之间共享文件读取时间戳
"""
import logging
from pathlib import Path

# 创建全局时间戳字典
GLOBAL_TIMESTAMPS = {}

def clear_timestamps():
    """清空时间戳字典"""
    GLOBAL_TIMESTAMPS.clear()
    logging.info("全局时间戳字典已清空")

def set_timestamp(file_path, timestamp):
    """设置文件的时间戳"""
    # 尝试规范化路径
    normalized_path = str(Path(file_path).resolve())
    GLOBAL_TIMESTAMPS[normalized_path] = timestamp
    logging.info(f"设置时间戳: {normalized_path} -> {timestamp}")

def get_timestamp(file_path):
    """获取文件的时间戳"""
    # 尝试规范化路径
    normalized_path = str(Path(file_path).resolve())
    
    if normalized_path in GLOBAL_TIMESTAMPS:
        timestamp = GLOBAL_TIMESTAMPS[normalized_path]
        logging.info(f"获取时间戳: {normalized_path} -> {timestamp}")
        return timestamp
        
    # 尝试原始路径
    if file_path in GLOBAL_TIMESTAMPS:
        timestamp = GLOBAL_TIMESTAMPS[file_path]
        logging.info(f"获取时间戳(原始路径): {file_path} -> {timestamp}")
        return timestamp
        
    logging.info(f"时间戳不存在: {normalized_path}")
    return None

def dump_timestamps():
    """打印所有时间戳（用于调试）"""
    logging.info(f"时间戳字典内容 ({len(GLOBAL_TIMESTAMPS)} 项):")
    for path, ts in GLOBAL_TIMESTAMPS.items():
        logging.info(f"  {path}: {ts}")
    return GLOBAL_TIMESTAMPS