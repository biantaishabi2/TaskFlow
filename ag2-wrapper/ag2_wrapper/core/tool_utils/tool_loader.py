"""
工具加载器模块 - 负责工具的动态加载和管理
"""
import os
import logging
import importlib
from typing import Dict, List, Set, Tuple, Any, Optional
from .exceptions import ToolLoadError
from .tool_scanner import ToolScanner

class ToolLoader:
    """工具加载管理器"""
    
    def __init__(self):
        self.scanner = ToolScanner()
        self._cache = {}  # 工具缓存
        
    async def load_tools(
        self,
        category: str = "common",
        excluded_tools: Optional[Set[str]] = None,
        use_cache: bool = True,
        base_path: str = None
    ) -> List[Tuple[Any, str]]:
        """
        加载工具和它们的提示词
        
        Args:
            category: 工具类别 ("common", "dispatch_only", "all")
            excluded_tools: 要排除的工具集合
            use_cache: 是否使用缓存
            base_path: 基础目录路径
            
        Returns:
            List[Tuple[Tool, str]]: 工具实例和提示词的列表
        """
        try:
            cache_key = f"{category}_{sorted(excluded_tools or set())}"
            
            # 检查缓存
            if use_cache and cache_key in self._cache:
                logging.debug(f"使用缓存的工具: {cache_key}")
                return self._cache[cache_key]
                
            # 扫描工具目录
            tool_infos = self.scanner.scan_directories(
                category=category,
                excluded_tools=excluded_tools,
                base_path=base_path
            )
            
            # 加载工具
            loaded_tools = []
            for tool_info in tool_infos:
                try:
                    tool_class, prompt = await self._import_tool(tool_info)
                    if tool_class and prompt:
                        loaded_tools.append((tool_class, prompt))
                except Exception as e:
                    logging.error(f"加载工具 {tool_info['name']} 失败: {str(e)}")
                    
            # 更新缓存
            if use_cache:
                self._cache[cache_key] = loaded_tools
                
            logging.debug(f"成功加载 {len(loaded_tools)} 个工具")
            return loaded_tools
            
        except Exception as e:
            raise ToolLoadError(f"加载工具失败: {str(e)}")
        
    async def _import_tool(self, tool_info: Dict) -> Tuple[Any, str]:
        """导入单个工具和其提示词"""
        try:
            # 导入工具模块
            tool_module = importlib.import_module(
                f"{tool_info['path']}.{tool_info['tool_file'][:-3]}"
            )
            
            # 导入提示词模块
            prompt_module = importlib.import_module(
                f"{tool_info['path']}.prompt"
            )
            
            # 获取工具类
            tool_class = getattr(tool_module, tool_info["name"])
            prompt = getattr(prompt_module, "PROMPT", "")
            
            if not tool_class:
                raise ToolLoadError(f"工具类 {tool_info['name']} 未找到")
                
            if not prompt:
                logging.warning(f"工具 {tool_info['name']} 没有提示词")
                
            return tool_class, prompt
            
        except ImportError as e:
            raise ToolLoadError(f"导入工具 {tool_info['name']} 失败: {str(e)}")
        except AttributeError as e:
            raise ToolLoadError(f"工具 {tool_info['name']} 属性错误: {str(e)}")
        except Exception as e:
            raise ToolLoadError(f"处理工具 {tool_info['name']} 时出错: {str(e)}")
            
    def _import_tool_sync(self, tool_info: Dict) -> Tuple[Any, str]:
        """导入单个工具和其提示词的同步版本"""
        try:
            # 导入工具模块
            tool_module = importlib.import_module(
                f"{tool_info['path']}.{tool_info['tool_file'][:-3]}"
            )
            
            # 导入提示词模块
            prompt_module = importlib.import_module(
                f"{tool_info['path']}.prompt"
            )
            
            # 获取工具类
            tool_class = getattr(tool_module, tool_info["name"])
            prompt = getattr(prompt_module, "PROMPT", "")
            
            if not tool_class:
                raise ToolLoadError(f"工具类 {tool_info['name']} 未找到")
                
            if not prompt:
                logging.warning(f"工具 {tool_info['name']} 没有提示词")
                
            return tool_class, prompt
            
        except ImportError as e:
            raise ToolLoadError(f"导入工具 {tool_info['name']} 失败: {str(e)}")
        except AttributeError as e:
            raise ToolLoadError(f"工具 {tool_info['name']} 属性错误: {str(e)}")
        except Exception as e:
            raise ToolLoadError(f"处理工具 {tool_info['name']} 时出错: {str(e)}")
            
    def load_tools_sync(
        self,
        category: str = "common",
        excluded_tools: Optional[Set[str]] = None,
        use_cache: bool = True,
        base_path: str = None
    ) -> List[Tuple[Any, str]]:
        """
        加载工具和它们的提示词 - 同步版本
        
        Args:
            category: 工具类别 ("common", "dispatch_only", "all")
            excluded_tools: 要排除的工具集合
            use_cache: 是否使用缓存
            base_path: 基础目录路径
            
        Returns:
            List[Tuple[Tool, str]]: 工具实例和提示词的列表
        """
        try:
            cache_key = f"{category}_{sorted(excluded_tools or set())}"
            
            # 检查缓存
            if use_cache and cache_key in self._cache:
                logging.debug(f"使用缓存的工具: {cache_key}")
                return self._cache[cache_key]
                
            # 扫描工具目录
            tool_infos = self.scanner.scan_directories(
                category=category,
                excluded_tools=excluded_tools,
                base_path=base_path
            )
            
            # 加载工具
            loaded_tools = []
            for tool_info in tool_infos:
                try:
                    tool_class, prompt = self._import_tool_sync(tool_info)
                    if tool_class and prompt:
                        loaded_tools.append((tool_class, prompt))
                except Exception as e:
                    logging.error(f"加载工具 {tool_info['name']} 失败: {str(e)}")
                    
            # 更新缓存
            if use_cache:
                self._cache[cache_key] = loaded_tools
                
            logging.debug(f"成功加载 {len(loaded_tools)} 个工具")
            return loaded_tools
            
        except Exception as e:
            raise ToolLoadError(f"加载工具失败: {str(e)}")
            
    def clear_cache(self):
        """清除工具缓存"""
        self._cache.clear()
        logging.debug("工具缓存已清除")