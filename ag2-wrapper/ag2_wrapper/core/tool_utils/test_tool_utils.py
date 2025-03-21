"""
工具辅助模块的单元测试
"""
import pytest
import os
import logging
from pathlib import Path
from typing import List, Dict
from tool_scanner import ToolScanner
from tool_loader import ToolLoader
from exceptions import ToolError, ToolLoadError, ToolScanError

# 配置日志输出
logging.basicConfig(
    level=logging.DEBUG,  # 改为 DEBUG 级别
    format='%(message)s'  # 简化格式，只显示消息
)

def print_separator():
    print("\n" + "="*50 + "\n")

@pytest.fixture
def tool_scanner():
    """创建工具扫描器实例"""
    return ToolScanner()

@pytest.fixture
def tool_loader():
    """创建工具加载器实例"""
    return ToolLoader()

def test_tool_scanner_initialization(tool_scanner):
    """测试工具扫描器初始化"""
    print_separator()
    print("测试工具扫描器初始化")
    
    print("排除的工具文件:")
    for file in tool_scanner.EXCLUDED_TOOL_FILES:
        print(f"- {file}")
    
    assert isinstance(tool_scanner, ToolScanner)
    assert isinstance(tool_scanner.EXCLUDED_TOOL_FILES, set)
    assert "conclusion_tool.py" in tool_scanner.EXCLUDED_TOOL_FILES
    
    print("✓ 工具扫描器初始化测试通过")

def test_detect_tools_path(tool_scanner):
    """测试工具目录路径检测"""
    print_separator()
    print("测试工具目录路径检测")
    
    tools_path = tool_scanner._detect_tools_path()
    print(f"检测到的工具路径: {tools_path}")
    
    assert tools_path is not None
    assert os.path.exists(tools_path)
    assert os.path.isdir(tools_path)
    assert tools_path.endswith("agent_tools")
    
    print("✓ 工具目录路径检测测试通过")

def test_scan_common_tools(tool_scanner):
    """测试扫描通用工具"""
    print_separator()
    print("测试扫描通用工具")
    
    tool_infos = tool_scanner.scan_directories(category="common")
    print(f"\n找到 {len(tool_infos)} 个通用工具:")
    
    assert isinstance(tool_infos, list)
    assert len(tool_infos) > 0
    
    # 验证每个工具信息的结构
    for tool_info in tool_infos:
        print(f"\n工具详情: {tool_info['name']}")
        print(f"  - 路径: {tool_info['path']}")
        print(f"  - 工具文件: {tool_info['tool_file']}")
        print(f"  - 提示词文件: {tool_info['prompt_file']}")
        
        assert isinstance(tool_info, dict)
        assert "name" in tool_info
        assert "path" in tool_info
        assert "tool_file" in tool_info
        assert "prompt_file" in tool_info
        assert tool_info["name"] not in tool_scanner.TOOL_CATEGORIES["dispatch_only"]
        
        # 验证文件存在
        base_path = tool_scanner._detect_tools_path()
        tool_dir = os.path.join(base_path, tool_info["name"])
        assert os.path.exists(tool_dir)
        assert os.path.exists(os.path.join(tool_dir, tool_info["tool_file"]))
        assert os.path.exists(os.path.join(tool_dir, tool_info["prompt_file"]))
        print(f"  ✓ 工具 {tool_info['name']} 验证通过")
    
    print("\n✓ 通用工具扫描测试通过")

