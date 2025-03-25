#!/usr/bin/env python3
"""
任务拆分与执行系统 - 上下文管理模块
实现基于文件的任务上下文管理和传递机制

新的上下文管理机制:
1. 基于文件存储，每个任务都有独立的上下文文件
2. 全局上下文只读，存储在 .context/global_context.json
3. 父任务上下文只读，存储在对应的任务目录
4. 当前任务上下文可读写，存储在当前任务目录
5. 历史记录只读，存储在 .context/history.json
"""

from datetime import datetime
import copy
import json
import os
import shutil

class TaskContext:
    """
    任务上下文类，用于管理任务相关的上下文信息
    新机制下主要存储文件路径而非直接存储内容，
    通过文件系统实现上下文隔离和权限控制
    """
    
    def __init__(self, task_id, global_context=None, base_dir=None):
        """
        初始化任务上下文
        
        参数:
            task_id (str): 任务唯一标识符
            global_context (dict, optional): 全局共享上下文
            base_dir (str, optional): 任务文件的基础目录
        """
        self.task_id = task_id
        self.global_context = global_context or {}  # 全局共享上下文
        self.local_context = {}  # 任务特定上下文
        self.file_paths = {}  # 任务相关文件路径
        self.execution_history = []  # 执行历史
        self.base_dir = base_dir
        self.artifacts = {}  # 任务工件
        
    def update_global(self, key, value):
        """更新全局上下文"""
        self.global_context[key] = value
        
    def update_local(self, key, value):
        """更新本地上下文"""
        self.local_context[key] = value
    
    def add_file_reference(self, name, file_path, metadata=None):
        """
        添加任务关联的文件引用
        
        参数:
            name (str): 文件引用名称
            file_path (str): 文件路径
            metadata (dict, optional): 文件元数据，包含类型、格式等信息
        """
        metadata = metadata or {}
        
        # 确保元数据包含文件类型
        if 'type' not in metadata:
            # 根据文件扩展名推断类型
            ext = os.path.splitext(file_path)[1].lower()
            if ext in ['.py', '.js', '.java', '.c', '.cpp', '.cs', '.go', '.rs']:
                metadata['type'] = 'code'
            elif ext in ['.json', '.yaml', '.yml']:
                metadata['type'] = 'data'
            elif ext in ['.md', '.txt', '.rst']:
                metadata['type'] = 'text'
            elif ext in ['.png', '.jpg', '.jpeg', '.gif']:
                metadata['type'] = 'image'
            else:
                metadata['type'] = 'unknown'
                
        # 存储文件引用
        self.file_paths[name] = {
            'path': file_path,
            'metadata': metadata,
            'added_at': datetime.now().isoformat()
        }
        
    def add_execution_record(self, action, result, metadata=None):
        """记录执行历史"""
        self.execution_history.append({
            'action': action,
            'result': result,
            'metadata': metadata or {},
            'timestamp': datetime.now().isoformat()
        })
        
    def add_artifact(self, name, content, metadata=None):
        """
        添加任务工件
        
        参数:
            name (str): 工件名称
            content (str/dict): 工件内容
            metadata (dict, optional): 工件元数据
        """
        self.artifacts[name] = {
            'content': content,
            'metadata': metadata or {},
            'created_at': datetime.now().isoformat()
        }
        
    def get_file_content(self, file_reference_name):
        """
        获取引用文件的内容
        
        参数:
            file_reference_name (str): 文件引用名称
            
        返回:
            str/dict: 文件内容，根据文件类型自动解析
        """
        if file_reference_name not in self.file_paths:
            return None
            
        file_path = self.file_paths[file_reference_name]['path']
        file_type = self.file_paths[file_reference_name]['metadata'].get('type', 'unknown')
        
        try:
            if file_type == 'data':
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
        except Exception as e:
            print(f"无法读取文件 {file_path}: {str(e)}")
            return None
    
    def serialize(self):
        """序列化上下文以便传递或存储"""
        return {
            'task_id': self.task_id,
            'global_context': self.global_context,
            'local_context': self.local_context,
            'file_paths': self.file_paths,
            'execution_history': self.execution_history,
            'base_dir': self.base_dir,
            'artifacts': self.artifacts
        }
        
    @classmethod
    def deserialize(cls, data):
        """从序列化数据重建上下文"""
        context = cls(data['task_id'], base_dir=data.get('base_dir'))
        context.global_context = data['global_context']
        context.local_context = data['local_context']
        context.file_paths = data['file_paths']
        context.execution_history = data['execution_history']
        if 'artifacts' in data:
            context.artifacts = data['artifacts']
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
    上下文管理器，用于管理多个任务的上下文和基于文件的上下文传递
    
    新机制的关键特性:
    1. 文件系统隔离 - 每个任务有独立目录
    2. 权限控制 - 通过文件系统权限控制读写
    3. 继承关系 - 通过目录结构表达任务依赖
    4. 历史记录 - 所有上下文变更都有记录
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
        
        # 如果指定了上下文目录，确保它存在并创建子目录
        if self.context_dir and not os.path.exists(self.context_dir):
            os.makedirs(self.context_dir)
            os.makedirs(os.path.join(self.context_dir, 'subtasks'), exist_ok=True)
            os.makedirs(os.path.join(self.context_dir, 'results'), exist_ok=True)
        
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
        
        # 为子任务创建结果目录
        subtask_result_dir = None
        if self.context_dir:
            subtask_result_dir = os.path.join(self.context_dir, 'results', subtask_id)
            os.makedirs(subtask_result_dir, exist_ok=True)
        
        # 创建新的任务上下文
        subtask_context = TaskContext(subtask_id, self.global_context.copy(), base_dir=subtask_result_dir)
        
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
        
    def propagate_results(self, from_task_id, to_task_ids, keys=None, file_reference_keys=None, artifact_keys=None):
        """
        将一个任务的结果传播到其他任务（主要传递文件路径信息，而非内容）
        
        参数:
            from_task_id (str): 源任务ID
            to_task_ids (list): 目标任务ID列表
            keys (list, optional): 要传播的上下文键列表
            file_reference_keys (list, optional): 要传播的文件引用键列表，如果为None则传播所有文件引用
            artifact_keys (list, optional): 要传播的工件键列表，如果为None则不传播工件
        """
        if from_task_id not in self.task_contexts:
            raise ValueError(f"源任务ID {from_task_id} 的上下文不存在")
            
        source_context = self.task_contexts[from_task_id]
        
        # 确定要传播的上下文键
        if keys is None:
            # 默认传播所有结果（但不包括file_paths）
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
            
            # 传播文件引用
            if file_reference_keys is not None or 'file_paths' in keys:
                # 确定要传播的文件引用
                if file_reference_keys is None:
                    # 传播所有文件引用
                    file_reference_keys = source_context.file_paths.keys()
                    
                # 传播指定的文件引用
                for ref_name in file_reference_keys:
                    if ref_name in source_context.file_paths:
                        # 复制文件引用到目标上下文
                        target_context.file_paths[ref_name] = copy.deepcopy(
                            source_context.file_paths[ref_name]
                        )
                        
                        # 添加引用信息
                        if 'references' not in target_context.file_paths[ref_name]['metadata']:
                            target_context.file_paths[ref_name]['metadata']['references'] = []
                            
                        # 添加源任务引用
                        reference = {
                            'source_task': from_task_id,
                            'propagated_at': datetime.now().isoformat()
                        }
                        target_context.file_paths[ref_name]['metadata']['references'].append(reference)
                    
            # 传播工件
            if artifact_keys is not None:
                # 确定要传播的工件
                for artifact_name in artifact_keys:
                    if artifact_name in source_context.artifacts:
                        # 复制工件到目标上下文
                        target_context.artifacts[artifact_name] = copy.deepcopy(
                            source_context.artifacts[artifact_name]
                        )
                        
                        # 添加引用信息
                        if 'references' not in target_context.artifacts[artifact_name]['metadata']:
                            target_context.artifacts[artifact_name]['metadata']['references'] = []
                            
                        # 添加源任务引用
                        reference = {
                            'source_task': from_task_id,
                            'propagated_at': datetime.now().isoformat()
                        }
                        target_context.artifacts[artifact_name]['metadata']['references'].append(reference)
            
            # 记录传播事件
            propagation_data = {
                'context_keys': keys,
                'file_reference_keys': list(file_reference_keys) if file_reference_keys is not None else [],
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
            'file_references': list(context.file_paths.keys()),
            'artifacts': list(context.artifacts.keys()),
            'execution_events': len(context.execution_history),
            'last_event': context.execution_history[-1] if context.execution_history else None,
            'key_metrics': context.local_context.get('metrics', {})
        }
        
        # 获取结果文件内容（如果存在）
        result_file_path = None
        if 'result_file' in context.file_paths:
            result_file_path = context.file_paths['result_file']['path']
            try:
                with open(result_file_path, 'r', encoding='utf-8') as f:
                    summary['result_data'] = json.load(f)
            except Exception as e:
                summary['result_load_error'] = str(e)
        
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
        
    def create_output_directories(self, subtasks):
        """
        为子任务创建输出目录
        
        参数:
            subtasks (list): 子任务列表
        """
        if not self.context_dir:
            return
            
        for subtask in subtasks:
            # 为每个子任务创建结果目录
            subtask_id = subtask['id']
            result_dir = os.path.join(self.context_dir, 'results', subtask_id)
            os.makedirs(result_dir, exist_ok=True)
            
            # 创建子任务定义文件
            subtask_def_path = os.path.join(self.context_dir, 'subtasks', f'{subtask_id}.json')
            with open(subtask_def_path, 'w', encoding='utf-8') as f:
                json.dump(subtask, f, ensure_ascii=False, indent=2)
                
            # 如果子任务定义了输出文件目录，确保它们存在
            if 'output_files' in subtask:
                for output_type, output_path in subtask['output_files'].items():
                    # 如果路径是相对路径，转换为绝对路径
                    if not os.path.isabs(output_path):
                        output_path = os.path.join(self.context_dir, output_path)
                        
                    # 如果是目录路径，确保目录存在
                    if output_path.endswith('/'):
                        os.makedirs(output_path, exist_ok=True)
                    else:
                        # 确保父目录存在
                        parent_dir = os.path.dirname(output_path)
                        os.makedirs(parent_dir, exist_ok=True)
        
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