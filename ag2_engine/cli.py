import argparse
import sys
import yaml
import os

from ag2_engine.ag2_executor import AG2Executor

def parse_args():
    parser = argparse.ArgumentParser(description="使用AG2-Agent执行任务")
    
    parser.add_argument(
        "--task", 
        type=str, 
        required=True,
        help="要执行的任务描述"
    )
    
    parser.add_argument(
        "--config", 
        type=str,
        default="configs/ag2_config.yaml",
        help="AG2执行器配置文件路径"
    )
    
    parser.add_argument(
        "--mode", 
        type=str,
        choices=["two_agent", "sequential", "group", "nested", "swarm"],
        default="sequential",
        help="AG2执行器的对话模式"
    )
    
    parser.add_argument(
        "--output", 
        type=str,
        help="输出结果文件路径"
    )
    
    return parser.parse_args()

def main():
    """AG2执行器命令行入口点"""
    args = parse_args()
    
    # 创建AG2执行器
    executor = AG2Executor(
        config_path=args.config,
        mode=args.mode
    )
    
    # 执行任务
    task = {"description": args.task}
    result = executor.execute(task)
    
    # 输出结果
    if args.output:
        with open(args.output, 'w') as f:
            yaml.dump(result, f)
    else:
        print(yaml.dump(result))
    
    return 0

if __name__ == "__main__":
    sys.exit(main())