def test_scan_dispatch_only_tools(tool_scanner):
    """测试特定工具文件的排除"""
    print_separator()
    print("测试特定工具文件的排除")
    
    # 获取 DispatchTool 目录下的所有文件
    base_path = tool_scanner._detect_tools_path()
    dispatch_dir = os.path.join(base_path, "DispatchTool")
    
    if os.path.exists(dispatch_dir):
        # 1. 首先验证文件确实存在于目录中
        all_files = os.listdir(dispatch_dir)
        print(f"\nDispatchTool 目录下的所有文件:")
        for file in all_files:
            print(f"- {file}")
            
        # 验证 conclusion_tool.py 确实存在于目录中
        assert "conclusion_tool.py" in all_files
        print("✓ 验证通过：conclusion_tool.py 存在于目录中")
        
        # 2. 然后验证扫描结果不包含被排除的工具
        tool_infos = tool_scanner.scan_directories()
        dispatch_tool = None
        for info in tool_infos:
            if info["name"] == "DispatchTool":
                dispatch_tool = info
                break
                
        assert dispatch_tool is not None
        print(f"\n扫描到的 DispatchTool 信息:")
        print(f"- 工具文件: {dispatch_tool['tool_file']}")
        print(f"- 提示词文件: {dispatch_tool['prompt_file']}")
        
        # 验证使用了正确的工具文件
        assert dispatch_tool["tool_file"] == "dispatch_tool.py"
        assert "conclusion_tool.py" != dispatch_tool["tool_file"]
        print("✓ 验证通过：使用了正确的工具文件，排除了 conclusion_tool.py")
        
        print("\n✓ 特定工具文件排除测试通过")
    else:
        pytest.skip("DispatchTool 目录不存在")

@pytest.mark.asyncio
async def test_tool_loader_common_tools(tool_loader):
    """测试加载通用工具"""
    print_separator()
    print("测试加载通用工具")
    
    tools = await tool_loader.load_tools()
    print(f"\n成功加载 {len(tools)} 个工具:")
    
    assert isinstance(tools, list)
    assert len(tools) > 0
    
    # 验证每个加载的工具
    for tool_class, prompt in tools:
        tool_instance = tool_class()
        print(f"\n工具详情: {tool_instance.name}")
        print(f"  - 描述: {tool_instance.description}")
        print(f"  - 提示词长度: {len(prompt)} 字符")
        
        assert tool_class is not None
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        
        # 验证工具类的基本属性
        assert hasattr(tool_instance, "name")
        assert hasattr(tool_instance, "description")
        assert hasattr(tool_instance, "execute")
        
        # 验证不是被排除的工具
        assert not tool_instance.__class__.__name__.endswith("ConclusionTool")
        
        print(f"  ✓ 工具 {tool_instance.name} 验证通过")
    
    print("\n✓ 工具加载测试通过")

@pytest.mark.asyncio
async def test_tool_loader_dispatch_tools(tool_loader):
    """测试加载 dispatch_only 工具"""
    print_separator()
    print("测试加载 dispatch_only 工具")
    
    tools = await tool_loader.load_tools(category="dispatch_only")
    print(f"\n成功加载 {len(tools)} 个 dispatch_only 工具:")
    
    assert isinstance(tools, list)
    
    # 验证只加载了 dispatch_only 类别的工具
    for tool_class, prompt in tools:
        tool_instance = tool_class()
        print(f"\n工具详情: {tool_instance.name}")
        print(f"  - 描述: {tool_instance.description}")
        print(f"  - 提示词长度: {len(prompt)} 字符")
        assert tool_instance.name in tool_loader.scanner.TOOL_CATEGORIES["dispatch_only"]
        print(f"  ✓ 工具 {tool_instance.name} 验证通过")
    
    print("\n✓ dispatch_only 工具加载测试通过")

@pytest.mark.asyncio
async def test_tool_loader_cache(tool_loader):
    """测试工具加载缓存"""
    print_separator()
    print("测试工具加载缓存")
    
    # 第一次加载
    print("\n1. 第一次加载工具...")
    tools1 = await tool_loader.load_tools(category="common", use_cache=True)
    print(f"   加载了 {len(tools1)} 个工具")
    
    # 第二次加载应该使用缓存
    print("\n2. 第二次加载工具（应使用缓存）...")
    tools2 = await tool_loader.load_tools(category="common", use_cache=True)
    print(f"   加载了 {len(tools2)} 个工具")
    
    assert tools1 == tools2
    print("   ✓ 缓存验证通过：两次加载结果相同")
    
    # 清除缓存后重新加载
    print("\n3. 清除缓存后重新加载...")
    tool_loader.clear_cache()
    tools3 = await tool_loader.load_tools(category="common", use_cache=True)
    print(f"   加载了 {len(tools3)} 个工具")
    
    assert len(tools3) == len(tools1)
    print(f"   ✓ 重新加载验证通过：工具数量保持一致 ({len(tools1)})")
    
    print("\n✓ 工具加载缓存测试通过")

