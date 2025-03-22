"""
用于调试时间戳错误的简化测试
"""
import os
import sys
import logging
from pathlib import Path
import tempfile
import traceback

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.append(str(project_root))

# 导入工具
from ag2_wrapper.agent_tools.FileReadTool.file_read_tool import FileReadTool
from ag2_wrapper.agent_tools.FileEditTool.file_edit_tool import FileEditTool
from ag2_wrapper.agent_tools.global_timestamps import GLOBAL_TIMESTAMPS

def main():
    """测试主函数"""
    print("\n===== 调试测试开始 =====")
    
    # 创建临时测试文件
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.txt') as temp:
        temp.write("测试内容\n第二行\n这是个测试文件\n")
        temp_path = temp.name
        
    print(f"创建测试文件: {temp_path}")
    
    try:
        # 初始化工具
        read_tool = FileReadTool()
        edit_tool = FileEditTool()
        
        # 添加测试模式环境变量
        os.environ["TEST_MODE"] = "1"
        
        # 清空全局时间戳
        GLOBAL_TIMESTAMPS.clear()
        print(f"全局时间戳已清空: {GLOBAL_TIMESTAMPS}")
        
        # 设置一个测试时间戳
        GLOBAL_TIMESTAMPS[temp_path] = os.path.getmtime(temp_path) - 10
        print(f"已设置时间戳: {GLOBAL_TIMESTAMPS}")
        
        # 尝试验证文件读取
        try:
            print("\n尝试验证文件读取...")
            result = edit_tool._verify_file_read(temp_path, GLOBAL_TIMESTAMPS)
            print(f"验证结果: {result}")
        except Exception as e:
            print(f"验证文件读取时出错: {str(e)}")
            traceback.print_exc()
        
        # 尝试验证参数
        try:
            print("\n尝试验证参数...")
            params = {
                "file_path": temp_path,
                "old_string": "测试内容",
                "new_string": "已修改的内容",
                "context": {
                    "read_timestamps": {}
                }
            }
            result = edit_tool.validate_parameters(params)
            print(f"参数验证结果: {result}")
        except Exception as e:
            print(f"参数验证时出错: {str(e)}")
            traceback.print_exc()
        
    finally:
        # 清理临时文件
        if os.path.exists(temp_path):
            os.unlink(temp_path)
            print(f"清理临时文件: {temp_path}")
            
    print("\n===== 调试测试完成 =====")

if __name__ == "__main__":
    main()