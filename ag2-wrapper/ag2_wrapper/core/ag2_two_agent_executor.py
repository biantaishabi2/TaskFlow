"""
AG2 Two Agent Executor
基于 AG2 Wrapper 的双代理执行器实现
用于适配 TaskExecutor 的任务执行接口

关于任务上下文(task_context)的使用说明：
1. 目前 task_context 为空，要启用任务间上下文传递功能，需要：
   - 从 task_context_prompts.py 获取提示词模板
   - 使用 get_context_prompt(task_id, step_id, parent_step_id) 生成上下文提示词

2. 添加方式有两种：
   a) 在实例化时通过参数传入：
      ```python
      executor = AG2TwoAgentExecutor(
          config=config,
          tool_manager=tool_manager,
          context_manager=context_manager,
          task_context=get_context_prompt(task_id, step_id, parent_step_id)
      )
      ```
   
   b) 在初始化时设置：
      ```python
      def __init__(self, ..., task_context: str = ""):
          self.task_context = task_context
      ```
      
3. 更新方式：
   - 在需要更新时调用 update_system_message() 方法
   - 传入新的 task_context 值
"""

from autogen import AssistantAgent, register_function
from ..chat_modes.llm_driven_agent import LLMDrivenUserProxy
import os
import logging
import asyncio
import concurrent.futures
from typing import Dict, Any, Optional, List, Tuple
from task_planner.core.context_management import TaskContext
from .ag2tools import AG2ToolManager
from .tool_utils import ToolLoader, ToolError
from .config import ConfigManager
from .ag2_context import ContextManager
import json
from pathlib import Path
from ..core.config import create_openrouter_config
import platform
from datetime import datetime
from ..agent_tools.BashTool.prompt import PROMPT as BASH_PROMPT
import functools
from ..agent_tools.MCPTool import MCPTool
from ..core.base_tool import BaseTool

logger = logging.getLogger(__name__)

# 将默认系统提示词拆分成多个部分
DEFAULT_SYSTEM_PROMPT = """
# 基础系统提示词
你是一个帮助用户完成软件工程任务的交互式命令行工具。请使用以下说明和可用工具来协助用户。

# 记忆
如果当前工作目录包含一个名为 MEMORY.ME 的文件，它会自动添加到你的上下文中。你可以记录你需要记录的事情，如待办事项列表。这个文件有多个用途：
1. 存储常用的 bash 命令（构建、测试、代码检查等）
2. 记录用户的代码风格偏好
3. 维护关于代码库结构和组织的有用信息
4. 记录用户需要记录的事情，如待办事项列表，并动态更新

# Git 工作流规范
- **禁止** 直接在主分支（如 `master`, `main`）上进行任何修改或提交。
- **必须** 在进行任何文件修改或代码编写之前，从最新的主分支创建一个新的、有描述性名称的功能分支。
- 标准流程：
  1. 确保在主分支上: `git checkout main` (或 `master`)
  2. 拉取最新代码: `git pull origin main` (或 `master`)
  3. 创建并切换到新分支: `git checkout -b new-feature-branch-name`
  4. 在新分支上进行所有修改和提交。
- 永远不要建议在主分支上直接执行 `git commit` 或 `git push`。

# 语气和风格
- 简洁、直接、切中要点
- 运行非简单的 bash 命令时，解释其功能和目的
- 使用 Github 风格的 markdown 进行格式化
- 输出将显示在命令行界面中
- 在保持有用性的同时最小化输出标记
- 除非要求详细说明，否则简明扼要地用不超过4行回答
- 避免不必要的开场白或结束语
- 只使用工具来完成任务，不要用Bash工具或代码注释作为与用户交流的手段
- 如果不能帮助用户，不要解释原因，提供替代方案或限制回复在1-2句话内
- 直接回答问题，避免阐述、解释或详细说明
- 避免在回答前后使用多余文本（如"答案是..."）

# Shell 命令执行规范
对于所有需要在 shell 中执行的命令，无论简单或复杂，你都必须将它们封装在 ```sh ... ``` 代码块中以供执行。
不要尝试建议或调用名为 'bash' 或 'shell' 的工具，始终使用 `sh` 代码块。

**重要：** 在执行完 ```sh ... ``` 代码块后，你必须将该命令的 **完整输出**（包括标准输出和标准错误）**原样**返回给我。这对于调试和确认命令是否成功执行至关重要。如果命令出现错误，务必包含完整的错误信息。

<示例>
用户：2 + 2
助手：4
</示例>

<示例>
用户：11是质数吗？
助手：true
</示例>

<示例>
用户：我应该运行什么命令来列出当前目录中的文件？
助手：ls
</示例>

<示例>
用户：src/目录中有哪些文件？
助手：[运行ls并看到foo.c、bar.c、baz.c]
用户：哪个文件包含foo的实现？
助手：src/foo.c
</示例>

<示例>
用户：为新功能编写测试
助手：[使用grep和glob搜索工具找到定义类似测试的位置，在一个工具调用中使用并发读取文件工具块同时读取相关文件，使用编辑文件工具编写新测试]
</示例>

# 主动性
- 在被要求时保持主动，但不要让用户感到意外
- 在做正确的事情和不越界之间保持平衡
- 如果用户询问如何处理某事，先回答问题而不是立即行动
- 除非用户要求，不要添加额外的代码解释摘要
- 处理完文件后直接停止，不要提供工作总结

# 合成消息
- 不要回应[用户中断请求]等系统合成消息
- 不要自己发送这类消息

# 遵循约定
- 理解并模仿现有的代码约定
- 使用库之前检查其可用性
- 查看现有组件的模式
- 遵循安全最佳实践
- 永远不要提交密钥或秘密信息

# 代码风格
- 不要在代码中添加注释，除非用户要求或代码复杂需要额外上下文

# 执行任务
1. 使用搜索工具理解代码库和查询
2. 使用所有可用工具实现解决方案
3. 通过测试验证解决方案
4. 运行lint和类型检查命令
- 除非明确要求，否则不要提交更改

# 工具使用政策
- 优先使用Agent工具进行文件搜索
- 无依赖关系的多个工具调用应在同一个function_calls块中进行

# Bash命令执行规范
{BASH_PROMPT}

# 代码处理规范
使用你的编程和语言技能解决任务。在以下情况中，为用户提供Python代码（放在python代码块中）或shell脚本（放在sh代码块中）来执行：
如```python
import os
print(os.getcwd())
```
1. 当你需要收集信息时，使用代码输出你需要的信息，例如浏览或搜索网络、下载/读取文件、打印网页或文件内容。当打印了足够的信息，并且任务可以基于你的语言能力解决时，你可以自己解决任务。

2. 当你需要用代码执行某些任务时，使用代码执行任务并输出结果。明智地完成任务。

执行规范：
- 如果需要，可以一步一步地解决任务
- 如果没有提供计划，请先解释你的计划
- 明确说明哪一步使用代码，哪一步使用你的语言能力
- 必须在代码块中指明脚本类型
- 提供完整可执行的代码，不要提供需要用户修改的代码
- 每次回复仅包含一个代码块
- 使用 print 函数输出结果，不要要求用户复制粘贴
- 检查执行结果，如有错误及时修复

结果处理：
- 如果结果表明有错误，请修复错误并修改文件
- 如果错误无法修复，或任务未解决：
  - 分析问题
  - 重新审视假设
  - 收集额外信息
  - 尝试不同方法
- 找到答案时仔细验证，并提供可验证的证据

# 环境信息
{ENV_INFO}

# 安全警告
{SECURITY_WARNINGS}

# 上下文管理
{CONTEXT_INFO}

# 任务上下文管理
{task_context}

# 命令执行说明
在执行每个命令之前，你需要用一句话简要说明将要执行什么命令以及目的。格式如下：

我将使用 [命令名] 来 [目的]。

示例：
- "我将使用 ls 命令来查看当前目录的内容。"
- "我将使用 git status 命令来检查文件的修改状态。"
- "我将使用 grep 命令来搜索包含特定文本的文件。"

# 工具集成
{TOOLS_SECTION}

当任务完成时，请回复"完成任务"。
"""

