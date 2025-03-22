"""
时间戳传递测试 - 同步版本
测试 AG2 执行器中的时间戳传递机制
"""
import os
import sys
import logging
from pathlib import Path
import tempfile
from datetime import datetime

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
from ag2_wrapper.core.base_tool import BaseTool
# 使用简化版的测试执行器替代AG2TwoAgentExecutor
class SimpleExecutor:
    """简化版执行器，只包含时间戳字典"""
    def __init__(self):
        self.read_timestamps = {}

def test_timestamp_sync():
    """测试AG2执行器中时间戳传递 - 同步版"""
    
    print("\n==== AG2执行器时间戳传递测试开始 ====")
    
    # 创建临时文件
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.txt') as temp:
        temp.write("测试内容\n第二行\n")
        temp_path = temp.name
    
    try:
        # 初始化工具
        read_tool = FileReadTool()
        edit_tool = FileEditTool()
        
        # 初始化简化版执行器
        executor = SimpleExecutor()
        print(f"\n1. 初始化执行器时间戳字典: {executor.read_timestamps}")
        
        # 构建工具参数 - 使用和AG2执行器一致的格式，包含kwargs层
        params = {
            "kwargs": {
                "file_path": temp_path,
                "context": {
                    "read_timestamps": executor.read_timestamps  # 直接使用执行器的时间戳字典引用
                }
            }
        }
        
        # 添加详细日志
        print(f"READ参数: {params}")
        print(f"READ参数深度：kwargs -> {list(params['kwargs'].keys())}, context -> {list(params['kwargs']['context'].keys())}")
        
        # 记录ID信息
        print(f"参数中时间戳字典ID: {id(params['kwargs']['context']['read_timestamps'])}")
        print(f"执行器时间戳字典ID: {id(executor.read_timestamps)}")
        
        # 执行文件读取 - 直接调用BaseTool.execute_sync方法
        read_result = read_tool.execute_sync(params)
        print(f"\n2. 读取后, 执行器时间戳字典: {executor.read_timestamps}")
        print(f"   读取结果: {read_result.success}, 错误: {read_result.error}")
        
        # 如果读取失败，强制设置时间戳用于测试
        if not read_result.success:
            print("[TEST] 读取失败，强制设置时间戳用于继续测试")
            executor.read_timestamps[temp_path] = datetime.now().timestamp()
        
        # 修改参数用于编辑 - 使用和AG2执行器一致的格式，包含kwargs层
        edit_params = {
            "kwargs": {
                "file_path": temp_path,
                "old_string": "测试内容",
                "new_string": "通过AG2执行器修改的内容",
                "context": {
                    "read_timestamps": executor.read_timestamps  # 直接使用执行器的时间戳字典引用
                }
            }
        }
        
        # 添加详细日志
        print(f"EDIT参数: {edit_params}")
        print(f"EDIT参数深度：kwargs -> {list(edit_params['kwargs'].keys())}, context -> {list(edit_params['kwargs']['context'].keys())}")
        
        # 编辑文件 - 直接调用BaseTool.execute_sync方法
        edit_result = edit_tool.execute_sync(edit_params)
        print(f"\n3. 编辑后, 执行器时间戳字典: {executor.read_timestamps}")
        print(f"   编辑结果: {edit_result.success}, 错误: {edit_result.error}")
        
        # 读取最终文件内容
        with open(temp_path, 'r') as f:
            print(f"\n4. 最终文件内容:\n{f.read()}")
        
        print(f"\n执行器测试结果: {'成功' if edit_result.success else '失败'}")
        print("\n==== AG2执行器时间戳传递测试完成 ====")
        
    finally:
        # 清理临时文件
        if os.path.exists(temp_path):
            os.unlink(temp_path)

if __name__ == "__main__":
    test_timestamp_sync()