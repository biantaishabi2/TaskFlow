#!/usr/bin/env python3
"""
任务拆分与执行系统 - 主系统模块
集成外层循环(规划者)和内层循环(执行者)，提供完整的任务分解与执行功能
"""

import os
import json
import logging
import time
from datetime import datetime
from task_planner.core.context_management import ContextManager
from task_planner.core.task_planner import TaskPlanner
from task_planner.core.task_executor import TaskExecutor
from ag2_wrapper.core.ag2_two_agent_executor import AG2TwoAgentExecutor
from task_planner.util.claude_task_bridge import TaskClaudeBridge, TaskLLMBridge
import asyncio

# 配置日志
logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'logs')
os.makedirs(logs_dir, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(logs_dir, 'task_decomposition.log'))
    ]
)
logger = logging.getLogger('task_decomposition_system')

class TaskDecompositionSystem:
    """任务拆分与执行系统主类，集成规划者和执行者"""
    
    def __init__(self, logs_dir="logs", use_claude=False):
        """
        初始化任务拆分与执行系统
        
        参数:
            logs_dir (str): 日志和上下文存储目录
            use_claude (bool): 是否使用Claude执行器，默认使用AG2
        """
        # 确保日志目录存在
        os.makedirs(logs_dir, exist_ok=True)
        self.logs_dir = logs_dir
        self.use_claude = use_claude
        
        # 初始化上下文管理器
        self.context_manager = ContextManager()
        
        # 初始化Claude桥接
        self.llm_bridge = TaskLLMBridge()
        self.claude_bridge = TaskClaudeBridge(llm_bridge=self.llm_bridge)
        
        logger.info(f"任务拆分与执行系统已初始化，使用{'Claude' if use_claude else 'AG2'}执行器")
        
    def execute_complex_task(self, task_description, save_results=True):
        """
        执行复杂任务
        
        参数:
            task_description (str): 任务描述
            save_results (bool): 是否保存结果到文件
            
        返回:
            dict: 最终执行结果
        """
        # 记录任务开始
        task_id = f"task_{int(time.time())}"
        logger.info(f"开始执行复杂任务 (ID: {task_id})")
        
        # 修复点：添加类型检查和转换
        if isinstance(task_description, dict):
            desc_str = task_description.get('description', '')
        else:
            desc_str = str(task_description)
        logger.info(f"任务描述: {desc_str[:100]}{'...' if len(desc_str) > 100 else ''}")
        
        # 创建上下文目录
        context_dir = os.path.join(self.logs_dir, task_id)
        os.makedirs(context_dir, exist_ok=True)
        
        # 初始化上下文管理器
        self.context_manager = ContextManager(context_dir=context_dir)
        
        # 创建规划者（外层循环）
        planner = TaskPlanner(
            task_description if isinstance(task_description, dict) else {'description': desc_str}, 
            context_manager=self.context_manager,
            logs_dir=context_dir
        )
        
        # 分析任务
        logger.info("正在分析任务...")
        analysis = planner.analyze_task()
        logger.info(f"任务分析完成: {analysis.get('result', {}).get('summary', '')[:100]}...")
        
        # 拆分任务
        logger.info("正在拆分任务...")
        subtasks = planner.break_down_task(analysis)
        logger.info(f"任务拆分完成，共{len(subtasks)}个子任务")
        
        # 根据配置创建执行者（内层循环）
        if self.use_claude:
            executor = TaskExecutor(
                context_manager=self.context_manager,
                claude_bridge=self.claude_bridge
            )
            logger.info("使用Claude执行器")
        else:
            executor = AG2TwoAgentExecutor(
                context_manager=self.context_manager
            )
            logger.info("使用AG2执行器")
        
        # 执行每个子任务
        execution_start_time = time.time()
        executed_tasks_count = 0
        
        logger.info("开始执行子任务...")
        while not planner.is_complete():
            # 获取下一个子任务
            subtask = planner.get_next_subtask()
            if not subtask:
                logger.info("没有更多子任务，执行完毕")
                break
                
            subtask_id = subtask['id']
            subtask_name = subtask.get('name', subtask_id)
            
            # 记录开始执行子任务
            logger.info(f"执行子任务 {executed_tasks_count+1}/{len(subtasks)}: {subtask_name} (ID: {subtask_id})")
            subtask_start_time = time.time()
            
            # 执行子任务
            result = executor.execute_subtask(subtask)
            
            # 记录子任务完成
            subtask_duration = time.time() - subtask_start_time
            success = result.get('success', False)
            status = "成功" if success else "失败"
            logger.info(f"子任务 {subtask_name} 执行{status}, 耗时: {subtask_duration:.2f}秒")
            
            # 处理结果
            planner.process_result(subtask_id, result)
            executed_tasks_count += 1
            
            # 保存当前进度
            if save_results:
                progress_file = os.path.join(context_dir, "progress.json")
                with open(progress_file, 'w', encoding='utf-8') as f:
                    progress_data = {
                        'task_id': task_id,
                        'task_description': task_description,
                        'subtasks_total': len(subtasks),
                        'subtasks_completed': executed_tasks_count,
                        'success_count': sum(1 for r in planner.results.values() if r.get('success', False)),
                        'start_time': execution_start_time,
                        'current_time': time.time(),
                        'elapsed_time': time.time() - execution_start_time
                    }
                    json.dump(progress_data, f, ensure_ascii=False, indent=2)
        
        # 计算总耗时
        execution_duration = time.time() - execution_start_time
        
        # 获取最终结果
        logger.info("正在生成最终结果...")
        final_result = planner.get_final_result()
        
        # 记录任务完成
        success = final_result.get('success', False)
        status = "成功" if success else "失败"
        logger.info(f"复杂任务执行{status}, 总耗时: {execution_duration:.2f}秒")
        logger.info(f"共执行了{executed_tasks_count}个子任务，"
                   f"成功: {sum(1 for r in planner.results.values() if r.get('success', False))}, "
                   f"失败: {sum(1 for r in planner.results.values() if not r.get('success', False))}")
        
        # 保存最终结果
        if save_results:
            result_file = os.path.join(context_dir, "final_result.json")
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(final_result, f, ensure_ascii=False, indent=2)
            
            # 保存执行摘要
            summary_file = os.path.join(context_dir, "execution_summary.json")
            with open(summary_file, 'w', encoding='utf-8') as f:
                summary_data = {
                    'task_id': task_id,
                    'task_description': task_description,
                    'execution_time': datetime.now().isoformat(),
                    'execution_duration': execution_duration,
                    'subtasks_total': len(subtasks),
                    'subtasks_executed': executed_tasks_count,
                    'success_count': sum(1 for r in planner.results.values() if r.get('success', False)),
                    'failure_count': sum(1 for r in planner.results.values() if not r.get('success', False)),
                    'final_status': status,
                    'result_summary': final_result.get('result', {}).get('summary', '没有结果摘要')
                }
                json.dump(summary_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"结果已保存到: {context_dir}")
        
        return final_result
    
    def load_and_resume_task(self, task_id):
        """
        加载并恢复之前的任务
        
        参数:
            task_id (str): 任务ID
            
        返回:
            dict: 恢复执行后的最终结果
        """
        # 构建上下文目录路径
        context_dir = os.path.join(self.logs_dir, task_id)
        
        # 检查目录是否存在
        if not os.path.exists(context_dir):
            logger.error(f"任务 {task_id} 的上下文目录不存在: {context_dir}")
            return {
                'success': False,
                'error': f"任务 {task_id} 不存在或上下文已丢失"
            }
        
        logger.info(f"正在加载任务 {task_id} 的上下文...")
        
        # 初始化上下文管理器并加载上下文
        self.context_manager = ContextManager(context_dir=context_dir)
        self.context_manager.load_all_contexts()
        
        # 获取任务描述
        planner_context = self.context_manager.task_contexts.get('planner')
        if not planner_context:
            logger.error(f"任务 {task_id} 的规划者上下文不存在")
            return {
                'success': False,
                'error': f"任务 {task_id} 的规划者上下文不存在，无法恢复任务"
            }
            
        task_description = planner_context.local_context.get('task_description')
        if not task_description:
            # 尝试从执行记录中获取
            for record in planner_context.execution_history:
                if record['action'] == 'task_created' and 'metadata' in record:
                    task_description = record['metadata'].get('full_description')
                    if task_description:
                        break
                        
            if not task_description:
                logger.error(f"无法获取任务 {task_id} 的描述")
                return {
                    'success': False,
                    'error': f"无法获取任务 {task_id} 的描述，无法恢复任务"
                }
        
        logger.info(f"正在恢复任务: {task_description[:100]}{'...' if len(task_description) > 100 else ''}")
        
        # 重新创建规划者和执行者
        planner = TaskPlanner(
            task_description if isinstance(task_description, dict) else {'description': task_description}, 
            context_manager=self.context_manager,
            logs_dir=context_dir
        )
        
        executor = TaskExecutor(
            claude_bridge=self.claude_bridge,
            context_manager=self.context_manager
        )
        
        # 重新加载任务状态
        subtasks = planner_context.local_context.get('subtasks', [])
        if not subtasks:
            logger.error(f"无法获取任务 {task_id} 的子任务列表")
            return {
                'success': False,
                'error': f"无法获取任务 {task_id} 的子任务列表，无法恢复任务"
            }
            
        # 设置规划者状态
        planner.subtasks = subtasks
        
        # 重新加载已完成任务的结果
        for task_id, context in self.context_manager.task_contexts.items():
            if task_id == 'planner':
                continue
                
            if 'result' in context.local_context:
                planner.results[task_id] = context.local_context['result']
                
        # 计算当前索引
        executed_task_ids = set(planner.results.keys())
        current_index = 0
        for i, task in enumerate(subtasks):
            if task['id'] in executed_task_ids:
                current_index = i + 1
                
        planner.current_index = current_index
        
        logger.info(f"任务状态已恢复: 共{len(subtasks)}个子任务，已完成{len(planner.results)}个，当前索引: {current_index}")
        
        # 继续执行任务
        return self.continue_execution(planner, executor, task_id, task_description)
    
    def continue_execution(self, planner, executor, task_id, task_description):
        """
        继续执行任务
        
        参数:
            planner (TaskPlanner): 规划者实例
            executor (TaskExecutor): 执行者实例
            task_id (str): 任务ID
            task_description (str): 任务描述
            
        返回:
            dict: 最终执行结果
        """
        # 获取上下文目录
        context_dir = self.context_manager.context_dir
        
        # 执行剩余子任务
        execution_start_time = time.time()
        executed_tasks_count = len(planner.results)
        total_tasks = len(planner.subtasks)
        
        logger.info(f"继续执行剩余子任务: {total_tasks - executed_tasks_count}个")
        
        while not planner.is_complete():
            # 获取下一个子任务
            subtask = planner.get_next_subtask()
            if not subtask:
                logger.info("没有更多子任务，执行完毕")
                break
                
            subtask_id = subtask['id']
            subtask_name = subtask.get('name', subtask_id)
            
            # 记录开始执行子任务
            logger.info(f"执行子任务 {executed_tasks_count+1}/{total_tasks}: {subtask_name} (ID: {subtask_id})")
            subtask_start_time = time.time()
            
            # 执行子任务
            result = executor.execute_subtask(subtask)
            
            # 记录子任务完成
            subtask_duration = time.time() - subtask_start_time
            success = result.get('success', False)
            status = "成功" if success else "失败"
            logger.info(f"子任务 {subtask_name} 执行{status}, 耗时: {subtask_duration:.2f}秒")
            
            # 处理结果
            planner.process_result(subtask_id, result)
            executed_tasks_count += 1
            
            # 保存当前进度
            progress_file = os.path.join(context_dir, "progress.json")
            with open(progress_file, 'w', encoding='utf-8') as f:
                progress_data = {
                    'task_id': task_id,
                    'task_description': task_description,
                    'subtasks_total': total_tasks,
                    'subtasks_completed': executed_tasks_count,
                    'success_count': sum(1 for r in planner.results.values() if r.get('success', False)),
                    'resumed_at': execution_start_time,
                    'current_time': time.time(),
                    'elapsed_since_resume': time.time() - execution_start_time
                }
                json.dump(progress_data, f, ensure_ascii=False, indent=2)
            
        # 计算总耗时
        execution_duration = time.time() - execution_start_time
        
        # 获取最终结果
        logger.info("正在生成最终结果...")
        final_result = planner.get_final_result()
        
        # 记录任务完成
        success = final_result.get('success', False)
        status = "成功" if success else "失败"
        logger.info(f"复杂任务执行{status}, 自恢复以来耗时: {execution_duration:.2f}秒")
        logger.info(f"共执行了{executed_tasks_count}个子任务，"
                   f"成功: {sum(1 for r in planner.results.values() if r.get('success', False))}, "
                   f"失败: {sum(1 for r in planner.results.values() if not r.get('success', False))}")
        
        # 保存最终结果
        result_file = os.path.join(context_dir, "final_result.json")
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(final_result, f, ensure_ascii=False, indent=2)
        
        # 保存执行摘要
        summary_file = os.path.join(context_dir, "execution_summary.json")
        with open(summary_file, 'w', encoding='utf-8') as f:
            summary_data = {
                'task_id': task_id,
                'task_description': task_description,
                'resumed': True,
                'resume_time': datetime.now().isoformat(),
                'execution_duration_since_resume': execution_duration,
                'subtasks_total': total_tasks,
                'subtasks_executed': executed_tasks_count,
                'success_count': sum(1 for r in planner.results.values() if r.get('success', False)),
                'failure_count': sum(1 for r in planner.results.values() if not r.get('success', False)),
                'final_status': status,
                'result_summary': final_result.get('result', {}).get('summary', '没有结果摘要')
            }
            json.dump(summary_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"结果已保存到: {context_dir}")
        
        return final_result

    def execute_predefined_subtasks(self, subtasks, save_results=True):
        """
        直接执行预定义子任务（跳过分析和拆分阶段）
        
        参数:
            subtasks (list): 预定义子任务列表
            save_results (bool): 是否保存结果到文件
            
        返回:
            dict: 最终执行结果
        """
        # 创建任务上下文
        task_id = f"predefined_task_{int(time.time())}"
        context_dir = os.path.join(self.logs_dir, task_id)
        os.makedirs(context_dir, exist_ok=True)
        
        logger.info("==================================================")
        logger.info("直接执行预定义子任务模式")
        logger.info("==================================================")
        logger.info(f"从文件加载了 {len(subtasks)} 个子任务")
        
        # 初始化上下文管理器
        self.context_manager = ContextManager(context_dir=context_dir)
        
        # 为每个子任务创建上下文
        for subtask in subtasks:
            subtask_id = subtask.get('id', f"task_{int(time.time())}")
            self.context_manager.create_subtask_context('root', subtask_id)
            self.context_manager.update_task_context(subtask_id, {
                'task_definition': subtask
            })
        
        # 直接创建规划者并注入子任务（跳过分析阶段）
        planner = TaskPlanner(
            task_description="预定义子任务执行",
            context_manager=self.context_manager,
            logs_dir=context_dir,
            skip_analysis=True  # 新增跳过分析标志
        )
        
        # 修改后的子任务设置逻辑
        planner.subtasks = self._normalize_subtasks(subtasks)
        planner.current_index = 0
        planner.results = {}
        
        # 根据配置创建执行者（内层循环）
        executor = AG2TwoAgentExecutor(
            context_manager=self.context_manager
        ) if not self.use_claude else TaskExecutor(
            context_manager=self.context_manager,
            claude_bridge=self.claude_bridge
        )
        logger.info(f"使用{'AG2' if not self.use_claude else 'Claude'}执行器")
        
        # 开始执行预定义子任务
        logger.info("开始执行预定义子任务...")
        
        # 执行每个子任务
        execution_start_time = time.time()
        executed_tasks_count = 0
        success_count = 0
        failure_count = 0
        
        for subtask in subtasks:
            subtask_id = subtask.get('id', f"task_{int(time.time())}")
            subtask_name = subtask.get('name', subtask_id)
            
            # 记录开始执行子任务
            logger.info(f"执行子任务 {executed_tasks_count+1}/{len(subtasks)}: {subtask_name} (ID: {subtask_id})")
            subtask_start_time = time.time()
            
            # 执行子任务
            result = executor.execute_subtask(subtask)
            
            # 记录子任务完成
            subtask_duration = time.time() - subtask_start_time
            success = result.get('success', False)
            status = "成功" if success else "失败"
            logger.info(f"子任务 {subtask_name} 执行{status}, 耗时: {subtask_duration:.2f}秒")
            
            # 更新统计信息
            if success:
                success_count += 1
            else:
                failure_count += 1
                
            # 保存结果
            planner.results[subtask_id] = result
            executed_tasks_count += 1
            
        # 计算总执行时间
        total_execution_time = time.time() - execution_start_time
        
        # 构建最终结果
        final_result = {
            'success': failure_count == 0,  # 只有当所有任务都成功时才算成功
            'success_count': success_count,
            'failure_count': failure_count,
            'total_tasks': len(subtasks),
            'execution_time': total_execution_time,
            'results': planner.results
        }
        
        # 保存结果
        if save_results:
            results_file = os.path.join(context_dir, 'execution_results.json')
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(final_result, f, ensure_ascii=False, indent=2)
                
            logger.info(f"结果已保存到: {results_file}")
            
        return final_result

    def _normalize_subtasks(self, subtasks):
        """确保子任务格式标准化"""
        normalized = []
        for task in subtasks:
            # 确保必需字段存在
            if 'id' not in task:
                task['id'] = f"subtask_{len(normalized)+1}"
            if 'name' not in task:
                task['name'] = task['id']
            if 'dependencies' not in task:
                task['dependencies'] = []
            normalized.append(task)
        return normalized


