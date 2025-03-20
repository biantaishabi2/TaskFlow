"""
=== 文件操作工具调用规范 ===
请按照以下固定格式生成文件操作工具调用，不需要包含 id 和 role 字段，
且 tool_name 固定为 "file_operation"，具体操作类型由 parameters 中的 operation 字段决定。

格式：
{
    "tool_calls": [
        {
            "tool_name": "file_operation",
            "parameters": {
                "operation": "操作类型",       // 可选值："create"、"read" 或 "modify"
                "path": "文件路径",            // 所有操作均必填
                // 当 operation 为 "create" 时，必须同时提供：
                "content": "文件内容",
                // 当 operation 为 "modify" 时，必须同时提供：
                "original_snippet": "原始内容片段",
                "new_snippet": "新的内容片段"
            }
        }
    ]
}

示例 1：创建文件
{
    "tool_calls": [
        {
            "tool_name": "file_operation",
            "parameters": {
                "operation": "create",
                "path": "result.txt",
                "content": "Hello, file!"
            }
        }
    ]
}

示例 2：读取文件
{
    "tool_calls": [
        {
            "tool_name": "file_operation",
            "parameters": {
                "operation": "read",
                "path": "result.txt"
            }
        }
    ]
}

示例 3：修改文件
{
    "tool_calls": [
        {
            "tool_name": "file_operation",
            "parameters": {
                "operation": "modify",
                "path": "result.txt",
                "original_snippet": "old content",
                "new_snippet": "new content"
            }
        }
    ]
}

注意事项：
1. 每次调用工具前，请确保一次只调用一个工具。
2. 参数 JSON 必须与工具内部定义保持一致，不要随意更改字段名或格式。
3. 所有路径必须相对于项目根目录。
4. 调用修改操作前，建议先调用读取工具确认文件内容。
"""
import logging
from typing import Dict, Any, Optional, Tuple, ClassVar, Set
from pathlib import Path
from ..core.base_tool import BaseTool, ToolCallResult  # 使用相对导入
import json
import os

class FileOperationTool(BaseTool):
    """
    ▛▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▛
    文件操作工具类（与工作流引擎统一接口）
    
    支持的操作：
    1. 创建文件 (create)
    2. 读取文件 (read)
    3. 修改文件 (modify)
    """
    # 添加类型注解
    VALID_OPERATIONS: ClassVar[Set[str]] = {"create", "read", "modify"}
    
    def __init__(self, **data):
        # 在调用父类初始化之前准备必需的字段
        base_data = {
            "name": "file_operation",
            "description": """文件操作工具，支持创建、读取和修改文件。

使用方法:
1. 创建文件:
   {
       "tool_calls": [{
           "tool_name": "file_operation",
           "parameters": {
               "operation": "create",
               "path": "test.txt",
               "content": "要写入的内容"
           }
       }]
   }

2. 读取文件:
   {
       "tool_calls": [{
           "tool_name": "file_operation",
           "parameters": {
               "operation": "read",
               "path": "test.txt"
           }
       }]
   }

3. 修改文件:
   {
       "tool_calls": [{
           "tool_name": "file_operation",
           "parameters": {
               "operation": "modify",
               "path": "test.txt",
               "original_snippet": "原始内容",
               "new_snippet": "新内容"
           }
       }]
   }

注意事项:
1. operation 必须是 create、read 或 modify 之一
2. path 是必填参数
3. create 操作需要提供 content 参数
4. modify 操作需要提供 original_snippet 和 new_snippet 参数
5. 所有文本内容都使用 UTF-8 编码""",
            "parameters": {
                "operation": {
                    "type": "str",
                    "required": True,
                    "enum": list(self.VALID_OPERATIONS),
                    "description": "操作类型：create/read/modify"
                },
                "path": {
                    "type": "str",
                    "required": True,
                    "description": "文件路径"
                },
                "content": {
                    "type": "str",
                    "required": False,
                    "description": "创建操作时的文件内容"
                },
                "original_snippet": {
                    "type": "str",
                    "required": False,
                    "description": "修改操作时的原始内容片段"
                },
                "new_snippet": {
                    "type": "str",
                    "required": False,
                    "description": "修改操作时的新内容片段"
                }
            }
        }
        # 合并用户提供的数据和默认数据
        base_data.update(data)
        super().__init__(**base_data)

    def validate_parameters(self, params: Dict) -> Tuple[bool, str]:
        """验证参数有效性"""
        operation = params.get("operation")
        if operation not in self.VALID_OPERATIONS:
            return False, f"操作参数 'operation' 必须是 {', '.join(self.VALID_OPERATIONS)} 之一"
            
        if "path" not in params or not isinstance(params["path"], str):
            return False, "必须提供字符串类型的 'path' 参数"

        if operation == "create":
            if "content" not in params or not isinstance(params["content"], str):
                return False, "创建操作要求提供字符串类型的 'content' 参数"
        elif operation == "modify":
            for key in ("original_snippet", "new_snippet"):
                if key not in params or not isinstance(params[key], str):
                    return False, f"修改操作要求提供字符串类型的 '{key}' 参数"
        
        return True, ""

    async def execute(self, params: Dict[str, Any]) -> ToolCallResult:
        """统一执行入口"""
        # 首先验证参数
        is_valid, error_msg = self.validate_parameters(params)
        if not is_valid:
            return ToolCallResult(
                success=False,
                result=None,
                error=error_msg
            )
        
        # 根据操作类型调用相应的处理方法
        operation = params.get("operation")
        handlers = {
            "create": self._create_file,
            "read": self._read_file,
            "modify": self._apply_diff
        }
        
        handler = handlers.get(operation)
        if not handler:
            return ToolCallResult(
                success=False,
                result=None,
                error=f"无效操作类型: {operation}"
            )
            
        return await handler(params)

    async def _create_file(self, params: Dict) -> ToolCallResult:
        """创建文件"""
        try:
            path = Path(params["path"]).resolve()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(params["content"], encoding="utf-8")
            
            return ToolCallResult(
                success=True,
                result={"path": str(path)},
                error=None
            )
        except Exception as e:
            return ToolCallResult(
                success=False,
                result=None,
                error=f"创建文件失败: {str(e)}"
            )

    async def _read_file(self, params: Dict) -> ToolCallResult:
        """读取文件"""
        try:
            path = Path(params["path"]).resolve()
            if not path.exists():
                return ToolCallResult(
                    success=False,
                    result=None,
                    error=f"文件不存在: {str(path)}"
                )
                
            content = path.read_text(encoding="utf-8")
            return ToolCallResult(
                success=True,
                result={"content": content},
                error=None
            )
        except Exception as e:
            return ToolCallResult(
                success=False,
                result=None,
                error=f"读取文件失败: {str(e)}"
            )

    async def _apply_diff(self, params: Dict) -> ToolCallResult:
        """应用修改"""
        try:
            path = Path(params["path"]).resolve()
            if not path.exists():
                return ToolCallResult(
                    success=False,
                    result=None,
                    error=f"文件不存在: {str(path)}"
                )
            
            original = path.read_text(encoding="utf-8")
            if params["original_snippet"] not in original:
                return ToolCallResult(
                    success=False,
                    result=None,
                    error="原始内容片段未找到",
                )
                
            updated = original.replace(
                params["original_snippet"],
                params["new_snippet"],
                1  # 只替换第一次出现的内容
            )
            
            path.write_text(updated, encoding="utf-8")
            return ToolCallResult(
                success=True,
                result={"path": str(path)},
                error=None
            )
        except Exception as e:
            return ToolCallResult(
                success=False,
                result=None,
                error=f"修改文件失败: {str(e)}"
            )