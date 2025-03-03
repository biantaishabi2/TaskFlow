#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
任务分解与执行系统的API服务器
允许外部程序通过HTTP API调用任务分解与执行系统
"""

import os
import json
import logging
from flask import Flask, request, jsonify
from src.core.task_decomposition_system import TaskDecompositionSystem
from src.distributed.parallel_task_decomposition_system import ParallelTaskDecompositionSystem

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join('logs', 'task_api_server.log'))
    ]
)
logger = logging.getLogger('task_api_server')

# 创建Flask应用
app = Flask(__name__)

# 保存进行中的任务
active_tasks = {}

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查端点"""
    return jsonify({"status": "ok", "active_tasks": len(active_tasks)}), 200

@app.route('/execute_task', methods=['POST'])
def execute_task():
    """执行任务API端点"""
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        task_description = data.get('task')
        if not task_description:
            return jsonify({"error": "No task description provided"}), 400
            
        parallel = data.get('parallel', False)
        save_results = data.get('save_results', True)
        
        logger.info(f"收到任务请求: {task_description[:50]}... 并行模式: {parallel}")
        
        # 选择系统类型
        if parallel:
            system = ParallelTaskDecompositionSystem()
            logger.info("使用并行任务分解系统")
        else:
            system = TaskDecompositionSystem()
            logger.info("使用标准任务分解系统")
        
        # 执行任务
        result = system.execute_complex_task(task_description, save_results=save_results)
        
        logger.info(f"任务完成，结果长度: {len(str(result))}")
        return jsonify({"result": result})
    
    except Exception as e:
        logger.error(f"执行任务时发生错误: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/execute_task_async', methods=['POST'])
def execute_task_async():
    """异步执行任务API端点"""
    import threading
    import uuid
    
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        task_description = data.get('task')
        if not task_description:
            return jsonify({"error": "No task description provided"}), 400
            
        parallel = data.get('parallel', False)
        save_results = data.get('save_results', True)
        
        # 生成唯一任务ID
        task_id = str(uuid.uuid4())
        
        # 定义任务执行函数
        def run_task():
            try:
                # 选择系统类型
                if parallel:
                    system = ParallelTaskDecompositionSystem()
                else:
                    system = TaskDecompositionSystem()
                
                # 执行任务
                result = system.execute_complex_task(task_description, save_results=save_results)
                
                # 保存结果
                active_tasks[task_id] = {
                    "status": "completed",
                    "result": result
                }
                logger.info(f"异步任务 {task_id} 完成")
            except Exception as e:
                active_tasks[task_id] = {
                    "status": "failed",
                    "error": str(e)
                }
                logger.error(f"异步任务 {task_id} 失败: {str(e)}", exc_info=True)
        
        # 初始化任务状态
        active_tasks[task_id] = {
            "status": "running",
            "description": task_description[:100] + ("..." if len(task_description) > 100 else "")
        }
        
        # 启动任务线程
        thread = threading.Thread(target=run_task)
        thread.daemon = True
        thread.start()
        
        logger.info(f"启动异步任务: {task_id}")
        return jsonify({"task_id": task_id, "status": "running"})
    
    except Exception as e:
        logger.error(f"启动异步任务时发生错误: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/task_status/<task_id>', methods=['GET'])
def task_status(task_id):
    """获取任务状态API端点"""
    if task_id not in active_tasks:
        return jsonify({"error": "Task not found"}), 404
        
    task = active_tasks[task_id]
    
    # 如果任务已完成，可以选择是否返回完整结果
    include_result = request.args.get('include_result', 'false').lower() == 'true'
    
    if task["status"] == "completed" and not include_result:
        response = {
            "task_id": task_id,
            "status": task["status"],
            "result_available": True
        }
    else:
        response = {
            "task_id": task_id,
            "status": task["status"]
        }
        
        if "error" in task:
            response["error"] = task["error"]
            
        if include_result and "result" in task:
            response["result"] = task["result"]
    
    return jsonify(response)

@app.route('/task_result/<task_id>', methods=['GET'])
def task_result(task_id):
    """获取任务结果API端点"""
    if task_id not in active_tasks:
        return jsonify({"error": "Task not found"}), 404
        
    task = active_tasks[task_id]
    
    if task["status"] != "completed":
        return jsonify({"error": f"Task is not completed, current status: {task['status']}"}), 400
        
    if "result" not in task:
        return jsonify({"error": "Task result not available"}), 500
        
    return jsonify({"task_id": task_id, "result": task["result"]})

@app.route('/tasks', methods=['GET'])
def list_tasks():
    """列出所有任务API端点"""
    task_list = []
    
    for task_id, task in active_tasks.items():
        task_info = {
            "task_id": task_id,
            "status": task["status"],
            "description": task.get("description", "")
        }
        
        if task["status"] == "failed" and "error" in task:
            task_info["error"] = task["error"]
            
        task_list.append(task_info)
    
    return jsonify({"tasks": task_list})

if __name__ == '__main__':
    # 确保日志目录存在
    os.makedirs('logs', exist_ok=True)
    
    logger.info("启动任务API服务器")
    app.run(host='0.0.0.0', port=9000)