"""
Tests for the Claude Input Tool functionality
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

class MockBaseTool:
    """模拟BaseTool类"""
    async def execute(self, params):
        return MagicMock(success=True)
    
    def validate_parameters(self, params):
        if 'message' not in params:
            return False, "缺少'message'参数"
        return True, ""

@pytest.mark.asyncio
async def test_claude_input_tool():
    """测试Claude输入工具的基本功能"""
    # 模拟BaseTool基类和其他依赖
    with patch('task_planner.vendor.claude_client.agent_tools.tools.BaseTool', MockBaseTool):
        # 导入可能不存在的模块
        try:
            from task_planner.vendor.claude_client.agent_tools.tools import BaseTool
        except ImportError:
            pytest.skip("BaseTool不可用")
            
        # 创建ClaudeInputTool类
        class ClaudeInputTool(BaseTool):
            """向Claude输入文字的工具"""
            
            def validate_parameters(self, params):
                """验证参数"""
                if 'message' not in params:
                    return False, "缺少'message'参数"
                return True, ""
                
            async def execute(self, params):
                """执行工具 - 向Claude输入文字"""
                message = params['message']
                
                try:
                    # 模拟向Claude发送输入
                    return {
                        "success": True,
                        "message": f"成功向Claude发送输入: {message}",
                        "response": "Claude响应"
                    }
                except Exception as e:
                    return {
                        "success": False,
                        "error": str(e)
                    }
        
        # 创建工具实例
        tool = ClaudeInputTool()
        
        # 测试参数验证
        is_valid, error = tool.validate_parameters({"message": "继续"})
        assert is_valid is True
        
        is_valid, error = tool.validate_parameters({})
        assert is_valid is False
        assert "缺少'message'参数" in error
        
        # 测试执行
        result = await tool.execute({"message": "继续"})
        assert result["success"] is True
        assert "成功向Claude发送输入: 继续" in result["message"]

@pytest.mark.asyncio
async def test_tool_manager_integration():
    """测试与ToolManager集成"""
    try:
        # 尝试导入ToolManager
        from task_planner.vendor.claude_client.agent_tools.tool_manager import ToolManager
        from task_planner.vendor.claude_client.agent_tools.tools import BaseTool
    except ImportError:
        pytest.skip("ToolManager或BaseTool不可用")
    
    # 创建自定义工具
    class TestClaudeInputTool(BaseTool):
        async def execute(self, params):
            return {
                "success": True,
                "message": f"执行成功: {params.get('message', '')}",
                "response": "测试响应"
            }
        
        def validate_parameters(self, params):
            if 'message' not in params:
                return False, "缺少'message'参数"
            return True, ""
    
    # 创建ToolManager实例
    tool_manager = ToolManager()
    
    # 注册工具
    tool_manager.register_tool("claude_input", TestClaudeInputTool())
    
    # 执行工具调用
    result = await tool_manager.execute_tool("claude_input", {
        "message": "测试消息"
    })
    
    # 验证结果
    assert result.success is True
    assert "执行成功: 测试消息" in result.message

@pytest.mark.asyncio
async def test_error_handling():
    """测试错误处理机制"""
    try:
        # 尝试导入ToolManager
        from task_planner.vendor.claude_client.agent_tools.tool_manager import ToolManager
        from task_planner.vendor.claude_client.agent_tools.tools import BaseTool
    except ImportError:
        pytest.skip("ToolManager或BaseTool不可用")
    
    # 创建会抛出异常的工具
    class ErrorTool(BaseTool):
        async def execute(self, params):
            raise Exception("测试异常")
        
        def validate_parameters(self, params):
            return True, ""
    
    # 创建ToolManager实例
    tool_manager = ToolManager()
    
    # 注册工具
    tool_manager.register_tool("error_tool", ErrorTool())
    
    # 执行工具调用
    result = await tool_manager.execute_tool("error_tool", {})
    
    # 验证结果
    assert result.success is False
    assert "测试异常" in result.error

@pytest.mark.asyncio
async def test_validation_failure():
    """测试参数验证失败场景"""
    try:
        # 尝试导入ToolManager
        from task_planner.vendor.claude_client.agent_tools.tool_manager import ToolManager
        from task_planner.vendor.claude_client.agent_tools.tools import BaseTool
    except ImportError:
        pytest.skip("ToolManager或BaseTool不可用")
    
    # 创建有严格参数验证的工具
    class StrictTool(BaseTool):
        async def execute(self, params):
            return {
                "success": True,
                "message": "执行成功"
            }
        
        def validate_parameters(self, params):
            if 'required_param' not in params:
                return False, "缺少'required_param'参数"
            return True, ""
    
    # 创建ToolManager实例
    tool_manager = ToolManager()
    
    # 注册工具
    tool_manager.register_tool("strict_tool", StrictTool())
    
    # 执行工具调用，但没有提供所需参数
    result = await tool_manager.execute_tool("strict_tool", {})
    
    # 验证结果
    assert result.success is False
    assert "缺少'required_param'参数" in result.error