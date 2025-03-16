# TaskPlanner Refactor V3 - 改进任务执行状态判断与路径处理

## 主要问题分析

### 1. 任务状态判断问题
当前系统在不使用Gemini的情况下始终将任务状态标记为"COMPLETED"，而不是基于任务实际完成情况判断。即使使用Gemini，也没有将任务定义传递给Gemini作为判断依据。

### 2. 文件路径处理问题
Claude在创建文件时使用了错误的导入路径，并且系统没有在提示中明确指定工作目录、目标路径和文件名的完整关系。

### 3. 工具调用实现问题
当前实现没有充分利用已有的agent tool call系统（位于 `/home/wangbo/document/wangbo/task_planner/src/task_planner/vendor/claude_client/agent_tools/`）进行工具调用的标准化处理。该目录下已经实现了`tool_manager.py`、`parser.py`及`gemini_analyzer.py`等组件。

## 改进方案

### 1. 改进Gemini任务状态判断

#### claude_cli.py改进
```python
def claude_api(prompt, task_definition=None, verbose=False, timeout=500, use_gemini=True, conversation_history=None):
    """
    向Claude发送一个问题并获取回答。
    
    Args:
        prompt (str): 要发送给Claude的问题
        task_definition (dict, optional): 当前任务定义，用于任务状态判断
        verbose (bool): 是否打印详细信息
        timeout (int): 命令执行超时时间(秒)
        use_gemini (bool): 是否使用Gemini来判断任务完成状态，默认为True
        conversation_history (list): 对话历史，适用于继续之前的对话
        
    Returns:
        dict: 包含结果的字典，包括status、output、error_msg和task_status
    """
    # 现有代码...
    
    if use_gemini:
        # 改进Gemini分析器初始化，传入任务定义
        # 使用已有的GeminiTaskAnalyzer（位于agent_tools目录下）
        try:
            from task_planner.vendor.claude_client.agent_tools.gemini_analyzer import GeminiTaskAnalyzer
            analyzer = GeminiTaskAnalyzer()
            # 扩展analyze方法以接收任务定义
            analyzer.task_definition = task_definition
        except ImportError:
            if verbose:
                print("未能导入GeminiTaskAnalyzer")
            use_gemini = False
        
        # ...其他代码
    else:
        # 使用原始客户端，但返回待验证状态而非直接COMPLETED
        # ...其他代码
        return {
            "status": "success",
            "output": response,
            "error_msg": "",
            "task_status": "NEEDS_VERIFICATION"  # 修改为需要验证状态
        }
```

#### 扩展GeminiTaskAnalyzer

通过扩展已有的GeminiTaskAnalyzer类（位于`/home/wangbo/document/wangbo/task_planner/src/task_planner/vendor/claude_client/agent_tools/gemini_analyzer.py`），添加任务定义参数和相关分析方法。

```python
# 在现有的gemini_analyzer.py中扩展_build_analyzer_prompt方法

def _build_analyzer_prompt(self, 
                         conversation_history: List[Tuple[str, str]], 
                         last_response: str) -> str:
    """构建分析提示，加入任务定义作为判断依据"""
    # 获取原始请求
    original_request = conversation_history[0][0] if conversation_history else "无"
    
    # 构建对话历史摘要
    history_summary = "\n".join([
        f"用户: {q}\nAI: {a[:100]}..." 
        for q, a in conversation_history[:-1]
    ]) if len(conversation_history) > 1 else "无之前对话"
    
    # 检测任务类型
    task_type = self._detect_task_type(original_request)
    
    # 添加任务定义信息（如果有）
    task_definition_text = ""
    if hasattr(self, 'task_definition') and self.task_definition:
        # 提取任务关键信息
        task_id = self.task_definition.get('id', 'unknown')
        task_name = self.task_definition.get('name', 'unknown')
        task_description = self.task_definition.get('description', 'unknown')
        
        # 提取输出文件要求
        output_files = self.task_definition.get('output_files', {})
        output_files_text = "\n".join([f"- {key}: {value}" for key, value in output_files.items()])
        
        # 提取成功标准
        success_criteria = self.task_definition.get('success_criteria', [])
        success_criteria_text = "\n".join([f"- {criterion}" for criterion in success_criteria])
        
        # 构建任务定义部分
        task_definition_text = f"""
        ## 任务定义
        - 任务ID: {task_id}
        - 任务名称: {task_name}
        - 任务描述: {task_description}
        
        ## 输出文件要求
        {output_files_text}
        
        ## 成功标准
        {success_criteria_text}
        """
    
    # 创建提示
    prompt = f"""
    分析下面AI回复是否完成了用户的请求。
    
    原始请求: {original_request}
    
    任务类型: {task_type}
    
    {task_definition_text}
    
    对话历史摘要:
    {history_summary}
    
    最新AI回复:
    {last_response[:500]}...
    
    根据以下标准分析AI回复:
    1. 回复是否直接且完整地回答了用户的请求
    2. 回复是否包含所有必要的细节和信息
    3. 回复是否提及创建了任务定义中要求的所有输出文件
    4. 回复是否满足了所有的成功标准
    
    只返回以下三种状态之一（不要解释你的选择）:
    COMPLETED - 任务已经完成，无需进一步交互
    NEEDS_MORE_INFO - 需要用户提供更多信息才能继续
    CONTINUE - 任务进行中但尚未完成，AI应该继续
    """
    
    return prompt
```

