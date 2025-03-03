#!/usr/bin/env python3
import os
import re

def fix_imports_in_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检测导入语句并替换
    updated_content = content
    
    # 更新对自定义模块的导入
    imports_to_fix = {
        r'from\s+context_management\s+import': 'from src.core.context_management import',
        r'import\s+context_management': 'import src.core.context_management as context_management',
        
        r'from\s+task_planner\s+import': 'from src.core.task_planner import',
        r'import\s+task_planner': 'import src.core.task_planner as task_planner',
        
        r'from\s+task_executor\s+import': 'from src.core.task_executor import',
        r'import\s+task_executor': 'import src.core.task_executor as task_executor',
        
        r'from\s+task_decomposition_system\s+import': 'from src.core.task_decomposition_system import',
        r'import\s+task_decomposition_system': 'import src.core.task_decomposition_system as task_decomposition_system',
        
        r'from\s+parallel_task_executor\s+import': 'from src.distributed.parallel_task_executor import',
        r'import\s+parallel_task_executor': 'import src.distributed.parallel_task_executor as parallel_task_executor',
        
        r'from\s+parallel_task_decomposition_system\s+import': 'from src.distributed.parallel_task_decomposition_system import',
        r'import\s+parallel_task_decomposition_system': 'import src.distributed.parallel_task_decomposition_system as parallel_task_decomposition_system',
        
        r'from\s+distributed_task_decomposition_system\s+import': 'from src.distributed.distributed_task_decomposition_system import',
        r'import\s+distributed_task_decomposition_system': 'import src.distributed.distributed_task_decomposition_system as distributed_task_decomposition_system',
        
        r'from\s+claude_task_bridge\s+import': 'from src.util.claude_task_bridge import',
        r'import\s+claude_task_bridge': 'import src.util.claude_task_bridge as claude_task_bridge',
        
        r'from\s+claude_cli\s+import': 'from src.util.claude_cli import',
        r'import\s+claude_cli': 'import src.util.claude_cli as claude_cli',
        
        r'from\s+task_api_server\s+import': 'from src.server.task_api_server import',
        r'import\s+task_api_server': 'import src.server.task_api_server as task_api_server',
        
        r'from\s+task_visualization_server\s+import': 'from src.server.task_visualization_server import',
        r'import\s+task_visualization_server': 'import src.server.task_visualization_server as task_visualization_server',
        
        r'from\s+task_monitor\s+import': 'from src.server.task_monitor import',
        r'import\s+task_monitor': 'import src.server.task_monitor as task_monitor',
    }
    
    for pattern, replacement in imports_to_fix.items():
        updated_content = re.sub(pattern, replacement, updated_content)
    
    if content != updated_content:
        print(f"修改文件: {file_path}")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        return True
    
    return False

def process_python_files(directory):
    modified_count = 0
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                if fix_imports_in_file(file_path):
                    modified_count += 1
    
    return modified_count

if __name__ == "__main__":
    directories = ['src', 'examples', 'tests']
    
    total_modified = 0
    for directory in directories:
        print(f"处理 {directory} 目录中的Python文件...")
        modified = process_python_files(directory)
        total_modified += modified
    
    print(f"共修改了 {total_modified} 个文件的导入语句。")