#!/usr/bin/env python3
"""
任务拆分与执行系统示例
展示如何使用任务拆分与执行系统处理复杂任务
"""

import os
import time
from task_decomposition_system import TaskDecompositionSystem

def run_example():
    """运行任务拆分与执行系统示例"""
    print("="*80)
    print("任务拆分与执行系统示例")
    print("="*80)
    
    # 初始化系统
    logs_dir = os.path.join(os.getcwd(), "logs", "examples")
    system = TaskDecompositionSystem(logs_dir=logs_dir)
    
    # 定义一个复杂任务
    task_description = """
设计并生成一个简单的Python网站内容管理系统(CMS)的核心模块。
这个CMS应该包含以下功能:

1. 用户管理:
   - 支持用户注册、登录和权限管理
   - 不同用户角色(管理员、编辑、作者、访客)
   
2. 内容管理:
   - 文章的创建、编辑、发布和删除
   - 支持多种内容类型(文章、页面、媒体)
   - 内容分类和标签系统
   
3. 数据存储:
   - 使用SQLite作为数据库后端
   - 定义合理的数据模型和关系

请提供该CMS的核心Python代码文件，包括但不限于数据模型定义、用户认证、内容管理API等。
不需要实现前端界面和完整的Web框架集成，只需要提供核心功能模块的实现。
使用现代Python设计模式，确保代码易于理解和扩展。
"""
    
    print("\n任务描述:")
    print("-" * 40)
    print(task_description)
    print("-" * 40)
    
    # 执行复杂任务
    print("\n开始执行任务...")
    start_time = time.time()
    
    result = system.execute_complex_task(task_description)
    
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
        print(f"python task_decomposition_system.py --resume {task_id}")
    
    print("\n示例运行完成")
    print("="*80)


def run_alternative_example():
    """运行另一个示例任务"""
    print("="*80)
    print("任务拆分与执行系统示例 - 数据分析任务")
    print("="*80)
    
    # 初始化系统
    logs_dir = os.path.join(os.getcwd(), "logs", "examples")
    system = TaskDecompositionSystem(logs_dir=logs_dir)
    
    # 定义一个数据分析任务
    task_description = """
设计一个数据分析流程，用于处理和分析电子商务网站的销售数据。具体要求如下:

1. 数据预处理:
   - 读取CSV格式的销售数据
   - 清洗数据(处理缺失值、异常值等)
   - 数据转换和特征工程

2. 销售分析:
   - 计算基本统计指标(总销售额、平均订单金额等)
   - 按时间维度分析销售趋势(日、周、月)
   - 按产品类别和区域分析销售情况

3. 客户分析:
   - 计算客户生命周期价值(CLV)
   - 客户细分(基于购买行为)
   - 识别高价值客户

请提供完整的Python代码实现以上分析流程，使用pandas和matplotlib/seaborn等库。
假设CSV数据格式包含以下字段:订单ID、客户ID、订单日期、产品ID、产品类别、产品价格、购买数量、客户所在区域。
"""
    
    print("\n任务描述:")
    print("-" * 40)
    print(task_description)
    print("-" * 40)
    
    # 执行复杂任务
    print("\n开始执行任务...")
    start_time = time.time()
    
    result = system.execute_complex_task(task_description)
    
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
    
    # 显示结果保存位置
    task_id = result.get('task_id', f"task_{int(time.time())}")
    result_dir = os.path.join(logs_dir, task_id)
    if os.path.exists(result_dir):
        print(f"\n结果已保存到: {result_dir}")
    
    print("\n示例运行完成")
    print("="*80)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="任务拆分与执行系统示例")
    parser.add_argument("--type", choices=["cms", "data_analysis"], default="cms",
                        help="要运行的示例类型")
    
    args = parser.parse_args()
    
    if args.type == "cms":
        run_example()
    elif args.type == "data_analysis":
        run_alternative_example()