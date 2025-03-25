#!/usr/bin/env python3
"""
任务拆分与执行系统 - 上下文管理模块
实现任务上下文管理和传递机制

OBSOLETE: 这个实现使用了内存中的字典存储上下文，已被新的基于文件的上下文管理机制取代
建议使用新的上下文管理机制，它提供了更好的隔离性和可靠性
"""

from datetime import datetime
import copy
import json
import os

class TaskContext:
    """
    任务上下文类，用于存储和管理任务相关的上下文信息
    
    OBSOLETE: 这个实现将所有数据存储在内存中，容易造成内存泄露和数据丢失
    建议使用新的基于文件的上下文管理机制
    """
    
    def __init__(self, task_id, global_context=None):
        """
        初始化任务上下文
        
        参数:
            task_id (str): 任务唯一标识符
            global_context (dict, optional): 全局共享上下文
        """
        self.task_id = task_id
        self.global_context = global_context or {}  # 全局共享上下文
        self.local_context = {}  # 任务特定上下文
        self.artifacts = {}  # 任务产生的工件（代码、文档等）
        self.execution_history = []  # 执行历史
        
    def update_global(self, key, value):
        """更新全局上下文"""
        self.global_context[key] = value
        
    def update_local(self, key, value):
        """更新本地上下文"""
        self.local_context[key] = value
        
    def add_artifact(self, name, content, metadata=None):
        """
        添加任务产生的工件
        
        参数:
            name (str): 工件名称
            content (str/dict/list): 工件内容
            metadata (dict, optional): 工件元数据，包含类型、格式等信息
        """
        # 确保元数据包含工件类型
        metadata = metadata or {}
        if 'type' not in metadata:
            # 根据内容推断类型
            if isinstance(content, str):
                if content.startswith("def ") or content.startswith("class ") or "import " in content:
                    metadata['type'] = 'code'
                elif content.startswith("<") and ">" in content:
                    metadata['type'] = 'markup'
                else:
                    metadata['type'] = 'text'
            elif isinstance(content, dict):
                metadata['type'] = 'structured_data'
            elif isinstance(content, list):
                metadata['type'] = 'collection'
            else:
                metadata['type'] = 'unknown'
                
        # 存储工件
        self.artifacts[name] = {
            'content': content,
            'metadata': metadata,
            'created_at': datetime.now().isoformat()
        }
        
    def add_execution_record(self, action, result, metadata=None):
        """记录执行历史"""
        self.execution_history.append({
            'action': action,
            'result': result,
            'metadata': metadata or {},
            'timestamp': datetime.now().isoformat()
        })
        
    def serialize(self):
        """序列化上下文以便传递或存储"""
        return {
            'task_id': self.task_id,
            'global_context': self.global_context,
            'local_context': self.local_context,
            'artifacts': self.artifacts,
            'execution_history': self.execution_history
        }
        
    @classmethod
    def deserialize(cls, data):
        """从序列化数据重建上下文"""
        context = cls(data['task_id'])
        context.global_context = data['global_context']
        context.local_context = data['local_context']
        context.artifacts = data['artifacts']
        context.execution_history = data['execution_history']
        return context
        
    def save_to_file(self, file_path):
        """将上下文保存到文件"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.serialize(), f, ensure_ascii=False, indent=2)
            
    @classmethod
    def load_from_file(cls, file_path):
        """从文件加载上下文"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.deserialize(data)


