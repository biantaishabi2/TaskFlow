# TaskPlanner V3 Refactor 测试套件

本目录包含针对 TaskPlanner V3 重构版本的测试用例，主要覆盖以下改进功能：

1. Gemini 任务状态判断改进
2. 路径处理优化
3. 工具调用集成
4. 任务自动继续功能

## 测试文件结构

- `test_gemini_analyzer.py` - 测试 Gemini 分析器的任务状态判断功能
- `test_claude_input_tool.py` - 测试 Claude 输入工具及工具管理器
- `test_task_executor.py` - 测试任务执行器的核心功能
- `test_continue_feature.py` - 测试任务自动继续功能
- `test_path_handling.py` - 测试路径处理和验证功能
- `conftest.py` - 共享测试配置和 fixtures
- `run_tests.py` - 用于运行所有测试的脚本

## 运行测试

可以使用以下命令运行测试：

```bash
# 运行所有测试
python tests/test_v3/run_tests.py

# 运行特定类型的测试
python tests/test_v3/run_tests.py --type gemini
python tests/test_v3/run_tests.py --type tool
python tests/test_v3/run_tests.py --type executor
python tests/test_v3/run_tests.py --type continue
python tests/test_v3/run_tests.py --type path

# 显示详细输出
python tests/test_v3/run_tests.py --verbose

# 生成覆盖率报告
python tests/test_v3/run_tests.py --coverage

# 生成HTML覆盖率报告并指定输出目录
python tests/test_v3/run_tests.py --coverage --output-dir coverage_reports
```

也可以直接使用 pytest 运行：

```bash
# 运行所有测试
pytest tests/test_v3/

# 运行特定测试文件
pytest tests/test_v3/test_gemini_analyzer.py

# 生成覆盖率报告
pytest tests/test_v3/ --cov=task_planner.core --cov=task_planner.util --cov=task_planner.vendor.claude_client.agent_tools --cov-report=html
```

## 测试依赖

运行这些测试需要以下依赖：

```
pytest
pytest-mock
pytest-asyncio
pytest-cov
```

可以通过以下命令安装：

```bash
pip install pytest pytest-mock pytest-asyncio pytest-cov
```