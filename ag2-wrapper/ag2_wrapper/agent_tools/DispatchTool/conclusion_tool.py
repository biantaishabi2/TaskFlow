from typing import Dict, Any
from ...core.base_tool import BaseTool, ToolCallResult

# 添加提示词常量
PROMPT = """这是一个用于返回任务执行结论的工具。当你完成了所有任务后,必须使用此工具返回最终结论。

使用说明:
1. 此工具必须是你调用的最后一个工具
2. 调用此工具后,对话将结束并返回结论
3. 在返回结论前,请确保:
   - 所有必要的任务都已完成
   - 已收集到所有需要的信息
   - 结论已经过充分整理和总结

参数说明:
1. success (必需,布尔值):
   - True: 表示任务成功完成
   - False: 表示任务执行失败
   
2. conclusion (必需,字符串):
   - 如果成功: 提供完整的任务执行总结,包括:
     * 完成了哪些具体任务
     * 得到了什么重要发现
     * 最终的分析结论
   - 如果失败: 详细说明:
     * 失败的具体原因
     * 遇到了什么问题
     * 建议的解决方案

示例:
成功情况:
{
    "success": true,
    "conclusion": "完成了项目分析任务:
    1. 已分析了所有核心代码文件
    2. 发现项目主要包含3个核心模块
    3. 代码结构清晰,文档完整
    建议: 可以考虑添加更多单元测试"
}

失败情况:
{
    "success": false,
    "conclusion": "任务执行失败:
    1. 无法访问关键配置文件
    2. 缺少必要的依赖项
    建议: 请确保配置文件权限正确并安装所需依赖"
}"""

class ConclusionTool(BaseTool):
    """结论返回工具 - 用于Assistant返回调研结论"""
    
    def __init__(self):
        super().__init__(
            name="return_conclusion",
            description="返回调研结论的工具",
            prompt=PROMPT,  # 添加提示词
            parameters={
                "success": {
                    "type": "bool",
                    "required": True,
                    "description": "调研是否成功"
                },
                "conclusion": {
                    "type": "str",
                    "required": True,
                    "description": "调研结论或失败原因"
                }
            },
            metadata={
                "read_only": True,
                "is_termination": True  # 添加终止标记
            }
        )
    
    async def execute(self, params: Dict[str, Any]) -> ToolCallResult:
        # 验证参数
        if not isinstance(params.get("success"), bool):
            raise Exception("success 参数必须是布尔类型")
        
        if not params.get("conclusion") or not isinstance(params.get("conclusion"), str):
            raise Exception("conclusion 参数必须是非空字符串")
            
        return ToolCallResult(
            success=True,
            result={
                "success": params["success"],
                "conclusion": params["conclusion"]
            },
            should_terminate=True  # 添加终止标记
        )