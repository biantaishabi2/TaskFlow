"""
使用 AG2ToolManager 管理工具并分析项目目录
"""
import asyncio
import os
from pathlib import Path
from ag2_wrapper.core.ag2tools import AG2ToolManager
from ag2_wrapper.agent_tools.DispatchTool.dispatch_tool import DispatchTool

async def main():
    # 创建工具管理器
    tool_manager = AG2ToolManager()
    
    # 创建 DispatchTool 实例
    dispatch_tool = DispatchTool(work_dir="./workspace")
    
    # 设置分析目标目录和报告路径
    project_dir = "/home/wangbo/document/wangbo/task_planner"
    report_path = "project_analysis_report.md"
    
    # 构建分析任务
    analysis_prompt = f"""
请分析 {project_dir} 目录下的项目结构和内容，完成以下任务：

1. 使用 ls_tool 和 glob_tool 获取目录结构
2. 使用 grep_tool 搜索关键的代码文件和配置文件
3. 使用 file_read_tool 读取重要文件的内容
4. 整理分析结果，包括：
   - 项目的主要组件和功能
   - 关键文件的作用
   - 代码结构的组织方式
5. 使用 file_write_tool 将分析报告写入 {report_path}
6. 如果需要，使用 file_edit_tool 优化报告格式

请确保报告结构清晰，内容完整。完成后返回分析总结。
"""

    # 执行任务
    result = await dispatch_tool.execute({"prompt": analysis_prompt})
    
    # 打印结果
    if result.success:
        print("分析完成！")
        print("\n结论：")
        print(result.result["conclusion"])
        print(f"\n详细报告已保存到：{report_path}")
    else:
        print("分析失败！")
        print("错误：", result.error)

if __name__ == "__main__":
    asyncio.run(main())