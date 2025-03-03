#!/bin/bash

# 设置变量
MASTER_PORT=23456
WORKER1_PORT=23457
WORKER2_PORT=23458
VIZ_PORT=23459
LOGS_DIR="./logs"

# 定义清理函数，在脚本结束或Ctrl+C时执行
cleanup() {
    echo "收到中断信号，正在清理所有进程..."
    # 终止所有子进程
    pkill -f "python.*distributed_task_decomposition_system.py" || true
    pkill -f "python.*task_visualization_server.py" || true
    exit 0
}

# 注册信号处理，捕获中断信号
trap cleanup SIGINT SIGTERM EXIT

# 确保日志目录存在
mkdir -p $LOGS_DIR

# 清理旧进程
echo "清理旧进程..."
pkill -f "python.*distributed_task_decomposition_system.py" || true
pkill -f "python.*task_visualization_server.py" || true
sleep 2

# 逐步启动并验证
echo "启动主节点..."
python distributed_task_decomposition_system.py --mode master --api-port $MASTER_PORT --workers 2 --logs-dir $LOGS_DIR > master.log 2>&1 &
MASTER_PID=$!
echo "主节点PID: $MASTER_PID"
sleep 3

# 测试主节点是否响应
echo "测试主节点..."
curl -s http://localhost:$MASTER_PORT/health || echo "主节点未启动成功"
echo

echo "启动工作节点1..."
python distributed_task_decomposition_system.py --mode worker --api-port $WORKER1_PORT --max-threads 2 --logs-dir $LOGS_DIR > worker1.log 2>&1 &
WORKER1_PID=$!
echo "工作节点1 PID: $WORKER1_PID"
sleep 3

echo "启动工作节点2..."
python distributed_task_decomposition_system.py --mode worker --api-port $WORKER2_PORT --max-threads 2 --logs-dir $LOGS_DIR > worker2.log 2>&1 &
WORKER2_PID=$!
echo "工作节点2 PID: $WORKER2_PID"
sleep 3

echo "注册工作节点..."
python distributed_task_decomposition_system.py --mode master --api-port $MASTER_PORT --register "http://localhost:$WORKER1_PORT" || echo "工作节点1注册失败"
python distributed_task_decomposition_system.py --mode master --api-port $MASTER_PORT --register "http://localhost:$WORKER2_PORT" || echo "工作节点2注册失败"

echo "启动可视化服务器..."
python task_visualization_server.py --port $VIZ_PORT --api-url "http://localhost:$MASTER_PORT" --logs-dir $LOGS_DIR &
VIZ_PID=$!
echo "可视化服务器 PID: $VIZ_PID"
sleep 3

echo "测试可视化服务器..."
curl -s http://localhost:$VIZ_PORT || echo "可视化服务器未启动成功"

echo "系统启动完成，可以在浏览器访问: http://$(hostname -I | awk '{print $1}'):$VIZ_PORT"
echo "按 Ctrl+C 终止所有进程"

# 保持脚本运行，等待信号
wait $MASTER_PID 