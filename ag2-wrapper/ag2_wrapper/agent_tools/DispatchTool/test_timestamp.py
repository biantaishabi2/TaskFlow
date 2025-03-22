"""
时间戳传递测试
专门用于测试文件读取和编辑工具间的时间戳传递
"""
import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any
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

from ag2_wrapper.core.ag2_two_agent_executor import AG2TwoAgentExecutor
from ag2_wrapper.agent_tools.FileReadTool.file_read_tool import FileReadTool
from ag2_wrapper.agent_tools.FileEditTool.file_edit_tool import FileEditTool
from ag2_wrapper.core.base_tool import ToolCallResult

# 直接调用工具的execute_sync方法的封装函数
def call_tool_sync(tool, params):
    """模拟AG2TwoAgentExecutor中的工具包装函数逻辑"""
    # 确保params有正确的结构
    if "kwargs" not in params:
        params = {"kwargs": params}
        
    # 确保kwargs中有context
    if "context" not in params["kwargs"]:
        params["kwargs"]["context"] = {}
        
    # 确保context中有read_timestamps
    if "read_timestamps" not in params["kwargs"]["context"]:
        params["kwargs"]["context"]["read_timestamps"] = {}
        
    # 打印调试信息
    print(f"[调用前] 参数中的timestamps: {list(params['kwargs']['context']['read_timestamps'].keys())}")
        
    # 调用工具
    result = tool.execute_sync(params)
    
    # 打印调试信息
    print(f"[调用后] 参数中的timestamps: {list(params['kwargs']['context']['read_timestamps'].keys())}")
    
    return result, params["kwargs"]["context"]["read_timestamps"]

async def test_timestamp_transfer():
    """测试时间戳传递过程"""
    
    print("\n==== 时间戳传递测试开始 ====")
    
    # 创建临时文件用于测试
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.txt') as temp:
        temp.write("这是测试内容\n第二行\n第三行\n")
        temp_path = temp.name
    
    try:
        # 初始化工具
        file_read_tool = FileReadTool()
        file_edit_tool = FileEditTool()
        
        # 读取文件
        print("\n1. 读取文件测试")
        read_params = {
            "kwargs": {
                "file_path": temp_path,
                "context": {
                    "read_timestamps": {}
                }
            }
        }
        
        read_result, read_timestamps = call_tool_sync(file_read_tool, read_params)
        print(f"读取结果: success={read_result.success}, 时间戳键数量: {len(read_timestamps)}")
        
        # 编辑文件
        print("\n2. 编辑文件测试 - 使用读取后的时间戳")
        edit_params = {
            "kwargs": {
                "file_path": temp_path,
                "old_string": "这是测试内容",
                "new_string": "这是已修改的内容",
                "context": {
                    "read_timestamps": read_timestamps
                }
            }
        }
        
        edit_result, edit_timestamps = call_tool_sync(file_edit_tool, edit_params)
        print(f"编辑结果: success={edit_result.success}, error={edit_result.error}")
        
        # 如果编辑失败，打印更多诊断信息
        if not edit_result.success:
            print(f"\n编辑失败原因: {edit_result.error}")
            
            # 检查时间戳验证函数
            file_path = temp_path
            resolved_path = str(Path(file_path).resolve())
            
            print(f"\n诊断信息:")
            print(f"编辑目标文件路径: {file_path}")
            print(f"解析后的路径: {resolved_path}")
            print(f"时间戳键列表: {list(read_timestamps.keys())}")
            print(f"路径是否在时间戳中: {resolved_path in read_timestamps}")
            
            # 检查相似路径
            similar_keys = [k for k in read_timestamps.keys() if file_path in k or k in file_path]
            print(f"相似路径: {similar_keys}")
            
        # 读取文件内容验证
        with open(temp_path, 'r') as f:
            content = f.read()
            print(f"\n3. 文件最终内容:\n{content}")
            
        print("\n==== 时间戳传递测试完成 ====")
        
    finally:
        # 清理临时文件
        if os.path.exists(temp_path):
            os.unlink(temp_path)
            
if __name__ == "__main__":
    asyncio.run(test_timestamp_transfer())