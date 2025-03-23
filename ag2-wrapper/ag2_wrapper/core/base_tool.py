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
from typing import Dict, Any, Optional, Tuple, ClassVar, Set
from pydantic import BaseModel, Field  # 添加Pydantic
import requests
import json
from pathlib import Path  # 添加此行以导入 Path

# ============================== 核心数据定义 ==============================
class ToolCallResult(BaseModel):
    """
    ▛▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▛
    工具调用结果容器（Pydantic版本）
    """
    success: bool = Field(..., description="调用是否成功")
    result: Optional[Any] = Field(None, description="成功时的返回结果")
    error: Optional[str] = Field(None, description="失败时的错误描述")


# ============================== 抽象接口层 ================================
class BaseTool(BaseModel, ABC):
    """
    ▛▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▛
    工具抽象基类（Pydantic兼容版本）
    """
    name: str = Field(..., description="工具名称")
    description: str = Field(..., description="工具功能描述")
    parameters: Optional[Dict[str, Any]] = Field(None, description="工具参数定义")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="工具元数据，用于存储工具的额外属性如只读标记等")

    class Config:
        arbitrary_types_allowed = True

    @abstractmethod
    async def execute(self, **kwargs):
        """工具执行方法"""
        raise NotImplementedError

    def execute_sync(self, params=None, context=None):
        """工具同步执行方法，使用新的事件循环同步运行异步execute方法
        
        参数:
            params: Dict[str, Any] - 工具参数字典，用户提供的参数
            context: Optional[Dict] - 执行上下文，包含如read_timestamps等系统状态信息
            
        返回:
            ToolCallResult - 工具执行结果
        """
        import asyncio
        import nest_asyncio
        
        try:
            # 处理参数格式
            kwargs = {}
            if params is not None:
                if isinstance(params, dict):
                    kwargs = params
                else:
                    # 尝试从其他格式转换
                    try:
                        kwargs = dict(params)
                    except:
                        kwargs = {"params": params}
            
            # 添加上下文参数
            if context is not None:
                kwargs["context"] = context
            
            # 处理嵌套事件循环
            try:
                # 如果当前有事件循环，使用nest_asyncio允许嵌套
                current_loop = asyncio.get_event_loop()
                if current_loop.is_running():
                    nest_asyncio.apply(current_loop)
                    result = asyncio.run(self.execute(**kwargs))
                else:
                    # 没有运行中的事件循环时正常执行
                    result = asyncio.run(self.execute(**kwargs))
            except RuntimeError:
                # 如果获取当前事件循环失败，创建一个新的
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                nest_asyncio.apply(new_loop)
                result = asyncio.run(self.execute(**kwargs))
            
            return result
        except Exception as e:
            import logging
            logging.error(f"同步执行工具 {self.name} 失败: {str(e)}")
            return ToolCallResult(
                success=False,
                result=None,
                error=f"执行出错: {str(e)}"
            )


# ============================== 具体工具实现 ==============================
# ============================== 接口调用工具 ==============================
class APICallTool(BaseTool):
    """
    ▛▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▛
    REST API 调用工具（Pydantic适配版）
    
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
    VALID_METHODS: ClassVar[set[str]] = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}

    session_manager: Any = Field(exclude=True)
    session: Any = Field(exclude=True)

    def __init__(self, session_manager, **data):
        super().__init__(**data)
        self.session_manager = session_manager
        self.session = session_manager.get_session()
        # 初始化工具元数据
        self.name = "api_call"
        self.description = "执行HTTP API调用的工具"
        self.parameters = {
            "url": {"type": "str", "required": True},
            "method": {"type": "str", "default": "GET", "enum": list(self.VALID_METHODS)},
            "headers": {"type": "dict", "default": {}},
            "body": {"type": "dict"},
            "params": {"type": "dict", "default": {}}
        }

    async def execute(self, **kwargs):
        # 参数校验
        if not (url := kwargs.get("url")):
            return ToolCallResult(
                success=False,
                result=None,
                error="缺少必要参数: url"
            )
            
        # 参数预处理
        method = kwargs.get("method", "GET").upper()
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            **kwargs.get("headers", {})
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
                request_args["json"] = kwargs.get("body")
            else:
                request_args["params"] = kwargs.get("params", {})
     
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

    async def execute(self, **kwargs):
        """统一执行入口"""
        operation = kwargs.get("operation")
        handlers = {
            "create": self._create_file,
            "read": self._read_file,
            "modify": self._apply_diff
        }
        
        if not operation or operation not in handlers:
            return ToolCallResult(False, None, f"无效操作类型: {operation}")
            
        return await handlers[operation](kwargs)

    async def _create_file(self, **kwargs):
        """创建文件"""
        if not (path := kwargs.get("path")) or "content" not in kwargs:
            return ToolCallResult(False, None, "缺少必要参数: path 或 content")
            
        try:
            final_path = Path(path).resolve()
            final_path.parent.mkdir(parents=True, exist_ok=True)
            final_path.write_text(kwargs["content"], encoding="utf-8")
            return ToolCallResult(True, {"path": str(final_path)})
        except Exception as e:
            return ToolCallResult(False, None, f"创建失败: {str(e)}")

    async def _read_file(self, **kwargs):
        """读取文件"""
        if not (path := kwargs.get("path")):
            return ToolCallResult(False, None, "缺少必要参数: path")
            
        try:
            final_path = Path(path).resolve()
            if not final_path.exists():
                return ToolCallResult(False, None, f"文件不存在: {path}")
                
            content = final_path.read_text(encoding="utf-8")
            return ToolCallResult(True, {"content": content})
        except Exception as e:
            return ToolCallResult(False, None, f"读取失败: {str(e)}")

    async def _apply_diff(self, **kwargs):
        """应用修改"""
        required = ["path", "original_snippet", "new_snippet"]
        if missing := [p for p in required if p not in kwargs]:
            return ToolCallResult(False, None, f"缺少参数: {', '.join(missing)}")
            
        try:
            final_path = Path(kwargs["path"]).resolve()
            original = final_path.read_text(encoding="utf-8")
            
            if kwargs["original_snippet"] not in original:
                return ToolCallResult(
                    False,
                    None,
                    "原始片段未找到",
                    details={
                        "expected": kwargs["original_snippet"],
                        "actual": original
                    }
                )
                
            updated = original.replace(
                kwargs["original_snippet"],
                kwargs["new_snippet"],
                1
            )
            final_path.write_text(updated, encoding="utf-8")
            return ToolCallResult(True, {"path": str(final_path)})
        except Exception as e:
            return ToolCallResult(False, None, f"修改失败: {str(e)}")
