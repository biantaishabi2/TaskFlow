#!/usr/bin/env python3
"""
运行完整的V3测试套件
"""

import os
import sys
import subprocess
import argparse
import time

# 基础测试 - 可以一起运行的测试
BASIC_TESTS = [
    # 基础路径处理测试
    "tests/test_v3/test_path_handling.py::test_absolute_path_handling",
    "tests/test_v3/test_path_handling.py::test_relative_path_conversion",
    "tests/test_v3/test_path_handling.py::test_context_dir_path_handling",
    
    # Gemini分析器测试
    "tests/test_v3/mock_gemini_test.py::test_detect_task_type",
    "tests/test_v3/mock_gemini_test.py::test_mock_analyze"
]

# 需要单独运行的高级测试
ADVANCED_TESTS = [
    # 高级路径处理测试
    "tests/test_v3/test_path_handling.py::test_path_verification",
    "tests/test_v3/test_path_handling.py::test_multiple_output_files",
    
    # 任务继续功能测试
    "tests/test_v3/test_continue_feature.py::test_continue_feature_with_toolmanager",
    "tests/test_v3/test_continue_feature.py::test_continue_fallback_mechanism",
    "tests/test_v3/test_continue_feature.py::test_multi_continue_scenario",
    "tests/test_v3/test_continue_feature.py::test_needs_more_info_status"
]

# 新增的边界条件和集成测试
INTEGRATION_TESTS = [
    # 端到端测试
    "tests/test_v3/test_end_to_end.py::test_end_to_end_flow",
    "tests/test_v3/test_end_to_end.py::test_error_handling_and_recovery",
    
    # 边界条件测试
    "tests/test_v3/test_edge_cases.py::test_empty_task_handling",
    "tests/test_v3/test_edge_cases.py::test_minimal_task_execution",
    "tests/test_v3/test_edge_cases.py::test_extremely_long_instruction",
    "tests/test_v3/test_edge_cases.py::test_timeout_handling",
    "tests/test_v3/test_edge_cases.py::test_circular_dependency_handling",
    "tests/test_v3/test_edge_cases.py::test_special_characters_handling",
    "tests/test_v3/test_edge_cases.py::test_extremely_large_output"
]

def run_test_group(tests, verbose=False, group_name=""):
    """运行一组测试"""
    print(f"\n=== 运行{group_name}测试 ({len(tests)}个) ===\n")
    
    # 设置命令基础部分
    cmd_base = ["pytest"]
    
    # 添加详细输出选项
    if verbose:
        cmd_base.append("-v")
    
    # 一起运行这组测试
    cmd = cmd_base + tests
    
    # 执行测试命令
    print(f"执行命令: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    
    return result.returncode

def run_individual_tests(tests, verbose=False, group_name=""):
    """单独运行每个测试"""
    print(f"\n=== 单独运行{group_name}测试 ({len(tests)}个) ===\n")
    
    # 设置命令基础部分
    cmd_base = ["pytest"]
    
    # 添加详细输出选项
    if verbose:
        cmd_base.append("-v")
    
    # 单独运行每个测试
    results = []
    for test in tests:
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
        
        # 测试之间稍微停顿，避免资源争用
        time.sleep(0.2)
    
    # 打印分组结果总结
    print(f"\n{group_name}测试结果总结:")
    for result in results:
        status = "✅ 通过" if result["success"] else "❌ 失败"
        print(f"{status}: {result['test']}")
    
    # 计算失败数
    failed_count = sum(1 for r in results if not r["success"])
    return failed_count

def run_all_tests(verbose=False):
    """运行所有测试"""
    print("\n=================== TaskPlanner V3 测试套件 ===================")
    print("测试总数:", len(BASIC_TESTS) + len(ADVANCED_TESTS) + len(INTEGRATION_TESTS))
    
    # 测试结果
    results = {}
    
    # 1. 运行基础测试（一起运行）
    results["basic"] = run_test_group(BASIC_TESTS, verbose, "基础")
    
    # 2. 运行高级测试（单独运行每个）
    results["advanced"] = run_individual_tests(ADVANCED_TESTS, verbose, "高级")
    
    # 3. 运行集成测试（单独运行每个）
    results["integration"] = run_individual_tests(INTEGRATION_TESTS, verbose, "集成")
    
    # 打印整体测试结果总结
    print("\n=================== 整体测试结果总结 ===================")
    basic_status = "✅ 通过" if results["basic"] == 0 else "❌ 失败"
    advanced_status = "✅ 通过" if results["advanced"] == 0 else "❌ 失败"
    integration_status = "✅ 通过" if results["integration"] == 0 else "❌ 失败"
    
    print(f"{basic_status}: 基础测试 (返回码: {results['basic']})")
    print(f"{advanced_status}: 高级测试 (失败数: {results['advanced']})")
    print(f"{integration_status}: 集成测试 (失败数: {results['integration']})")
    
    # 计算总失败数
    total_failed = (1 if results["basic"] != 0 else 0) + results["advanced"] + results["integration"]
    
    overall_status = "✅ 全部通过" if total_failed == 0 else f"❌ 失败 ({total_failed})"
    print(f"\n整体状态: {overall_status}")
    
    return total_failed

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="运行TaskPlanner V3完整测试套件")
    parser.add_argument("--verbose", "-v", action="store_true", help="显示详细输出")
    
    args = parser.parse_args()
    sys.exit(run_all_tests(args.verbose))