### 2. 改进TaskExecutor中的路径处理和状态判断

#### 改进_prepare_context_aware_prompt方法
```python
def _prepare_context_aware_prompt(self, subtask, task_context):
    # 提取基本任务信息...
    
    # 添加当前工作目录信息
    current_working_dir = os.getcwd()
    context_dir = self.context_manager.context_dir if self.context_manager else "output/logs/subtasks_execution"
    
    prompt_parts = [
        f"# 任务：{task_name}",
        instruction,
        f"\n## 环境信息",
        f"当前工作目录: {current_working_dir}",
        f"上下文目录: {context_dir}",
    ]
    
    # 添加输出文件路径，使用绝对路径
    if 'output_files' in subtask and isinstance(subtask['output_files'], dict):
        prompt_parts.append("\n## 输出文件要求")
        prompt_parts.append("你必须创建以下具体文件（使用完整的绝对路径）：")
        
        for output_type, output_path in subtask['output_files'].items():
            # 确保路径是绝对路径
            if not os.path.isabs(output_path):
                if self.context_manager and self.context_manager.context_dir:
                    if os.path.isabs(self.context_manager.context_dir):
                        output_path = os.path.join(self.context_manager.context_dir, output_path)
                    else:
                        output_path = os.path.join(current_working_dir, self.context_manager.context_dir, output_path)
                else:
                    output_path = os.path.join(current_working_dir, output_path)
            
            prompt_parts.append(f"- {output_type}: {output_path}")
    
    # 增强提示，更强调文件创建与路径重要性
    prompt_parts.append("\n## 重要提示 - 文件创建：")
    prompt_parts.append("1. 你必须实际创建上述所有文件，必须使用完整的绝对路径")
    prompt_parts.append("2. 不要尝试使用相对路径，必须使用指定的完整绝对路径")
    prompt_parts.append("3. 当导入其他文件时，请使用它们的正确绝对路径或相对路径")
    prompt_parts.append("4. 不要尝试运行代码或执行其他文件，只需创建所需文件")
    # 其他提示...
    
    # 合并所有部分...
```

#### 改进execute_subtask方法
```python
def execute_subtask(self, subtask, task_context=None):
    # 现有代码...
    
    # 使用claude_api时传入任务定义
    response = claude_api(
        prompt,
        task_definition=subtask,  # 传入完整任务定义
        verbose=self.verbose,
        timeout=task_timeout,
        use_gemini=self.use_gemini,
        conversation_history=conversation_history
    )
    
    # 处理任务状态
    if 'task_status' in response:
        task_status = response['task_status']
        logger.info(f"任务状态分析: {task_status}")
        task_context.update_local('task_status', task_status)
        
        # 当状态为NEEDS_VERIFICATION时进行额外验证
        if task_status == "NEEDS_VERIFICATION":
            # 验证所有预期的输出文件是否已经被创建
            missing_files = self._verify_output_files(subtask)
            if missing_files:
                # 文件缺失，修改状态为错误
                task_status = "ERROR"
                error_msg = f"任务执行失败：AI未能创建预期的输出文件。缺失的文件：\n" + "\n".join(missing_files)
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "task_id": subtask.get("id", "unknown"),
                    "result": {"details": error_msg}
                }
            else:
                # 所有文件都存在，修改状态为完成
                task_status = "COMPLETED"
                logger.info("通过文件验证，任务状态更新为COMPLETED")
    
    # 其余代码...
```

### 3. 使用已有的Agent Tool Call机制

