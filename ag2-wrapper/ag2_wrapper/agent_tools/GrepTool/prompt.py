"""
GrepTool 的提示词配置
"""

TOOL_NAME_FOR_PROMPT = "GrepTool"

DESCRIPTION = """
- 快速内容搜索工具，适用于任何规模的代码库
- 使用正则表达式搜索文件内容
- 支持完整的正则表达式语法（如 "log.*Error"、"function\\s+\\w+"等）
- 可通过include参数按文件模式过滤（如 "*.js"、"*.{ts,tsx}"）
- 返回按修改时间排序的匹配文件路径
- 当需要查找包含特定模式的文件时使用此工具
- 如果需要进行多轮glob和grep的开放式搜索，请使用Agent工具
"""

PROMPT = """使用正则表达式在代码库中搜索文件内容。

使用此工具前请注意：

1. 支持完整的正则表达式语法（如 "log.*Error"、"function\\s+\\w+"）
2. 默认返回最多100个匹配结果
3. 结果按文件修改时间排序
4. 可以通过include参数指定文件类型过滤（如 "*.js"、"*.{ts,tsx}"）
5. 建议使用具体的搜索路径来缩小范围
6. 对于需要多轮搜索的场景，建议使用Agent工具""" 