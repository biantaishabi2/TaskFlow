#!/usr/bin/env python3
"""
任务规划测试脚本
仅测试任务分析和拆分阶段，不执行实际任务
"""

import os
import json
from task_planner.core.task_planner import TaskPlanner
from task_planner.core.context_management import ContextManager

def test_planning_only():
    """测试仅任务规划功能"""
    print("="*50)
    print("任务规划测试 - 仅分析和拆分，不执行")
    print("="*50)
    
    # 初始化上下文管理器
    context_manager = ContextManager()
    
    # 任务描述
    task_description = """
设计一个数据分析流程，用于处理销售数据：
1. 数据预处理
   - 读取CSV格式的销售数据
   - 清洗数据(处理缺失值、异常值等)
   - 数据转换和特征工程

2. 销售分析
   - 计算基本统计指标(总销售额、平均订单金额等)
   - 按时间维度分析销售趋势(日、周、月)
   - 按产品类别和区域分析销售情况

3. 客户分析
   - 计算客户生命周期价值(CLV)
   - 客户细分(基于购买行为)
   - 识别高价值客户
"""
    
    print("\n任务描述:")
    print("-" * 40)
    print(task_description)
    print("-" * 40)
    
    # 创建规划器实例
    planner = TaskPlanner(task_description, context_manager=context_manager)
    
    # 仅执行任务分析（规划阶段1）
    print("\n===== 任务分析结果 =====")
    analysis = planner.analyze_task()
    print(json.dumps(analysis, indent=2, ensure_ascii=False))
    
    # 仅执行任务拆分（规划阶段2）
    print("\n===== 任务拆分结果 =====")
    subtasks = planner.break_down_task(analysis)
    
    for i, subtask in enumerate(subtasks):
        print(f"\n子任务 {i+1}:")
        print(f"  名称: {subtask['name']}")
        print(f"  描述: {subtask['description']}")
        print(f"  优先级: {subtask.get('priority', 'normal')}")
        if 'dependencies' in subtask and subtask['dependencies']:
            print(f"  依赖: {', '.join(subtask['dependencies'])}")
    
    # 保存结果到文件
    output_dir = os.path.join(os.getcwd(), "output")
    os.makedirs(output_dir, exist_ok=True)
    
    with open(os.path.join(output_dir, "task_analysis.json"), "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)
    
    with open(os.path.join(output_dir, "task_breakdown.json"), "w", encoding="utf-8") as f:
        json.dump(subtasks, f, indent=2, ensure_ascii=False)
    
    print("\n分析和拆分结果已保存到:")
    print(f"- {os.path.join(output_dir, 'task_analysis.json')}")
    print(f"- {os.path.join(output_dir, 'task_breakdown.json')}")
    
    print("\n测试完成")
    print("="*50)

if __name__ == "__main__":
    test_planning_only()