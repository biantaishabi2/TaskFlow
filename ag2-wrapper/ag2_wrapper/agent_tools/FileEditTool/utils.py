"""
FileEditTool 的工具函数
"""
from pathlib import Path
import os
from typing import Dict, Tuple, Optional
import difflib
import chardet
import re
from difflib import unified_diff

def apply_edit(file_path: str, old_string: str, new_string: str) -> Tuple[list, str]:
    """
    对文件应用编辑并返回补丁和更新后的文件内容。
    不会写入磁盘。
    
    Args:
        file_path: 文件路径
        old_string: 要替换的文本
        new_string: 新的替换文本
        
    Returns:
        Tuple[list, str]: (补丁列表, 更新后的文件内容)
        
    Raises:
        FileNotFoundError: 文件不存在
        ValueError: 编辑应用失败
    """
    if old_string == "":
        # 创建新文件
        original_file = ""
        updated_file = new_string
    else:
        # 编辑已存在的文件
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
            
        encoding = detect_file_encoding(Path(file_path))
        with open(file_path, 'r', encoding=encoding) as f:
            original_file = f.read()
            
        # 处理删除操作
        if new_string == "":
            if not old_string.endswith('\n') and old_string + '\n' in original_file:
                updated_file = original_file.replace(old_string + '\n', new_string)
            else:
                updated_file = original_file.replace(old_string, new_string)
        else:
            updated_file = original_file.replace(old_string, new_string)
            
        if updated_file == original_file:
            raise ValueError("原始文件和编辑后的文件完全相同，编辑应用失败。")
            
    # 生成补丁
    patch = list(unified_diff(
        original_file.splitlines(keepends=True),
        updated_file.splitlines(keepends=True),
        fromfile=file_path,
        tofile=file_path,
        n=3  # 上下文行数
    ))
    
    return patch, updated_file
    
def get_snippet(initial_text: str, old_str: str, new_str: str, n_lines: int = 4) -> Dict[str, any]:
    """
    获取编辑前后的文件片段。
    
    Args:
        initial_text: 原始文件内容
        old_str: 要替换的文本
        new_str: 新的替换文本
        n_lines: 上下文行数
        
    Returns:
        Dict: {
            'snippet': str,  # 编辑后的文件片段
            'start_line': int  # 片段开始行号（从1开始）
        }
    """
    # 如果是创建新文件
    if old_str == "":
        return {
            'snippet': new_str,
            'start_line': 1
        }
        
    # 找到替换位置
    before = initial_text.split(old_str)[0]
    replacement_line = before.count('\n') + 1  # 加1因为行号从1开始
    
    # 计算片段的起始和结束行
    lines = initial_text.replace(old_str, new_str).splitlines()
    start_line = max(1, replacement_line - n_lines + 1)  # 修改：加1以获得正确的起始行
    end_line = min(
        len(lines),
        replacement_line + n_lines + 1  # 修改：加1以包含完整的上下文
    )
    
    # 获取片段
    snippet_lines = lines[start_line-1:end_line]  # 因为lines是0基的，所以要减1
    snippet = '\n'.join(snippet_lines)
    
    return {
        'snippet': snippet,
        'start_line': start_line
    }
    
def detect_file_encoding(file_path: Path) -> str:
    """
    检测文件编码。
    
    Args:
        file_path: 文件路径
        
    Returns:
        str: 文件编码（如 'utf-8'）
    """
    # 读取文件的一部分来检测编码
    with open(file_path, 'rb') as f:
        raw_data = f.read(4096)  # 读取前4KB
        
    # 使用 chardet 检测编码
    result = chardet.detect(raw_data)
    encoding = result['encoding']
    
    # 如果检测失败或置信度低，默认使用 utf-8
    if not encoding or result['confidence'] < 0.6:
        return 'utf-8'
        
    return encoding.lower()
    
def detect_line_endings(file_path: Path) -> str:
    """
    检测文件的换行符类型。
    
    Args:
        file_path: 文件路径
        
    Returns:
        str: 换行符类型（'LF' 或 'CRLF'）
    """
    with open(file_path, 'rb') as f:
        content = f.read(4096)  # 读取前4KB
        
    # 计算 CRLF 和 LF 的数量
    crlf_count = content.count(b'\r\n')
    lf_count = content.count(b'\n') - crlf_count  # 减去 CRLF 中的 \n
    
    # 根据数量决定使用哪种换行符
    # 如果 CRLF 数量大于等于 LF 数量，使用 CRLF
    if crlf_count >= lf_count:
        return 'CRLF'
    return 'LF'
    
def find_similar_file(file_path: Path) -> Optional[str]:
    """
    在同一目录下查找具有相似名称的文件。
    
    Args:
        file_path: 文件路径
        
    Returns:
        Optional[str]: 相似文件的路径，如果没有找到则返回 None
    """
    if not file_path.parent.exists():
        return None
        
    # 获取文件名和扩展名
    stem = file_path.stem
    
    # 在同一目录下查找文件
    similar_files = []
    for f in file_path.parent.iterdir():
        if f.is_file() and f.stem == stem and f.suffix != file_path.suffix:
            similar_files.append(str(f))
            
    # 如果找到相似文件，返回第一个
    return similar_files[0] if similar_files else None 