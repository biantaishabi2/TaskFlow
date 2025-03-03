#!/usr/bin/env python3
"""
任务拆分与执行系统 - 并行任务执行模块
扩展任务执行功能，支持无依赖任务的并行执行
"""

import json
import re
import time
import logging
import os
import concurrent.futures
from datetime import datetime
from claude_task_bridge import TaskClaudeBridge, TaskLLMBridge
from context_management import TaskContext, ContextManager
from task_executor import TaskExecutor

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('parallel_task_executor')

class ParallelTaskExecutor(TaskExecutor):
    """
    并行任务执行器，扩展TaskExecutor支持并行执行能力
    """
    
    def __init__(self, claude_bridge=None, context_manager=None, max_workers=4):
        """
        初始化并行任务执行器
        
        参数:
            claude_bridge (TaskClaudeBridge, optional): Claude任务桥接
            context_manager (ContextManager, optional): 上下文管理器实例
            max_workers (int): 最大并行工作线程数
        """
        super().__init__(claude_bridge, context_manager)
        self.max_workers = max_workers
        logger.info(f"并行任务执行器已初始化，最大工作线程数: {max_workers}")
        
    def execute_parallel_subtasks(self, subtasks, task_contexts=None):
        """
        并行执行多个子任务
        
        参数:
            subtasks (list): 子任务列表
            task_contexts (dict, optional): 任务上下文字典 {task_id: TaskContext}
            
        返回:
            dict: {task_id: result} 形式的执行结果字典
        """
        if not subtasks:
            return {}
            
        logger.info(f"开始并行执行 {len(subtasks)} 个子任务，最大并行数: {self.max_workers}")
        
        # 准备任务上下文
        if task_contexts is None:
            task_contexts = {}
        
        # 并行执行任务
        results = {}
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 创建未来任务字典
            future_to_task = {}
            
            for subtask in subtasks:
                task_id = subtask['id']
                # 获取或创建任务上下文
                task_context = task_contexts.get(task_id)
                
                # 提交任务到线程池
                future = executor.submit(self.execute_subtask, subtask, task_context)
                future_to_task[future] = task_id
                logger.info(f"任务 {task_id} 已提交到线程池")
            
            # 收集执行结果
            for future in concurrent.futures.as_completed(future_to_task):
                task_id = future_to_task[future]
                try:
                    result = future.result()
                    results[task_id] = result
                    success = result.get('success', False)
                    status = "成功" if success else "失败"
                    logger.info(f"任务 {task_id} 执行{status}")
                except Exception as e:
                    logger.error(f"任务 {task_id} 执行异常: {str(e)}")
                    # 构造错误结果
                    results[task_id] = {
                        'task_id': task_id,
                        'success': False,
                        'error': str(e),
                        'result': {
                            'summary': f"任务执行异常: {str(e)}",
                            'details': f"并行执行任务 {task_id} 时发生异常"
                        }
                    }
        
        execution_time = time.time() - start_time
        success_count = sum(1 for r in results.values() if r.get('success', False))
        logger.info(f"并行执行完成，总耗时: {execution_time:.2f}秒, 成功: {success_count}/{len(subtasks)}")
        
        return results
    
    def analyze_dependencies(self, subtasks):
        """
        分析任务依赖关系，将任务分组为可并行执行的批次
        
        参数:
            subtasks (list): 子任务列表
            
        返回:
            list: 任务批次列表，每个批次包含可并行执行的任务
        """
        if not subtasks:
            return []
        
        # 构建任务ID到任务的映射
        task_map = {task['id']: task for task in subtasks}
        
        # 构建依赖图（邻接表）
        dependency_graph = {}
        for task in subtasks:
            task_id = task['id']
            dependency_graph[task_id] = task.get('dependencies', [])
        
        # 计算任务的入度（依赖数）
        in_degree = {task_id: 0 for task_id in task_map}
        for task_id, deps in dependency_graph.items():
            for dep in deps:
                if dep in in_degree:
                    in_degree[dep] += 1
        
        # 创建任务批次
        batches = []
        remaining_tasks = set(task_map.keys())
        
        while remaining_tasks:
            # 找出当前没有依赖的任务
            current_batch = [
                task_id for task_id in remaining_tasks
                if all(dep not in remaining_tasks for dep in dependency_graph[task_id])
            ]
            
            if not current_batch:
                # 检测到循环依赖
                logger.warning("检测到循环依赖，将剩余任务作为一个批次")
                current_batch = list(remaining_tasks)
            
            # 添加当前批次并从剩余任务中移除
            batches.append([task_map[task_id] for task_id in current_batch])
            remaining_tasks -= set(current_batch)
        
        logger.info(f"任务依赖分析完成，共分为 {len(batches)} 个执行批次")
        for i, batch in enumerate(batches):
            logger.info(f"批次 {i+1}: {[task['id'] for task in batch]}")
            
        return batches
    
    def batch_execute_subtasks(self, subtasks, update_context=True):
        """
        按批次并行执行任务
        
        参数:
            subtasks (list): 子任务列表
            update_context (bool): 是否在每个批次后更新上下文
            
        返回:
            dict: {task_id: result} 形式的执行结果字典
        """
        # 分析依赖，创建批次
        batches = self.analyze_dependencies(subtasks)
        
        # 存储所有结果
        all_results = {}
        
        # 按批次执行任务
        for i, batch in enumerate(batches):
            logger.info(f"执行批次 {i+1}/{len(batches)}, 包含 {len(batch)} 个任务")
            
            # 获取每个任务的上下文
            task_contexts = {}
            if self.context_manager:
                for task in batch:
                    task_id = task['id']
                    if task_id in self.context_manager.task_contexts:
                        task_contexts[task_id] = self.context_manager.task_contexts[task_id]
            
            # 并行执行当前批次任务
            batch_results = self.execute_parallel_subtasks(batch, task_contexts)
            
            # 合并结果
            all_results.update(batch_results)
            
            # 如果需要，更新上下文（为下一批次做准备）
            if update_context and self.context_manager and i < len(batches) - 1:
                # 找出下一批次中有依赖关系的任务
                next_batch = batches[i+1]
                for next_task in next_batch:
                    next_task_id = next_task['id']
                    dependencies = next_task.get('dependencies', [])
                    
                    # 传播依赖任务的结果
                    for dep_id in dependencies:
                        if dep_id in all_results and dep_id in self.context_manager.task_contexts:
                            # 只传播已完成的依赖任务的结果
                            if next_task_id in self.context_manager.task_contexts:
                                logger.info(f"传播任务 {dep_id} 的结果到任务 {next_task_id}")
                                self.context_manager.propagate_results(dep_id, [next_task_id])
        
        return all_results


