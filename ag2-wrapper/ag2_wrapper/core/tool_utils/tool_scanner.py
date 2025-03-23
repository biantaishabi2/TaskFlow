"""
工具扫描器模块 - 负责扫描和识别工具目录
"""
import os
import logging
from typing import Dict, List, Set, Optional
from pathlib import Path
from .exceptions import ToolScanError

class ToolScanner:
    """工具目录扫描器"""
    
    # 工具分类配置
    TOOL_CATEGORIES = {
        "dispatch_only": ["ConclusionTool"],
        "common": []  # 自动包含未分类的工具
    }
    
    # 排除的具体工具文件
    EXCLUDED_TOOL_FILES = {
        "conclusion_tool.py",  # 排除结论工具
    }
    
    # 默认排除的工具目录
    DEFAULT_EXCLUDED = set()
    
    def scan_directories(
        self,
        category: str = "common",
        excluded_tools: Optional[Set[str]] = None,
        base_path: str = None
    ) -> List[Dict]:
        """
        扫描工具目录
        
        Args:
            category: 工具类别 ("common", "dispatch_only", "all")
            excluded_tools: 要排除的工具目录集合
            base_path: 基础目录路径，如果为None则自动检测
            
        Returns:
            List[Dict]: 工具信息列表
        """
        try:
            # 如果未指定base_path，自动检测
            if base_path is None:
                base_path = self._detect_tools_path()
            
            excluded = excluded_tools or self.DEFAULT_EXCLUDED
            tool_infos = []
            
            for item in os.listdir(base_path):
                if self._should_process_tool(item, category, excluded):
                    tool_info = self._get_tool_info(base_path, item)
                    if tool_info:
                        tool_infos.append(tool_info)
                        
            logging.info(f"在 {category} 类别中找到 {len(tool_infos)} 个工具")
            return tool_infos
            
        except Exception as e:
            raise ToolScanError(f"扫描工具目录失败: {str(e)}")
    
    def _detect_tools_path(self) -> str:
        """自动检测工具目录路径"""
        # 获取当前文件所在目录
        current_dir = Path(__file__).resolve().parent
        
        # 向上查找直到找到 ag2_wrapper 目录
        while current_dir.name != "ag2_wrapper":
            current_dir = current_dir.parent
            if current_dir == current_dir.parent:
                raise ToolScanError("无法找到工具目录")
        
        # 返回 agent_tools 目录的路径
        tools_dir = current_dir / "agent_tools"
        if not tools_dir.exists():
            raise ToolScanError("agent_tools 目录不存在")
            
        return str(tools_dir)
        
    def _should_process_tool(
        self,
        tool_name: str,
        category: str,
        excluded: Set[str]
    ) -> bool:
        """判断是否应该处理该工具"""
        if tool_name in excluded:
            return False
            
        if category == "all":
            return True
            
        if category == "dispatch_only":
            return tool_name in self.TOOL_CATEGORIES["dispatch_only"]
            
        # common 类别排除 dispatch_only 工具
        return tool_name not in self.TOOL_CATEGORIES["dispatch_only"]
        
    def _get_tool_info(self, base_path: str, tool_name: str) -> Optional[Dict]:
        """获取工具信息"""
        dir_path = os.path.join(base_path, tool_name)
        # 只检查是否为目录，移除大小写检查
        if not os.path.isdir(dir_path):
            return None
            
        try:
            tool_info = {
                "name": tool_name,
                "path": f"ag2_wrapper.agent_tools.{tool_name}",
                "tool_file": None,
                "prompt_file": None
            }
            
            # 首先找到所有非测试的工具文件
            tool_files = []
            for file in os.listdir(dir_path):
                if file.endswith("_tool.py") and not file.startswith("test_"):
                    tool_files.append(file)
            
            # 从工具文件中排除被排除的文件
            valid_tool_files = [f for f in tool_files if f not in self.EXCLUDED_TOOL_FILES]
            
            # 如果有多个工具文件，使用与目录名匹配的那个
            if valid_tool_files:
                # 优先使用与目录名匹配的工具文件
                expected_name = f"{tool_name.lower()}_tool.py"
                matching_files = [f for f in valid_tool_files if f.lower() == expected_name]
                if matching_files:
                    tool_info["tool_file"] = matching_files[0]
                else:
                    # 如果没有匹配的，使用第一个有效的工具文件
                    tool_info["tool_file"] = valid_tool_files[0]
                    
            # 查找提示词文件
            if os.path.exists(os.path.join(dir_path, "prompt.py")):
                tool_info["prompt_file"] = "prompt.py"
                    
            if tool_info["tool_file"] and tool_info["prompt_file"]:
                logging.debug(f"找到工具: {tool_name} (工具文件: {tool_info['tool_file']})")
                return tool_info
                
            return None
            
        except Exception as e:
            logging.warning(f"处理工具 {tool_name} 时出错: {str(e)}")
            return None