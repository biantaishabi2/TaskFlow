"""
时间戳传递测试 - 完整版
测试 AG2 执行器中的时间戳传递机制
"""
import os
import sys
import logging
from pathlib import Path
import tempfile
import asyncio

# 配置日志级别
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.append(str(project_root))

from ag2_wrapper.agent_tools.FileReadTool.file_read_tool import FileReadTool
from ag2_wrapper.agent_tools.FileEditTool.file_edit_tool import FileEditTool
from ag2_wrapper.core.ag2_two_agent_executor import AG2TwoAgentExecutor

async def test_timestamp_fixed():
    """测试修复后的时间戳传递"""
    
    print("\n==== 精简版时间戳测试开始 ====")
    
    # 创建临时文件
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.txt') as temp:
        temp.write("测试内容\n第二行\n")
        temp_path = temp.name
    
    try:
        # 初始化工具和共享的时间戳字典
        shared_timestamps = {}
        read_tool = FileReadTool()
        edit_tool = FileEditTool()
        
        # 构建读取文件的参数
        read_params = {
            "file_path": temp_path,
            "context": {
                "read_timestamps": shared_timestamps  # 直接传递共享字典的引用
            }
        }
        
        print(f"\n1. 读取前, 时间戳字典: {shared_timestamps}")
        
        # 执行文件读取
        read_result = await read_tool.execute(read_params)
        
        print(f"\n2. 读取后, 时间戳字典: {shared_timestamps}")
        print(f"   读取结果: {read_result.success}")
        
        # 构建编辑文件的参数 - 使用同一个时间戳字典
        edit_params = {
            "file_path": temp_path,
            "old_string": "测试内容",
            "new_string": "已修改的内容",
            "context": {
                "read_timestamps": shared_timestamps  # 直接传递共享字典的引用
            }
        }
        
        # 执行文件编辑
        edit_result = await edit_tool.execute(edit_params)
        
        print(f"\n3. 编辑后, 时间戳字典: {shared_timestamps}")
        print(f"   编辑结果: {edit_result.success}, 错误: {edit_result.error}")
        
        # 如果编辑失败，打印诊断信息
        if not edit_result.success:
            print(f"\n编辑失败原因: {edit_result.error}")
            
            # 检查路径是否在时间戳字典中
            resolved_path = str(Path(temp_path).resolve())
            
            print(f"\n诊断信息:")
            print(f"编辑目标文件路径: {temp_path}")
            print(f"解析后的路径: {resolved_path}")
            print(f"时间戳字典内容: {shared_timestamps}")
            print(f"路径是否在时间戳中: {resolved_path in shared_timestamps}")
        
        # 读取最终文件内容
        with open(temp_path, 'r') as f:
            print(f"\n4. 最终文件内容:\n{f.read()}")
        
        print("\n==== 精简版时间戳测试完成 ====")
        
        print("\n测试已完成，AG2执行器时间戳传递测试需要在单独的同步环境中运行")
        
    finally:
        # 清理临时文件
        if os.path.exists(temp_path):
            os.unlink(temp_path)

if __name__ == "__main__":
    asyncio.run(test_timestamp_fixed())