class DependencyGraph:
    """
    任务依赖关系图，用于分析任务依赖并优化执行顺序
    """
    
    def __init__(self, tasks):
        """
        初始化依赖图
        
        参数:
            tasks (list): 任务列表
        """
        self.tasks = tasks
        self.task_map = {task['id']: task for task in tasks}
        self.graph = self._build_graph()
        self.topological_order = self._topological_sort()
        
    def _build_graph(self):
        """
        构建依赖图（邻接表表示）
        
        返回:
            dict: {task_id: [dependent_task_ids]}
        """
        graph = {task['id']: [] for task in self.tasks}
        
        # 构建依赖关系
        for task in self.tasks:
            task_id = task['id']
            dependencies = task.get('dependencies', [])
            for dep_id in dependencies:
                if dep_id in graph:
                    # dep_id 依赖于 task_id
                    graph[dep_id].append(task_id)
        
        return graph
        
    def _topological_sort(self):
        """
        拓扑排序，确定执行顺序
        
        返回:
            list: 任务ID的拓扑排序
        """
        # 计算入度
        in_degree = {task_id: 0 for task_id in self.task_map}
        for task_id, dependents in self.graph.items():
            for dep in dependents:
                in_degree[dep] += 1
                
        # 使用队列进行拓扑排序
        queue = [task_id for task_id, degree in in_degree.items() if degree == 0]
        topo_order = []
        
        while queue:
            current = queue.pop(0)
            topo_order.append(current)
            
            for dependent in self.graph[current]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
                    
        # 检查是否有环
        if len(topo_order) != len(self.task_map):
            logger.warning("依赖图中检测到循环依赖")
            # 添加未被拓扑排序的任务（有循环依赖）
            for task_id in self.task_map:
                if task_id not in topo_order:
                    topo_order.append(task_id)
        
        return topo_order
    
    def get_execution_batches(self):
        """
        获取可并行执行的任务批次
        
        返回:
            list: 任务批次列表
        """
        batches = []
        executed = set()
        
        while len(executed) < len(self.task_map):
            # 找出当前可以执行的任务（其依赖都已执行）
            current_batch_ids = []
            
            for task_id in self.topological_order:
                if task_id in executed:
                    continue
                    
                task = self.task_map[task_id]
                dependencies = task.get('dependencies', [])
                
                # 如果所有依赖都已执行，可以将此任务加入当前批次
                if all(dep in executed for dep in dependencies):
                    current_batch_ids.append(task_id)
            
            # 如果没有找到可执行的任务但还有未执行的任务，说明有循环依赖
            if not current_batch_ids and len(executed) < len(self.task_map):
                # 将所有未执行的任务作为一个批次
                current_batch_ids = [task_id for task_id in self.task_map if task_id not in executed]
                logger.warning(f"检测到循环依赖，将 {len(current_batch_ids)} 个任务作为单一批次执行")
            
            # 创建当前批次的任务列表
            current_batch = [self.task_map[task_id] for task_id in current_batch_ids]
            batches.append(current_batch)
            
            # 更新已执行集合
            executed.update(current_batch_ids)
        
        return batches
    
    def get_critical_path(self):
        """
        计算关键路径（执行时间最长的路径）
        
        返回:
            list: 关键路径上的任务ID列表
        """
        # 假设每个任务的执行时间为1
        # 在实际应用中，可以使用历史执行时间或估计值
        path_length = {task_id: 0 for task_id in self.task_map}
        
        # 按拓扑排序计算最长路径
        for task_id in self.topological_order:
            task = self.task_map[task_id]
            dependencies = task.get('dependencies', [])
            
            # 当前任务的路径长度是其最长依赖路径长度+1
            if dependencies:
                path_length[task_id] = max(path_length[dep] for dep in dependencies) + 1
            else:
                path_length[task_id] = 1
                
        # 找出最长路径
        max_length = max(path_length.values())
        critical_path = []
        
        # 反向构建关键路径
        current_length = max_length
        for task_id in reversed(self.topological_order):
            if path_length[task_id] == current_length:
                critical_path.insert(0, task_id)
                current_length -= 1
                
        return critical_path