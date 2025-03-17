#!/usr/bin/env python3
"""
任务拆分与执行系统 - 任务规划模块
实现外层循环(规划者)功能，负责任务分析、拆分和协调
"""

import json
import os
import time
from datetime import datetime
import logging
from openai import OpenAI
from task_planner.core.context_management import TaskContext, ContextManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('task_planner')

class TaskPlanner:
    """任务规划者类，负责复杂任务的分析、拆分和协调"""
    
    def __init__(self, task_description, context_manager=None, logs_dir="logs", skip_analysis=False):
        """
        初始化任务规划者
        
        参数:
            task_description (str): 任务描述
            context_manager (ContextManager, optional): 上下文管理器
            logs_dir (str): 日志目录
            skip_analysis (bool): 是否跳过分析
        """
        # 统一处理任务描述格式
        if isinstance(task_description, dict):
            self.full_description = task_description
            self.task_description = task_description.get('description', '')
        else:
            self.task_description = str(task_description)
            self.full_description = {'description': self.task_description}

        logger.info(
            f"创建任务: {self.task_description[:100]}{'...' if len(self.task_description) > 100 else ''}"
        )
        
        self.subtasks = []
        self.current_index = 0
        self.results = {}
        
        # 初始化上下文管理器
        if context_manager:
            self.context_manager = context_manager
        else:
            # 创建日志目录
            os.makedirs(logs_dir, exist_ok=True)
            context_dir = os.path.join(logs_dir, f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            os.makedirs(context_dir, exist_ok=True)
            self.context_manager = ContextManager(context_dir=context_dir)
        
        # 创建规划者上下文
        self.plan_context = self.context_manager.task_contexts.get(
            'planner', TaskContext('planner', self.context_manager.global_context)
        )
        self.context_manager.task_contexts['planner'] = self.plan_context
        
        # 初始化大模型桥接（使用OpenRouter API）
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ.get("OPENROUTER_API_KEY", "")
        )
        
        # 记录任务创建
        self.plan_context.add_execution_record(
            'task_created',
            f"创建任务: {self.task_description[:100]}{'...' if len(self.task_description) > 100 else ''}",
            {'full_description': self.full_description}
        )
        logger.info(f"任务规划者已初始化，任务描述: {self.task_description[:50]}...")
        
        self.skip_analysis = skip_analysis  # 新增跳过分析标志
        
        if not self.skip_analysis:  # 控制是否执行分析
            self.analysis_result = self.analyze_task()
        else:
            self.analysis_result = {"status": "predefined"}
        
    def analyze_task(self):
        """
        分析任务特性和需求
        
        返回:
            dict: 任务分析结果
        """
        logger.info("开始分析任务...")
        
        # 构建分析提示
        analysis_prompt = self._build_analysis_prompt()
        
        # 记录开始分析
        self.plan_context.add_execution_record(
            'analysis_started',
            "开始任务分析",
            {'prompt': analysis_prompt}
        )
        
        # 使用Claude API直接分析任务
        system_prompt = """你是任务分析专家，负责分析复杂任务并提供结构化输出。
请分析提供的任务，返回JSON格式的分析结果，包含任务类型、目标、技术需求和可能的挑战。
输出必须是有效的JSON格式。
"""
        try:
            # 调用OpenRouter API
            response = self.client.chat.completions.create(
                model="anthropic/claude-3.7-sonnet",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": analysis_prompt}
                ],
                max_tokens=100000
            )
            
            # 从响应中提取内容
            result_text = response.choices[0].message.content
            
            # 尝试从文本中提取JSON
            import re
            json_matches = re.findall(r'```json\n(.*?)\n```', result_text, re.DOTALL)
            
            if json_matches:
                # 使用找到的最后一个JSON块
                result_json = json_matches[-1]
                analysis = json.loads(result_json)
            else:
                # 直接尝试解析整个响应
                analysis = json.loads(result_text)
                
            # 规范化分析结果格式
            if 'task_id' not in analysis:
                analysis = {
                    "task_id": "task_analysis",
                    "success": True,
                    "result": analysis
                }
                
            # 存储分析结果到上下文
            self.plan_context.update_local('analysis', analysis)
            self.plan_context.add_execution_record(
                'analysis_completed',
                "任务分析完成",
                {'analysis_summary': analysis.get('result', {}).get('summary', '')}
            )
            logger.info("任务分析完成")
            return analysis
                
        except Exception as e:
            logger.error(f"任务分析失败: {str(e)}")
        
        # 如果未能获取有效结果，返回默认分析
        default_analysis = {
            "task_id": "task_analysis",
            "success": False,
            "result": {
                "summary": "无法完成任务分析",
                "details": "未能解析Claude的分析结果"
            }
        }
        self.plan_context.update_local('analysis', default_analysis)
        logger.warning("使用默认分析结果")
        return default_analysis
        
    def break_down_task(self, analysis=None):
        """
        将任务拆分为子任务
        
        参数:
            analysis (dict, optional): 任务分析结果
            
        返回:
            list: 子任务列表
        """
        if self.skip_analysis:  # 直接返回预定义子任务
            logger.info("跳过任务拆分，使用预定义子任务")
            return self.subtasks
            
        logger.info("开始任务拆分...")
        
        # 如果未提供分析，使用存储的分析
        if analysis is None:
            analysis = self.plan_context.local_context.get('analysis')
            # 如果仍然没有分析，先进行分析
            if analysis is None:
                analysis = self.analyze_task()
                
        # 构建任务拆分提示
        breakdown_prompt = self._build_breakdown_prompt(analysis)
        
        # 记录开始拆分
        self.plan_context.add_execution_record(
            'breakdown_started',
            "开始任务拆分",
            {'prompt': breakdown_prompt}
        )
        
        # 使用Claude API直接拆分任务
        system_prompt = """你是任务拆分专家，负责将复杂任务分解为小任务并定义它们之间的依赖关系。
请将提供的任务分解为适当数量的明确子任务。

每个子任务必须包含以下字段：
- id: 唯一标识符
- name: 任务名称
- description: 任务描述
- instruction: 详细执行指令
- input_files: 输入文件路径字典
- output_files: 输出文件路径字典，必须使用完整的绝对路径。每个任务必须包含一个main_result字段指向JSON结果文件
- success_criteria: 成功标准列表
- dependencies: 依赖任务ID列表

特别注意：
1. 所有文件路径必须使用用户提供的base_dir作为前缀，构建完整的绝对路径
2. 每个output_files字典中的路径必须是完整的绝对路径，例如"/home/user/project/output/file.py"
3. 用户会在提示中指定完整的基础目录路径，你必须严格使用该路径生成所有文件路径

输出必须是有效的JSON格式，包含subtasks数组。
"""
        try:
            # 调用OpenRouter API
            response = self.client.chat.completions.create(
                model="anthropic/claude-3.7-sonnet",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": breakdown_prompt}
                ],
                max_tokens=100000
            )
            
            # 从响应中提取内容
            result_text = response.choices[0].message.content
            
            # 尝试从文本中提取JSON
            import re
            json_matches = re.findall(r'```json\n(.*?)\n```', result_text, re.DOTALL)
            
            if json_matches:
                # 使用找到的最后一个JSON块
                result_json = json_matches[-1]
                breakdown_data = json.loads(result_json)
            else:
                # 直接尝试解析整个响应
                breakdown_data = json.loads(result_text)
            
            # 提取子任务列表
            if 'subtasks' in breakdown_data:
                subtasks = breakdown_data['subtasks']
            elif 'result' in breakdown_data and 'subtasks' in breakdown_data['result']:
                subtasks = breakdown_data['result']['subtasks']
            else:
                # 如果数据结构不符合预期，尝试从顶层获取子任务
                subtasks = breakdown_data
                if not isinstance(subtasks, list):
                    raise ValueError("无法找到有效的子任务列表")
                    
            # 验证并规范化子任务
            self.subtasks = self._normalize_subtasks(subtasks)
            
            # 创建子任务目录结构
            self.context_manager.create_output_directories(self.subtasks)
            
            # 初始化任务上下文
            for subtask in self.subtasks:
                subtask_id = subtask['id']
                # 为每个子任务创建上下文，包含任务定义和全局分析
                self.context_manager.create_subtask_context('planner', subtask_id)
                self.context_manager.update_task_context(subtask_id, {
                    'task_definition': subtask,
                    'analysis_summary': analysis.get('result', {}).get('summary', '')
                })
                
                # 添加输出文件路径引用
                if 'output_files' in subtask:
                    for output_type, output_path in subtask['output_files'].items():
                        # 如果路径是相对路径，使用上下文目录作为基础
                        if not os.path.isabs(output_path) and self.context_manager.context_dir:
                            full_path = os.path.join(self.context_manager.context_dir, output_path)
                        else:
                            full_path = output_path
                            
                        # 将输出文件路径添加到上下文
                        self.context_manager.task_contexts[subtask_id].add_file_reference(
                            f"output_{output_type}",
                            full_path,
                            {
                                'type': 'output_file',
                                'output_type': output_type
                            }
                        )
                
            # 存储任务分解结果
            self.plan_context.update_local('subtasks', self.subtasks)
            self.plan_context.add_execution_record(
                'breakdown_completed',
                f"任务拆分完成，共{len(self.subtasks)}个子任务",
                {'subtasks_count': len(self.subtasks)}
            )
            logger.info(f"任务拆分完成，共{len(self.subtasks)}个子任务")
            return self.subtasks
            
        except Exception as e:
            logger.error(f"任务拆分失败: {str(e)}")
        
        # 如果未能获取有效结果，返回默认子任务列表
        self.subtasks = [
            {
                "id": "fallback_task",
                "name": "执行完整任务",
                "description": "因任务拆分失败，直接执行完整任务",
                "instruction": self.task_description,
                "output_files": {
                    "main_result": "results/fallback_task/result.json",
                    "report": "results/fallback_task/report.md"
                },
                "success_criteria": ["完成任务目标"],
                "dependencies": []
            }
        ]
        
        # 创建子任务目录结构
        self.context_manager.create_output_directories(self.subtasks)
        
        # 为fallback任务创建上下文
        self.context_manager.create_subtask_context('planner', "fallback_task")
        self.context_manager.update_task_context("fallback_task", {
            'task_definition': self.subtasks[0],
            'analysis_summary': '任务拆分失败，使用默认任务'
        })
        
        # 添加输出文件路径引用
        if self.context_manager.context_dir:
            result_path = os.path.join(self.context_manager.context_dir, "results/fallback_task/result.json")
            report_path = os.path.join(self.context_manager.context_dir, "results/fallback_task/report.md")
            
            self.context_manager.task_contexts["fallback_task"].add_file_reference(
                "output_main_result", 
                result_path,
                {'type': 'output_file', 'output_type': 'main_result'}
            )
            
            self.context_manager.task_contexts["fallback_task"].add_file_reference(
                "output_report", 
                report_path,
                {'type': 'output_file', 'output_type': 'report'}
            )
        
        self.plan_context.update_local('subtasks', self.subtasks)
        logger.warning("使用默认任务拆分")
        return self.subtasks
        
    def get_next_subtask(self):
        """
        获取下一个待执行的子任务
        
        返回:
            dict: 下一个子任务，如果所有任务都已执行则返回None
        """
        if self.current_index >= len(self.subtasks):
            logger.info("所有子任务已执行完毕")
            return None
        
        subtask = self.subtasks[self.current_index]
        subtask_id = subtask['id']
        
        # 获取上下文并添加必要的依赖数据
        if self.current_index > 0:
            # 不是第一个任务，可能需要前置任务的文件引用
            
            # 如果有明确定义的依赖关系，使用它们
            dependencies = subtask.get('dependencies', [])
            if dependencies:
                # 建立前置任务文件引用到当前任务的映射
                input_files = {}
                    
                # 只传播依赖任务的文件引用
                for dep_id in dependencies:
                    if dep_id in self.results:
                        # 传播依赖任务的文件引用到当前任务
                        logger.info(f"传播任务{dep_id}的文件引用到任务{subtask_id}")
                        self.context_manager.propagate_results(dep_id, [subtask_id], keys=['success'], file_reference_keys=None)
                        
                        # 添加依赖结果引用
                        if subtask_id in self.context_manager.task_contexts:
                            if 'dependency_files' not in self.context_manager.task_contexts[subtask_id].local_context:
                                self.context_manager.task_contexts[subtask_id].local_context['dependency_files'] = {}
                            
                            # 查找依赖任务的结果文件路径
                            if dep_id in self.context_manager.task_contexts:
                                dep_context = self.context_manager.task_contexts[dep_id]
                                for file_key, file_info in dep_context.file_paths.items():
                                    if file_info['metadata'].get('type') == 'output_file':
                                        output_type = file_info['metadata'].get('output_type')
                                        input_files[f"{dep_id}_{output_type}"] = file_info['path']
                                
                                # 添加依赖文件映射到当前任务上下文
                                self.context_manager.task_contexts[subtask_id].local_context['dependency_files'][dep_id] = input_files
            else:
                # 默认传播前一个任务的文件引用
                prev_task_id = self.subtasks[self.current_index-1]['id']
                if prev_task_id in self.results:
                    logger.info(f"传播前一任务{prev_task_id}的文件引用到任务{subtask_id}")
                    self.context_manager.propagate_results(prev_task_id, [subtask_id], keys=['success'], file_reference_keys=None)
        
        # 更新输入文件映射（如果任务有定义）
        if 'input_files' in subtask and isinstance(subtask['input_files'], dict):
            # 确保所有引用的输入文件实际存在
            input_files_mapping = {}
            for input_key, input_path in subtask['input_files'].items():
                # 如果输入文件是前置任务的输出文件引用
                if ':' in input_path:
                    # 格式： task_id:output_type
                    parts = input_path.split(':')
                    if len(parts) == 2:
                        ref_task_id, ref_output_type = parts
                        if ref_task_id in self.context_manager.task_contexts:
                            ref_context = self.context_manager.task_contexts[ref_task_id]
                            ref_file_key = f"output_{ref_output_type}"
                            if ref_file_key in ref_context.file_paths:
                                # 获取实际文件路径
                                actual_path = ref_context.file_paths[ref_file_key]['path']
                                input_files_mapping[input_key] = actual_path
                                
                                # 添加文件引用到当前任务上下文
                                self.context_manager.task_contexts[subtask_id].add_file_reference(
                                    f"input_{input_key}",
                                    actual_path,
                                    {
                                        'type': 'input_file',
                                        'input_type': input_key,
                                        'from_task': ref_task_id,
                                        'from_output': ref_output_type
                                    }
                                )
                else:
                    # 直接文件路径
                    if not os.path.isabs(input_path) and self.context_manager.context_dir:
                        full_path = os.path.join(self.context_manager.context_dir, input_path)
                    else:
                        full_path = input_path
                        
                    input_files_mapping[input_key] = full_path
                    
                    # 添加文件引用到当前任务上下文
                    self.context_manager.task_contexts[subtask_id].add_file_reference(
                        f"input_{input_key}",
                        full_path,
                        {
                            'type': 'input_file',
                            'input_type': input_key
                        }
                    )
            
            # 更新子任务的输入文件映射
            subtask['input_files_mapping'] = input_files_mapping
        
        # 更新上下文添加全局进度信息
        self.context_manager.update_task_context(subtask_id, {
            'progress': {
                'current_index': self.current_index,
                'total_tasks': len(self.subtasks),
                'completed_tasks': list(self.results.keys())
            }
        })
        
        # 记录即将执行的任务
        self.plan_context.add_execution_record(
            'subtask_prepared',
            f"准备执行子任务: {subtask.get('name', subtask_id)}",
            {'subtask_id': subtask_id, 'index': self.current_index}
        )
        logger.info(f"准备执行子任务: {subtask.get('name', subtask_id)} (任务ID: {subtask_id})")
        
        self.current_index += 1
        return subtask
        
    def process_result(self, subtask_id, result):
        """
        处理子任务执行结果
        
        参数:
            subtask_id (str): 子任务ID
            result (dict): 子任务执行结果，包含结果文件路径等信息
            
        返回:
            bool: 处理是否成功
        """
        # 存储内存中的结果
        self.results[subtask_id] = result
        
        # 获取结果文件路径并检查
        result_file_path = None
        try:
            # 检查任务上下文中的输出文件信息
            if subtask_id in self.context_manager.task_contexts:
                task_context = self.context_manager.task_contexts[subtask_id]
                
                # 查找main_result输出文件
                result_file_key = "output_main_result"
                if result_file_key in task_context.file_paths:
                    result_file_path = task_context.file_paths[result_file_key]['path']
                    
                    # 检查结果文件是否存在
                    if os.path.exists(result_file_path):
                        logger.info(f"发现任务 {subtask_id} 的结果文件: {result_file_path}")
                        
                        # 读取结果文件内容
                        try:
                            with open(result_file_path, 'r', encoding='utf-8') as f:
                                file_result = json.load(f)
                                
                            # 合并文件结果与内存结果
                            self.results[subtask_id].update(file_result)
                            
                            # 确保必要字段存在
                            if 'task_id' not in self.results[subtask_id]:
                                self.results[subtask_id]['task_id'] = subtask_id
                                
                            # 添加文件引用到结果
                            self.context_manager.task_contexts[subtask_id].add_file_reference(
                                'result_file',
                                result_file_path,
                                {'type': 'result_file'}
                            )
                        except Exception as e:
                            logger.warning(f"解析结果文件 {result_file_path} 时出错: {str(e)}")
                
                # 检查并记录任务生成的其他文件
                subtask_result_dir = task_context.base_dir
                if subtask_result_dir and os.path.exists(subtask_result_dir):
                    artifacts = {}
                    try:
                        # 遍历子任务结果目录，收集生成的文件
                        for root, dirs, files in os.walk(subtask_result_dir):
                            rel_dir = os.path.relpath(root, subtask_result_dir)
                            for file in files:
                                if file == 'result.json' and os.path.join(root, file) == result_file_path:
                                    continue  # 跳过主结果文件
                                
                                file_path = os.path.join(root, file)
                                rel_path = os.path.join(rel_dir, file) if rel_dir != '.' else file
                                artifact_name = rel_path.replace('/', '_')
                                
                                # 添加到文件引用
                                task_context.add_file_reference(
                                    f'artifact_{artifact_name}',
                                    file_path,
                                    {'type': 'artifact_file', 'rel_path': rel_path}
                                )
                                
                                # 添加到工件列表
                                artifacts[rel_path] = file_path
                        
                        # 如果找到了工件，添加到结果
                        if artifacts:
                            self.results[subtask_id]['artifacts'] = artifacts
                            logger.info(f"收集到任务 {subtask_id} 的 {len(artifacts)} 个工件文件")
                    except Exception as e:
                        logger.warning(f"收集任务 {subtask_id} 的工件文件时出错: {str(e)}")
        except Exception as e:
            logger.warning(f"处理任务 {subtask_id} 的结果文件时出错: {str(e)}")
        
        # 更新任务上下文
        if subtask_id in self.context_manager.task_contexts:
            self.context_manager.update_task_context(subtask_id, {
                'success': self.results[subtask_id].get('success', False),
                'completion_time': datetime.now().isoformat()
            })
        
        # 记录任务完成
        success = self.results[subtask_id].get('success', False)
        status = "成功" if success else "失败"
        self.plan_context.add_execution_record(
            'subtask_completed',
            f"子任务 {subtask_id} 执行{status}",
            {'subtask_id': subtask_id, 'success': success}
        )
        logger.info(f"子任务 {subtask_id} 执行{status}")
        
        # 评估结果并决定是否需要调整计划
        self._evaluate_and_adjust_plan(subtask_id, self.results[subtask_id])
        
        return True
        
    def _evaluate_and_adjust_plan(self, subtask_id, result):
        """
        评估任务结果，决定是否需要调整计划
        
        参数:
            subtask_id (str): 子任务ID
            result (dict): 子任务执行结果
        """
        # 获取任务执行摘要（包含结果文件内容）
        task_summary = self.context_manager.get_execution_summary(subtask_id)
        
        # 如果任务失败，可能需要调整计划
        if not result.get('success', False):
            logger.warning(f"子任务 {subtask_id} 失败，准备评估调整计划")
            
            # 构建评估提示
            evaluation_prompt = self._build_plan_adjustment_prompt(task_summary)
            
            # 记录开始评估
            self.plan_context.add_execution_record(
                'plan_adjustment_started',
                f"开始评估任务 {subtask_id} 的结果",
                {'task_summary': task_summary}
            )
            
            # 使用Claude API直接评估是否需要调整
            system_prompt = """你是任务规划调整专家，负责评估任务执行结果并决定是否需要修改计划。
请分析任务执行情况，评估是否需要调整计划，返回JSON格式的评估结果。
如果需要调整，应包含needs_adjustment=true和具体的调整方案。
如果不需要调整，应包含needs_adjustment=false和具体的理由。
输出必须是有效的JSON格式。
"""
            try:
                # 调用OpenRouter API
                response = self.client.chat.completions.create(
                    model="anthropic/claude-3.7-sonnet",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": evaluation_prompt}
                    ],
                    max_tokens=100000
                )
                
                # 从响应中提取内容
                result_text = response.choices[0].message.content
                
                # 尝试从文本中提取JSON
                import re
                json_matches = re.findall(r'```json\n(.*?)\n```', result_text, re.DOTALL)
                
                if json_matches:
                    # 使用找到的最后一个JSON块
                    result_json = json_matches[-1]
                    adjustment = json.loads(result_json)
                else:
                    # 直接尝试解析整个响应
                    adjustment = json.loads(result_text)
                
                # 规范化结果格式
                if 'result' not in adjustment and 'needs_adjustment' in adjustment:
                    adjustment = {
                        "result": adjustment
                    }
                    
                # 检查是否需要调整
                needs_adjustment = adjustment.get('result', {}).get('needs_adjustment', False)
                if needs_adjustment:
                    # 需要调整计划
                    self._apply_plan_adjustment(adjustment, subtask_id)
                else:
                    # 不需要调整计划
                    logger.info(f"评估结果：不需要调整计划")
                    self.plan_context.add_execution_record(
                        'plan_adjustment_skipped',
                        "评估结果：不需要调整计划",
                        {'reason': adjustment.get('result', {}).get('reason', '当前计划适合继续执行')}
                    )
                    
                # 保存调整决策到文件
                if self.context_manager.context_dir:
                    adjustment_file_path = os.path.join(self.context_manager.context_dir, 
                                                      f"adjustment_{subtask_id}.json")
                    try:
                        with open(adjustment_file_path, 'w', encoding='utf-8') as f:
                            json.dump(adjustment, f, ensure_ascii=False, indent=2)
                    except Exception as e:
                        logger.warning(f"保存调整决策到文件时出错: {str(e)}")
                    
            except Exception as e:
                logger.error(f"计划调整评估失败: {str(e)}")
        else:
            # 任务成功，但仍检查结果中是否有下一步建议
            if 'next_steps' in result and result['next_steps']:
                logger.info(f"子任务 {subtask_id} 成功，但提供了下一步建议: {result['next_steps']}")
                
                # 将下一步建议记录到上下文
                self.plan_context.add_execution_record(
                    'task_suggestions',
                    f"任务 {subtask_id} A提供了建议",
                    {'next_steps': result['next_steps']}
                )
                
                # 可以保存建议到文件
                if self.context_manager.context_dir:
                    suggestions_file_path = os.path.join(self.context_manager.context_dir, 
                                                     f"suggestions_{subtask_id}.json")
                    try:
                        with open(suggestions_file_path, 'w', encoding='utf-8') as f:
                            json.dump({'next_steps': result['next_steps']}, f, ensure_ascii=False, indent=2)
                    except Exception as e:
                        logger.warning(f"保存任务建议到文件时出错: {str(e)}")
            else:
                # 任务成功，暂时不考虑调整计划
                logger.info(f"子任务 {subtask_id} 成功，继续执行当前计划")
            
    def _apply_plan_adjustment(self, adjustment, trigger_task_id):
        """
        应用计划调整
        
        参数:
            adjustment (dict): 调整方案
            trigger_task_id (str): 触发调整的任务ID
        """
        # 记录原始计划
        logger.info(f"开始调整计划，由任务 {trigger_task_id} 触发")
        self.plan_context.add_execution_record(
            'plan_adjustment_started',
            f"由于任务 {trigger_task_id} 的结果，计划被调整",
            {'original_plan': self.subtasks[self.current_index:]}
        )
        
        # 获取调整方案
        adjustment_data = adjustment.get('result', {})
        adjustment_reason = adjustment_data.get('reason', '未提供调整原因')
        
        # 应用调整
        if 'insert_tasks' in adjustment_data:
            # 插入新任务
            for task in adjustment_data['insert_tasks']:
                task_id = task['id']
                insert_index = task.get('insert_index', self.current_index)
                
                # 规范化任务数据
                task = self._normalize_subtasks([task])[0]
                
                # 创建任务上下文
                self.context_manager.create_subtask_context('planner', task_id)
                self.context_manager.update_task_context(task_id, {
                    'task_definition': task,
                    'created_from_adjustment': True,
                    'parent_task': trigger_task_id
                })
                
                # 插入任务列表
                self.subtasks.insert(insert_index, task)
                logger.info(f"插入新任务 '{task.get('name', task_id)}' 到位置 {insert_index}")
                
                # 如果插入位置在当前索引之前，需要调整当前索引
                if insert_index <= self.current_index:
                    self.current_index += 1
        
        if 'remove_tasks' in adjustment_data:
            # 移除任务
            for task_id in adjustment_data['remove_tasks']:
                for i, task in enumerate(self.subtasks):
                    if task['id'] == task_id and i >= self.current_index:
                        # 只能移除尚未执行的任务
                        logger.info(f"移除任务 '{task.get('name', task_id)}'")
                        self.subtasks.pop(i)
                        break
        
        if 'modify_tasks' in adjustment_data:
            # 修改任务
            for task_mod in adjustment_data['modify_tasks']:
                task_id = task_mod['id']
                for i, task in enumerate(self.subtasks):
                    if task['id'] == task_id and i >= self.current_index:
                        # 更新任务定义
                        logger.info(f"修改任务 '{task.get('name', task_id)}'")
                        for key, value in task_mod.items():
                            if key != 'id':
                                task[key] = value
                                
                        # 更新任务上下文
                        if task_id in self.context_manager.task_contexts:
                            self.context_manager.update_task_context(task_id, {
                                'task_definition': task,
                                'modified_from_adjustment': True,
                                'modification_reason': adjustment_reason
                            })
                        break
                        
        # 记录调整后的计划
        logger.info(f"计划调整完成，现有{len(self.subtasks) - self.current_index}个待执行任务")
        self.plan_context.update_local('adjusted_plan', {
            'subtasks': self.subtasks,
            'adjustment_reason': adjustment_reason,
            'triggering_task': trigger_task_id,
            'adjustment_time': datetime.now().isoformat()
        })
        self.plan_context.add_execution_record(
            'plan_adjustment_completed',
            "计划调整完成",
            {'remaining_tasks': len(self.subtasks) - self.current_index}
        )
        
    def is_complete(self):
        """
        检查所有任务是否已完成
        
        返回:
            bool: 是否所有任务都已完成
        """
        return self.current_index >= len(self.subtasks)
        
    def get_final_result(self):
        """
        获取最终结果，整合所有小任务结果文件
        
        返回:
            dict: 最终结果
        """
        logger.info("开始生成最终结果...")
        
        # 收集所有子任务的结果文件
        subtask_results = {}
        for subtask_id, result in self.results.items():
            # 查找任务的结果文件路径
            if subtask_id in self.context_manager.task_contexts:
                task_context = self.context_manager.task_contexts[subtask_id]
                
                # 检查是否有结果文件
                result_file_key = "output_main_result"
                if result_file_key in task_context.file_paths:
                    result_file_path = task_context.file_paths[result_file_key]['path']
                    if os.path.exists(result_file_path):
                        try:
                            # 读取结果文件
                            with open(result_file_path, 'r', encoding='utf-8') as f:
                                file_result = json.load(f)
                                
                            # 将结果文件内容添加到集合
                            subtask_results[subtask_id] = {
                                'result_data': file_result,
                                'result_file': result_file_path
                            }
                            
                            # 收集任务生成的其他文件
                            artifacts = {}
                            for file_key, file_info in task_context.file_paths.items():
                                if file_info['metadata'].get('type') == 'artifact_file':
                                    rel_path = file_info['metadata'].get('rel_path', '')
                                    artifacts[rel_path] = file_info['path']
                                    
                            if artifacts:
                                subtask_results[subtask_id]['artifacts'] = artifacts
                        except Exception as e:
                            logger.warning(f"读取任务 {subtask_id} 的结果文件时出错: {str(e)}")
        
        # 准备整合提示
        integration_prompt = self._build_integration_prompt()
        
        # 将文件结果路径一览添加到提示
        integration_prompt += "\n\n## 子任务结果文件\n"
        for subtask_id, result_info in subtask_results.items():
            integration_prompt += f"- {subtask_id}: {result_info['result_file']}\n"
            if 'artifacts' in result_info and result_info['artifacts']:
                integration_prompt += f"  工件文件: {len(result_info['artifacts'])} 个\n"
        
        # 记录开始生成最终结果
        self.plan_context.add_execution_record(
            'integration_started',
            "开始生成最终结果",
            {'prompt': integration_prompt}
        )
        
        # 使用Claude API直接整合结果
        system_prompt = """你是任务结果整合专家，负责综合多个子任务的结果，提供最终的完整输出。
请分析所有子任务的结果文件，整合为一个完整的最终结果，返回JSON格式的整合结果。
输出必须包含执行摘要、主要成果、工件列表、后续建议和限制说明。
输出必须是有效的JSON格式。
"""
        try:
            # 调用OpenRouter API
            response = self.client.chat.completions.create(
                model="anthropic/claude-3.7-sonnet",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": integration_prompt}
                ],
                max_tokens=100000
            )
            
            # 从响应中提取内容
            result_text = response.choices[0].message.content
            
            # 尝试从文本中提取JSON
            import re
            json_matches = re.findall(r'```json\n(.*?)\n```', result_text, re.DOTALL)
            
            if json_matches:
                # 使用找到的最后一个JSON块
                result_json = json_matches[-1]
                final_result = json.loads(result_json)
            else:
                # 直接尝试解析整个响应
                final_result = json.loads(result_text)
            
            # 规范化结果格式
            if 'task_id' not in final_result:
                final_result = {
                    "task_id": "final_result",
                    "success": True,
                    "result": final_result
                }
            
            # 创建一个汇总所有工件的字典
            all_artifacts = {}
            for subtask_id, result_info in subtask_results.items():
                if 'artifacts' in result_info:
                    for rel_path, path in result_info['artifacts'].items():
                        artifact_key = f"{subtask_id}_{rel_path}"
                        all_artifacts[artifact_key] = path
            
            # 添加工件引用到最终结果
            if all_artifacts:
                if 'artifacts' not in final_result:
                    final_result['artifacts'] = {}
                final_result['artifacts'].update(all_artifacts)
                
            # 存储最终结果
            self.plan_context.update_local('final_result', final_result)
            self.plan_context.add_execution_record(
                'integration_completed',
                "最终结果生成完成",
                {'summary': final_result.get('result', {}).get('summary', '')}
            )
            logger.info("最终结果生成完成")
            
            # 将最终结果保存到文件
            if self.context_manager.context_dir:
                final_result_path = os.path.join(self.context_manager.context_dir, "final_result.json")
                try:
                    with open(final_result_path, 'w', encoding='utf-8') as f:
                        json.dump(final_result, f, ensure_ascii=False, indent=2)
                    
                    # 添加最终结果文件引用
                    self.plan_context.add_file_reference(
                        "final_result_file",
                        final_result_path,
                        {'type': 'final_result'}
                    )
                    
                    logger.info(f"最终结果已保存到文件: {final_result_path}")
                except Exception as e:
                    logger.warning(f"保存最终结果到文件时出错: {str(e)}")
            
            # 保存所有上下文
            self.context_manager.save_all_contexts()
            
            return final_result
                
        except Exception as e:
            logger.error(f"结果整合失败: {str(e)}")
        
        # 如果未能生成有效结果，返回简单汇总
        default_result = self._create_default_final_result()
        self.plan_context.update_local('final_result', default_result)
        logger.warning("使用默认最终结果")
        
        # 将默认结果保存到文件
        if self.context_manager.context_dir:
            default_result_path = os.path.join(self.context_manager.context_dir, "final_result.json")
            try:
                with open(default_result_path, 'w', encoding='utf-8') as f:
                    json.dump(default_result, f, ensure_ascii=False, indent=2)
                
                # 添加最终结果文件引用
                self.plan_context.add_file_reference(
                    "final_result_file",
                    default_result_path,
                    {'type': 'final_result'}
                )
            except Exception as e:
                logger.warning(f"保存默认最终结果到文件时出错: {str(e)}")
        
        # 保存所有上下文
        self.context_manager.save_all_contexts()
        
        return default_result
        
    def _create_default_final_result(self):
        """创建默认最终结果"""
        # 计算成功和失败的任务数
        success_count = sum(1 for r in self.results.values() if r.get('success', False))
        
        # 构建默认结果
        return {
            "task_id": "final_result",
            "success": success_count > 0,
            "result": {
                "summary": f"任务执行完成，共{len(self.results)}个子任务，{success_count}个成功",
                "details": "未能自动整合结果，提供原始任务结果"
            },
            "subtask_results": {task_id: result for task_id, result in self.results.items()}
        }
        
    def _normalize_subtasks(self, subtasks):
        """
        规范化子任务列表，确保必要的字段存在
        
        参数:
            subtasks (list): 原始子任务列表
            
        返回:
            list: 规范化后的子任务列表
        """
        normalized = []
        for i, subtask in enumerate(subtasks):
            # 确保任务有ID
            if 'id' not in subtask:
                subtask['id'] = f"task_{i+1}"
                
            # 确保任务有名称
            if 'name' not in subtask:
                subtask['name'] = f"任务 {i+1}"
                
            # 确保任务有指令
            if 'instruction' not in subtask:
                if 'description' in subtask:
                    subtask['instruction'] = subtask['description']
                else:
                    subtask['instruction'] = f"执行任务 {i+1}"
                    
            # 初始化依赖列表
            if 'dependencies' not in subtask:
                subtask['dependencies'] = []
                
            # 确保有输出文件定义
            if 'output_files' not in subtask or not isinstance(subtask['output_files'], dict):
                subtask['output_files'] = {'main_result': f"results/task_{i+1}/result.json"}
                
            # 确保main_result存在
            if 'main_result' not in subtask['output_files']:
                subtask['output_files']['main_result'] = f"results/task_{i+1}/result.json"
                
            normalized.append(subtask)
            
        return normalized
        
    def _build_analysis_prompt(self):
        """构建任务分析提示"""
        return f"""
分析以下复杂任务，确定其特性、需求和可能的挑战。

# 任务描述
{self.task_description}

# 分析要求
1. 确定任务的主要目标和预期结果
2. 识别任务的关键领域和技术要求
3. 分析任务的复杂度和挑战点
4. 考虑可能的方法和策略
5. 评估任务所需的资源和工具

请提供详细的任务分析，包含以下方面：
- 任务类型和性质
- 主要目标和子目标
- 技术需求和依赖
- 可能的难点和风险
- 建议的实施策略

结果必须包含JSON格式的分析摘要。
"""
        
    def _build_breakdown_prompt(self, analysis):
        """
        构建任务拆分提示
        
        参数:
            analysis (dict): 任务分析结果
        """
        # 提取分析摘要
        analysis_summary = analysis.get('result', {}).get('summary', '未提供分析摘要')
        analysis_details = analysis.get('result', {}).get('details', '未提供详细分析')
        
        # 获取当前工作目录的绝对路径作为输出基础目录
        import os
        current_working_dir = os.getcwd()
        if self.context_manager and self.context_manager.context_dir:
            if os.path.isabs(self.context_manager.context_dir):
                output_base_dir = self.context_manager.context_dir
            else:
                output_base_dir = os.path.join(current_working_dir, self.context_manager.context_dir)
        else:
            # 使用更可能与实际执行环境匹配的路径
            output_base_dir = os.path.join(current_working_dir, "logs/subtasks_execution")
        
        return f"""
将以下复杂任务分解为一系列小任务，确定执行顺序和依赖关系。

# 任务描述
{self.task_description}

# 任务分析摘要
{analysis_summary}

# 详细分析
{analysis_details}

# 拆分要求
1. 仔细检查原始任务描述中是否明确要求特定数量的步骤，如有明确要求，请严格遵循
2. 如果原始描述未指定步骤数，则将任务分解为适当数量的小任务（通常为3-6个,如原始任务描述中有明确要求可以忽略这个3-6条的要求），确保每个任务足够简单明确
3. 保持每个子任务的复杂度一致，避免某些任务过于复杂而其他任务过于简单
4. 确保每个小任务具有明确的目标和输入/输出
5. 定义任务之间的依赖关系和执行顺序
6. 考虑每个任务可能的失败点和替代路径

对于每个小任务，请提供以下信息：
- 唯一任务ID
- 任务名称
- 任务描述
- 详细指令
- 输入文件(input_files)：指定任务所需的输入文件路径
- 输出文件(output_files)：必须使用完整的绝对路径，明确指定任务必须生成的所有文件路径
- 预期输出
- 依赖的任务ID列表
- 成功标准(success_criteria)：明确定义任务成功的条件

# 输出路径要求（非常重要！）
所有输出文件(output_files)必须使用以下绝对路径：
基础目录: {output_base_dir}

对于每个文件，你必须提供完整的绝对路径，例如：
- 如果要创建一个名为add.py的文件，完整路径必须是："{output_base_dir}/add.py"
- 如果要创建一个名为test_add.py的文件，完整路径必须是："{output_base_dir}/test_add.py"
- 如果要创建结果文件，例如task1_result.json，完整路径必须是："{output_base_dir}/task1_result.json"

严格遵守：所有文件路径都必须以"{output_base_dir}/"开头，不允许使用相对路径或其他目录

# 关于结果文件的特殊要求
每个任务必须在output_files中包含一个名为"main_result"的JSON结果文件，该文件必须：
1. 包含任务的执行状态和结果摘要
2. 记录该任务生成的所有文件的完整路径
3. 在"artifacts"字段中列出所有生成的文件，包括中间文件和最终输出
4. 对于每个文件，提供其用途和内容的简要说明
5. 提供对生成的代码和文档文件的完整引用

示例结果JSON结构:
```json
{{
  "task_id": "task1",
  "success": true,
  "result": {{
    "summary": "成功创建了项目结构和基础文件",
    "details": "创建了项目目录、主程序文件和配置文件"
  }},
  "artifacts": {{
    "main_script": "{output_base_dir}/main.py",
    "config_file": "{output_base_dir}/config.py",
    "readme": "{output_base_dir}/README.md"
  }},
  "next_steps": ["完善配置文件", "添加更多功能"]
}}
```

执行环境中，实际输出文件路径的例子:
```
output_files: {{
  "add_module": "{output_base_dir}/add.py",
  "main_result": "{output_base_dir}/task1_result.json"
}}
```

重要提示：
1. 所有文件路径必须使用绝对路径，以"{output_base_dir}/"为前缀
2. 确保所有输出文件名清晰且唯一，避免文件冲突
3. 文件将由执行环境直接创建在指定位置，路径必须准确

请将任务列表组织为JSON格式，每个任务包含上述所有字段。
"""
        
    def _build_plan_adjustment_prompt(self, task_summary):
        """
        构建计划调整提示
        
        参数:
            task_summary (dict): 任务执行摘要
        """
        # 提取任务ID和状态
        task_id = task_summary.get('task_id', 'unknown')
        success = task_summary.get('success', False)
        
        # 提取当前剩余计划
        remaining_tasks = [
            {
                'id': task['id'],
                'name': task.get('name', f"任务 {i+1}"),
                'description': task.get('description', ''),
                'dependencies': task.get('dependencies', [])
            }
            for i, task in enumerate(self.subtasks[self.current_index:])
        ]
        
        # 提取已完成任务
        completed_tasks = [
            {
                'id': task_id,
                'success': self.results[task_id].get('success', False)
            }
            for task_id in self.results.keys()
        ]
        
        # 序列化为JSON字符串
        remaining_tasks_json = json.dumps(remaining_tasks, ensure_ascii=False, indent=2)
        completed_tasks_json = json.dumps(completed_tasks, ensure_ascii=False, indent=2)
        task_summary_json = json.dumps(task_summary, ensure_ascii=False, indent=2)
        
        # 构建提示
        status = "失败" if not success else "成功"
        return f"""
评估任务执行结果，决定是否需要调整任务计划。

# 任务执行摘要
任务ID: {task_id}
执行状态: {status}

详细摘要:
```json
{task_summary_json}
```

# 已完成任务
```json
{completed_tasks_json}
```

# 剩余待执行任务
```json
{remaining_tasks_json}
```

# 评估要求
1. 分析任务 {task_id} 的执行结果，特别关注失败原因（如果有）
2. 考虑该结果对后续任务的影响
3. 确定是否需要调整任务计划，以下情况可能需要调整：
   - 当前任务失败，需要重试或替代方案
   - 发现新信息，需要添加额外任务
   - 任务顺序或依赖关系需要调整

# 可能的调整类型
1. 插入新任务：在特定位置添加新任务
2. 移除任务：删除不再需要的任务
3. 修改任务：调整现有任务的内容或依赖关系

请提供JSON格式的评估结果，包含以下字段：
- needs_adjustment：布尔值，表示是否需要调整
- reason：调整或不调整的原因
- insert_tasks：要插入的新任务列表（如果有）
- remove_tasks：要移除的任务ID列表（如果有）
- modify_tasks：要修改的任务列表（如果有）
"""
        
    def _build_integration_prompt(self):
        """构建结果整合提示"""
        # 创建任务结果摘要
        results_summary = []
        for task_id, result in self.results.items():
            # 查找对应的任务定义
            task_name = "未知任务"
            for task in self.subtasks:
                if task['id'] == task_id:
                    task_name = task.get('name', task_id)
                    break
                    
            # 添加结果摘要
            status = "成功" if result.get('success', False) else "失败"
            summary = result.get('result', {}).get('summary', '未提供摘要')
            results_summary.append(f"- {task_name} ({task_id}): {status} - {summary}")
        
        # 组合结果摘要
        results_summary_text = "\n".join(results_summary)
        
        return f"""
整合所有子任务的执行结果，生成最终的综合结果。

# 原始任务描述
{self.task_description}

# 子任务执行结果摘要
{results_summary_text}

# 整合要求
1. 综合所有成功完成的子任务结果
2. 考虑任何失败的子任务及其影响
3. 确保最终结果直接回应原始任务需求
4. 提供具体的成果和交付物
5. 包含任何限制或注意事项

请提供一个完整的最终结果报告，包含以下部分：
- 执行摘要：简要描述完成情况
- 主要成果：任务的关键成果和发现
- 工件列表：生成的所有代码、文档等
- 后续建议：可能的改进或扩展
- 限制说明：结果的任何限制或约束

结果必须以JSON格式呈现，便于后续处理。
"""
