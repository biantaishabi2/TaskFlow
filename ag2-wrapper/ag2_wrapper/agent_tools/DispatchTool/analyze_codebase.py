import asyncio
import os
import logging
from pathlib import Path
from ag2_wrapper.agent_tools.DispatchTool.dispatch_tool import DispatchTool

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def main():
    # 确保设置了必要的环境变量
    if not os.environ.get("OPENROUTER_API_KEY"):
        raise ValueError("请先设置 OPENROUTER_API_KEY 环境变量")

    # 设置要分析的目录路径
    target_dir = "/home/wangbo/document/wangbo/dev/webhook"
    
    # 确保目标目录存在
    if not os.path.exists(target_dir):
        raise ValueError(f"目标目录不存在: {target_dir}")
    
    # 初始化 DispatchTool，将工作目录设置为目标目录
    dispatch_tool = DispatchTool(
        work_dir=target_dir,  # 设置工作目录为目标分析目录
        use_docker=False
    )

    # 准备分析任务的提示词
    prompt = """
    请使用工具分析工作目录下的所有文件和文件夹结构。

    要求：
    1. 使用 ls 工具列出目录结构，参数 path="."
    2. 使用 glob 工具查找所有源代码文件
    3. 使用 grep 工具搜索关键函数和类定义
    4. 使用 file_read 工具读取重要文件的内容

    需要提供的信息：
    1. 主要的文件和目录结构
    2. 每个主要文件的功能和作用
    3. 代码库的主要功能和特点
    4. 发现的任何潜在问题或改进建议
    
    注意：所有工具调用都应该使用相对于工作目录的路径。
    最后使用 return_conclusion 工具返回分析结论。
    """

    try:
        # 执行分析任务
        result = await dispatch_tool.execute({"prompt": prompt})
        
        # 打印结果
        if result.success:
            print("\n=== 分析结果 ===")
            print(result.result["conclusion"])
        else:
            print("\n=== 分析失败 ===")
            print(f"错误信息: {result.error}")
            
    except Exception as e:
        print(f"执行过程中发生错误: {str(e)}")

if __name__ == "__main__":
    # 运行主函数
    asyncio.run(main()) 