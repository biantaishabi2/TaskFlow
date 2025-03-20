# AG2-Agent集成到Task Planner的设计方案

## 1. 背景与需求

当前task_planner项目中已有一个基于Claude Code的executor，运行良好。我们希望创建一个完全独立的、基于AG2-Agent的新executor接口，不修改现有executor，让用户可以根据需要选择使用哪种executor。目前AG2-Agent代码位于`/home/wangbo/document/wangbo/dev/ag2-agent/`目录中，需要将其适当集成到task_planner项目中。

## 2. 设计目标

1. 创建一个完全独立的AG2执行器接口和实现
2. 不修改现有的Claude Code executor代码
3. 提供独立的命令行入口点来使用AG2执行器
4. 支持通过配置文件灵活设置AG2-Agent的对话模式和工具
5. 清晰定义如何从当前AG2-Agent项目迁移代码到task_planner

## 3. 系统架构设计

### 3.1 整体架构

创建全新的、独立于现有executor的模块：

```
task_planner/
├── core/
│   └── task_executor.py (保持不变)
├── ag2_engine/             # 全新的、独立的模块
│   ├── __init__.py
│   ├── ag2_executor.py     # AG2执行器核心实现
│   ├── cli.py              # AG2执行器的命令行入口
│   ├── config_loader.py    # 配置加载工具
│   └── adapters/
│       ├── __init__.py
│       ├── llm_adapters.py # LLM服务适配器
│       └── tool_adapters.py # 工具适配器
├── vendor/                 # 第三方库依赖
│   └── ag2_agent/          # 复制的AG2-Agent核心代码
└── cli.py (保持不变)
```

### 3.2 命令行入口

创建一个全新的、独立的命令行入口来使用AG2执行器：

```python
# ag2_engine/cli.py
import argparse
import sys
import yaml
import os

from task_planner.ag2_engine.ag2_executor import AG2Executor

def parse_args():
    parser = argparse.ArgumentParser(description="使用AG2-Agent执行任务")
    
    parser.add_argument(
        "--task", 
        type=str, 
        required=True,
        help="要执行的任务描述"
    )
    
    parser.add_argument(
        "--config", 
        type=str,
        default="configs/ag2_config.yaml",
        help="AG2执行器配置文件路径"
    )
    
    parser.add_argument(
        "--mode", 
        type=str,
        choices=["two_agent", "sequential", "group", "nested", "swarm"],
        default="sequential",
        help="AG2执行器的对话模式"
    )
    
    parser.add_argument(
        "--output", 
        type=str,
        help="输出结果文件路径"
    )
    
    return parser.parse_args()

def main():
    """AG2执行器命令行入口点"""
    args = parse_args()
    
    # 创建AG2执行器
    executor = AG2Executor(
        config_path=args.config,
        mode=args.mode
    )
    
    # 执行任务
    task = {"description": args.task}
    result = executor.execute(task)
    
    # 输出结果
    if args.output:
        with open(args.output, 'w') as f:
            yaml.dump(result, f)
    else:
        print(yaml.dump(result))
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

### 3.3 AG2执行器实现

独立的AG2执行器实现，不依赖于现有的task_executor：

```python
# ag2_engine/ag2_executor.py
import os
import yaml
import asyncio
from typing import Dict, Any, Optional

from task_planner.vendor.ag2_agent import create_orchestration_manager
from task_planner.vendor.ag2_agent.factories.factory_registry import register_default_factories