class AG2TwoAgentExecutor:
    """
    基于 AG2 的双代理执行器
    使用 AssistantAgent 和 LLMDrivenUserProxy 来执行任务
    适配 TaskExecutor 的接口规范
    """
    
    # 文件读取时间戳字典,key为文件路径,value为最后读取时间
    read_timestamps: Dict[str, float]
    
    def __init__(self,
                 config: ConfigManager = None,
                 tool_manager: AG2ToolManager = None,
                 context_manager = None,
                 task_context: str = "",
                 use_human_input: bool = False,
                 mcp_tool: Optional[MCPTool] = None):
        """初始化双代理执行器
        
        Args:
            config: 配置对象
            tool_manager: 工具管理器（可选）
            context_manager: 上下文管理器（可选，用于与TaskExecutor接口兼容）
            task_context: 任务上下文
            use_human_input: 是否使用标准UserProxyAgent而不是LLMDrivenUserProxy
                            设置为True时将使用标准的UserProxyAgent与真人交互
                            设置为False时使用LLMDrivenUserProxy自动处理工具调用
            mcp_tool: MCPTool实例（可选，用于MCP工具集成）
        """
        self.config = config or ConfigManager()
        self.tool_manager = tool_manager or AG2ToolManager()
        self.mcp_tool = mcp_tool
        
        # 初始化上下文管理器
        if context_manager:
            self.context_manager = context_manager
            # 使用当前工作目录创建 AG2 上下文管理器
            self.ag2_context_manager = ContextManager(cwd=os.getcwd())
        else:
            self.context_manager = TaskContext("default")
            # 使用当前工作目录创建 AG2 上下文管理器
            self.ag2_context_manager = ContextManager(cwd=os.getcwd())
            
        # 初始化工具加载器
        self.tool_loader = ToolLoader()
        
        # 使用标准配置格式，添加从config获取的温度参数
        temperature = config.config.get('llm', {}).get('temperature', 0.1)
        
        self.llm_config = {
            "config_list": [
                {
                    "model": "anthropic/claude-3.7-sonnet",
                    "base_url": "https://openrouter.ai/api/v1",
                    "api_key": os.environ.get("OPENROUTER_API_KEY")
                }
            ],
            "temperature": temperature,
            "cache_seed": 42,
        }
        
        # 使用模块级全局时间戳字典，确保所有工具共享同一个引用
        from ..agent_tools.global_timestamps import GLOBAL_TIMESTAMPS
        self.read_timestamps = GLOBAL_TIMESTAMPS
        
        # 添加路径标准化辅助函数
        self.normalize_path = lambda p: str(Path(p).resolve())
        
        self.task_context = task_context
        self.use_human_input = use_human_input

    async def initialize(self):
        """异步初始化方法"""
        # 根据配置选择不同的用户代理类型
        if self.use_human_input:
            # 使用标准UserProxyAgent，启用代码执行
            try:
                from autogen import UserProxyAgent
                
                # 创建UserProxyAgent，启用代码执行
                self.executor = UserProxyAgent(
                    name="用户代理",
                    human_input_mode="ALWAYS",
                    code_execution_config={
                        "work_dir": ".",  # 设置工作目录为当前目录
                        "use_docker": False  # 不使用docker执行
                    }
                )
                logging.info("使用标准UserProxyAgent，启用代码执行")
            except ImportError as e:
                logging.error(f"无法导入UserProxyAgent: {str(e)}，回退到LLMDrivenUserProxy")
                self.executor = LLMDrivenUserProxy(
                    name="用户代理", 
                    human_input_mode="ALWAYS"
                )
        else:
            # 使用LLMDrivenUserProxy进行自动化对话
            self.executor = LLMDrivenUserProxy(
                name="用户代理",
                human_input_mode="ALWAYS"
            )
            logging.info("使用LLMDrivenUserProxy，自动处理工具调用")
        
        # 构建系统提示词
        system_prompt = DEFAULT_SYSTEM_PROMPT.format(
            SECURITY_WARNINGS=self._build_security_warnings(),
            ENV_INFO=self._build_env_info(),
            CONTEXT_INFO=await self._build_context_info(),
            task_context=self.task_context,  
            TOOLS_SECTION=self._build_tools_prompt(),  # 初始为空，后续更新
            BASH_PROMPT=BASH_PROMPT
        )
        
        # 创建助手代理
        self.assistant = AssistantAgent(
            name="助手代理",
            system_message=system_prompt,
            llm_config=self.llm_config
        )
        
        # 初始化工具
        await self._initialize_tools()
        
        # 获取已加载的工具列表并更新系统提示词
        tools = self.tool_loader.load_tools_sync()
        updated_system_prompt = DEFAULT_SYSTEM_PROMPT.format(
            SECURITY_WARNINGS=self._build_security_warnings(),
            ENV_INFO=self._build_env_info(),
            CONTEXT_INFO=await self._build_context_info(),
            task_context=self.task_context,  
            TOOLS_SECTION=self._build_tools_prompt(),
            BASH_PROMPT=BASH_PROMPT
        )
        
        # 更新助手代理的系统提示词
        self.assistant.update_system_message(updated_system_prompt)

    @classmethod
    async def create(cls,
                    config: ConfigManager = None,
                    tool_manager: AG2ToolManager = None,
                    context_manager = None,
                    task_context: str = "",
                    use_human_input: bool = False,
                    mcp_tool: Optional[MCPTool] = None) -> 'AG2TwoAgentExecutor':
        """创建并初始化执行器的工厂方法
        
        Args:
            config: 配置对象
            tool_manager: 工具管理器
            context_manager: 上下文管理器
            task_context: 任务上下文
            use_human_input: 是否使用标准UserProxyAgent与真人交互
                            默认为False，使用LLMDrivenUserProxy
            mcp_tool: MCPTool实例（可选）
        Returns:
            初始化后的AG2TwoAgentExecutor实例
        """
        executor = cls(config, tool_manager, context_manager, task_context, use_human_input, mcp_tool)
        await executor.initialize()
        return executor

    async def _build_context_info(self) -> str:
        """构建上下文管理部分"""
        try:
            context = await self.ag2_context_manager.get_context()
            
            # 将上下文转换为XML格式
            context_parts = []
            for key, value in context.items():
                if value:
                    context_parts.append(f"<context name=\"{key}\">\n{value}\n</context>")
            
            if not context_parts:
                return "No additional context available."
                
            return "\n\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"构建上下文信息失败: {str(e)}")
            return "Error loading context information."

    def __del__(self):
        """析构函数"""
        pass
        
    def _build_tools_prompt(self) -> str:
        """构建工具部分的提示词 (重构后，使用 self._registered_tools_info)"""
        tools_section = []
        
        # 迭代内部存储的所有工具信息
        if not hasattr(self, '_registered_tools_info') or not self._registered_tools_info:
             return "此代理没有配置任何可用工具。"

        for tool_info in self._registered_tools_info:
            tool_name = tool_info.get("name", "Unknown Tool")
            description = tool_info.get("description", "No description available.")
            parameters = tool_info.get("parameters", {}) # AG2 JSON Schema
            prompt_details = tool_info.get("prompt_details", "") # 特定工具提示

            # 跳过 BashTool (或类似工具) 的显式描述，因为它有单独的处理方式
            if "bash" in tool_name.lower() or "shell" in tool_name.lower(): 
                logging.debug(f"Skipping prompt generation in TOOLS_SECTION for tool: {tool_name}")
                continue

            # 构建参数描述 (从 AG2 JSON Schema)
            params_desc = []
            if isinstance(parameters, dict) and parameters.get("type") == "object" and "properties" in parameters:
                params_desc.append("**参数**:")
                required_params = parameters.get("required", [])
                for param_name, param_info_detail in parameters["properties"].items():
                    required = "必需" if param_name in required_params else "可选"
                    param_type = param_info_detail.get("type", "未知")
                    desc = param_info_detail.get("description", "")
                    enum_desc = ""
                    if "enum" in param_info_detail:
                        enum_desc = f" (可选值: {', '.join(map(str, param_info_detail['enum']))})"
                    params_desc.append(f"- {param_name} ({param_type}, {required}): {desc}{enum_desc}")
            
            # 组装工具描述
            tool_section_parts = [
                f"### {tool_name}",
                f"{description}",
                "",
            ]
            
            if params_desc:
                tool_section_parts.extend(params_desc)
                tool_section_parts.append("")
            
            # 添加特定工具提示 (如果 tool_info 中有)
            if prompt_details:
                tool_section_parts.append(prompt_details)
            
            tool_section_parts.append("---")
                
            tools_section.append("\n".join(tool_section_parts))
        
        if not tools_section:
            return "此代理没有配置任何显式描述的工具（可能只有Bash/Shell工具）。"
            
        return "\n".join(tools_section)

    async def _initialize_tools(self):
        """异步初始化工具 (重构后，统一处理标准和 MCP 工具)"""
        self._registered_tools_info: List[Dict[str, Any]] = [] # 用于存储所有工具信息
        total_tools_initialized = 0
        successfully_registered_names = [] # 用于记录成功注册到AutoGen的函数名

        # --- 1. 初始化标准 AG2 工具 --- 
        try:
            standard_tools = self.tool_loader.load_tools_sync() # 假设同步加载OK
            logging.info(f"发现 {len(standard_tools)} 个标准 AG2 工具。")
            
            for tool_class, prompt in standard_tools:
                try:
                    # 跳过 BashTool (通常用代码块执行)
                    if "bash" in tool_class.__name__.lower() or "shell" in tool_class.__name__.lower():
                        logging.debug(f"Skipping standard BashTool registration: {tool_class.__name__}")
                        continue
                    
                    tool_instance = tool_class()
                    context = {
                        "read_timestamps": self.read_timestamps,
                        "normalize_path": self.normalize_path
                    }
                    
                    # 注册到 AG2ToolManager (如果需要外部访问)
                    # self.tool_manager.register_tool(
                    #     tool_class=tool_class,
                    #     prompt=prompt,
                    #     context=context
                    # )
                    
                    # 存储信息，用于构建提示词和注册AutoGen函数
                    tool_info = {
                        "name": tool_instance.name,
                        "description": tool_instance.description,
                        "parameters": tool_instance.parameters, # AG2 格式 JSON Schema
                        "prompt_details": prompt,
                        "instance": tool_instance, # 保留实例用于包装器
                        "is_mcp": False
                    }
                    self._registered_tools_info.append(tool_info)
                    logging.debug(f"成功准备标准工具信息: {tool_instance.name}")
                    total_tools_initialized += 1
                    
                except Exception as e:
                    logging.error(f"初始化标准工具 {tool_class.__name__} 失败: {str(e)}", exc_info=True)
                    continue
            logging.info(f"成功准备 {total_tools_initialized} 个标准工具的信息。")
            
        except Exception as e:
            logging.error(f"加载标准工具失败: {str(e)}", exc_info=True)

        # --- 2. 初始化 MCP 工具 --- 
        if self.mcp_tool:
            mcp_tools_initialized = 0
            try:
                logging.info("开始初始化 MCP 工具...")
                # 从 MCPTool 获取 AG2 格式的工具列表
                ag2_mcp_tools = await self.mcp_tool.get_tools() 
                logging.info(f"从 MCPTool 获取了 {len(ag2_mcp_tools)} 个工具定义。")

                for tool_info in ag2_mcp_tools:
                    try:
                        mcp_tool_name = tool_info.get("name")
                        if not mcp_tool_name:
                            logging.warning("发现一个没有名称的 MCP 工具，已跳过。")
                            continue

                        logging.debug(f"准备 MCP 工具信息: {mcp_tool_name}")
                        
                        # 存储信息
                        self._registered_tools_info.append({
                            "name": mcp_tool_name,
                            "description": tool_info.get("description", ""),
                            "parameters": tool_info.get("parameters", {}), # 应该是 AG2 格式
                            "prompt_details": "", # 可以添加特定提示
                            "instance": None, # 不需要单独实例
                            "is_mcp": True,
                            "mcp_tool_ref": self.mcp_tool # 引用主 MCPTool 实例
                        })
                        mcp_tools_initialized += 1
                        logging.debug(f"成功准备 MCP 工具信息: {mcp_tool_name}")

                    except Exception as e:
                        mcp_tool_name_err = tool_info.get('name', '未知名称')
                        logging.error(f"处理 MCP 工具 {mcp_tool_name_err} 失败: {str(e)}", exc_info=True)
                        continue
                
                logging.info(f"成功准备 {mcp_tools_initialized} 个 MCP 工具的信息。")
                total_tools_initialized += mcp_tools_initialized

            except Exception as e:
                logging.error(f"获取或处理 MCP 工具列表失败: {str(e)}", exc_info=True)
        else:
            logging.info("未提供 MCPTool 实例，跳过 MCP 工具初始化。")

        logging.info(f"总共准备了 {total_tools_initialized} 个工具的信息，准备注册到 AutoGen...")

        # --- 3. 统一注册所有工具到 AutoGen --- 
        registered_count = 0
        if not self.assistant or not self.executor:
             logging.error("AutoGen Assistant or Executor 未初始化，无法注册函数。")
             return # Or raise an error

        for tool_info in self._registered_tools_info:
            tool_name = tool_info["name"]
            description = tool_info["description"]
            parameters = tool_info["parameters"] # AG2 JSON Schema
            prompt_details = tool_info.get("prompt_details", "")
            is_mcp = tool_info["is_mcp"]

            # 构建 AutoGen 需要的函数描述 (合并 description, 参数, prompt_details)
            params_desc_list = []
            if isinstance(parameters, dict) and parameters.get("type") == "object" and "properties" in parameters:
                required_params = parameters.get("required", [])
                for param_name, param_info_detail in parameters["properties"].items():
                    required = "必需" if param_name in required_params else "可选"
                    param_type = param_info_detail.get("type", "未知")
                    desc = param_info_detail.get("description", "")
                    enum_desc = ""
                    if "enum" in param_info_detail:
                        enum_desc = f" (可选值: {', '.join(map(str, param_info_detail['enum']))})"
                    params_desc_list.append(f"- {param_name} ({param_type}, {required}): {desc}{enum_desc}")
            params_section = ""            
            if params_desc_list:
                 params_section = "\\n**参数**:\\n" + "\\n".join(params_desc_list)
            # 完整描述，包含参数信息和特定提示
            full_description = f"{description}{params_section}\\n\\n{prompt_details}".strip()

            registration_successful = False 
            try:
                if is_mcp:
                    # --- MCP 工具包装器 --- 
                    mcp_tool_instance = tool_info["mcp_tool_ref"]
                    # 使用闭包捕获工具名和 MCPTool 实例
                    async def mcp_executor_func(captured_tool_name = tool_name, mcp_tool_ref = mcp_tool_instance, **kwargs: Any):
                        # 尝试处理嵌套参数问题 (AutoGen 有时会把参数包在 'params' 或 'kwargs' 里)
                        actual_params = kwargs
                        if len(kwargs) == 1:
                            first_key = next(iter(kwargs))
                            if first_key in ['params', 'kwargs'] and isinstance(kwargs[first_key], dict):
                                logging.warning(f"Detected nested '{first_key}' in MCP args... Extracting inner dict.")
                                actual_params = kwargs[first_key]
                        
                        logger.debug(f"Executing MCP tool '{captured_tool_name}' with params: {actual_params}")
                        try:
                             # 调用 MCPTool 的 execute 方法
                             return await mcp_tool_ref.execute(captured_tool_name, actual_params)
                        except Exception as e_exec:
                             logger.error(f"Error executing MCP tool {captured_tool_name}: {e_exec}", exc_info=True)
                             return {"error": True, "message": f"Failed to execute {captured_tool_name}: {str(e_exec)}"}
                    
                    # 设置函数元信息
                    mcp_executor_func.__name__ = tool_name
                    mcp_executor_func.__doc__ = full_description
                    target_func = mcp_executor_func
                
                else:
                    # --- 标准 AG2 工具包装器 --- 
                    tool_instance = tool_info["instance"]
                    if not tool_instance:
                        logging.warning(f"Skipping registration for standard tool {tool_name} due to missing instance.")
                        continue
                    # 使用闭包捕获工具实例
                    async def standard_executor_func(tool_inst = tool_instance, **kwargs: Any):
                        # 同样处理嵌套参数
                        params_to_pass = kwargs
                        if len(kwargs) == 1:
                             first_key = next(iter(kwargs))
                             if first_key in ['params', 'kwargs'] and isinstance(kwargs[first_key], dict):
                                  logging.warning(f"Detected nested '{first_key}' for standard tool... Using inner dict.")
                                  params_to_pass = kwargs[first_key]
                        
                        logger.debug(f"Executing standard tool '{tool_inst.name}' with params dict: {params_to_pass}")
                        try:
                             # 调用标准工具的 execute 方法
                             return await tool_inst.execute(params=params_to_pass)
                        except Exception as e_exec:
                             logger.error(f"Error executing standard tool {tool_inst.name}: {e_exec}", exc_info=True)
                             return {"error": True, "message": f"Failed to execute {tool_inst.name}: {str(e_exec)}"}

                    # 设置函数元信息
                    standard_executor_func.__name__ = tool_name
                    standard_executor_func.__doc__ = full_description
                    target_func = standard_executor_func

                # --- 注册到 AutoGen --- 
                register_function(
                     target_func, 
                     caller=self.assistant, # Assistant Agent 发起调用
                     executor=self.executor, # UserProxyAgent (或 LLMDrivenUserProxy) 执行
                     name=tool_name, # 函数名，LLM 需要匹配这个名字
                     description=full_description # 描述，给LLM看，包含参数等信息
                )
                registration_successful = True 

                if registration_successful:
                    logging.debug(f"成功注册 AutoGen 函数: {tool_name}")
                    registered_count += 1
                    successfully_registered_names.append(tool_name)

            except Exception as e:
                 logging.error(f"注册 AutoGen 函数 {tool_name} 失败: {str(e)}", exc_info=True)
        
        logging.info(f"总共成功注册 {registered_count} 个函数到 AutoGen。")
        logging.info(f"成功注册的函数名称: {successfully_registered_names}")

    def _safe_get_message_attribute(self, message: Any, attr_name: str, default_value: Any = "") -> Any:
        """安全获取消息的属性或键值
        
        支持从字典、对象或其他类型的消息中获取属性值
        
        Args:
            message: 消息对象或字典
            attr_name: 属性或键名
            default_value: 默认值，当属性不存在时返回
            
        Returns:
            属性值或默认值
        """
        try:
            if isinstance(message, dict):
                return message.get(attr_name, default_value)
            elif hasattr(message, attr_name):
                return getattr(message, attr_name, default_value)
            else:
                return default_value
        except Exception as e:
            logger.warning(f"获取消息属性 {attr_name} 时出错: {str(e)}")
            return default_value

    def _execute_with_timeout(self, prompt: str, task_definition: Dict[str, Any], 
                              task_context: TaskContext, timeout: Optional[int]) -> Dict[str, Any]:
        """同步执行任务，带超时控制"""
        try:
            # 1. 从 TaskContext 获取对话历史并转换为 AG2 格式
            conversation_history = task_context.local_context.get('conversation_history', [])
            recent_history = self._filter_recent_history(conversation_history, 5)
            
            ag2_messages = []
            for msg in recent_history:
                ag2_messages.append({
                    "name": "task_assistant" if msg["role"] == "assistant" else "task_executor",
                    "content": msg["content"]
                })
            
            # 2. 将 read_timestamps 添加到上下文
            task_context.update_local('read_timestamps', self.read_timestamps)
            
            # 3. 直接执行对话，使用concurrent.futures在线程池中执行，添加超时控制
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    self.executor.initiate_chat,
                    self.assistant,
                    message=prompt,
                    chat_history=ag2_messages
                )
                
                # 添加超时控制
                try:
                    chat_result = future.result(timeout=timeout or self.llm_config.get("timeout", 500))
                except concurrent.futures.TimeoutError:
                    logger.error(f"任务执行超时 (timeout={timeout}s)")
                    return {
                        "status": "error",
                        "error_msg": f"任务执行超时 (timeout={timeout}s)",
                        "task_status": "TIMEOUT",
                        "success": False
                    }
            
            # 4. 从上下文中更新 read_timestamps
            updated_timestamps = task_context.local_context.get('read_timestamps', {})
            self.read_timestamps.update(updated_timestamps)
            
            # 5. 如果上下文中有新的read_timestamps，合并到self.read_timestamps
            # 注: 大部分更新应该已经在工具调用时完成，这里是为了确保从上下文获取其他可能的更新
            if 'read_timestamps' in task_context.local_context:
                self.read_timestamps.update(task_context.local_context['read_timestamps'])
            
            # 6. 将新的对话结果转换并追加到历史记录
            new_messages = []
            if hasattr(chat_result, 'chat_history') and chat_result.chat_history:
                for msg in chat_result.chat_history:
                    try:
                        name = self._safe_get_message_attribute(msg, 'name')
                        content = self._safe_get_message_attribute(msg, 'content')
                        timestamp = self._safe_get_message_attribute(msg, 'timestamp', '')
                        
                        new_messages.append({
                            "role": "assistant" if name == "task_assistant" or name == "任务助手" else "user",
                            "content": content,
                            "timestamp": timestamp
                        })
                    except Exception as e:
                        logger.warning(f"处理消息时出错: {str(e)}, 消息类型: {type(msg)}")
                        continue
            
            # 7. 更新回 TaskContext
            task_context.update_local('conversation_history', conversation_history + new_messages)
            
            # 8. 分析对话结果
            task_status = self._analyze_chat_result(chat_result, task_definition)
            final_response = self._extract_final_response(chat_result)
            
            # 9. 根据任务状态返回结果
            logger.info(f"任务状态: {task_status}")
            
            if task_status == "COMPLETED":
                logger.info("根据任务状态标记为成功")
                return {
                    "status": "success",
                    "output": final_response,
                    "task_status": "COMPLETED",
                    "success": True
                }
            else:
                logger.info(f"任务未完成或执行出错，状态: {task_status}")
                return {
                    "status": "error",
                    "output": final_response,
                    "task_status": task_status,
                    "success": False,
                    "error_msg": "任务未完成或执行出错"
                }
            
        except Exception as e:
            logger.error(f"任务执行出错: {str(e)}")
            return {
                "status": "error",
                "error_msg": str(e),
                "task_status": "ERROR",
                "success": False
            }

    def execute(self, prompt: str, task_definition: dict = None, task_context = None, timeout: int = 600):
        """执行任务
        
        Args:
            prompt: 任务提示
            task_definition: 任务定义
            task_context: 任务上下文
            timeout: 超时时间（秒）
        """
        try:
            # 如果提供了任务上下文，更新当前上下文
            if task_context:
                self.context_manager = task_context
            
            # 使用已初始化的代理
            if not hasattr(self, 'executor') or not hasattr(self, 'assistant'):
                raise RuntimeError("执行器未正确初始化，请使用 create() 方法创建实例")
            
            # 初始化对话
            chat_result = self.executor.initiate_chat(
                self.assistant,
                message=prompt,
                silent=False
            )
            
            # --- 在这里添加代码，记录 initiate_chat 的完整结果 ---
            try:
                if chat_result and hasattr(chat_result, 'chat_history'):
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                    filename = f"debug_executor_chat_result_history_{timestamp}.json"
                    cwd = os.getcwd() # 获取当前工作目录
                    filepath = os.path.join(cwd, filename)
                    
                    # 尝试序列化聊天历史，处理无法序列化的对象
                    def safe_serialize(obj):
                        if isinstance(obj, (str, int, float, bool, list, dict)) or obj is None:
                            return obj
                        elif hasattr(obj, 'name'): # 尝试获取 Agent 的 name
                            return f"<Agent: {obj.name}>"
                        else:
                            return f"<object of type {type(obj).__name__} not serializable>"

                    # 创建可序列化的历史记录副本
                    serializable_history = []
                    if isinstance(chat_result.chat_history, list):
                        for msg in chat_result.chat_history:
                            if isinstance(msg, dict):
                                serializable_msg = {k: safe_serialize(v) for k, v in msg.items()}
                                serializable_history.append(serializable_msg)
                            else:
                                serializable_history.append(safe_serialize(msg)) # 处理非字典消息
                    
                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump(serializable_history, f, indent=2, ensure_ascii=False)
                    logger.info(f"Successfully wrote executor chat result history to: {filepath}")
                else:
                    logger.warning("chat_result or chat_result.chat_history not found, cannot write executor debug history.")
            except Exception as e:
                logger.error(f"Failed to write executor chat result history to file: {e}", exc_info=True)
            # --- 记录结束 ---

            return {
                "status": "success",
                "result": chat_result,
                "task_status": "COMPLETED",
                "success": True
            }
            
        except Exception as e:
            logger.error(f"任务执行出错: {str(e)}")
            return {
                "status": "error",
                "error_msg": str(e),
                "task_status": "ERROR",
                "success": False
            }

    def _filter_recent_history(self, history: list, max_turns: int) -> list:
        """
        筛选最近的对话历史
        
        Args:
            history: 完整的对话历史
            max_turns: 保留的最大对话轮次
            
        Returns:
            筛选后的对话历史
        """
        # 如果历史记录为空，直接返回
        if not history:
            return []
        
        # 计算一轮对话(一问一答)需要的消息数
        messages_per_turn = 2
        max_messages = max_turns * messages_per_turn
        
        # 如果历史消息数量在限制范围内，返回全部
        if len(history) <= max_messages:
            return history
        
        # 否则只返回最近的几轮对话
        return history[-max_messages:]
        
    def _build_message(self, prompt: str, task_definition: Dict[str, Any]) -> str:
        """构建完整的任务消息"""
        # 组合关键信息
        message_parts = [
            prompt,
            "\n## 任务要求",
            f"任务ID: {task_definition.get('id', 'unknown')}",
        ]
        
        # 添加输出文件要求
        if 'output_files' in task_definition:
            message_parts.append("\n## 输出文件要求")
            for output_type, path in task_definition['output_files'].items():
                message_parts.append(f"- {output_type}: {path}")
                
        # 添加成功标准
        if 'success_criteria' in task_definition:
            message_parts.append("\n## 成功标准")
            for criteria in task_definition['success_criteria']:
                message_parts.append(f"- {criteria}")
                
        return "\n".join(message_parts)
        
    def _analyze_chat_result(self, chat_result: Any, task_definition: Dict[str, Any]) -> str:
        """
        分析对话结果,检查任务完成状态
        
        Args:
            chat_result: 对话结果
            task_definition: 任务定义
            
        Returns:
            str: 任务状态 (COMPLETED/ERROR)
        """
        try:
            # 添加详细调试日志
            logger.info("======= 开始分析聊天结果 =======")
            logger.info(f"聊天结果类型: {type(chat_result)}")
            
            chat_history = None
            if hasattr(chat_result, 'chat_history'):
                chat_history = chat_result.chat_history
                logger.info(f"聊天历史类型: {type(chat_history)}")
                logger.info(f"聊天历史长度: {len(chat_history)}")
            elif isinstance(chat_result, dict) and 'chat_history' in chat_result:
                chat_history = chat_result['chat_history']
                logger.info(f"聊天历史类型(字典): {type(chat_history)}")
                logger.info(f"聊天历史长度: {len(chat_history)}")
            else:
                logger.warning("未找到聊天历史")
            
            # 详细记录每条消息
            if chat_history:
                for i, msg in enumerate(chat_history):
                    logger.info(f"消息 #{i+1}:")
                    logger.info(f"类型: {type(msg)}")
                    
                    if isinstance(msg, dict):
                        logger.info(f"键: {list(msg.keys())}")
                        for k, v in msg.items():
                            logger.info(f"  {k}: {v}")
                    else:
                        # 尝试使用常见属性获取信息
                        name = self._safe_get_message_attribute(msg, 'name', 'unknown')
                        content = self._safe_get_message_attribute(msg, 'content', '')
                        role = self._safe_get_message_attribute(msg, 'role', 'unknown')
                        logger.info(f"  name: {name}")
                        logger.info(f"  role: {role}")
                        logger.info(f"  content: {content}")
            
            # 0. 优先检查最后一条消息是否包含exit信号
            if hasattr(chat_result, 'chat_history') and chat_result.chat_history:
                # 获取最后一条消息
                last_msg = chat_result.chat_history[-1]
                content = self._safe_get_message_attribute(last_msg, 'content', '').lower()
                name = self._safe_get_message_attribute(last_msg, 'name', '')
                
                logger.info(f"检查最后一条消息: '{content}' (发送者: {name})")
                
                # 详细记录匹配逻辑
                has_exit = content.endswith('exit') or ' exit' in content or content == 'exit'
                logger.info(f"content.endswith('exit'): {content.endswith('exit')}")
                logger.info(f"' exit' in content: {' exit' in content}")
                logger.info(f"content == 'exit': {content == 'exit'}")
                logger.info(f"最终判断 exit 信号: {has_exit}")
                
                # 检查TERMINATE关键词
                has_terminate = 'terminate' in content.lower()
                logger.info(f"'terminate' in content.lower(): {has_terminate}")
                
                if has_exit:
                    logger.info(f"检测到exit信号，最后消息: '{content}'，标记任务为完成")
                    return "COMPLETED"
                
                if has_terminate:
                    logger.info(f"检测到TERMINATE信号，最后消息: '{content}'，标记任务为完成")
                    return "COMPLETED"
            
            # 1. 检查基本错误
            error = self._safe_get_message_attribute(chat_result, 'error')
                
            if error:
                logger.warning(f"对话结果包含错误: {error}")
                return "ERROR"
            
            # 2. 检查判断结果
            judgment = self._safe_get_message_attribute(chat_result, 'judgment')
            judgment_type = None
                
            # 从judgment中获取类型信息
            if judgment:
                judgment_type = self._safe_get_message_attribute(judgment, 'type')
                    
                if judgment_type == 'TASK_COMPLETED':
                    logger.info("根据判断结果标记任务为完成")
                    return "COMPLETED"
            
            # 3. 检查必要的输出文件是否存在
            if 'output_files' in task_definition:
                missing_files = []
                for output_type, path in task_definition['output_files'].items():
                    if not os.path.exists(path):
                        missing_files.append(path)
                        
                if missing_files:
                    logger.warning(f"缺少输出文件: {missing_files}")
                    return "ERROR"
            
            # 4. 检查对话历史中的最后几条消息
            chat_history = None
            if hasattr(chat_result, 'chat_history'):
                chat_history = chat_result.chat_history
            elif isinstance(chat_result, dict) and 'chat_history' in chat_result:
                chat_history = chat_result['chat_history']
                
            if chat_history:
                # 取最后几条消息
                last_messages = chat_history[-3:]
                for msg in reversed(last_messages):
                    name = self._safe_get_message_attribute(msg, 'name')
                    content = self._safe_get_message_attribute(msg, 'content', '').lower()
                        
                    if name == 'task_assistant' or name == '任务助手':
                        # 检查是否包含完成或失败的关键词
                        if 'task completed' in content or '任务完成' in content or 'completed' in content:
                            logger.info("根据对话内容标记任务为完成")
                            return "COMPLETED"
                        elif 'failed' in content or '失败' in content or 'error' in content:
                            logger.info("根据对话内容标记任务为失败")
                            return "ERROR"
            
            # 5. 如果没有明确的完成标志，返回ERROR
            return "ERROR"
        except Exception as e:
            logger.error(f"分析对话结果时出错: {str(e)}")
            return "ERROR"
        
    def _extract_final_response(self, chat_result: Any) -> str:
        """提取最终响应"""
        try:
            if hasattr(chat_result, 'chat_history') and chat_result.chat_history:
                # 获取最后一条助手消息
                for message in reversed(chat_result.chat_history):
                    name = self._safe_get_message_attribute(message, 'name')
                    if name == 'task_assistant' or name == '任务助手':
                        return self._safe_get_message_attribute(message, 'content')
            elif isinstance(chat_result, dict) and 'chat_history' in chat_result:
                # 字典形式的聊天历史
                for message in reversed(chat_result['chat_history']):
                    name = self._safe_get_message_attribute(message, 'name')
                    if name == 'task_assistant' or name == '任务助手':
                        return self._safe_get_message_attribute(message, 'content')
            
            # 如果找不到特定消息，尝试获取最后一条消息
            if hasattr(chat_result, 'chat_history') and chat_result.chat_history:
                if chat_result.chat_history:
                    last_msg = chat_result.chat_history[-1]
                    return self._safe_get_message_attribute(last_msg, 'content')
                    
            return ""
        except Exception as e:
            logger.error(f"提取最终响应时出错: {str(e)}")
            return ""

    def execute_subtask(self, subtask, task_context=None):
        """
        执行单个子任务
        
        参数:
            subtask (dict): 子任务定义
            task_context (TaskContext, optional): 任务上下文
            
        返回:
            dict: 执行结果
        """
        # 获取任务ID
        subtask_id = subtask.get('id', 'unknown')
        subtask_name = subtask.get('name', subtask_id)
        logger.info(f"开始执行子任务: {subtask_name} (ID: {subtask_id})")
        
        # 如果没有提供任务上下文，尝试获取或创建一个新的
        if task_context is None:
            try:
                if self.context_manager is not None:
                    # 如果上下文不存在，创建一个新的
                    if subtask_id not in self.context_manager.task_contexts:
                        logger.info(f"为子任务 {subtask_id} 创建新的上下文")
                        task_context = self.context_manager.create_subtask_context('root', subtask_id)
                    else:
                        logger.info(f"使用已存在的上下文: {subtask_id}")
                        task_context = self.context_manager.task_contexts[subtask_id]
                else:
                    # 如果没有上下文管理器，创建一个独立的上下文
                    from task_planner.core.context_management import TaskContext
                    logger.info(f"创建独立上下文: {subtask_id} (无上下文管理器)")
                    task_context = TaskContext(subtask_id)
            except Exception as e:
                logger.error(f"创建或获取任务上下文时出错: {str(e)}")
                return {
                    "status": "error",
                    "error_msg": f"上下文初始化失败: {str(e)}",
                    "task_status": "ERROR",
                    "success": False
                }
        
        try:
            # 构建任务提示
            prompt = self._build_message(subtask.get('description', ''), subtask)
            logger.info(f"子任务 {subtask_id} 提示构建完成，长度: {len(prompt)}")
            
            # 执行任务
            logger.info(f"开始执行子任务 {subtask_id} 主体逻辑")
            result = self.execute(
                prompt=prompt,
                task_definition=subtask,
                task_context=task_context,
                timeout=subtask.get('timeout', None)
            )
            
            # 检查结果并记录
            task_status = result.get('task_status', 'UNKNOWN')
            success = result.get('success', False)
            status_str = "成功" if success else "失败"
            logger.info(f"子任务 {subtask_id} 执行完成，状态: {task_status}，结果: {status_str}")
            
            # 清晰的返回格式，确保TaskDecompositionSystem能正确处理
            return {
                "status": "success" if success else "error",
                "output": result.get('output', ''),
                "task_status": task_status,
                "success": success,
                "error_msg": result.get('error_msg', '') if not success else None
            }
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"子任务 {subtask_id} 执行过程中出现异常: {error_msg}", exc_info=True)
            return {
                "status": "error",
                "error_msg": error_msg,
                "task_status": "ERROR",
                "success": False
            }

    def _build_security_warnings(self) -> str:
        """构建安全警告部分"""
        return """
        重要提示：
        1. 拒绝编写或解释可能被恶意使用的代码
        2. 在处理文件时，检查文件用途，拒绝处理恶意代码
        3. 不要提交或泄露任何密钥或敏感信息
        """

    def _build_env_info(self) -> str:
        """构建环境信息部分"""
        # 获取 ContextManager 知道的 CWD
        # 使用 self.ag2_context_manager.cwd (在 executor 初始化时设置)
        initial_cwd = self.ag2_context_manager.cwd if hasattr(self, 'ag2_context_manager') and self.ag2_context_manager else os.getcwd()
        return f"""
        平台：{platform.system()}
        今天日期：{datetime.now().strftime('%Y-%m-%d')}
        模型：{self.llm_config['config_list'][0]['model']}
        初始工作目录: {initial_cwd}
        """
