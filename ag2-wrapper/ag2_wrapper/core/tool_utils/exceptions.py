"""
工具相关的自定义异常
"""

class ToolError(Exception):
    """工具基础异常"""
    pass

class ToolLoadError(ToolError):
    """工具加载异常"""
    pass

class ToolScanError(ToolError):
    """工具扫描异常"""
    pass 