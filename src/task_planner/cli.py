#!/usr/bin/env python
import argparse
import sys
import os
import importlib.util
import time
import json
from datetime import datetime
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('task_planner_cli')

# 这个函数用于动态导入模块
def import_module_from_path(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def main():
    parser = argparse.ArgumentParser(
        description='任务拆分与执行系统CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例用法:
  # 执行单个任务
  task-planner execute "设计一个Python Web应用程序"
  task-planner execute -f task_description.txt --logs-dir my_logs
  
  # 仅进行任务规划拆分
  task-planner plan "开发一个数据分析流程" 
  task-planner plan -f complex_task.txt --output custom_output
  
  # 执行已拆分的子任务
  task-planner run-subtasks -f subtasks.json
  
  # 运行分布式任务系统
  task-planner distributed --mode master --api-port 5000 --task "创建一个博客系统"
  task-planner distributed --mode worker --api-port 5001
  
  # 运行可视化服务器
  task-planner visualization --port 8080 --api-url http://localhost:5000
'''
    )
    subparsers = parser.add_subparsers(dest='command', help='要运行的命令')
    
    # API服务器命令
    api_parser = subparsers.add_parser('api', 
        help='运行任务API服务器',
        description='运行任务API服务器，提供HTTP接口访问任务系统功能',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  # 在默认端口(9000)运行API服务器
  task-planner api
  
  # 在指定端口运行API服务器
  task-planner api --port 8000
  
  # 指定日志目录
  task-planner api --port 8000 --logs-dir custom_logs
'''
    )
    api_parser.add_argument('--port', type=int, default=9000,
                           help='API服务端口号(默认: 9000)')
    api_parser.add_argument('--logs-dir', default='logs',
                           help='日志目录(默认: logs)')
    
    # 可视化服务器命令
    viz_parser = subparsers.add_parser('visualization', 
        help='运行可视化服务器',
        description='运行任务可视化Web服务器，用于展示任务执行状态和结果',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  # 在8080端口运行可视化服务器，连接到本地API
  task-planner visualization --port 8080 --api-url http://localhost:5000
  
  # 连接到远程API服务
  task-planner visualization --port 8080 --api-url http://192.168.1.100:5000
'''
    )
    viz_parser.add_argument('--port', type=int, required=True,
                           help='Web服务器端口号')
    viz_parser.add_argument('--api-url', type=str, required=True,
                           help='任务API服务URL地址')
    
    # 单个任务执行命令
    task_parser = subparsers.add_parser('execute', 
        help='执行单个任务',
        description='执行单个复杂任务，包括任务分析、拆分和执行',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  # 直接输入任务描述
  task-planner execute "设计一个Python Web应用程序"
  
  # 从文件读取任务描述
  task-planner execute -f task_description.txt
  
  # 指定自定义日志目录
  task-planner execute "创建数据分析报告" --logs-dir my_project_logs
  
  # 从文件读取任务并指定日志目录
  task-planner execute -f complex_task.txt --logs-dir custom_logs
  
  # 使用Claude执行器而不是默认的AG2
  task-planner execute "创建数据分析报告" --use-claude
'''
    )
    task_parser.add_argument('task', nargs='?', 
                            help='任务描述文本(如不提供，将提示输入)')
    task_parser.add_argument('-f', '--file', 
                            help='任务描述文件路径，从文件读取任务内容')
    task_parser.add_argument('--logs-dir', help='日志保存目录(默认: logs)', 
                            default='logs')
    task_parser.add_argument('--use-claude', action='store_true',
                            help='使用Claude作为执行器(默认使用AG2)')
    
    # 任务规划命令
    plan_parser = subparsers.add_parser('plan', 
        help='仅规划任务分解',
        description='进行任务分析和拆分，但不执行任务',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  # 直接输入任务描述进行规划
  task-planner plan "开发一个数据分析流程"
  
  # 从文件读取任务描述
  task-planner plan -f complex_task.txt
  
  # 指定自定义输出目录
  task-planner plan "设计一个电子商务网站" --output ecommerce_plan
  
  # 规划结果将保存为两个JSON文件:
  # - task_analysis.json: 包含任务的综合分析
  # - task_breakdown.json: 包含拆分后的子任务列表
'''
    )
    plan_parser.add_argument('task', nargs='?', 
                            help='任务描述文本(如不提供，将提示输入)')
    plan_parser.add_argument('-f', '--file', 
                            help='任务描述文件路径，从文件读取任务内容')
    plan_parser.add_argument('--output', help='结果输出目录(默认: output)', 
                            default='output')
    
    # 执行预定义子任务命令
    subtasks_parser = subparsers.add_parser('run-subtasks',
        help='执行子任务列表',
        description='执行已分解的子任务列表',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  # 执行子任务文件中的所有任务
  task-planner run-subtasks subtasks.json
  
  # 指定自定义日志目录
  task-planner run-subtasks subtasks.json --logs-dir my_subtasks_logs
  
  # 使用Claude执行器而不是默认的AG2
  task-planner run-subtasks subtasks.json --use-claude
'''
    )
    subtasks_parser.add_argument('subtasks_file',
                                help='包含子任务列表的JSON文件路径')
    subtasks_parser.add_argument('--logs-dir', help='日志保存目录(默认: logs)',
                                default='logs')
    subtasks_parser.add_argument('--use-claude', action='store_true',
                                help='使用Claude作为执行器(默认使用AG2)')
    subtasks_parser.add_argument('--start-from', 
                                help='指定从哪个子任务ID开始执行',
                                default=None)
    
    args = parser.parse_args()
    
    # 确保脚本可以找到正确的模块
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    if args.command == 'api':
        # 导入API服务器模块
        sys.path.insert(0, base_dir)
        from task_planner.server.task_api_server import app

        # 确保日志目录存在
        os.makedirs(args.logs_dir, exist_ok=True)
        
        # 启动API服务器
        print(f"启动任务API服务器，端口: {args.port}")
        app.run(host='0.0.0.0', port=args.port)
            
    elif args.command == 'visualization':
        # 动态导入模块
        module_path = os.path.join(base_dir, 'src', 'server', 'task_visualization_server.py')
        viz_module = import_module_from_path('visualization', module_path)
        
        # 重构命令行参数
        sys.argv = [sys.argv[0]]
        for k, v in vars(args).items():
            if k not in ['command'] and v is not None:
                if isinstance(v, bool):
                    if v:
                        sys.argv.append(f'--{k}')
                else:
                    sys.argv.append(f'--{k}')
                    sys.argv.append(str(v))
                    
        # 调用原始模块的main函数
        if hasattr(viz_module, 'main'):
            viz_module.main()
        else:
            print("Error: 找不到可视化服务器模块的main函数")
    
    elif args.command == 'execute':
        try:
            # 动态导入TaskDecompositionSystem
            sys.path.insert(0, base_dir)
            from task_planner.core.task_decomposition_system import TaskDecompositionSystem
            
            # 获取任务文本
            task_text = ""
            if args.file:
                with open(args.file, 'r', encoding='utf-8') as f:
                    task_text = f.read()
            elif args.task:
                task_text = args.task
            else:
                task_text = input("请输入任务描述: ")
                
            # 创建日志目录
            os.makedirs(args.logs_dir, exist_ok=True)
            
            # 初始化任务拆分系统
            system = TaskDecompositionSystem(
                logs_dir=args.logs_dir,
                use_claude=args.use_claude
            )
            
            # 执行任务
            print(f"开始执行任务...\n{'-'*40}\n{task_text}\n{'-'*40}")
            print(f"使用{'Claude' if args.use_claude else 'AG2'}执行器")
            start_time = time.time()
            
            result = system.execute_complex_task(task_text)
            
            # 显示结果
            execution_time = time.time() - start_time
            print(f"\n任务执行完成，总耗时: {execution_time:.2f}秒")
            
            success = result.get('success', False)
            status = "成功" if success else "失败"
            print(f"任务状态: {status}")
            
            if 'result' in result and 'summary' in result['result']:
                print("\n结果摘要:")
                print("-" * 40)
                print(result['result']['summary'])
                print("-" * 40)
            
            # 显示任务拆分情况
            if 'result' in result and 'details' in result['result'] and 'subtasks' in result['result']['details']:
                subtasks = result['result']['details']['subtasks']
                print("\n任务拆分:")
                print("-" * 40)
                for i, subtask in enumerate(subtasks):
                    status = "成功" if subtask.get('success', False) else "失败"
                    print(f"{i+1}. {subtask.get('name', f'子任务 {i+1}')} - {status}")
                print("-" * 40)
            
            # 显示结果保存位置
            task_id = result.get('task_id', f"task_{int(time.time())}")
            result_dir = os.path.join(args.logs_dir, task_id)
            if os.path.exists(result_dir):
                print(f"\n结果已保存到: {result_dir}")
        
        except ImportError as e:
            print(f"Error: 无法导入必要的模块: {e}")
    
    elif args.command == 'plan':
        try:
            # 动态导入TaskPlanner
            sys.path.insert(0, base_dir)
            from task_planner.core.task_planner import TaskPlanner
            from task_planner.core.context_management import ContextManager
            import json
            
            # 获取任务文本
            task_text = ""
            if args.file:
                with open(args.file, 'r', encoding='utf-8') as f:
                    task_text = f.read()
            elif args.task:
                task_text = args.task
            else:
                task_text = input("请输入任务描述: ")
            
            # 创建输出目录
            os.makedirs(args.output, exist_ok=True)
            
            # 初始化上下文管理器
            context_manager = ContextManager()
            
            # 创建规划器实例
            planner = TaskPlanner(task_text, context_manager=context_manager)
            
            # 执行任务分析
            print("\n===== 任务分析中... =====")
            analysis = planner.analyze_task()
            
            # 执行任务拆分
            print("\n===== 任务拆分中... =====")
            subtasks = planner.break_down_task(analysis)
            
            # 显示拆分结果
            for i, subtask in enumerate(subtasks):
                print(f"\n子任务 {i+1}:")
                print(f"  名称: {subtask['name']}")
                print(f"  描述: {subtask['description']}")
                print(f"  优先级: {subtask.get('priority', 'normal')}")
                if 'dependencies' in subtask and subtask['dependencies']:
                    print(f"  依赖: {', '.join(subtask['dependencies'])}")
            
            # 保存结果到文件
            with open(os.path.join(args.output, "task_analysis.json"), "w", encoding="utf-8") as f:
                json.dump(analysis, f, indent=2, ensure_ascii=False)
            
            with open(os.path.join(args.output, "task_breakdown.json"), "w", encoding="utf-8") as f:
                json.dump(subtasks, f, indent=2, ensure_ascii=False)
            
            print("\n分析和拆分结果已保存到:")
            print(f"- {os.path.join(args.output, 'task_analysis.json')}")
            print(f"- {os.path.join(args.output, 'task_breakdown.json')}")
            
        except ImportError as e:
            print(f"Error: 无法导入必要的模块: {e}")
    
    elif args.command == 'run-subtasks':
        try:
            # 动态导入需要的模块
            sys.path.insert(0, base_dir)
            from task_planner.core.task_decomposition_system import TaskDecompositionSystem
            import json
            
            # 读取子任务文件
            with open(args.subtasks_file, 'r', encoding='utf-8') as f:
                subtasks = json.load(f)
                
            # 如果指定了起始任务
            if args.start_from:
                # 找到起始任务的索引
                start_index = next((i for i, task in enumerate(subtasks) 
                                  if task['id'] == args.start_from), None)
                if start_index is None:
                    logger.error(f"找不到指定的起始任务ID: {args.start_from}")
                    return 1
                # 只执行从该任务开始的子任务
                subtasks = subtasks[start_index:]
                logger.info(f"从任务 {args.start_from} 开始执行，共 {len(subtasks)} 个任务")
            
            # 执行子任务
            system = TaskDecompositionSystem(
                logs_dir=args.logs_dir,
                use_claude=args.use_claude
            )
            final_result = system.execute_predefined_subtasks(subtasks)
            
            # 输出结果摘要
            print("\n执行结果摘要:")
            print(f"总子任务数: {len(subtasks)}")
            print(f"成功: {final_result['success_count']}")
            print(f"失败: {final_result['failure_count']}")
            print(f"最终状态: {'成功' if final_result['success'] else '失败'}")
            
            return 0
            
        except Exception as e:
            logger.error(f"子任务执行失败: {str(e)}")
            return 1
    
    else:
        parser.print_help()
        
if __name__ == '__main__':
    sys.exit(main())