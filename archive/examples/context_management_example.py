#!/usr/bin/env python3
"""
任务拆分与执行系统 - 上下文管理示例
展示如何使用上下文管理模块
"""

from context_management import TaskContext, ContextManager
import json
import os

def main():
    """主函数"""
    print("===== 任务拆分与执行系统 - 上下文管理示例 =====")
    
    # 创建上下文管理器
    context_dir = "/tmp/task_contexts"
    if not os.path.exists(context_dir):
        os.makedirs(context_dir)
    manager = ContextManager(context_dir)
    
    # 设置全局上下文
    manager.global_context.update({
        "project": "任务拆分系统",
        "version": "0.1.0",
        "environment": "development"
    })
    
    # 创建主任务上下文
    main_task_id = "main_task"
    main_context = TaskContext(main_task_id, manager.global_context)
    manager.task_contexts[main_task_id] = main_context
    
    # 添加主任务信息
    main_context.update_local("name", "构建系统原型")
    main_context.update_local("description", "实现任务拆分与执行系统的基本功能")
    main_context.update_local("priority", "high")
    
    # 添加主任务工件
    main_context.add_artifact(
        "requirements",
        "- 实现上下文管理\n- 实现Claude交互\n- 实现任务拆分",
        {"type": "text", "format": "markdown"}
    )
    
    print(f"创建了主任务: {main_task_id}")
    print(f"  名称: {main_context.local_context['name']}")
    print(f"  描述: {main_context.local_context['description']}")
    print(f"  优先级: {main_context.local_context['priority']}")
    print(f"  工件: {list(main_context.artifacts.keys())}")
    print()
    
    # 创建子任务
    subtasks = [
        {"id": "subtask_1", "name": "实现上下文管理", "subset": ["description"]},
        {"id": "subtask_2", "name": "实现Claude交互", "subset": ["description"]},
        {"id": "subtask_3", "name": "实现任务拆分", "subset": ["description"]}
    ]
    
    for subtask in subtasks:
        # 创建子任务上下文
        subtask_id = subtask["id"]
        subtask_context = manager.create_subtask_context(
            main_task_id, 
            subtask_id,
            context_subset=subtask["subset"]
        )
        
        # 添加子任务特定信息
        subtask_context.update_local("name", subtask["name"])
        subtask_context.update_local("status", "pending")
        
        print(f"创建了子任务: {subtask_id}")
        print(f"  名称: {subtask_context.local_context['name']}")
        print(f"  状态: {subtask_context.local_context['status']}")
        print(f"  从主任务继承的描述: {subtask_context.local_context['description']}")
        print()
    
    # 模拟子任务1完成
    subtask_1 = manager.task_contexts["subtask_1"]
    subtask_1.update_local("status", "completed")
    subtask_1.update_local("output", "上下文管理模块已实现")
    
    # 添加多个工件
    subtask_1.add_artifact(
        "context_class",
        "class TaskContext:\n    def __init__(self, task_id, global_context=None):\n        self.task_id = task_id\n        self.global_context = global_context or {}\n        self.local_context = {}\n        self.artifacts = {}\n        self.execution_history = []",
        {"language": "python", "category": "implementation"}
    )
    
    subtask_1.add_artifact(
        "manager_class",
        "class ContextManager:\n    def __init__(self):\n        self.global_context = {}\n        self.task_contexts = {}\n        self.context_history = []",
        {"language": "python", "category": "implementation"}
    )
    
    subtask_1.add_artifact(
        "design_notes",
        "上下文管理模块设计注意事项:\n- 确保上下文传递高效\n- 支持工件复用\n- 实现序列化/反序列化",
        {"type": "text", "category": "documentation"}
    )
    
    subtask_1.add_execution_record("complete", "成功完成任务")
    
    # 将子任务1的结果传播到子任务2和子任务3
    # 子任务2接收所有上下文和工件
    manager.propagate_results(
        "subtask_1", 
        ["subtask_2"], 
        keys=["status", "output"],
        artifact_keys=["context_class", "manager_class"]
    )
    
    # 子任务3只接收状态和设计笔记工件
    manager.propagate_results(
        "subtask_1", 
        ["subtask_3"], 
        keys=["status"],
        artifact_keys=["design_notes"]
    )
    
    print("子任务1已完成并将结果传播到子任务2和子任务3")
    print(f"  子任务1状态: {subtask_1.local_context['status']}")
    print(f"  子任务1输出: {subtask_1.local_context['output']}")
    print(f"  子任务1工件: {list(subtask_1.artifacts.keys())}")
    print()
    
    # 检查子任务2的继承内容
    subtask_2 = manager.task_contexts["subtask_2"]
    print("子任务2继承的内容:")
    print(f"  状态: {subtask_2.local_context.get('status', '无')}")
    print(f"  输出: {subtask_2.local_context.get('output', '无')}")
    print(f"  继承的工件: {list(subtask_2.artifacts.keys())}")
    
    # 显示工件引用信息
    if subtask_2.artifacts:
        artifact_name = list(subtask_2.artifacts.keys())[0]
        references = subtask_2.artifacts[artifact_name]['metadata'].get('references', [])
        print(f"  工件 '{artifact_name}' 的引用信息: {references}")
    print()
    
    # 检查子任务3的继承内容
    subtask_3 = manager.task_contexts["subtask_3"]
    print("子任务3继承的内容:")
    print(f"  状态: {subtask_3.local_context.get('status', '无')}")
    print(f"  输出: {subtask_3.local_context.get('output', '无')}") # 应该为无，因为没有传递输出
    print(f"  继承的工件: {list(subtask_3.artifacts.keys())}")
    print()
    
    # 获取子任务1的执行摘要
    summary = manager.get_execution_summary("subtask_1")
    print("子任务1执行摘要:")
    print(json.dumps(summary, indent=2))
    print()
    
    # 保存所有上下文
    manager.save_all_contexts()
    print(f"所有上下文已保存到目录: {context_dir}")
    print(f"  保存的文件: {os.listdir(context_dir)}")
    
if __name__ == "__main__":
    main()