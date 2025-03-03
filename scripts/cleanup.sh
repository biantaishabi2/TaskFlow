#!/bin/bash

echo "彻底清理所有相关进程..."

# 查找并终止所有Python进程
echo "终止所有Python相关进程..."
sudo pkill -9 -f "python.*distributed_task_decomposition_system.py" || true
sudo pkill -9 -f "python.*task_visualization_server.py" || true
sleep 2

# 检查进程是否仍然存在
echo "验证进程已终止..."
ps aux | grep -E "distributed_task_decomposition_system.py|task_visualization_server.py" | grep -v grep

# 检查所有相关端口
echo "检查端口状态..."
for port in 5001 5002 23456 23457 23458 23459; do
    echo -n "端口 $port: "
    netstat -tuln | grep ":$port " || echo "空闲"
done

echo "清理完成" 