from setuptools import setup, find_packages
import site
import sys

# 添加用户特定的site-packages路径
site.ENABLE_USER_SITE = True

setup(
    name="task-planner-system",
    version="0.1",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=[
        'pydantic>=2.0',
        'pyautogen>=0.2.0'
    ],
    entry_points={
        'console_scripts': [
            'task-planner=task_planner.cli:main',
        ],
    },
    # 添加这些选项来确保正确的安装位置
    python_requires='>=3.8',
    zip_safe=False,
    include_package_data=True,
)
