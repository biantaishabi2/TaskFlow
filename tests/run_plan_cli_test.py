"""
模拟plan命令的CLI测试工具 - 使用模拟TaskPlanner代替真实实现，避免OpenAI API调用
"""

import os
import sys
import json
import tempfile
from pathlib import Path

# 添加项目根目录到路径以便导入模块
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class MockTaskPlanner:
    """模拟TaskPlanner类，用于测试plan命令"""
    
    def __init__(self, task_description, context_manager=None, logs_dir="logs"):
        self.task_description = task_description
        self.context_manager = context_manager
        self.logs_dir = logs_dir
        print(f"创建TaskPlanner: {task_description[:50]}...")
        
    def analyze_task(self):
        """模拟任务分析方法"""
        print("执行任务分析...")
        return {
            "task_id": "test_analysis",
            "success": True,
            "result": {
                "summary": "这是一个数据分析任务，需要包括数据清洗、特征工程和模型训练步骤",
                "details": "任务涉及多个数据处理步骤，需要按顺序进行"
            }
        }
        
    def break_down_task(self, analysis=None):
        """模拟任务分解方法"""
        print("执行任务分解...")
        return [
            {
                "id": "data_prep",
                "name": "数据预处理",
                "description": "清洗和准备数据",
                "instruction": "执行数据清洗和准备过程",
                "dependencies": [],
                "priority": "high",
                "output_files": {
                    "main_result": "results/data_prep/result.json"
                }
            },
            {
                "id": "feature_eng",
                "name": "特征工程",
                "description": "创建和选择特征",
                "instruction": "基于清洗后的数据创建特征",
                "dependencies": ["data_prep"],
                "priority": "medium",
                "output_files": {
                    "main_result": "results/feature_eng/result.json"
                }
            },
            {
                "id": "model_train",
                "name": "模型训练",
                "description": "训练机器学习模型",
                "instruction": "使用准备好的特征训练模型",
                "dependencies": ["feature_eng"],
                "priority": "medium",
                "output_files": {
                    "main_result": "results/model_train/result.json"
                }
            }
        ]


def main():
    """模拟plan命令执行流程"""
    # 解析命令行参数
    import argparse
    parser = argparse.ArgumentParser(description="模拟任务规划命令")
    parser.add_argument("task", nargs="?", help="任务描述")
    parser.add_argument("--file", "-f", help="任务描述文件")
    parser.add_argument("--output", default="output", help="输出目录")
    args = parser.parse_args()
    
    # 获取任务描述
    task_text = ""
    if args.file:
        with open(args.file, 'r', encoding='utf-8') as f:
            task_text = f.read()
    elif args.task:
        task_text = args.task
    else:
        task_text = input("请输入任务描述: ")
    
    # 创建输出目录
    os.makedirs(args.output, exist_ok=True)
    
    # 创建模拟的规划器
    planner = MockTaskPlanner(task_text)
    
    # 执行分析
    print("\n===== 任务分析中... =====")
    analysis = planner.analyze_task()
    
    # 执行任务分解
    print("\n===== 任务拆分中... =====")
    subtasks = planner.break_down_task(analysis)
    
    # 显示拆分结果
    for i, subtask in enumerate(subtasks):
        print(f"\n子任务 {i+1}:")
        print(f"  名称: {subtask['name']}")
        print(f"  描述: {subtask['description']}")
        print(f"  优先级: {subtask.get('priority', 'normal')}")
        if 'dependencies' in subtask and subtask['dependencies']:
            print(f"  依赖: {', '.join(subtask['dependencies'])}")
    
    # 保存结果到文件
    with open(os.path.join(args.output, "task_analysis.json"), "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)
    
    with open(os.path.join(args.output, "task_breakdown.json"), "w", encoding="utf-8") as f:
        json.dump(subtasks, f, indent=2, ensure_ascii=False)
    
    print("\n分析和拆分结果已保存到:")
    print(f"- {os.path.join(args.output, 'task_analysis.json')}")
    print(f"- {os.path.join(args.output, 'task_breakdown.json')}")


if __name__ == "__main__":
    main()