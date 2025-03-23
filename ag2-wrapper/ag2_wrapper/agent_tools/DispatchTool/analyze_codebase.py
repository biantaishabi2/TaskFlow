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
    target_dir = "/home/wangbo/document/wangbo/dev/think"
    
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
    请读取工作目录下deepseek_recursive_thinking.py的代码。不要看别的东西直接给分析结论！
    
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