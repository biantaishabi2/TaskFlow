#!/usr/bin/env python3
"""
并行任务拆分与执行系统示例
展示如何使用并行任务拆分与执行系统处理复杂任务
"""

import os
import time
import json
from task_planner.distributed.parallel_task_decomposition_system import ParallelTaskDecompositionSystem

def run_example(max_workers=4):
    """运行并行任务拆分与执行系统示例"""
    print("="*80)
    print("并行任务拆分与执行系统示例")
    print("="*80)
    
    # 初始化系统
    logs_dir = os.path.join(os.getcwd(), "logs", "parallel_examples")
    system = ParallelTaskDecompositionSystem(logs_dir=logs_dir, max_workers=max_workers)
    
    # 定义一个复杂任务，包含多个可并行的子任务
    task_description = """
设计并实现一个简单的Python数据处理管道，包含以下组件：

1. 数据收集模块：
   - 模拟从多个源获取数据
   - 支持CSV、JSON和XML格式的数据
   - 实现数据源配置和注册机制
   
2. 数据转换模块：
   - 提供数据清洗功能：处理缺失值、异常值检测
   - 实现数据格式转换：日期标准化、类型转换
   - 支持数据聚合和分组操作
   
3. 数据存储模块：
   - 支持将处理后的数据保存为CSV、JSON或SQLite
   - 实现数据版本管理，支持回滚
   - 提供数据压缩和加密选项
   
4. 监控与报告模块：
   - 记录处理过程中的事件和性能指标
   - 生成处理摘要报告
   - 提供错误通知机制

请提供完整的Python代码实现以上模块，包括接口定义、类实现和示例用法。
代码应遵循面向对象设计原则，易于扩展和维护。
"""
    
    print("\n任务描述:")
    print("-" * 40)
    print(task_description)
    print("-" * 40)
    
    # 执行复杂任务
    print(f"\n开始执行任务，最大并行线程数: {max_workers}...")
    start_time = time.time()
    
    result = system.execute_complex_task(task_description, parallel_threshold=2)
    
    # 显示结果
    execution_time = time.time() - start_time
    print(f"\n任务执行完成，总耗时: {execution_time:.2f}秒")
    
    success = result.get('success', False)
    status = "成功" if success else "失败"
    print(f"任务状态: {status}")
    
    # 显示并行执行统计
    if 'stats' in result:
        stats = result['stats']
        print("\n并行执行统计:")
        print(f"理论顺序执行时间: {stats.get('sequential_time', 0):.2f}秒")
        print(f"实际并行执行时间: {stats.get('parallel_time', 0):.2f}秒")
        print(f"加速比: {stats.get('speedup', 0):.2f}x")
        print(f"并行效率: {stats.get('efficiency', 0):.2f}")
        if stats.get('sequential_time', 0) > 0 and stats.get('parallel_time', 0) > 0:
            time_saved = stats['sequential_time'] - stats['parallel_time']
            saved_percent = (time_saved / stats['sequential_time']) * 100 if stats['sequential_time'] > 0 else 0
            print(f"节省时间: {time_saved:.2f}秒 ({saved_percent:.1f}%)")
    
    if 'result' in result and 'summary' in result['result']:
        print("\n结果摘要:")
        print("-" * 40)
        print(result['result']['summary'])
        print("-" * 40)
    
    # 显示任务拆分情况
    if 'subtasks' in result:
        subtasks = result['subtasks']
        print("\n任务拆分:")
        print("-" * 40)
        for i, subtask in enumerate(subtasks):
            status = "成功" if subtask.get('success', False) else "失败"
            print(f"{i+1}. {subtask.get('name', f'子任务 {i+1}')} - {status}")
        print("-" * 40)
    
    # 显示生成的工件
    if 'artifacts' in result:
        artifacts = result['artifacts']
        print("\n生成的工件:")
        print("-" * 40)
        for name, content in artifacts.items():
            print(f"- {name}")
        print("-" * 40)
    
    # 显示结果保存位置
    task_id = result.get('task_id', f"task_{int(time.time())}")
    result_dir = os.path.join(logs_dir, task_id)
    if os.path.exists(result_dir):
        print(f"\n结果已保存到: {result_dir}")
        print(f"可使用以下命令恢复任务:")
        print(f"python parallel_task_decomposition_system.py --resume {task_id}")
    
    print("\n示例运行完成")
    print("="*80)


