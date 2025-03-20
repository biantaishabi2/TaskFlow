"""
GrepTool 的测试文件
包含单元测试和集成测试
"""
import os
import pytest
import logging
from pathlib import Path
import subprocess
from ag2_wrapper.agent_tools.GrepTool.grep_tool import GrepTool

# 设置日志级别
logging.basicConfig(level=logging.INFO)

pytestmark = pytest.mark.asyncio  # 标记所有测试为异步测试

@pytest.fixture
def grep_tool():
    """创建 GrepTool 实例"""
    tool = GrepTool()
    tool.is_test = True  # 确保测试模式
    return tool

@pytest.fixture
def temp_dir(tmp_path):
    """创建临时测试目录"""
    abs_path = tmp_path.absolute()
    logging.info(f"创建临时目录，绝对路径: {abs_path}")
    return abs_path

@pytest.fixture
def test_files(temp_dir):
    """创建测试文件结构"""
    # 创建测试文件和目录
    files = {
        "src/main.js": "function main() { console.log('Hello'); }",
        "src/utils.js": "function logError(msg) { console.error(msg); }",
        "src/components/Button.tsx": "export const Button = () => { console.log('click'); }",
        "test/test.js": "test('should work', () => { console.error('test'); })",
        "README.md": "# Test Project\nThis is a test project."
    }
    
    abs_temp_dir = Path(temp_dir).absolute()
    logging.info(f"创建临时目录: {abs_temp_dir}")
    
    # 创建并验证每个文件
    created_files = []
    for rel_path, content in files.items():
        abs_file_path = abs_temp_dir / rel_path
        abs_file_path.parent.mkdir(parents=True, exist_ok=True)
        abs_file_path.write_text(content)
        assert abs_file_path.exists(), f"文件未创建成功: {abs_file_path}"
        created_files.append(abs_file_path)
        logging.info(f"创建文件: {abs_file_path}")
        logging.info(f"文件内容: {content}")
        
    # 验证所有文件都包含预期内容
    for file_path in created_files:
        if file_path.suffix in ['.js', '.tsx']:
            content = file_path.read_text()
            assert 'console' in content, f"文件内容不正确: {file_path}"
            logging.info(f"验证文件 {file_path} 内容包含 'console'")
            
    # 列出所有创建的文件
    all_files = list(abs_temp_dir.rglob('*'))
    logging.info(f"临时目录中的所有文件和目录:")
    for f in all_files:
        if f.is_file():
            logging.info(f"文件: {f} (大小: {f.stat().st_size} 字节)")
        else:
            logging.info(f"目录: {f}")
            
    return abs_temp_dir

# 单元测试
async def test_validate_parameters(grep_tool):
    """测试参数验证"""
    # 测试有效参数
    assert grep_tool.validate_parameters({"pattern": "test"}) == (True, "")
    assert grep_tool.validate_parameters({
        "pattern": "test",
        "path": ".",
        "include": "*.js"
    }) == (True, "")
    
    # 测试无效参数
    result, msg = grep_tool.validate_parameters({})
    assert result is False
    assert "pattern" in msg.lower()
    
    result, msg = grep_tool.validate_parameters({"pattern": 123})
    assert result is False
    assert "pattern" in msg.lower()

async def test_check_search_permission(grep_tool, temp_dir):
    """测试搜索权限检查"""
    # 测试有效目录
    result, msg = grep_tool._check_search_permission(temp_dir)
    assert result is True
    assert msg == ""
    
    # 测试不存在的目录
    invalid_dir = temp_dir / "not_exists"
    result, msg = grep_tool._check_search_permission(invalid_dir)
    assert result is False
    assert "不存在" in msg
    
    # 测试无权限目录
    readonly_dir = temp_dir / "readonly"
    readonly_dir.mkdir()
    os.chmod(readonly_dir, 0o000)
    result, msg = grep_tool._check_search_permission(readonly_dir)
    assert result is False
    assert "无权限" in msg
    os.chmod(readonly_dir, 0o777)  # 恢复权限以便清理

async def test_sort_results(grep_tool, test_files):
    """测试结果排序"""
    # 创建测试文件列表
    files = [
        test_files / "src/main.js",
        test_files / "src/utils.js",
        test_files / "test/test.js"
    ]
    
    # 测试模式下应该按文件名排序
    sorted_files = grep_tool._sort_results(files)
    assert len(sorted_files) == 3
    assert sorted_files == sorted(str(f) for f in files)