利用项目中现有的agent_tools（位于`/home/wangbo/document/wangbo/task_planner/src/task_planner/vendor/claude_client/agent_tools/`）包中的工具调用系统，实现向Claude输入的工具：

```python
def execute_subtask(self, subtask, task_context=None):
    # 现有代码...
    
    # 导入已有的工具管理器和解析器
    try:
        from task_planner.vendor.claude_client.agent_tools.tool_manager import ToolManager
        from task_planner.vendor.claude_client.agent_tools.parser import DefaultResponseParser
        from task_planner.vendor.claude_client.agent_tools.tools import BaseTool
    except ImportError:
        logger.warning("无法导入agent_tools包，将使用基础功能")
        # 继续使用现有代码...
    
    # 创建Claude交互工具
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
                # 这里应该实现向Claude Code发送文字输入的逻辑
                # 可能需要使用pexpect或其他方式与Claude进程交互
                logger.info(f"向Claude发送输入: {message}")
                
                # 这里是示例实现，实际应根据claude_client的实现方式
                try:
                    from task_planner.vendor.claude_client.claude_client import send_input_to_claude
                    result = send_input_to_claude(message)
                    return {
                        "success": True,
                        "message": f"成功向Claude发送输入",
                        "response": result
                    }
                except (ImportError, AttributeError):
                    logger.warning("无法直接调用Claude输入方法，将通过Claude API实现")
                    # 作为备选方案，可以通过再次调用claude_api来实现
                    return {
                        "success": True,
                        "message": "将在后续步骤中通过API重新发送请求"
                    }
                    
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e)
                }
    
    # 注册工具
    tool_manager = ToolManager()
    tool_manager.register_tool("claude_input", ClaudeInputTool())
    
    # 创建响应解析器
    response_parser = DefaultResponseParser()
    
    # 当Gemini任务分析返回CONTINUE状态时使用此工具
    if 'task_status' in response and response['task_status'] == "CONTINUE":
        try:
            # 使用ClaudeInputTool向Claude发送"继续"指令
            import asyncio
            logger.info("使用工具管理器向Claude发送继续指令...")
            
            # 默认的继续提示
            continue_message = "请继续，完成剩余的任务。"
            
            # 执行工具调用
            result = asyncio.run(tool_manager.execute_tool("claude_input", {
                "message": continue_message
            }))
            
            if result.success:
                logger.info(f"成功发送继续指令: {result}")
            else:
                logger.warning(f"发送继续指令失败: {result.error}")
                
                # 如果直接输入失败，可以尝试重新调用claude_api
                logger.info("尝试通过API重新发送请求...")
                continue_response = claude_api(
                    continue_message,
                    task_definition=subtask,
                    verbose=self.verbose,
                    timeout=task_timeout,
                    use_gemini=self.use_gemini,
                    conversation_history=conversation_history
                )
                
                if continue_response["status"] == "success":
                    logger.info("重新发送请求成功")
                    # 更新响应以包含新内容
                    response["output"] += "\n\n" + continue_response["output"]
                    if "task_status" in continue_response:
                        response["task_status"] = continue_response["task_status"]
        except Exception as e:
            logger.warning(f"向Claude发送继续指令时出错: {str(e)}")
    
    # 其余代码...
```

## 预期效果

1. 通过引入明确的任务状态判断机制，Gemini会基于任务定义和成功标准对任务完成状态进行准确评估
2. 通过在提示中明确工作目录和路径关系，Claude将能够正确处理文件路径
3. 利用已有的agent_tools包中的工具调用系统，Claude可以更结构化地创建和读取文件，无需重新实现
4. 当不使用Gemini时，系统将默认状态设为"NEEDS_VERIFICATION"并进行文件验证
5. 明确指示Claude不要尝试运行代码，避免进入权限确认对话
6. 系统默认使用Gemini来判断工作是否完成，确保更准确的任务状态评估
7. 当工作未完成时(CONTINUE状态)，系统会自动向Claude发送后续输入，保持交互的连续性

## 实现步骤

1. 修改`claude_cli.py`，在调用Gemini分析器时传递任务定义参数
2. 修改`gemini_analyzer.py`，扩展_build_analyzer_prompt方法以纳入任务定义信息
3. 修改TaskExecutor的_prepare_context_aware_prompt方法，添加明确的工作目录和路径信息
4. 集成agent_tools包中的工具管理器和解析器
5. 实现FileCreationTool作为BaseTool的子类
6. 增强提示词，添加工具调用格式说明和路径要求
7. 扩展execute_subtask方法，支持解析和执行工具调用
8. 根据Gemini分析器返回的状态（CONTINUE、NEEDS_MORE_INFO等），自动调用相应的工具实现任务继续执行

