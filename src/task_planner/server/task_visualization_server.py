#!/usr/bin/env python3
"""
任务拆分与执行系统 - 可视化服务器
阶段4：主系统集成 - 可视化界面，提供任务执行状态和结果的实时监控
"""

import os
import json
import time
import logging
import threading
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_from_directory
import requests
import plotly
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
import numpy as np

# 配置日志
logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'logs')
os.makedirs(logs_dir, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(logs_dir, 'task_visualization.log'))
    ]
)
logger = logging.getLogger('task_visualization_server')

class TaskVisualizationServer:
    """任务执行可视化服务器，提供Web界面监控任务执行情况"""
    
    def __init__(self, logs_dir="logs", server_port=9000, api_url="http://localhost:8000"):
        """
        初始化任务可视化服务器
        
        参数:
            logs_dir (str): 日志和任务数据目录
            server_port (int): Web服务器端口
            api_url (str): 任务系统API URL
        """
        # 确保日志目录存在
        os.makedirs(logs_dir, exist_ok=True)
        self.logs_dir = logs_dir
        self.server_port = server_port
        self.api_url = api_url
        
        # 创建Flask应用
        self.app = Flask(
            __name__, 
            template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
            static_folder=os.path.join(os.path.dirname(__file__), 'static')
        )
        
        # 任务数据
        self.tasks = {}  # {task_id: task_data}
        self.workers = {}  # {node_id: worker_data}
        self.system_stats = {
            'start_time': time.time(),
            'tasks_completed': 0,
            'tasks_failed': 0,
            'total_execution_time': 0
        }
        
        # 设置路由
        self._setup_routes()
        
        # 启动数据收集线程
        self.running = True
        self.data_thread = threading.Thread(target=self._collect_data)
        self.data_thread.daemon = True
        self.data_thread.start()
        
        logger.info(f"可视化服务器已初始化，端口: {server_port}, API地址: {api_url}")
    
    def _setup_routes(self):
        """设置Flask路由"""
        
        @self.app.route('/')
        def index():
            """首页 - 任务概览"""
            return render_template('index.html', title="任务执行系统 - 概览")
        
        @self.app.route('/tasks')
        def tasks():
            """任务列表页"""
            return render_template('tasks.html', title="任务列表")
        
        @self.app.route('/tasks/<task_id>')
        def task_detail(task_id):
            """任务详情页"""
            return render_template('task_detail.html', title=f"任务详情 - {task_id}", task_id=task_id)
        
        @self.app.route('/workers')
        def workers():
            """工作节点列表页"""
            return render_template('workers.html', title="工作节点列表")
        
        @self.app.route('/api/overview')
        def api_overview():
            """API - 系统概览数据"""
            active_tasks = sum(1 for t in self.tasks.values() if t.get('status') not in ['completed', 'error'])
            completed_tasks = sum(1 for t in self.tasks.values() if t.get('status') == 'completed')
            failed_tasks = sum(1 for t in self.tasks.values() if t.get('status') == 'error')
            
            # 计算平均执行时间
            execution_times = []
            for task in self.tasks.values():
                if task.get('completion_time') and task.get('start_time'):
                    execution_times.append(task['completion_time'] - task['start_time'])
            
            avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0
            
            # 统计任务类型
            task_types = {}
            for task in self.tasks.values():
                task_type = task.get('type', 'unknown')
                task_types[task_type] = task_types.get(task_type, 0) + 1
            
            # 最近的任务
            recent_tasks = sorted(
                [t for t in self.tasks.values() if 'start_time' in t],
                key=lambda x: x['start_time'],
                reverse=True
            )[:5]
            
            return jsonify({
                'tasks_count': len(self.tasks),
                'active_tasks': active_tasks,
                'completed_tasks': completed_tasks,
                'failed_tasks': failed_tasks,
                'workers_count': len(self.workers),
                'avg_execution_time': avg_execution_time,
                'task_types': task_types,
                'recent_tasks': recent_tasks,
                'uptime': time.time() - self.system_stats['start_time']
            })
        
        @self.app.route('/api/tasks')
        def api_tasks():
            """API - 任务列表数据"""
            # 按开始时间排序
            sorted_tasks = sorted(
                [t for t in self.tasks.values() if 'start_time' in t],
                key=lambda x: x['start_time'],
                reverse=True
            )
            return jsonify(sorted_tasks)
        
        @self.app.route('/api/tasks/<task_id>')
        def api_task_detail(task_id):
            """API - 任务详情数据"""
            task = self.tasks.get(task_id, {})
            if not task:
                try:
                    # 尝试从API获取任务数据
                    response = requests.get(f"{self.api_url}/tasks/{task_id}", timeout=5)
                    if response.status_code == 200:
                        task = response.json()
                        self.tasks[task_id] = task
                except:
                    pass
            
            return jsonify(task)
        
        @self.app.route('/api/tasks/<task_id>/result')
        def api_task_result(task_id):
            """API - 任务结果数据"""
            try:
                # 尝试从API获取任务结果
                response = requests.get(f"{self.api_url}/tasks/{task_id}/result", timeout=5)
                if response.status_code == 200:
                    return jsonify(response.json())
            except:
                pass
            
            # 尝试从本地读取
            try:
                for task_dir in os.listdir(self.logs_dir):
                    if task_id in task_dir:
                        result_file = os.path.join(self.logs_dir, task_dir, "final_result.json")
                        if os.path.exists(result_file):
                            with open(result_file, 'r', encoding='utf-8') as f:
                                return jsonify(json.load(f))
            except:
                pass
            
            return jsonify({'error': f"无法获取任务 {task_id} 的结果"})
        
        @self.app.route('/api/workers')
        def api_workers():
            """API - 工作节点列表数据"""
            return jsonify(list(self.workers.values()))
        
        @self.app.route('/api/chart/tasks_timeline')
        def api_chart_tasks_timeline():
            """API - 任务时间线图表数据"""
            completed_tasks = [t for t in self.tasks.values() 
                               if 'start_time' in t and 'completion_time' in t]
            
            if not completed_tasks:
                return jsonify({'error': '没有已完成的任务数据'})
            
            # 创建时间线数据
            df = pd.DataFrame([
                {
                    'Task': f"{t.get('id', 'unknown')}",
                    'Start': datetime.fromtimestamp(t['start_time']),
                    'Finish': datetime.fromtimestamp(t['completion_time']),
                    'Type': t.get('type', 'unknown'),
                    'Status': 'Success' if t.get('success', False) else 'Failed'
                }
                for t in completed_tasks
            ])
            
            if df.empty:
                return jsonify({'error': '没有有效的任务数据'})
                
            # 创建甘特图
            fig = px.timeline(
                df, 
                x_start="Start", 
                x_end="Finish", 
                y="Task",
                color="Status",
                hover_data=["Type"]
            )
            fig.update_layout(title="任务执行时间线")
            
            # 转换为JSON
            graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
            return jsonify(graphJSON)
        
        @self.app.route('/api/chart/task_status')
        def api_chart_task_status():
            """API - 任务状态图表数据"""
            statuses = {}
            for task in self.tasks.values():
                status = task.get('status', 'unknown')
                statuses[status] = statuses.get(status, 0) + 1
            
            # 创建饼图
            labels = list(statuses.keys())
            values = list(statuses.values())
            
            fig = go.Figure(data=[go.Pie(labels=labels, values=values)])
            fig.update_layout(title="任务状态分布")
            
            # 转换为JSON
            graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
            return jsonify(graphJSON)
        
        @self.app.route('/api/chart/worker_load')
        def api_chart_worker_load():
            """API - 工作节点负载图表数据"""
            worker_data = []
            for worker in self.workers.values():
                if 'stats' in worker:
                    worker_data.append({
                        'node_id': worker.get('node_id', 'unknown'),
                        'cpu_usage': worker['stats'].get('cpu_usage', 0),
                        'memory_usage': worker['stats'].get('memory_usage', 0),
                        'tasks_completed': worker['stats'].get('tasks_completed', 0),
                        'active_tasks': worker.get('active_tasks', 0)
                    })
            
            if not worker_data:
                return jsonify({'error': '没有工作节点数据'})
            
            # 创建条形图
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=[w['node_id'] for w in worker_data],
                y=[w['cpu_usage'] for w in worker_data],
                name='CPU使用率 (%)'
            ))
            fig.add_trace(go.Bar(
                x=[w['node_id'] for w in worker_data],
                y=[w['active_tasks'] for w in worker_data],
                name='活动任务数'
            ))
            
            fig.update_layout(
                title="工作节点负载",
                xaxis_title="节点ID",
                yaxis_title="值",
                barmode='group'
            )
            
            # 转换为JSON
            graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
            return jsonify(graphJSON)
    
    def _collect_data(self, interval=10):
        """收集任务系统的数据"""
        while self.running:
            try:
                # 获取系统健康状态
                response = requests.get(f"{self.api_url}/health", timeout=5)
                if response.status_code == 200:
                    system_data = response.json()
                    
                    # 更新工作节点数据
                    if 'workers' in system_data:
                        for worker in system_data['workers']:
                            node_id = worker.get('node_id')
                            if node_id:
                                self.workers[node_id] = worker
                
                # 获取任务列表
                response = requests.get(f"{self.api_url}/tasks", timeout=5)
                if response.status_code == 200:
                    tasks_data = response.json()
                    for task in tasks_data:
                        task_id = task.get('task_id')
                        if task_id:
                            self.tasks[task_id] = task
                
                # 扫描日志目录获取额外任务数据
                self._scan_logs_directory()
                
            except Exception as e:
                logger.error(f"数据收集失败: {str(e)}")
            
            time.sleep(interval)
    
    def _scan_logs_directory(self):
        """扫描日志目录获取额外的任务数据"""
        try:
            for task_dir in os.listdir(self.logs_dir):
                # 检查是否是任务目录
                if not os.path.isdir(os.path.join(self.logs_dir, task_dir)):
                    continue
                
                # 读取执行摘要
                summary_file = os.path.join(self.logs_dir, task_dir, "execution_summary.json")
                if os.path.exists(summary_file):
                    try:
                        with open(summary_file, 'r', encoding='utf-8') as f:
                            summary_data = json.load(f)
                            
                            task_id = summary_data.get('task_id')
                            if task_id and task_id not in self.tasks:
                                # 构建任务数据
                                task_data = {
                                    'id': task_id,
                                    'type': 'complex',
                                    'status': 'completed',
                                    'success': summary_data.get('final_status') == '成功',
                                    'start_time': summary_data.get('start_time', 0),
                                    'completion_time': summary_data.get('execution_time', 0),
                                    'subtasks_total': summary_data.get('subtasks_total', 0),
                                    'subtasks_executed': summary_data.get('subtasks_executed', 0),
                                    'success_count': summary_data.get('success_count', 0),
                                    'failure_count': summary_data.get('failure_count', 0),
                                    'batches_count': summary_data.get('batches_count', 0),
                                    'result_summary': summary_data.get('result_summary', '')
                                }
                                
                                self.tasks[task_id] = task_data
                    except:
                        pass
        except Exception as e:
            logger.error(f"扫描日志目录失败: {str(e)}")
    
    def start(self):
        """启动可视化服务器"""
        logger.info(f"启动可视化服务器，端口: {self.server_port}")
        self.app.run(host='0.0.0.0', port=self.server_port, debug=False)
    
    def stop(self):
        """停止可视化服务器"""
        logger.info("停止可视化服务器")
        self.running = False


