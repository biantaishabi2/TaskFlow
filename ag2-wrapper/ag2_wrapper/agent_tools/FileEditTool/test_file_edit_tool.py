"""
FileEditTool 的单元测试
"""
import unittest
import pytest
from unittest.mock import patch, mock_open, MagicMock
from pathlib import Path
import os
import tempfile
import shutil
from datetime import datetime
import time

from ag2_wrapper.agent_tools.FileEditTool.file_edit_tool import FileEditTool
from ag2_wrapper.agent_tools.FileEditTool.utils import (
    apply_edit,
    get_snippet,
    detect_file_encoding,
    detect_line_endings,
    find_similar_file
)

class TestFileEditTool(unittest.TestCase):
    def setUp(self):
        """测试前的准备工作"""
        self.tool = FileEditTool()
        # 创建临时测试目录
        self.test_dir = Path(tempfile.mkdtemp())
        
    def tearDown(self):
        """测试后的清理工作"""
        # 清理临时测试目录
        shutil.rmtree(self.test_dir)
        
    def create_test_file(self, content: str, name: str = "test.txt") -> Path:
        """创建测试文件"""
        file_path = self.test_dir / name
        file_path.write_text(content)
        return file_path
        
    def test_validate_parameters_missing_params(self):
        """测试缺少参数的情况"""
        params = {}
        is_valid, error_msg = self.tool.validate_parameters(params)
        self.assertFalse(is_valid)
        self.assertIn("缺少必需参数", error_msg)
        
    def test_validate_parameters_wrong_type(self):
        """测试参数类型错误的情况"""
        params = {
            "file_path": 123,  # 应该是字符串
            "old_string": "old",
            "new_string": "new"
        }
        is_valid, error_msg = self.tool.validate_parameters(params)
        self.assertFalse(is_valid)
        self.assertIn("参数类型错误", error_msg)
        
    def test_validate_parameters_file_not_exists(self):
        """测试文件不存在的情况"""
        params = {
            "file_path": str(self.test_dir / "not_exists.txt"),
            "old_string": "old",
            "new_string": "new"
        }
        is_valid, error_msg = self.tool.validate_parameters(params)
        self.assertFalse(is_valid)
        self.assertIn("文件不存在", error_msg)
        
    def test_validate_parameters_valid(self):
        """测试有效参数的情况"""
        file_path = self.create_test_file("test content")
        str_path = str(file_path)
        params = {
            "file_path": str_path,
            "old_string": "test",
            "new_string": "new"
        }
        # 添加必需的 context 参数，包含有效的时间戳
        context = {'read_timestamps': {str_path: os.stat(str_path).st_mtime}}
        is_valid, error_msg = self.tool.validate_parameters(params, context)
        self.assertTrue(is_valid)
        self.assertEqual("", error_msg)
        
    def test_normalize_newlines(self):
        """测试换行符统一化"""
        content = "line1\r\nline2\rline3\nline4"
        normalized = self.tool._normalize_newlines(content)
        self.assertEqual(normalized.count("\n"), 3)
        self.assertNotIn("\r", normalized)
        
    def test_check_file_permission_no_dir(self):
        """测试目录不存在的情况"""
        path = self.test_dir / "subdir" / "test.txt"
        has_perm, msg = self.tool._check_file_permission(path)
        self.assertTrue(has_perm)  # 应该能创建目录
        self.assertTrue(path.parent.exists())
        
    @patch('os.access')
    def test_check_file_permission_no_write(self, mock_access):
        """测试无写入权限的情况"""
        mock_access.return_value = False
        file_path = self.create_test_file("test")
        has_perm, msg = self.tool._check_file_permission(file_path)
        self.assertFalse(has_perm)
        self.assertIn("无权限写入文件", msg)
        
    def test_verify_file_read_not_read(self):
        """测试文件未读取的情况"""
        file_path = str(self.create_test_file("test"))
        read_timestamps = {}
        is_read, msg = self.tool._verify_file_read(file_path, read_timestamps)
        self.assertFalse(is_read)
        self.assertIn("尚未被读取", msg)
        
    def test_verify_file_read_modified(self):
        """测试文件被修改的情况"""
        file_path = str(self.create_test_file("test"))
        read_timestamps = {file_path: datetime.now().timestamp() - 1}
        # 修改文件
        Path(file_path).write_text("modified")
        is_read, msg = self.tool._verify_file_read(file_path, read_timestamps)
        self.assertFalse(is_read)
        self.assertIn("被修改", msg)
        
    def test_verify_unique_match_not_found(self):
        """测试未找到匹配的情况"""
        is_unique, msg = self.tool._verify_unique_match("content", "not found")
        self.assertFalse(is_unique)
        self.assertIn("不存在", msg)
        
    def test_verify_unique_match_multiple(self):
        """测试多处匹配的情况"""
        is_unique, msg = self.tool._verify_unique_match("test test", "test")
        self.assertFalse(is_unique)
        self.assertIn("2 处匹配", msg)
        
    def test_verify_unique_match_single(self):
        """测试单一匹配的情况"""
        is_unique, msg = self.tool._verify_unique_match("test content", "test")
        self.assertTrue(is_unique)
        
    def test_validate_parameters_no_timestamp(self):
        """测试没有时间戳的情况"""
        file_path = self.create_test_file("test content")
        params = {
            "file_path": str(file_path),
            "old_string": "test",
            "new_string": "new"
        }
        context = {'read_timestamps': {}}
        
        is_valid, error_msg = self.tool.validate_parameters(params, context)
        self.assertFalse(is_valid)
        self.assertIn("尚未被读取", error_msg)
        
    def test_validate_parameters_with_timestamp(self):
        """测试有时间戳的情况"""
        file_path = self.create_test_file("test content")
        str_path = str(file_path)
        params = {
            "file_path": str_path,
            "old_string": "test",
            "new_string": "new"
        }
        
        # 设置时间戳为当前文件的修改时间
        context = {'read_timestamps': {str_path: os.stat(str_path).st_mtime}}
        
        is_valid, error_msg = self.tool.validate_parameters(params, context)
        self.assertTrue(is_valid)
        self.assertEqual("", error_msg)
        
    def test_validate_parameters_modified_after_read(self):
        """测试文件在读取后被修改的情况"""
        file_path = self.create_test_file("test content")
        str_path = str(file_path)
        params = {
            "file_path": str_path,
            "old_string": "test",
            "new_string": "new"
        }
        
        # 设置一个旧的时间戳
        context = {'read_timestamps': {str_path: os.stat(str_path).st_mtime}}
        
        # 修改文件
        time.sleep(0.1)  # 确保时间戳会变化
        file_path.write_text("modified content")
        
        is_valid, error_msg = self.tool.validate_parameters(params, context)
        self.assertFalse(is_valid)
        self.assertIn("在读取后被修改", error_msg)
        
    @pytest.mark.asyncio
    async def test_execute_create_new_file(self):
        """测试创建新文件"""
        new_file = self.test_dir / "new.txt"
        # 创建新文件不需要时间戳验证
        result = await self.tool.execute({
            "file_path": str(new_file),
            "old_string": "",
            "new_string": "new content"
        })
        self.assertTrue(result.success)
        self.assertTrue(new_file.exists())
        self.assertEqual(new_file.read_text(), "new content")
        
    @pytest.mark.asyncio
    async def test_execute_edit_file(self):
        """测试编辑文件"""
        file_path = self.create_test_file("old content")
        str_path = str(file_path)
        # 添加必需的 context 参数
        context = {'read_timestamps': {str_path: os.stat(str_path).st_mtime}}
        result = await self.tool.execute({
            "file_path": str_path,
            "old_string": "old",
            "new_string": "new"
        }, context)
        self.assertTrue(result.success)
        self.assertEqual(file_path.read_text(), "new content")
        
    @pytest.mark.asyncio
    async def test_execute_delete_content(self):
        """测试删除内容"""
        file_path = self.create_test_file("line1\nline2\nline3")
        str_path = str(file_path)
        # 添加必需的 context 参数
        context = {'read_timestamps': {str_path: os.stat(str_path).st_mtime}}
        result = await self.tool.execute({
            "file_path": str_path,
            "old_string": "line2\n",
            "new_string": ""
        }, context)
        self.assertTrue(result.success)
        self.assertEqual(file_path.read_text(), "line1\nline3")
        
    @pytest.mark.asyncio
    async def test_execute_updates_timestamp(self):
        """测试执行后更新时间戳"""
        # 创建测试文件
        file_path = self.create_test_file("test content")
        str_path = str(file_path)
        
        # 设置初始时间戳
        initial_mtime = os.stat(str_path).st_mtime
        context = {'read_timestamps': {str_path: initial_mtime}}
        
        # 执行编辑
        result = await self.tool.execute({
            "file_path": str_path,
            "old_string": "test",
            "new_string": "new"
        }, context)
        
        self.assertTrue(result.success)
        
        # 验证时间戳已更新
        self.assertGreater(context['read_timestamps'][str_path], initial_mtime)
        self.assertEqual(context['read_timestamps'][str_path], os.stat(str_path).st_mtime)
        
    @pytest.mark.asyncio
    async def test_execute_with_context_persistence(self):
        """测试 context 在多次编辑操作间的持久性"""
        # 创建测试文件
        file_path = self.create_test_file("test content")
        str_path = str(file_path)
        
        # 准备持久化的 context
        context = {'read_timestamps': {str_path: os.stat(str_path).st_mtime}}
        
        # 第一次编辑
        result1 = await self.tool.execute({
            "file_path": str_path,
            "old_string": "test",
            "new_string": "new"
        }, context)
        self.assertTrue(result1.success)
        first_timestamp = context['read_timestamps'][str_path]
        
        # 等待一下确保时间戳会变化
        time.sleep(0.1)
        
        # 第二次编辑
        result2 = await self.tool.execute({
            "file_path": str_path,
            "old_string": "new",
            "new_string": "modified"
        }, context)
        self.assertTrue(result2.success)
        
        # 验证时间戳被更新
        self.assertGreater(context['read_timestamps'][str_path], first_timestamp)
        self.assertEqual(context['read_timestamps'][str_path], os.stat(str_path).st_mtime)

