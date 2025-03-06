#!/usr/bin/env python3
"""
Run all v3 refactor tests
"""

import os
import sys
import subprocess
import argparse

def run_tests(test_type=None, verbose=False):
    """运行指定类型的测试或所有测试"""
    test_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 设置命令基础部分
    cmd_base = ["pytest"]
    
    # 添加详细输出选项
    if verbose:
        cmd_base.append("-v")
    
    # 如果指定了测试类型，只运行该类型的测试
    if test_type:
        if test_type == "gemini":
            cmd = cmd_base + [os.path.join(test_dir, "test_gemini_analyzer.py")]
        elif test_type == "tool":
            cmd = cmd_base + [os.path.join(test_dir, "test_claude_input_tool.py")]
        elif test_type == "executor":
            cmd = cmd_base + [os.path.join(test_dir, "test_task_executor.py")]
        elif test_type == "continue":
            cmd = cmd_base + [os.path.join(test_dir, "test_continue_feature.py")]
        elif test_type == "path":
            cmd = cmd_base + [os.path.join(test_dir, "test_path_handling.py")]
        else:
            print(f"未知的测试类型: {test_type}")
            return 1
    else:
        # 运行所有测试
        cmd = cmd_base + [test_dir]
    
    # 执行测试命令
    print(f"运行命令: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    
    return result.returncode

def run_coverage(output_dir=None):
    """运行测试并生成覆盖率报告"""
    test_dir = os.path.dirname(os.path.abspath(__file__))
    
    cmd = [
        "pytest", 
        test_dir,
        "--cov=task_planner.core",
        "--cov=task_planner.util",
        "--cov=task_planner.vendor.claude_client.agent_tools"
    ]
    
    # 如果指定了输出目录，则生成HTML报告
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        cmd.append(f"--cov-report=html:{output_dir}")
    else:
        cmd.append("--cov-report=term")
    
    # 执行测试命令
    print(f"运行命令: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    
    return result.returncode

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="运行V3重构测试")
    parser.add_argument("--type", choices=["gemini", "tool", "executor", "continue", "path", "all"], 
                        default="all", help="要运行的测试类型")
    parser.add_argument("--verbose", "-v", action="store_true", help="显示详细输出")
    parser.add_argument("--coverage", action="store_true", help="生成覆盖率报告")
    parser.add_argument("--output-dir", help="覆盖率报告输出目录")
    
    args = parser.parse_args()
    
    if args.coverage:
        sys.exit(run_coverage(args.output_dir))
    else:
        test_type = None if args.type == "all" else args.type
        sys.exit(run_tests(test_type, args.verbose))