#!/usr/bin/env python
import argparse
import sys
import os
import importlib.util
import time
import json
from datetime import datetime

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
    
    args = parser.parse_args()
    
    # 确保脚本可以找到正确的模块
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    if args.command == 'api':
        # 导入API服务器模块
        sys.path.insert(0, base_dir)
        from task_planner.server.task_api_server import app
        import logging

        # 确保日志目录存在
        os.makedirs(args.logs_dir, exist_ok=True)
        
        # 配置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(os.path.join(args.logs_dir, 'task_api_server.log'))
            ]
        )
        logger = logging.getLogger('task_api_server')
        
        # 启动API服务器
        print(f"启动任务API服务器，端口: {args.port}")
        logger.info(f"启动任务API服务器，端口: {args.port}")
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
            
            # 确保日志目录存在
            log_dir = os.path.join(os.getcwd(), args.logs_dir, "subtasks_execution")
            os.makedirs(log_dir, exist_ok=True)
            
            # 读取子任务定义文件
            with open(args.subtasks_file, 'r', encoding='utf-8') as f:
                subtasks = json.load(f)
                
            print("="*50)
            print("预定义子任务执行")
            print("="*50)
            print(f"从文件加载了 {len(subtasks)} 个子任务")
            print(f"使用{'Claude' if args.use_claude else 'AG2'}执行器")
            
            # 初始化任务拆分系统
            system = TaskDecompositionSystem(
                logs_dir=args.logs_dir,
                use_claude=args.use_claude
            )
            
            # 执行任务
            result = system.execute_complex_task({
                'type': 'subtasks_execution',
                'subtasks': subtasks
            })
            
            # 保存执行结果
            results_file = os.path.join(log_dir, f"execution_results_{int(datetime.now().timestamp())}.json")
            with open(results_file, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            print(f"\n执行结果已保存到: {results_file}")
            print("\n执行完成")
            print("="*50)
            
        except ImportError as e:
            print(f"Error: 无法导入必要的模块: {e}")
        except FileNotFoundError:
            print(f"Error: 找不到任务定义文件: {args.subtasks_file}")
        except json.JSONDecodeError:
            print(f"Error: 任务定义文件不是有效的JSON格式: {args.subtasks_file}")
    
    else:
        parser.print_help()
        
if __name__ == '__main__':
    main()