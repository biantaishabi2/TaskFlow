"""
工具调用核心模块

架构组成：
███████████████████████████████
█ 基础定义  █ 抽象接口 █ 具体实现 █
███████████████████████████████

模块结构：
1. 数据容器 (ToolCallResult)
2. 抽象基类 (BaseTool)
3. 具体工具实现 (APICallTool)
"""

# -------------------------------- 基础依赖 ---------------------------------
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
import requests
import json
from pathlib import Path  # 添加此行以导入 Path

# ============================== 核心数据定义 ==============================
@dataclass
class ToolCallResult:
    """
    ▛▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▛
    工具调用结果容器
    
    使用示例：
    >>> success_result = ToolCallResult(True, {"data": ...})
    >>> error_result = ToolCallResult(False, None, "Timeout Error")
    
    属性说明：
    - success : 调用是否成功（布尔值）
    - result  : 成功时的返回结果（任意类型）
    - error   : 失败时的错误描述（字符串）
    ▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔
    """
    success: bool
    result: Any
    error: Optional[str] = None


# ============================== 抽象接口层 ================================
class BaseTool(ABC):
    """
    ▛▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▛
    工具抽象基类（所有具体工具的父类）
    
    继承要求：
    1. 必须实现 execute 方法
    2. 必须返回 ToolCallResult 实例
    3. 建议处理所有内部异常
    
    方法签名：
    ▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔
    @abstractmethod
    async def execute(self, params: Dict[str, Any]) -> ToolCallResult:
        \"""执行工具调用
        参数：
        - params : 参数字典，具体结构由工具类型决定
                   示例：{"url": "...", "method": "GET"}
        \"""
    """
    
    @abstractmethod
    async def execute(self, params: Dict[str, Any]) -> ToolCallResult:
        """执行工具调用"""
        pass


# ============================== 具体工具实现 ==============================
# ============================== 接口调用工具 ==============================
class APICallTool(BaseTool):
    """
    ▛▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▛
    REST API 调用工具
    
    调用流程：
    [用户代码] → [ToolManager] → APICallTool.execute() → [返回结果]
    
    参数规范：
    ▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔
    | 参数名  | 必填 | 类型   | 默认值 | 说明                  |
    |---------|------|--------|--------|-----------------------|
    | url     | 是   | str    | 无     | API端点地址           |
    | method  | 否   | str    | GET    | HTTP方法(GET/POST等)  |
    | headers | 否   | dict   | {}     | 自定义请求头          |
    | body    | 否   | dict   | None   | 请求体(JSON格式)      |
    | params  | 否   | dict   | {}     | URL查询参数           |
    """
    VALID_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}

    def __init__(self, session_manager):
        self.session_manager = session_manager
        self.session = session_manager.get_session()
        
    async def execute(self, params: Dict[str, Any]) -> ToolCallResult:
        # 参数校验
        if not (url := params.get("url")):
            return ToolCallResult(
                success=False,
                result=None,
                error="缺少必要参数: url"
            )
            
        # 参数预处理
        method = params.get("method", "GET").upper()
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            **params.get("headers", {})
        }
        
        try:
            # 构建请求参数
            request_args = {
                "method": method,
                "url": url,
                "headers": headers
            }
            
            # 根据请求方法添加相应参数
            if method in {"POST", "PUT", "PATCH", "DELETE"}:
                request_args["json"] = params.get("body")
            else:
                request_args["params"] = params.get("params", {})
     
            # 获取会话并执行请求
            response = self.session.request(**request_args)
            response.raise_for_status()
            
            # 处理响应数据
            try:
                result = response.json() if response.content else {}
            except json.JSONDecodeError:
                # 如果不是JSON格式，返回文本内容
                result = {"text": response.text}
            
            return ToolCallResult(
                success=True,
                result=result,
                error=None
            )
            
        except requests.exceptions.RequestException as e:
            return ToolCallResult(
                success=False,
                result=None,
                error=f"请求异常: {str(e)}"
            )
        except Exception as e:
            return ToolCallResult(
                success=False,
                result=None,
                error=f"未知错误: {str(e)}"
            )

    def validate_parameters(self, params: Dict) -> Tuple[bool, str]:
        # 具体到缺失哪个参数
        missing = [p for p in ["url", "method"] if p not in params]
        if missing:
            return False, f"缺少必要参数: {', '.join(missing)}"
            
        method = params["method"].upper()
        if method not in self.VALID_METHODS:
            return False, f"非法的HTTP方法: {method}，允许的方法: {', '.join(sorted(self.VALID_METHODS))}"
            
        return True, ""
    

