#!/usr/bin/env python3
"""
运行所有与继续功能相关的测试
"""

import os
import sys
import logging
import subprocess

# 配置日志
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('run_continue_tests')

def run_test(test_script):
    """运行指定的测试脚本"""
    test_path = os.path.join(os.getcwd(), 'output', test_script)
    logger.info(f"运行测试: {test_script}")
    
    try:
        # 运行测试
        result = subprocess.run(['python', test_path], 
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.PIPE,
                                text=True,
                                check=True)
        
        # 输出结果
        logger.info(f"测试 {test_script} 成功")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"测试 {test_script} 失败: {e}")
        logger.error(f"输出: {e.stdout}")
        logger.error(f"错误: {e.stderr}")
        return False

def run_all_continue_tests():
    """运行所有与继续功能相关的测试"""
    # 测试脚本列表
    test_scripts = [
        'test_continue_feature.py',
        'test_task_executor_continue.py',
        'test_multiple_continue.py'
    ]
    
    # 运行结果
    results = {}
    
    # 运行测试
    for script in test_scripts:
        results[script] = run_test(script)
    
    # 输出总结
    logger.info("测试结果汇总:")
    passed = 0
    for script, result in results.items():
        status = "通过" if result else "失败"
        logger.info(f"  {script}: {status}")
        if result:
            passed += 1
    
    success_rate = passed / len(test_scripts) * 100
    logger.info(f"通过率: {success_rate:.2f}% ({passed}/{len(test_scripts)})")
    
    # 返回成功标志
    return passed == len(test_scripts)

if __name__ == "__main__":
    success = run_all_continue_tests()
    sys.exit(0 if success else 1)