class ContextManager:
    """
    上下文管理器，用于管理多个任务的上下文和上下文传递
    
    OBSOLETE: 这个实现没有很好的隔离性和持久化机制，已被新的基于文件的实现取代
    建议使用新的上下文管理机制，它提供了更好的:
    1. 数据隔离
    2. 权限控制
    3. 可靠性
    4. 可审计性
    """
    
    def __init__(self, context_dir=None):
        """
        初始化上下文管理器
        
        参数:
            context_dir (str, optional): 上下文文件存储目录
        """
        self.global_context = {}  # 所有任务共享的全局上下文
        self.task_contexts = {}  # 各任务的上下文
        self.context_history = []  # 上下文变更历史
        self.context_dir = context_dir
        
        # 如果指定了上下文目录，确保它存在
        if self.context_dir and not os.path.exists(self.context_dir):
            os.makedirs(self.context_dir)
        
    def create_subtask_context(self, parent_task_id, subtask_id, context_subset=None):
        """
        为子任务创建上下文，继承父任务上下文的指定子集
        
        参数:
            parent_task_id (str): 父任务ID
            subtask_id (str): 子任务ID
            context_subset (list, optional): 要继承的上下文键列表
            
        返回:
            TaskContext: 新创建的子任务上下文
        """
        parent_context = self.task_contexts.get(parent_task_id, TaskContext(parent_task_id, self.global_context))
        
        # 创建新的任务上下文
        subtask_context = TaskContext(subtask_id, self.global_context.copy())
        
        # 如果指定了上下文子集，只继承这些键
        if context_subset:
            for key in context_subset:
                if key in parent_context.local_context:
                    subtask_context.local_context[key] = copy.deepcopy(parent_context.local_context[key])
        else:
            # 默认继承所有父任务上下文
            subtask_context.local_context = copy.deepcopy(parent_context.local_context)
            
        # 记录上下文继承关系
        subtask_context.local_context['_parent_task_id'] = parent_task_id
        
        # 存储新创建的上下文
        self.task_contexts[subtask_id] = subtask_context
        
        # 记录上下文创建事件
        self._log_context_event('create', subtask_id, parent_task_id)
        
        return subtask_context
        
    def update_task_context(self, task_id, update_data, update_global=False):
        """
        更新任务上下文，并选择性地更新全局上下文
        
        参数:
            task_id (str): 任务ID
            update_data (dict): 要更新的数据
            update_global (bool): 是否同时更新全局上下文
            
        返回:
            TaskContext: 更新后的任务上下文
        """
        if task_id not in self.task_contexts:
            raise ValueError(f"任务ID {task_id} 的上下文不存在")
            
        # 更新任务本地上下文
        for key, value in update_data.items():
            self.task_contexts[task_id].update_local(key, value)
            
        # 如果需要，同时更新全局上下文
        if update_global:
            for key, value in update_data.items():
                self.global_context[key] = value
                self.task_contexts[task_id].update_global(key, value)
                
        # 记录上下文更新事件
        self._log_context_event('update', task_id, update_data)
        
        return self.task_contexts[task_id]
        
    def propagate_results(self, from_task_id, to_task_ids, keys=None, artifact_keys=None):
        """
        将一个任务的结果传播到其他任务
        
        参数:
            from_task_id (str): 源任务ID
            to_task_ids (list): 目标任务ID列表
            keys (list, optional): 要传播的上下文键列表
            artifact_keys (list, optional): 要传播的工件键列表，如果为None则传播所有工件
        """
        if from_task_id not in self.task_contexts:
            raise ValueError(f"源任务ID {from_task_id} 的上下文不存在")
            
        source_context = self.task_contexts[from_task_id]
        
        # 确定要传播的上下文键
        if keys is None:
            # 默认传播所有结果（但不包括artifacts）
            keys = list(source_context.local_context.keys())
            
        # 对每个目标任务传播上下文
        for task_id in to_task_ids:
            if task_id not in self.task_contexts:
                continue
                
            target_context = self.task_contexts[task_id]
            
            # 传播上下文键值
            for key in keys:
                if key in source_context.local_context:
                    target_context.local_context[key] = copy.deepcopy(
                        source_context.local_context[key]
                    )
            
            # 传播工件
            if artifact_keys is not None or 'artifacts' in keys:
                # 确定要传播的工件
                if artifact_keys is None:
                    # 传播所有工件
                    artifact_keys = source_context.artifacts.keys()
                    
                # 传播指定的工件
                for art_name in artifact_keys:
                    if art_name in source_context.artifacts:
                        # 复制工件到目标上下文
                        target_context.artifacts[art_name] = copy.deepcopy(
                            source_context.artifacts[art_name]
                        )
                        
                        # 添加引用信息
                        if 'references' not in target_context.artifacts[art_name]['metadata']:
                            target_context.artifacts[art_name]['metadata']['references'] = []
                            
                        # 添加源任务引用
                        reference = {
                            'source_task': from_task_id,
                            'propagated_at': datetime.now().isoformat()
                        }
                        target_context.artifacts[art_name]['metadata']['references'].append(reference)
                    
            # 记录传播事件
            propagation_data = {
                'context_keys': keys,
                'artifact_keys': list(artifact_keys) if artifact_keys is not None else []
            }
            self._log_context_event('propagate', from_task_id, task_id, propagation_data)
            
    def get_execution_summary(self, task_id):
        """
        获取任务执行摘要，用于规划者评估
        
        参数:
            task_id (str): 任务ID
            
        返回:
            dict: 任务执行摘要
        """
        if task_id not in self.task_contexts:
            raise ValueError(f"任务ID {task_id} 的上下文不存在")
            
        context = self.task_contexts[task_id]
        
        # 构建执行摘要
        summary = {
            'task_id': task_id,
            'success': context.local_context.get('success', False),
            'output': context.local_context.get('output', ''),
            'artifacts': list(context.artifacts.keys()),
            'execution_events': len(context.execution_history),
            'last_event': context.execution_history[-1] if context.execution_history else None,
            'key_metrics': context.local_context.get('metrics', {})
        }
        
        return summary
        
    def save_all_contexts(self):
        """将所有上下文保存到文件"""
        if not self.context_dir:
            return
            
        # 保存全局上下文
        global_context_path = os.path.join(self.context_dir, 'global_context.json')
        with open(global_context_path, 'w', encoding='utf-8') as f:
            json.dump(self.global_context, f, ensure_ascii=False, indent=2)
            
        # 保存各任务上下文
        for task_id, context in self.task_contexts.items():
            task_context_path = os.path.join(self.context_dir, f'task_{task_id}.json')
            context.save_to_file(task_context_path)
            
        # 保存上下文历史
        history_path = os.path.join(self.context_dir, 'context_history.json')
        with open(history_path, 'w', encoding='utf-8') as f:
            json.dump(self.context_history, f, ensure_ascii=False, indent=2)
            
    def load_all_contexts(self):
        """从文件加载所有上下文"""
        if not self.context_dir or not os.path.exists(self.context_dir):
            return
            
        # 加载全局上下文
        global_context_path = os.path.join(self.context_dir, 'global_context.json')
        if os.path.exists(global_context_path):
            with open(global_context_path, 'r', encoding='utf-8') as f:
                self.global_context = json.load(f)
                
        # 加载任务上下文
        for filename in os.listdir(self.context_dir):
            if filename.startswith('task_') and filename.endswith('.json'):
                task_id = filename[5:-5]  # 提取task_id
                task_context_path = os.path.join(self.context_dir, filename)
                context = TaskContext.load_from_file(task_context_path)
                self.task_contexts[task_id] = context
                
        # 加载上下文历史
        history_path = os.path.join(self.context_dir, 'context_history.json')
        if os.path.exists(history_path):
            with open(history_path, 'r', encoding='utf-8') as f:
                self.context_history = json.load(f)
        
    def _log_context_event(self, event_type, primary_id, secondary_id=None, data=None):
        """
        记录上下文事件
        
        参数:
            event_type (str): 事件类型
            primary_id (str): 主要相关的任务ID
            secondary_id (str, optional): 次要相关的任务ID
            data (any, optional): 事件相关数据
        """
        self.context_history.append({
            'event_type': event_type,
            'primary_id': primary_id,
            'secondary_id': secondary_id,
            'data': data,
            'timestamp': datetime.now().isoformat()
        })