class AG2Executor:
    """基于AG2-Agent的独立执行器"""
    
    def __init__(self, config_path: Optional[str] = None, mode: str = "sequential"):
        """初始化AG2执行器
        
        Args:
            config_path: AG2配置文件路径
            mode: 对话模式 (two_agent, sequential, group, nested, swarm)
        """
        self.manager = create_orchestration_manager()
        self.config = self._load_config(config_path)
        self.mode = mode
        
        # 注册默认工厂
        for name, factory in register_default_factories().items():
            self.manager.register_chat_factory(name, factory)
            
        # 设置agents和tools
        self._setup_agents()
        self._setup_tools()
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """加载配置文件
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            配置字典
        """
        if not config_path or not os.path.exists(config_path):
            return {}
            
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _setup_agents(self) -> None:
        """从配置设置agents"""
        for name, agent_config in self.config.get('agents', {}).items():
            # 这里需要根据配置创建适当的agent
            # 简化实现，实际中需要更复杂的逻辑
            self.manager.register_agent(name, agent_config)
    
    def _setup_tools(self) -> None:
        """从配置设置工具"""
        for name, tool_config in self.config.get('tools', {}).items():
            # 简化实现，实际中需要更复杂的逻辑
            self.manager.register_tool(
                name=name,
                tool_function=lambda params, tool_name=name: self._execute_tool(tool_name, params),
                description=tool_config.get('description', '')
            )
    
    def _execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """执行工具
        
        Args:
            tool_name: 工具名称
            params: 工具参数
            
        Returns:
            工具执行结果
        """
        # 实际实现中，这里需要根据配置动态调用适当的工具
        # 简化实现
        return {"result": f"执行工具 {tool_name} 完成", "params": params}
    
    def _get_agents_for_mode(self) -> Dict[str, Any]:
        """根据当前模式获取适当的agents配置
        
        Returns:
            agents配置字典
        """
        mode_config = self.config.get('modes', {}).get(self.mode, {})
        return mode_config.get('agents', {})
    
    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """执行任务
        
        Args:
            task: 任务描述字典
            
        Returns:
            执行结果
        """
        # 使用asyncio运行异步代码
        return asyncio.run(self._execute_async(task))
    
    async def _execute_async(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """异步执行任务
        
        Args:
            task: 任务描述字典
            
        Returns:
            执行结果
        """
        # 根据任务和模式创建对话
        agents = self._get_agents_for_mode()
        chat = self.manager.create_chat(
            mode=self.mode,
            agents=agents,
            initial_prompt=task.get("description", ""),
            config=self.config.get('modes', {}).get(self.mode, {}).get('config', {})
        )
        
        # 执行对话
        response = await chat.initiate_chat(task.get("description", ""))
        
        # 如果需要额外的任务处理
        if task.get("follow_up"):
            for message in task.get("follow_up"):
                response = await chat.continue_chat(message)
        
        # 结束对话并获取结果
        result = chat.end_chat()
        
        # 返回结果
        return {
            "result": response,
            "status": "completed",
            "metadata": result
        }
```

### 3.4 配置文件设计

AG2执行器配置文件示例：

```yaml
# configs/ag2_config.yaml
# AG2执行器配置

# 定义可用的agents
agents:
  task_planner:
    name: "任务规划专家"
    type: "llm"
    llm_config:
      model_name: "claude-3-5-sonnet"
      temperature: 0.2
      system_message: "你是一个专业的任务规划专家，负责将复杂任务分解为可执行的子任务。"
  
  executor:
    name: "代码执行者"
    type: "llm"
    llm_config:
      model_name: "claude-3-5-sonnet"
      temperature: 0.0
      system_message: "你是一个代码执行专家，负责执行代码并报告结果。"
  
  analyst:
    name: "数据分析专家"
    type: "llm"
    llm_config:
      model_name: "claude-3-5-sonnet" 
      temperature: 0.1
      system_message: "你是一个数据分析专家，擅长解读数据并提供见解。"

# 定义可用的工具
tools:
  file_reader:
    description: "读取本地文件内容"
    adapter: "task_planner.ag2_engine.adapters.tool_adapters.FileToolAdapter"
    params:
      base_path: "/home/data"
  
  web_search:
    description: "搜索互联网获取信息"
    adapter: "task_planner.ag2_engine.adapters.tool_adapters.WebSearchAdapter"
    params:
      api_key: "${WEB_SEARCH_API_KEY}"

# 特定对话模式的配置
modes:
  two_agent:
    agents: ["task_planner", "executor"]
    config:
      max_turns: 10
  
  sequential:
    agents: ["task_planner", "executor", "analyst"]
    config:
      max_turns: 10
      timeout: 300
  
  group:
    agents: ["task_planner", "executor", "analyst"]
    config:
      max_rounds: 5
      facilitator: "task_planner"
  
  swarm:
    agents:
      coordinator: "task_planner"
      coder: "executor"
      reviewer: "analyst"
    config:
      max_subtasks: 5
      parallel_execution: true
```

## 4. 具体文件迁移与集成步骤

### 4.1 文件夹结构创建

首先在task_planner项目中创建所需的目录结构：

```bash
# 创建所需目录结构
cd /home/wangbo/document/wangbo/task_planner
mkdir -p ag2_engine/adapters
mkdir -p vendor
mkdir -p configs
touch ag2_engine/__init__.py
touch ag2_engine/adapters/__init__.py
```

### 4.2 AG2-Agent核心代码迁移

使用复制代码到vendor目录的方式：

```bash
# 将AG2-Agent核心代码复制到vendor目录
cp -r /home/wangbo/document/wangbo/dev/ag2-agent/ag2_agent /home/wangbo/document/wangbo/task_planner/vendor/

# 确保setup.py或requirements.txt包含AG2-Agent所需依赖
```

### 4.3 创建新文件

1. **AG2执行器核心实现**:

```bash
# 创建AG2执行器文件
touch /home/wangbo/document/wangbo/task_planner/ag2_engine/ag2_executor.py
```

2. **命令行入口**:

```bash
# 创建命令行入口文件
touch /home/wangbo/document/wangbo/task_planner/ag2_engine/cli.py
```

3. **配置加载器**:

```bash
# 创建配置加载器
touch /home/wangbo/document/wangbo/task_planner/ag2_engine/config_loader.py
```

4. **适配器文件**:

```bash
# 创建LLM适配器
touch /home/wangbo/document/wangbo/task_planner/ag2_engine/adapters/llm_adapters.py

# 创建工具适配器
touch /home/wangbo/document/wangbo/task_planner/ag2_engine/adapters/tool_adapters.py
```

5. **示例配置**:

```bash
# 创建示例配置文件
touch /home/wangbo/document/wangbo/task_planner/configs/ag2_config.yaml
```

## 5. 具体实施计划与进度

下面是完整的实施计划，包含具体命令和进度标记：

### 5.1 阶段1: 准备目录结构 [待完成]

```bash
# 进入task_planner目录
cd /home/wangbo/document/wangbo/task_planner

# 创建目录结构
mkdir -p ag2_engine/adapters
mkdir -p vendor
mkdir -p configs

# 创建空的初始化文件
touch ag2_engine/__init__.py
touch ag2_engine/adapters/__init__.py
```

### 5.2 阶段2: 复制AG2-Agent代码 [待完成]

```bash
# 复制AG2-Agent核心代码到vendor目录
cp -r /home/wangbo/document/wangbo/dev/ag2-agent/ag2_agent /home/wangbo/document/wangbo/task_planner/vendor/

# 检查复制的代码
ls -la /home/wangbo/document/wangbo/task_planner/vendor/ag2_agent/
```

### 5.3 阶段3: 创建AG2执行器核心文件 [待完成]

```bash
# 创建AG2执行器实现文件
cat > /home/wangbo/document/wangbo/task_planner/ag2_engine/ag2_executor.py << 'EOF'
import os
import yaml
import asyncio
from typing import Dict, Any, Optional

from task_planner.vendor.ag2_agent import create_orchestration_manager
from task_planner.vendor.ag2_agent.factories.factory_registry import register_default_factories

class AG2Executor:
    """基于AG2-Agent的独立执行器"""
    
    def __init__(self, config_path: Optional[str] = None, mode: str = "sequential"):
        """初始化AG2执行器
        
        Args:
            config_path: AG2配置文件路径
            mode: 对话模式 (two_agent, sequential, group, nested, swarm)
        """
        self.manager = create_orchestration_manager()
        self.config = self._load_config(config_path)
        self.mode = mode
        
        # 注册默认工厂
        for name, factory in register_default_factories().items():
            self.manager.register_chat_factory(name, factory)
            
        # 设置agents和tools
        self._setup_agents()
        self._setup_tools()
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """加载配置文件
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            配置字典
        """
        if not config_path or not os.path.exists(config_path):
            return {}
            
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _setup_agents(self) -> None:
        """从配置设置agents"""
        for name, agent_config in self.config.get('agents', {}).items():
            # 这里需要根据配置创建适当的agent
            # 简化实现，实际中需要更复杂的逻辑
            self.manager.register_agent(name, agent_config)
    
    def _setup_tools(self) -> None:
        """从配置设置工具"""
        for name, tool_config in self.config.get('tools', {}).items():
            # 简化实现，实际中需要更复杂的逻辑
            self.manager.register_tool(
                name=name,
                tool_function=lambda params, tool_name=name: self._execute_tool(tool_name, params),
                description=tool_config.get('description', '')
            )
    
    def _execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """执行工具
        
        Args:
            tool_name: 工具名称
            params: 工具参数
            
        Returns:
            工具执行结果
        """
        # 实际实现中，这里需要根据配置动态调用适当的工具
        # 简化实现
        return {"result": f"执行工具 {tool_name} 完成", "params": params}
    
    def _get_agents_for_mode(self) -> Dict[str, Any]:
        """根据当前模式获取适当的agents配置
        
        Returns:
            agents配置字典
        """
        mode_config = self.config.get('modes', {}).get(self.mode, {})
        return mode_config.get('agents', {})
    
    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """执行任务
        
        Args:
            task: 任务描述字典
            
        Returns:
            执行结果
        """
        # 使用asyncio运行异步代码
        return asyncio.run(self._execute_async(task))
    
    async def _execute_async(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """异步执行任务
        
        Args:
            task: 任务描述字典
            
        Returns:
            执行结果
        """
        # 根据任务和模式创建对话
        agents = self._get_agents_for_mode()
        chat = self.manager.create_chat(
            mode=self.mode,
            agents=agents,
            initial_prompt=task.get("description", ""),
            config=self.config.get('modes', {}).get(self.mode, {}).get('config', {})
        )
        
        # 执行对话
        response = await chat.initiate_chat(task.get("description", ""))
        
        # 如果需要额外的任务处理
        if task.get("follow_up"):
            for message in task.get("follow_up"):
                response = await chat.continue_chat(message)
        
        # 结束对话并获取结果
        result = chat.end_chat()
        
        # 返回结果
        return {
            "result": response,
            "status": "completed",
            "metadata": result
        }
EOF
```

### 5.4 阶段4: 创建命令行入口 [待完成]

```bash
# 创建命令行入口文件
cat > /home/wangbo/document/wangbo/task_planner/ag2_engine/cli.py << 'EOF'
import argparse
import sys
import yaml
import os

from task_planner.ag2_engine.ag2_executor import AG2Executor

def parse_args():
    parser = argparse.ArgumentParser(description="使用AG2-Agent执行任务")
    
    parser.add_argument(
        "--task", 
        type=str, 
        required=True,
        help="要执行的任务描述"
    )
    
    parser.add_argument(
        "--config", 
        type=str,
        default="configs/ag2_config.yaml",
        help="AG2执行器配置文件路径"
    )
    
    parser.add_argument(
        "--mode", 
        type=str,
        choices=["two_agent", "sequential", "group", "nested", "swarm"],
        default="sequential",
        help="AG2执行器的对话模式"
    )
    
    parser.add_argument(
        "--output", 
        type=str,
        help="输出结果文件路径"
    )
    
    return parser.parse_args()

def main():
    """AG2执行器命令行入口点"""
    args = parse_args()
    
    # 创建AG2执行器
    executor = AG2Executor(
        config_path=args.config,
        mode=args.mode
    )
    
    # 执行任务
    task = {"description": args.task}
    result = executor.execute(task)
    
    # 输出结果
    if args.output:
        with open(args.output, 'w') as f:
            yaml.dump(result, f)
    else:
        print(yaml.dump(result))
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
EOF
```

### 5.5 阶段5: 创建配置加载器 [待完成]

```bash
# 创建配置加载器文件
cat > /home/wangbo/document/wangbo/task_planner/ag2_engine/config_loader.py << 'EOF'
import os
import yaml
from typing import Dict, Any, Optional

def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """加载AG2执行器配置
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        配置字典
    """
    if not config_path or not os.path.exists(config_path):
        return {}
        
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"加载配置错误: {e}")
        return {}
EOF
```

### 5.6 阶段6: 创建适配器文件 [待完成]

```bash
# 创建LLM适配器文件
cat > /home/wangbo/document/wangbo/task_planner/ag2_engine/adapters/llm_adapters.py << 'EOF'
from typing import Dict, Any, Optional, List, AsyncGenerator
import asyncio
from abc import ABC, abstractmethod

class BaseLLMAdapter(ABC):
    """LLM服务适配器基类"""
    
    @abstractmethod
    async def generate(self, messages: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """生成回复
        
        Args:
            messages: 消息列表
            **kwargs: 其他参数
            
        Returns:
            生成的回复
        """
        pass
    
    @abstractmethod
    async def generate_stream(self, messages: List[Dict[str, Any]], **kwargs) -> AsyncGenerator[Dict[str, Any], None]:
        """生成流式回复
        
        Args:
            messages: 消息列表
            **kwargs: 其他参数
            
        Yields:
            生成的回复片段
        """
        pass

class ClaudeLLMAdapter(BaseLLMAdapter):
    """Claude LLM服务适配器"""
    
    def __init__(self, model_name: str = "claude-3-5-sonnet", **kwargs):
        """初始化Claude适配器
        
        Args:
            model_name: 模型名称
            **kwargs: 其他参数
        """
        self.model_name = model_name
        self.config = kwargs
    
    async def generate(self, messages: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """使用Claude生成回复
        
        Args:
            messages: 消息列表
            **kwargs: 其他参数
            
        Returns:
            生成的回复
        """
        # 实际实现中，这里需要调用Claude API
        # 简化实现
        return {"content": "这是Claude生成的回复", "role": "assistant"}
    
    async def generate_stream(self, messages: List[Dict[str, Any]], **kwargs) -> AsyncGenerator[Dict[str, Any], None]:
        """使用Claude生成流式回复
        
        Args:
            messages: 消息列表
            **kwargs: 其他参数
            
        Yields:
            生成的回复片段
        """
        # 简化实现
        chunks = ["这是", "Claude", "生成的", "流式", "回复"]
        for chunk in chunks:
            yield {"content": chunk, "role": "assistant"}
            await asyncio.sleep(0.1)

# 根据需要添加其他LLM适配器
EOF

# 创建工具适配器文件
cat > /home/wangbo/document/wangbo/task_planner/ag2_engine/adapters/tool_adapters.py << 'EOF'
from typing import Dict, Any, Optional, List, Callable
from abc import ABC, abstractmethod

class BaseToolAdapter(ABC):
    """工具适配器基类"""
    
    @abstractmethod
    def execute(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """执行工具
        
        Args:
            tool_name: 工具名称
            params: 工具参数
            
        Returns:
            工具执行结果
        """
        pass
    
    @abstractmethod
    def get_tools(self) -> Dict[str, Dict[str, Any]]:
        """获取所有可用工具信息
        
        Returns:
            工具信息字典
        """
        pass

class FileToolAdapter(BaseToolAdapter):
    """文件操作工具适配器"""
    
    def __init__(self, base_path: str = "."):
        """初始化文件工具适配器
        
        Args:
            base_path: 基础路径
        """
        self.base_path = base_path
        self._tools = {
            "read_file": {
                "description": "读取文件内容",
                "function": self._read_file
            },
            "write_file": {
                "description": "写入文件内容",
                "function": self._write_file
            },
            "list_files": {
                "description": "列出目录中的文件",
                "function": self._list_files
            }
        }
    
    def execute(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """执行文件工具
        
        Args:
            tool_name: 工具名称
            params: 工具参数
            
        Returns:
            工具执行结果
            
        Raises:
            ValueError: 工具不存在或执行失败
        """
        if tool_name not in self._tools:
            raise ValueError(f"未知的工具: {tool_name}")
        
        tool_func = self._tools[tool_name]["function"]
        return tool_func(params)
    
    def get_tools(self) -> Dict[str, Dict[str, Any]]:
        """获取所有可用文件工具信息
        
        Returns:
            工具信息字典
        """
        return {name: {"description": info["description"]} for name, info in self._tools.items()}
    
    def _read_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """读取文件内容
        
        Args:
            params: 包含file_path的参数字典
            
        Returns:
            包含文件内容的结果字典
        """
        file_path = params.get("file_path")
        if not file_path:
            return {"error": "缺少必要参数: file_path"}
        
        try:
            import os
            full_path = os.path.join(self.base_path, file_path)
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return {"content": content}
        except Exception as e:
            return {"error": f"读取文件失败: {str(e)}"}
    
    def _write_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """写入文件内容
        
        Args:
            params: 包含file_path和content的参数字典
            
        Returns:
            执行结果字典
        """
        file_path = params.get("file_path")
        content = params.get("content")
        if not file_path or content is None:
            return {"error": "缺少必要参数: file_path或content"}
        
        try:
            import os
            full_path = os.path.join(self.base_path, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return {"success": True}
        except Exception as e:
            return {"error": f"写入文件失败: {str(e)}"}
    
    def _list_files(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """列出目录中的文件
        
        Args:
            params: 包含dir_path的参数字典
            
        Returns:
            包含文件列表的结果字典
        """
        dir_path = params.get("dir_path", ".")
        
        try:
            import os
            full_path = os.path.join(self.base_path, dir_path)
            files = os.listdir(full_path)
            return {"files": files}
        except Exception as e:
            return {"error": f"列出文件失败: {str(e)}"}

class WebSearchAdapter(BaseToolAdapter):
    """Web搜索工具适配器"""
    
    def __init__(self, api_key: Optional[str] = None):
        """初始化Web搜索适配器
        
        Args:
            api_key: API密钥
        """
        self.api_key = api_key
        self._tools = {
            "search": {
                "description": "搜索互联网信息",
                "function": self._search
            }
        }
    
    def execute(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """执行Web搜索工具
        
        Args:
            tool_name: 工具名称
            params: 工具参数
            
        Returns:
            工具执行结果
        """
        if tool_name not in self._tools:
            raise ValueError(f"未知的工具: {tool_name}")
        
        tool_func = self._tools[tool_name]["function"]
        return tool_func(params)
    
    def get_tools(self) -> Dict[str, Dict[str, Any]]:
        """获取所有可用Web搜索工具信息
        
        Returns:
            工具信息字典
        """
        return {name: {"description": info["description"]} for name, info in self._tools.items()}
    
    def _search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """搜索互联网信息
        
        Args:
            params: 包含query的参数字典
            
        Returns:
            搜索结果字典
        """
        query = params.get("query")
        if not query:
            return {"error": "缺少必要参数: query"}
        
        # 实际实现中，这里需要调用搜索API
        # 简化实现
        return {
            "results": [
                {"title": "示例结果1", "snippet": "这是示例搜索结果1", "url": "https://example.com/1"},
                {"title": "示例结果2", "snippet": "这是示例搜索结果2", "url": "https://example.com/2"}
            ]
        }

# 根据需要添加其他工具适配器
EOF
```

### 5.7 阶段7: 创建示例配置文件 [待完成]

```bash
# 创建示例配置文件
cat > /home/wangbo/document/wangbo/task_planner/configs/ag2_config.yaml << 'EOF'
# AG2执行器配置

# 定义可用的agents
agents:
  task_planner:
    name: "任务规划专家"
    type: "llm"
    llm_config:
      model_name: "claude-3-5-sonnet"
      temperature: 0.2
      system_message: "你是一个专业的任务规划专家，负责将复杂任务分解为可执行的子任务。"
  
  executor:
    name: "代码执行者"
    type: "llm"
    llm_config:
      model_name: "claude-3-5-sonnet"
      temperature: 0.0
      system_message: "你是一个代码执行专家，负责执行代码并报告结果。"
  
  analyst:
    name: "数据分析专家"
    type: "llm"
    llm_config:
      model_name: "claude-3-5-sonnet" 
      temperature: 0.1
      system_message: "你是一个数据分析专家，擅长解读数据并提供见解。"

# 定义可用的工具
tools:
  file_reader:
    description: "读取本地文件内容"
    adapter: "task_planner.ag2_engine.adapters.tool_adapters.FileToolAdapter"
    params:
      base_path: "/home/data"
  
  web_search:
    description: "搜索互联网获取信息"
    adapter: "task_planner.ag2_engine.adapters.tool_adapters.WebSearchAdapter"
    params:
      api_key: "${WEB_SEARCH_API_KEY}"

# 特定对话模式的配置
modes:
  two_agent:
    agents: ["task_planner", "executor"]
    config:
      max_turns: 10
  
  sequential:
    agents: ["task_planner", "executor", "analyst"]
    config:
      max_turns: 10
      timeout: 300
  
  group:
    agents: ["task_planner", "executor", "analyst"]
    config:
      max_rounds: 5
      facilitator: "task_planner"
  
  swarm:
    agents:
      coordinator: "task_planner"
      coder: "executor"
      reviewer: "analyst"
    config:
      max_subtasks: 5
      parallel_execution: true
EOF
```

### 5.8 阶段8: 测试与验证 [待完成]

```bash
# 测试AG2执行器
cd /home/wangbo/document/wangbo/task_planner

# 简单测试命令行接口
python -m ag2_engine.cli --task "简单测试任务" --mode sequential

# 使用配置文件测试
python -m ag2_engine.cli --task "使用配置文件测试" --config configs/ag2_config.yaml --mode group

# 测试输出到文件
python -m ag2_engine.cli --task "测试输出到文件" --mode swarm --output ./test_result.yaml
```

### 实施进度跟踪表

| 阶段 | 任务描述 | 状态 | 计划完成时间 |
|------|---------|------|------------|
| 1 | 创建目录结构 | 待完成 | 第1天 |
| 2 | 复制AG2-Agent代码 | 待完成 | 第1天 |
| 3 | 创建AG2执行器核心文件 | 待完成 | 第2天 |
| 4 | 创建命令行入口 | 待完成 | 第2天 |
| 5 | 创建配置加载器 | 待完成 | 第2天 |
| 6 | 创建适配器文件 | 待完成 | 第3天 |
| 7 | 创建示例配置文件 | 待完成 | 第3天 |
| 8 | 测试与验证 | 待完成 | 第4天 |

## 6. 使用方式

### 6.1 使用原有Claude Code执行器

```bash
# 继续使用现有命令行，不变
python -m task_planner.cli plan --task "分析销售数据并生成报告"
```

### 6.2 使用新的AG2执行器

```bash
# 使用新的AG2命令行入口
python -m task_planner.ag2_engine.cli --task "分析销售数据并生成报告" \
  --mode sequential \
  --config configs/ag2_config.yaml \
  --output results/analysis_report.yaml
```

## 7. 注意事项与挑战

1. **依赖管理**: 确保AG2-Agent及其依赖正确安装
2. **配置灵活性**: 设计灵活的配置系统，支持不同的对话模式和工具
3. **与现有系统兼容**: 确保结果格式与现有系统兼容，便于后续集成
4. **错误处理**: 添加健壮的错误处理机制
5. **版本管理**: 复制到vendor方式需要管理AG2-Agent代码的版本同步

## 8. 总结

本设计方案采用完全独立模块的方式，创建一个新的基于AG2-Agent的执行器，不修改现有Claude Code executor。通过独立的命令行入口和配置文件，提供了使用AG2-Agent执行任务的能力，同时保持了对现有系统的零影响。

方案详细指定了如何从当前AG2-Agent项目迁移代码到task_planner项目，包括完整的实施计划、具体命令和进度跟踪。这种方法风险低、集成简单，同时为将来可能的更深入集成奠定了基础。