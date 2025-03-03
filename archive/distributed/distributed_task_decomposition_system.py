#!/usr/bin/env python3
"""
任务拆分与执行系统 - 分布式版主系统模块
阶段4：主系统集成 - 分布式架构实现
支持跨设备/服务器分布式任务执行，提供API接口和资源管理
"""

import os
import json
import logging
import time
import threading
import queue
import uuid
import socket
import requests
from datetime import datetime
from flask import Flask, request, jsonify
from concurrent.futures import ThreadPoolExecutor
from werkzeug.serving import run_simple

from context_management import ContextManager, TaskContext
from task_planner import TaskPlanner
from parallel_task_executor import ParallelTaskExecutor, DependencyGraph
from claude_task_bridge import TaskClaudeBridge, TaskLLMBridge

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('distributed_task_decomposition.log')
    ]
)
logger = logging.getLogger('distributed_task_decomposition_system')

class TaskWorkerNode:
    """任务工作节点，负责执行分配的子任务"""
    
    def __init__(self, node_id=None, max_workers=4, api_port=23457):
        """
        初始化任务工作节点
        
        参数:
            node_id (str): 节点ID，如果为None则自动生成
            max_workers (int): 最大并行工作线程数
            api_port (int): 节点API端口
        """
        self.node_id = node_id or f"worker_{socket.gethostname()}_{uuid.uuid4().hex[:8]}"
        self.max_workers = max_workers
        self.api_port = api_port
        
        # 初始化Claude桥接
        self.llm_bridge = TaskLLMBridge()
        self.claude_bridge = TaskClaudeBridge(llm_bridge=self.llm_bridge)
        
        # 初始化执行器
        self.executor = ParallelTaskExecutor(
            claude_bridge=self.claude_bridge,
            max_workers=max_workers
        )
        
        # 初始化任务队列
        self.task_queue = queue.PriorityQueue()
        self.active_tasks = {}  # {task_id: task_info}
        self.completed_tasks = {}  # {task_id: result}
        
        # 系统状态
        self.status = "idle"  # idle, busy, error
        self.stats = {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "total_execution_time": 0,
            "cpu_usage": 0,
            "memory_usage": 0
        }
        
        # 启动任务处理线程
        self.running = True
        self.worker_thread = threading.Thread(target=self._process_task_queue)
        self.worker_thread.daemon = True
        self.worker_thread.start()
        
        # 启动状态监控线程
        self.monitor_thread = threading.Thread(target=self._monitor_system_resources)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        # 启动API服务
        self.api_app = self._create_api_app()
        self.api_thread = threading.Thread(target=self._start_api_server)
        self.api_thread.daemon = True
        self.api_thread.start()
        
        logger.info(f"工作节点 {self.node_id} 已初始化，最大工作线程数: {max_workers}，API端口: {api_port}")
    
    def _create_api_app(self):
        """创建Flask API应用"""
        app = Flask(f"worker_node_{self.node_id}")
        
        @app.route('/health', methods=['GET'])
        def health_check():
            return jsonify({
                "status": self.status,
                "node_id": self.node_id,
                "stats": self.stats,
                "active_tasks": len(self.active_tasks),
                "queued_tasks": self.task_queue.qsize()
            })
        
        @app.route('/tasks', methods=['POST'])
        def submit_task():
            data = request.json
            if not data or 'task' not in data:
                return jsonify({"error": "任务数据无效"}), 400
                
            task = data['task']
            priority = data.get('priority', 5)  # 默认优先级：5（1-10，1最高）
            
            task_id = task.get('id', str(uuid.uuid4()))
            task['id'] = task_id
            
            # 将任务添加到队列
            self.task_queue.put((priority, task))
            
            return jsonify({
                "message": "任务已提交",
                "task_id": task_id,
                "queue_position": self.task_queue.qsize()
            })
        
        @app.route('/tasks/<task_id>', methods=['GET'])
        def get_task_status(task_id):
            # 检查任务是否在活动任务中
            if task_id in self.active_tasks:
                return jsonify({
                    "task_id": task_id,
                    "status": "running",
                    "start_time": self.active_tasks[task_id].get("start_time")
                })
            
            # 检查任务是否已完成
            if task_id in self.completed_tasks:
                return jsonify({
                    "task_id": task_id,
                    "status": "completed",
                    "result": self.completed_tasks[task_id]
                })
            
            # 检查任务是否在队列中
            for priority, task in list(self.task_queue.queue):
                if task['id'] == task_id:
                    return jsonify({
                        "task_id": task_id,
                        "status": "queued",
                        "priority": priority
                    })
            
            return jsonify({"error": f"任务 {task_id} 不存在"}), 404
        
        @app.route('/tasks/<task_id>', methods=['DELETE'])
        def cancel_task(task_id):
            # 如果任务在队列中，尝试移除
            updated_queue = queue.PriorityQueue()
            removed = False
            
            for priority, task in list(self.task_queue.queue):
                if task['id'] != task_id:
                    updated_queue.put((priority, task))
                else:
                    removed = True
            
            if removed:
                self.task_queue = updated_queue
                return jsonify({"message": f"任务 {task_id} 已从队列中移除"})
            
            # 如果任务正在执行，我们无法安全地取消（简化版）
            if task_id in self.active_tasks:
                return jsonify({"error": "无法取消正在执行的任务"}), 400
                
            # 如果任务已完成
            if task_id in self.completed_tasks:
                return jsonify({"message": f"任务 {task_id} 已完成，无需取消"})
                
            return jsonify({"error": f"任务 {task_id} 不存在"}), 404
        
        return app
    
    def _start_api_server(self):
        """启动API服务器"""
        run_simple('0.0.0.0', self.api_port, self.api_app, threaded=True)
    
    def _process_task_queue(self):
        """处理任务队列中的任务"""
        while self.running:
            try:
                if self.task_queue.empty():
                    self.status = "idle"
                    time.sleep(1)
                    continue
                
                self.status = "busy"
                priority, task = self.task_queue.get(timeout=1)
                task_id = task['id']
                
                # 记录任务开始执行
                self.active_tasks[task_id] = {
                    "task": task,
                    "priority": priority,
                    "start_time": time.time()
                }
                
                logger.info(f"开始执行任务 {task_id} (优先级: {priority})")
                
                try:
                    # 创建任务特定的上下文管理器
                    context_manager = ContextManager()
                    self.executor.context_manager = context_manager
                    
                    # 执行任务
                    start_time = time.time()
                    result = self.executor.execute_subtask(task)
                    execution_time = time.time() - start_time
                    
                    # 记录结果
                    self.completed_tasks[task_id] = result
                    self.stats["tasks_completed"] += 1
                    self.stats["total_execution_time"] += execution_time
                    
                    success = result.get('success', False)
                    status = "成功" if success else "失败"
                    logger.info(f"任务 {task_id} 执行{status}, 耗时: {execution_time:.2f}秒")
                    
                    if not success:
                        self.stats["tasks_failed"] += 1
                        
                except Exception as e:
                    logger.error(f"任务 {task_id} 执行异常: {str(e)}")
                    error_result = {
                        'task_id': task_id,
                        'success': False,
                        'error': str(e),
                        'execution_time': time.time() - start_time
                    }
                    self.completed_tasks[task_id] = error_result
                    self.stats["tasks_failed"] += 1
                
                finally:
                    # 从活动任务中移除
                    if task_id in self.active_tasks:
                        del self.active_tasks[task_id]
                    
                    # 标记队列任务为已处理
                    self.task_queue.task_done()
            
            except queue.Empty:
                pass
            except Exception as e:
                logger.error(f"任务处理线程异常: {str(e)}")
                self.status = "error"
                time.sleep(5)  # 出错后暂停一段时间
    
    def _monitor_system_resources(self, interval=10):
        """监控系统资源使用情况"""
        while self.running:
            try:
                # 获取CPU和内存使用情况
                import psutil
                process = psutil.Process(os.getpid())
                
                # 更新统计信息
                self.stats["cpu_usage"] = process.cpu_percent()
                self.stats["memory_usage"] = process.memory_info().rss / (1024 * 1024)  # MB
                
                # 检查是否需要调整工作线程数
                self._adjust_workers_based_on_load()
                
            except Exception as e:
                logger.error(f"资源监控异常: {str(e)}")
            
            time.sleep(interval)
    
    def _adjust_workers_based_on_load(self):
        """根据系统负载动态调整工作线程数"""
        # 这里是一个简单的自适应策略，可以根据实际需求调整
        cpu_usage = self.stats["cpu_usage"]
        
        if cpu_usage > 90 and self.executor.max_workers > 2:
            # CPU使用率高，减少线程数
            self.executor.max_workers -= 1
            logger.info(f"系统负载高 (CPU: {cpu_usage}%)，减少工作线程数至 {self.executor.max_workers}")
        elif cpu_usage < 50 and self.executor.max_workers < self.max_workers:
            # CPU使用率低，增加线程数
            self.executor.max_workers += 1
            logger.info(f"系统负载低 (CPU: {cpu_usage}%)，增加工作线程数至 {self.executor.max_workers}")
    
    def submit_task(self, task, priority=5):
        """
        提交任务到本地队列
        
        参数:
            task (dict): 任务定义
            priority (int): 任务优先级（1-10，1最高）
            
        返回:
            str: 任务ID
        """
        task_id = task.get('id', str(uuid.uuid4()))
        task['id'] = task_id
        
        # 添加到队列
        self.task_queue.put((priority, task))
        
        logger.info(f"任务 {task_id} 已提交到队列，优先级: {priority}")
        return task_id
    
    def get_task_result(self, task_id, wait=False, timeout=None):
        """
        获取任务执行结果
        
        参数:
            task_id (str): 任务ID
            wait (bool): 是否等待任务完成
            timeout (float): 等待超时时间（秒）
            
        返回:
            dict: 任务结果，如果任务未完成则返回None
        """
        start_time = time.time()
        
        while True:
            # 检查任务是否已完成
            if task_id in self.completed_tasks:
                return self.completed_tasks[task_id]
            
            # 如果不等待，直接返回None
            if not wait:
                return None
            
            # 检查是否超时
            if timeout and (time.time() - start_time > timeout):
                return {
                    'task_id': task_id,
                    'success': False,
                    'error': f"等待任务结果超时 ({timeout}秒)"
                }
            
            # 等待一段时间再检查
            time.sleep(0.5)
    
    def stop(self):
        """停止工作节点"""
        logger.info(f"正在停止工作节点 {self.node_id}")
        self.running = False
        
        # 等待所有任务完成
        while not self.task_queue.empty() or self.active_tasks:
            logger.info(f"等待 {self.task_queue.qsize()} 个排队任务和 {len(self.active_tasks)} 个活动任务完成")
            time.sleep(1)
        
        logger.info("工作节点已停止")


