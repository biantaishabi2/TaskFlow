# TaskPlanner 实施方案

## 实施目标

开发一个基于AutoGen的任务规划执行系统，支持复杂工作流自动化，集成人工确认机制，实现高效、安全、可扩展的任务处理框架。

## 实施步骤

### 第一阶段：基础架构搭建（4周）

1. **核心组件设计与开发**
   - TaskExecutor基础实现
   - TaskContext框架设计
   - 基本配置管理系统
   - 单元测试框架搭建

2. **执行环境准备**
   - 开发环境配置
   - 依赖管理系统实现
   - CI/CD流程设计
   - 代码规范与文档模板

3. **成果验收**
   - 基础组件单元测试通过
   - 简单任务执行流程演示
   - 技术文档初稿

### 第二阶段：核心功能实现（6周）

1. **TaskContext组件扩展**
   - VariableManager实现变量作用域管理
   - 完善ArtifactManager产物管理功能
   - 实现ExecutionHistory执行历史记录
   - 组件集成测试

2. **AutoGen集成开发**
   - AutoGenExecutor基础实现
   - AutoGen代理注册与管理机制
   - 工具调用路由系统
   - 人机交互接口设计

3. **权限管理系统**
   - 基于human input的权限确认机制
   - 上下文感知的权限决策系统
   - 权限审计日志实现
   - 安全模型测试用例

4. **成果验收**
   - 完整任务执行流程测试通过
   - 权限管理机制演示
   - 技术文档更新

### 第三阶段：高级特性开发（4周）

1. **TaskPlanner系统集成**
   - 整合TaskExecutor与AutoGenExecutor
   - 实现统一调度接口
   - 完善错误处理机制
   - 系统集成测试

2. **多代理协作模式**
   - 专家代理角色定义
   - 代理间通信协议实现
   - 任务分解与协作机制
   - 多代理系统测试

3. **成果验收**
   - 复杂任务执行测试通过
   - 多代理协作模式演示
   - 技术文档完善

### 第四阶段：优化与扩展（4周）

1. **性能优化**
   - 并行任务执行优化
   - 缓存系统实现
   - 资源使用效率提升
   - 性能测试与基准

2. **插件系统开发**
   - 插件接口设计
   - 核心插件实现
   - 插件管理系统
   - 插件文档与示例

3. **成果验收**
   - 性能指标达成
   - 插件系统演示
   - 完整技术文档

### 第五阶段：用户体验与文档（2周）

1. **用户界面优化**
   - CLI界面完善
   - 交互式配置系统
   - 执行状态可视化
   - 用户体验测试

2. **文档与培训**
   - 用户手册编写
   - 开发者文档完善
   - 示例与教程制作
   - 内部培训与知识转移

3. **成果验收**
   - 用户体验评估通过
   - 文档完整性验证
   - 系统部署演示

## 关键技术点

1. **AutoGen集成**
   - 模型接口封装
   - 多代理协调机制
   - 工具注册与调用

2. **权限管理**
   - Human-in-the-loop确认
   - 上下文感知安全决策
   - 权限审计与追踪

3. **变量管理**
   - 多级作用域机制
   - 类型安全验证
   - 变量历史追踪

4. **工作流编排**
   - 任务依赖管理
   - 并行执行控制
   - 错误恢复策略

## 风险与缓解措施

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|----------|
| AutoGen API变更 | 中 | 高 | 封装适配层，快速响应变更 |
| 性能瓶颈 | 中 | 中 | 早期性能测试，增量优化 |
| 安全漏洞 | 低 | 高 | 严格权限管理，安全审计 |
| 需求变更 | 高 | 中 | 模块化设计，灵活响应变化 |
| 测试覆盖不足 | 中 | 中 | 自动化测试，TDD开发模式 |

## 实施团队

- 项目负责人：1名
- 后端开发工程师：2名
- AI集成专家：1名
- 测试工程师：1名
- 文档与DevOps：1名

## 里程碑计划

| 里程碑 | 时间点 | 关键成果 |
|--------|--------|----------|
| 基础架构完成 | 第4周末 | 核心组件可运行，基本流程可执行 |
| 核心功能实现 | 第10周末 | 变量管理、产物管理、权限系统可用 |
| 高级特性完成 | 第14周末 | 多代理协作，复杂任务处理能力 |
| 优化与扩展 | 第18周末 | 性能指标达成，插件系统可用 |
| 项目交付 | 第20周末 | 完整系统部署上线，文档完备 |

