#!/usr/bin/env python3
"""
运行已验证通过的测试
"""

import os
import sys
import subprocess
import argparse

# 已验证通过的测试
VERIFIED_TESTS = [
    # 基础路径处理测试 (已验证)
    "tests/test_v3/test_path_handling.py::test_absolute_path_handling",
    "tests/test_v3/test_path_handling.py::test_relative_path_conversion",
    "tests/test_v3/test_path_handling.py::test_context_dir_path_handling",
    
    # Gemini分析器测试 (已验证)
    "tests/test_v3/mock_gemini_test.py::test_detect_task_type",
    "tests/test_v3/mock_gemini_test.py::test_mock_analyze"
    
    # 高级测试需要单独运行
    # "tests/test_v3/test_path_handling.py::test_path_verification",
    # "tests/test_v3/test_path_handling.py::test_multiple_output_files",
    # "tests/test_v3/test_continue_feature.py::test_continue_feature_with_toolmanager",
    # "tests/test_v3/test_continue_feature.py::test_continue_fallback_mechanism",
    # "tests/test_v3/test_continue_feature.py::test_multi_continue_scenario"
]

def run_verified_tests(verbose=False):
    """运行已验证通过的测试"""
    # 设置命令基础部分
    cmd_base = ["pytest"]
    
    # 添加详细输出选项
    if verbose:
        cmd_base.append("-v")
    
    # 添加所有已验证的测试
    cmd = cmd_base + VERIFIED_TESTS
    
    # 执行测试命令
    print(f"运行已验证的测试: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    
    return result.returncode

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="运行已验证通过的V3重构测试")
    parser.add_argument("--verbose", "-v", action="store_true", help="显示详细输出")
    
    args = parser.parse_args()
    sys.exit(run_verified_tests(args.verbose))