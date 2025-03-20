"""
测试 DispatchTool 类的功能
"""
import pytest
import asyncio
from typing import Dict, List, Any
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到 Python 路径
project_root = str(Path(__file__).parent.parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from ag2_wrapper.core.base_tool import BaseTool, ToolCallResult
from ag2_wrapper.core.tools import AG2ToolManager
from ag2_wrapper.agent_tools.DispatchTool.dispatch_tool import DispatchTool, DEFAULT_LLM_CONFIG

# Mock 类定义
class MockTool(BaseTool):
    """模拟测试工具"""
    def __init__(self, name: str, read_only: bool = True):
        super().__init__(
            name=name,
            description=f"Mock tool {name}",
            parameters={"prompt": {"type": "str", "required": True}},
            metadata={"read_only": read_only}
        )
    
    async def execute(self, params: Dict[str, Any]) -> ToolCallResult:
        return ToolCallResult(success=True, result=f"Executed {self.name}")

class MockToolManager:
    """模拟工具管理器"""
    def __init__(self, tools: List[BaseTool]):
        self.tools = {tool.name: {"tool": tool} for tool in tools}
    
    def get_registered_tools(self) -> Dict[str, Dict[str, Any]]:
        return self.tools

class MockAssistant:
    """模拟 Assistant 代理"""
    def __init__(self, name, llm_config, system_message):
        self.name = name
        self.llm_config = llm_config
        self.system_message = system_message

class MockExecutor:
    """模拟执行器"""
    def initiate_chat(self, assistant, message):
        return {"chat_history": [{"role": "assistant", "content": "分析完成", 
                "tool_calls": [{"name": "return_conclusion", 
                "result": {"success": True, "conclusion": "测试结论"}}]}]}

@pytest.fixture
def mock_tools():
    """创建模拟工具列表"""
    return [
        MockTool("read_tool_1", read_only=True),
        MockTool("read_tool_2", read_only=True),
        MockTool("write_tool_1", read_only=False),
        MockTool("write_tool_2", read_only=False)
    ]

@pytest.fixture
def dispatch_tool(mock_tools):
    """创建 DispatchTool 实例"""
    tool = DispatchTool()
    tool.tool_manager = MockToolManager(mock_tools)
    # 使用 Mock 对象替代真实的 AssistantAgent
    tool.assistant = MockAssistant(
        name="test_assistant",
        llm_config=DEFAULT_LLM_CONFIG,
        system_message="You are a test assistant"
    )
    tool.executor = MockExecutor()
    return tool

@pytest.mark.asyncio
async def test_initialization(dispatch_tool):
    """测试工具初始化"""
    assert dispatch_tool.name == "dispatch_agent"
    assert dispatch_tool.tool_manager is not None
    assert dispatch_tool.metadata["read_only"] is True

@pytest.mark.asyncio
async def test_parameter_validation(dispatch_tool):
    """测试参数验证"""
    # 有效参数
    is_valid, _ = dispatch_tool.validate_parameters({"prompt": "test task"})
    assert is_valid is True
    
    # 无效参数
    is_valid, error = dispatch_tool.validate_parameters({})
    assert is_valid is False
    assert "必须提供字符串类型的 'prompt' 参数" in error

@pytest.mark.asyncio
async def test_get_available_tools(dispatch_tool):
    """测试获取可用工具"""
    # 获取只读工具
    read_only_tools = await dispatch_tool._get_available_tools(read_only=True)
    assert len(read_only_tools) == 2
    assert all(tool.metadata["read_only"] for tool in read_only_tools)
    
    # 获取所有工具
    all_tools = await dispatch_tool._get_available_tools(read_only=False)
    assert len(all_tools) == 4

@pytest.mark.asyncio
async def test_initialize_task(dispatch_tool):
    """测试任务初始化"""
    task_info = await dispatch_tool._initialize_task("test task")
    
    assert "task_id" in task_info
    assert task_info["prompt"] == "test task"
    assert len(task_info["available_tools"]) > 0
    assert "dynamic_prompt" in task_info
    assert "start_time" in task_info
    assert task_info["status"] == "initialized"

@pytest.mark.asyncio
async def test_execute_task(dispatch_tool):
    """测试任务执行"""
    # 准备任务信息
    result = await dispatch_tool.execute({"prompt": "test task"})
    
    # 验证执行结果
    assert result.success is True
    assert result.error is None
    assert "conclusion" in result.result

# 删除重复的 test_execute_task，保留并修改一个
@pytest.mark.asyncio
async def test_execute(dispatch_tool):
    """测试任务执行"""
    # 准备任务信息
    result = await dispatch_tool.execute({"prompt": "test task"})
    
    # 验证执行结果
    assert result.success is True
    assert result.error is None
    assert "conclusion" in result.result

# 修改 test_complete_execution 测试用例
@pytest.mark.asyncio
async def test_complete_execution(dispatch_tool):
    """测试完整的执行流程"""
    # 执行任务
    result = await dispatch_tool.execute({"prompt": "test complete execution"})
    
    # 验证执行成功
    assert result.success is True
    assert result.error is None
    assert "conclusion" in result.result

# 修改 test_complete_execution 测试用例
@pytest.mark.asyncio
async def test_complete_execution(dispatch_tool):
    """测试完整的执行流程"""
    # 执行任务
    result = await dispatch_tool.execute({"prompt": "test complete execution"})
    
    # 验证执行成功
    assert result.success is True
    assert result.error is None
    assert "conclusion" in result.result

# 修改 test_complete_execution_with_conclusion
@pytest.mark.asyncio
async def test_complete_execution_with_conclusion(dispatch_tool):
    """测试完整执行流程（包含结论）"""
    # 模拟成功的结论
    class MockChatResult:
        def __init__(self):
            self.chat_history = [
                {
                    "tool_calls": [
                        {
                            "name": "return_conclusion",
                            "result": {
                                "success": True,
                                "conclusion": "完整测试结论"
                            }
                        }
                    ]
                }
            ]
    
    class MockExecutor:
        def initiate_chat(self, assistant, message):
            return MockChatResult()
    
    dispatch_tool.executor = MockExecutor()
    
    result = await dispatch_tool.execute({"prompt": "test complete execution"})
    
    assert result.success is True
    assert "完整测试结论" in result.result["conclusion"]

# 修改 test_agent_conversation_with_conclusion
@pytest.mark.asyncio
async def test_agent_conversation_with_conclusion(dispatch_tool):
    """测试代理对话和结论处理"""
    # 模拟对话结果
    class MockChatResult:
        def __init__(self):
            self.chat_history = [
                {
                    "role": "assistant",
                    "content": "分析完成",
                    "tool_calls": [
                        {
                            "name": "return_conclusion",
                            "result": {
                                "success": True,
                                "conclusion": "测试结论"
                            }
                        }
                    ]
                }
            ]
    
    # 修改 executor 的 initiate_chat 方法
    class MockExecutor:
        def initiate_chat(self, assistant, message):
            return MockChatResult()
    
    # 替换执行器
    dispatch_tool.executor = MockExecutor()
    
    # 执行对话
    task_info = await dispatch_tool._initialize_task("test task")
    result = await dispatch_tool._run_agent_conversation(task_info)
    
    # 验证结果
    assert result["status"] == "completed"
    assert result["success"] is True
    assert result["conclusion"] == "测试结论"

@pytest.mark.asyncio
async def test_error_handling(dispatch_tool):
    """测试错误处理"""
    # 测试无效参数
    result = await dispatch_tool.execute({})
    assert result.success is False
    assert result.error is not None
    
    # 测试工具执行异常
    class ErrorTool(MockTool):
        async def execute(self, params):
            raise Exception("Test error")
    
    error_tool = ErrorTool("error_tool", read_only=True)
    dispatch_tool.tool_manager = MockToolManager([error_tool])    
    # 只保留一个测试，统一期望失败
    result = await dispatch_tool.execute({"prompt": "test error"})
    assert result.success is False
    assert result.error is not None

# 添加 ConclusionTool 的 Mock 版本
class MockConclusionTool(BaseTool):
    """模拟结论返回工具"""
    def __init__(self):
        super().__init__(
            name="return_conclusion",
            description="返回调研结论的工具",
            parameters={
                "success": {"type": "bool", "required": True},
                "conclusion": {"type": "str", "required": True}
            },
            metadata={"read_only": True}
        )
    
    async def execute(self, params: Dict[str, Any]) -> ToolCallResult:
        # 添加参数验证
        if not isinstance(params.get("success"), bool):
            raise Exception("success 必须是布尔类型")
        if not isinstance(params.get("conclusion"), str):
            raise Exception("conclusion 必须是字符串类型")
        if not params.get("conclusion"):
            raise Exception("conclusion 不能为空")
            
        return ToolCallResult(
            success=True,
            result={
                "success": params["success"],
                "conclusion": params["conclusion"]
            }
        )

# 在 MockConclusionTool 类定义后添加以下测试用例
@pytest.mark.asyncio
async def test_conclusion_tool_basic():
    """测试结论工具基本功能"""
    tool = MockConclusionTool()
    
    # 测试工具初始化
    assert tool.name == "return_conclusion"
    assert tool.metadata["read_only"] is True
    assert "success" in tool.parameters
    assert "conclusion" in tool.parameters
    
    # 测试成功结论
    result = await tool.execute({
        "success": True,
        "conclusion": "测试成功结论"
    })
    assert result.success is True
    assert result.result["success"] is True
    assert result.result["conclusion"] == "测试成功结论"
    
    # 测试失败结论
    result = await tool.execute({
        "success": False,
        "conclusion": "测试失败原因"
    })
    assert result.success is True  # 工具执行成功
    assert result.result["success"] is False  # 结论表明失败
    assert result.result["conclusion"] == "测试失败原因"

@pytest.mark.asyncio
async def test_conclusion_tool_validation():
    """测试结论工具参数验证"""
    tool = MockConclusionTool()
    
    # 测试缺少参数
    with pytest.raises(Exception):
        await tool.execute({})
    
    # 测试参数类型错误
    with pytest.raises(Exception):
        await tool.execute({
            "success": "not_a_boolean",
            "conclusion": "测试"
        })
    
    # 测试空结论
    with pytest.raises(Exception):
        await tool.execute({
            "success": True,
            "conclusion": ""
        })

@pytest.mark.asyncio
async def test_conclusion_tool_integration(dispatch_tool):
    """测试结论工具集成"""
    # 初始化任务
    task_info = await dispatch_tool._initialize_task("test task")
    
    # 验证结论工具是否被添加
    tools = task_info["available_tools"]
    conclusion_tools = [t for t in tools if t.name == "return_conclusion"]
    assert len(conclusion_tools) == 1
    
    # 验证结论工具参数
    conclusion_tool = conclusion_tools[0]
    assert "success" in conclusion_tool.parameters
    assert "conclusion" in conclusion_tool.parameters

@pytest.mark.asyncio
async def test_agent_conversation_with_conclusion(dispatch_tool):
    """测试代理对话和结论处理"""
    # 模拟对话结果
    class MockChatResult:
        def __init__(self):
            self.chat_history = [
                {
                    "role": "assistant",
                    "content": "分析完成",
                    "tool_calls": [
                        {
                            "name": "return_conclusion",
                            "result": {
                                "success": True,
                                "conclusion": "测试结论"
                            }
                        }
                    ]
                }
            ]
    
    # 修改 executor 的 initiate_chat 方法
    class MockExecutor:
        def initiate_chat(self, assistant, message):
            return MockChatResult()
    
    # 替换执行器
    dispatch_tool.executor = MockExecutor()
    
    # 执行对话
    task_info = await dispatch_tool._initialize_task("test task")
    result = await dispatch_tool._run_agent_conversation(task_info)
    
    # 验证结果
    assert result["status"] == "completed"
    assert result["success"] is True
    assert result["conclusion"] == "测试结论"

@pytest.mark.asyncio
async def test_agent_conversation_without_conclusion(dispatch_tool):
    """测试没有结论的情况"""
    class MockChatResult:
        def __init__(self):
            self.chat_history = [
                {
                    "role": "assistant",
                    "content": "分析完成",
                    "tool_calls": []
                }
            ]
    
    class MockExecutor:
        def initiate_chat(self, assistant, message):
            return MockChatResult()
    
    dispatch_tool.executor = MockExecutor()
    
    task_info = await dispatch_tool._initialize_task("test task")
    result = await dispatch_tool._run_agent_conversation(task_info)
    
    assert result["status"] == "failed"
    assert "未找到调研结论" in result["conclusion"]

@pytest.mark.asyncio
async def test_complete_execution_with_conclusion(dispatch_tool):
    """测试完整执行流程（包含结论）"""
    # 模拟成功的结论
    class MockChatResult:
        def __init__(self):
            self.chat_history = [
                {
                    "tool_calls": [
                        {
                            "name": "return_conclusion",
                            "result": {
                                "success": True,
                                "conclusion": "完整测试结论"
                            }
                        }
                    ]
                }
            ]
    
    class MockExecutor:
        def initiate_chat(self, assistant, message):
            return MockChatResult()
    
    dispatch_tool.executor = MockExecutor()
    
    result = await dispatch_tool.execute({"prompt": "test complete execution"})
    
    assert result.success is True
    assert "完整测试结论" in result.result["conclusion"]

@pytest.mark.asyncio
async def test_error_handling(dispatch_tool):
    """测试错误处理"""
    # 测试无效参数
    result = await dispatch_tool.execute({})
    assert result.success is False
    assert result.error is not None
    
    # 测试工具执行异常
    class ErrorTool(MockTool):
        async def execute(self, params):
            raise Exception("Test error")
    
    error_tool = ErrorTool("error_tool", read_only=True)
    dispatch_tool.tool_manager = MockToolManager([error_tool])
    
    # 只保留一个测试，期望失败
    result = await dispatch_tool.execute({"prompt": "test error"})
    assert result.success is False
    assert result.error is not None

@pytest.mark.asyncio
async def test_task_timeout(dispatch_tool):
    """测试任务超时处理"""
    class TimeoutExecutor:
        def initiate_chat(self, assistant, message):
            # 模拟超时
            raise asyncio.TimeoutError("任务执行超时")
    
    dispatch_tool.executor = TimeoutExecutor()
    result = await dispatch_tool.execute({"prompt": "test timeout"})
    
    assert result.success is False
    assert "超时" in result.error

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

# 添加 MockExecutor 类定义到文件开头的类定义部分
# 在文件开头添加导入
from autogen import AssistantAgent
# 删除这行
# from ...chat_modes.llm_driven_agent import LLMDrivenUserProxy

# 改为
from ag2_wrapper.chat_modes.llm_driven_agent import LLMDrivenUserProxy

class MockExecutor:
    """模拟执行器"""
    def initiate_chat(self, assistant, message):
        return MockChatResult()

class MockChatResult:
    """模拟聊天结果"""
    def __init__(self):
        self.chat_history = [
            {
                "role": "assistant",
                "content": "分析完成",
                "tool_calls": [
                    {
                        "name": "return_conclusion",
                        "result": {
                            "success": True,
                            "conclusion": "测试结论"
                        }
                    }
                ]
            }
        ]

class MockAssistant:
    """模拟 Assistant 代理"""
    def __init__(self, name, llm_config, system_message):
        self.name = name
        self.llm_config = llm_config
        self.system_message = system_message