# CLI入口点
if __name__ == "__main__":
    import argparse
    
    # 主解析器
    parser = argparse.ArgumentParser(description="任务拆分与执行系统")
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # run-subtasks 子命令
    run_subtasks_parser = subparsers.add_parser('run-subtasks', help='执行预定义子任务')
    run_subtasks_parser.add_argument("file", help="子任务文件路径")
    run_subtasks_parser.add_argument("--logs-dir", default="logs", help="日志存储目录")
    run_subtasks_parser.add_argument("--save-results", action="store_true", default=True, help="保存结果到文件")
    
    # 常规任务命令
    task_parser = subparsers.add_parser('run-task', help='执行新任务')
    task_parser.add_argument("task", help="任务描述或任务文件路径")
    task_parser.add_argument("--file", action="store_true", help="指示任务参数是文件路径")
    task_parser.add_argument("--logs-dir", default="logs", help="日志存储目录")
    task_parser.add_argument("--save-results", action="store_true", default=True, help="保存结果到文件")
    
    # 恢复任务命令
    resume_parser = subparsers.add_parser('resume', help='恢复已存在的任务')
    resume_parser.add_argument("task_id", help="要恢复的任务ID")
    resume_parser.add_argument("--logs-dir", default="logs", help="日志存储目录")
    
    args = parser.parse_args()
    
    # 根据子命令处理逻辑
    if args.command == 'run-subtasks':
        logger.info("==================================================")
        logger.info("直接执行预定义子任务模式")
        logger.info("==================================================")
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                subtasks = json.load(f)
                logger.info(f"从文件加载了 {len(subtasks)} 个子任务")
                
                system = TaskDecompositionSystem(logs_dir=args.logs_dir)
                final_result = system.execute_predefined_subtasks(
                    subtasks, 
                    save_results=args.save_results
                )
                
                # 直接输出结果摘要
                print("\n执行结果摘要:")
                print(f"总子任务数: {len(subtasks)}")
                print(f"成功: {final_result['success_count']}")
                print(f"失败: {final_result['failure_count']}")
                print(f"最终状态: {'成功' if final_result['success'] else '失败'}")
                
                exit(0)
        except Exception as e:
            logger.error(f"子任务执行失败: {str(e)}")
            exit(1)
            
    elif args.command == 'run-task':
        # 处理常规任务...
        # ...保持原有逻辑...
        pass
        
    elif args.command == 'resume':
        # 处理恢复任务...
        # ...保持原有逻辑...
        pass
        
    else:
        parser.print_help()
        exit(1)