#!/usr/bin/env python3
"""
任务执行测试脚本
仅测试任务执行阶段，使用预定义的任务数据，不进行任务规划
"""

import os
import json
from datetime import datetime
from task_planner.core.task_executor import TaskExecutor
from task_planner.core.context_management import ContextManager, TaskContext

def test_execution_only():
    """测试仅任务执行功能"""
    print("="*50)
    print("任务执行测试 - 仅执行预定义任务，不进行规划")
    print("="*50)
    
    # 创建日志目录
    log_dir = os.path.join(os.getcwd(), "logs", "execution_test")
    os.makedirs(log_dir, exist_ok=True)
    
    # 初始化上下文管理器
    context_manager = ContextManager(context_dir=log_dir)
    
    # 预定义任务数据
    subtasks = [
        {
            "id": "data_prep",
            "name": "数据预处理",
            "description": "准备数据分析所需的数据集",
            "instruction": """
你是一位数据分析师，需要完成数据预处理工作。
请执行以下数据预处理任务:

1. 读取CSV数据 (这里模拟这个过程)
   - 假设数据包含以下字段：日期、产品ID、产品名称、类别、销售量、单价、区域

2. 数据清洗
   - 处理缺失值：对销售量和单价的缺失值进行均值填充
   - 处理异常值：识别并处理销售量异常高或低的记录
   - 格式化日期字段为标准格式

3. 数据转换
   - 创建新的"销售额"字段 = 销售量 × 单价
   - 提取日期的年、月、周等信息作为新特征
   - 对类别和区域字段进行编码

请模拟这个过程，提供以下输出:
1. 简要描述你的数据预处理流程
2. 生成一个数据处理代码示例
3. 提供预处理后的数据样本(模拟10条记录)
4. 说明预处理过程中遇到的问题及解决方法
""",
            "priority": "high",
            "dependencies": []
        },
        {
            "id": "sales_analysis",
            "name": "销售分析",
            "description": "分析销售数据的趋势和模式",
            "instruction": """
作为数据分析师，你需要对预处理完成的销售数据进行全面分析。

请基于预处理的数据执行以下销售分析任务:

1. 计算基本统计指标
   - 总销售额、平均订单金额
   - 各产品类别的销售占比
   - 不同区域的销售表现

2. 时间维度分析
   - 按月度/季度/年度的销售趋势
   - 识别销售的周期性模式
   - 同比/环比增长率计算

3. 产品与区域分析
   - 表现最好/最差的产品类别
   - 各区域销售差异及原因分析
   - 产品组合分析

请模拟这个分析过程，提供:
1. 分析方法说明
2. 数据可视化代码示例(使用matplotlib或其他可视化库)
3. 关键发现和洞察
4. 建议的业务行动要点
""",
            "priority": "medium",
            "dependencies": ["data_prep"]
        },
        {
            "id": "customer_analysis",
            "name": "客户分析",
            "description": "分析客户价值和行为特征",
            "instruction": """
作为客户分析专家，你需要基于销售数据分析客户价值和行为特征。

请执行以下客户分析任务:

1. 客户生命周期价值(CLV)计算
   - 定义客户获取成本和客户维系成本
   - 计算客户平均购买频率和客户留存率
   - 估算客户终身价值

2. 客户细分
   - 基于购买频率、金额、最近一次购买时间(RFM分析)进行客户分群
   - 识别高价值客户、有增长潜力客户和流失风险客户
   - 分析不同客户群的购买行为特征

3. 客户画像构建
   - 识别高价值客户的共同特征
   - 分析客户购买路径和决策因素
   - 提出个性化营销建议

请模拟这个分析过程，提供:
1. 客户分析方法论
2. 客户细分的代码示例
3. 高价值客户特征总结
4. 针对不同客户群的营销策略建议
""",
            "priority": "medium",
            "dependencies": ["data_prep", "sales_analysis"]
        }
    ]
    
    # 初始化上下文和依赖关系
    for subtask in subtasks:
        task_id = subtask["id"]
        # 创建任务上下文
        task_context = TaskContext(task_id)
        # 存储任务定义
        task_context.update_local("task_definition", subtask)
        # 添加到上下文管理器
        context_manager.task_contexts[task_id] = task_context
    
    # 初始化任务执行器
    executor = TaskExecutor(context_manager=context_manager, verbose=True)
    
    # 按依赖关系顺序执行任务
    print("\n开始执行任务序列...")
    results = {}
    
    # 1. 执行无依赖的任务
    for subtask in subtasks:
        if not subtask["dependencies"]:
            print(f"\n执行任务: {subtask['name']} (ID: {subtask['id']})")
            result = executor.execute_subtask(subtask)
            results[subtask["id"]] = result
            print(f"任务 {subtask['name']} 执行{'成功' if result.get('success') else '失败'}")
            
            # 显示执行摘要
            if "result" in result and "summary" in result["result"]:
                print(f"结果摘要: {result['result']['summary']}")
    
    # 2. 为依赖任务准备上下文
    for subtask in subtasks:
        if subtask["dependencies"]:
            task_id = subtask["id"]
            
            # 收集依赖任务的结果
            dependency_results = {}
            all_dependencies_met = True
            
            for dep_id in subtask["dependencies"]:
                if dep_id in results:
                    dependency_results[dep_id] = results[dep_id]
                else:
                    print(f"警告: 依赖任务 {dep_id} 的结果不可用")
                    all_dependencies_met = False
            
            # 更新任务上下文中的依赖结果
            if all_dependencies_met:
                context_manager.task_contexts[task_id].update_local("dependency_results", dependency_results)
    
    # 3. 执行有依赖的任务
    for subtask in subtasks:
        if subtask["dependencies"]:
            # 检查所有依赖是否已执行成功
            dependencies_ok = all(dep_id in results and results[dep_id].get("success", False) 
                                for dep_id in subtask["dependencies"])
            
            if dependencies_ok:
                print(f"\n执行任务: {subtask['name']} (ID: {subtask['id']})")
                result = executor.execute_subtask(subtask)
                results[subtask["id"]] = result
                print(f"任务 {subtask['name']} 执行{'成功' if result.get('success') else '失败'}")
                
                # 显示执行摘要
                if "result" in result and "summary" in result["result"]:
                    print(f"结果摘要: {result['result']['summary']}")
            else:
                print(f"\n跳过任务 {subtask['name']} (ID: {subtask['id']})，因为依赖任务未成功执行")
    
    # 保存执行结果
    results_file = os.path.join(log_dir, f"execution_results_{int(datetime.now().timestamp())}.json")
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    # 保存上下文信息
    context_manager.save_all_contexts()
    
    print(f"\n执行结果已保存到: {results_file}")
    print(f"上下文信息已保存到: {log_dir}")
    print("\n测试完成")
    print("="*50)

if __name__ == "__main__":
    test_execution_only()