## 注意事项

- 确保工具调用格式与已有的DefaultResponseParser兼容
- 工具调用应放在JSON代码块中，而不是使用自定义格式
- 对每个输出文件路径进行明确的绝对路径处理
- 避免在提示中指示Claude运行文件，只要求创建文件
- 对不使用Gemini时的任务状态验证提供完整的文件检查逻辑
- 默认启用Gemini分析器（use_gemini=True）进行任务状态判断
- 当Gemini分析器返回CONTINUE状态时，需通过ClaudeInputTool向Claude Code发送继续指令
- 实现ClaudeInputTool需与claude_client的实现相匹配，确保能够正确向Claude进程发送输入
- 当直接输入失败时，应提供备选方案（如重新通过API调用）确保任务不会中断
- 工具调用结果应当记录在任务上下文中，便于任务完成状态的验证

这些改进将大幅提高任务执行的可靠性和成功率，解决当前存在的路径混淆和任务状态判断不准确的问题，同时充分利用项目中已有的工具调用机制，无需重复实现。通过默认启用Gemini分析器并配合工具管理器，可以实现更智能的任务状态判断，特别是通过向Claude Code发送继续指令，确保长任务能够顺利完成而无需人工干预。

## 测试计划

为了验证改进的有效性，我们需要进行以下测试：

### 1. 单元测试

#### Gemini分析器测试
```python
def test_gemini_analyzer_with_task_definition():
    """测试Gemini分析器在有任务定义时的行为"""
    from task_planner.vendor.claude_client.agent_tools.gemini_analyzer import GeminiTaskAnalyzer
    
    # 创建分析器实例
    analyzer = GeminiTaskAnalyzer()
    
    # 创建模拟任务定义
    task_definition = {
        "id": "test_task_1",
        "name": "测试任务",
        "description": "这是一个测试任务",
        "output_files": {
            "main_result": "/tmp/test_result.json"
        },
        "success_criteria": ["创建输出文件"]
    }
    
    # 设置任务定义
    analyzer.task_definition = task_definition
    
    # 构建测试对话历史
    conversation_history = [
        ("请创建一个JSON文件", "我将为您创建JSON文件")
    ]
    
    # 模拟响应
    last_response = "我已经创建了文件: /tmp/test_result.json，内容为{...}"
    
    # 分析结果
    result = analyzer.analyze(conversation_history, last_response)
    
    # 验证结果（如果实际调用Gemini，这里会使用mock）
    assert result in ["COMPLETED", "NEEDS_MORE_INFO", "CONTINUE"]
```

#### ClaudeInputTool测试
```python
def test_claude_input_tool():
    """测试Claude输入工具的基本功能"""
    import asyncio
    
    # 注意：这里可能需要mock或stub claude_client模块的send_input_to_claude函数
    
    # 创建工具实例
    class ClaudeInputTool(BaseTool):
        # 实现与代码中相同...
        
    tool = ClaudeInputTool()
    
    # 测试参数验证
    is_valid, error = tool.validate_parameters({"message": "继续"})
    assert is_valid is True
    
    is_valid, error = tool.validate_parameters({})
    assert is_valid is False
    assert "缺少'message'参数" in error
    
    # 测试执行（使用mock）
    async def test_execution():
        result = await tool.execute({"message": "继续"})
        # 如果使用mock，验证mock被正确调用
        assert result.success is True
        
    asyncio.run(test_execution())
```

### 2. 集成测试

#### 任务状态判断测试

```python
def test_task_execution_with_gemini_status():
    """测试使用Gemini进行任务状态判断的执行流程"""
    # 设置测试环境
    from task_planner.core.task_executor import TaskExecutor
    from task_planner.core.context_management import TaskContext
    
    # 创建执行器实例，默认使用Gemini
    executor = TaskExecutor(verbose=True)
    
    # 创建测试任务
    task = {
        "id": "test_integration_1",
        "name": "集成测试任务",
        "instruction": "创建一个简单的测试文件",
        "output_files": {
            "main_result": "/tmp/integration_test.txt"
        }
    }
    
    # 执行任务（这里可能需要mock掉claude_api调用）
    result = executor.execute_subtask(task)
    
    # 验证结果包含预期的字段
    assert "success" in result
    assert "task_id" in result
    assert result["task_id"] == "test_integration_1"
```