# ============================== 文件操作工具 ==============================
class FileOperationTool(BaseTool):  # 修改类名
    """
    ▛▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▛
    文件操作工具类（与工作流引擎统一接口）
    
    支持的操作：
    1. 创建文件 (create)
    2. 读取文件 (read)
    3. 修改文件 (modify)
    
    使用方式：
    >>> tool = FileOperationTool()
    >>> await tool.execute({
    ...     "operation": "create",
    ...     "path": "test.txt",
    ...     "content": "Hello World"
    ... })
    """
    def validate_parameters(self, params: Dict) -> Tuple[bool, str]:
        operation = params.get("operation")
        if operation not in ("create", "read", "modify"):
            return False, "操作参数 'operation' 必须是 'create'、'read' 或 'modify'"
        if "path" not in params or not isinstance(params["path"], str):
            return False, "必须提供字符串类型的 'path' 参数"

        if operation == "create":
            if "content" not in params or not isinstance(params["content"], str):
                return False, "创建操作要求提供字符串类型的 'content' 参数"
        elif operation == "modify":
            for key in ("original_snippet", "new_snippet"):
                if key not in params or not isinstance(params[key], str):
                    return False, f"修改操作要求提供字符串类型的 '{key}' 参数"
        # 对于 'read' 操作，可以根据实际需求增加额外的参数校验
        return True, ""

    async def execute(self, params: Dict[str, Any]) -> ToolCallResult:
        """统一执行入口"""
        operation = params.get("operation")
        handlers = {
            "create": self._create_file,
            "read": self._read_file,
            "modify": self._apply_diff
        }
        
        if not operation or operation not in handlers:
            return ToolCallResult(False, None, f"无效操作类型: {operation}")
            
        return await handlers[operation](params)

    async def _create_file(self, params: Dict) -> ToolCallResult:
        """创建文件"""
        if not (path := params.get("path")) or "content" not in params:
            return ToolCallResult(False, None, "缺少必要参数: path 或 content")
            
        try:
            final_path = Path(path).resolve()
            final_path.parent.mkdir(parents=True, exist_ok=True)
            final_path.write_text(params["content"], encoding="utf-8")
            return ToolCallResult(True, {"path": str(final_path)})
        except Exception as e:
            return ToolCallResult(False, None, f"创建失败: {str(e)}")

    async def _read_file(self, params: Dict) -> ToolCallResult:
        """读取文件"""
        if not (path := params.get("path")):
            return ToolCallResult(False, None, "缺少必要参数: path")
            
        try:
            final_path = Path(path).resolve()
            if not final_path.exists():
                return ToolCallResult(False, None, f"文件不存在: {path}")
                
            content = final_path.read_text(encoding="utf-8")
            return ToolCallResult(True, {"content": content})
        except Exception as e:
            return ToolCallResult(False, None, f"读取失败: {str(e)}")

    async def _apply_diff(self, params: Dict) -> ToolCallResult:
        """应用修改"""
        required = ["path", "original_snippet", "new_snippet"]
        if missing := [p for p in required if p not in params]:
            return ToolCallResult(False, None, f"缺少参数: {', '.join(missing)}")
            
        try:
            final_path = Path(params["path"]).resolve()
            original = final_path.read_text(encoding="utf-8")
            
            if params["original_snippet"] not in original:
                return ToolCallResult(
                    False,
                    None,
                    "原始片段未找到",
                    details={
                        "expected": params["original_snippet"],
                        "actual": original
                    }
                )
                
            updated = original.replace(
                params["original_snippet"],
                params["new_snippet"],
                1
            )
            final_path.write_text(updated, encoding="utf-8")
            return ToolCallResult(True, {"path": str(final_path)})
        except Exception as e:
            return ToolCallResult(False, None, f"修改失败: {str(e)}")
