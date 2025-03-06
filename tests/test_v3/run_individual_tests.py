#!/usr/bin/env python3
"""
单独运行需要隔离的测试
这些测试会相互干扰，需要单独运行
"""

import os
import sys
import subprocess
import argparse

# 需要单独运行的测试
INDIVIDUAL_TESTS = [
    # 高级路径处理测试
    "tests/test_v3/test_path_handling.py::test_path_verification",
    "tests/test_v3/test_path_handling.py::test_multiple_output_files",
    
    # 任务继续功能测试
    "tests/test_v3/test_continue_feature.py::test_continue_feature_with_toolmanager",
    "tests/test_v3/test_continue_feature.py::test_continue_fallback_mechanism",
    "tests/test_v3/test_continue_feature.py::test_multi_continue_scenario"
]

def run_individual_tests(verbose=False):
    """单独运行每个测试"""
    # 设置命令基础部分
    cmd_base = ["pytest"]
    
    # 添加详细输出选项
    if verbose:
        cmd_base.append("-v")
    
    # 单独运行每个测试
    results = []
    for test in INDIVIDUAL_TESTS:
        cmd = cmd_base + [test]
        print(f"\n运行测试: {' '.join(cmd)}")
        
        # 执行测试命令
        result = subprocess.run(cmd)
        
        # 记录结果
        test_result = {
            "test": test,
            "success": result.returncode == 0
        }
        results.append(test_result)
    
    # 打印总结
    print("\n测试结果总结:")
    for result in results:
        status = "✅ 通过" if result["success"] else "❌ 失败"
        print(f"{status}: {result['test']}")
    
    # 计算失败数
    failed_count = sum(1 for r in results if not r["success"])
    return failed_count

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="单独运行需要隔离的V3重构测试")
    parser.add_argument("--verbose", "-v", action="store_true", help="显示详细输出")
    
    args = parser.parse_args()
    sys.exit(run_individual_tests(args.verbose))