def test_tool_categories_separation(tool_scanner):
    """测试工具加载和排除"""
    print_separator()
    print("测试工具加载和排除机制")
    
    # 扫描所有工具
    all_tools = tool_scanner.scan_directories()
    
    print(f"\n工具加载统计:")
    print(f"- 总工具数: {len(all_tools)} 个")
    
    # 获取所有加载的工具文件
    loaded_tool_files = set()
    for tool_info in all_tools:
        if tool_info["tool_file"]:
            loaded_tool_files.add(tool_info["tool_file"])
    
    print("\n加载的工具文件:")
    for file in sorted(loaded_tool_files):
        print(f"- {file}")
        
    # 验证被排除的文件确实未被加载
    for excluded_file in tool_scanner.EXCLUDED_TOOL_FILES:
        assert excluded_file not in loaded_tool_files
        print(f"\n✓ 验证通过：{excluded_file} 已被排除")
    
    print("\n✓ 工具加载和排除机制测试通过")

def test_excluded_tools(tool_scanner):
    """测试工具排除功能"""
    print_separator()
    print("测试工具排除功能")
    
    # 1. 测试文件级别的排除
    print("\n1. 测试文件级别排除:")
    base_path = tool_scanner._detect_tools_path()
    dispatch_dir = os.path.join(base_path, "DispatchTool")
    
    if os.path.exists(dispatch_dir):
        # 首先验证文件存在于目录中
        all_files = [f for f in os.listdir(dispatch_dir) if f.endswith("_tool.py")]
        print("DispatchTool 目录中的工具文件:")
        for file in all_files:
            print(f"- {file}")
            
        # 验证 conclusion_tool.py 确实存在于目录中
        assert "conclusion_tool.py" in all_files
        print("✓ 验证通过：conclusion_tool.py 存在于目录中")
        
        # 然后验证扫描结果
        tools = tool_scanner.scan_directories()
        loaded_files = set()
        for info in tools:
            if info["tool_file"]:
                loaded_files.add(info["tool_file"])
                
        print("\n加载的工具文件:")
        for file in sorted(loaded_files):
            print(f"- {file}")
            
        # 验证排除结果
        assert "conclusion_tool.py" not in loaded_files
        assert "dispatch_tool.py" in loaded_files
        print("✓ 验证通过：conclusion_tool.py 已被排除，dispatch_tool.py 已被加载")
    
    # 2. 测试目录级别的排除
    print("\n2. 测试目录级别排除:")
    # 获取一个存在的工具目录名称
    all_tools = tool_scanner.scan_directories()
    if not all_tools:
        pytest.skip("没有找到可用的工具")
    
    tool_to_exclude = all_tools[0]["name"]
    print(f"将要排除的工具目录: {tool_to_exclude}")
    
    # 使用排除列表扫描
    filtered_tools = tool_scanner.scan_directories(
        excluded_tools={tool_to_exclude}
    )
    
    # 验证工具目录被排除
    original_names = {t["name"] for t in all_tools}
    filtered_names = {t["name"] for t in filtered_tools}
    
    print(f"原始工具列表: {sorted(original_names)}")
    print(f"排除后工具列表: {sorted(filtered_names)}")
    
    assert tool_to_exclude not in filtered_names
    assert len(filtered_tools) == len(all_tools) - 1
    print(f"✓ 验证通过：工具目录 {tool_to_exclude} 已被排除")
    
    print("\n✓ 工具排除功能测试通过") 