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
from ...core.ag2_two_agent_executor import AG2TwoAgentExecutor

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
            read_timestamps: 读取时间戳字典（兼容参数，但主要使用全局时间戳）
            
        Returns:
            (是否验证通过, 错误消息)
        """
        # 导入全局时间戳字典
        from ..global_timestamps import GLOBAL_TIMESTAMPS
        
        resolved_path = str(Path(file_path).resolve())
        logging.debug(f"验证文件路径: {resolved_path}")
        
        # 检查多种可能的路径表示形式
        possible_paths = [
            resolved_path,           # 完全解析的路径
            file_path,               # 原始路径
            str(Path(file_path))     # 标准化但非绝对路径
        ]
        
        # 尝试所有可能的路径 - 优先检查全局时间戳字典
        found_timestamp = False
        read_timestamp = None
        matched_path = None
        
        # 首先尝试从全局时间戳字典获取
        for path_key in possible_paths:
            if path_key in GLOBAL_TIMESTAMPS:
                read_timestamp = GLOBAL_TIMESTAMPS[path_key]
                matched_path = path_key
                found_timestamp = True
                logging.debug(f"从全局时间戳找到匹配路径: {path_key}")
                break
                
        # 如果在全局字典中没找到，再尝试参数传递的时间戳字典
        if not found_timestamp:
            for path_key in possible_paths:
                if path_key in read_timestamps:
                    read_timestamp = read_timestamps[path_key]
                    matched_path = path_key
                    found_timestamp = True
                    logging.debug(f"从参数时间戳找到匹配路径: {path_key}")
                    break
        
        # 尝试相似路径匹配 - 首先在全局字典中查找
        if not found_timestamp:
            logging.debug("尝试全局相似路径匹配")
            for stored_path in GLOBAL_TIMESTAMPS.keys():
                if file_path in stored_path or stored_path in file_path:
                    read_timestamp = GLOBAL_TIMESTAMPS[stored_path]
                    matched_path = stored_path
                    found_timestamp = True
                    logging.debug(f"从全局时间戳找到相似路径: {stored_path}")
                    break
                    
        # 然后在参数时间戳字典中查找相似路径
        if not found_timestamp:
            for stored_path in read_timestamps.keys():
                if file_path in stored_path or stored_path in file_path:
                    read_timestamp = read_timestamps[stored_path]
                    matched_path = stored_path
                    found_timestamp = True
                    logging.debug(f"从参数时间戳找到相似路径: {stored_path}")
                    break
        
        # 如果最终都没找到，返回失败
        if not found_timestamp:
            logging.error(f"未找到任何匹配的时间戳，文件尚未被读取: {file_path}")
            return False, "文件尚未被读取，请先使用 FileReadTool 读取文件"
            
        try:
            # 检查文件是否被修改
            current_mtime = os.stat(resolved_path).st_mtime
            
            # 检查文件修改时间是否大于上次读取时间
            if current_mtime > read_timestamp:
                time_diff = current_mtime - read_timestamp
                logging.error(f"文件在读取后被修改 (差异: {time_diff:.2f} 秒): {file_path}")
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
        """验证参数有效性
        
        Args:
            params: 参数字典，可以是直接的参数字典或者包含在 params 中的参数
            context: 上下文字典
        """
        logging.debug(f"开始验证参数")
        
        # 处理嵌套参数结构
        processed_params = params
        
        # 处理 params['params'] 的情况
        if isinstance(params, dict) and 'params' in params:
            processed_params = params['params']
            
        # 处理 params['kwargs'] 的情况 (AG2TwoAgentExecutor中的格式)
        if isinstance(processed_params, dict) and 'kwargs' in processed_params:
            processed_params = processed_params['kwargs']
        
        # 首先检查context是否已存在
        if context is None and isinstance(processed_params, dict) and 'context' in processed_params:
            context = processed_params['context']
            
        # 如果仍然没有context，创建一个空的
        if context is None:
            context = {}
            
        # 检查必需参数
        required_keys = ["file_path", "old_string", "new_string"]
        missing_keys = [key for key in required_keys if key not in processed_params]
        if missing_keys:
            return False, f"缺少必需参数: {missing_keys}"
            
        # 检查参数类型
        invalid_types = [key for key in required_keys if not isinstance(processed_params[key], str)]
        if invalid_types:
            return False, f"参数类型错误: {invalid_types}"
            
        file_path = processed_params["file_path"]
        old_string = processed_params["old_string"]
        new_string = processed_params["new_string"]
        
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
        
        # 获取当前文件路径的所有可能表示
        resolved_path = str(path.resolve())
        orig_path = str(path)
        
        # 导入全局时间戳字典
        from ..global_timestamps import GLOBAL_TIMESTAMPS
        
        logging.debug(f"检查文件路径: {orig_path}, 解析路径: {resolved_path}")
        
        # 检查全局时间戳字典中的时间戳
        has_timestamp = False
        if resolved_path in GLOBAL_TIMESTAMPS:
            has_timestamp = True
            logging.debug(f"全局时间戳中找到完全匹配路径: {resolved_path}")
        elif orig_path in GLOBAL_TIMESTAMPS:
            has_timestamp = True
            logging.debug(f"全局时间戳中找到原始路径: {orig_path}")
        
        # 如果全局字典中没有时间戳，尝试其他方法
        if not has_timestamp:
            logging.debug(f"全局时间戳中未找到文件: {file_path}")
            
            # 尝试从参数中获取时间戳字典
            if context and "read_timestamps" in context:
                param_timestamps = context["read_timestamps"]
                
                # 如果参数中有时间戳，复制到全局字典中
                if file_path in param_timestamps:
                    timestamp = param_timestamps[file_path]
                    GLOBAL_TIMESTAMPS[file_path] = timestamp
                    logging.debug(f"从参数复制时间戳到全局字典: {file_path}")
                    has_timestamp = True
                elif resolved_path in param_timestamps:
                    timestamp = param_timestamps[resolved_path]
                    GLOBAL_TIMESTAMPS[resolved_path] = timestamp
                    logging.debug(f"从参数复制时间戳到全局字典: {resolved_path}")
                    has_timestamp = True
                    
            # 如果仍然没有时间戳，尝试创建一个测试时间戳（仅测试模式）
            if not has_timestamp and not any(p in GLOBAL_TIMESTAMPS for p in [resolved_path, orig_path]):
                if "TEST_MODE" in os.environ:
                    test_timestamp = os.path.getmtime(resolved_path) - 100  # 安全测试值
                    GLOBAL_TIMESTAMPS[resolved_path] = test_timestamp
                    logging.warning(f"测试模式 - 创建时间戳: {resolved_path}")
                else:
                    return False, "文件尚未被读取，请先使用 FileReadTool 读取文件"
            
        # 使用全局时间戳字典验证
        is_read, error_msg = self._verify_file_read(str(path), GLOBAL_TIMESTAMPS)
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
        
    async def execute(self, params: Dict[str, Any] = None, **kwargs) -> ToolCallResult:
        """执行文件编辑"""
        try:
            # 确保params是一个字典
            if params is None:
                params = kwargs
                
            # 保存原始参数用于可能的回退
            original_params = params.copy() if isinstance(params, dict) else {"non_dict": str(params)}
            
            # 处理嵌套的参数结构
            processed_params = params
            
            # 解包 kwargs
            if isinstance(processed_params, dict) and "kwargs" in processed_params:
                processed_params = processed_params["kwargs"]
            
            # 检查 context 参数
            if "context" not in processed_params or not isinstance(processed_params["context"], dict):
                # 如果没有 context，创建一个空的 context
                processed_params["context"] = {}
                logging.debug("在参数中创建了空的 context 字典")
            
            context = processed_params["context"]
            
            # 确保有read_timestamps字典
            if "read_timestamps" not in context:
                # 尝试从原始参数中获取
                if isinstance(original_params, dict) and "kwargs" in original_params:
                    kwargs_context = original_params["kwargs"].get("context", {})
                    if isinstance(kwargs_context, dict) and "read_timestamps" in kwargs_context:
                        logging.debug("从原始参数中恢复read_timestamps字典")
                        context["read_timestamps"] = kwargs_context["read_timestamps"]
            
            read_timestamps = context.get("read_timestamps", {})
            
            # 验证参数
            is_valid, error_msg = self.validate_parameters(processed_params, processed_params["context"])
            if not is_valid:
                logging.error(f"参数验证失败: {error_msg}")
                return ToolCallResult(
                    success=False,
                    result=None,
                    error=error_msg
                )
            
            file_path = processed_params["file_path"]
            old_string = processed_params["old_string"]
            new_string = processed_params["new_string"]
pip install -e .            
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