---

# 附录：TaskPlanner设计方案

## 1. 核心架构设计

### 1.1 组件层次结构

```
TaskPlanner
├── TaskExecutor (任务执行器) ✅
│   └── TaskContext (任务上下文) 🔄
│       ├── VariableManager (变量管理器) 🔄
│       ├── ArtifactManager (产物管理器) ✅
│       └── ExecutionHistory (执行历史) 🔄
└── AutoGenExecutor (AutoGen执行器) 🔄
    └── 连接AutoGen代理和权限管理 🔄
```

图例说明：
- ✅ 已实现功能
- 🔄 待实现功能
- 无标识：基础框架已搭建，需完善

### 1.2 核心接口定义

```python
class ITaskExecutor:
    async def execute_task(self, task_definition: dict) -> dict
    async def execute_subtask(self, subtask: dict) -> dict
    
class IContextManager:
    def create_context(self, task_id: str)
    def get_context(self, task_id: str) -> TaskContext
    def update_context(self, task_id: str, data: dict)
```

### 1.3 变量管理实现

```python
class VariableManager:
    def __init__(self, execution_history: ExecutionHistory):
        self.scopes = {
            "global": {},
            "current": None  # 当前作用域指针
        }
        self.history = execution_history
        
    def set_variable(self, name: str, value: Any, scope: str = "task") -> None:
        """设置变量值并记录变更历史"""
        scope_store = self._get_scope_store(scope)
        old_value = scope_store.get(name)
        scope_store[name] = value
        self.history.log_variable_change(name, old_value, value, scope)
        
    def get_variable(self, name: str, scope: str = None) -> Any:
        """支持作用域链查询：局部 > 任务 > 全局"""
        scopes = [scope] if scope else ["local", "task", "global"]
        for s in scopes:
            if value := self._get_scope_store(s).get(name):
                return value
        raise VariableNotFoundError(name)
    
    def create_scope(self, scope_type: str) -> str:
        """创建隔离的作用域（用于并行任务）"""
        scope_id = f"{scope_type}_{uuid.uuid4().hex[:6]}"
        self.scopes[scope_id] = {}
        return scope_id

    def _get_scope_store(self, scope: str) -> dict:
        """获取指定作用域的存储字典"""
        if scope == "local" and self.scopes["current"]:
            return self.scopes[self.scopes["current"]]
        return self.scopes.get(scope, {})
```

#### 实现特性：
1. **作用域链查询**：自动按 local > task > global 顺序查找变量
2. **变更追踪**：与 ExecutionHistory 集成记录变量修改历史
3. **并行隔离**：通过 create_scope 为并行任务创建独立作用域
4. **类型安全**：通过 VariableType 定义实现类型校验

## 2. 实现规划与优先级

根据组件层次结构实现优先级如下：

### 2.1 TaskPlanner实现（总体规划）
- **组件整合** 🔄
  - 整合TaskExecutor与AutoGenExecutor
  - 实现组件间通信机制
  - 提供统一的任务规划调度接口

### 2.2 TaskExecutor实现（阶段1）
- **任务执行管理** ✅
  - 解析任务定义
  - 执行任务流程控制
  - 处理执行状态和结果

- **任务上下文管理** 🔄
  - 创建和维护任务上下文
  - 管理上下文生命周期
  - 提供上下文访问接口

### 2.3 TaskContext实现（阶段1）
- **VariableManager** 🔄
  - 实现变量作用域管理
  - 提供变量读写和查询接口
  - 支持变量类型检查和验证

- **ArtifactManager** ✅
  - 管理任务产出物
  - 支持产物的存储和检索
  - 维护产物元数据

- **ExecutionHistory** 🔄
  - 记录任务执行历史
  - 提供执行回溯能力
  - 生成执行统计和报告

### 2.4 AutoGenExecutor实现（阶段2）
- **AutoGen集成** 🔄
  - 创建和配置AutoGen代理
  - 管理代理生命周期
  - 处理代理间通信

- **权限管理** 🔄
  - 通过human input实现权限确认
  - 实现上下文感知的权限判断
  - 记录权限决策和审计日志

## 3. 功能集成方案

### 3.1 AutoGen集成方案

