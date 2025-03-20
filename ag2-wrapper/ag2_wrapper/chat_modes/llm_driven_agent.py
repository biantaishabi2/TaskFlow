"""
AG2-Wrapper LLM驱动的自动用户代理模块

这个模块提供了一个完全由LLM驱动的自动用户代理，该代理能够代替人类用户参与对话，
自主处理工具调用并做出决策。
"""

import logging
import sys
from typing import Dict, Any, Optional, List, Callable, Union, Literal
from pathlib import Path
from . import content_tool_call_agent


# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

try:
    import autogen
except ImportError:
    raise ImportError(
        "未找到autogen包。请确保已正确安装:\n"
        "$ pip install pyautogen"
    )
from ..agent_tools import LLMResponseAgent, ResponseType

logger = logging.getLogger(__name__)

class LLMDrivenUserProxy(content_tool_call_agent.ContentToolCallAgent):
    """
    LLM驱动的自动用户代理，完全由LLM控制。
    主要功能：
    1. 自动处理工具调用
    2. 生成对话响应
    3. 验证消息结构
    """
    
    def __init__(self, *args, **kwargs):
        """初始化代理"""
        # 设置代码执行配置
        from autogen.coding import LocalCommandLineCodeExecutor
        
        # 创建代码执行器，使用coding_workspace作为工作目录
        executor = LocalCommandLineCodeExecutor(
            timeout=500,
            work_dir="coding_workspace"  # 固定使用coding_workspace目录
        )
        
        # 添加代码执行配置
        kwargs['code_execution_config'] = {
            "executor": executor
        }
        
        # 调用父类初始化
        super().__init__(*args, **kwargs)
        
        # 创建默认响应代理
        self.response_agent = LLMResponseAgent()
        
        logger.info("LLMDrivenUserProxy initialized with %d tools", len(self.function_map))

    def get_human_input(self, prompt=""):
        """获取用户输入（由LLM自动判断）"""
        # 收集聊天历史
        chat_history = []
        for agent_name, messages in self.chat_messages.items():
            for msg in messages[-5:]:  # 最近5条
                chat_history.append({
                    "sender": agent_name,
                    "content": msg.get("content", "")
                })
        
        # 获取响应判断（不需要额外参数）
        response = self.response_agent.get_response(chat_history)
        
        # 打印响应判断结果
        print(f"\n=== 响应判断结果 ===")
        print(f"类型: {response['type']}")
        print(f"消息: {response['message']}")
        print(f"理由: {response['reasoning']}")
        print("=== 响应判断结束 ===\n")
        
        # 根据响应类型返回不同值
        if response["type"] == ResponseType.TOOL_APPROVED:
            print(f"[判断] 允许执行工具：{response['reasoning']}")
            return ""  # 返回空字符串，允许工具执行
        
        elif response["type"] == ResponseType.TOOL_REJECTED:
            print(f"[判断] 拒绝执行工具：{response['reasoning']}")
            return f"我拒绝执行该操作，原因：{response['reasoning']}"
        
        elif response["type"] == ResponseType.TASK_COMPLETED:
            print(f"[判断] 任务已完成：{response['reasoning']}")
            return "exit"
        
        else:  # TEXT_RESPONSE
            print(f"[判断] 继续对话：{response['reasoning']}")
            return response["message"] or "请继续"

    def validate_tools(self) -> bool:
        """
        验证必要工具是否已正确注册
        """
        try:
            required_tools = ['search_web']  # 可以根据需要添加其他必要工具
            for tool in required_tools:
                if tool not in self.function_map:
                    logger.error("必需的工具'%s'未注册", tool)
                    return False
            return True
        except Exception as e:
            logger.error("验证工具时出错: %s", str(e))
            return False
