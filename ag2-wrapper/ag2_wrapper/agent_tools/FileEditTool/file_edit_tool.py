"""
文件编辑工具 - 提供安全可靠的文件编辑功能
用于编辑已存在的文件内容
"""
import logging
from typing import Dict, Any, Optional, Tuple, ClassVar
from pathlib import Path
from ...core.base_tool import BaseTool, ToolCallResult
import json
import os
from datetime import datetime
from .prompt import PROMPT, DESCRIPTION
from .utils import (
    apply_edit,
    get_snippet,
    detect_file_encoding,
    detect_line_endings,
    find_similar_file
)

# 在结果消息中包含的上下文行数
N_LINES_SNIPPET = 4

class FileEditTool(BaseTool):
    """
    文件编辑工具类 - 用于编辑已存在的文件
    
    特性：
    1. 仅支持编辑已存在的文件
    2. 要求先使用 FileReadTool 读取文件
    3. 每次调用只能修改一个实例
    4. 自动处理文件编码和换行符
    5. 支持文件修改时间戳验证
    """
    
    def __init__(self, **data):
        base_data = {
            "name": "file_edit",
            "description": DESCRIPTION,
            "prompt": PROMPT,
            "parameters": {
                "file_path": {
                    "type": "str",
                    "required": True,
                    "description": "目标文件的绝对路径"
                },
                "old_string": {
                    "type": "str",
                    "required": True,
                    "description": "要替换的文本内容（必须在文件中唯一存在）"
                },
                "new_string": {
                    "type": "str",
                    "required": True,
                    "description": "新的文本内容"
                }
            },
            "metadata": {
                "read_only": False,
                "description": "编辑工具，用于修改现有文件内容"
            }
        }
        base_data.update(data)
        super().__init__(**base_data)
        
    def _verify_file_read(self, file_path: str, read_timestamps: Dict[str, float]) -> Tuple[bool, str]:
        """验证文件是否已被读取且未被修改
        
        Args:
            file_path: 文件路径
            read_timestamps: 读取时间戳字典
            
        Returns:
            (是否验证通过, 错误消息)
        """
        read_timestamp = read_timestamps.get(file_path)
        
        if not read_timestamp:
            return False, "文件尚未被读取，请先使用 FileReadTool 读取文件"
            
        try:
            stats = os.stat(file_path)
            if stats.st_mtime > read_timestamp:
                return False, "文件在读取后被修改，请重新读取文件"
        except Exception as e:
            return False, f"检查文件状态失败: {str(e)}"
            
        return True, ""
        
    def _verify_unique_match(self, content: str, old_string: str) -> Tuple[bool, str]:
        """验证要替换的内容在文件中是否唯一存在
        
        Args:
            content: 文件内容
            old_string: 要替换的文本
            
        Returns:
            (是否验证通过, 错误消息)
        """
        if old_string not in content:
            return False, "要替换的内容在文件中不存在"
            
        matches = content.count(old_string)
        if matches > 1:
            return False, f"找到 {matches} 处匹配。为了安全起见，此工具每次只能替换一处。请添加更多上下文后重试。"
            
        return True, ""
        
    def validate_parameters(self, params: Dict, context: Optional[Dict] = None) -> Tuple[bool, str]:
        """验证参数有效性"""
        # 检查必需参数
        if not all(key in params for key in ["file_path", "old_string", "new_string"]):
            return False, "缺少必需参数"
            
        # 检查参数类型
        if not all(isinstance(params[key], str) for key in ["file_path", "old_string", "new_string"]):
            return False, "参数类型错误"
            
        file_path = params["file_path"]
        old_string = params["old_string"]
        new_string = params["new_string"]
        
        # 检查是否有实际修改
        if old_string == new_string:
            return False, "old_string 和 new_string 完全相同，没有需要修改的内容"
            
        path = Path(file_path).resolve()
        
        # 处理新文件创建的情况
        if old_string == "":
            if path.exists():
                return False, "无法创建新文件 - 文件已存在"
            return True, ""
            
        # 检查文件是否存在
        if not path.exists():
            similar_file = find_similar_file(path)
            message = "文件不存在"
            if similar_file:
                message += f"，是否要找的是 {similar_file}？"
            return False, message
            
        # 检查文件是否已被读取（时间戳验证）
        read_timestamps = context.get('read_timestamps', {})
        is_read, error_msg = self._verify_file_read(str(path), read_timestamps)
        if not is_read:
            return False, error_msg
            
        # 检查替换内容的唯一性
        try:
            with open(file_path, 'r', encoding=detect_file_encoding(path)) as f:
                content = f.read()
                
            is_unique, error_msg = self._verify_unique_match(content, old_string)
            if not is_unique:
                return False, error_msg
                
        except Exception as e:
            return False, f"检查文件内容失败: {str(e)}"
            
        return True, ""
        
    def _normalize_newlines(self, content: str) -> str:
        """统一换行符"""
        return content.replace("\r\n", "\n").replace("\r", "\n")
        
    def _check_file_permission(self, path: Path) -> Tuple[bool, str]:
        """检查文件权限，返回 (是否有权限, 错误消息)"""
        if not path.exists():
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
            except PermissionError:
                return False, f"无权限创建目录: {str(path.parent)}"
                
        if path.exists() and not os.access(path, os.W_OK):
            return False, f"无权限写入文件: {str(path)}"
            
        return True, ""
        
    async def execute(self, params: Dict[str, Any], context: Optional[Dict] = None) -> ToolCallResult:
        """执行文件编辑"""
        # 检查 context 参数
        if "context" not in params or not isinstance(params["context"], dict):
            return ToolCallResult(
                success=False,
                result=None,
                error="必须在 params 中提供包含 read_timestamps 字典的 context 参数"
            )
            
        context = params["context"]
        if "read_timestamps" not in context:
            context["read_timestamps"] = {}
            
        # 验证参数
        is_valid, error_msg = self.validate_parameters(params, context)
        if not is_valid:
            return ToolCallResult(
                success=False,
                result=None,
                error=error_msg
            )
            
        try:
            file_path = params["file_path"]
            old_string = params["old_string"]
            new_string = params["new_string"]
            
            # 检查文件权限
            path = Path(file_path)
            has_permission, error_msg = self._check_file_permission(path)
            if not has_permission:
                return ToolCallResult(
                    success=False,
                    result=None,
                    error=error_msg
                )
                
            # 应用编辑
            patch, updated_file = apply_edit(file_path, old_string, new_string)
            
            # 获取编辑片段
            snippet_info = get_snippet(
                updated_file,
                old_string,
                new_string,
                N_LINES_SNIPPET
            )
            
            # 写入文件
            encoding = detect_file_encoding(path) if path.exists() else "utf-8"
            line_endings = detect_line_endings(path) if path.exists() else "LF"
            path.write_text(updated_file, encoding=encoding)
            
            # 更新读取时间戳为文件的最新修改时间
            read_timestamps = context["read_timestamps"]
            read_timestamps[str(path)] = os.stat(str(path)).st_mtime
            
            result = {
                "file_path": file_path,
                "old_string": old_string,
                "new_string": new_string,
                "patch": patch,
                "snippet": snippet_info["snippet"],
                "start_line": snippet_info["start_line"]
            }
            
            return ToolCallResult(
                success=True,
                result=result,
                error=None
            )
            
        except Exception as e:
            return ToolCallResult(
                success=False,
                result=None,
                error=f"编辑文件失败: {str(e)}"
            ) 