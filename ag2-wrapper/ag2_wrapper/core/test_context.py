"""
测试 AG2 Context Manager 的功能
"""

import asyncio
import os
from pathlib import Path
import sys

# 添加项目根目录到 Python 路径
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent.parent  # ag2-wrapper 目录
sys.path.append(str(project_root))

from ag2_wrapper.core.ag2_context import ContextManager

async def test_context():
    print('开始测试 ContextManager...\n')
    
    # 初始化
    cm = ContextManager()
    print('=== 基础信息 ===')
    print(f'工作目录: {cm.cwd}\n')
    
    # 测试 Git 相关方法
    print('=== Git 相关测试 ===')
    is_git = await cm.is_git_repo()
    print(f'是否为 Git 仓库: {is_git}')
    
    if is_git:
        print(f'Git 邮箱: {await cm.get_git_email()}')
        print(f'Git 状态:\n{await cm.get_git_status()}\n')
    
    # 测试文件相关方法
    print('=== 文件相关测试 ===')
    print(f'是否存在 README: {await cm.has_readme()}')
    print(f'是否存在 CLAUDE.md: {await cm.has_claude_files()}')
    
    if await cm.has_readme():
        print('\nREADME 内容:')
        print(await cm.get_readme_content())
    
    if await cm.has_claude_files():
        print('\nCLAUDE.md 文件列表:')
        claude_files = await cm.get_claude_files()
        for file in claude_files:
            print(f'- {file}')
            content = await cm.get_claude_content(file)
            print(f'内容预览: {content[:200]}...\n')
    
    # 测试完整上下文获取
    print('\n=== 完整上下文测试 ===')
    context = await cm.get_context()
    for key, value in context.items():
        print(f'\n--- {key} ---')
        print(value)
    
    print('\n测试完成!')

if __name__ == "__main__":
    asyncio.run(test_context()) 