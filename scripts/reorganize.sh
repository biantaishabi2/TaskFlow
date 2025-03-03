#\!/bin/bash

# 创建目录结构
mkdir -p src/{core,distributed,server,utils} examples tests scripts

# 创建包初始化文件
find src -type d -exec touch {}/__init__.py \;
touch examples/__init__.py tests/__init__.py

# 移动核心文件
cp context_management.py src/core/
cp task_decomposition_system.py src/core/
cp task_planner.py src/core/
cp task_executor.py src/core/

# 移动分布式系统和执行器文件
cp distributed_task_decomposition_system.py src/distributed/
cp parallel_task_decomposition_system.py src/distributed/
cp parallel_task_executor.py src/distributed/

# 移动服务器组件
cp task_api_server.py src/server/
cp task_visualization_server.py src/server/
cp task_monitor.py src/server/

# 移动示例文件
cp context_management_example.py examples/
cp task_decomposition_example.py examples/
cp parallel_task_example.py examples/
cp test_complex_task.txt examples/

# 移动测试文件
cp test_context_management.py tests/
cp test_task_decomposition.py tests/
touch tests/conftest.py

# 移动脚本文件
cp run_test.sh scripts/
cp simulate_test.sh scripts/
cp cleanup.sh scripts/

# 确保脚本可执行
chmod +x scripts/*.sh

echo "完成重组项目结构！"