# 集成测试
async def test_basic_search(grep_tool, test_files):
    """测试基本搜索功能"""
    abs_path = Path(test_files).absolute()
    logging.info(f"测试目录绝对路径: {abs_path}")
    
    # 验证测试目录中的文件
    js_files = list(Path(abs_path).rglob('*.js'))
    tsx_files = list(Path(abs_path).rglob('*.tsx'))
    logging.info(f"JS文件: {js_files}")
    logging.info(f"TSX文件: {tsx_files}")
    assert len(js_files) > 0, "没有找到JS文件"
    
    # 验证文件内容
    for js_file in js_files:
        content = js_file.read_text()
        logging.info(f"JS文件 {js_file} 内容: {content}")
        assert 'console' in content, f"文件 {js_file} 中没有找到 'console'"
    
    # 执行搜索
    logging.info(f"开始搜索，使用绝对路径: {abs_path}")
    result = await grep_tool.execute({
        "pattern": "console",
        "path": str(abs_path)  # 使用绝对路径
    })
    
    # 记录搜索结果
    logging.info(f"搜索结果: {result.result}")
    if result.result["numFiles"] == 0:
        logging.error("搜索结果为空，检查目录信息:")
        logging.error(f"当前工作目录: {os.getcwd()}")
        logging.error(f"搜索目录: {abs_path}")
        logging.error(f"目录是否存在: {os.path.exists(abs_path)}")
        logging.error(f"目录内容: {list(Path(abs_path).rglob('*'))}")
    
    assert result.success is True
    assert result.result["numFiles"] > 0
    # 验证返回的文件路径是有效的
    for file_path in result.result["filenames"]:
        assert os.path.exists(file_path), f"文件路径不存在: {file_path}"
        # 读取文件内容，确认确实包含搜索词
        assert 'console' in Path(file_path).read_text(), f"文件 {file_path} 不包含搜索词"

async def test_file_type_filter(grep_tool, test_files):
    """测试文件类型过滤"""
    abs_path = Path(test_files).absolute()
    logging.info(f"测试目录绝对路径: {abs_path}")
    
    # 验证JS文件存在
    js_files = list(Path(abs_path).rglob('*.js'))
    logging.info(f"JS文件: {js_files}")
    assert len(js_files) > 0, "没有找到JS文件"
    
    result = await grep_tool.execute({
        "pattern": "console",
        "path": str(abs_path),  # 使用绝对路径
        "include": "*.js"
    })
    
    logging.info(f"搜索结果: {result.result}")
    assert result.success is True
    assert result.result["numFiles"] > 0
    assert all(f.endswith(".js") for f in result.result["filenames"])

async def test_no_matches(grep_tool, test_files):
    """测试无匹配结果的情况"""
    result = await grep_tool.execute({
        "pattern": "nonexistentpattern123",
        "path": str(test_files)
    })
    
    assert result.success is True
    assert result.result["numFiles"] == 0

async def test_invalid_regex(grep_tool, test_files):
    """测试无效的正则表达式"""
    result = await grep_tool.execute({
        "pattern": "[invalid regex",
        "path": str(test_files)
    })
    
    assert result.success is False
    # 错误消息可能会变化，但应该包含关键信息
    assert "无效" in result.error.lower() or "搜索失败" in result.error.lower()

async def test_real_codebase_search(grep_tool):
    """测试在实际代码库中搜索"""
    # 在当前项目中搜索
    result = await grep_tool.execute({
        "pattern": "class.*Tool",
        "include": "*.py"
    })
    
    assert result.success is True
    assert result.result["numFiles"] > 0
    assert any("tool.py" in f.lower() for f in result.result["filenames"])

async def test_result_truncation(grep_tool, test_files):
    """测试结果截断功能"""
    # 创建大量测试文件
    many_files_dir = test_files / "many_files"
    many_files_dir.mkdir(exist_ok=True)
    
    created_files = []
    for i in range(150):
        file_path = many_files_dir / f"file_{i}.js"
        file_path.write_text(f"console.log('file {i}');")
        created_files.append(file_path)
        
    # 验证文件创建成功
    js_files = list(many_files_dir.glob('*.js'))
    logging.info(f"创建了 {len(js_files)} 个JS文件")
    assert len(js_files) == 150, f"文件创建不完整，只有 {len(js_files)} 个文件"
    
    result = await grep_tool.execute({
        "pattern": "console",
        "path": str(test_files)
    })
    
    logging.info(f"搜索结果: {result.result}")
    assert result.success is True
    assert result.result["truncated"] is True
    assert len(result.result["filenames"]) <= grep_tool.max_results

async def test_search_with_context(grep_tool, test_files):
    """测试在特定目录下搜索"""
    # 验证src目录中的文件
    src_dir = test_files / "src"
    src_files = list(src_dir.rglob('*'))
    logging.info(f"src目录文件: {src_files}")
    assert len(src_files) > 0, "src目录为空"
    
    result = await grep_tool.execute({
        "pattern": "console",
        "path": str(test_files / "src")
    })
    
    logging.info(f"搜索结果: {result.result}")
    assert result.success is True
    assert result.result["numFiles"] > 0
    
    # 验证所有结果都是有效路径
    for file_path in result.result["filenames"]:
        assert os.path.exists(file_path), f"文件路径不存在: {file_path}"
        # 验证所有文件确实含有 console
        assert 'console' in Path(file_path).read_text(), f"文件 {file_path} 不包含搜索词"
    
    # 验证所有结果都在src目录下（使用startswith而不是包含）
    src_abs_path = str(src_dir.absolute())
    for file_path in result.result["filenames"]:
        assert file_path.startswith(src_abs_path), f"文件 {file_path} 不在src目录下" 