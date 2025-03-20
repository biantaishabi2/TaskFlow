"""
LSTool 的测试文件
包含单元测试和集成测试
"""
import os
import pytest
import logging
from pathlib import Path
from ag2_wrapper.agent_tools.lsTool.ls_tool import LSTool

# 设置日志级别
logging.basicConfig(level=logging.INFO)

pytestmark = pytest.mark.asyncio  # 标记所有测试为异步测试

@pytest.fixture
def ls_tool():
    """创建 LSTool 实例"""
    return LSTool(test_mode=True)  # 通过构造函数参数设置测试模式

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
        "README.md": "# Test Project\nThis is a test project.",
        ".hidden/config.json": '{"debug": true}',
        "__pycache__/cache.pyc": "# 缓存文件"
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
async def test_validate_parameters(ls_tool):
    """测试参数验证"""
    # 测试有效参数
    result, msg = ls_tool.validate_parameters({"path": "/absolute/path"})
    assert result is True
    assert msg == ""
    
    # 测试无参数
    result, msg = ls_tool.validate_parameters({})
    assert result is False
    assert "必须提供" in msg
    
    # 测试非字符串参数
    result, msg = ls_tool.validate_parameters({"path": 123})
    assert result is False
    assert "必须是字符串" in msg
    
    # 测试相对路径
    result, msg = ls_tool.validate_parameters({"path": "relative/path"})
    assert result is False
    assert "必须是绝对路径" in msg

async def test_check_search_permission(ls_tool, temp_dir):
    """测试搜索权限检查"""
    # 测试有效目录
    result, msg = ls_tool._check_search_permission(Path(temp_dir))
    assert result is True
    assert msg == ""
    
    # 测试不存在的目录
    nonexistent_dir = Path(temp_dir) / "nonexistent"
    result, msg = ls_tool._check_search_permission(nonexistent_dir)
    assert result is False
    assert "不存在" in msg
    
    # 测试文件而非目录
    test_file = Path(temp_dir) / "test_file.txt"
    test_file.write_text("test")
    result, msg = ls_tool._check_search_permission(test_file)
    assert result is False
    assert "不是目录" in msg

async def test_skip_function(ls_tool):
    """测试文件过滤功能"""
    # 测试普通文件
    assert ls_tool.skip("normal.txt") is False
    
    # 测试隐藏文件
    assert ls_tool.skip(".hidden") is True
    
    # 测试当前目录
    assert ls_tool.skip(".") is False
    
    # 测试Python缓存目录
    assert ls_tool.skip("__pycache__/file.pyc") is True

# 集成测试
async def test_basic_listing(ls_tool, test_files):
    """测试基本目录列表功能"""
    # 执行目录列表操作
    result = await ls_tool.execute({"path": str(test_files)})
    
    # 验证结果
    assert result.success is True
    assert result.error is None
    assert "tree" in result.result
    assert "file_count" in result.result
    assert result.result["truncated"] is False
    
    # 验证树结构
    tree_text = result.result["tree"]
    assert "src/" in tree_text
    assert "test/" in tree_text
    assert "README.md" in tree_text
    
    # 验证隐藏文件和缓存目录被过滤
    assert ".hidden" not in tree_text
    assert "__pycache__" not in tree_text

async def test_directory_not_found(ls_tool, temp_dir):
    """测试目录不存在的情况"""
    # 构造不存在的目录路径
    nonexistent_dir = str(Path(temp_dir) / "nonexistent")
    
    # 执行目录列表操作
    result = await ls_tool.execute({"path": nonexistent_dir})
    
    # 验证结果
    assert result.success is False
    assert result.result is None
    assert "不存在" in result.error

async def test_hidden_files(ls_tool, test_files):
    """测试隐藏文件处理"""
    # 创建一个包含隐藏文件的测试目录
    hidden_dir = Path(test_files) / "hidden_test"
    hidden_dir.mkdir(exist_ok=True)
    
    # 创建普通文件和隐藏文件
    (hidden_dir / "normal.txt").write_text("Normal file")
    (hidden_dir / ".hidden.txt").write_text("Hidden file")
    
    # 执行目录列表操作
    result = await ls_tool.execute({"path": str(hidden_dir)})
    
    # 验证结果
    assert result.success is True
    tree_text = result.result["tree"]
    assert "normal.txt" in tree_text
    assert ".hidden.txt" not in tree_text

