使用Docker运行步骤指南
# Docker运行指南

本项目已配置Docker环境，可以通过以下步骤运行:

## 1. 准备配置文件

首先，需要将本机的Claude CLI配置复制到Docker环境：

```bash
# 将.claude.json配置文件复制到项目根目录
cp /home/wangbo/.claude.json /home/wangbo/document/wangbo/code_rag/.claude.json
```

> 注意：这个文件包含了Claude的OAuth认证信息和API密钥

## 2. 构建和启动容器

```bash
# 使用docker-compose构建并启动
docker-compose up -d
```

## 3. 查看日志

```bash
# 查看运行日志
docker-compose logs -f
```

## 4. 修改运行入口

您可以在docker-compose.yml文件中直接修改command来选择运行不同的程序:

```yaml
services:
  code-rag:
    # ... 其他配置 ...
    # 选择以下命令之一:
    
    # 任务可视化服务器
    command: python task_visualization_server.py
    
    # 任务分解系统(需要传入任务参数)
    command: python task_decomposition_system.py "您的任务描述"
    
    # 并行任务分解系统(需要传入任务参数)
    command: python parallel_task_decomposition_system.py "您的任务描述"
    
    # 直接进入Claude命令行模式
    command: claude
    
    # API服务器模式(外部程序可通过HTTP调用)
    command: python task_api_server.py
```

## 5. 从外部调用容器内的框架

以下是几种从外部程序调用容器内任务分解框架的方法：

### 方法1: 通过REST API (推荐)

在项目中创建API服务器文件`task_api_server.py`：

```python
from flask import Flask, request, jsonify
from task_decomposition_system import TaskDecompositionSystem

app = Flask(__name__)

@app.route('/execute_task', methods=['POST'])
def execute_task():
    data = request.json
    task_description = data.get('task')
    system = TaskDecompositionSystem()
    result = system.execute_complex_task(task_description)
    return jsonify({"result": result})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9000)
```

然后在docker-compose.yml中使用此服务器：
```yaml
command: python task_api_server.py
```

外部程序可以通过HTTP请求调用：
```python
import requests

response = requests.post("http://localhost:12345/execute_task", 
                         json={"task": "分析此代码并优化性能"})
result = response.json()
```

### 方法2: 直接通过Docker执行命令

```bash
# 从外部调用并传递参数
docker exec code-rag python task_decomposition_system.py "您的任务描述"
```

### 方法3: 使用共享卷进行文件交换

在docker-compose.yml中添加共享卷：
```yaml
volumes:
  - ./logs:/app/logs
  - ./input:/app/input   # 用于从外部传入任务
  - ./output:/app/output # 用于将结果返回给外部
```

创建任务监控脚本在容器内运行：
```python
# task_monitor.py
import os
import json
import time
from task_decomposition_system import TaskDecompositionSystem

INPUT_DIR = "/app/input"
OUTPUT_DIR = "/app/output"

system = TaskDecompositionSystem()

while True:
    for filename in os.listdir(INPUT_DIR):
        if filename.endswith('.json'):
            file_path = os.path.join(INPUT_DIR, filename)
            
            with open(file_path, 'r') as f:
                try:
                    data = json.load(f)
                    task_id = data.get('id', 'unknown')
                    task = data.get('task', '')
                    
                    # 执行任务
                    result = system.execute_complex_task(task)
                    
                    # 输出结果
                    output_path = os.path.join(OUTPUT_DIR, f"result_{task_id}.json")
                    with open(output_path, 'w') as out_f:
                        json.dump({"id": task_id, "result": result}, out_f)
                    
                    # 删除已处理的输入文件
                    os.remove(file_path)
                except Exception as e:
                    print(f"Error processing {filename}: {e}")
                    
    time.sleep(5)  # 每5秒检查一次
```

## 6. 停止容器

```bash
docker-compose down
```

## 功能特性

已安装以下组件:

1. **Claude CLI工具**: 已在容器中安装`@anthropic-ai/claude-code`，可直接使用`claude`命令

2. **Python依赖**: 已安装所有必要Python库，包括Flask, Pandas, Numpy等

3. **Node.js**: 已安装Node.js 20.x，支持运行JavaScript应用

4. **配置同步**: 使用本机的Claude配置文件，确保OAuth认证信息正确

## 环境变量和配置

Docker环境中已包含：

1. Claude CLI的OAuth认证配置（从.claude.json）
2. 必要的环境变量

当系统使用pexpect调用Claude命令行工具时，会使用容器中的配置文件，无需再次认证。