# 创建前端模板和静态文件目录
def create_templates_and_static():
    """创建前端模板和静态文件目录"""
    # 创建模板目录
    templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
    os.makedirs(templates_dir, exist_ok=True)
    
    # 创建静态文件目录
    static_dir = os.path.join(os.path.dirname(__file__), 'static')
    os.makedirs(static_dir, exist_ok=True)
    os.makedirs(os.path.join(static_dir, 'css'), exist_ok=True)
    os.makedirs(os.path.join(static_dir, 'js'), exist_ok=True)
    
    # 创建基础模板
    base_html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
    {% block head %}{% endblock %}
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container">
            <a class="navbar-brand" href="/">任务拆分与执行系统</a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav">
                    <li class="nav-item">
                        <a class="nav-link" href="/">概览</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/tasks">任务列表</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/workers">工作节点</a>
                    </li>
                </ul>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        <h1 class="mb-4">{{ title }}</h1>
        {% block content %}{% endblock %}
    </div>

    <footer class="footer mt-5 py-3 bg-light">
        <div class="container text-center">
            <span class="text-muted">任务拆分与执行系统 - 可视化界面</span>
        </div>
    </footer>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/jquery@3.6.0/dist/jquery.min.js"></script>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <script src="{{ url_for('static', filename='js/app.js') }}"></script>
    {% block scripts %}{% endblock %}