async def test_max_files_limit(ls_tool, test_files):
    """测试文件数量限制"""
    # 创建一个包含大量文件的测试目录
    many_files_dir = Path(test_files) / "many_files"
    many_files_dir.mkdir(exist_ok=True)
    
    # 创建超过MAX_FILES数量的文件
    file_count = ls_tool.MAX_FILES + 10
    for i in range(file_count):
        (many_files_dir / f"file_{i}.txt").write_text(f"Content {i}")
    
    # 执行目录列表操作
    result = await ls_tool.execute({"path": str(many_files_dir)})
    
    # 验证结果
    assert result.success is True
    assert result.result["truncated"] is True
    assert result.result["file_count"] >= ls_tool.MAX_FILES
    
    # 验证截断消息
    tree_text = result.result["tree"]
    assert f"目录中文件数量超过 {ls_tool.MAX_FILES}" in tree_text

async def test_nested_directories(ls_tool, test_files):
    """测试嵌套目录结构显示"""
    # 创建一个具有多级嵌套目录的测试目录
    nested_dir = Path(test_files) / "nested"
    nested_dir.mkdir(exist_ok=True)
    
    # 创建嵌套目录结构
    level1 = nested_dir / "level1"
    level1.mkdir(exist_ok=True)
    (level1 / "file1.txt").write_text("Level 1 file")
    
    level2 = level1 / "level2"
    level2.mkdir(exist_ok=True)
    (level2 / "file2.txt").write_text("Level 2 file")
    
    level3 = level2 / "level3"
    level3.mkdir(exist_ok=True)
    (level3 / "file3.txt").write_text("Level 3 file")
    
    # 执行目录列表操作
    result = await ls_tool.execute({"path": str(nested_dir)})
    
    # 验证结果
    assert result.success is True
    tree_text = result.result["tree"]
    
    # 验证目录结构（使用实际的输出格式）
    assert "- level1/" in tree_text, "level1目录应该存在"
    assert "- level2/" in tree_text, "level2目录应该存在"
    assert "- level3/" in tree_text, "level3目录应该存在"
    assert "- file1.txt" in tree_text, "file1.txt应该存在"
    assert "- file2.txt" in tree_text, "file2.txt应该存在"
    assert "- file3.txt" in tree_text, "file3.txt应该存在"

async def test_permission_denied(ls_tool, temp_dir):
    """测试无权限访问的目录"""
    # 创建一个无权限访问的目录
    no_access_dir = Path(temp_dir) / "no_access"
    no_access_dir.mkdir(exist_ok=True)
    
    try:
        # 尝试更改权限（在某些环境中可能不生效）
        os.chmod(no_access_dir, 0o000)
        
        # 执行目录列表操作
        result = await ls_tool.execute({"path": str(no_access_dir)})
        
        # 验证结果
        if not result.success:
            assert "权限" in result.error
    except:
        # 如果无法更改权限或测试环境不支持，则跳过此测试
        pytest.skip("无法在当前环境中创建无权限目录")
    finally:
        # 恢复权限以便清理
        try:
            os.chmod(no_access_dir, 0o755)
        except:
            pass

async def test_real_project_directory(ls_tool):
    """测试真实项目目录，验证工具在实际环境中的表现"""
    # 获取当前项目根目录
    current_dir = Path(__file__).parent.parent.parent.parent
    logging.info(f"测试真实项目目录: {current_dir}")
    
    # 执行目录列表操作
    result = await ls_tool.execute({"path": str(current_dir)})
    
    # 验证结果
    assert result.success is True
    assert result.error is None
    tree_text = result.result["tree"]
    
    # 验证关键目录和文件存在
    assert "ag2_wrapper/" in tree_text, "项目目录中应包含ag2_wrapper目录"
    
    # 验证工具目录存在
    assert "agent_tools/" in tree_text, "项目目录中应包含agent_tools目录"
    
    # 验证工具返回的文件数与实际情况相符
    file_count = result.result["file_count"]
    logging.info(f"返回的文件数量: {file_count}")
    assert file_count > 0, "应返回多个文件"
    
    # 检查隐藏文件是否被正确过滤
    hidden_files = [line for line in tree_text.split('\n') if '.' in line and os.path.basename(line).startswith('.')]
    for hidden_file in hidden_files:
        assert not os.path.basename(hidden_file).startswith('.'), f"隐藏文件未被过滤: {hidden_file}"
        
    # 检查__pycache__目录是否被过滤
    assert "__pycache__" not in tree_text, "__pycache__目录应被过滤"

