"""
任务分发调度工具 - 提供任务协调和分发功能
用于将复杂任务分解并分发给其他工具执行
"""
import logging
from typing import Dict, Any, Optional, Tuple, ClassVar, List
from pathlib import Path
from ag2_wrapper.core.base_tool import BaseTool, ToolCallResult
from ag2_wrapper.core.ag2tools import AG2ToolManager  # 改用新的工具管理器
from ag2_wrapper.agent_tools.DispatchTool.prompt import PROMPT, DESCRIPTION
from ag2_wrapper.agent_tools.DispatchTool.conclusion_tool import ConclusionTool
import json
import os
from datetime import datetime
import asyncio
from .prompt import PROMPT, DESCRIPTION
from pydantic import Field
from autogen import AssistantAgent, register_function  # 添加 register_function
from ...chat_modes.llm_driven_agent import LLMDrivenUserProxy

# 添加在类定义前
DEFAULT_LLM_CONFIG = {
    "api_type": "openai",
    "base_url": "https://openrouter.ai/api/v1",
    "api_key": os.environ.get("OPENROUTER_API_KEY"),
    "model": "anthropic/claude-3.7-sonnet"
}

# 在文件开头的导入部分添加
from .conclusion_tool import ConclusionTool, PROMPT as CONCLUSION_PROMPT

# 在文件开头添加导入
from ...agent_tools.FileReadTool.prompt import DESCRIPTION as FR_DESC, PROMPT as FR_PROMPT
from ...agent_tools.GlobTool.prompt import DESCRIPTION as GLOB_DESC, PROMPT as GLOB_PROMPT
from ...agent_tools.GrepTool.prompt import DESCRIPTION as GREP_DESC, PROMPT as GREP_PROMPT
from ...agent_tools.lsTool.prompt import DESCRIPTION as LS_DESC, PROMPT as LS_PROMPT
from ...agent_tools.FileReadTool.file_read_tool import FileReadTool
from ...agent_tools.GlobTool.glob_tool import GlobTool
from ...agent_tools.GrepTool.grep_tool import GrepTool
from ...agent_tools.lsTool.ls_tool import lsTool

