#!/usr/bin/env python
import argparse
import sys
import os
import importlib.util

# 这个函数用于动态导入模块
def import_module_from_path(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def main():
    parser = argparse.ArgumentParser(description='任务拆分与执行系统CLI')
    subparsers = parser.add_subparsers(dest='command', help='要运行的命令')
    
    # 分布式系统命令
    distributed_parser = subparsers.add_parser('distributed', help='运行分布式任务系统')
    distributed_parser.add_argument('--mode', choices=['master', 'worker'], required=True)
    distributed_parser.add_argument('--api-port', type=int, required=True)
    distributed_parser.add_argument('--workers', type=int, default=2)
    distributed_parser.add_argument('--task', type=str)
    distributed_parser.add_argument('--file', action='store_true')
    distributed_parser.add_argument('--async', action='store_true', dest='is_async')
    
    # 可视化服务器命令
    viz_parser = subparsers.add_parser('visualization', help='运行可视化服务器')
    viz_parser.add_argument('--port', type=int, required=True)
    viz_parser.add_argument('--api-url', type=str, required=True)
    
    args = parser.parse_args()
    
    # 确保脚本可以找到正确的模块
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    if args.command == 'distributed':
        # 动态导入模块
        module_path = os.path.join(base_dir, 'src', 'distributed', 'distributed_task_decomposition_system.py')
        distributed_module = import_module_from_path('distributed_system', module_path)
        
        # 重构命令行参数以适应原始脚本的期望
        sys.argv = [sys.argv[0]]
        for k, v in vars(args).items():
            if k not in ['command'] and v is not None:
                if isinstance(v, bool):
                    if v:  # 只添加为真的布尔标志
                        sys.argv.append(f'--{k}')
                else:
                    sys.argv.append(f'--{k}')
                    sys.argv.append(str(v))
        
        # 调用原始模块的main函数
        if hasattr(distributed_module, 'main'):
            distributed_module.main()
        else:
            print("Error: 找不到分布式系统模块的main函数")
            
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
    else:
        parser.print_help()
        
if __name__ == '__main__':
    main()