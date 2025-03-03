#\!/bin/bash

echo "===== 模拟测试分布式任务执行系统 ====="
echo "注意：这个测试不会实际启动进程，只是模拟测试流程和API交互"
echo

# 模拟启动主节点
echo "1. 启动主节点 (8000端口)..."
echo "   python distributed_task_decomposition_system.py --mode master --api-port 8000 --workers 2"
echo 

# 模拟启动工作节点
echo "2. 启动工作节点1 (5001端口)..."
echo "   python distributed_task_decomposition_system.py --mode worker --api-port 5001"
echo 
echo "3. 启动工作节点2 (5002端口)..."
echo "   python distributed_task_decomposition_system.py --mode worker --api-port 5002"
echo 

# 模拟注册工作节点
echo "4. 注册工作节点到主节点..."
echo "   python distributed_task_decomposition_system.py --mode master --api-port 8000 --register \"http://localhost:5001\""
echo "   python distributed_task_decomposition_system.py --mode master --api-port 8000 --register \"http://localhost:5002\""
echo 

# 模拟启动可视化服务器
echo "5. 启动可视化服务器 (9000端口)..."
echo "   python task_visualization_server.py --port 9000 --api-url \"http://localhost:8000\""
echo 

# 模拟提交任务
echo "6. 提交复杂测试任务..."
echo "   python distributed_task_decomposition_system.py --mode master --api-port 8000 --task test_complex_task.txt --file --async"
echo

# 模拟API交互
echo "7. 可用的API端点:"
echo "   主节点:"
echo "   - 健康检查: GET http://localhost:8000/health"
echo "   - 提交任务: POST http://localhost:8000/tasks"
echo "   - 查询任务: GET http://localhost:8000/tasks/<task_id>"
echo "   - 获取任务结果: GET http://localhost:8000/tasks/<task_id>/result"
echo "   - 工作节点列表: GET http://localhost:8000/workers"
echo 
echo "   工作节点:"
echo "   - 健康检查: GET http://localhost:5001/health"
echo "   - 提交子任务: POST http://localhost:5001/tasks"
echo "   - 查询子任务: GET http://localhost:5001/tasks/<task_id>"
echo 
echo "   可视化服务器:"
echo "   - Web界面: http://localhost:9000"
echo "   - 系统概览: GET http://localhost:9000/api/overview"
echo "   - 任务列表: GET http://localhost:9000/api/tasks"
echo "   - 任务详情: GET http://localhost:9000/api/tasks/<task_id>"
echo 

echo "8. 实际测试:"
echo "   运行完整测试: ./run_test.sh"
echo "   之后可访问: http://localhost:9000 查看可视化界面"
echo 
echo "测试完成后可使用以下命令终止所有进程:"
echo "pkill -f \"python.*distributed_task_decomposition_system.py\""
echo "pkill -f \"python.*task_visualization_server.py\""
