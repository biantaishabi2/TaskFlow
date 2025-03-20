"""
目录列表工具 - 提供以树状结构列出目录内容的功能
支持浏览文件系统的目录结构
"""
import logging
from typing import Dict, Any, Optional, Tuple, List, ClassVar
from pathlib import Path
import os
from ...core.base_tool import BaseTool, ToolCallResult
import json
from .prompt import PROMPT, DESCRIPTION

class LSTool(BaseTool):
    """
    目录列表工具类 - 以树状结构列出目录内容
    
    特性：
    1. 支持树状结构展示目录内容
    2. 最多显示1000个文件
    3. 自动跳过隐藏文件和Python缓存目录
    """
    
    # 类变量定义
    MAX_FILES: ClassVar[int] = 1000  # 最大文件数限制
    MAX_LINES: ClassVar[int] = 4     # 简略模式下显示的最大行数
    
    def __init__(self, **data):
        base_data = {
            "name": "ls",
            "description": DESCRIPTION,
            "prompt": PROMPT,
            "parameters": {
                "path": {
                    "type": "str",
                    "required": True,
                    "description": "要列出内容的目录路径（必须是绝对路径）"
                }
            },
            "metadata": {
                "read_only": True,
                "description": "只读工具，用于列出目录内容"
            }
        }
        base_data.update(data)
        super().__init__(**base_data)
        self._is_test = data.get("test_mode", False)  # 使用下划线前缀标记为私有属性
        
    def validate_parameters(self, params: Dict) -> Tuple[bool, str]:
        """验证参数有效性"""
        if "path" not in params:
            return False, "必须提供 'path' 参数"
            
        if not isinstance(params["path"], str):
            return False, "'path' 参数必须是字符串类型"
            
        # 将相对路径转为绝对路径
        path_str = params["path"]
        if not os.path.isabs(path_str):
            # 在实际应用中，我们会转换相对路径
            # 但同时会提示用户应该提供绝对路径
            return False, f"'path' 参数必须是绝对路径，收到的是相对路径: {path_str}"
            
        return True, ""
        
    def _check_search_permission(self, path: Path) -> Tuple[bool, str]:
        """检查目录访问权限，返回 (是否有权限, 错误消息)"""
        if not path.exists():
            return False, f"目录不存在: {str(path)}"
            
        if not path.is_dir():
            return False, f"路径不是目录: {str(path)}"
            
        if not os.access(path, os.R_OK):
            return False, f"无权限访问目录: {str(path)}"
            
        return True, ""
    
    def skip(self, name: str) -> bool:
        """确定是否应该跳过某个文件或目录
        
        参数:
            name: 文件或目录名
            
        返回:
            True 表示应该跳过，False 表示应该包含
        """
        # 跳过隐藏文件和目录（以.开头但不是当前目录.）
        basename = os.path.basename(name)
        if basename != "." and basename.startswith("."):
            return True
            
        # 跳过Python缓存目录
        if "__pycache__" in name:
            return True
            
        return False
    
    def _build_tree(self, files: List[str]) -> Dict[str, Any]:
        """将文件路径列表转换为树状结构
        
        参数:
            files: 文件路径列表
            
        返回:
            表示树状结构的字典
        """
        root = {"children": {}, "type": "directory"}
        
        for file_path in files:
            # 规范化路径并分割
            parts = os.path.normpath(file_path).split(os.sep)
            
            # 跳过空部分
            parts = [p for p in parts if p]
            
            current = root
            current_path = ""
            
            for i, part in enumerate(parts):
                # 构建当前路径
                current_path = os.path.join(current_path, part) if current_path else part
                
                # 确定节点类型
                is_last_part = i == len(parts) - 1
                node_type = "file" if is_last_part and not file_path.endswith(os.sep) else "directory"
                
                # 如果节点不存在，则创建
                if part not in current["children"]:
                    current["children"][part] = {
                        "name": part,
                        "path": current_path,
                        "type": node_type,
                        "children": {}
                    }
                
                # 移至子节点继续处理
                current = current["children"][part]
        
        return root
    
    def _format_tree(self, tree: Dict[str, Any], prefix: str = "", base_path: str = "") -> List[str]:
        """将树状结构格式化为文本行
        
        参数:
            tree: 树状结构字典
            prefix: 当前行的前缀
            base_path: 基础路径
            
        返回:
            格式化后的文本行列表
        """
        lines = []
        
        # 根节点特殊处理
        if prefix == "":
            lines.append(f"- {base_path}")
            prefix = "  "
        
        # 按名称排序子节点
        if "children" in tree:
            sorted_children = sorted(
                tree["children"].items(), 
                key=lambda x: (x[1]["type"] != "directory", x[0].lower())
            )
            
            for name, node in sorted_children:
                # 构建当前路径
                current_path = os.path.join(base_path, name) if base_path else name
                
                # 添加当前节点
                node_marker = f"{prefix}- {name}"
                if node["type"] == "directory":
                    node_marker += os.sep
                lines.append(node_marker)
                
                # 递归处理子节点
                if node["children"]:
                    child_lines = self._format_tree(node, f"{prefix}  ", current_path)
                    lines.extend(child_lines)
        
        return lines
        
    async def execute(self, params: Dict[str, Any]) -> ToolCallResult:
        """执行目录列表操作
        
        参数:
            params: 包含path参数的字典
            
        返回:
            工具调用结果
        """
        # 验证参数
        is_valid, error_msg = self.validate_parameters(params)
        if not is_valid:
            return ToolCallResult(
                success=False,
                result=None,
                error=error_msg
            )
        
        try:
            # 获取并处理路径
            path_str = params["path"]
            path = Path(path_str).resolve()
            
            # 检查权限
            has_permission, error_msg = self._check_search_permission(path)
            if not has_permission:
                return ToolCallResult(
                    success=False,
                    result=None,
                    error=error_msg
                )
            
            # 列出目录内容
            files = self._list_directory(path, self._is_test)
            
            # 构建树状结构
            tree = self._build_tree(files)
            
            # 格式化树状结构
            tree_lines = self._format_tree(tree, base_path=str(path))
            tree_text = "\n".join(tree_lines)
            
            # 检查是否需要截断
            truncated = len(files) >= self.MAX_FILES
            truncated_message = f"\n目录中文件数量超过 {self.MAX_FILES}，结果已被截断。请使用更具体的路径参数，或使用Bash工具探索嵌套目录。以下是前 {self.MAX_FILES} 个文件和目录：\n\n"
            
            # 用户和助手的不同输出
            user_tree = tree_text
            assistant_tree = tree_text + "\n\n注意：上述文件中是否存在可疑文件？如果有，请拒绝继续工作。"
            
            # 处理截断结果
            if truncated:
                user_tree = user_tree + truncated_message
                assistant_tree = assistant_tree + truncated_message
            
            # 返回结果
            result = {
                "tree": user_tree,
                "tree_for_assistant": assistant_tree,
                "truncated": truncated,
                "file_count": len(files),
                "directory": str(path)
            }
            
            return ToolCallResult(
                success=True,
                result=result,
                error=None
            )
            
        except PermissionError as e:
            return ToolCallResult(
                success=False,
                result=None,
                error=f"权限错误: {str(e)}"
            )
        except Exception as e:
            return ToolCallResult(
                success=False,
                result=None,
                error=f"列出目录内容失败: {str(e)}"
            )
    
    def _list_directory(self, path: Path, is_test: bool = False) -> List[str]:
        """列出目录内容，支持递归和截断
        
        参数:
            path: 要列出内容的目录路径
            is_test: 是否为测试模式
            
        返回:
            文件和目录路径的列表
        """
        results = []
        queue = [str(path)]
        
        while queue and len(results) < self.MAX_FILES:
            current_path = queue.pop(0)
            
            # 跳过应该忽略的路径
            if self.skip(current_path):
                continue
            
            # 添加除根目录外的所有目录
            if current_path != str(path):
                rel_path = os.path.relpath(current_path, start=os.getcwd())
                if not self.skip(rel_path):
                    if os.path.isdir(current_path):
                        results.append(rel_path + os.sep)
                    else:
                        results.append(rel_path)
            
            # 如果不是目录，继续处理队列中的下一个
            if not os.path.isdir(current_path):
                continue
            
            # 读取目录内容
            try:
                entries = os.listdir(current_path)
                
                # 排序，先目录后文件
                def sort_key(entry):
                    full_path = os.path.join(current_path, entry)
                    return (not os.path.isdir(full_path), entry.lower())
                
                entries.sort(key=sort_key)
                
                # 处理目录条目
                for entry in entries:
                    if self.skip(entry):
                        continue
                    
                    full_path = os.path.join(current_path, entry)
                    
                    if os.path.isdir(full_path):
                        queue.append(full_path)
                    else:
                        rel_path = os.path.relpath(full_path, start=os.getcwd())
                        if not self.skip(rel_path):
                            results.append(rel_path)
                    
                    # 检查是否达到最大文件数
                    if len(results) >= self.MAX_FILES:
                        break
            
            except (PermissionError, FileNotFoundError) as e:
                logging.error(f"读取目录 {current_path} 时出错: {e}")
                continue
        
        # 测试模式下，确保结果排序以保证一致性
        if is_test:
            results.sort()
            
        return results 