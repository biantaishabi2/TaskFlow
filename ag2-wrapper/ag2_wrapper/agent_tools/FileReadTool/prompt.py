"""
FileReadTool 的提示词配置
"""

MAX_LINES_TO_READ = 2000
MAX_LINE_LENGTH = 2000

PROMPT = f"""读取本地文件系统中的文件内容。

使用此工具前请注意：

1. file_path 参数必须是绝对路径
2. 默认最多读取 {MAX_LINES_TO_READ} 行
3. 可以通过 offset 和 limit 参数来读取指定范围的内容
4. 单行超过 {MAX_LINE_LENGTH} 字符会被截断
5. 支持图片文件的读取和自动压缩
6. 对于 Jupyter notebook (.ipynb) 文件，请使用专门的 NotebookReadTool

多文件读取：
1. 可以在同一条消息中多次调用此工具来读取多个文件
2. 每个文件的读取是独立的，互不影响
3. 建议按照文件的相关性顺序读取，例如：
   - 先读取主文件，再读取相关的配置文件
   - 先读取父类文件，再读取子类文件
   - 先读取接口文件，再读取实现文件"""

DESCRIPTION = "从本地文件系统读取文件内容（支持文本和图片）" 