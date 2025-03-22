"""
FileReadTool 的提示词配置
"""

MAX_LINES_TO_READ = 2000
MAX_LINE_LENGTH = 2000

# 基本提示词
BASE_PROMPT = f"""读取本地文件系统中的文件内容。

使用此工具前请注意：

1. file_path 参数必须是绝对路径
2. 默认最多读取 {MAX_LINES_TO_READ} 行
3. 可以通过 start_line 和 end_line 参数来读取指定范围的内容
4. 单行超过 {MAX_LINE_LENGTH} 字符会被截断
5. 支持图片文件的读取和自动压缩
6. 对于 Jupyter notebook (.ipynb) 文件，请使用专门的 NotebookReadTool
7. 【重要】调用此工具时必须提供context参数，包含read_timestamps字典

文件安全机制：
1. 系统会自动跟踪文件的读取和修改时间戳
2. 编辑文件前必须先通过此工具读取文件
3. 这种机制确保文件操作的安全性，防止编辑未经审查的文件

多文件读取：
1. 可以在同一条消息中多次调用此工具来读取多个文件
2. 每个文件的读取是独立的，互不影响
3. 建议按照文件的相关性顺序读取，例如：
   - 先读取主文件，再读取相关的配置文件
   - 先读取父类文件，再读取子类文件
   - 先读取接口文件，再读取实现文件"""

# 示例代码
EXAMPLE_CODE = """
正确的调用格式：
```json
{
    "file_path": "/path/to/your/file.txt",
    "start_line": 1,  // 可选
    "end_line": 100,  // 可选
    "context": {
        "read_timestamps": {}
    }
}
```

错误的调用格式（会导致错误）：
```json
{
    "file_path": "/path/to/your/file.txt"
}
```

注意事项：
1. context 参数是必需的，必须包含 read_timestamps 字典
2. start_line 和 end_line 是可选参数
3. read_timestamps 用于跟踪文件的读取历史"""

# 组合完整提示词
PROMPT = BASE_PROMPT + "\n" + EXAMPLE_CODE

DESCRIPTION = "从本地文件系统读取文件内容（支持文本和图片）" 