```python
class AutoGenExecutor:
    """AutoGen执行器 - 集成AutoGen代理和权限管理"""
    
    def __init__(self):
        """初始化执行器"""
        self.registered_tools = {}
    
    def register_tools(self, agent, tools, agent_type="llm"):
        """将工具注册到AutoGen代理
        
        Args:
            agent: AutoGen代理实例
            tools: 要注册的工具列表
            agent_type: "llm"或"execution"
        """
        # 注册每个工具
        for tool in tools:
            self._register_tool(agent, tool, agent_type)
    
    def _register_tool(self, agent, tool, agent_type):
        """注册单个工具的所有方法"""
        # 获取工具的公共方法
        methods = [m for m in dir(tool) if callable(getattr(tool, m)) 
                  and not m.startswith('_')]
        
        # 注册每个方法
        for method_name in methods:
            tool_name = tool.__class__.__name__
            full_name = f"{tool_name}_{method_name}"
            method = getattr(tool, method_name)
            
            # 获取方法文档作为描述
            description = method.__doc__ or f"{method_name} of {tool_name}"
            
            # 根据代理类型注册
            if agent_type == "llm":
                agent.register_for_llm(
                    name=full_name,
                    description=description
                )(method)
            else:
                agent.register_for_execution()(method)
            
            self.registered_tools[full_name] = method
```

### 3.2 基于Agent的权限确认

```python
class PermissionAgent:
    """权限确认Agent"""
    async def verify_tool_call(self, tool_name: str, params: dict, task_description: str) -> bool:
        """验证工具调用权限"""
        context = self._build_verification_context(tool_name, params, task_description)
        return await self._make_verification_decision(context)
        
    def _build_verification_context(self, tool_name: str, params: dict, task_description: str) -> dict:
        """构建验证上下文"""
        return {
            "tool_name": tool_name,
            "params": self._sanitize_params(params),
            "task_description": task_description,
            "timestamp": datetime.now(),
            "previous_calls": self.get_recent_calls()
        }
    
    async def request_human_confirmation(self, tool_call: dict) -> bool:
        """请求人工确认权限"""
        # 通过agent在human input阶段显示工具调用信息并获取确认
        confirmation = await self._get_human_input(
            f"请确认以下工具调用权限:\n"
            f"工具: {tool_call['tool_name']}\n"
            f"参数: {tool_call['params']}\n"
            f"请回复 'yes' 确认或 'no' 拒绝"
        )
        return confirmation.lower() == "yes"
```

## 4. 配置示例

### 4.1 AutoGen集成配置示例

```yaml
autogen:
  agents:
    assistant:
      name: "开发助手"
      model: "claude-3-5-sonnet-20240620"
      system_message: |
        您是全栈开发专家，请严格遵循：
        1. 使用工具前验证权限
        2. 修改前先读取文件
        3. 完成后发送TERMINATE
      temperature: 0
      
    user_proxy:
      name: "user_proxy"
      human_input_mode: "TERMINATE"
      max_consecutive_auto_reply: 10
      system_message: "严格遵循工作流步骤执行操作，完成当前步骤后必须发送TERMINATE"
```

### 4.2 任务定义示例

```yaml
task:
  id: "code_analysis_task"
  name: "代码分析任务"
  steps:
    - id: "read_code"
      action: "read"
      params:
        path: "src/main.py"
        
    - id: "analyze_code"
      action: "analyze"
      params:
        code: "$result.read_code.content"
        
    - id: "generate_report"
      action: "write"
      params:
        path: "reports/analysis.json"
        content: "$result.analyze_code.result"
```

## 5. 注意事项

1. **兼容性考虑**
   - 保持与现有Task Planner API的兼容
   - 支持渐进式迁移
   - 提供向后兼容的配置格式

2. **性能优化**
   - 实现工具调用的缓存机制
   - 优化并行执行性能
   - 减少不必要的上下文切换

3. **基于Agent的安全机制**
   - 实现上下文感知的权限确认流程
   - 提供人工确认与自动确认混合模式
   - 允许根据任务描述智能判断操作合法性
   - 建立完整的权限决策审计日志
   - 支持敏感操作的多级确认机制
   - 通过agent在human input阶段实现权限确认

4. **可扩展性**
   - 设计插件化架构
   - 提供标准化的工具接口
   - 支持自定义工具集成