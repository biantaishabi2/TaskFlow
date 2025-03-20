"""
FileWriteTool 的单元测试
"""
import os
import pytest
from pathlib import Path
from ag2_wrapper.agent_tools.FileWriteTool.file_write_tool import FileWriteTool

pytestmark = pytest.mark.asyncio  # 标记所有测试为异步测试

@pytest.fixture
def write_tool():
    """创建 FileWriteTool 实例"""
    return FileWriteTool()

@pytest.fixture
def temp_dir(tmp_path):
    """创建临时测试目录"""
    return tmp_path

@pytest.fixture
def existing_file(temp_dir):
    """创建一个已存在的测试文件"""
    file_path = temp_dir / "existing.txt"
    file_path.write_text("这是一个已存在的文件", encoding="utf-8")
    return file_path

async def test_create_new_file(write_tool, temp_dir):
    """测试创建新文件"""
    # 准备测试数据
    new_file = temp_dir / "new_file.txt"
    test_content = "这是测试内容\n包含多行\n测试换行符处理"
    
    # 执行测试
    result = await write_tool.execute({
        "path": str(new_file),
        "content": test_content
    })
    
    # 验证结果
    assert result.success is True
    assert result.error is None
    assert new_file.exists()
    assert new_file.read_text(encoding="utf-8") == test_content.replace("\n", os.linesep)

async def test_create_file_in_new_directory(write_tool, temp_dir):
    """测试在新目录中创建文件"""
    # 准备测试数据
    new_dir = temp_dir / "new_dir"
    new_file = new_dir / "test.txt"
    test_content = "测试内容"
    
    # 执行测试
    result = await write_tool.execute({
        "path": str(new_file),
        "content": test_content
    })
    
    # 验证结果
    assert result.success is True
    assert result.error is None
    assert new_dir.exists()
    assert new_file.exists()
    assert new_file.read_text(encoding="utf-8") == test_content

async def test_cannot_overwrite_existing_file(write_tool, existing_file):
    """测试不能覆盖已存在的文件"""
    # 准备测试数据
    test_content = "尝试覆盖已存在的文件"
    original_content = existing_file.read_text(encoding="utf-8")
    
    # 执行测试
    result = await write_tool.execute({
        "path": str(existing_file),
        "content": test_content
    })
    
    # 验证结果
    assert result.success is False
    assert "文件已存在" in result.error
    assert "EditFile" in result.error
    # 确认文件内容没有被修改
    assert existing_file.read_text(encoding="utf-8") == original_content

async def test_invalid_parameters(write_tool):
    """测试无效的参数"""
    # 测试缺少 path
    result = await write_tool.execute({
        "content": "测试内容"
    })
    assert result.success is False
    assert "path" in result.error.lower()
    
    # 测试缺少 content
    result = await write_tool.execute({
        "path": "test.txt"
    })
    assert result.success is False
    assert "content" in result.error.lower()

async def test_no_permission(write_tool, temp_dir):
    """测试没有写入权限的情况"""
    # 创建一个只读目录
    readonly_dir = temp_dir / "readonly"
    readonly_dir.mkdir()
    os.chmod(readonly_dir, 0o444)  # 设置为只读
    
    # 尝试在只读目录中创建文件
    test_file = readonly_dir / "test.txt"
    result = await write_tool.execute({
        "path": str(test_file),
        "content": "测试内容"
    })
    
    # 验证结果
    assert result.success is False
    assert "无权限" in result.error
    
    # 清理：恢复目录权限以便删除
    os.chmod(readonly_dir, 0o777)