class TestUtils(unittest.TestCase):
    def setUp(self):
        """测试前的准备工作"""
        self.test_dir = Path(tempfile.mkdtemp())
        
    def tearDown(self):
        """测试后的清理工作"""
        shutil.rmtree(self.test_dir)
        
    def create_test_file(self, content: str, name: str = "test.txt") -> Path:
        """创建测试文件"""
        file_path = self.test_dir / name
        file_path.write_text(content)
        return file_path
        
    def test_apply_edit_create_new(self):
        """测试创建新文件的编辑"""
        file_path = str(self.test_dir / "new.txt")
        patch, content = apply_edit(file_path, "", "new content")
        self.assertEqual(content, "new content")
        self.assertTrue(patch)  # 应该有补丁内容
        
    def test_apply_edit_modify(self):
        """测试修改文件的编辑"""
        file_path = self.create_test_file("old content")
        patch, content = apply_edit(str(file_path), "old", "new")
        self.assertEqual(content, "new content")
        self.assertTrue(patch)
        
    def test_apply_edit_delete(self):
        """测试删除内容的编辑"""
        file_path = self.create_test_file("line1\nline2\nline3")
        patch, content = apply_edit(str(file_path), "line2\n", "")
        self.assertEqual(content, "line1\nline3")
        self.assertTrue(patch)
        
    def test_get_snippet_new_file(self):
        """测试新文件的片段获取"""
        result = get_snippet("", "", "new content")
        self.assertEqual(result["snippet"], "new content")
        self.assertEqual(result["start_line"], 1)
        
    def test_get_snippet_with_context(self):
        """测试带上下文的片段获取"""
        content = "\n".join([f"line{i}" for i in range(1, 10)])
        result = get_snippet(content, "line5", "new5", n_lines=2)
        self.assertEqual(result["start_line"], 4)  # 应该从第4行开始
        self.assertEqual(len(result["snippet"].splitlines()), 5)  # 应该有5行
        
    def test_detect_file_encoding_utf8(self):
        """测试 UTF-8 编码检测"""
        file_path = self.create_test_file("测试内容")
        encoding = detect_file_encoding(file_path)
        self.assertEqual(encoding, "utf-8")
        
    def test_detect_line_endings_mixed(self):
        """测试混合换行符检测"""
        content = b"line1\r\nline2\r\nline3\nline4\n"
        file_path = self.test_dir / "test.txt"
        file_path.write_bytes(content)
        endings = detect_line_endings(file_path)
        self.assertEqual(endings, "CRLF")  # 应该选择占多数的类型
        
    def test_find_similar_file(self):
        """测试相似文件查找"""
        # 创建一些测试文件
        self.create_test_file("content", "test.txt")
        self.create_test_file("content", "test.py")
        
        # 查找不存在的 .js 文件的相似文件
        similar = find_similar_file(self.test_dir / "test.js")
        self.assertIsNotNone(similar)
        self.assertTrue(similar.endswith((".txt", ".py")))
        
if __name__ == '__main__':
    unittest.main() 