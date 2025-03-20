"""
Glob 模式文件搜索工具 - 提供快速的文件模式匹配功能
支持任意大小的代码库，返回按修改时间排序的文件路径
"""
import logging
from typing import Dict, Any, Optional, Tuple, List, TypedDict
from pathlib import Path
from ...core.base_tool import BaseTool, ToolCallResult
import glob
import os
import time
from datetime import datetime
from .prompt import PROMPT, DESCRIPTION, TOOL_NAME_FOR_PROMPT

class GlobOutput(TypedDict):
    """Glob 搜索结果类型"""
    filenames: List[str]
    durationMs: float
    numFiles: int
    truncated: bool

class GlobTool(BaseTool):
    """
    Glob 模式文件搜索工具类
    
    特性：
    1. 支持标准 glob 模式搜索
    2. 结果按修改时间排序
    3. 默认限制返回数量
    4. 支持分页加载
    5. 提供执行时间统计
    """
    
    # 默认最大返回文件数
    DEFAULT_LIMIT: int = 100
    
    def __init__(self, **data):
        base_data = {
            "name": TOOL_NAME_FOR_PROMPT,
            "description": DESCRIPTION,
            "prompt": PROMPT,
            "parameters": {
                "pattern": {
                    "type": "str",
                    "required": True,
                    "description": "要匹配的 glob 模式"
                },
                "path": {
                    "type": "str",
                    "required": False,
                    "description": "搜索的起始目录路径，默认为当前目录"
                }
            },
            "metadata": {
                "read_only": True,
                "description": "只读工具，用于文件模式匹配搜索"
            }
        }
        base_data.update(data)
        super().__init__(**base_data)
    
    def _has_read_permission(self, path: Path) -> bool:
        """检查目录是否有读取权限"""
        try:
            return os.access(path, os.R_OK)
        except Exception:
            return False
    
    def _get_files_with_mtime(self, pattern: str, base_path: Path) -> List[Tuple[str, float]]:
        """获取匹配文件及其修改时间"""
        files = []
        try:
            # 使用 glob 模块搜索文件
            for filepath in glob.glob(str(base_path / pattern), recursive=True):
                try:
                    mtime = os.path.getmtime(filepath)
                    files.append((filepath, mtime))
                except OSError:
                    continue
        except Exception as e:
            logging.warning(f"搜索文件时出错: {str(e)}")
            
        return files
    
    def _format_path(self, path: str, base_path: Path, verbose: bool = False) -> str:
        """格式化文件路径（相对路径或绝对路径）"""
        if verbose:
            return str(Path(path).resolve())
        try:
            return str(Path(path).relative_to(base_path))
        except ValueError:
            return path
    
    def _format_result_for_assistant(self, output: GlobOutput) -> str:
        """格式化返回给助手的结果"""
        if output["numFiles"] == 0:
            return "未找到匹配的文件"
            
        result = "\n".join(output["filenames"])
        if output["truncated"]:
            result += "\n(结果已截断。建议使用更具体的路径或模式。)"
            
        return result
    
    async def execute(self, params: Dict[str, Any]) -> ToolCallResult:
        """执行 glob 搜索"""
        try:
            pattern = params["pattern"]
            base_path = Path(params.get("path", os.getcwd())).resolve()
            
            # 检查目录权限
            if not self._has_read_permission(base_path):
                return ToolCallResult(
                    success=False,
                    result=None,
                    error=f"无权限访问目录: {str(base_path)}"
                )
            
            # 搜索文件并计时
            start_time = time.time()
            files = self._get_files_with_mtime(pattern, base_path)
            files.sort(key=lambda x: x[1], reverse=True)  # 按修改时间降序排序
            
            # 应用限制
            total_files = len(files)
            files = files[:self.DEFAULT_LIMIT]
            
            # 格式化输出
            output = GlobOutput(
                filenames=[self._format_path(f[0], base_path) for f in files],
                durationMs=(time.time() - start_time) * 1000,
                numFiles=len(files),
                truncated=total_files > self.DEFAULT_LIMIT
            )
            
            return ToolCallResult(
                success=True,
                result=output,
                error=None,
                result_for_assistant=self._format_result_for_assistant(output)
            )
            
        except Exception as e:
            return ToolCallResult(
                success=False,
                result=None,
                error=f"搜索文件失败: {str(e)}"
            ) 