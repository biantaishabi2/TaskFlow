"""
Mock Claude工具实现，用于测试
"""

import logging
import asyncio
from typing import Dict, Any

# 配置日志
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('mock_claude_tools')

class MockBaseTool:
    """工具基类模拟实现"""
    async def execute(self, params):
        """执行工具"""
        raise NotImplementedError("工具未实际实现")
        
    def validate_parameters(self, params):
        """验证参数"""
        return True, ""

class MockClaudeInputTool(MockBaseTool):
    """模拟向Claude输入文字的工具"""
    
    def __init__(self, response=None):
        self.response = response or {
            "success": True,
            "message": "成功向Claude发送继续指令",
            "response": "任务已继续执行并完成"
        }
        self.call_count = 0
    
    def validate_parameters(self, params):
        """验证参数"""
        if 'message' not in params:
            return False, "缺少'message'参数"
        return True, ""
        
    async def execute(self, params):
        """执行工具 - 向Claude输入文字"""
        message = params['message']
        self.call_count += 1
        
        logger.info(f"模拟向Claude发送输入: {message} (调用次数: {self.call_count})")
        
        # 返回预设的响应
        return self.response

class MockToolManager:
    """模拟工具管理器"""
    
    def __init__(self):
        self.tools = {}
        self.call_history = []
    
    def register_tool(self, name, tool):
        """注册工具"""
        self.tools[name] = tool
    
    async def execute_tool(self, tool_name, params):
        """执行工具"""
        self.call_history.append((tool_name, params))
        
        if tool_name not in self.tools:
            return {"success": False, "error": f"工具 {tool_name} 未注册"}
        
        tool = self.tools[tool_name]
        
        # 验证参数
        is_valid, error = tool.validate_parameters(params)
        if not is_valid:
            return {"success": False, "error": error}
        
        # 执行工具
        return await tool.execute(params)

async def test_continue_async():
    """异步测试继续功能"""
    # 创建工具和工具管理器
    claude_input_tool = MockClaudeInputTool()
    tool_manager = MockToolManager()
    tool_manager.register_tool("claude_input", claude_input_tool)
    
    # 执行继续操作
    logger.info("模拟向Claude发送继续指令...")
    result = await tool_manager.execute_tool("claude_input", {
        "message": "请继续，完成剩余的任务。"
    })
    
    logger.info(f"执行结果: {result}")
    logger.info(f"工具调用历史: {tool_manager.call_history}")
    
    return result

def test_continue():
    """同步测试继续功能"""
    return asyncio.run(test_continue_async())

if __name__ == "__main__":
    result = test_continue()
    print(f"测试结果: {result}")