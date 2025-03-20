"""
文件写入工具 - 提供安全可靠的文件写入功能
仅用于创建新文件，不支持覆盖已有文件
"""
import logging
from typing import Dict, Any, Optional, Tuple, ClassVar
from pathlib import Path
from ...core.base_tool import BaseTool, ToolCallResult
import json
import os
from datetime import datetime
from .prompt import PROMPT, DESCRIPTION

class FileWriteTool(BaseTool):
    """
    文件写入工具类 - 仅用于创建新文件
    
    特性：
    1. 仅支持创建新文件，不能覆盖已有文件
    2. 使用 UTF-8 编码
    3. 换行符自动处理
    """
    
    def __init__(self, **data):
        base_data = {
            "name": "file_write",
            "description": DESCRIPTION,
            "prompt": PROMPT,
            "parameters": {
                "path": {
                    "type": "str",
                    "required": True,
                    "description": "目标文件路径（必须是不存在的文件）"
                },
                "content": {
                    "type": "str",
                    "required": True,
                    "description": "要写入的内容"
                }
            },
            "metadata": {
                "read_only": False,
                "description": "写入工具，用于创建新文件"
            }
        }
        base_data.update(data)
        super().__init__(**base_data)
        
    def validate_parameters(self, params: Dict) -> Tuple[bool, str]:
        """验证参数有效性"""
        if "path" not in params or not isinstance(params["path"], str):
            return False, "必须提供字符串类型的 'path' 参数"
            
        if "content" not in params or not isinstance(params["content"], str):
            return False, "必须提供字符串类型的 'content' 参数"
            
        return True, ""
        
    def _normalize_newlines(self, content: str) -> str:
        """统一换行符"""
        return content.replace("\r\n", "\n").replace("\r", "\n")
        
    def _check_file_permission(self, path: Path) -> Tuple[bool, str]:
        """检查文件权限，返回 (是否有权限, 错误消息)"""
        if path.exists():
            return False, f"文件已存在，不能覆盖: {str(path)}。如果需要修改已存在的文件，请使用 EditFile 工具。"
            
        # 创建父目录（如果不存在）
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            return False, f"无权限创建目录: {str(path.parent)}"
            
        # 检查目录写入权限
        if not os.access(path.parent, os.W_OK):
            return False, f"无权限在目录下创建文件: {str(path.parent)}"
            
        return True, ""
        
    async def execute(self, params: Dict[str, Any]) -> ToolCallResult:
        """执行文件写入"""
        # 验证参数
        is_valid, error_msg = self.validate_parameters(params)
        if not is_valid:
            return ToolCallResult(
                success=False,
                result=None,
                error=error_msg
            )
            
        try:
            path = Path(params["path"]).resolve()
            content = params["content"]
            
            # 检查权限
            has_permission, error_msg = self._check_file_permission(path)
            if not has_permission:
                return ToolCallResult(
                    success=False,
                    result=None,
                    error=error_msg
                )
                
            # 处理换行符
            content = self._normalize_newlines(content)
            
            # 写入文件（使用 UTF-8 编码）
            path.write_text(content, encoding="utf-8")
            
            result = {
                "path": str(path)
            }
            
            return ToolCallResult(
                success=True,
                result=result,
                error=None
            )
            
        except PermissionError as e:
            return ToolCallResult(
                success=False,
                result=None,
                error=f"无权限: {str(e)}"
            )
        except Exception as e:
            return ToolCallResult(
                success=False,
                result=None,
                error=f"创建文件失败: {str(e)}"
            ) 