#### 自动继续功能测试

```python
def test_continue_on_incomplete_task():
    """测试任务未完成时的自动继续功能"""
    # 使用mock模拟CONTINUE状态和后续调用
    # 使用mock替换claude_api函数
    
    # 设置测试环境
    from unittest.mock import patch, MagicMock
    from task_planner.core.task_executor import TaskExecutor
    
    # 创建模拟的claude_api函数，第一次返回CONTINUE状态，第二次返回COMPLETED
    mock_responses = [
        {
            "status": "success",
            "output": "我开始处理任务...",
            "error_msg": "",
            "task_status": "CONTINUE"
        },
        {
            "status": "success",
            "output": "任务已完成",
            "error_msg": "",
            "task_status": "COMPLETED"
        }
    ]
    
    mock_claude_api = MagicMock(side_effect=mock_responses)
    
    # 使用patch替换真实的claude_api
    with patch('task_planner.core.task_executor.claude_api', mock_claude_api):
        # 创建执行器实例
        executor = TaskExecutor(verbose=True)
        
        # 创建测试任务
        task = {
            "id": "test_continue",
            "name": "自动继续测试",
            "instruction": "创建一个需要多次交互的任务"
        }
        
        # 执行任务
        result = executor.execute_subtask(task)
        
        # 验证claude_api被调用了两次
        assert mock_claude_api.call_count == 2
        
        # 第二次调用是使用"请继续"的消息
        assert "请继续" in mock_claude_api.call_args_list[1][0][0]
        
        # 验证最终结果是成功的
        assert result["success"] is True
```

### 3. 系统测试

#### 长任务自动化测试

```bash
# 创建一个特别复杂的任务，需要多次交互才能完成
python -m task_planner plan --task "创建一个复杂的数据分析系统，包含数据收集、清洗、分析和可视化四个模块，每个模块用独立的Python文件实现，并创建一个主程序文件集成所有功能" --output-dir /tmp/complex_task --verbose

# 检查是否成功完成，并验证所有预期的文件都被创建
ls -la /tmp/complex_task/
```

#### 路径处理测试

```bash
# 测试相对路径和绝对路径的正确处理
python -m task_planner plan --task "创建一个简单的文本处理工具，读取和写入文件" --input-file relative/path/input.txt --output-file /absolute/path/output.txt --verbose

# 验证路径被正确处理，并且文件在正确的位置
```

### 4. 性能和健壮性测试

#### 超时处理测试

```python
def test_timeout_handling():
    """测试超时处理机制"""
    from task_planner.core.task_executor import TaskExecutor
    
    # 创建执行器实例，设置非常短的超时
    executor = TaskExecutor(timeout=1, verbose=True)
    
    # 创建一个复杂任务，确保无法在短时间内完成
    task = {
        "id": "timeout_test",
        "name": "超时测试",
        "instruction": "实现一个完整的机器学习管道，包括数据预处理、特征工程、模型训练和评估" * 10,  # 非常长的指令
    }
    
    # 执行任务
    result = executor.execute_subtask(task)
    
    # 验证结果包含超时信息
    assert result["success"] is False
    assert "timeout" in result.get("error", "").lower() or "超时" in result.get("error", "").lower()
```

#### 错误恢复测试

```python
def test_error_recovery():
    """测试在发生错误时的恢复机制"""
    # 使用mock模拟错误和恢复过程
    # ...
```

### 5. 安全性测试

#### 文件权限测试

```python
def test_file_permission_handling():
    """测试文件权限处理"""
    import os
    import tempfile
    from task_planner.core.task_executor import TaskExecutor
    
    # 创建一个只读目录
    with tempfile.TemporaryDirectory() as temp_dir:
        # 将目录权限设置为只读
        os.chmod(temp_dir, 0o555)
        
        # 创建任务尝试在只读目录写入文件
        task = {
            "id": "permission_test",
            "name": "权限测试",
            "instruction": "创建一个简单的文本文件",
            "output_files": {
                "main_result": os.path.join(temp_dir, "test.txt")
            }
        }
        
        # 执行任务
        executor = TaskExecutor(verbose=True)
        result = executor.execute_subtask(task)
        
        # 验证任务失败，包含权限错误信息
        assert result["success"] is False
        assert "permission" in result.get("error", "").lower() or "权限" in result.get("error", "").lower()
```

