#!/usr/bin/env python3
"""
任务拆分与执行系统 - 并行版主系统模块
扩展主系统，支持并行执行无依赖任务，提高执行效率
"""

import os
import json
import logging
import time
import threading
from datetime import datetime
from src.core.context_management import ContextManager
from src.core.task_planner import TaskPlanner
from src.distributed.parallel_task_executor import ParallelTaskExecutor, DependencyGraph
from src.util.claude_task_bridge import TaskClaudeBridge, TaskLLMBridge

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('parallel_task_decomposition.log')
    ]
)
logger = logging.getLogger('parallel_task_decomposition_system')

class ParallelTaskDecompositionSystem:
    """并行任务拆分与执行系统主类，支持并行执行无依赖任务"""
    
    def __init__(self, logs_dir="logs", max_workers=4):
        """
        初始化并行任务拆分与执行系统
        
        参数:
            logs_dir (str): 日志和上下文存储目录
            max_workers (int): 最大并行工作线程数
        """
        # 确保日志目录存在
        os.makedirs(logs_dir, exist_ok=True)
        self.logs_dir = logs_dir
        self.max_workers = max_workers
        
        # 初始化上下文管理器
        self.context_manager = ContextManager()
        
        # 初始化Claude桥接
        self.llm_bridge = TaskLLMBridge()
        self.claude_bridge = TaskClaudeBridge(llm_bridge=self.llm_bridge)
        
        # 初始化任务执行统计信息
        self.stats = {
            'sequential_time': 0,  # 顺序执行模式预估时间
            'parallel_time': 0,    # 并行执行实际时间
            'speedup': 0,          # 加速比
            'efficiency': 0        # 并行效率
        }
        
        # 执行效率监控
        self.monitor_data = []
        
        logger.info(f"并行任务拆分与执行系统已初始化，最大工作线程数: {max_workers}")
        
    def execute_complex_task(self, task_description, save_results=True, parallel_threshold=2):
        """
        执行复杂任务
        
        参数:
            task_description (str): 任务描述
            save_results (bool): 是否保存结果到文件
            parallel_threshold (int): 并行执行触发阈值（批次中任务数超过此值才并行）
            
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
        
        # 创建并行执行者（内层循环）
        executor = ParallelTaskExecutor(
            claude_bridge=self.claude_bridge,
            context_manager=self.context_manager,
            max_workers=self.max_workers
        )
        
        # 开始监控执行效率
        monitor_thread = threading.Thread(target=self._monitor_execution, args=(task_id,))
        monitor_thread.daemon = True
        monitor_thread.start()
        
        # 分析依赖关系
        dependency_graph = DependencyGraph(subtasks)
        execution_batches = dependency_graph.get_execution_batches()
        logger.info(f"任务依赖分析完成，共分为 {len(execution_batches)} 个执行批次")
        
        # 记录关键路径，用于性能分析
        critical_path = dependency_graph.get_critical_path()
        logger.info(f"关键路径包含 {len(critical_path)} 个任务: {critical_path}")
        
        # 执行每个批次的任务
        execution_start_time = time.time()
        executed_tasks_count = 0
        all_results = {}
        
        logger.info("开始执行子任务...")
        for i, batch in enumerate(execution_batches):
            batch_size = len(batch)
            use_parallel = batch_size >= parallel_threshold
            
            # 记录批次开始
            batch_start_time = time.time()
            logger.info(f"执行批次 {i+1}/{len(execution_batches)}, 包含 {batch_size} 个任务")
            logger.info(f"执行模式: {'并行' if use_parallel else '顺序'}")
            
            # 根据批次大小决定是否并行执行
            if use_parallel:
                # 并行执行当前批次
                batch_results = executor.execute_parallel_subtasks(batch)
            else:
                # 顺序执行当前批次
                batch_results = {}
                for subtask in batch:
                    subtask_id = subtask['id']
                    result = executor.execute_subtask(subtask)
                    batch_results[subtask_id] = result
            
            # 将批次结果合并到总结果
            all_results.update(batch_results)
            executed_tasks_count += batch_size
            
            # 记录批次完成
            batch_duration = time.time() - batch_start_time
            success_count = sum(1 for r in batch_results.values() if r.get('success', False))
            logger.info(f"批次 {i+1} 执行完成, 耗时: {batch_duration:.2f}秒, 成功: {success_count}/{batch_size}")
            
            # 更新任务状态
            for subtask_id, result in batch_results.items():
                planner.process_result(subtask_id, result)
                
            # 保存当前进度
            if save_results:
                progress_file = os.path.join(context_dir, "progress.json")
                with open(progress_file, 'w', encoding='utf-8') as f:
                    progress_data = {
                        'task_id': task_id,
                        'task_description': task_description,
                        'subtasks_total': len(subtasks),
                        'subtasks_completed': executed_tasks_count,
                        'success_count': sum(1 for r in all_results.values() if r.get('success', False)),
                        'start_time': execution_start_time,
                        'current_time': time.time(),
                        'elapsed_time': time.time() - execution_start_time,
                        'batches_completed': i + 1,
                        'batches_total': len(execution_batches)
                    }
                    json.dump(progress_data, f, ensure_ascii=False, indent=2)
        
        # 计算总耗时
        execution_duration = time.time() - execution_start_time
        
        # 计算顺序执行时间（理论值）
        sequential_time = sum(
            sum(task.get('estimated_duration', 1) for task in batch)
            for batch in execution_batches
        )
        
        # 计算加速比和效率
        self.stats['sequential_time'] = sequential_time
        self.stats['parallel_time'] = execution_duration
        self.stats['speedup'] = sequential_time / execution_duration if execution_duration > 0 else 0
        self.stats['efficiency'] = self.stats['speedup'] / self.max_workers
        
        # 获取最终结果
        logger.info("正在生成最终结果...")
        final_result = planner.get_final_result()
        
        # 添加执行统计信息到结果
        if 'stats' not in final_result:
            final_result['stats'] = {}
        final_result['stats'].update(self.stats)
        
        # 记录任务完成
        success = final_result.get('success', False)
        status = "成功" if success else "失败"
        logger.info(f"复杂任务执行{status}, 总耗时: {execution_duration:.2f}秒")
        logger.info(f"并行加速比: {self.stats['speedup']:.2f}x, 效率: {self.stats['efficiency']:.2f}")
        logger.info(f"共执行了{executed_tasks_count}个子任务，"
                   f"成功: {sum(1 for r in all_results.values() if r.get('success', False))}, "
                   f"失败: {sum(1 for r in all_results.values() if not r.get('success', False))}")
        
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
                    'parallel_speedup': self.stats['speedup'],
                    'parallel_efficiency': self.stats['efficiency'],
                    'subtasks_total': len(subtasks),
                    'subtasks_executed': executed_tasks_count,
                    'success_count': sum(1 for r in all_results.values() if r.get('success', False)),
                    'failure_count': sum(1 for r in all_results.values() if not r.get('success', False)),
                    'batches_count': len(execution_batches),
                    'critical_path': critical_path,
                    'final_status': status,
                    'result_summary': final_result.get('result', {}).get('summary', '没有结果摘要')
                }
                json.dump(summary_data, f, ensure_ascii=False, indent=2)
            
            # 保存执行监控数据
            monitor_file = os.path.join(context_dir, "execution_monitor.json")
            with open(monitor_file, 'w', encoding='utf-8') as f:
                json.dump(self.monitor_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"结果已保存到: {context_dir}")
        
        return final_result
    
    def _monitor_execution(self, task_id, interval=5):
        """
        监控执行效率
        
        参数:
            task_id (str): 任务ID
            interval (int): 监控间隔（秒）
        """
        start_time = time.time()
        while True:
            # 收集当前状态
            current_time = time.time()
            elapsed = current_time - start_time
            
            # 获取当前内存使用情况
            try:
                import psutil
                process = psutil.Process(os.getpid())
                memory_info = process.memory_info()
                memory_mb = memory_info.rss / 1024 / 1024
            except:
                memory_mb = 0
                
            # 记录状态
            status = {
                'timestamp': current_time,
                'elapsed_seconds': elapsed,
                'memory_mb': memory_mb,
                'active_contexts': len(self.context_manager.task_contexts) if hasattr(self, 'context_manager') else 0
            }
            self.monitor_data.append(status)
            
            # 暂停
            time.sleep(interval)
    
    def load_and_resume_task(self, task_id, parallel_threshold=2):
        """
        加载并恢复之前的任务
        
        参数:
            task_id (str): 任务ID
            parallel_threshold (int): 并行执行触发阈值
            
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
        
        executor = ParallelTaskExecutor(
            claude_bridge=self.claude_bridge,
            context_manager=self.context_manager,
            max_workers=self.max_workers
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
        
        # 分析剩余任务的依赖关系
        remaining_tasks = subtasks[current_index:]
        dependency_graph = DependencyGraph(remaining_tasks)
        execution_batches = dependency_graph.get_execution_batches()
        
        logger.info(f"任务状态已恢复: 共{len(subtasks)}个子任务，已完成{len(planner.results)}个，"
                  f"剩余{len(remaining_tasks)}个，分为{len(execution_batches)}个执行批次")
        
        # 继续执行任务
        execution_start_time = time.time()
        executed_tasks_count = len(planner.results)
        all_results = planner.results.copy()
        
        logger.info(f"继续执行剩余子任务: {len(remaining_tasks)}个")
        for i, batch in enumerate(execution_batches):
            batch_size = len(batch)
            use_parallel = batch_size >= parallel_threshold
            
            # 记录批次开始
            batch_start_time = time.time()
            logger.info(f"执行批次 {i+1}/{len(execution_batches)}, 包含 {batch_size} 个任务")
            logger.info(f"执行模式: {'并行' if use_parallel else '顺序'}")
            
            # 根据批次大小决定是否并行执行
            if use_parallel:
                # 并行执行当前批次
                batch_results = executor.execute_parallel_subtasks(batch)
            else:
                # 顺序执行当前批次
                batch_results = {}
                for subtask in batch:
                    subtask_id = subtask['id']
                    result = executor.execute_subtask(subtask)
                    batch_results[subtask_id] = result
            
            # 将批次结果合并到总结果
            all_results.update(batch_results)
            executed_tasks_count += batch_size
            
            # 记录批次完成
            batch_duration = time.time() - batch_start_time
            success_count = sum(1 for r in batch_results.values() if r.get('success', False))
            logger.info(f"批次 {i+1} 执行完成, 耗时: {batch_duration:.2f}秒, 成功: {success_count}/{batch_size}")
            
            # 更新任务状态
            for subtask_id, result in batch_results.items():
                planner.process_result(subtask_id, result)
                
            # 保存当前进度
            progress_file = os.path.join(context_dir, "progress.json")
            with open(progress_file, 'w', encoding='utf-8') as f:
                progress_data = {
                    'task_id': task_id,
                    'task_description': task_description,
                    'subtasks_total': len(subtasks),
                    'subtasks_completed': executed_tasks_count,
                    'success_count': sum(1 for r in all_results.values() if r.get('success', False)),
                    'resumed_at': execution_start_time,
                    'current_time': time.time(),
                    'elapsed_since_resume': time.time() - execution_start_time,
                    'batches_completed': i + 1,
                    'batches_total': len(execution_batches)
                }
                json.dump(progress_data, f, ensure_ascii=False, indent=2)
        
        # 计算恢复执行耗时
        execution_duration = time.time() - execution_start_time
        
        # 获取最终结果
        logger.info("正在生成最终结果...")
        final_result = planner.get_final_result()
        
        # 记录任务完成
        success = final_result.get('success', False)
        status = "成功" if success else "失败"
        logger.info(f"复杂任务执行{status}, 自恢复以来耗时: {execution_duration:.2f}秒")
        logger.info(f"共执行了{executed_tasks_count}个子任务，"
                   f"成功: {sum(1 for r in all_results.values() if r.get('success', False))}, "
                   f"失败: {sum(1 for r in all_results.values() if not r.get('success', False))}")
        
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
                'subtasks_total': len(subtasks),
                'subtasks_executed': executed_tasks_count,
                'success_count': sum(1 for r in all_results.values() if r.get('success', False)),
                'failure_count': sum(1 for r in all_results.values() if not r.get('success', False)),
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
    parser = argparse.ArgumentParser(description="并行任务拆分与执行系统")
    parser.add_argument("task", nargs="?", help="任务描述或任务文件路径")
    parser.add_argument("--logs-dir", default="logs", help="日志和上下文存储目录")
    parser.add_argument("--resume", help="恢复之前的任务ID")
    parser.add_argument("--file", action="store_true", help="指示任务参数是文件路径")
    parser.add_argument("--max-workers", type=int, default=4, help="最大并行工作线程数")
    parser.add_argument("--parallel-threshold", type=int, default=2, help="触发并行执行的最小任务数量")
    parser.add_argument("--save-results", action="store_true", default=True, help="保存结果到文件")
    
    args = parser.parse_args()
    
    # 初始化系统
    system = ParallelTaskDecompositionSystem(logs_dir=args.logs_dir, max_workers=args.max_workers)
    
    # 执行或恢复任务
    if args.resume:
        # 恢复任务
        logger.info(f"正在恢复任务: {args.resume}")
        result = system.load_and_resume_task(
            args.resume, 
            parallel_threshold=args.parallel_threshold
        )
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
        result = system.execute_complex_task(
            task_description, 
            save_results=args.save_results,
            parallel_threshold=args.parallel_threshold
        )
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
        
        # 输出并行执行统计
        if 'stats' in result:
            stats = result['stats']
            print("\n并行执行统计:")
            print(f"并行加速比: {stats.get('speedup', 0):.2f}x")
            print(f"并行效率: {stats.get('efficiency', 0):.2f}")
            if stats.get('sequential_time', 0) > 0 and stats.get('parallel_time', 0) > 0:
                time_saved = stats['sequential_time'] - stats['parallel_time']
                print(f"节省时间: {time_saved:.2f}秒 ({time_saved/stats['sequential_time']*100:.1f}%)")
            
        print("="*80)