class DistributedTaskDecompositionSystem:
    """分布式任务拆分与执行系统主类，管理多个工作节点"""
    
    def __init__(self, logs_dir="logs", local_workers=2, api_port=23456):
        """
        初始化分布式任务拆分与执行系统
        
        参数:
            logs_dir (str): 日志和上下文存储目录
            local_workers (int): 本地工作节点数量
            api_port (int): API端口
        """
        # 确保日志目录存在
        os.makedirs(logs_dir, exist_ok=True)
        self.logs_dir = logs_dir
        
        # 初始化节点管理
        self.master_id = f"master_{socket.gethostname()}_{uuid.uuid4().hex[:8]}"
        self.local_workers = []
        self.remote_workers = {}  # {node_id: {url, status, ...}}
        
        # 初始化API服务
        self.api_port = api_port
        self.api_app = self._create_api_app()
        
        # 初始化上下文管理器和规划者
        self.context_manager = ContextManager(context_dir=logs_dir)
        self.llm_bridge = TaskLLMBridge()
        
        # 初始化本地工作节点
        self.local_workers = []
        self.worker_ports = []
        
        # 使用递增端口，从主端口+1开始
        base_port = api_port + 1
        for i in range(local_workers):
            worker_port = base_port + i
            self.worker_ports.append(worker_port)
            # 创建工作节点
            worker = TaskWorkerNode(
                node_id=f"local_worker_{i}_{uuid.uuid4().hex[:6]}",
                max_workers=2,  # 每个本地工作节点的默认线程数
                api_port=worker_port
            )
            
            self.local_workers.append(worker)
            logger.info(f"已启动本地工作节点 {worker.node_id} (端口: {worker_port})")
        
        # 任务跟踪
        self.tasks = {}  # {task_id: task_info}
        
        # 启动API服务器
        self.api_thread = threading.Thread(target=self._start_api_server)
        self.api_thread.daemon = True
        self.api_thread.start()
        
        # 启动节点监控
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_workers)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        logger.info(f"分布式任务拆分与执行系统已初始化，主节点ID: {self.master_id}, API端口: {api_port}")
        logger.info(f"已启动 {len(self.local_workers)} 个本地工作节点")
    
    def _create_api_app(self):
        """创建Flask API应用"""
        app = Flask(f"distributed_system_{self.master_id}")
        
        @app.route('/health', methods=['GET'])
        def health_check():
            # 收集所有工作节点状态
            workers_status = []
            
            # 收集本地工作节点状态
            for worker in self.local_workers:
                workers_status.append({
                    "node_id": worker.node_id,
                    "type": "local",
                    "status": worker.status,
                    "stats": worker.stats
                })
            
            # 收集远程工作节点状态
            for node_id, node_info in self.remote_workers.items():
                workers_status.append({
                    "node_id": node_id,
                    "type": "remote",
                    "status": node_info.get("status", "unknown"),
                    "url": node_info.get("url"),
                    "last_check": node_info.get("last_check")
                })
            
            return jsonify({
                "master_id": self.master_id,
                "status": "running",
                "workers": workers_status,
                "tasks_count": len(self.tasks)
            })
        
        @app.route('/tasks', methods=['POST'])
        def submit_task():
            data = request.json
            if not data or 'task_description' not in data:
                return jsonify({"error": "任务描述无效"}), 400
                
            task_description = data['task_description']
            task_type = data.get('task_type', 'complex')  # complex 或 simple
            priority = data.get('priority', 5)
            save_results = data.get('save_results', True)
            
            if task_type == 'complex':
                # 复杂任务通过execute_complex_task处理
                task_id = self.execute_complex_task(
                    task_description, 
                    save_results=save_results,
                    async_execution=True,
                    priority=priority
                )
            else:
                # 简单任务直接分配给工作节点
                subtask = {
                    "id": str(uuid.uuid4()),
                    "name": "单一任务",
                    "instruction": task_description
                }
                task_id = self.distribute_task(subtask, priority)
            
            return jsonify({
                "message": "任务已提交",
                "task_id": task_id,
                "task_type": task_type
            })
        
        @app.route('/tasks/<task_id>', methods=['GET'])
        def get_task_status(task_id):
            if task_id not in self.tasks:
                return jsonify({"error": f"任务 {task_id} 不存在"}), 404
                
            task_info = self.tasks[task_id]
            
            # 如果是复杂任务，收集所有子任务的状态
            if task_info.get('type') == 'complex':
                subtasks_status = {}
                for subtask_id, subtask_info in task_info.get('subtasks', {}).items():
                    node_id = subtask_info.get('node_id')
                    if not node_id:
                        subtasks_status[subtask_id] = {"status": "pending"}
                        continue
                        
                    # 查询节点获取任务状态
                    status = self._get_subtask_status(subtask_id, node_id)
                    subtasks_status[subtask_id] = status
                
                # 计算整体完成度
                completed = sum(1 for s in subtasks_status.values() 
                              if s.get('status') == 'completed')
                total = len(subtasks_status)
                progress = completed / total if total > 0 else 0
                
                return jsonify({
                    "task_id": task_id,
                    "type": "complex",
                    "status": task_info.get('status', 'unknown'),
                    "progress": f"{completed}/{total} ({progress:.0%})",
                    "subtasks": subtasks_status
                })
            else:
                # 简单任务直接查询节点
                node_id = task_info.get('node_id')
                if not node_id:
                    return jsonify({
                        "task_id": task_id,
                        "type": "simple",
                        "status": "pending"
                    })
                
                status = self._get_subtask_status(task_id, node_id)
                return jsonify({
                    "task_id": task_id,
                    "type": "simple",
                    "status": status.get('status', 'unknown'),
                    "node_id": node_id,
                    "details": status
                })
        
        @app.route('/tasks/<task_id>/result', methods=['GET'])
        def get_task_result(task_id):
            if task_id not in self.tasks:
                return jsonify({"error": f"任务 {task_id} 不存在"}), 404
                
            task_info = self.tasks[task_id]
            
            # 检查任务是否为复杂任务
            if task_info.get('type') == 'complex':
                # 如果任务已完成，返回最终结果
                if task_info.get('status') == 'completed' and 'result' in task_info:
                    return jsonify(task_info['result'])
                
                # 如果任务正在执行，返回部分结果
                return jsonify({
                    "message": f"任务 {task_id} 仍在执行中",
                    "status": task_info.get('status', 'unknown'),
                    "partial_results": task_info.get('partial_results', {})
                })
            else:
                # 简单任务直接查询节点
                node_id = task_info.get('node_id')
                if not node_id:
                    return jsonify({
                        "message": f"任务 {task_id} 尚未分配到节点"
                    })
                
                result = self._get_subtask_result(task_id, node_id)
                if result:
                    return jsonify(result)
                else:
                    return jsonify({
                        "message": f"任务 {task_id} 仍在执行中或未找到结果"
                    })
        
        @app.route('/workers', methods=['GET'])
        def list_workers():
            workers = []
            
            # 收集本地工作节点信息
            for worker in self.local_workers:
                workers.append({
                    "node_id": worker.node_id,
                    "type": "local",
                    "status": worker.status,
                    "stats": worker.stats,
                    "active_tasks": len(worker.active_tasks),
                    "queued_tasks": worker.task_queue.qsize()
                })
            
            # 收集远程工作节点信息
            for node_id, node_info in self.remote_workers.items():
                workers.append({
                    "node_id": node_id,
                    "type": "remote",
                    "status": node_info.get("status", "unknown"),
                    "url": node_info.get("url"),
                    "last_check": node_info.get("last_check")
                })
            
            return jsonify({
                "workers_count": len(workers),
                "workers": workers
            })
        
        @app.route('/workers', methods=['POST'])
        def register_worker():
            data = request.json
            if not data or 'url' not in data:
                return jsonify({"error": "工作节点URL无效"}), 400
                
            url = data['url']
            node_id = data.get('node_id')
            
            # 尝试连接工作节点
            try:
                response = requests.get(f"{url}/health", timeout=5)
                if response.status_code == 200:
                    worker_info = response.json()
                    node_id = node_id or worker_info.get('node_id')
                    
                    if not node_id:
                        return jsonify({"error": "工作节点未提供有效的节点ID"}), 400
                    
                    # 注册工作节点
                    self.remote_workers[node_id] = {
                        "url": url,
                        "status": worker_info.get('status', 'unknown'),
                        "last_check": time.time(),
                        "health_data": worker_info
                    }
                    
                    logger.info(f"已注册远程工作节点 {node_id} ({url})")
                    return jsonify({
                        "message": "工作节点注册成功",
                        "node_id": node_id
                    })
                else:
                    return jsonify({"error": f"工作节点健康检查失败: {response.status_code}"}), 400
            except Exception as e:
                return jsonify({"error": f"连接工作节点失败: {str(e)}"}), 400
        
        @app.route('/workers/<node_id>', methods=['DELETE'])
        def unregister_worker(node_id):
            if node_id in self.remote_workers:
                del self.remote_workers[node_id]
                logger.info(f"已注销远程工作节点 {node_id}")
                return jsonify({
                    "message": f"工作节点 {node_id} 已注销"
                })
            else:
                return jsonify({"error": f"工作节点 {node_id} 不存在"}), 404
        
        return app
    
    def _start_api_server(self):
        """启动API服务器"""
        run_simple('0.0.0.0', self.api_port, self.api_app, threaded=True)
    
    def _start_local_workers(self, count):
        """启动本地工作节点"""
        for i in range(count):
            # 计算每个工作节点的API端口（避免冲突）
            worker_port = self.worker_ports[i]
            
            # 创建工作节点
            worker = TaskWorkerNode(
                node_id=f"local_worker_{i}_{uuid.uuid4().hex[:6]}",
                max_workers=2,  # 每个本地工作节点的默认线程数
                api_port=worker_port
            )
            
            self.local_workers.append(worker)
            logger.info(f"已启动本地工作节点 {worker.node_id} (端口: {worker_port})")
    
    def _monitor_workers(self, interval=30):
        """定期监控工作节点状态"""
        while self.running:
            try:
                # 监控远程工作节点
                for node_id, node_info in list(self.remote_workers.items()):
                    url = node_info.get('url')
                    try:
                        response = requests.get(f"{url}/health", timeout=5)
                        if response.status_code == 200:
                            worker_info = response.json()
                            self.remote_workers[node_id].update({
                                "status": worker_info.get('status', 'unknown'),
                                "last_check": time.time(),
                                "health_data": worker_info
                            })
                        else:
                            logger.warning(f"工作节点 {node_id} 健康检查失败: {response.status_code}")
                            self.remote_workers[node_id]["status"] = "error"
                    except Exception as e:
                        logger.warning(f"连接工作节点 {node_id} 失败: {str(e)}")
                        self.remote_workers[node_id]["status"] = "unreachable"
                        self.remote_workers[node_id]["last_error"] = str(e)
                
                # 检查并清理长时间不可达的节点
                current_time = time.time()
                for node_id, node_info in list(self.remote_workers.items()):
                    last_check = node_info.get('last_check', 0)
                    status = node_info.get('status', '')
                    
                    # 如果节点超过2小时不可达，移除它
                    if status == 'unreachable' and (current_time - last_check > 7200):
                        logger.info(f"移除长时间不可达的工作节点 {node_id}")
                        del self.remote_workers[node_id]
            
            except Exception as e:
                logger.error(f"监控工作节点时出错: {str(e)}")
            
            time.sleep(interval)
    
    def _get_subtask_status(self, subtask_id, node_id):
        """获取子任务状态"""
        # 检查节点是否为本地节点
        for worker in self.local_workers:
            if worker.node_id == node_id:
                # 检查任务是否在活动任务中
                if subtask_id in worker.active_tasks:
                    return {
                        "status": "running",
                        "start_time": worker.active_tasks[subtask_id].get("start_time")
                    }
                
                # 检查任务是否已完成
                if subtask_id in worker.completed_tasks:
                    return {
                        "status": "completed",
                        "success": worker.completed_tasks[subtask_id].get('success', False)
                    }
                
                # 检查任务是否在队列中
                for priority, task in list(worker.task_queue.queue):
                    if task['id'] == subtask_id:
                        return {
                            "status": "queued",
                            "priority": priority
                        }
                
                return {"status": "unknown"}
        
        # 检查节点是否为远程节点
        if node_id in self.remote_workers:
            node_info = self.remote_workers[node_id]
            url = node_info.get('url')
            
            try:
                response = requests.get(f"{url}/tasks/{subtask_id}", timeout=5)
                if response.status_code == 200:
                    return response.json()
                else:
                    return {"status": "error", "error": f"状态查询失败: {response.status_code}"}
            except Exception as e:
                return {"status": "error", "error": f"连接节点失败: {str(e)}"}
        
        return {"status": "unknown", "error": f"节点 {node_id} 不存在"}
    
    def _get_subtask_result(self, subtask_id, node_id):
        """获取子任务结果"""
        # 检查节点是否为本地节点
        for worker in self.local_workers:
            if worker.node_id == node_id:
                # 检查任务是否已完成
                if subtask_id in worker.completed_tasks:
                    return worker.completed_tasks[subtask_id]
                return None
        
        # 检查节点是否为远程节点
        if node_id in self.remote_workers:
            node_info = self.remote_workers[node_id]
            url = node_info.get('url')
            
            try:
                response = requests.get(f"{url}/tasks/{subtask_id}", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('status') == 'completed':
                        return data.get('result')
                return None
            except Exception:
                return None
        
        return None
    
    def register_remote_worker(self, url):
        """
        注册远程工作节点
        
        参数:
            url (str): 工作节点API URL
            
        返回:
            bool: 是否成功注册
        """
        try:
            response = requests.get(f"{url}/health", timeout=5)
            if response.status_code == 200:
                worker_info = response.json()
                node_id = worker_info.get('node_id')
                
                if not node_id:
                    logger.error("工作节点未提供有效的节点ID")
                    return False
                
                # 注册工作节点
                self.remote_workers[node_id] = {
                    "url": url,
                    "status": worker_info.get('status', 'unknown'),
                    "last_check": time.time(),
                    "health_data": worker_info
                }
                
                logger.info(f"已注册远程工作节点 {node_id} ({url})")
                return True
            else:
                logger.error(f"工作节点健康检查失败: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"连接工作节点失败: {str(e)}")
            return False
    
    def distribute_task(self, task, priority=5):
        """
        分配任务到最合适的工作节点
        
        参数:
            task (dict): 任务定义
            priority (int): 任务优先级（1-10，1最高）
            
        返回:
            str: 任务ID
        """
        task_id = task.get('id', str(uuid.uuid4()))
        task['id'] = task_id
        
        # 找出最合适的工作节点（最少排队任务的节点）
        best_worker = None
        min_queue_size = float('inf')
        
        # 检查本地工作节点
        for worker in self.local_workers:
            queue_size = worker.task_queue.qsize()
            if queue_size < min_queue_size:
                min_queue_size = queue_size
                best_worker = ('local', worker)
        
        # 检查远程工作节点
        for node_id, node_info in self.remote_workers.items():
            if node_info.get('status') != 'idle' and node_info.get('status') != 'busy':
                continue  # 跳过不可用的节点
                
            url = node_info.get('url')
            try:
                response = requests.get(f"{url}/health", timeout=3)
                if response.status_code == 200:
                    worker_info = response.json()
                    queue_size = worker_info.get('queued_tasks', float('inf'))
                    
                    if queue_size < min_queue_size:
                        min_queue_size = queue_size
                        best_worker = ('remote', node_id, url)
            except:
                continue  # 跳过连接失败的节点
        
        # 分配任务到最合适的节点
        if best_worker:
            worker_type = best_worker[0]
            
            if worker_type == 'local':
                worker = best_worker[1]
                worker.submit_task(task, priority)
                
                # 记录任务信息
                self.tasks[task_id] = {
                    'type': 'simple',
                    'node_id': worker.node_id,
                    'status': 'submitted',
                    'priority': priority,
                    'submit_time': time.time()
                }
                
                logger.info(f"任务 {task_id} 已分配到本地工作节点 {worker.node_id}")
            else:
                node_id, url = best_worker[1], best_worker[2]
                
                try:
                    # 提交任务到远程节点
                    response = requests.post(
                        f"{url}/tasks",
                        json={'task': task, 'priority': priority},
                        timeout=5
                    )
                    
                    if response.status_code == 200:
                        # 记录任务信息
                        self.tasks[task_id] = {
                            'type': 'simple',
                            'node_id': node_id,
                            'status': 'submitted',
                            'priority': priority,
                            'submit_time': time.time()
                        }
                        
                        logger.info(f"任务 {task_id} 已分配到远程工作节点 {node_id}")
                    else:
                        logger.error(f"提交任务到远程节点 {node_id} 失败: {response.status_code}")
                        
                        # 尝试分配到本地节点
                        if self.local_workers:
                            worker = min(self.local_workers, key=lambda w: w.task_queue.qsize())
                            worker.submit_task(task, priority)
                            
                            # 记录任务信息
                            self.tasks[task_id] = {
                                'type': 'simple',
                                'node_id': worker.node_id,
                                'status': 'submitted',
                                'priority': priority,
                                'submit_time': time.time()
                            }
                            
                            logger.info(f"任务 {task_id} 改为分配到本地工作节点 {worker.node_id}")
                        else:
                            logger.error("没有可用的工作节点")
                            return None
                except Exception as e:
                    logger.error(f"提交任务到远程节点 {node_id} 异常: {str(e)}")
                    
                    # 尝试分配到本地节点
                    if self.local_workers:
                        worker = min(self.local_workers, key=lambda w: w.task_queue.qsize())
                        worker.submit_task(task, priority)
                        
                        # 记录任务信息
                        self.tasks[task_id] = {
                            'type': 'simple',
                            'node_id': worker.node_id,
                            'status': 'submitted',
                            'priority': priority,
                            'submit_time': time.time()
                        }
                        
                        logger.info(f"任务 {task_id} 改为分配到本地工作节点 {worker.node_id}")
                    else:
                        logger.error("没有可用的工作节点")
                        return None
        else:
            logger.error("没有可用的工作节点")
            return None
        
        return task_id
    
    def execute_complex_task(self, task_description, save_results=True, async_execution=False, priority=5):
        """
        执行复杂任务，将其分解为子任务并分布式执行
        
        参数:
            task_description (str): 任务描述
            save_results (bool): 是否保存结果到文件
            async_execution (bool): 是否异步执行（不等待任务完成）
            priority (int): 任务优先级（1-10，1最高）
            
        返回:
            str or dict: 异步模式下返回任务ID，同步模式下返回最终执行结果
        """
        # 创建任务ID
        task_id = f"complex_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        
        # 创建上下文目录
        context_dir = os.path.join(self.logs_dir, task_id)
        os.makedirs(context_dir, exist_ok=True)
        
        # 初始化上下文管理器
        context_manager = ContextManager(context_dir=context_dir)
        
        # 创建规划者（外层循环）
        planner = TaskPlanner(
            task_description, 
            context_manager=context_manager,
            logs_dir=context_dir
        )
        
        # 分析任务
        logger.info(f"[{task_id}] 正在分析任务...")
        analysis = planner.analyze_task()
        logger.info(f"[{task_id}] 任务分析完成: {analysis.get('result', {}).get('summary', '')[:100]}...")
        
        # 拆分任务
        logger.info(f"[{task_id}] 正在拆分任务...")
        subtasks = planner.break_down_task(analysis)
        logger.info(f"[{task_id}] 任务拆分完成，共{len(subtasks)}个子任务")
        
        # 分析任务依赖
        dependency_graph = DependencyGraph(subtasks)
        execution_batches = dependency_graph.get_execution_batches()
        logger.info(f"[{task_id}] 任务依赖分析完成，共分为 {len(execution_batches)} 个执行批次")
        
        # 记录任务信息
        self.tasks[task_id] = {
            'type': 'complex',
            'status': 'planning',
            'description': task_description,
            'context_dir': context_dir,
            'subtasks': {subtask['id']: {'data': subtask} for subtask in subtasks},
            'execution_batches': [
                [subtask['id'] for subtask in batch]
                for batch in execution_batches
            ],
            'current_batch': 0,
            'start_time': time.time(),
            'planner': planner,
            'context_manager': context_manager
        }
        
        # 如果是异步执行，启动执行线程并返回任务ID
        if async_execution:
            execution_thread = threading.Thread(
                target=self._execute_complex_task_async,
                args=(task_id, priority, save_results)
            )
            execution_thread.daemon = True
            execution_thread.start()
            
            return task_id
        
        # 同步执行并返回结果
        return self._execute_complex_task_sync(task_id, priority, save_results)
    
    def _execute_complex_task_async(self, task_id, priority, save_results):
        """异步执行复杂任务的内部方法"""
        try:
            # 获取任务信息
            task_info = self.tasks[task_id]
            execution_batches = task_info['execution_batches']
            planner = task_info['planner']
            context_dir = task_info['context_dir']
            
            # 更新任务状态
            task_info['status'] = 'executing'
            
            # 记录执行开始时间
            execution_start_time = time.time()
            executed_tasks_count = 0
            
            # 执行每个批次的任务
            logger.info(f"[{task_id}] 开始执行子任务...")
            
            for batch_index, batch_task_ids in enumerate(execution_batches):
                # 获取当前批次的任务
                batch_subtasks = []
                for subtask_id in batch_task_ids:
                    subtask_data = task_info['subtasks'][subtask_id]['data']
                    batch_subtasks.append(subtask_data)
                
                # 更新当前批次索引
                task_info['current_batch'] = batch_index
                
                # 记录批次开始
                batch_start_time = time.time()
                batch_size = len(batch_subtasks)
                logger.info(f"[{task_id}] 执行批次 {batch_index+1}/{len(execution_batches)}, 包含 {batch_size} 个任务")
                
                # 分配并执行当前批次的任务
                batch_results = {}
                for subtask in batch_subtasks:
                    subtask_id = subtask['id']
                    
                    # 分配子任务到工作节点
                    node_task_id = self.distribute_task(subtask, priority=priority)
                    
                    if node_task_id:
                        # 关联子任务和节点
                        node_id = self.tasks[subtask_id]['node_id']
                        task_info['subtasks'][subtask_id]['node_id'] = node_id
                        task_info['subtasks'][subtask_id]['node_task_id'] = node_task_id
                        
                        logger.info(f"[{task_id}] 子任务 {subtask_id} 已分配到节点 {node_id}")
                    else:
                        logger.error(f"[{task_id}] 子任务 {subtask_id} 分配失败")
                        # 记录失败结果
                        batch_results[subtask_id] = {
                            'success': False,
                            'error': "任务分配失败，没有可用的工作节点"
                        }
                
                # 等待当前批次所有任务完成
                pending_tasks = set(subtask['id'] for subtask in batch_subtasks) - set(batch_results.keys())
                
                while pending_tasks:
                    # 检查每个待处理的任务是否完成
                    for subtask_id in list(pending_tasks):
                        node_id = task_info['subtasks'][subtask_id].get('node_id')
                        if not node_id:
                            continue
                        
                        # 获取任务结果
                        result = self._get_subtask_result(subtask_id, node_id)
                        
                        if result:
                            # 记录结果
                            batch_results[subtask_id] = result
                            pending_tasks.remove(subtask_id)
                            logger.info(f"[{task_id}] 子任务 {subtask_id} 已完成")
                    
                    # 短暂等待后再检查
                    if pending_tasks:
                        time.sleep(2)
                
                # 记录批次完成
                batch_duration = time.time() - batch_start_time
                success_count = sum(1 for r in batch_results.values() if r.get('success', False))
                logger.info(f"[{task_id}] 批次 {batch_index+1} 执行完成, 耗时: {batch_duration:.2f}秒, "
                           f"成功: {success_count}/{batch_size}")
                
                # 更新任务状态
                executed_tasks_count += batch_size
                
                # 处理每个子任务的结果
                for subtask_id, result in batch_results.items():
                    # 更新规划者的结果
                    planner.process_result(subtask_id, result)
                    
                    # 保存结果到任务信息
                    task_info['subtasks'][subtask_id]['result'] = result
                    task_info['subtasks'][subtask_id]['completion_time'] = time.time()
                
                # 保存当前进度
                if save_results:
                    progress_file = os.path.join(context_dir, "progress.json")
                    with open(progress_file, 'w', encoding='utf-8') as f:
                        progress_data = {
                            'task_id': task_id,
                            'subtasks_total': sum(len(batch) for batch in execution_batches),
                            'subtasks_completed': executed_tasks_count,
                            'success_count': sum(
                                1 for st in task_info['subtasks'].values()
                                if st.get('result', {}).get('success', False)
                            ),
                            'start_time': execution_start_time,
                            'current_time': time.time(),
                            'elapsed_time': time.time() - execution_start_time,
                            'batches_completed': batch_index + 1,
                            'batches_total': len(execution_batches)
                        }
                        json.dump(progress_data, f, ensure_ascii=False, indent=2)
            
            # 计算总耗时
            execution_duration = time.time() - execution_start_time
            
            # 获取最终结果
            logger.info(f"[{task_id}] 正在生成最终结果...")
            final_result = planner.get_final_result()
            
            # 记录任务完成
            success = final_result.get('success', False)
            status = "成功" if success else "失败"
            logger.info(f"[{task_id}] 复杂任务执行{status}, 总耗时: {execution_duration:.2f}秒")
            logger.info(f"[{task_id}] 共执行了{executed_tasks_count}个子任务，"
                       f"成功: {sum(1 for st in task_info['subtasks'].values() if st.get('result', {}).get('success', False))}, "
                       f"失败: {sum(1 for st in task_info['subtasks'].values() if not st.get('result', {}).get('success', False))}")
            
            # 更新任务状态
            task_info['status'] = 'completed'
            task_info['completion_time'] = time.time()
            task_info['result'] = final_result
            
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
                        'execution_time': datetime.now().isoformat(),
                        'execution_duration': execution_duration,
                        'subtasks_total': sum(len(batch) for batch in execution_batches),
                        'subtasks_executed': executed_tasks_count,
                        'success_count': sum(
                            1 for st in task_info['subtasks'].values()
                            if st.get('result', {}).get('success', False)
                        ),
                        'failure_count': sum(
                            1 for st in task_info['subtasks'].values()
                            if not st.get('result', {}).get('success', False)
                        ),
                        'batches_count': len(execution_batches),
                        'final_status': status,
                        'result_summary': final_result.get('result', {}).get('summary', '没有结果摘要')
                    }
                    json.dump(summary_data, f, ensure_ascii=False, indent=2)
                
                logger.info(f"[{task_id}] 结果已保存到: {context_dir}")
        
        except Exception as e:
            logger.error(f"[{task_id}] 执行复杂任务时出错: {str(e)}", exc_info=True)
            # 更新任务状态
            task_info = self.tasks.get(task_id)
            if task_info:
                task_info['status'] = 'error'
                task_info['error'] = str(e)
    
    def _execute_complex_task_sync(self, task_id, priority, save_results):
        """同步执行复杂任务的内部方法"""
        try:
            # 执行异步方法
            self._execute_complex_task_async(task_id, priority, save_results)
            
            # 等待任务完成
            task_info = self.tasks[task_id]
            while task_info['status'] not in ['completed', 'error']:
                time.sleep(1)
            
            # 返回最终结果
            if task_info['status'] == 'error':
                return {
                    'success': False,
                    'error': task_info.get('error', '未知错误')
                }
            
            return task_info['result']
            
        except Exception as e:
            logger.error(f"[{task_id}] 同步执行复杂任务时出错: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_task_result(self, task_id, wait=False, timeout=None):
        """
        获取任务执行结果
        
        参数:
            task_id (str): 任务ID
            wait (bool): 是否等待任务完成
            timeout (float): 等待超时时间（秒）
            
        返回:
            dict: 任务结果，如果任务未完成则返回任务状态
        """
        if task_id not in self.tasks:
            return {
                'success': False,
                'error': f"任务 {task_id} 不存在"
            }
        
        task_info = self.tasks[task_id]
        
        # 如果是复杂任务
        if task_info.get('type') == 'complex':
            # 如果任务已完成，返回结果
            if task_info.get('status') == 'completed' and 'result' in task_info:
                return task_info['result']
            
            # 如果任务出错，返回错误
            if task_info.get('status') == 'error':
                return {
                    'success': False,
                    'error': task_info.get('error', '未知错误')
                }
            
            # 如果需要等待任务完成
            if wait:
                start_time = time.time()
                while task_info.get('status') not in ['completed', 'error']:
                    # 检查是否超时
                    if timeout and (time.time() - start_time > timeout):
                        return {
                            'success': False,
                            'status': task_info.get('status', 'unknown'),
                            'error': f"等待任务结果超时 ({timeout}秒)"
                        }
                    
                    time.sleep(1)
                
                # 返回最终结果
                if task_info.get('status') == 'completed' and 'result' in task_info:
                    return task_info['result']
                else:
                    return {
                        'success': False,
                        'status': task_info.get('status', 'error'),
                        'error': task_info.get('error', '未知错误')
                    }
            
            # 如果不等待，返回当前状态
            return {
                'status': task_info.get('status', 'unknown'),
                'progress': f"{sum(1 for st in task_info['subtasks'].values() if 'result' in st)}/{len(task_info['subtasks'])}"
            }
        
        # 如果是简单任务
        node_id = task_info.get('node_id')
        if not node_id:
            return {
                'status': 'pending',
                'message': "任务尚未分配到节点"
            }
        
        # 获取节点上的任务结果
        result = self._get_subtask_result(task_id, node_id)
        
        # 如果已有结果，直接返回
        if result:
            return result
        
        # 如果需要等待结果
        if wait:
            start_time = time.time()
            while True:
                result = self._get_subtask_result(task_id, node_id)
                
                if result:
                    return result
                
                # 检查是否超时
                if timeout and (time.time() - start_time > timeout):
                    return {
                        'status': 'timeout',
                        'error': f"等待任务结果超时 ({timeout}秒)"
                    }
                
                time.sleep(1)
        
        # 返回当前状态
        status = self._get_subtask_status(task_id, node_id)
        return {
            'status': status.get('status', 'unknown')
        }
    
    def stop(self):
        """停止分布式系统"""
        logger.info("正在停止分布式任务拆分与执行系统...")
        self.running = False
        
        # 停止所有本地工作节点
        for worker in self.local_workers:
            worker.stop()
        
        logger.info("分布式系统已停止")


# CLI入口点
if __name__ == "__main__":
    import argparse
    
    # 命令行参数
    parser = argparse.ArgumentParser(description="分布式任务拆分与执行系统")
    parser.add_argument("--mode", choices=['master', 'worker'], default='master',
                        help="运行模式：master(主节点)或worker(工作节点)")
    parser.add_argument("--logs-dir", default="logs", help="日志和上下文存储目录")
    parser.add_argument("--api-port", type=int, default=23456, help="API端口")
    parser.add_argument("--workers", type=int, default=2, help="本地工作节点数量")
    parser.add_argument("--max-threads", type=int, default=4, help="每个工作节点的最大线程数")
    parser.add_argument("--register", help="要注册的远程工作节点URL")
    parser.add_argument("--task", help="要执行的任务描述或任务文件路径")
    parser.add_argument("--file", action="store_true", help="指示任务参数是文件路径")
    parser.add_argument("--async", action="store_true", dest="async_execution",
                        help="异步执行任务，不等待完成")
    
    args = parser.parse_args()
    
    # 确保日志目录存在
    os.makedirs(args.logs_dir, exist_ok=True)
    
    if args.mode == 'worker':
        # 启动工作节点
        worker = TaskWorkerNode(
            max_workers=args.max_threads,
            api_port=args.api_port
        )
        
        logger.info(f"工作节点已启动，节点ID: {worker.node_id}, API端口: {args.api_port}")
        logger.info("按 Ctrl+C 停止工作节点...")
        
        try:
            # 保持程序运行
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("正在停止工作节点...")
            worker.stop()
            logger.info("工作节点已停止")
    else:
        # 启动主节点
        system = DistributedTaskDecompositionSystem(
            logs_dir=args.logs_dir,
            local_workers=args.workers,
            api_port=args.api_port
        )
        
        # 注册远程工作节点
        if args.register:
            success = system.register_remote_worker(args.register)
            if success:
                logger.info(f"已成功注册远程工作节点: {args.register}")
            else:
                logger.error(f"注册远程工作节点失败: {args.register}")
        
        # 执行任务
        if args.task:
            # 读取任务
            if args.file:
                try:
                    with open(args.task, 'r', encoding='utf-8') as f:
                        task_description = f.read()
                except Exception as e:
                    logger.error(f"无法读取任务文件: {str(e)}")
                    exit(1)
            else:
                task_description = args.task
            
            logger.info("开始执行任务...")
            
            # 执行任务
            if args.async_execution:
                # 异步执行
                task_id = system.execute_complex_task(
                    task_description,
                    save_results=True,
                    async_execution=True
                )
                
                logger.info(f"任务已提交，ID: {task_id}")
                logger.info(f"可通过 API 查询任务状态: GET http://localhost:{args.api_port}/tasks/{task_id}")
            else:
                # 同步执行
                result = system.execute_complex_task(
                    task_description,
                    save_results=True,
                    async_execution=False
                )
                
                # 输出结果
                success = result.get('success', False)
                status = "成功" if success else "失败"
                summary = result.get('result', {}).get('summary', '没有结果摘要')
                
                print("\n" + "="*80)
                print(f"任务执行{status}")
                print(f"结果摘要: {summary}")
                print("="*80)
        else:
            logger.info(f"分布式系统已启动，API端口: {args.api_port}")
            logger.info(f"API地址: http://localhost:{args.api_port}")
            logger.info("按 Ctrl+C 停止系统...")
            
            try:
                # 保持程序运行
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("正在停止系统...")
                system.stop()
                logger.info("系统已停止")