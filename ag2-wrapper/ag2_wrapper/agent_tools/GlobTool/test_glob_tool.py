"""
GlobTool 的单元测试
"""
import unittest
import pytest
from unittest.mock import patch, mock_open, MagicMock
from pathlib import Path
import os
import tempfile
import shutil
import time

from ag2_wrapper.core.base_tool import BaseTool, ToolCallResult
from ag2_wrapper.agent_tools.GlobTool.glob_tool import GlobTool, GlobOutput

class TestGlobTool(unittest.TestCase):
    def setUp(self):
        """测试前的准备工作"""
        self.tool = GlobTool()
        # 创建临时测试目录
        self.test_dir = Path(tempfile.mkdtemp())
        # 保存原始工作目录
        self.original_cwd = os.getcwd()
        
    def tearDown(self):
        """测试后的清理工作"""
        # 恢复原始工作目录
        os.chdir(self.original_cwd)
        # 清理临时测试目录
        shutil.rmtree(self.test_dir)
        
    def create_test_files(self) -> None:
        """创建测试文件结构"""
        # 创建一些测试文件
        (self.test_dir / "src").mkdir()
        (self.test_dir / "src/test1.js").write_text("test1")
        (self.test_dir / "src/test2.js").write_text("test2")
        (self.test_dir / "src/sub").mkdir()
        (self.test_dir / "src/sub/test3.ts").write_text("test3")
        (self.test_dir / "test4.py").write_text("test4")
        
        # 添加更多真实文件场景
        (self.test_dir / "docs").mkdir()
        (self.test_dir / "docs/README.md").write_text("# Documentation")
        (self.test_dir / "docs/api.md").write_text("API docs")
        (self.test_dir / "config").mkdir()
        (self.test_dir / "config/settings.json").write_text('{"debug": true}')
        (self.test_dir / "config/dev.yaml").write_text("debug: true")
        (self.test_dir / "tests").mkdir()
        (self.test_dir / "tests/test_main.py").write_text("def test_main(): pass")
        (self.test_dir / "tests/test_utils.py").write_text("def test_utils(): pass")
        
    def test_init_parameters(self):
        """测试初始化参数配置"""
        self.assertEqual(self.tool.DEFAULT_LIMIT, 100)
        self.assertEqual(len(self.tool.parameters), 2)  # pattern 和 path
        self.assertTrue(self.tool.parameters["pattern"]["required"])
        self.assertFalse(self.tool.parameters["path"]["required"])
        
    def test_has_read_permission_valid(self):
        """测试有效的目录读取权限"""
        self.create_test_files()
        self.assertTrue(self.tool._has_read_permission(self.test_dir))
        
    @patch('os.access')
    def test_has_read_permission_invalid(self, mock_access):
        """测试无效的目录读取权限"""
        mock_access.return_value = False
        self.assertFalse(self.tool._has_read_permission(self.test_dir))
        
    def test_get_files_with_mtime(self):
        """测试获取文件及其修改时间"""
        self.create_test_files()
        files = self.tool._get_files_with_mtime("**/*.js", self.test_dir)
        self.assertEqual(len(files), 2)  # 应该找到2个 .js 文件
        self.assertTrue(all(isinstance(f[1], float) for f in files))  # 检查时间戳类型
        
    def test_format_path_relative(self):
        """测试相对路径格式化"""
        self.create_test_files()
        path = str(self.test_dir / "src/test1.js")
        formatted = self.tool._format_path(path, self.test_dir)
        self.assertEqual(formatted, "src/test1.js")
        
    def test_format_path_absolute(self):
        """测试绝对路径格式化"""
        self.create_test_files()
        path = str(self.test_dir / "src/test1.js")
        formatted = self.tool._format_path(path, self.test_dir, verbose=True)
        self.assertEqual(formatted, str(Path(path).resolve()))
        
    def test_format_result_empty(self):
        """测试空结果的格式化"""
        output = GlobOutput(
            filenames=[],
            durationMs=100.0,
            numFiles=0,
            truncated=False
        )
        result = self.tool._format_result_for_assistant(output)
        self.assertEqual(result, "未找到匹配的文件")
        
    def test_format_result_truncated(self):
        """测试被截断的结果格式化"""
        output = GlobOutput(
            filenames=["file1.js", "file2.js"],
            durationMs=100.0,
            numFiles=2,
            truncated=True
        )
        result = self.tool._format_result_for_assistant(output)
        self.assertIn("file1.js", result)
        self.assertIn("file2.js", result)
        self.assertIn("结果已截断", result)
        
    @pytest.mark.asyncio
    async def test_execute_no_permission(self):
        """测试无权限目录的执行"""
        with patch.object(GlobTool, '_has_read_permission', return_value=False):
            result = await self.tool.execute({
                "pattern": "**/*.js",
                "path": str(self.test_dir)
            })
            self.assertFalse(result.success)
            self.assertIn("无权限访问目录", str(result.error))
            
    @pytest.mark.asyncio
    async def test_execute_valid_search(self):
        """测试有效的搜索执行"""
        self.create_test_files()
        result = await self.tool.execute({
            "pattern": "**/*.js",
            "path": str(self.test_dir)
        })
        self.assertTrue(result.success)
        self.assertIsInstance(result.result, dict)
        self.assertEqual(result.result["numFiles"], 2)
        self.assertFalse(result.result["truncated"])
        
    @pytest.mark.asyncio
    async def test_execute_truncated_results(self):
        """测试结果截断的情况"""
        self.create_test_files()
        # 临时修改默认限制为1
        self.tool.DEFAULT_LIMIT = 1
        result = await self.tool.execute({
            "pattern": "**/*.*",
            "path": str(self.test_dir)
        })
        self.assertTrue(result.success)
        self.assertEqual(len(result.result["filenames"]), 1)
        self.assertTrue(result.result["truncated"])
        
    @pytest.mark.asyncio
    async def test_execute_sort_by_mtime(self):
        """测试按修改时间排序"""
        self.create_test_files()
        # 修改一个文件的时间
        test_file = self.test_dir / "src/test1.js"
        os.utime(test_file, (time.time(), time.time()))
        
        result = await self.tool.execute({
            "pattern": "**/*.js",
            "path": str(self.test_dir)
        })
        self.assertTrue(result.success)
        self.assertEqual(result.result["filenames"][0], "src/test1.js")
        
    @pytest.mark.asyncio
    async def test_execute_with_error(self):
        """测试执行出错的情况"""
        with patch.object(GlobTool, '_get_files_with_mtime', side_effect=Exception("测试错误")):
            result = await self.tool.execute({
                "pattern": "**/*.js",
                "path": str(self.test_dir)
            })
            self.assertFalse(result.success)
            self.assertIn("搜索文件失败", str(result.error))
            
    def test_multiple_patterns(self):
        """测试多种模式匹配"""
        self.create_test_files()
        patterns_and_expected = [
            ("**/*.js", 2),   # JavaScript 文件
            ("**/*.ts", 1),   # TypeScript 文件
            ("**/*.py", 3),   # Python 文件 (test4.py + 2个测试文件)
            ("src/**/*", 4),  # src 目录下所有文件（包括目录本身）
            ("**/sub/*", 1),  # sub 目录下所有文件
            ("docs/*.md", 2),  # 文档文件
            ("config/*.*", 2),  # 配置文件
            ("tests/test_*.py", 2),  # 测试文件
            ("src/**/*.js", 2),  # src 目录下的 JavaScript 文件
            ("config/*.json", 1),  # JSON 配置文件
            ("config/*.yaml", 1),  # YAML 配置文件
        ]
        
        for pattern, expected_count in patterns_and_expected:
            files = self.tool._get_files_with_mtime(pattern, self.test_dir)
            self.assertEqual(len(files), expected_count, 
                           f"模式 '{pattern}' 应该匹配 {expected_count} 个文件")

    @pytest.mark.asyncio
    async def test_execute_default_cwd(self):
        """测试使用默认工作目录"""
        self.create_test_files()
        # 切换到测试目录
        os.chdir(self.test_dir)
        
        result = await self.tool.execute({
            "pattern": "**/*.js"
            # 不指定 path，应该使用当前工作目录
        })
        self.assertTrue(result.success)
        self.assertEqual(result.result["numFiles"], 2)
        self.assertIn("src/test1.js", result.result["filenames"])
        self.assertIn("src/test2.js", result.result["filenames"])
        
    @pytest.mark.asyncio
    async def test_execute_with_relative_path(self):
        """测试使用相对路径"""
        self.create_test_files()
        os.chdir(self.test_dir)
        
        result = await self.tool.execute({
            "pattern": "**/*.ts",
            "path": "src"  # 使用相对路径
        })
        self.assertTrue(result.success)
        self.assertEqual(result.result["numFiles"], 1)
        self.assertEqual(result.result["filenames"][0], "sub/test3.ts")
        
    @pytest.mark.asyncio
    async def test_execute_with_absolute_path(self):
        """测试使用绝对路径"""
        self.create_test_files()
        # 使用绝对路径，不需要切换工作目录
        result = await self.tool.execute({
            "pattern": "**/*.py",
            "path": str(self.test_dir)  # 使用绝对路径
        })
        self.assertTrue(result.success)
        self.assertEqual(result.result["numFiles"], 1)
        self.assertEqual(result.result["filenames"][0], "test4.py")
        
    @pytest.mark.asyncio
    async def test_execute_nested_cwd(self):
        """测试在嵌套目录中使用"""
        self.create_test_files()
        # 切换到嵌套的 src 目录
        os.chdir(self.test_dir / "src")
        
        result = await self.tool.execute({
            "pattern": "**/*.ts"
            # 不指定 path，应该从 src 目录开始搜索
        })
        self.assertTrue(result.success)
        self.assertEqual(result.result["numFiles"], 1)
        self.assertEqual(result.result["filenames"][0], "sub/test3.ts")
        
    @pytest.mark.asyncio
    async def test_execute_parent_path(self):
        """测试使用父目录路径"""
        self.create_test_files()
        # 切换到 src/sub 目录
        os.chdir(self.test_dir / "src" / "sub")
        
        result = await self.tool.execute({
            "pattern": "*.js",
            "path": ".."  # 使用父目录
        })
        self.assertTrue(result.success)
        self.assertEqual(result.result["numFiles"], 2)
        self.assertTrue(all(f.endswith('.js') for f in result.result["filenames"]))

    @pytest.mark.asyncio
    async def test_tool_usage_examples(self):
        """测试工具的实际使用场景"""
        self.create_test_files()
        os.chdir(self.test_dir)
        
        # 测试场景1：搜索所有 Python 文件
        result = await self.tool.execute({
            "pattern": "**/*.py"
        })
        self.assertTrue(result.success)
        self.assertEqual(result.result["numFiles"], 3)
        self.assertTrue(any("test4.py" in f for f in result.result["filenames"]))
        self.assertTrue(any("test_main.py" in f for f in result.result["filenames"]))
        
        # 测试场景2：在特定目录下搜索
        result = await self.tool.execute({
            "pattern": "*.md",
            "path": "docs"
        })
        self.assertTrue(result.success)
        self.assertEqual(result.result["numFiles"], 2)
        self.assertTrue(all(f.endswith(".md") for f in result.result["filenames"]))
        
        # 测试场景3：使用多级目录模式
        result = await self.tool.execute({
            "pattern": "src/**/*.js"
        })
        self.assertTrue(result.success)
        self.assertEqual(result.result["numFiles"], 2)
        self.assertTrue(all("src" in f for f in result.result["filenames"]))
        
        # 测试场景4：使用文件名通配符
        result = await self.tool.execute({
            "pattern": "tests/test_*.py"
        })
        self.assertTrue(result.success)
        self.assertEqual(result.result["numFiles"], 2)
        self.assertTrue(all(f.startswith("tests/test_") for f in result.result["filenames"]))
        
        # 测试场景5：搜索配置文件（分别搜索不同类型）
        result = await self.tool.execute({
            "pattern": "config/*.json"
        })
        self.assertTrue(result.success)
        self.assertEqual(result.result["numFiles"], 1)
        self.assertTrue(any(f.endswith(".json") for f in result.result["filenames"]))
        
        result = await self.tool.execute({
            "pattern": "config/*.yaml"
        })
        self.assertTrue(result.success)
        self.assertEqual(result.result["numFiles"], 1)
        self.assertTrue(any(f.endswith(".yaml") for f in result.result["filenames"]))

if __name__ == '__main__':
    unittest.main() 