</body>
</html>
"""
    
    # 创建首页模板
    index_html = """{% extends "base.html" %}

{% block content %}
<div class="row">
    <div class="col-md-6">
        <div class="card mb-4">
            <div class="card-header">
                系统状态
            </div>
            <div class="card-body">
                <div id="system-stats">加载中...</div>
            </div>
        </div>
    </div>
    <div class="col-md-6">
        <div class="card mb-4">
            <div class="card-header">
                任务状态分布
            </div>
            <div class="card-body">
                <div id="task-status-chart"></div>
            </div>
        </div>
    </div>
</div>

<div class="card mb-4">
    <div class="card-header">
        工作节点负载
    </div>
    <div class="card-body">
        <div id="worker-load-chart"></div>
    </div>
</div>

<div class="card">
    <div class="card-header">
        最近任务
    </div>
    <div class="card-body">
        <div id="recent-tasks">加载中...</div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
$(document).ready(function() {
    // 加载系统概览
    function loadOverview() {
        $.getJSON('/api/overview', function(data) {
            let html = `
                <div class="row">
                    <div class="col-md-6">
                        <p><strong>任务总数:</strong> ${data.tasks_count}</p>
                        <p><strong>活动任务:</strong> ${data.active_tasks}</p>
                        <p><strong>完成任务:</strong> ${data.completed_tasks}</p>
                        <p><strong>失败任务:</strong> ${data.failed_tasks}</p>
                    </div>
                    <div class="col-md-6">
                        <p><strong>工作节点数:</strong> ${data.workers_count}</p>
                        <p><strong>平均执行时间:</strong> ${data.avg_execution_time.toFixed(2)}秒</p>
                        <p><strong>系统运行时间:</strong> ${(data.uptime / 3600).toFixed(2)}小时</p>
                    </div>
                </div>
            `;
            $('#system-stats').html(html);
            
            // 渲染最近任务
            let recentTasksHtml = '<div class="table-responsive"><table class="table table-striped">';
            recentTasksHtml += '<thead><tr><th>任务ID</th><th>类型</th><th>状态</th><th>开始时间</th></tr></thead><tbody>';
            
            data.recent_tasks.forEach(function(task) {
                const status = task.status === 'completed' ? 
                    (task.success ? '<span class="text-success">成功</span>' : '<span class="text-danger">失败</span>') :
                    task.status;
                    
                recentTasksHtml += `
                    <tr>
                        <td><a href="/tasks/${task.id}">${task.id}</a></td>
                        <td>${task.type || '未知'}</td>
                        <td>${status}</td>
                        <td>${new Date(task.start_time * 1000).toLocaleString()}</td>
                    </tr>
                `;
            });
            
            recentTasksHtml += '</tbody></table></div>';
            $('#recent-tasks').html(recentTasksHtml);
        });
    }
    
    // 加载任务状态图表
    function loadTaskStatusChart() {
        $.getJSON('/api/chart/task_status', function(data) {
            var graphData = JSON.parse(data);
            Plotly.newPlot('task-status-chart', graphData.data, graphData.layout);
        });
    }
    
    // 加载工作节点负载图表
    function loadWorkerLoadChart() {
        $.getJSON('/api/chart/worker_load', function(data) {
            if (data.error) {
                $('#worker-load-chart').html('<p class="text-center text-muted">'+data.error+'</p>');
                return;
            }
            var graphData = JSON.parse(data);
            Plotly.newPlot('worker-load-chart', graphData.data, graphData.layout);
        });
    }
    
    // 初始加载
    loadOverview();
    loadTaskStatusChart();
    loadWorkerLoadChart();
    
    // 定时刷新
    setInterval(loadOverview, 10000);
    setInterval(loadTaskStatusChart, 30000);
    setInterval(loadWorkerLoadChart, 15000);
});
</script>
{% endblock %}
"""
    
    # 创建任务列表模板
    tasks_html = """{% extends "base.html" %}

