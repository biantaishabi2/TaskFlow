#!/usr/bin/env python3
"""
简单测试ToolManager的继续功能，不依赖Claude
"""

import os
import sys
import json
import logging
import asyncio
from unittest.mock import MagicMock

# 配置日志
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('simple_tool_test')

# 测试用的简单工具和工具管理器
class MockBaseTool:
    """工具基类"""
    
    def validate_parameters(self, params):
        """验证参数"""
        return True, ""
        
    async def execute(self, params):
        """执行工具"""
        raise NotImplementedError("未实现execute方法")

class ClaudeInputTool(MockBaseTool):
    """向Claude输入的工具"""
    
    def __init__(self):
        self.calls = []
        
    def validate_parameters(self, params):
        """验证参数"""
        if 'message' not in params:
            return False, "缺少message参数"
        return True, ""
        
    async def execute(self, params):
        """执行工具"""
        message = params.get('message', '')
        self.calls.append(message)
        
        logger.info(f"ClaudeInputTool收到请求: {message}")
        
        # 返回成功结果
        result = MagicMock()
        result.success = True
        result.message = "消息已发送"
        result.response = "继续执行的结果"
        
        return result

class ToolManager:
    """工具管理器"""
    
    def __init__(self):
        self.tools = {}
        
    def register_tool(self, name, tool):
        """注册工具"""
        self.tools[name] = tool
        
    async def execute_tool(self, tool_name, params):
        """执行工具"""
        tool = self.tools.get(tool_name)
        if not tool:
            result = MagicMock()
            result.success = False
            result.error = f"工具{tool_name}未找到"
            return result
            
        # 验证参数
        is_valid, error = tool.validate_parameters(params)
        if not is_valid:
            result = MagicMock()
            result.success = False
            result.error = error
            return result
            
        # 执行工具
        return await tool.execute(params)

# 测试工具调用
async def test_tool_call_async():
    """异步测试工具调用"""
    # 创建工具和工具管理器
    claude_input_tool = ClaudeInputTool()
    tool_manager = ToolManager()
    tool_manager.register_tool("claude_input", claude_input_tool)
    
    # 测试发送继续指令
    result = await tool_manager.execute_tool("claude_input", {"message": "请继续执行"})
    
    # 验证结果
    logger.info(f"工具调用结果: success={result.success}, message={result.message}")
    logger.info(f"Claude工具被调用了 {len(claude_input_tool.calls)} 次")
    logger.info(f"调用参数: {claude_input_tool.calls}")
    
    return result.success

# 执行测试
def test_tool_call():
    """同步测试工具调用"""
    return asyncio.run(test_tool_call_async())

if __name__ == "__main__":
    success = test_tool_call()
    sys.exit(0 if success else 1)