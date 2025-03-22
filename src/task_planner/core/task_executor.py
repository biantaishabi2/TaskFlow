#!/usr/bin/env python3
"""
任务拆分与执行系统 - 任务执行模块
实现内层循环(执行者)功能，负责执行具体的小任务
"""

import json
import re
import time
import logging
import os
import sys
from datetime import datetime
from task_planner.util.claude_cli import claude_api
from task_planner.core.context_management import TaskContext

# 尝试导入Gemini分析器
# 注释掉claude_client导入，因为不再使用该功能
# try:
#     # 首先尝试从项目内部vendor目录导入
#     from task_planner.vendor.claude_client.agent_tools.gemini_analyzer import GeminiTaskAnalyzer
#     GEMINI_AVAILABLE = True
# except ImportError:
#     try:
#         # 备选：外部依赖路径
#         sys.path.insert(0, '/home/wangbo/document/wangbo/claude_client')
#         from agent_tools.gemini_analyzer import GeminiTaskAnalyzer
#         GEMINI_AVAILABLE = True
#     except ImportError:
#         GEMINI_AVAILABLE = False
GEMINI_AVAILABLE = False  # 直接设置为False，不再尝试导入

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('task_executor')

class TaskExecutor:
    """任务执行者类，负责执行规划者分配的具体小任务"""
    
    def __init__(self, context_manager=None, timeout=500, verbose=False, use_gemini=True):
        """
        初始化任务执行者
        
        参数:
            context_manager (ContextManager, optional): 上下文管理器实例
            timeout (int): Claude命令执行超时时间(秒)
            verbose (bool): 是否打印详细日志
            use_gemini (bool): 是否使用Gemini来判断任务完成状态，默认为True
        """
        self.context_manager = context_manager
        self.timeout = timeout
        self.verbose = verbose
        self.use_gemini = use_gemini
        
        # 检查是否可以使用Gemini
        if self.use_gemini and not GEMINI_AVAILABLE:
            logger.warning("请求使用Gemini进行任务分析，但未能导入相关模块，将使用默认分析方法")
            self.use_gemini = False
        elif self.use_gemini:
            logger.info("已启用Gemini任务完成状态分析")
            
        logger.info("任务执行者已初始化")
        
    def _run_async_tool(self, coro):
        """
        运行异步工具（可用于测试替换）
        
        参数:
            coro: 异步协程对象
            
        返回:
            运行结果
        """
        import asyncio
        return asyncio.run(coro)
        
    def execute_subtask(self, subtask, task_context=None):
        """
        执行子任务
        
        参数:
            subtask (dict): 子任务定义
            task_context (TaskContext, optional): 任务上下文
            
        返回:
            dict: 执行结果
        """
        subtask_id = subtask['id']
        logger.info(f"开始执行子任务: {subtask.get('name', subtask_id)} (任务ID: {subtask_id})")
        
        # 获取任务上下文
        if self.context_manager and subtask_id in self.context_manager.task_contexts:
            task_context = self.context_manager.task_contexts[subtask_id]
        elif not task_context:
            # 如果未提供上下文，创建新上下文
            task_context = TaskContext(subtask_id)
            
        # 确保任务输出目录存在
        if 'output_files' in subtask and isinstance(subtask['output_files'], dict):
            for output_type, output_path in subtask['output_files'].items():
                if not output_path:
                    continue
                    
                try:
                    # 如果是相对路径，使用上下文目录作为基础
                    if not os.path.isabs(output_path) and self.context_manager and self.context_manager.context_dir:
                        full_path = os.path.join(self.context_manager.context_dir, output_path)
                    else:
                        full_path = output_path
                        
                    # 确保目录存在
                    directory = os.path.dirname(full_path)
                    if not os.path.exists(directory):
                        os.makedirs(directory, exist_ok=True)
                        logger.info(f"为子任务 {subtask_id} 创建输出目录: {directory}")
                except Exception as e:
                    logger.warning(f"创建输出目录时出错: {str(e)}")
            
        # 记录执行开始
        task_context.add_execution_record(
            'execution_started',
            f"开始执行任务: {subtask.get('name', subtask_id)}",
            {'task_id': subtask_id, 'start_time': datetime.now().isoformat()}
        )
        
        # 构建提示，包含上下文信息
        prompt = self._prepare_context_aware_prompt(subtask, task_context)
        
        # 导入已有的工具管理器和解析器
        try:
            from task_planner.vendor.claude_client.agent_tools.tool_manager import ToolManager
            from task_planner.vendor.claude_client.agent_tools.parser import DefaultResponseParser
            from task_planner.core.tools import ClaudeInputTool
            
            # 注册工具
            tool_manager = ToolManager()
            tool_manager.register_tool("claude_input", ClaudeInputTool())
            
            # 创建响应解析器
            response_parser = DefaultResponseParser()
            
            has_agent_tools = True
        except ImportError:
            logger.warning("无法导入agent_tools包，将使用基础功能")
            has_agent_tools = False
            
        # 提取任务执行参数
        task_timeout = subtask.get('timeout', self.timeout)
        
        # 执行Claude命令
        try:
            logger.info(f"启动Claude任务 (超时: {task_timeout}秒)")
            
            # 获取之前的对话历史（如果有）
            conversation_history = task_context.local_context.get('conversation_history', None)
            
            # 使用claude_cli直接执行，根据设置决定是否使用Gemini
            response = claude_api(
                prompt,
                task_definition=subtask,  # 传入完整任务定义
                verbose=self.verbose,
                timeout=task_timeout,
                use_gemini=self.use_gemini,
                conversation_history=conversation_history
            )
            
            # 保存或更新对话历史
            if self.use_gemini and 'conversation_history' in response:
                task_context.update_local('conversation_history', response['conversation_history'])
            
            # 如果启用了工具调用，解析和执行工具调用
            if has_agent_tools:
                try:
                    # 解析响应，提取工具调用
                    parsed_response = response_parser.parse(response["output"])
                    
                    # 执行工具调用（如果有）
                    if parsed_response.tool_calls:
                        import asyncio
                        tool_results = []
                        
                        for tool_call in parsed_response.tool_calls:
                            tool_name = tool_call.get("tool_name")
                            params = tool_call.get("parameters", {})
                            
                            # 执行工具调用
                            result = asyncio.run(tool_manager.execute_tool(tool_name, params))
                            tool_results.append({
                                "tool_name": tool_name,
                                "params": params,
                                "result": result
                            })
                        
                        # 将工具执行结果添加到上下文
                        task_context.update_local('tool_results', tool_results)
                        logger.info(f"执行了 {len(tool_results)} 个工具调用")
                except Exception as e:
                    logger.warning(f"解析或执行工具调用时出错: {str(e)}")
                
            # 构建交互记录
            interactions = [
                {"role": "user", "content": prompt, "timestamp": datetime.now().isoformat()},
                {"role": "claude", "content": response["output"], "timestamp": datetime.now().isoformat()}
            ]
            
            # 记录任务状态分析结果
            if 'task_status' in response:
                task_status = response['task_status']
                logger.info(f"任务状态分析: {task_status}")
                task_context.update_local('task_status', task_status)
                
                # 根据不同任务状态进行处理
                if task_status == "CONTINUE":
                    # 任务未完成，需要继续执行
                    logger.info("任务未完成，需要继续执行")
                    
                    # 如果有工具管理器，使用相应工具继续任务
                    if has_agent_tools:
                        try:
                            # 使用ClaudeInputTool向Claude发送"继续"指令
                            import asyncio
                            logger.info("使用工具管理器向Claude发送继续指令...")
                            
                            # 默认的继续提示
                            continue_message = "请继续，完成剩余的任务。"
                            
                            # 执行工具调用
                            result = self._run_async_tool(tool_manager.execute_tool("claude_input", {
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
                                    conversation_history=task_context.local_context.get('conversation_history', None)
                                )
                                
                                if continue_response["status"] == "success":
                                    logger.info("重新发送请求成功")
                                    # 更新响应以包含新内容
                                    response["output"] += "\n\n" + continue_response["output"]
                                    if "task_status" in continue_response:
                                        response["task_status"] = continue_response["task_status"]
                            
                            # 记录继续执行的状态
                            task_context.add_execution_record(
                                'task_continued',
                                "任务未完成，系统已发送继续指令",
                                {'continued_at': datetime.now().isoformat()}
                            )
                        except Exception as e:
                            logger.warning(f"向Claude发送继续指令时出错: {str(e)}")
                    
                elif task_status == "NEEDS_MORE_INFO":
                    # 需要更多信息，记录状态
                    logger.info("任务需要更多信息才能继续")
                    task_context.add_execution_record(
                        'needs_more_info',
                        "任务需要更多用户信息才能继续",
                        {'requested_at': datetime.now().isoformat()}
                    )
                
                elif task_status == "NEEDS_VERIFICATION":
                    # 验证所有预期的输出文件是否已经被创建
                    missing_files = self._verify_output_files(subtask)
                    
                    if missing_files:
                        # 文件缺失，修改状态为错误
                        task_status = "ERROR"
                        error_msg = f"任务执行失败：AI未能创建预期的输出文件。缺失的文件：\n" + "\n".join(missing_files)
                        logger.error(error_msg)
                        response['task_status'] = task_status
                        task_context.update_local('task_status', task_status)
                    else:
                        # 所有文件都存在，修改状态为完成
                        task_status = "COMPLETED"
                        logger.info("通过文件验证，任务状态更新为COMPLETED")
                        response['task_status'] = task_status
                        task_context.update_local('task_status', task_status)
            
            # 记录交互完成
            execution_status = response["status"]
            if execution_status == "success":
                task_context.add_execution_record(
                    'claude_execution_completed',
                    f"Claude执行完成",
                    {'execution_status': execution_status}
                )
            else:
                task_context.add_execution_record(
                    'claude_execution_failed',
                    f"Claude执行失败: {response.get('error_msg', '未知错误')}",
                    {'execution_status': execution_status, 'error': response.get('error_msg')}
                )
            
            # 存储原始响应
            task_context.update_local('claude_response', response)
            
            # 处理执行结果
            basic_result = self._process_direct_result(response, subtask, task_context)
            
            # 添加任务ID
            if 'task_id' not in basic_result:
                basic_result['task_id'] = subtask_id
                
            # 不再从AI响应中提取工件，完全依赖AI直接创建文件
            
            # 检查是否需要生成结果文件
            if 'output_files' in subtask and 'main_result' in subtask['output_files']:
                result_file_path = subtask['output_files']['main_result']
                
                # 确保路径是绝对路径
                if not os.path.isabs(result_file_path) and self.context_manager and self.context_manager.context_dir:
                    result_file_path = os.path.join(self.context_manager.context_dir, result_file_path)
                    
                # 检查是否已经在任务状态验证中判定为错误
                if 'task_status' in response and response['task_status'] == "ERROR":
                    error_msg = f"任务执行失败：AI未能创建预期的输出文件"
                    logger.error(error_msg)
                    return {
                        "success": False,
                        "error": error_msg,
                        "task_id": subtask.get("id", "unknown"),
                        "result": {"details": error_msg}
                    }
                
                # 添加结果文件引用
                task_context.add_file_reference(
                    'output_main_result',
                    result_file_path,
                    {'type': 'output_file', 'output_type': 'main_result'}
                )
                
                # 更新基本结果，添加文件路径信息
                basic_result['result_file'] = result_file_path
            
            # 记录执行成功
            success = basic_result.get('success', False)
            status = "成功" if success else "失败"
            task_context.add_execution_record(
                'execution_completed',
                f"任务执行{status}",
                {'success': success, 'completion_time': datetime.now().isoformat()}
            )
            logger.info(f"子任务 {subtask_id} 执行{status}")
            
            return basic_result
            
        except Exception as e:
            # 记录执行异常
            error_msg = str(e)
            logger.error(f"执行子任务 {subtask_id} 时发生错误: {error_msg}")
            task_context.add_execution_record(
                'execution_error',
                f"任务执行出错: {error_msg}",
                {'error': error_msg, 'error_time': datetime.now().isoformat()}
            )
            
            # 记录错误但不创建占位文件，让上层任务规划者能够明确知道任务失败
            logger.error(f"子任务 {subtask_id} 执行失败，错误: {error_msg}")
            
            # 添加详细的错误信息到文件（但不是占位符JSON，而是错误日志）
            try:
                if self.context_manager and self.context_manager.context_dir:
                    log_dir = os.path.join(self.context_manager.context_dir, "logs")
                    os.makedirs(log_dir, exist_ok=True)
                    error_log_path = os.path.join(log_dir, f"error_{subtask_id}.log")
                    
                    with open(error_log_path, 'w', encoding='utf-8') as f:
                        f.write(f"执行时间: {datetime.now().isoformat()}\n")
                        f.write(f"任务ID: {subtask_id}\n")
                        f.write(f"错误信息: {error_msg}\n")
                        f.write("详细堆栈:\n")
                        import traceback
                        f.write(traceback.format_exc())
                    
                    # 添加错误日志文件引用，但不作为正常输出文件
                    if self.context_manager and subtask_id in self.context_manager.task_contexts:
                        self.context_manager.task_contexts[subtask_id].add_file_reference(
                            'error_log',
                            error_log_path,
                            {'type': 'error_log'}
                        )
                        
                    logger.info(f"错误详情已记录到: {error_log_path}")
            except Exception as e2:
                logger.warning(f"创建错误日志文件时出错: {str(e2)}")
            
            # 返回错误结果
            return {
                'task_id': subtask_id,
                'success': False,
                'error': error_msg,
                'result': {
                    'summary': f"任务执行失败: {error_msg}",
                    'details': f"执行子任务 {subtask_id} 时发生错误"
                }
            }
    
    def _prepare_context_aware_prompt(self, subtask, task_context):
        """
        构建包含上下文信息的提示
        
        参数:
            subtask (dict): 子任务定义
            task_context (TaskContext): 任务上下文
            
        返回:
            str: 包含上下文的提示
        """
        # 提取基本任务信息
        task_id = subtask['id']
        task_name = subtask.get('name', task_id)
        instruction = subtask.get('instruction', '')
        
        # 添加当前工作目录信息
        current_working_dir = os.getcwd()
        context_dir = self.context_manager.context_dir if self.context_manager else "output/logs/subtasks_execution"
        
        # 添加任务目标和背景
        prompt_parts = [
            f"# 任务：{task_name}",
            instruction,
            f"\n## 环境信息",
            f"当前工作目录: {current_working_dir}",
            f"上下文目录: {context_dir}",
        ]
        
        # 添加文件路径和结果要求
        prompt_parts.append("\n## 文件路径和结果要求")
        
        # 添加输出文件路径
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
                
                if output_type == 'main_result':
                    prompt_parts.append(f"- 主要结果: {output_path}")
                else:
                    prompt_parts.append(f"- {output_type}: {output_path}")
            
            # 创建工件目录提示
            if task_context.base_dir:
                # 确保是绝对路径
                base_dir = task_context.base_dir
                if not os.path.isabs(base_dir):
                    base_dir = os.path.join(current_working_dir, base_dir)
                prompt_parts.append(f"- 其他工件: {base_dir}/")
                
            # 增强提示，更强调文件创建与路径重要性
            prompt_parts.append("\n## 重要提示 - 文件创建：")
            prompt_parts.append("1. 你必须实际创建上述所有文件，必须使用完整的绝对路径")
            prompt_parts.append("2. 不要尝试使用相对路径，必须使用指定的完整绝对路径")
            prompt_parts.append("3. 当导入其他文件时，请使用它们的正确绝对路径或相对路径")
            prompt_parts.append("4. 不要尝试运行代码或执行其他文件，只需创建所需文件")
            prompt_parts.append("5. 任务的成功完全取决于这些文件是否被成功创建在指定的绝对路径位置")
            prompt_parts.append("6. 系统会严格验证每个列出的文件是否在指定的路径上实际存在")
            
            # 添加强调输出文件的检查清单
            prompt_parts.append("\n## 关键输出文件检查清单：")
            if 'output_files' in subtask and subtask['output_files']:
                for output_type, output_path in subtask['output_files'].items():
                    prompt_parts.append(f"- {output_type}: {output_path}")
                
                # 特别强调main_result文件的格式要求
                if 'main_result' in subtask['output_files']:
                    main_result_path = subtask['output_files']['main_result']
                    prompt_parts.append(f"\n特别注意：'{main_result_path}'是验证任务成功的关键文件，必须创建并符合以下JSON格式:")
                    prompt_parts.append("```json")
                    prompt_parts.append("{")
                    prompt_parts.append(f'  "task_id": "{subtask["id"]}",')
                    prompt_parts.append('  "status": "completed",')
                    prompt_parts.append('  "success": true,')
                    prompt_parts.append('  "result": {')
                    prompt_parts.append('    // 任务相关的具体结果')
                    prompt_parts.append('  },')
                    prompt_parts.append('  "summary": "简要描述任务执行结果和生成的文件"')
                    prompt_parts.append("}")
                    prompt_parts.append("```")
            
            prompt_parts.append("\n## 任务完成前的必要检查：")
            prompt_parts.append("1. 我是否已创建所有'output_files'中列出的文件，特别是main_result文件？")
            prompt_parts.append("2. main_result文件是否包含正确格式的JSON？")
            prompt_parts.append("3. 我创建的所有文件是否都在正确的绝对路径位置？")
            prompt_parts.append("4. 在任务结束前检查：缺少任何预期的输出文件将导致任务失败！")
            prompt_parts.append("5. 在回复中，请明确列出你已创建的每个文件的完整绝对路径")
            prompt_parts.append("6. 如果无法创建任何文件，请明确指出并解释原因")
            prompt_parts.append("7. 占位文件或空文件不会被视为有效的输出")
                
            # 添加结果JSON格式要求
            prompt_parts.append("""
结果JSON必须包含以下字段：
- task_id：任务ID
- success：表示任务是否成功完成
- result：包含summary和details
- artifacts：所有生成文件的路径列表
- next_steps（可选）：建议的后续步骤""")
        
        # 添加任务上下文信息
        if 'progress' in task_context.local_context:
            progress = task_context.local_context['progress']
            prompt_parts.append(
                f"\n## 任务进度\n"
                f"当前任务: {progress.get('current_index', 0) + 1}/{progress.get('total_tasks', 1)}\n"
                f"已完成任务: {len(progress.get('completed_tasks', []))}"
            )
        
        # 添加前置任务的文件引用
        dependency_files = []
        
        # 从input_files_mapping获取文件映射
        if 'input_files_mapping' in subtask and isinstance(subtask['input_files_mapping'], dict):
            prompt_parts.append("\n## 输入文件")
            for input_key, file_path in subtask['input_files_mapping'].items():
                prompt_parts.append(f"- {input_key}: {file_path}")
                dependency_files.append(file_path)
                
        # 从依赖文件中获取文件映射
        elif 'dependency_files' in task_context.local_context:
            prompt_parts.append("\n## 前置任务结果文件")
            for dep_id, files in task_context.local_context['dependency_files'].items():
                if isinstance(files, dict):
                    for file_key, file_path in files.items():
                        prompt_parts.append(f"- {dep_id} ({file_key}): {file_path}")
                        dependency_files.append(file_path)
        
        # 添加依赖文件内容提示
        if dependency_files:
            prompt_parts.append("\n你可以读取上述文件来获取必要的输入数据。")
            
            # 对于较小的JSON文件，可以将部分内容包含在提示中
            for file_path in dependency_files:
                if file_path.endswith('.json') and os.path.exists(file_path):
                    try:
                        file_size = os.path.getsize(file_path)
                        if file_size < 10000:  # 只包含小文件内容
                            with open(file_path, 'r', encoding='utf-8') as f:
                                file_content = f.read()
                                
                            # 添加文件内容预览
                            prompt_parts.append(f"\n### 文件内容预览: {os.path.basename(file_path)}")
                            prompt_parts.append(f"```json\n{file_content}\n```")
                    except Exception as e:
                        # 忽略读取错误
                        pass
        
        # 添加成功标准
        if 'success_criteria' in subtask and isinstance(subtask['success_criteria'], list):
            prompt_parts.append("\n## 成功标准")
            prompt_parts.append("任务被视为成功需要满足：")
            for criteria in subtask['success_criteria']:
                prompt_parts.append(f"- {criteria}")
        
        # 合并所有部分
        return "\n\n".join(prompt_parts)
    
    def _prepare_claude_task_context(self, subtask, task_context):
        """
        准备Claude任务上下文
        
        参数:
            subtask (dict): 子任务定义
            task_context (TaskContext): 任务上下文
            
        返回:
            dict: Claude任务上下文
        """
        # 创建基本任务上下文
        claude_context = {
            "task_id": subtask['id'],
            "task_type": subtask.get('type', 'general'),
            "context": {}
        }
        
        # 添加任务定义信息
        claude_context["context"]["task_definition"] = {
            "name": subtask.get('name', subtask['id']),
            "description": subtask.get('description', ''),
            "expected_output": subtask.get('expected_output', '')
        }
        
        # 添加进度信息
        if 'progress' in task_context.local_context:
            claude_context["context"]["progress"] = task_context.local_context['progress']
        
        # 添加依赖任务的摘要信息
        if 'dependency_results' in task_context.local_context:
            dependency_summaries = {}
            for dep_id, dep_result in task_context.local_context['dependency_results'].items():
                dependency_summaries[dep_id] = {
                    "success": dep_result.get('success', False),
                    "summary": dep_result.get('result', {}).get('summary', '')
                }
            claude_context["context"]["dependency_summaries"] = dependency_summaries
        
        # 添加工件引用
        artifacts_refs = {}
        for name, artifact in task_context.artifacts.items():
            # 只添加工件的引用和元数据，不包含完整内容
            artifacts_refs[name] = {
                "type": artifact['metadata'].get('type', 'unknown'),
                "created_at": artifact['created_at'],
                "metadata": artifact['metadata']
            }
        claude_context["artifacts"] = artifacts_refs
        
        return claude_context
    
    def _process_direct_result(self, response, subtask, task_context):
        """
        处理直接执行结果，提取关键信息
        
        参数:
            response (dict): Claude CLI的响应
            subtask (dict): 子任务定义
            task_context (TaskContext): 任务上下文
            
        返回:
            dict: 结构化结果
        """
        # 首先检查执行状态
        if response["status"] != "success":
            # 如果执行失败，返回错误结果
            return {
                "task_id": subtask["id"],
                "success": False,
                "error": response.get("error_msg", "执行失败"),
                "result": {
                    "summary": f"执行失败: {response.get('error_msg', '未知错误')}",
                    "details": response.get("output", "")
                }
            }
            
        # 尝试从输出中提取JSON结果
        output = response["output"]
        result = None
        
        # 尝试提取JSON块
        json_blocks = re.findall(r'```json\s*(.*?)\s*```', output, re.DOTALL)
        
        if json_blocks:
            try:
                # 使用最后一个JSON块
                result = json.loads(json_blocks[-1])
                logger.info(f"从Claude输出提取到JSON结果")
            except json.JSONDecodeError:
                logger.warning(f"无法解析从Claude输出提取的JSON")
                        
        # 如果仍然没有有效结果，构建一个基本结果
        if not result:
            logger.warning(f"未能提取结构化结果，使用启发式方法构建结果")
            result = self._create_heuristic_result_from_text(output, subtask)
        
        # 验证结果是否满足期望
        result = self._verify_and_normalize_result(result, subtask)
        
        # 更新任务上下文
        task_context.update_local('result', result)
        task_context.update_local('success', result.get('success', False))
        if 'result' in result and 'summary' in result['result']:
            task_context.update_local('summary', result['result']['summary'])
        
        return result
    
    def _create_heuristic_result_from_text(self, text, subtask):
        """
        使用启发式方法从文本构建结果
        
        参数:
            text (str): Claude输出文本
            subtask (dict): 子任务定义
            
        返回:
            dict: 构建的结果
        """
        # 检查文本是否为空
        if not text:
            return {
                'task_id': subtask['id'],
                'success': False,
                'result': {
                    'summary': '任务执行失败，没有Claude响应',
                    'details': '未能从Claude获取有效输出'
                }
            }
            
        last_output = text
        
        # 提取代码块
        code_blocks = re.findall(r'```(\w*)\n(.*?)```', last_output, re.DOTALL)
        artifacts = {}
        for i, (lang, code) in enumerate(code_blocks):
            artifact_name = f"code_block_{i+1}"
            if lang:
                artifact_name = f"{lang}_code_{i+1}"
            artifacts[artifact_name] = code.strip()
        
        # 尝试判断是否成功
        success_indicators = ['成功', '完成', 'success', 'done', 'completed']
        failure_indicators = ['失败', '错误', 'error', 'fail', 'failed', 'failure']
        
        success = any(indicator in last_output.lower() for indicator in success_indicators)
        failure = any(indicator in last_output.lower() for indicator in failure_indicators)
        
        # 如果有明确的失败指示，则标记为失败
        if failure and not success:
            success = False
        # 如果有明确的成功指示，或者没有明确的失败指示，则标记为成功
        elif success or not failure:
            success = True
        else:
            success = False
            
        # 提取前几句作为摘要
        lines = [line for line in last_output.split('\n') if line.strip()]
        summary_lines = []
        total_chars = 0
        for line in lines:
            if total_chars < 200 and not line.startswith('```'):
                summary_lines.append(line)
                total_chars += len(line)
            if total_chars >= 200:
                break
                
        summary = ' '.join(summary_lines)
        if len(summary) > 200:
            summary = summary[:197] + '...'
            
        # 构建结果
        return {
            'task_id': subtask['id'],
            'success': success,
            'result': {
                'summary': summary,
                'details': last_output[:2000] + ('...' if len(last_output) > 2000 else '')
            },
            'artifacts': artifacts
        }
    
    def _verify_and_normalize_result(self, result, subtask):
        """
        验证并规范化结果
        
        参数:
            result (dict): 原始结果
            subtask (dict): 子任务定义
            
        返回:
            dict: 验证和规范化后的结果
        """
        # 确保结果有基本结构
        normalized = {'task_id': subtask['id']}
        
        # 复制success字段
        normalized['success'] = result.get('success', False)
        
        # 规范化result部分
        if 'result' in result and isinstance(result['result'], dict):
            normalized['result'] = result['result']
        else:
            # 创建result部分
            normalized['result'] = {
                'summary': result.get('summary', '任务执行完成'),
                'details': result.get('details', '')
            }
            
        # 确保result有summary和details
        if 'summary' not in normalized['result']:
            normalized['result']['summary'] = '任务执行完成'
        if 'details' not in normalized['result']:
            normalized['result']['details'] = ''
            
        # 复制artifacts
        if 'artifacts' in result and isinstance(result['artifacts'], dict):
            normalized['artifacts'] = result['artifacts']
        else:
            normalized['artifacts'] = {}
            
        # 复制next_steps
        if 'next_steps' in result and isinstance(result['next_steps'], list):
            normalized['next_steps'] = result['next_steps']
            
        # 如果有错误，添加到结果
        if 'error' in result:
            normalized['error'] = result['error']
            
        # 获取任务期望的输出字段
        expected_fields = subtask.get('expected_output_fields', [])
        
        # 验证是否包含所有期望的字段
        missing_fields = []
        for field in expected_fields:
            # 检查字段是否存在于结果的任何级别
            if field not in normalized and field not in normalized.get('result', {}) and field not in normalized.get('artifacts', {}):
                missing_fields.append(field)
                
        # 如果缺少关键字段，记录警告
        if missing_fields:
            logger.warning(f"结果缺少期望的字段: {', '.join(missing_fields)}")
            if 'validation_notes' not in normalized:
                normalized['validation_notes'] = []
            normalized['validation_notes'].append(f"缺少期望的字段: {', '.join(missing_fields)}")
            
        return normalized
    
    # _extract_and_store_artifacts_from_text 方法已移除
    # 重构v2: 不再从AI响应中提取工件，完全依赖AI直接创建文件
    
    def _lang_to_extension(self, lang):
        """将语言名称转换为文件扩展名"""
        extension_map = {
            'python': '.py',
            'py': '.py',
            'javascript': '.js',
            'js': '.js',
            'typescript': '.ts',
            'ts': '.ts',
            'java': '.java',
            'c': '.c',
            'cpp': '.cpp',
            'cs': '.cs',
            'go': '.go',
            'rust': '.rs',
            'ruby': '.rb',
            'php': '.php',
            'swift': '.swift',
            'kotlin': '.kt',
            'scala': '.scala',
            'r': '.r',
            'shell': '.sh',
            'bash': '.sh',
            'sql': '.sql',
            'html': '.html',
            'css': '.css',
            'xml': '.xml',
            'json': '.json',
            'yaml': '.yaml',
            'yml': '.yml',
            'markdown': '.md',
            'md': '.md',
            'text': '.txt'
        }
        
        return extension_map.get(lang.lower(), '.txt')
    
    def _verify_output_files(self, subtask):
        """
        验证所有预期的输出文件是否已经被创建
        
        参数:
            subtask (dict): 子任务定义
            
        返回:
            list: 缺失的文件路径列表
        """
        missing_files = []
        if 'output_files' in subtask and isinstance(subtask['output_files'], dict):
            for output_type, output_path in subtask['output_files'].items():
                # 如果是相对路径，转换为绝对路径
                if not os.path.isabs(output_path) and self.context_manager and self.context_manager.context_dir:
                    output_path = os.path.join(self.context_manager.context_dir, output_path)
                
                # 记录文件验证
                logger.info(f"验证输出文件是否存在: {output_path}")
                    
                if not os.path.exists(output_path):
                    missing_files.append(f"{output_type}: {output_path}")
        
        return missing_files
        
    def _determine_file_type(self, file_path):
        """根据文件扩展名判断文件类型"""
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext in ['.py', '.js', '.ts', '.java', '.c', '.cpp', '.cs', '.go', '.rs', '.rb', '.php', '.swift', '.kt']:
            return 'code_file'
        elif ext in ['.json', '.yaml', '.yml', '.xml']:
            return 'data_file'
        elif ext in ['.md', '.txt', '.rst']:
            return 'text_file'
        elif ext in ['.html', '.css']:
            return 'web_file'
        elif ext in ['.png', '.jpg', '.jpeg', '.gif', '.svg']:
            return 'image_file'
        else:
            return 'unknown_file'