{% block content %}
<div class="card">
    <div class="card-header d-flex justify-content-between align-items-center">
        <span>任务列表</span>
        <div>
            <input type="text" id="search-tasks" class="form-control" placeholder="搜索任务...">
        </div>
    </div>
    <div class="card-body">
        <div class="table-responsive">
            <table class="table table-striped" id="tasks-table">
                <thead>
                    <tr>
                        <th>任务ID</th>
                        <th>类型</th>
                        <th>状态</th>
                        <th>开始时间</th>
                        <th>完成时间</th>
                        <th>执行时间</th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody id="tasks-list">
                    <tr><td colspan="7" class="text-center">加载中...</td></tr>
                </tbody>
            </table>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
$(document).ready(function() {
    // 加载任务列表
    function loadTasks() {
        $.getJSON('/api/tasks', function(tasks) {
            let html = '';
            
            if (tasks.length === 0) {
                html = '<tr><td colspan="7" class="text-center">没有任务数据</td></tr>';
            } else {
                tasks.forEach(function(task) {
                    const status = task.status === 'completed' ? 
                        (task.success ? '<span class="text-success">成功</span>' : '<span class="text-danger">失败</span>') :
                        task.status;
                        
                    const startTime = task.start_time ? new Date(task.start_time * 1000).toLocaleString() : '-';
                    const completionTime = task.completion_time ? new Date(task.completion_time * 1000).toLocaleString() : '-';
                    
                    let executionTime = '-';
                    if (task.start_time && task.completion_time) {
                        executionTime = ((task.completion_time - task.start_time) / 60).toFixed(2) + ' 分钟';
                    } else if (task.start_time) {
                        executionTime = '进行中';
                    }
                    
                    html += `
                        <tr>
                            <td>${task.id}</td>
                            <td>${task.type || '未知'}</td>
                            <td>${status}</td>
                            <td>${startTime}</td>
                            <td>${completionTime}</td>
                            <td>${executionTime}</td>
                            <td>
                                <a href="/tasks/${task.id}" class="btn btn-sm btn-primary">详情</a>
                            </td>
                        </tr>
                    `;
                });
            }
            
            $('#tasks-list').html(html);
        });
    }
    
    // 搜索功能
    $('#search-tasks').on('keyup', function() {
        const value = $(this).val().toLowerCase();
        $("#tasks-list tr").filter(function() {
            $(this).toggle($(this).text().toLowerCase().indexOf(value) > -1)
        });
    });
    
    // 初始加载
    loadTasks();
    
    // 定时刷新
    setInterval(loadTasks, 30000);
});
</script>
{% endblock %}
"""
    
    # 创建任务详情模板
    task_detail_html = """{% extends "base.html" %}

