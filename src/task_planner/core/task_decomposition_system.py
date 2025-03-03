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
from task_planner.util.claude_task_bridge import TaskClaudeBridge, TaskLLMBridge

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
    
    def __init__(self, logs_dir="logs"):
        """
        初始化任务拆分与执行系统
        
        参数:
            logs_dir (str): 日志和上下文存储目录
        """
        # 确保日志目录存在
        os.makedirs(logs_dir, exist_ok=True)
        self.logs_dir = logs_dir
        
        # 初始化上下文管理器
        self.context_manager = ContextManager()
        
        # 初始化Claude桥接
        self.llm_bridge = TaskLLMBridge()
        self.claude_bridge = TaskClaudeBridge(llm_bridge=self.llm_bridge)
        
        logger.info("任务拆分与执行系统已初始化")
        
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
        logger.info(f"任务描述: {task_description[:100]}{'...' if len(task_description) > 100 else ''}")
        
        # 创建上下文目录
        context_dir = os.path.join(self.logs_dir, task_id)
        os.makedirs(context_dir, exist_ok=True)
        
        # 初始化上下文管理器
        self.context_manager = ContextManager(context_dir=context_dir)
        
        # 创建规划者（外层循环）
        planner = TaskPlanner(
            task_description, 
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
        
        # 创建执行者（内层循环）
        executor = TaskExecutor(
            context_manager=self.context_manager
        )
        
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
            task_description, 
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


# CLI入口点
if __name__ == "__main__":
    import argparse
    
    # 命令行参数
    parser = argparse.ArgumentParser(description="任务拆分与执行系统")
    parser.add_argument("task", nargs="?", help="任务描述或任务文件路径")
    parser.add_argument("--logs-dir", default="logs", help="日志和上下文存储目录")
    parser.add_argument("--resume", help="恢复之前的任务ID")
    parser.add_argument("--file", action="store_true", help="指示任务参数是文件路径")
    parser.add_argument("--save-results", action="store_true", default=True, help="保存结果到文件")
    
    args = parser.parse_args()
    
    # 初始化系统
    system = TaskDecompositionSystem(logs_dir=args.logs_dir)
    
    # 执行或恢复任务
    if args.resume:
        # 恢复任务
        logger.info(f"正在恢复任务: {args.resume}")
        result = system.load_and_resume_task(args.resume)
    elif args.task:
        # 执行新任务
        if args.file:
            # 从文件读取任务
            try:
                with open(args.task, 'r', encoding='utf-8') as f:
                    task_description = f.read()
            except Exception as e:
                logger.error(f"无法读取任务文件: {str(e)}")
                task_description = args.task
        else:
            # 直接使用命令行任务
            task_description = args.task
            
        logger.info("开始执行新任务")
        result = system.execute_complex_task(task_description, save_results=args.save_results)
    else:
        parser.print_help()
        exit(1)
    
    # 输出结果摘要
    if result:
        success = result.get('success', False)
        status = "成功" if success else "失败"
        summary = result.get('result', {}).get('summary', '没有结果摘要')
        
        print("\n" + "="*80)
        print(f"任务执行{status}")
        print(f"结果摘要: {summary}")
        print("="*80)
    else:
        print("\n任务执行失败，未返回有效结果")