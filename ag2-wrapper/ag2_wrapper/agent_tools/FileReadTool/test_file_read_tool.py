"""
FileReadTool 的单元测试
"""
import unittest
import pytest
from unittest.mock import patch, mock_open, MagicMock
from pathlib import Path
import os
import io
from PIL import Image
import base64
import time
from ag2_wrapper.agent_tools.FileReadTool.file_read_tool import FileReadTool

class TestFileReadTool(unittest.TestCase):
    def setUp(self):
        """测试前的准备工作"""
        self.tool = FileReadTool()
        self.test_dir = Path(__file__).parent / "test_files"
        self.test_dir.mkdir(exist_ok=True)
        
    def tearDown(self):
        """测试后的清理工作"""
        # 清理测试文件
        if self.test_dir.exists():
            for file in self.test_dir.iterdir():
                file.unlink()
            self.test_dir.rmdir()
            
    def create_test_text_file(self, content: str) -> Path:
        """创建测试文本文件"""
        file_path = self.test_dir / "test.txt"
        file_path.write_text(content)
        return file_path
        
    def create_test_image_file(self) -> Path:
        """创建测试图片文件"""
        file_path = self.test_dir / "test.png"
        img = Image.new('RGB', (100, 100), color='red')
        img.save(file_path)
        return file_path
        
    def test_validate_parameters_missing_file_path(self):
        """测试缺少 file_path 参数的情况"""
        params = {}
        is_valid, error_msg = self.tool.validate_parameters(params)
        self.assertFalse(is_valid)
        self.assertIn("必须提供 file_path 参数", error_msg)
        
    def test_validate_parameters_file_not_exists(self):
        """测试文件不存在的情况"""
        params = {"file_path": str(self.test_dir / "not_exists.txt")}
        is_valid, error_msg = self.tool.validate_parameters(params)
        self.assertFalse(is_valid)
        self.assertIn("文件不存在", error_msg)
        
    def test_validate_parameters_file_too_large(self):
        """测试文本文件过大的情况"""
        file_path = self.test_dir / "large.txt"
        content = "x" * int(self.tool.TEXT_FILE_SIZE_LIMIT + 1)
        file_path.write_text(content)
        
        params = {"file_path": str(file_path)}
        is_valid, error_msg = self.tool.validate_parameters(params)
        self.assertFalse(is_valid)
        self.assertIn("文件过大", error_msg)
        
    def test_validate_parameters_valid_file(self):
        """测试有效文件的情况"""
        file_path = self.create_test_text_file("test content")
        params = {"file_path": str(file_path)}
        is_valid, error_msg = self.tool.validate_parameters(params)
        self.assertTrue(is_valid)
        
    def test_is_image_file(self):
        """测试图片文件类型判断"""
        for ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp']:
            path = Path(f"test{ext}")
            self.assertTrue(self.tool._is_image_file(path))
            
        self.assertFalse(self.tool._is_image_file(Path("test.txt")))
        
    def test_find_similar_file(self):
        """测试相似文件查找"""
        file1 = self.test_dir / "test.txt"
        file2 = self.test_dir / "test.bak"
        file1.touch()
        file2.touch()
        
        similar = self.tool._find_similar_file(self.test_dir / "test.doc")
        self.assertIsNotNone(similar)
        self.assertTrue(similar.endswith((".txt", ".bak")))
        
    def test_read_text_file(self):
        """测试文本文件读取"""
        test_content = "line1\nline2\nline3\n"
        file_path = self.create_test_text_file(test_content)
        
        content, metadata = self.tool._read_text_file(file_path)
        
        self.assertEqual(content, test_content)
        self.assertEqual(metadata["line_count"], 3)
        self.assertEqual(metadata["total_lines"], 3)
        self.assertEqual(metadata["start_line"], 1)
        
    def test_read_text_file_with_offset_limit(self):
        """测试带偏移和限制的文本文件读取"""
        content = "\n".join(f"line{i}" for i in range(1, 6))
        file_path = self.create_test_text_file(content)
        
        # 测试 offset
        content, metadata = self.tool._read_text_file(file_path, offset=2)
        self.assertEqual(metadata["start_line"], 2)
        self.assertTrue(content.startswith("line2"))
        
        # 测试 limit
        content, metadata = self.tool._read_text_file(file_path, limit=2)
        self.assertEqual(metadata["line_count"], 2)
        
    @unittest.skipIf(not FileReadTool.HAS_PIL, "PIL not available")
    def test_read_image_file(self):
        """测试图片文件读取"""
        file_path = self.create_test_image_file()
        content, metadata = self.tool._read_image_file(file_path)
        
        self.assertIsInstance(content, bytes)
        self.assertIn("original_size", metadata)
        self.assertIn("final_size", metadata)
        
    def test_format_result_text(self):
        """测试文本结果格式化"""
        result = self.tool._format_result(
            content="test content",
            file_path="/path/to/file.txt",
            is_image=False,
            line_count=1,
            total_lines=1
        )
        
        self.assertEqual(result["type"], "text")
        self.assertEqual(result["file"]["content"], "test content")
        self.assertEqual(result["file"]["numLines"], 1)
        
    def test_format_result_image(self):
        """测试图片结果格式化"""
        result = self.tool._format_result(
            content=b"image data",
            file_path="/path/to/file.png",
            is_image=True
        )
        
        self.assertEqual(result["type"], "image")
        self.assertTrue(result["file"]["base64"])
        self.assertEqual(result["file"]["type"], "image/png")
        
    @pytest.mark.asyncio
    async def test_execute_text_file(self):
        """测试执行文本文件读取"""
        file_path = self.create_test_text_file("test content")
        result = await self.tool.execute({"file_path": str(file_path)})
        
        self.assertTrue(result.success)
        self.assertEqual(result.result["type"], "text")
        self.assertEqual(result.result["file"]["content"], "test content")
        
    @pytest.mark.asyncio
    async def test_execute_image_file(self):
        """测试执行图片文件读取"""
        file_path = self.create_test_image_file()
        result = await self.tool.execute({"file_path": str(file_path)})
        
        self.assertTrue(result.success)
        self.assertEqual(result.result["type"], "image")
        self.assertTrue(result.result["file"]["base64"])
        
    @pytest.mark.asyncio
    async def test_execute_invalid_params(self):
        """测试执行参数无效的情况"""
        result = await self.tool.execute({})
        self.assertFalse(result.success)
        self.assertIsNotNone(result.error)
        
    @pytest.mark.asyncio
    async def test_execute_no_permission(self):
        """测试执行无权限的情况"""
        file_path = self.create_test_text_file("test")
        os.chmod(file_path, 0o000)
        
        result = await self.tool.execute({"file_path": str(file_path)})
        self.assertFalse(result.success)
        self.assertIn("权限", result.error)
        
        os.chmod(file_path, 0o666)
        
    @pytest.mark.asyncio
    async def test_execute_with_timestamps(self):
        """测试执行时的时间戳更新机制"""
        # 创建测试文件
        file_path = self.create_test_text_file("test content")
        str_path = str(file_path)
        
        # 准备 context
        context = {'read_timestamps': {}}
        
        # 第一次执行，应该更新时间戳
        result = await self.tool.execute({"file_path": str_path}, context)
        self.assertTrue(result.success)
        self.assertIn(str_path, context['read_timestamps'])
        
        # 记录第一次的时间戳
        first_timestamp = context['read_timestamps'][str_path]
        
        # 修改文件
        time.sleep(0.1)  # 确保时间戳会变化
        file_path.write_text("modified content")
        
        # 再次执行，应该更新为新的时间戳
        result = await self.tool.execute({"file_path": str_path}, context)
        self.assertTrue(result.success)
        self.assertGreater(context['read_timestamps'][str_path], first_timestamp)
        
    def test_verify_file_read_not_read(self):
        """测试验证未读取文件的情况"""
        file_path = self.create_test_text_file("test content")
        context = {'read_timestamps': {}}
        
        is_valid, error_msg = self.tool._verify_file_read(str(file_path), context['read_timestamps'])
        self.assertFalse(is_valid)
        self.assertIn("文件尚未被读取", error_msg)
        
    def test_verify_file_read_modified(self):
        """测试验证文件被修改的情况"""
        # 创建测试文件
        file_path = self.create_test_text_file("test content")
        str_path = str(file_path)
        
        # 记录初始时间戳
        context = {'read_timestamps': {str_path: os.stat(str_path).st_mtime}}
        
        # 修改文件
        time.sleep(0.1)  # 确保时间戳会变化
        file_path.write_text("modified content")
        
        # 验证
        is_valid, error_msg = self.tool._verify_file_read(str_path, context['read_timestamps'])
        self.assertFalse(is_valid)
        self.assertIn("文件在上次读取后被修改", error_msg)
        
    def test_verify_file_read_valid(self):
        """测试验证有效的文件读取"""
        # 创建测试文件
        file_path = self.create_test_text_file("test content")
        str_path = str(file_path)
        
        # 记录当前时间戳
        current_mtime = os.stat(str_path).st_mtime
        context = {'read_timestamps': {str_path: current_mtime}}
        
        # 验证
        is_valid, error_msg = self.tool._verify_file_read(str_path, context['read_timestamps'])
        self.assertTrue(is_valid)
        self.assertEqual("", error_msg)
        
    @pytest.mark.asyncio
    async def test_execute_with_context_persistence(self):
        """测试 context 在多次调用间的持久性"""
        # 创建测试文件
        file_path = self.create_test_text_file("test content")
        str_path = str(file_path)
        
        # 准备持久化的 context
        context = {'read_timestamps': {}}
        
        # 第一次执行
        result1 = await self.tool.execute({"file_path": str_path}, context)
        self.assertTrue(result1.success)
        
        # 保存第一次的时间戳
        first_timestamp = context['read_timestamps'][str_path]
        
        # 第二次执行（不修改文件）
        result2 = await self.tool.execute({"file_path": str_path}, context)
        self.assertTrue(result2.success)
        
        # 验证时间戳没有不必要的更新
        self.assertEqual(first_timestamp, context['read_timestamps'][str_path])
        
if __name__ == '__main__':
    unittest.main() 