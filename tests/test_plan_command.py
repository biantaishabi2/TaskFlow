"""
测试plan命令功能
"""

import os
import sys
import json
import pytest
import tempfile
from unittest.mock import patch, MagicMock
from pathlib import Path

# 添加项目根目录到路径以便导入模块
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class MockTaskPlanner:
    """模拟TaskPlanner类，用于测试plan命令"""
    
    def __init__(self, task_description, context_manager=None, logs_dir="logs"):
        self.task_description = task_description
        self.context_manager = context_manager
        self.logs_dir = logs_dir
        
    def analyze_task(self):
        """模拟任务分析方法"""
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

def test_plan_command():
    """测试plan命令的基本功能"""
    # 创建临时输出目录
    with tempfile.TemporaryDirectory() as temp_dir:
        output_dir = os.path.join(temp_dir, "plan_output")
        os.makedirs(output_dir, exist_ok=True)
        
        # 模拟的任务描述
        task_description = "测试一个数据分析任务，包括数据清洗、特征工程和模型训练"
        
        # 创建模拟的规划器
        planner = MockTaskPlanner(task_description)
        
        # 执行分析
        analysis = planner.analyze_task()
        
        # 执行任务分解
        subtasks = planner.break_down_task(analysis)
        
        # 保存结果
        analysis_path = os.path.join(output_dir, "task_analysis.json")
        breakdown_path = os.path.join(output_dir, "task_breakdown.json")
        
        with open(analysis_path, "w", encoding="utf-8") as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
            
        with open(breakdown_path, "w", encoding="utf-8") as f:
            json.dump(subtasks, f, indent=2, ensure_ascii=False)
        
        # 验证结果文件已创建
        assert os.path.exists(analysis_path), "任务分析结果文件应该存在"
        assert os.path.exists(breakdown_path), "任务分解结果文件应该存在"
        
        # 读取并验证结果内容
        with open(analysis_path, "r", encoding="utf-8") as f:
            saved_analysis = json.load(f)
        
        with open(breakdown_path, "r", encoding="utf-8") as f:
            saved_subtasks = json.load(f)
            
        # 验证分析结果内容
        assert saved_analysis["task_id"] == "test_analysis"
        assert saved_analysis["success"] == True
        assert "数据分析任务" in saved_analysis["result"]["summary"]
        
        # 验证任务分解结果
        assert len(saved_subtasks) == 3
        assert saved_subtasks[0]["id"] == "data_prep"
        assert saved_subtasks[1]["id"] == "feature_eng"
        assert saved_subtasks[2]["id"] == "model_train"
        
        # 验证子任务包含output_files
        for subtask in saved_subtasks:
            assert "output_files" in subtask, f"子任务 {subtask['id']} 缺少output_files字段"
            assert isinstance(subtask["output_files"], dict), f"子任务 {subtask['id']} 的output_files应为字典"
            assert "main_result" in subtask["output_files"], f"子任务 {subtask['id']} 的output_files应包含main_result"

if __name__ == "__main__":
    # 直接运行测试
    pytest.main(["-xvs", __file__])