{% block content %}
<div class="card mb-4">
    <div class="card-header">
        任务信息
    </div>
    <div class="card-body">
        <div id="task-info">加载中...</div>
    </div>
</div>

<div class="card mb-4" id="subtasks-card" style="display:none;">
    <div class="card-header">
        子任务列表
    </div>
    <div class="card-body">
        <div id="subtasks-list"></div>
    </div>
</div>

<div class="card">
    <div class="card-header">
        任务结果
    </div>
    <div class="card-body">
        <div id="task-result">加载中...</div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
$(document).ready(function() {
    const taskId = "{{ task_id }}";
    
    // 加载任务详情
    function loadTaskDetail() {
        $.getJSON(`/api/tasks/${taskId}`, function(task) {
            if (task.error) {
                $('#task-info').html(`<div class="alert alert-danger">${task.error}</div>`);
                return;
            }
            
            const status = task.status === 'completed' ? 
                (task.success ? '<span class="text-success">成功</span>' : '<span class="text-danger">失败</span>') :
                task.status;
                
            const startTime = task.start_time ? new Date(task.start_time * 1000).toLocaleString() : '-';
            const completionTime = task.completion_time ? new Date(task.completion_time * 1000).toLocaleString() : '-';
            
            let executionTime = '-';
            if (task.start_time && task.completion_time) {
                executionTime = ((task.completion_time - task.start_time) / 60).toFixed(2) + ' 分钟';
            } else if (task.start_time) {
                const elapsed = (Date.now() / 1000 - task.start_time).toFixed(2);
                executionTime = `进行中 (${elapsed} 秒)`;
            }
            
            let infoHtml = `
                <div class="row">
                    <div class="col-md-6">
                        <p><strong>任务ID:</strong> ${task.id}</p>
                        <p><strong>类型:</strong> ${task.type || '未知'}</p>
                        <p><strong>状态:</strong> ${status}</p>
                        <p><strong>开始时间:</strong> ${startTime}</p>
                        <p><strong>完成时间:</strong> ${completionTime}</p>
                        <p><strong>执行时间:</strong> ${executionTime}</p>
                    </div>
            `;
            
            // 如果是复杂任务，显示额外信息
            if (task.type === 'complex') {
                infoHtml += `
                    <div class="col-md-6">
                        <p><strong>子任务总数:</strong> ${task.subtasks_total || '-'}</p>
                        <p><strong>已执行子任务:</strong> ${task.subtasks_executed || '-'}</p>
                        <p><strong>成功子任务:</strong> ${task.success_count || '-'}</p>
                        <p><strong>失败子任务:</strong> ${task.failure_count || '-'}</p>
                        <p><strong>执行批次数:</strong> ${task.batches_count || '-'}</p>
                        <p><strong>进度:</strong> ${task.progress || '-'}</p>
                    </div>
                `;
                
                // 显示子任务卡片
                $('#subtasks-card').show();
                
                // 渲染子任务列表
                if (task.subtasks) {
                    let subtasksHtml = '<div class="table-responsive"><table class="table table-sm table-striped">';
                    subtasksHtml += '<thead><tr><th>子任务ID</th><th>状态</th><th>节点ID</th></tr></thead><tbody>';
                    
                    Object.entries(task.subtasks).forEach(function([subtaskId, subtaskInfo]) {
                        const subtaskStatus = subtaskInfo.status || '未知';
                        subtasksHtml += `
                            <tr>
                                <td>${subtaskId}</td>
                                <td>${subtaskStatus}</td>
                                <td>${subtaskInfo.node_id || '-'}</td>
                            </tr>
                        `;
                    });
                    
                    subtasksHtml += '</tbody></table></div>';
                    $('#subtasks-list').html(subtasksHtml);
                } else {
                    $('#subtasks-list').html('<p class="text-center text-muted">没有子任务数据</p>');
                }
            } else {
                infoHtml += `
                    <div class="col-md-6">
                        <p><strong>节点ID:</strong> ${task.node_id || '-'}</p>
                        <p><strong>优先级:</strong> ${task.priority || '-'}</p>
                    </div>
                `;
            }
            
            infoHtml += '</div>';
            
            // 如果任务有错误，显示错误信息
            if (task.error) {
                infoHtml += `
                    <div class="alert alert-danger mt-3">
                        <h5>错误信息:</h5>
                        <pre>${task.error}</pre>
                    </div>
                `;
            }
            
            $('#task-info').html(infoHtml);
        });
    }
    
    // 加载任务结果
    function loadTaskResult() {
        $.getJSON(`/api/tasks/${taskId}/result`, function(result) {
            if (result.error) {
                $('#task-result').html(`<div class="alert alert-info">${result.error}</div>`);
                return;
            }
            
            if (result.message) {
                $('#task-result').html(`<div class="alert alert-info">${result.message}</div>`);
                return;
            }
            
            // 生成结果HTML
            let resultHtml = '';
            
            // 如果有摘要，显示摘要
            if (result.result && result.result.summary) {
                resultHtml += `
                    <div class="mb-4">
                        <h5>结果摘要:</h5>
                        <div class="card">
                            <div class="card-body">
                                ${result.result.summary}
                            </div>
                        </div>
                    </div>
                `;
            }
            
            // 显示完整结果
            resultHtml += `
                <div>
                    <h5>完整结果:</h5>
                    <pre class="bg-light p-3 rounded">${JSON.stringify(result, null, 2)}</pre>
                </div>
            `;
            
            $('#task-result').html(resultHtml);
        });
    }
    
    // 初始加载
    loadTaskDetail();
    loadTaskResult();
    
    // 定时刷新
    setInterval(loadTaskDetail, 5000);
    setInterval(loadTaskResult, 10000);
});
</script>
{% endblock %}
"""
    
    # 创建工作节点模板
    workers_html = """{% extends "base.html" %}

