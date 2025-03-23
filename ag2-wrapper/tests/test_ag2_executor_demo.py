import sys
import os

# 修改后的路径设置
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 动态获取项目根目录
sys.path.extend([
    PROJECT_ROOT,  # 添加项目根目录到路径
    os.path.join(PROJECT_ROOT, "ag2-wrapper")  # 确保ag2-wrapper目录在路径中
])

from ag2_wrapper.core.ag2_two_agent_executor import AG2TwoAgentExecutor
from ag2_wrapper.core.config import ConfigManager

# 动态验证路径
try:
    from task_planner.core.context_management import TaskContext
    print("✅ 成功导入TaskContext")
except ImportError:
    print("❌ 导入失败，当前Python路径：")
    print('\n'.join(sys.path))
    exit(1)

# 初始化配置
config = ConfigManager()

# 测试代码
executor = AG2TwoAgentExecutor(config=config)
context = TaskContext(task_id="test")

# 修改这部分，让用户代理发起对话
result = executor.executor.initiate_chat(
    executor.assistant,  # 助手作为接收者
    message="请将'测试一下'写入文件'test.txt'中",
)

print(f"执行结果：{result.chat_history[-1]['content'] if result.chat_history else 'No response'}")

# 测试一个实际的任务场景
def test_practical_task():
    config = ConfigManager()
    executor = AG2TwoAgentExecutor(config=config)
    
    # 创建一个模拟的任务上下文
    context = TaskContext(task_id="data_analysis_task_001")
    context.update_local('project_path', '/path/to/project')
    context.update_local('data_path', '/path/to/data')
    
    # 定义一个实际的任务
    task_definition = {
        "id": "data_analysis_task_001",
        "name": "数据分析报告生成",
        "description": "分析销售数据并生成月度报告",
        "input_files": {
            "sales_data": "/path/to/data/sales.csv",
            "customer_data": "/path/to/data/customers.csv"
        },
        "output_files": {
            "report": "/path/to/output/monthly_report.pdf",
            "summary": "/path/to/output/summary.json"
        },
        "success_criteria": [
            "报告必须包含销售趋势分析",
            "必须生成客户购买行为的可视化图表",
            "输出文件格式必须符合规范"
        ],
        "parameters": {
            "time_period": "2024-02",
            "analysis_depth": "detailed",
            "required_metrics": ["sales_growth", "customer_retention", "product_performance"]
        }
    }
    
    # 模拟一个复杂的任务提示
    complex_prompt = """
    请分析2024年2月的销售数据，重点关注以下方面：
    1. 销售增长趋势分析
    2. 客户留存率分析
    3. 产品表现评估
    
    要求：
    - 使用pandas进行数据处理
    - 使用matplotlib生成可视化图表
    - 生成PDF格式的分析报告
    - 输出JSON格式的数据摘要
    """
    
    # 执行任务
    result = executor.execute(
        prompt=complex_prompt,
        task_definition=task_definition,
        task_context=context
    )
    
    print("任务执行结果：")
    print(f"状态: {result['status']}")
    print(f"输出: {result['output']}")
    print(f"任务状态: {result['task_status']}")

def test_multi_step_task():
    config = ConfigManager()
    executor = AG2TwoAgentExecutor(config=config)
    context = TaskContext(task_id="web_app_development_001")
    
    # 定义一个包含多个子任务的复杂任务
    task_definition = {
        "id": "web_app_development_001",
        "name": "开发一个简单的Web应用",
        "description": "开发一个带有用户认证的Todo应用",
        "subtasks": [
            {
                "id": "setup_001",
                "name": "项目初始化",
                "description": "设置项目基础结构",
                "output_files": {
                    "requirements": "./requirements.txt",
                    "readme": "./README.md",
                    "config": "./config.py"
                },
                "success_criteria": [
                    "创建基本项目结构",
                    "配置依赖管理",
                    "初始化git仓库"
                ]
            },
            {
                "id": "database_002",
                "name": "数据库设计",
                "description": "设计并实现数据库模型",
                "dependencies": ["setup_001"],
                "output_files": {
                    "models": "./app/models.py",
                    "migrations": "./migrations/initial.py"
                },
                "success_criteria": [
                    "实现用户模型",
                    "实现Todo项模型",
                    "创建数据库迁移"
                ]
            },
            {
                "id": "api_003",
                "name": "API实现",
                "description": "实现RESTful API接口",
                "dependencies": ["database_002"],
                "output_files": {
                    "routes": "./app/routes.py",
                    "views": "./app/views.py"
                },
                "success_criteria": [
                    "实现用户认证API",
                    "实现Todo CRUD API",
                    "添加API文档"
                ]
            }
        ],
        "execution_order": {
            "type": "sequential",
            "order": ["setup_001", "database_002", "api_003"]
        },
        "global_parameters": {
            "framework": "flask",
            "database": "sqlite",
            "auth_method": "jwt"
        },
        "success_criteria": [
            "所有子任务完成",
            "API测试通过",
            "文档完整"
        ]
    }
    
    # 设置任务上下文
    context.update_local('project_root', os.path.join(PROJECT_ROOT, 'demo_output/web_app'))
    context.update_local('template_path', os.path.join(PROJECT_ROOT, 'templates'))
    context.update_local('current_subtask', 'setup_001')
    
    # 执行第一个子任务
    setup_prompt = """
    请初始化一个Flask Web应用项目：
    1. 创建基本的项目结构
    2. 设置requirements.txt，包含必要的依赖
    3. 创建README.md文件，描述项目结构和启动方法
    4. 创建基本的配置文件
    
    请确保遵循Python最佳实践和Flask项目标准结构。
    """
    
    result = executor.execute(
        prompt=setup_prompt,
        task_definition=task_definition['subtasks'][0],  # 只执行第一个子任务
        task_context=context
    )
    
    print("\n多步骤任务执行结果（第一阶段）：")
    print(f"状态: {result['status']}")
    print(f"输出: {result['output']}")
    print(f"任务状态: {result['task_status']}")

if __name__ == "__main__":
    test_multi_step_task() 