class DispatchTool(BaseTool):
    # 添加配置属性
    llm_config: Dict[str, Any] = Field(default=DEFAULT_LLM_CONFIG, description="LLM配置")
    work_dir: str = Field(default="./workspace", description="工作目录")
    use_docker: bool = Field(default=False, description="是否使用Docker")
    prompt: str = Field(default=PROMPT, description="代理提示词")  # 添加这行
    
    # 核心属性
    tool_manager: Optional[AG2ToolManager] = Field(default=None, description="工具管理器实例")
    assistant: Optional[AssistantAgent] = Field(default=None, description="决策代理")
    executor: Optional[LLMDrivenUserProxy] = Field(default=None, description="执行代理")
    tools: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="内部工具注册表")
    
    async def _build_dynamic_prompt(self, available_tools: List[BaseTool]) -> str:
        try:
            # 1. 构建工具列表描述
            tool_descriptions = []
            for tool in available_tools:
                # 获取工具的基本信息
                name = tool.name
                desc = tool.description
                is_read_only = tool.metadata.get("read_only", False)
                prompt = tool.prompt if hasattr(tool, 'prompt') else None
                
                # 构建参数描述
                params = tool.parameters or {}
                param_desc = []
                for param_name, param_info in params.items():
                    required = param_info.get("required", False)
                    param_type = param_info.get("type", "any")
                    param_desc.append(
                        f"- {param_name}: {param_info.get('description', '')} "
                        f"({'必需' if required else '可选'}, 类型: {param_type})"
                    )
                
                # 组装工具描述
                tool_desc = [
                    f"工具名称: {name}",
                    f"功能描述: {desc}",
                    f"工具类型: {'只读' if is_read_only else '可写'}",
                ]
                
                # 添加完整的工具提示词
                if prompt:
                    tool_desc.append("工具提示词:")
                    tool_desc.append(prompt)
                
                if param_desc:
                    tool_desc.append("参数列表:")
                    tool_desc.extend(param_desc)
                
                tool_descriptions.append("\n".join(tool_desc))
            
            # 2. 构建完整提示词
            prompt_parts = [
                "工作环境：",
                f"当前工作目录: {os.path.abspath(self.work_dir)}",
                "注意: 所有相对路径都将相对于此目录进行解析",
                "=============",
                "可用工具列表：",
                "=============",
                *tool_descriptions,
                "=============",
                "使用建议：",
                "1. 优先使用只读工具进行信息收集和分析",
                "2. 仅在必要时使用可写工具修改系统状态",
                "3. 每个工具调用前请确保参数完整且正确",
                "4. 注意检查工具执行结果，处理可能的错误",
                "5. 在完成所有任务后，必须使用 return_conclusion 工具返回最终结论",
                "=============",
                "工作流程：",
                "1. 分析任务需求",
                "2. 按顺序调用所需工具完成任务",
                "3. 最后必须调用 return_conclusion 工具总结任务结果",
                "=============",
                "请根据以上工具列表和工作流程，完成任务。"
            ]
            
            return "\n".join(prompt_parts)
            
        except Exception as e:
            logging.error(f"构建动态提示词失败: {str(e)}")
            return "请描述需要执行的任务。"

    def __init__(self, **data):
        base_data = {
            "name": "dispatch_agent",
            "description": DESCRIPTION,
            "prompt": PROMPT,
            "parameters": {
                "prompt": {
                    "type": "str",
                    "required": True,
                    "description": "描述代理要执行的任务"
                }
            },
            "metadata": {
                "read_only": True,
                "description": "任务分发工具，用于协调和分发任务给其他工具执行"
            }
        }
        base_data.update(data)
        super().__init__(**base_data)
        self.tools = {}  # 初始化工具字典
        
    def validate_parameters(self, params: Dict) -> Tuple[bool, str]:
        """验证参数有效性"""
        if "prompt" not in params or not isinstance(params["prompt"], str):
            return False, "必须提供字符串类型的 'prompt' 参数"
            
        return True, ""
    
    async def _get_available_tools(self, read_only: bool = True) -> List[BaseTool]:
        """获取可用的工具列表"""
        try:
            if not self.tools:
                logging.warning("未设置工具")
                return []
                
            # 从内部工具表获取所有工具
            all_tools = [info['tool'] for info in self.tools.values()]
            
            # 打印所有注册的工具
            logging.info("已注册的工具列表:")
            for tool in all_tools:
                logging.info(f"- {tool.name}: {tool.description} (只读: {tool.metadata.get('read_only', False)})")
            
            if read_only:
                # 筛选只读工具
                available_tools = [
                    tool for tool in all_tools 
                    if tool.metadata.get("read_only", False) and 
                    tool.name != self.name  # 排除自身
                ]
                logging.info(f"筛选出的只读工具: {[tool.name for tool in available_tools]}")
            else:
                # 返回除自身外的所有工具
                available_tools = [
                    tool for tool in all_tools 
                    if tool.name != self.name
                ]
                logging.info(f"所有可用工具: {[tool.name for tool in available_tools]}")
                
            logging.info(f"获取到 {len(available_tools)} 个可用工具")
            return available_tools
            
        except Exception as e:
            logging.error(f"获取可用工具失败: {str(e)}")
            return []
    
    async def _initialize_task(self, prompt: str) -> Dict[str, Any]:
        try:
            # 1. 获取可用工具（优先使用只读工具）
            available_tools = await self._get_available_tools(read_only=True)
            if not available_tools:
                available_tools = await self._get_available_tools(read_only=False)
                
            if not available_tools:
                raise ValueError("没有可用的工具")
            
            # 添加结论返回工具
            conclusion_tool = ConclusionTool()
            available_tools.append(conclusion_tool)
                
            # 2. 构建动态提示词
            dynamic_prompt = await self._build_dynamic_prompt(available_tools)
            
            # 3. 生成任务信息
            task_info = {
                "task_id": f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "prompt": prompt,
                "available_tools": available_tools,
                "dynamic_prompt": dynamic_prompt,
                "start_time": datetime.now().isoformat(),
                "status": "initialized"
            }
            
            logging.info(f"任务初始化完成: {task_info['task_id']}")
            return task_info
            
        except Exception as e:
            logging.error(f"任务初始化失败: {str(e)}")
            raise
    
    async def _generate_statistics(self, execution_info: Dict[str, Any]) -> Dict[str, Any]:
        """生成执行统计信息
        
        Args:
            execution_info: 执行信息字典
            
        Returns:
            Dict[str, Any]: 统计信息，包含：
                - total_tools: 总工具数
                - successful_calls: 成功调用数
                - failed_calls: 失败调用数
                - total_time: 总执行时间
                - average_time: 平均执行时间
        """
        try:
            # 解析时间
            start_time = datetime.fromisoformat(execution_info["start_time"])
            end_time = datetime.fromisoformat(execution_info["end_time"])
            total_time = (end_time - start_time).total_seconds()
            
            # 统计工具调用
            tool_calls = execution_info.get("tool_calls", [])
            total_tools = len(tool_calls)
            successful_calls = sum(1 for call in tool_calls if call["status"] == "completed")
            failed_calls = total_tools - successful_calls
            
            # 计算平均执行时间
            tool_times = []
            for call in tool_calls:
                if "start_time" in call and "end_time" in call:
                    call_start = datetime.fromisoformat(call["start_time"])
                    call_end = datetime.fromisoformat(call["end_time"])
                    tool_times.append((call_end - call_start).total_seconds())
            
            average_time = sum(tool_times) / len(tool_times) if tool_times else 0
            
            return {
                "total_tools": total_tools,
                "successful_calls": successful_calls,
                "failed_calls": failed_calls,
                "total_time": total_time,
                "average_time": average_time
            }
            
        except Exception as e:
            logging.error(f"生成统计信息失败: {str(e)}")
            return {
                "error": f"统计信息生成失败: {str(e)}"
            }
    
    async def _format_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """格式化执行结果
        
        Args:
            result: 原始执行结果
            
        Returns:
            Dict[str, Any]: 格式化后的结果，包含：
                - summary: 执行摘要
                - status: 执行状态
                - results: 格式化的结果列表
                - errors: 格式化的错误列表
        """
        try:
            # 1. 生成执行摘要
            total_tools = len(result.get("tool_calls", []))
            successful_results = len(result.get("results", []))
            error_count = len(result.get("errors", []))
            
            summary = (
                f"任务执行完成。\n"
                f"共调用 {total_tools} 个工具，"
                f"成功 {successful_results} 个，"
                f"失败 {error_count} 个。"
            )
            
            # 2. 格式化结果
            formatted_results = []
            for item in result.get("results", []):
                formatted_results.append({
                    "tool": item["tool"],
                    "result": item["result"]
                })
                
            # 3. 格式化错误
            formatted_errors = []
            for item in result.get("errors", []):
                formatted_errors.append({
                    "tool": item["tool"],
                    "error": item["error"]
                })
                
            return {
                "summary": summary,
                "status": result["status"],
                "results": formatted_results,
                "errors": formatted_errors
            }
            
        except Exception as e:
            logging.error(f"格式化结果失败: {str(e)}")
            return {
                "summary": "结果格式化失败",
                "status": "error",
                "error": str(e)
            }
    
    # 移除错误的导入
    # from ...agent_tools.ConclusionTool.prompt import DESCRIPTION as CONCL_DESC, PROMPT as CONCL_PROMPT
    
    # 修改工具配置部分
    def _initialize_agents(self):
        """初始化决策代理和执行代理"""
        try:
            # 初始化工具管理器
            self.tool_manager = AG2ToolManager()
            
            # 初始化 AssistantAgent
            self.assistant = AssistantAgent(
                name="决策助手",
                llm_config=self.llm_config,
                system_message=self.prompt
            )
    
            # 初始化 LLMDrivenUserProxy - 修改为 ALWAYS 模式
            self.executor = LLMDrivenUserProxy(
                name="执行助手",
                human_input_mode="ALWAYS",  # 改为 ALWAYS,让大模型决定何时结束对话
                code_execution_config={
                    "work_dir": self.work_dir,
                    "use_docker": self.use_docker
                }
            )

            # 创建工具实例并注册
            tools = [
                (FileReadTool(), FR_PROMPT),
                (GlobTool(), GLOB_PROMPT),
                (GrepTool(), GREP_PROMPT),
                (LSTool(), LS_PROMPT),
                (ConclusionTool(), CONCLUSION_PROMPT)
            ]
            
            # 为每个工具创建包装函数并注册
            def create_tool_wrapper(tool: BaseTool):
                async def wrapper(*args: Any, **kwargs: Any) -> Dict[str, Any]:
                    # 直接传递kwargs给execute方法
                    result = await tool.execute(kwargs)
                    # 如果是 conclusion 工具且执行成功,立即结束对话
                    if tool.name == "return_conclusion" and result.success:
                        return {
                            **result.result,
                            "should_terminate": True
                        }
                    return result.result
                return wrapper
            
            for tool_instance, prompt in tools:
                # 为每个工具创建独立的包装函数
                tool_wrapper = create_tool_wrapper(tool_instance)
                
                # 注册到 AutoGen,使用完整的提示词
                register_function(
                    tool_wrapper,
                    name=tool_instance.name,
                    description=f"{tool_instance.description}\n\n{prompt}",  # 合并描述和提示词
                    caller=self.assistant,
                    executor=self.executor
                )
                
                # 同时注册到工具管理器和内部工具表
                self.tools[tool_instance.name] = {
                    'tool': tool_instance,
                    'prompt': prompt,
                    'parameters': tool_instance.parameters
                }
                
                # 注册到工具管理器
                self.tool_manager._tools[tool_instance.name] = tool_instance
            
            return True
            
        except Exception as e:
            logging.error(f"初始化代理失败: {str(e)}")
            return False

    async def _run_agent_conversation(self, task_info: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # 确保代理已初始化
            if not self.assistant or not self.executor:
                if not self._initialize_agents():
                    raise ValueError("代理初始化失败")
    
            # 构建完整的任务提示词
            full_prompt = (
                f"{task_info['dynamic_prompt']}\n\n"
                f"任务描述：{task_info['prompt']}\n\n"
                "注意：完成任务后，必须使用 return_conclusion 工具返回你的结论。\n"
                "如果任务成功，设置 success=True 并在 conclusion 中详细说明结果；\n"
                "如果任务失败，设置 success=False 并在 conclusion 中说明失败原因。"
            )
            
            # 启动对话
            chat_result = await self.executor.a_initiate_chat(
                self.assistant,
                message=full_prompt
            )
    
            # 获取最后一个工具调用
            last_message = chat_result.chat_history[-1]
            if not isinstance(last_message, dict) or "tool_calls" not in last_message:
                raise ValueError("对话未以工具调用结束")
                
            last_tool_call = last_message["tool_calls"][-1]
            
            # 检查是否是 return_conclusion 工具调用
            if last_tool_call.get("name") != "return_conclusion":
                raise ValueError("对话必须以 return_conclusion 工具调用结束")
                
            # 获取结论结果
            conclusion_result = last_tool_call.get("result", {})
            
            # 验证结论格式
            if not conclusion_result or \
               not isinstance(conclusion_result.get("success"), bool) or \
               not conclusion_result.get("conclusion") or \
               not isinstance(conclusion_result.get("conclusion"), str):
                error_msg = (
                    "未获取到有效的结论。结论必须包含：\n"
                    "1. success: 布尔值，表示任务是否成功\n"
                    "2. conclusion: 非空字符串，包含结论内容或失败原因\n"
                    f"当前结果: {conclusion_result}"
                )
                raise ValueError(error_msg)
            
            # 如果是 conclusion 工具调用,立即返回结果并终止对话
            if conclusion_result.get("should_terminate", False):
                await self.executor.stop_chat()  # 主动结束对话
                
            return {
                "status": "completed",
                "task_id": task_info["task_id"],
                "start_time": task_info["start_time"],
                "end_time": datetime.now().isoformat(),
                "success": conclusion_result.get("success", False),
                "conclusion": conclusion_result.get("conclusion", "未提供结论"),
                "chat_history": chat_result.chat_history,
                "terminated": True  # 始终标记为已终止
            }
    
        except Exception as e:
            logging.error(f"代理对话执行失败: {str(e)}")
            return {
                "status": "failed",
                "task_id": task_info["task_id"],
                "start_time": task_info["start_time"],
                "end_time": datetime.now().isoformat(),
                "success": False,
                "conclusion": f"执行失败: {str(e)}",
                "terminated": True
            }

    async def execute(self, params: Dict[str, Any]) -> ToolCallResult:
        """主执行流程"""
        try:
            # 验证参数
            is_valid, error_msg = self.validate_parameters(params)
            if not is_valid:
                return ToolCallResult(success=False, error=error_msg)
            
            # 先初始化代理和工具
            if not self._initialize_agents():
                return ToolCallResult(
                    success=False,
                    error="代理初始化失败"
                )
                
            # 1. 初始化任务
            task_info = await self._initialize_task(params["prompt"])
            
            # 2. 运行代理对话
            execution_result = await self._run_agent_conversation(task_info)
            
            # 直接返回结论
            if execution_result["status"] == "completed":
                return ToolCallResult(
                    success=execution_result["success"],
                    result={
                        "conclusion": execution_result["conclusion"]
                    }
                )
            else:
                return ToolCallResult(
                    success=False,
                    error=execution_result["conclusion"]
                )
            
        except Exception as e:
            logging.error(f"任务执行失败: {str(e)}")
            return ToolCallResult(
                success=False,
                error=f"任务执行失败: {str(e)}"
            )
        finally:
            # 清理资源
            self.assistant = None
            self.executor = None