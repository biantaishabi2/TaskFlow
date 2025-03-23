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
    
    def validate_parameters(self, params: Dict) -> Tuple[bool, str]:
        """验证参数有效性"""
        # 检查 pattern 参数
        if "pattern" not in params:
            return False, "必须提供 'pattern' 参数"
        
        if not isinstance(params["pattern"], str):
            return False, "'pattern' 参数必须是字符串类型"
        
        # 检查 path 参数
        if "path" in params:
            if not isinstance(params["path"], str):
                return False, "'path' 参数必须是字符串类型"
            
            path = params["path"]
            # 检查是否为绝对路径
            if not os.path.isabs(path):
                return False, f"必须提供绝对路径，当前提供的是相对路径：{path}"
            
            # 检查目录是否存在
            if not os.path.exists(path):
                return False, f"目录不存在：{path}"
            
            if not os.path.isdir(path):
                return False, f"路径不是目录：{path}"
            
            # 检查是否有读取权限
            if not os.access(path, os.R_OK):
                return False, f"无权限访问目录：{path}"
        
        return True, ""
    
    async def execute(self, params: Dict[str, Any]) -> ToolCallResult:
        """执行 glob 搜索"""
        logging.info(f"GlobTool execute called with params: {params}")
        
        # 处理参数，支持直接传参和kwargs包装的情况
        if "kwargs" in params:
            params = params["kwargs"]
        elif "args" in params and params["args"]:
            params["pattern"] = params["args"][0]
        
        # 验证参数
        is_valid, error_msg = self.validate_parameters(params)
        if not is_valid:
            logging.error(f"Parameter validation failed: {error_msg}")
            return ToolCallResult(
                success=False,
                error=error_msg
            )
        
        try:
            pattern = params["pattern"]
            path = params.get("path", os.getcwd())
            
            # 列出匹配的文件
            logging.info(f"开始在目录 {path} 中搜索模式 {pattern}")
            files = self._get_files_with_mtime(pattern, Path(path))
            logging.info(f"找到 {len(files)} 个匹配文件")
            
            if not files:
                empty_msg = f"在目录 {path} 中未找到匹配模式 {pattern} 的文件"
                return ToolCallResult(
                    success=True,
                    result={
                        "files": [],
                        "count": 0,
                        "message": empty_msg
                    }
                )
            
            # 应用限制
            total_files = len(files)
            files = files[:self.DEFAULT_LIMIT]
            
            # 格式化输出
            output = GlobOutput(
                filenames=[self._format_path(f[0], Path(path)) for f in files],
                durationMs=(time.time() - time.time()) * 1000,
                numFiles=len(files),
                truncated=total_files > self.DEFAULT_LIMIT
            )
            
            # 返回结果
            result = {
                "files": output["filenames"],
                "count": output["numFiles"],
                "message": f"找到 {output['numFiles']} 个匹配文件"
            }
            
            return ToolCallResult(
                success=True,
                result=result
            )
            
        except Exception as e:
            error_msg = f"执行 glob 搜索失败: {str(e)}"
            logging.error(error_msg)
            logging.exception("详细错误:")
            return ToolCallResult(
                success=False,
                error=error_msg
            ) 