{% block content %}
<div class="card mb-4">
    <div class="card-header">
        工作节点负载
    </div>
    <div class="card-body">
        <div id="worker-load-chart"></div>
    </div>
</div>

<div class="card">
    <div class="card-header">
        工作节点列表
    </div>
    <div class="card-body">
        <div class="table-responsive">
            <table class="table table-striped">
                <thead>
                    <tr>
                        <th>节点ID</th>
                        <th>类型</th>
                        <th>状态</th>
                        <th>活动任务数</th>
                        <th>队列任务数</th>
                        <th>CPU使用率</th>
                        <th>内存使用</th>
                        <th>已完成任务</th>
                    </tr>
                </thead>
                <tbody id="workers-list">
                    <tr><td colspan="8" class="text-center">加载中...</td></tr>
                </tbody>
            </table>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
$(document).ready(function() {
    // 加载工作节点列表
    function loadWorkers() {
        $.getJSON('/api/workers', function(workers) {
            let html = '';
            
            if (workers.length === 0) {
                html = '<tr><td colspan="8" class="text-center">没有工作节点数据</td></tr>';
            } else {
                workers.forEach(function(worker) {
                    const stats = worker.stats || {};
                    
                    html += `
                        <tr>
                            <td>${worker.node_id}</td>
                            <td>${worker.type || '未知'}</td>
                            <td>${worker.status || '未知'}</td>
                            <td>${worker.active_tasks || 0}</td>
                            <td>${worker.queued_tasks || 0}</td>
                            <td>${stats.cpu_usage ? stats.cpu_usage.toFixed(2) + '%' : '-'}</td>
                            <td>${stats.memory_usage ? stats.memory_usage.toFixed(2) + ' MB' : '-'}</td>
                            <td>${stats.tasks_completed || 0}</td>
                        </tr>
                    `;
                });
            }
            
            $('#workers-list').html(html);
        });
    }
    
    // 加载工作节点负载图表
    function loadWorkerLoadChart() {
        $.getJSON('/api/chart/worker_load', function(data) {
            if (data.error) {
                $('#worker-load-chart').html('<p class="text-center text-muted">'+data.error+'</p>');
                return;
            }
            var graphData = JSON.parse(data);
            Plotly.newPlot('worker-load-chart', graphData.data, graphData.layout);
        });
    }
    
    // 初始加载
    loadWorkers();
    loadWorkerLoadChart();
    
    // 定时刷新
    setInterval(loadWorkers, 5000);
    setInterval(loadWorkerLoadChart, 15000);
});
</script>
{% endblock %}
"""
    
    # 创建CSS文件
    css = """body {
    padding-bottom: 70px;
}

