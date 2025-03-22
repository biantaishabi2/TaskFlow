"""
文件读取工具 - 提供安全可靠的文件读取功能
支持文本和图片文件的读取，并提供相应的限制和优化
"""
import logging
from typing import Dict, Any, Optional, Tuple, ClassVar, Union, List, Set
from pathlib import Path
from ...core.base_tool import BaseTool, ToolCallResult
import json
import os
from datetime import datetime
import base64
from .prompt import PROMPT, DESCRIPTION, MAX_LINES_TO_READ, MAX_LINE_LENGTH

# 检查 PIL 是否可用
try:
    from PIL import Image
    import io
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False

class FileReadTool(BaseTool):
    """
    文件读取工具类
    
    特性：
    1. 支持文本和图片文件读取
    2. 自动处理文件编码
    3. 提供文件大小和读取行数限制
    4. 支持分段读取大文件
    5. 图片自动压缩和尺寸调整
    6. 跟踪文件读取时间戳
    """
    
    # PIL 库是否可用
    HAS_PIL: ClassVar[bool] = _HAS_PIL
    
    # 文件大小限制（字节）
    TEXT_FILE_SIZE_LIMIT: ClassVar[float] = 0.25 * 1024 * 1024  # 0.25MB
    IMAGE_FILE_SIZE_LIMIT: ClassVar[float] = 3.75 * 1024 * 1024  # 3.75MB
    
    # 图片处理限制
    MAX_IMAGE_WIDTH: ClassVar[int] = 2000
    MAX_IMAGE_HEIGHT: ClassVar[int] = 2000
    
    # 支持的图片格式
    IMAGE_EXTENSIONS: ClassVar[Set[str]] = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}
    
    def __init__(self, **data):
        base_data = {
            "name": "file_read",
            "description": DESCRIPTION,
            "prompt": PROMPT,
            "parameters": {
                "file_path": {
                    "type": "str",
                    "required": True,
                    "description": "要读取的文件路径"
                },
                "start_line": {
                    "type": "int",
                    "required": False,
                    "description": "起始行号（从1开始）"
                },
                "end_line": {
                    "type": "int",
                    "required": False,
                    "description": "结束行号（包含该行）"
                },
                "context": {
                    "type": "object",
                    "required": True,
                    "description": "包含 read_timestamps 字典的上下文对象",
                    "properties": {
                        "read_timestamps": {
                            "type": "object",
                            "description": "文件读取时间戳记录"
                        }
                    }
                }
            },
            "metadata": {
                "read_only": True,
                "description": "只读工具，用于安全地读取文件内容"
            }
        }
        base_data.update(data)
        super().__init__(**base_data)
        
    def validate_parameters(self, params: Dict) -> Tuple[bool, str]:
        """验证参数有效性"""
        if "file_path" not in params or not isinstance(params["file_path"], str):
            return False, "必须提供 file_path 参数"
            
        path = Path(params["file_path"]).resolve()
        
        # 检查文件是否存在
        if not path.exists():
            similar_file = self._find_similar_file(path)
            message = "文件不存在"
            if similar_file:
                message += f"，是否要找的是：{similar_file}？"
            return False, message
            
        # 检查文件大小
        file_size = path.stat().st_size
        if not self._is_image_file(path):
            if file_size > self.TEXT_FILE_SIZE_LIMIT and not (params.get("start_line") or params.get("end_line")):
                return False, f"文件过大 ({file_size/1024:.1f}KB)，请使用 start_line 和 end_line 参数分段读取"
                
        return True, ""
        
    def _check_file_permission(self, path: Path) -> Tuple[bool, str]:
        """检查文件读取权限"""
        try:
            if not path.exists():
                return False, "文件不存在"
            if not os.access(path, os.R_OK):
                return False, "无文件读取权限"
            return True, ""
        except Exception as e:
            return False, f"权限检查失败: {str(e)}"
        
    def _is_image_file(self, path: Path) -> bool:
        """判断是否为图片文件"""
        return path.suffix.lower() in self.IMAGE_EXTENSIONS
        
    def _find_similar_file(self, path: Path) -> Optional[str]:
        """查找相似文件名（当文件不存在时）"""
        try:
            # 获取文件名和父目录
            parent = path.parent
            name = path.stem
            
            # 如果父目录不存在，直接返回
            if not parent.exists():
                return None
                
            # 获取同目录下的所有文件
            files = [f for f in parent.iterdir() if f.is_file()]
            
            # 查找前缀匹配的文件
            similar_files = [f for f in files if f.stem.startswith(name) or name.startswith(f.stem)]
            
            # 如果找到相似文件，返回第一个
            if similar_files:
                return str(similar_files[0])
                
            return None
        except Exception as e:
            logging.error(f"查找相似文件失败: {str(e)}")
            return None
            
    def _read_text_file(self, path: Path, start_line: int = None, end_line: int = None) -> Tuple[str, Dict]:
        """读取文本文件内容"""
        try:
            # 读取所有行
            with path.open('r', encoding='utf-8') as f:
                all_lines = f.readlines()
                
            total_lines = len(all_lines)
            
            # 处理 start_line 和 end_line
            start_idx = (start_line - 1) if start_line is not None else 0
            end_idx = min(start_idx + (end_line or MAX_LINES_TO_READ), total_lines)
            
            # 截取指定范围的行
            selected_lines = all_lines[start_idx:end_idx]
            
            # 处理行长度限制
            processed_lines = []
            for line in selected_lines:
                if len(line) > MAX_LINE_LENGTH:
                    processed_lines.append(line[:MAX_LINE_LENGTH] + "...\n")
                else:
                    processed_lines.append(line)
                    
            content = "".join(processed_lines)
            
            return content, {
                "line_count": len(processed_lines),
                "total_lines": total_lines,
                "start_line": start_line or 1,
                "end_line": end_line or total_lines
            }
            
        except Exception as e:
            logging.error(f"读取文本文件失败: {str(e)}")
            raise
            
    def _read_image_file(self, path: Path) -> Tuple[bytes, Dict]:
        """读取并处理图片文件"""
        if not self.HAS_PIL:
            # 如果没有 PIL，直接返回原始图片数据
            with path.open('rb') as f:
                return f.read(), {}
                
        try:
            # 读取图片
            img = Image.open(path)
            
            # 获取原始尺寸
            width, height = img.size
            
            # 检查是否需要调整大小
            if width > self.MAX_IMAGE_WIDTH or height > self.MAX_IMAGE_HEIGHT:
                # 计算缩放比例
                ratio = min(self.MAX_IMAGE_WIDTH / width, self.MAX_IMAGE_HEIGHT / height)
                new_width = int(width * ratio)
                new_height = int(height * ratio)
                
                # 调整图片大小
                img = img.resize((new_width, new_height), Image.LANCZOS)
                
            # 转换为字节
            buffer = io.BytesIO()
            
            # 如果文件大小超过限制，使用 JPEG 格式并降低质量
            if path.stat().st_size > self.IMAGE_FILE_SIZE_LIMIT:
                img = img.convert('RGB')
                img.save(buffer, format='JPEG', quality=80, optimize=True)
            else:
                img.save(buffer, format=img.format or 'PNG')
                
            return buffer.getvalue(), {
                "original_size": (width, height),
                "final_size": img.size
            }
            
        except Exception as e:
            logging.error(f"处理图片文件失败: {str(e)}")
            # 如果处理失败，返回原始图片
            with path.open('rb') as f:
                return f.read(), {}
                
    def _format_result(self, content: Union[str, bytes], file_path: str, is_image: bool = False, 
                      line_count: int = 0, total_lines: int = 0, start_line: int = 1, end_line: int = 0) -> Dict:
        """格式化返回结果"""
        if is_image:
            return {
                "type": "image",
                "file": {
                    "base64": base64.b64encode(content).decode('utf-8'),
                    "type": f"image/{Path(file_path).suffix[1:]}"
                }
            }
        else:
            return {
                "type": "text",
                "file": {
                    "filePath": file_path,
                    "content": content,
                    "numLines": line_count,
                    "startLine": start_line,
                    "endLine": end_line,
                    "totalLines": total_lines
                }
            }
        
    def _verify_file_read(self, file_path: str, read_timestamps: Dict[str, float]) -> Tuple[bool, str]:
        """
        验证文件是否已被读取且未被修改
        
        Args:
            file_path: 文件路径
            read_timestamps: 文件读取时间戳字典
            
        Returns:
            Tuple[bool, str]: (是否验证通过, 错误信息)
        """
        # 检查文件是否被读取过
        last_read = read_timestamps.get(file_path)
        if last_read is None:
            return False, "文件尚未被读取"
            
        try:
            # 检查文件是否被修改
            current_mtime = os.path.getmtime(file_path)
            if current_mtime > last_read:
                return False, "文件在上次读取后被修改"
                
            return True, ""
        except Exception as e:
            return False, f"文件状态检查失败: {str(e)}"
            
    async def execute(self, params: Dict[str, Any], context: Optional[Dict] = None) -> ToolCallResult:
        """执行文件读取"""
        try:
            # 0. 检查context参数
            if "context" not in params or not isinstance(params["context"], dict):
                return ToolCallResult(
                    success=False,
                    result=None,
                    error="必须在 params 中提供包含 read_timestamps 字典的 context 参数"
                )
                
            context = params["context"]
            if "read_timestamps" not in context:
                context["read_timestamps"] = {}
                
            # 1. 参数验证
            is_valid, error_msg = self.validate_parameters(params)
            if not is_valid:
                return ToolCallResult(
                    success=False,
                    result=None,
                    error=error_msg
                )
                
            # 获取参数
            path = Path(params["file_path"]).resolve()
            start_line = params.get("start_line")
            end_line = params.get("end_line")
            
            # 2. 权限检查
            has_permission, error_msg = self._check_file_permission(path)
            if not has_permission:
                return ToolCallResult(
                    success=False,
                    result=None,
                    error=error_msg
                )
                
            # 3. 根据文件类型选择读取方式
            try:
                # 获取时间戳字典
                read_timestamps = context["read_timestamps"]
                
                # 更新读取时间戳
                read_timestamps[str(path)] = datetime.now().timestamp()
                
                if self._is_image_file(path):
                    content, metadata = self._read_image_file(path)
                    result = self._format_result(
                        content=content,
                        file_path=str(path),
                        is_image=True
                    )
                else:
                    content, metadata = self._read_text_file(path, start_line, end_line)
                    result = self._format_result(
                        content=content,
                        file_path=str(path),
                        is_image=False,
                        line_count=metadata["line_count"],
                        total_lines=metadata["total_lines"],
                        start_line=metadata["start_line"],
                        end_line=metadata["end_line"]
                    )
                    
                return ToolCallResult(
                    success=True,
                    result=result,
                    error=None
                )
                
            except Exception as e:
                return ToolCallResult(
                    success=False,
                    result=None,
                    error=f"读取文件失败: {str(e)}"
                )
                
        except Exception as e:
            return ToolCallResult(
                success=False,
                result=None,
                error=f"执行失败: {str(e)}"
            ) 