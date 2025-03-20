"""
文件内容搜索工具 - 提供高效的正则表达式搜索功能
基于ripgrep实现快速文件内容搜索
"""
import logging
import subprocess
import time
from typing import Dict, Any, Optional, Tuple, List
from pathlib import Path
import os
import json
from datetime import datetime
from pydantic import Field
from ...core.base_tool import BaseTool, ToolCallResult
from .prompt import PROMPT, DESCRIPTION

class GrepTool(BaseTool):
    """
    文件内容搜索工具类
    
    特性：
    1. 使用ripgrep进行高效搜索
    2. 支持完整的正则表达式语法
    3. 支持文件类型过滤
    4. 结果按修改时间排序
    5. 默认限制返回100个结果
    """
    
    # 添加类属性声明
    max_results: int = Field(default=100, description="最大返回结果数")
    is_test: bool = Field(default=False, description="测试模式标志")
    
    def __init__(self, **data):
        base_data = {
            "name": "grep",
            "description": DESCRIPTION,
            "prompt": PROMPT,
            "parameters": {
                "pattern": {
                    "type": "str",
                    "required": True,
                    "description": "正则表达式搜索模式"
                },
                "path": {
                    "type": "str",
                    "required": False,
                    "description": "搜索目录，默认为当前工作目录"
                },
                "include": {
                    "type": "str",
                    "required": False,
                    "description": "要包含的文件类型（例如：*.py）"
                }
            },
            "metadata": {
                "read_only": True,
                "description": "只读工具，用于文件内容搜索"
            }
        }
        base_data.update(data)
        super().__init__(**base_data)
        
        # 设置测试模式
        if os.getenv("NODE_ENV") == "test":
            self.is_test = True
        
    def validate_parameters(self, params: Dict) -> Tuple[bool, str]:
        """验证参数有效性"""
        if "pattern" not in params or not isinstance(params["pattern"], str):
            return False, "必须提供字符串类型的 'pattern' 参数"
            
        if "path" in params and not isinstance(params["path"], str):
            return False, "'path' 参数必须是字符串类型"
            
        if "include" in params and not isinstance(params["include"], str):
            return False, "'include' 参数必须是字符串类型"
            
        return True, ""
        
    def _check_search_permission(self, path: Path) -> Tuple[bool, str]:
        """检查搜索权限，返回 (是否有权限, 错误消息)"""
        if not path.exists():
            return False, f"目录不存在: {str(path)}"
            
        if not path.is_dir():
            return False, f"路径不是目录: {str(path)}"
            
        if not os.access(path, os.R_OK):
            return False, f"无权限读取目录: {str(path)}"
            
        return True, ""
        
    def _sort_results(self, files: List[Path]) -> List[str]:
        """对结果进行排序"""
        # 获取文件状态信息
        file_stats = []
        for file_path in files:
            try:
                stat = file_path.stat()
                file_stats.append((str(file_path), stat.st_mtime))
            except Exception:
                continue
                
        if self.is_test:
            # 测试模式下仅按文件名排序，确保结果确定性
            return sorted(str(f) for f, _ in file_stats)
        else:
            # 正常模式下按修改时间排序，同时间按文件名排序
            return [
                f for f, _ in sorted(
                    file_stats,
                    key=lambda x: (-x[1], x[0])  # 按mtime降序，文件名升序
                )
            ]
            
    def _run_ripgrep(self, pattern: str, path: str, include: Optional[str] = None) -> List[str]:
        """执行ripgrep搜索"""
        # 不使用 -F 参数保持正则表达式搜索功能
        cmd = ["rg", "-l", "-a", "--no-ignore"]  # -l 只列出文件名，-a 搜索所有文件，--no-ignore 忽略.gitignore
        if include:
            cmd.extend(["--glob", include])
            
        cmd.append(pattern)
            
        logging.info(f"执行命令: {' '.join(cmd)} in {path}")
        logging.info(f"当前工作目录: {os.getcwd()}")
        logging.info(f"目标目录内容: {os.listdir(path)}")
        
        try:
            result = subprocess.run(
                cmd,
                cwd=path,
                capture_output=True,
                text=True,
                check=False  # 不要因为没有匹配就抛出异常
            )
            
            logging.info(f"命令返回码: {result.returncode}")
            logging.info(f"命令标准输出: {result.stdout}")
            logging.info(f"命令标准错误: {result.stderr}")
            
            # 检查是否为无效的正则表达式
            if result.returncode == 2 and "regex syntax error" in result.stderr:
                logging.error(f"无效的正则表达式: {pattern}")
                raise RuntimeError(f"搜索失败: 无效的正则表达式: {pattern}")
                
            if result.returncode not in [0, 1]:  # 1表示没有匹配
                logging.error(f"ripgrep错误: {result.stderr}")
                raise RuntimeError(f"ripgrep搜索失败: {result.stderr}")
                
            # 保持相对路径
            matches = [line.strip() for line in result.stdout.splitlines()]
            logging.info(f"找到 {len(matches)} 个匹配: {matches}")
            return matches
            
        except Exception as e:
            logging.error(f"执行ripgrep时出错: {str(e)}")
            raise
            
    def _format_result_for_assistant(self, result: Dict[str, Any]) -> str:
        """格式化结果用于Assistant显示"""
        if result["numFiles"] == 0:
            return "未找到匹配文件"
            
        output = f"找到 {result['numFiles']} 个文件\n"
        output += "\n".join(result["filenames"][:self.max_results])
        
        if result["numFiles"] > self.max_results:
            output += "\n(结果已截断。建议使用更具体的路径或模式。)"
            
        return output
        
    async def execute(self, params: Dict[str, Any]) -> ToolCallResult:
        """执行文件内容搜索"""
        # 验证参数
        is_valid, error_msg = self.validate_parameters(params)
        if not is_valid:
            return ToolCallResult(
                success=False,
                error=error_msg
            )
            
        try:
            start_time = time.time()
            
            # 获取搜索路径
            search_path = Path(params.get("path", ".")).resolve()
            
            # 检查权限
            has_permission, error_msg = self._check_search_permission(search_path)
            if not has_permission:
                return ToolCallResult(
                    success=False,
                    error=error_msg
                )
            
            # 检查正则表达式是否有效
            pattern = params["pattern"]
            try:
                import re
                re.compile(pattern)
            except re.error:
                return ToolCallResult(
                    success=False,
                    error=f"搜索失败: 无效的正则表达式: {pattern}"
                )
                
            # 执行ripgrep搜索
            try:
                matches = self._run_ripgrep(
                    params["pattern"],
                    str(search_path),
                    params.get("include")
                )
            except Exception as e:
                return ToolCallResult(
                    success=False,
                    error=str(e)
                )
                
            # 对结果进行排序
            sorted_matches = self._sort_results([Path(os.path.join(str(search_path), m)) for m in matches])
            
            # 截断结果
            truncated = len(sorted_matches) > self.max_results
            if truncated:
                sorted_matches = sorted_matches[:self.max_results]
            
            # 准备结果
            result = {
                "durationMs": int((time.time() - start_time) * 1000),
                "numFiles": len(sorted_matches),
                "filenames": sorted_matches,
                "truncated": truncated
            }
            
            return ToolCallResult(
                success=True,
                result=result,
                error=None
            )
            
        except Exception as e:
            logging.error(f"搜索失败: {str(e)}")
            return ToolCallResult(
                success=False,
                error=f"搜索失败: {str(e)}"
            ) 