.footer {
    position: fixed;
    bottom: 0;
    width: 100%;
}

/* 添加一些间距 */
.card {
    margin-bottom: 1.5rem;
}

/* 表格样式 */
.table-responsive {
    overflow-x: auto;
}

.table th {
    white-space: nowrap;
}

/* 加载状态 */
.loading {
    text-align: center;
    padding: 2rem;
    color: #6c757d;
}

/* 图表容器 */
[id$="-chart"] {
    min-height: 300px;
}

/* 任务状态颜色 */
.status-completed {
    color: #28a745;
}

.status-error {
    color: #dc3545;
}

.status-running {
    color: #007bff;
}

.status-planning {
    color: #6c757d;
}

.status-executing {
    color: #fd7e14;
}

/* 预格式化文本 */
pre {
    background-color: #f8f9fa;
    padding: 1rem;
    border-radius: 0.25rem;
    overflow-x: auto;
}
"""
    
    # 创建JS文件
    js = """// 通用工具函数
function formatDate(timestamp) {
    if (!timestamp) return '-';
    return new Date(timestamp * 1000).toLocaleString();
}

function formatDuration(seconds) {
    if (!seconds) return '-';
    
    if (seconds < 60) {
        return seconds.toFixed(2) + ' 秒';
    } else if (seconds < 3600) {
        return (seconds / 60).toFixed(2) + ' 分钟';
    } else {
        return (seconds / 3600).toFixed(2) + ' 小时';
    }
}

