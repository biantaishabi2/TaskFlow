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
from datetime import datetime
from claude_cli import claude_api
from context_management import TaskContext

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('task_executor')

class TaskExecutor:
    """任务执行者类，负责执行规划者分配的具体小任务"""
    
    def __init__(self, context_manager=None, timeout=300, verbose=False):
        """
        初始化任务执行者
        
        参数:
            context_manager (ContextManager, optional): 上下文管理器实例
            timeout (int): Claude命令执行超时时间(秒)
            verbose (bool): 是否打印详细日志
        """
        self.context_manager = context_manager
        self.timeout = timeout
        self.verbose = verbose
        logger.info("任务执行者已初始化")
        
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
            
        # 记录执行开始
        task_context.add_execution_record(
            'execution_started',
            f"开始执行任务: {subtask.get('name', subtask_id)}",
            {'task_id': subtask_id, 'start_time': datetime.now().isoformat()}
        )
        
        # 构建提示，包含上下文信息
        prompt = self._prepare_context_aware_prompt(subtask, task_context)
        
        # 提取任务执行参数
        task_timeout = subtask.get('timeout', self.timeout)
        
        # 执行Claude命令
        try:
            logger.info(f"启动Claude任务 (超时: {task_timeout}秒)")
            
            # 使用claude_cli直接执行
            response = claude_api(
                prompt,
                verbose=self.verbose,
                timeout=task_timeout
            )
            
            # 构建模拟的交互记录
            interactions = [
                {"role": "user", "content": prompt, "timestamp": datetime.now().isoformat()},
                {"role": "claude", "content": response["output"], "timestamp": datetime.now().isoformat()}
            ]
            
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
            result = self._process_direct_result(response, subtask, task_context)
            
            # 添加任务ID
            if 'task_id' not in result:
                result['task_id'] = subtask_id
                
            # 提取并存储任务工件
            self._extract_and_store_artifacts_from_text(response["output"], subtask, task_context)
            
            # 记录执行成功
            success = result.get('success', False)
            status = "成功" if success else "失败"
            task_context.add_execution_record(
                'execution_completed',
                f"任务执行{status}",
                {'success': success, 'completion_time': datetime.now().isoformat()}
            )
            logger.info(f"子任务 {subtask_id} 执行{status}")
            
            return result
            
        except Exception as e:
            # 记录执行异常
            error_msg = str(e)
            logger.error(f"执行子任务 {subtask_id} 时发生错误: {error_msg}")
            task_context.add_execution_record(
                'execution_error',
                f"任务执行出错: {error_msg}",
                {'error': error_msg, 'error_time': datetime.now().isoformat()}
            )
            
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
        
        # 添加任务目标和背景
        prompt_parts = [
            f"# 任务: {task_name}",
            instruction
        ]
        
        # 添加任务上下文信息
        if 'progress' in task_context.local_context:
            progress = task_context.local_context['progress']
            prompt_parts.append(
                f"\n## 任务进度\n"
                f"当前任务: {progress.get('current_index', 0) + 1}/{progress.get('total_tasks', 1)}\n"
                f"已完成任务: {len(progress.get('completed_tasks', []))}"
            )
        
        # 添加依赖任务的结果
        if 'dependencies' in subtask and 'dependency_results' in task_context.local_context:
            prompt_parts.append("\n## 前置任务结果")
            for dep_id in subtask['dependencies']:
                if dep_id in task_context.local_context.get('dependency_results', {}):
                    dep_result = task_context.local_context['dependency_results'][dep_id]
                    dep_summary = dep_result.get('result', {}).get('summary', '无可用摘要')
                    dep_status = "成功" if dep_result.get('success', False) else "失败"
                    
                    prompt_parts.append(f"\n### 任务 {dep_id} 结果 ({dep_status}):")
                    prompt_parts.append(f"{dep_summary}")
                    
                    # 如果有详细结果且不太长，也包含
                    dep_details = dep_result.get('result', {}).get('details', '')
                    if dep_details and len(dep_details) < 1000:
                        prompt_parts.append(f"\n详细结果:\n{dep_details}")
        
        # 添加关键工件引用
        if task_context.artifacts:
            prompt_parts.append("\n## 可用工件")
            for name, artifact in task_context.artifacts.items():
                prompt_parts.append(f"\n### {name}:")
                content = artifact['content']
                # 如果内容太长，截断显示
                if isinstance(content, str) and len(content) > 1000:
                    content = content[:997] + "..."
                
                # 确定显示格式
                if artifact['metadata'].get('type') == 'code':
                    prompt_parts.append(f"```\n{content}\n```")
                elif isinstance(content, (dict, list)):
                    prompt_parts.append(f"```json\n{json.dumps(content, ensure_ascii=False, indent=2)}\n```")
                else:
                    prompt_parts.append(content)
        
        # 添加任务特定上下文
        if 'task_definition' in task_context.local_context:
            task_def = task_context.local_context['task_definition']
            if 'context' in task_def:
                prompt_parts.append("\n## 任务特定上下文")
                context = task_def['context']
                if isinstance(context, dict):
                    for key, value in context.items():
                        prompt_parts.append(f"\n### {key}:")
                        if isinstance(value, (dict, list)):
                            prompt_parts.append(f"```json\n{json.dumps(value, ensure_ascii=False, indent=2)}\n```")
                        else:
                            prompt_parts.append(str(value))
                else:
                    prompt_parts.append(str(context))
        
        # 添加特定输出格式要求
        if 'expected_output_format' in subtask or 'output_format' in subtask:
            output_format = subtask.get('expected_output_format', subtask.get('output_format', ''))
            prompt_parts.append(f"\n## 输出格式要求\n{output_format}")
        else:
            # 提供默认输出格式
            prompt_parts.append("""
## 输出格式要求
请在完成任务后，提供JSON格式的结构化输出：

```json
{
  "task_id": "任务ID",
  "success": true或false,
  "result": {
    "summary": "简要总结任务结果",
    "details": "详细任务结果"
  },
  "artifacts": {
    "key1": "值1",
    "key2": "值2"
  },
  "next_steps": [
    "后续步骤1",
    "后续步骤2"
  ]
}
```

请确保在回复的最后包含上述JSON格式的输出。
""")
        
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
        
        OBSOLETE: 这个方法使用了不可靠的正则表达式解析方式，已被新的结构化输出处理取代
        建议使用新的上下文管理机制
        
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
    
    def _extract_and_store_artifacts_from_text(self, text, subtask, task_context):
        """
        从文本中提取并存储任务产生的工件
        
        参数:
            text (str): Claude输出文本
            subtask (dict): 子任务定义
            task_context (TaskContext): 任务上下文
        """
        # 如果文本为空，直接返回
        if not text:
            return
            
        # 处理Claude输出
        last_output = text
        
        # 提取代码块
        code_blocks = re.findall(r'```(\w*)\n(.*?)```', last_output, re.DOTALL)
        for i, (lang, code) in enumerate(code_blocks):
            if not lang:
                lang = "text"
                
            artifact_name = f"{lang}_code_{i+1}"
            
            # 存储代码工件
            task_context.add_artifact(
                artifact_name,
                code.strip(),
                {
                    'type': 'code',
                    'language': lang,
                    'source': 'code_block',
                    'extracted_from': 'claude_output'
                }
            )
            logger.info(f"提取到{lang}代码工件: {artifact_name}")
            
        # 提取可能的文件路径
        file_paths = re.findall(r'(?:文件|File)[:：]\s*[`\'"]([^`\'"]+)[`\'"]', last_output)
        for i, path in enumerate(file_paths):
            # 将文件路径添加为工件引用
            artifact_name = f"file_ref_{i+1}"
            task_context.add_artifact(
                artifact_name,
                path,
                {
                    'type': 'file_reference',
                    'path': path,
                    'source': 'claude_output'
                }
            )
            logger.info(f"提取到文件引用: {path}")
            
        # 如果任务定义了特定工件提取规则
        if 'artifact_extraction' in subtask:
            for rule in subtask['artifact_extraction']:
                pattern = rule['pattern']
                name_template = rule.get('name', 'artifact_{i}')
                
                try:
                    matches = re.findall(pattern, last_output, re.DOTALL)
                    
                    for i, match in enumerate(matches):
                        # 生成工件名称
                        artifact_name = name_template.format(i=i+1)
                        
                        # 存储匹配内容为工件
                        task_context.add_artifact(
                            artifact_name,
                            match,
                            {
                                'type': rule.get('type', 'pattern_match'),
                                'extraction_rule': rule.get('name', pattern),
                                'source': 'pattern_match'
                            }
                        )
                        logger.info(f"使用规则'{rule.get('name', pattern)}'提取到工件: {artifact_name}")
                except re.error as e:
                    logger.error(f"工件提取规则'{rule.get('name', pattern)}'有误: {str(e)}")
                    
        # 检查结果中的工件字段
        if 'result' in task_context.local_context and isinstance(task_context.local_context['result'], dict):
            result = task_context.local_context['result']
            
            if 'artifacts' in result and isinstance(result['artifacts'], dict):
                for name, content in result['artifacts'].items():
                    # 如果工件还未存储，添加到上下文
                    if name not in task_context.artifacts:
                        # 推断工件类型
                        artifact_type = 'text'
                        if isinstance(content, str):
                            if content.startswith("def ") or content.startswith("class ") or "import " in content:
                                artifact_type = 'code'
                            elif content.startswith("<") and ">" in content:
                                artifact_type = 'markup'
                            elif content.startswith("{") or content.startswith("["):
                                try:
                                    json.loads(content)
                                    artifact_type = 'json'
                                except:
                                    pass
                                    
                        # 存储工件
                        task_context.add_artifact(
                            name,
                            content,
                            {
                                'type': artifact_type,
                                'source': 'result_artifacts'
                            }
                        )
                        logger.info(f"从结果中提取到工件: {name} (类型: {artifact_type})")