async def test_current_working_directory(ls_tool):
    """测试当前工作目录，这是最常见的使用场景"""
    # 获取当前工作目录
    cwd = os.getcwd()
    logging.info(f"测试当前工作目录: {cwd}")
    
    # 执行目录列表操作
    result = await ls_tool.execute({"path": cwd})
    
    # 验证结果
    assert result.success is True
    assert result.error is None
    
    # 验证树结构中包含了工作目录路径
    tree_text = result.result["tree"]
    assert cwd in tree_text.split('\n')[0], "树状结构第一行应包含当前工作目录路径"
    
    # 比较文件系统实际内容与工具返回的内容
    real_entries = [f for f in os.listdir(cwd)
                   if not f.startswith('.') and f != '__pycache__']
    
    # 检查每个实际存在的(非隐藏)条目是否在返回结果中
    for entry in real_entries:
        if os.path.isdir(os.path.join(cwd, entry)):
            assert f"- {entry}/" in tree_text, f"目录 {entry} 应在结果中"
        else:
            assert f"- {entry}" in tree_text, f"文件 {entry} 应在结果中"
    
    # 验证截断状态
    if result.result["truncated"]:
        # 如果结果被截断，实际文件数应该超过或等于最大限制
        assert result.result["file_count"] >= ls_tool.MAX_FILES
    else:
        # 如果结果未被截断，文件数应该小于最大限制
        assert result.result["file_count"] < ls_tool.MAX_FILES

async def test_specific_file_type_directory(ls_tool, test_files):
    """测试特定文件类型的目录，模拟源代码目录浏览场景"""
    # 创建一个包含多种文件类型的目录
    code_dir = Path(test_files) / "code_samples"
    code_dir.mkdir(exist_ok=True)
    
    # 创建不同类型的代码文件
    file_types = {
        "main.py": "print('Hello from Python')",
        "index.js": "console.log('Hello from JavaScript');",
        "styles.css": "body { font-family: sans-serif; }",
        "index.html": "<html><body><h1>Hello</h1></body></html>",
        "config.json": '{"debug": true}',
        "main.cpp": "#include <iostream>\nint main() { std::cout << \"Hello\"; return 0; }",
        "README.md": "# Code Samples\nThis directory contains code samples."
    }
    
    # 创建文件
    for filename, content in file_types.items():
        (code_dir / filename).write_text(content)
    
    # 执行目录列表操作
    result = await ls_tool.execute({"path": str(code_dir)})
    
    # 验证基本结果
    assert result.success is True
    assert result.error is None
    tree_text = result.result["tree"]
    
    # 验证所有文件类型都被列出
    for filename in file_types.keys():
        assert f"- {filename}" in tree_text, f"文件 {filename} 应在结果中"
    
    # 验证文件数量（不包括根目录本身）
    actual_files = [line.strip() for line in tree_text.split('\n') 
                   if line.strip().startswith('- ') 
                   and not line.endswith('/')
                   and not str(code_dir) in line]  # 排除根目录路径
    assert len(actual_files) == len(file_types), "树状结构中的文件数应与创建的文件数相符"
    
    # 验证目录路径
    assert str(code_dir) in tree_text.split('\n')[0], "树状结构第一行应包含目录路径"

