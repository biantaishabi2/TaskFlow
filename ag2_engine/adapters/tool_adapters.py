from typing import Dict, Any, Optional, List, Callable
from abc import ABC, abstractmethod

class BaseToolAdapter(ABC):
    """工具适配器基类"""
    
    @abstractmethod
    def execute(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """执行工具
        
        Args:
            tool_name: 工具名称
            params: 工具参数
            
        Returns:
            工具执行结果
        """
        pass
    
    @abstractmethod
    def get_tools(self) -> Dict[str, Dict[str, Any]]:
        """获取所有可用工具信息
        
        Returns:
            工具信息字典
        """
        pass

class FileToolAdapter(BaseToolAdapter):
    """文件操作工具适配器"""
    
    def __init__(self, base_path: str = "."):
        """初始化文件工具适配器
        
        Args:
            base_path: 基础路径
        """
        self.base_path = base_path
        self._tools = {
            "read_file": {
                "description": "读取文件内容",
                "function": self._read_file
            },
            "write_file": {
                "description": "写入文件内容",
                "function": self._write_file
            },
            "list_files": {
                "description": "列出目录中的文件",
                "function": self._list_files
            }
        }
    
    def execute(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """执行文件工具
        
        Args:
            tool_name: 工具名称
            params: 工具参数
            
        Returns:
            工具执行结果
            
        Raises:
            ValueError: 工具不存在或执行失败
        """
        if tool_name not in self._tools:
            raise ValueError(f"未知的工具: {tool_name}")
        
        tool_func = self._tools[tool_name]["function"]
        return tool_func(params)
    
    def get_tools(self) -> Dict[str, Dict[str, Any]]:
        """获取所有可用文件工具信息
        
        Returns:
            工具信息字典
        """
        return {name: {"description": info["description"]} for name, info in self._tools.items()}
    
    def _read_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """读取文件内容
        
        Args:
            params: 包含file_path的参数字典
            
        Returns:
            包含文件内容的结果字典
        """
        file_path = params.get("file_path")
        if not file_path:
            return {"error": "缺少必要参数: file_path"}
        
        try:
            import os
            full_path = os.path.join(self.base_path, file_path)
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return {"content": content}
        except Exception as e:
            return {"error": f"读取文件失败: {str(e)}"}
    
    def _write_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """写入文件内容
        
        Args:
            params: 包含file_path和content的参数字典
            
        Returns:
            执行结果字典
        """
        file_path = params.get("file_path")
        content = params.get("content")
        if not file_path or content is None:
            return {"error": "缺少必要参数: file_path或content"}
        
        try:
            import os
            full_path = os.path.join(self.base_path, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return {"success": True}
        except Exception as e:
            return {"error": f"写入文件失败: {str(e)}"}
    
    def _list_files(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """列出目录中的文件
        
        Args:
            params: 包含dir_path的参数字典
            
        Returns:
            包含文件列表的结果字典
        """
        dir_path = params.get("dir_path", ".")
        
        try:
            import os
            full_path = os.path.join(self.base_path, dir_path)
            files = os.listdir(full_path)
            return {"files": files}
        except Exception as e:
            return {"error": f"列出文件失败: {str(e)}"}

class WebSearchAdapter(BaseToolAdapter):
    """Web搜索工具适配器"""
    
    def __init__(self, api_key: Optional[str] = None):
        """初始化Web搜索适配器
        
        Args:
            api_key: API密钥
        """
        self.api_key = api_key
        self._tools = {
            "search": {
                "description": "搜索互联网信息",
                "function": self._search
            }
        }
    
    def execute(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """执行Web搜索工具
        
        Args:
            tool_name: 工具名称
            params: 工具参数
            
        Returns:
            工具执行结果
        """
        if tool_name not in self._tools:
            raise ValueError(f"未知的工具: {tool_name}")
        
        tool_func = self._tools[tool_name]["function"]
        return tool_func(params)
    
    def get_tools(self) -> Dict[str, Dict[str, Any]]:
        """获取所有可用Web搜索工具信息
        
        Returns:
            工具信息字典
        """
        return {name: {"description": info["description"]} for name, info in self._tools.items()}
    
    def _search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """搜索互联网信息
        
        Args:
            params: 包含query的参数字典
            
        Returns:
            搜索结果字典
        """
        query = params.get("query")
        if not query:
            return {"error": "缺少必要参数: query"}
        
        # 实际实现中，这里需要调用搜索API
        # 简化实现
        return {
            "results": [
                {"title": "示例结果1", "snippet": "这是示例搜索结果1", "url": "https://example.com/1"},
                {"title": "示例结果2", "snippet": "这是示例搜索结果2", "url": "https://example.com/2"}
            ]
        }

# 根据需要添加其他工具适配器