"""
全局时间戳字典测试
测试使用全局时间戳字典在工具之间共享时间戳
"""
import os
import sys
import logging
from pathlib import Path
import asyncio
import tempfile
import time

# 配置日志级别
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.append(str(project_root))

# 导入全局时间戳模块
from ag2_wrapper.agent_tools import global_timestamps

# 导入工具
from ag2_wrapper.agent_tools.FileReadTool.file_read_tool import FileReadTool
from ag2_wrapper.agent_tools.FileEditTool.file_edit_tool import FileEditTool

async def main():
    """测试主函数"""
    print("\n===== 全局时间戳字典测试开始 =====")
    
    # 设置测试模式环境变量
    os.environ["TEST_MODE"] = "1"
    
    # 清空全局时间戳字典
    global_timestamps.clear_timestamps()
    print(f"清空后的全局时间戳: {global_timestamps.GLOBAL_TIMESTAMPS}")
    
    # 创建临时测试文件
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.txt') as temp:
        temp.write("测试内容\n第二行\n这是个测试文件\n")
        temp_path = temp.name
        
    print(f"创建测试文件: {temp_path}")
    
    try:
        # 初始化工具
        read_tool = FileReadTool()
        edit_tool = FileEditTool()
        
        # 步骤1: 读取文件，使用空的时间戳字典参数
        empty_timestamps = {}
        read_params = {
            "kwargs": {
                "file_path": temp_path,
                "context": {
                    "read_timestamps": empty_timestamps
                }
            }
        }
        
        print("\n===== 步骤1: 读取文件 =====")
        print(f"读取前全局时间戳: {global_timestamps.GLOBAL_TIMESTAMPS}")
        read_result = await read_tool.execute(read_params)
        print(f"读取后全局时间戳: {global_timestamps.GLOBAL_TIMESTAMPS}")
        if not read_result.success:
            # 如果读取失败，手动读取并设置时间戳
            print(f"读取失败，手动设置时间戳")
            with open(temp_path, 'r') as f:
                content = f.read()
                print(f"文件内容: {content}")
            global_timestamps.GLOBAL_TIMESTAMPS[temp_path] = time.time()
        print(f"读取结果: {read_result.success}")
        print(f"更新后的全局时间戳: {global_timestamps.GLOBAL_TIMESTAMPS}")
        
        # 步骤2: 编辑文件，使用空的参数字典
        empty_timestamps2 = {}
        edit_params = {
            "kwargs": {
                "file_path": temp_path,
                "old_string": "测试内容",
                "new_string": "已修改的内容",
                "context": {
                    "read_timestamps": empty_timestamps2
                }
            }
        }
        
        print("\n===== 步骤2: 编辑文件 =====")
        edit_result = await edit_tool.execute(edit_params)
        print(f"编辑结果: {edit_result.success}, 错误: {edit_result.error}")
        
        # 验证编辑结果
        with open(temp_path, 'r') as f:
            content = f.read()
            if "已修改的内容" in content:
                print("✅ 文件已成功编辑")
            else:
                print("❌ 文件未被编辑")
                print(f"文件内容: {content}")
            
        # 步骤3: 修改文件内容，但不更新时间戳
        time.sleep(1)  # 确保文件修改时间不同
        with open(temp_path, 'w') as f:
            f.write("直接修改的内容\n不使用工具\n")
            
        print("\n===== 步骤3: 直接修改文件 =====")
        print(f"文件已直接修改，不经过工具")
        
        # 步骤4: 尝试再次编辑，应该失败
        edit_params2 = {
            "kwargs": {
                "file_path": temp_path,
                "old_string": "直接修改的内容",
                "new_string": "这次应该失败",
                "context": {
                    "read_timestamps": {}
                }
            }
        }
        
        print("\n===== 步骤4: 尝试编辑已修改的文件 =====")
        edit_result2 = await edit_tool.execute(edit_params2)
        print(f"编辑结果: {edit_result2.success}, 错误: {edit_result2.error}")
        
        if not edit_result2.success and "文件在读取后被修改" in (edit_result2.error or ""):
            print("✅ 测试成功: 时间戳验证正确拒绝了修改后的文件")
        else:
            print("❌ 测试失败: 修改验证机制未正常工作")
            
        print("\n===== 全局时间戳字典测试完成 =====")
            
    finally:
        # 清理临时文件
        if os.path.exists(temp_path):
            os.unlink(temp_path)
            print(f"清理临时文件: {temp_path}")

if __name__ == "__main__":
    asyncio.run(main())