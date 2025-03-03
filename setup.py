from setuptools import setup, find_packages

setup(
    name="task_planner",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,
    install_requires=[
        "flask",
        "werkzeug",
        "requests",
        "plotly",
        "pandas",
        "psutil",
    ],
    python_requires=">=3.6",
    entry_points={
        "console_scripts": [
            "task-planner=task_planner.cli:main",
        ],
    },
    author="Wang Bo",
    description="任务拆分与执行系统",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