通过这些测试，我们可以确保改进的功能按预期工作，特别是任务状态判断和自动继续功能。测试覆盖了单元测试、集成测试、系统测试、性能测试和安全测试等多个层面，确保系统的稳定性和可靠性。

## 测试执行计划

### 1. 准备测试环境

```bash
# 创建测试环境
python -m venv test_env
source test_env/bin/activate

# 安装依赖
pip install -e .
pip install pytest pytest-mock pytest-asyncio pytest-cov

# 准备测试目录
mkdir -p tests/test_v3
```

### 2. 编写测试用例

将上述测试用例组织到以下文件中：

```
tests/test_v3/
├── test_gemini_analyzer.py  # Gemini分析器测试
├── test_claude_input_tool.py  # Claude输入工具测试
├── test_task_executor.py  # 任务执行器集成测试
├── test_continue_feature.py  # 自动继续功能测试
├── test_path_handling.py  # 路径处理测试
└── conftest.py  # 测试公共设置和fixture
```

### 3. 具体测试用例集

#### 测试用例1：任务完成状态判断

| 测试ID | 测试场景 | 前置条件 | 测试步骤 | 预期结果 |
|--------|---------|----------|----------|----------|
| TD-001 | 任务完成判断-完整输出 | 设置任务定义和输出文件要求 | 1. 创建模拟Claude响应，包含所有要求的输出文件<br>2. 使用Gemini分析响应 | 返回COMPLETED状态 |
| TD-002 | 任务完成判断-部分输出 | 设置任务定义和输出文件要求 | 1. 创建模拟Claude响应，仅包含部分要求的输出文件<br>2. 使用Gemini分析响应 | 返回CONTINUE状态 |
| TD-003 | 任务完成判断-需要更多信息 | 设置任务定义 | 1. 创建模拟Claude响应，包含对更多信息的请求<br>2. 使用Gemini分析响应 | 返回NEEDS_MORE_INFO状态 |

#### 测试用例2：自动继续功能

| 测试ID | 测试场景 | 前置条件 | 测试步骤 | 预期结果 |
|--------|---------|----------|----------|----------|
| AC-001 | 任务自动继续-成功 | 1. 设置任务定义<br>2. 模拟Claude响应CONTINUE状态 | 1. 执行任务<br>2. 触发继续功能<br>3. 模拟第二次响应完成 | 1. Claude输入工具被调用<br>2. 最终结果成功完成 |
| AC-002 | 任务自动继续-备选方案 | 1. 设置任务定义<br>2. 模拟直接输入失败 | 1. 执行任务<br>2. 触发继续功能<br>3. 直接输入失败<br>4. 触发备选方案 | 1. 备选方案被调用<br>2. 通过API重新发送请求<br>3. 任务最终完成 |
| AC-003 | 多次继续测试 | 设置需要多次交互的复杂任务 | 1. 执行任务<br>2. 模拟多次CONTINUE状态<br>3. 最终返回COMPLETED | 自动继续功能被多次触发，任务最终完成 |

#### 测试用例3：路径处理

| 测试ID | 测试场景 | 前置条件 | 测试步骤 | 预期结果 |
|--------|---------|----------|----------|----------|
| PH-001 | 相对路径转换 | 设置任务定义，使用相对路径 | 1. 执行任务<br>2. 检查路径处理 | 相对路径被正确转换为绝对路径 |
| PH-002 | 绝对路径保留 | 设置任务定义，使用绝对路径 | 1. 执行任务<br>2. 检查路径处理 | 绝对路径保持不变 |
| PH-003 | 上下文路径合并 | 设置上下文目录和相对路径 | 1. 执行任务<br>2. 检查路径处理 | 相对路径正确与上下文路径合并 |

### 4. 测试执行

```bash
# 运行单元测试
pytest tests/test_v3/test_gemini_analyzer.py tests/test_v3/test_claude_input_tool.py -v

# 运行集成测试
pytest tests/test_v3/test_task_executor.py tests/test_v3/test_continue_feature.py -v

# 运行所有测试并生成覆盖率报告
pytest tests/test_v3/ --cov=task_planner.core --cov=task_planner.util --cov=task_planner.vendor.claude_client.agent_tools --cov-report=html
```

### 5. 确认验收标准

实现被视为成功需要满足以下标准：

1. 所有单元测试通过
2. 所有集成测试通过
3. 关键功能的代码覆盖率达到80%以上
4. 长时间运行的任务能够自动继续，无需人工干预
5. 所有文件路径处理正确
6. Gemini分析器能够根据任务定义准确判断任务完成状态