function formatTaskStatus(status, success) {
    if (status === 'completed') {
        return success ? 
            '<span class="status-completed">成功</span>' : 
            '<span class="status-error">失败</span>';
    } else if (status === 'running' || status === 'executing') {
        return '<span class="status-running">执行中</span>';
    } else if (status === 'planning') {
        return '<span class="status-planning">规划中</span>';
    } else if (status === 'error') {
        return '<span class="status-error">错误</span>';
    } else {
        return status || '未知';
    }
}

// 错误处理
function handleApiError(error, elementId) {
    console.error('API错误:', error);
    $(`#${elementId}`).html(`
        <div class="alert alert-danger">
            <h5>加载失败</h5>
            <p>${error.message || '无法连接到API服务器'}</p>
        </div>
    `);
}

// 数据刷新处理
let refreshTimers = {};

function startRefreshTimer(functionName, interval, ...args) {
    // 清除现有定时器
    if (refreshTimers[functionName]) {
        clearInterval(refreshTimers[functionName]);
    }
    
    // 创建新定时器
    refreshTimers[functionName] = setInterval(() => {
        window[functionName](...args);
    }, interval);
    
    // 立即执行一次
    window[functionName](...args);
}

function stopAllRefreshTimers() {
    Object.values(refreshTimers).forEach(timer => clearInterval(timer));
    refreshTimers = {};
}

// 页面离开时停止所有定时器
$(window).on('beforeunload', stopAllRefreshTimers);
"""
    
    # 写入文件
    with open(os.path.join(templates_dir, 'base.html'), 'w', encoding='utf-8') as f:
        f.write(base_html)
    
    with open(os.path.join(templates_dir, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(index_html)
    
    with open(os.path.join(templates_dir, 'tasks.html'), 'w', encoding='utf-8') as f:
        f.write(tasks_html)
    
    with open(os.path.join(templates_dir, 'task_detail.html'), 'w', encoding='utf-8') as f:
        f.write(task_detail_html)
    
    with open(os.path.join(templates_dir, 'workers.html'), 'w', encoding='utf-8') as f:
        f.write(workers_html)
    
    with open(os.path.join(static_dir, 'css', 'style.css'), 'w', encoding='utf-8') as f:
        f.write(css)
    
    with open(os.path.join(static_dir, 'js', 'app.js'), 'w', encoding='utf-8') as f:
        f.write(js)


# CLI入口点
if __name__ == "__main__":
    import argparse
    
    # 创建前端模板和静态文件
    create_templates_and_static()
    
    # 命令行参数
    parser = argparse.ArgumentParser(description="任务拆分与执行系统 - 可视化服务器")
    parser.add_argument("--logs-dir", default="logs", help="日志和任务数据目录")
    parser.add_argument("--port", type=int, default=9000, help="Web服务器端口")
    parser.add_argument("--api-url", default="http://localhost:8000", help="任务系统API URL")
    
    args = parser.parse_args()
    
    # 启动服务器
    server = TaskVisualizationServer(
        logs_dir=args.logs_dir,
        server_port=args.port,
        api_url=args.api_url
    )
    
    try:
        server.start()
    except KeyboardInterrupt:
        logger.info("停止服务器...")
        server.stop()
        logger.info("服务器已停止")