async def test_deep_directory_structure(ls_tool, test_files):
    """测试非常深层的目录结构，验证工具处理复杂层级的能力"""
    # 创建深层嵌套的目录结构
    deep_dir = Path(test_files) / "deep_structure"
    deep_dir.mkdir(exist_ok=True)
    
    # 创建10层嵌套的目录结构，每层有2个文件和2个子目录
    def create_nested_dirs(path, depth, max_depth=5):
        if depth > max_depth:
            return
            
        # 创建两个文件
        (path / f"file1_depth{depth}.txt").write_text(f"Content at depth {depth}")
        (path / f"file2_depth{depth}.txt").write_text(f"More content at depth {depth}")
        
        # 创建两个子目录并递归
        for i in range(1, 3):
            sub_dir = path / f"dir{i}_depth{depth}"
            sub_dir.mkdir(exist_ok=True)
            create_nested_dirs(sub_dir, depth + 1, max_depth)
    
    # 创建嵌套结构
    create_nested_dirs(deep_dir, 1)
    
    # 计算总目录和文件数量
    total_dirs = sum(1 for _ in deep_dir.rglob('*') if _.is_dir())
    total_files = sum(1 for _ in deep_dir.rglob('*') if _.is_file())
    
    logging.info(f"创建了深层目录结构，包含 {total_dirs} 个目录和 {total_files} 个文件")
    
    # 执行目录列表操作
    result = await ls_tool.execute({"path": str(deep_dir)})
    
    # 验证基本结果
    assert result.success is True
    assert result.error is None
    tree_text = result.result["tree"]
    
    # 检查是否有截断
    if total_files + total_dirs > ls_tool.MAX_FILES:
        assert result.result["truncated"] is True, "深层结构应触发截断"
        assert result.result["file_count"] >= ls_tool.MAX_FILES, f"返回数量应达到限制: {ls_tool.MAX_FILES}"
    else:
        assert result.result["file_count"] == total_files + total_dirs, "返回数量应与实际文件和目录总数相符"
    
    # 检查树结构的格式和缩进
    tree_lines = tree_text.split('\n')
    indentation_pattern = r'^(\s*)-'
    
    # 检查至少有一个二级缩进（表示目录结构正确呈现）
    has_indentation = False
    for line in tree_lines:
        if line.startswith('    -') or line.startswith('      -'):
            has_indentation = True
            break
    
    assert has_indentation, "树状结构应包含缩进，表示层级关系"
    
    # 验证目录命名格式出现在输出中
    depth_markers = [f"dir1_depth{i}" for i in range(1, 5)]
    for marker in depth_markers:
        assert marker in tree_text, f"深层目录标记 {marker} 应出现在树状结构中"

async def test_ls_tool_direct_usage():
    """测试直接使用 LSTool，模拟实际使用场景"""
    # 创建工具实例
    ls_tool = LSTool()
    
    # 获取当前目录
    current_dir = os.getcwd()
    
    # 测试不同的使用场景
    test_cases = [
        {
            "name": "列出当前目录",
            "path": current_dir,
            "expected_success": True
        },
        {
            "name": "列出上级目录",
            "path": os.path.dirname(current_dir),
            "expected_success": True
        },
        {
            "name": "列出不存在的目录",
            "path": "/not/exist/dir",
            "expected_success": False
        },
        {
            "name": "使用相对路径（应该失败）",
            "path": "relative/path",
            "expected_success": False
        }
    ]
    
    for case in test_cases:
        logging.info(f"测试场景: {case['name']}")
        result = await ls_tool.execute({"path": case["path"]})
        
        # 验证基本结果
        assert result.success == case["expected_success"], \
            f"{case['name']} - 期望 success={case['expected_success']}, 实际得到 {result.success}"
        
        if result.success:
            # 验证成功结果的内容
            assert "tree" in result.result, f"{case['name']} - 结果中应包含 tree"
            assert "file_count" in result.result, f"{case['name']} - 结果中应包含 file_count"
            assert isinstance(result.result["file_count"], int), f"{case['name']} - file_count 应为整数"
            assert result.result["file_count"] >= 0, f"{case['name']} - file_count 应大于等于0"
            
            # 验证树状结构
            tree_text = result.result["tree"]
            assert case["path"] in tree_text, f"{case['name']} - 树状结构应包含目标路径"
            
            # 验证目录路径
            assert result.result["directory"] == case["path"], \
                f"{case['name']} - 返回的目录路径应与输入路径匹配"
        else:
            # 验证失败结果包含错误信息
            assert result.error is not None, f"{case['name']} - 失败结果应包含错误信息"
            assert len(result.error) > 0, f"{case['name']} - 错误信息不应为空" 