def run_benchmark(max_workers_list=[1, 2, 4, 8]):
    """
    运行并行执行基准测试，比较不同并行度的性能
    
    参数:
        max_workers_list (list): 要测试的最大并行度列表
    """
    print("="*80)
    print("并行任务拆分与执行系统基准测试")
    print("="*80)
    
    # 初始化结果收集
    benchmark_results = []
    
    # 定义任务（包含多个可并行的子任务）
    task_description = """
实现一个基于Python的文档处理系统，具有以下功能模块：

1. 文档解析模块：
   - 支持读取并解析PDF、Word、HTML和Markdown文件
   - 提取文本内容、元数据和结构信息
   - 处理表格和图表内容

2. 内容分析模块：
   - 实现基本的自然语言处理功能，如分词、词性标注
   - 提供文本摘要生成功能
   - 实现关键词提取和主题识别

3. 索引与搜索模块：
   - 建立文档索引系统
   - 实现全文搜索功能
   - 支持基于元数据的过滤和排序

4. 文档转换模块：
   - 在不同格式之间转换文档
   - 支持自定义转换模板
   - 提供批量转换功能

请实现以上所有模块，设计良好的API接口，使用面向对象编程方法，确保代码可扩展性和可维护性。
提供完整的类定义、方法实现和使用示例。
"""
    
    print("\n任务描述:")
    print("-" * 40)
    print(task_description[:200] + "...")
    print("-" * 40)
    
    print("\n开始基准测试...\n")
    print(f"并行度设置: {max_workers_list}")
    
    # 为每个并行度设置运行一次测试
    for workers in max_workers_list:
        print(f"\n测试并行度: {workers} {'(顺序执行)' if workers == 1 else ''}")
        
        # 初始化系统
        logs_dir = os.path.join(os.getcwd(), "logs", f"benchmark_workers_{workers}")
        system = ParallelTaskDecompositionSystem(logs_dir=logs_dir, max_workers=workers)
        
        # 执行任务并计时
        start_time = time.time()
        result = system.execute_complex_task(task_description, parallel_threshold=2)
        execution_time = time.time() - start_time
        
        # 收集结果
        success = result.get('success', False)
        status = "成功" if success else "失败"
        stats = result.get('stats', {})
        
        print(f"执行完成: {status}, 耗时: {execution_time:.2f}秒")
        if 'speedup' in stats:
            print(f"加速比: {stats['speedup']:.2f}x, 效率: {stats['efficiency']:.2f}")
        
        # 保存测试结果
        test_result = {
            'workers': workers,
            'execution_time': execution_time,
            'success': success,
            'stats': stats,
            'task_id': result.get('task_id', '')
        }
        benchmark_results.append(test_result)
    
    # 保存基准测试结果
    benchmark_file = os.path.join(os.getcwd(), "logs", "parallel_benchmark_results.json")
    with open(benchmark_file, 'w', encoding='utf-8') as f:
        json.dump(benchmark_results, f, ensure_ascii=False, indent=2)
    
    # 显示比较结果
    print("\n基准测试结果比较:")
    print("-" * 60)
    print(f"{'并行度':<10}{'执行时间(秒)':<15}{'加速比':<10}{'并行效率':<10}{'状态':<10}")
    print("-" * 60)
    
    baseline_time = next((r['execution_time'] for r in benchmark_results if r['workers'] == 1), None)
    for result in benchmark_results:
        workers = result['workers']
        time_taken = result['execution_time']
        status = "成功" if result['success'] else "失败"
        
        # 计算加速比（相对于顺序执行）
        if baseline_time and baseline_time > 0:
            speedup = baseline_time / time_taken
        else:
            speedup = result['stats'].get('speedup', 0)
            
        efficiency = speedup / workers if workers > 0 else 0
        
        print(f"{workers:<10}{time_taken:<15.2f}{speedup:<10.2f}{efficiency:<10.2f}{status:<10}")
    
    print("-" * 60)
    print(f"基准测试结果已保存到: {benchmark_file}")
    print("\n基准测试完成")
    print("="*80)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="并行任务拆分与执行系统示例")
    parser.add_argument("--workers", type=int, default=4, help="最大并行工作线程数")
    parser.add_argument("--benchmark", action="store_true", help="运行基准测试")
    parser.add_argument("--benchmark-workers", type=str, default="1,2,4,8", 
                       help="基准测试的工作线程数列表，用逗号分隔")
    
    args = parser.parse_args()
    
    if args.benchmark:
        workers_list = [int(w) for w in args.benchmark_workers.split(',')]
        run_benchmark(workers_list)
    else:
        run_example(max_workers=args.workers)