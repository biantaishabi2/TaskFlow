"""
AG2 Runtime Context Manager

这个模块负责管理 AG2 执行器的运行时上下文，包括：
1. 收集环境信息（如操作系统、工作目录等）
2. 管理 MEMORY.ME 文件的内容
3. 读取项目配置和 README 信息
4. 提供统一的上下文访问接口

注意：这个模块与 task_context_prompts.py 不同，后者负责子任务之间的上下文传递。
本模块专注于 AG2 执行器运行时的上下文管理。
"""

from typing import Dict, Optional, List
import os
import logging
import asyncio
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

class ContextManager:
    MEMORY_FILE = "MEMORY.ME"  # 定义记忆文件名常量
    
    def __init__(self, cwd: str = None):
        self.cwd = cwd or os.getcwd()
        self.logger = logging.getLogger(__name__)

    async def get_context(self) -> Dict[str, str]:
        """获取完整的上下文信息"""
        try:
            context = {
                # 基础上下文
                **({"git_status": await self.get_git_status()} if await self.is_git_repo() else {}),
                # MEMORY.ME 文件
                **({"memory_files": await self.get_memory_files()} if await self.has_memory_files() else {}),
                # README
                **({"readme": await self.get_readme()} if await self.has_readme() else {})
            }
            return context
        except Exception as e:
            self.logger.error(f"获取上下文失败: {str(e)}")
            return {}

    async def is_git_repo(self) -> bool:
        """检查是否为git仓库"""
        try:
            process = await asyncio.create_subprocess_exec(
                'git',
                'rev-parse',
                '--is-inside-work-tree',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.cwd
            )
            await process.communicate()
            return process.returncode == 0
        except Exception:
            return False

    async def get_memory_files(self) -> Optional[str]:
        """查找所有的 MEMORY.ME 文件"""
        try:
            memory_files = []
            for root, _, files in os.walk(self.cwd):
                if self.MEMORY_FILE in files:
                    memory_files.append(os.path.join(root, self.MEMORY_FILE))
            
            if not memory_files:
                return None
                
            return "NOTE: Additional MEMORY.ME files were found:\n" + \
                   "\n".join([f"- {f}" for f in memory_files])
        except Exception as e:
            self.logger.error(f"查找 MEMORY.ME 文件失败: {str(e)}")
            return None

    async def get_git_status(self) -> str:
        """获取 Git 仓库状态"""
        if not await self.is_git_repo():
            return "Not a git repository"
            
        try:
            # 获取当前分支
            branch = await self._run_git_command(['rev-parse', '--abbrev-ref', 'HEAD'])
            
            # 获取主分支
            main_branch = await self._run_git_command(['rev-parse', 'HEAD'])
            
            # 获取状态
            status = await self._run_git_command(['status', '--porcelain'])
            
            # 获取最近的提交
            commits = await self._run_git_command(['log', '-5', '--pretty=format:%h %s'])
            
            # 获取你的最近提交
            your_commits = await self._run_git_command(['log', '-5', '--pretty=format:%h %s'])
            
            return f"""This is the git status at the start of the conversation. Note that this status is a snapshot in time, and will not update during the conversation.
Current branch: {branch}

Main branch (you will usually use this for PRs): {main_branch}

Status:
{status}

Recent commits:
{commits}

Your recent commits:
{your_commits}"""
        except Exception as e:
            logger.error(f"获取 Git 状态失败: {str(e)}")
            return f"Error getting git status: {str(e)}"

    async def _run_git_command(self, args: List[str]) -> str:
        """执行git命令并返回结果"""
        try:
            process = await asyncio.create_subprocess_exec(
                'git',
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.cwd
            )
            stdout, _ = await process.communicate()
            return stdout.decode().strip()
        except Exception as e:
            self.logger.error(f"执行git命令失败 {args}: {str(e)}")
            return ""

    async def get_git_email(self) -> Optional[str]:
        """获取git配置的用户邮箱"""
        try:
            email = await self._run_git_command(['config', 'user.email'])
            return email if email else None
        except Exception as e:
            self.logger.error(f"获取git邮箱失败: {str(e)}")
            return None

    async def has_memory_files(self) -> bool:
        """检查是否存在 MEMORY.ME 文件"""
        try:
            for root, _, files in os.walk(self.cwd):
                if self.MEMORY_FILE in files:
                    return True
            return False
        except Exception:
            return False

    async def get_memory_content(self, file_path: str) -> Optional[str]:
        """获取指定 MEMORY.ME 文件的内容"""
        try:
            path = Path(file_path)
            if not path.exists() or path.name != self.MEMORY_FILE:
                return None
            return await asyncio.to_thread(path.read_text, encoding='utf-8')
        except Exception as e:
            self.logger.error(f"读取 MEMORY.ME 文件失败: {str(e)}")
            return None

    async def has_readme(self) -> bool:
        """检查是否存在 README.md"""
        try:
            readme_path = Path(self.cwd) / 'README.md'
            return readme_path.exists()
        except Exception:
            return False

    async def get_readme(self) -> Optional[str]:
        """获取 README.md 内容"""
        try:
            readme_path = Path(self.cwd) / 'README.md'
            if not readme_path.exists():
                return None
            return await asyncio.to_thread(readme_path.read_text, encoding='utf-8')
        except Exception as e:
            self.logger.error(f"读取 README.md 失败: {str(e)}")
            return None 