#!/bin/bash

# 设置变量 - 使用全新的端口号
MASTER_PORT=23456
WORKER1_PORT=23457
WORKER2_PORT=23458
VIZ_PORT=23459
LOGS_DIR="./logs"

# 确保日志目录存在
mkdir -p $LOGS_DIR

# 先终止可能已运行的进程
echo "清理可能运行的旧进程..."
pkill -f "python.*distributed_task_decomposition_system.py" || true
pkill -f "python.*task_visualization_server.py" || true
sleep 2  # 等待进程完全终止

# 定义清理函数
cleanup() {
    echo "正在终止所有进程..."
    pkill -f "python.*distributed_task_decomposition_system.py"
    pkill -f "python.*task_visualization_server.py"
    exit 0
}

# 注册信号处理程序
trap cleanup SIGINT

# 打印提示信息
echo "===== 分布式任务拆分与执行系统测试 ====="
echo "主节点端口: $MASTER_PORT"
echo "工作节点1端口: $WORKER1_PORT"
echo "工作节点2端口: $WORKER2_PORT"
echo "可视化服务器端口: $VIZ_PORT"
echo "日志目录: $LOGS_DIR"
echo

# 启动主节点
echo "启动主节点..."
python distributed_task_decomposition_system.py --mode master --api-port $MASTER_PORT --workers 2 --logs-dir $LOGS_DIR > master.log 2>&1 &
MASTER_PID=$!
echo "主节点PID: $MASTER_PID"
echo "- API地址: http://localhost:$MASTER_PORT"
echo

# 等待主节点启动
sleep 3

# 启动工作节点1
echo "启动工作节点1..."
python distributed_task_decomposition_system.py --mode worker --api-port $WORKER1_PORT --max-threads 2 --logs-dir $LOGS_DIR > worker1.log 2>&1 &
WORKER1_PID=$!
echo "工作节点1 PID: $WORKER1_PID"
echo "- API地址: http://localhost:$WORKER1_PORT"
echo

# 启动工作节点2
echo "启动工作节点2..."
python distributed_task_decomposition_system.py --mode worker --api-port $WORKER2_PORT --max-threads 2 --logs-dir $LOGS_DIR > worker2.log 2>&1 &
WORKER2_PID=$!
echo "工作节点2 PID: $WORKER2_PID"
echo "- API地址: http://localhost:$WORKER2_PORT"
echo

# 等待工作节点启动
sleep 3

# 注册工作节点到主节点
echo "注册工作节点到主节点..."
echo "注册工作节点1..."
python distributed_task_decomposition_system.py --mode master --api-port $MASTER_PORT --register "http://localhost:$WORKER1_PORT" || echo "工作节点1注册失败"
echo "注册工作节点2..."
python distributed_task_decomposition_system.py --mode master --api-port $MASTER_PORT --register "http://localhost:$WORKER2_PORT" || echo "工作节点2注册失败"
echo "注册完成"

# 启动可视化服务器
echo "启动可视化服务器..."
python task_visualization_server.py --port $VIZ_PORT --api-url "http://localhost:$MASTER_PORT" --logs-dir $LOGS_DIR &
VIZ_PID=$!
echo "可视化服务器 PID: $VIZ_PID"
echo "- Web界面: http://localhost:$VIZ_PORT 或 http://$(hostname -I | awk '{print $1}'):$VIZ_PORT"
echo

# 等待可视化服务器启动
sleep 3

# 提交测试任务
echo "提交复杂测试任务..."
python distributed_task_decomposition_system.py --mode master --api-port $MASTER_PORT --task test_complex_task.txt --file --async > task.log 2>&1

echo
echo "系统已启动，可以在浏览器中访问可视化界面: http://localhost:$VIZ_PORT"
echo "按下 Ctrl+C 终止测试"

# 保持脚本运行
while true; do
    sleep 1
done
