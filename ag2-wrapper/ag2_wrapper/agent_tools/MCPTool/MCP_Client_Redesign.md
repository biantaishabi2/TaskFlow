# MCP 客户端重构设计文档

## 当前架构分析

### 主要文件及职责
1. **核心文件**
   - `mcpClient.ts`: 主客户端逻辑，管理服务器连接和功能集成

2. **辅助文件**
   - `config.ts`: 
     * 多作用域配置(项目/全局/mcprc)
     * 类型安全的配置访问  
     * 配置持久化到JSON文件
     * 内存缓存机制

### 核心功能模块
1. **服务器管理**
   - 多作用域配置（项目/全局/mcprc）
   - 增删查改接口

2. **连接管理**
   - 两种传输方式（SSE/Stdio）
   - 连接超时机制
   - 错误处理和日志

3. **功能集成**
   - 工具系统集成
   - 命令系统集成
   - 能力协商机制

### 当前TypeScript实现特点
- 强类型接口
- 基于Promise的异步模型
- 模块化设计
- 客户端缓存机制

## Python重构设计方案

### 1. 文件结构调整建议
```
MCPTool/
├── __init__.py
├── MCPTool.py          # 适配层主类，转换MCP工具为AG2格式
├── client.py           # MCP客户端逻辑
└── config.py           # 配置管理

### 2. 配置管理实现
```python
# 使用Pydantic进行配置建模
class McpServerConfig(BaseModel):
    type: Literal["stdio", "sse"]
    command: Optional[str] = None
    args: Optional[List[str]] = None
    env: Optional[Dict[str, str]] = None
    url: Optional[str] = None  # For SSE

class ProjectConfig(BaseModel):
    mcp_servers: Dict[str, McpServerConfig] = Field(default_factory=dict)

# 配置持久化使用TOML格式替代JSON
def save_config(config: BaseModel, path: Path):
    with open(path, "w") as f:
        toml.dump(config.dict(), f)
```

### 4. 类结构设计

```python
class MCPServer:
    def __init__(self, name: str, config: dict):
        self.name = name
        self.config = config
        self._client: Optional[Client] = None

class MCPClientManager:
    def __init__(self):
        self.servers: Dict[str, MCPServer] = {}
        self._connection_timeout = 5.0  # 可配置
        
    async def connect_all(self) -> List[MCPServer]:
        """连接所有服务器"""
        pass
```

### 2. 关键接口定义

```python
# 配置管理接口
def add_server(name: str, config: dict, scope="project") -> None
def remove_server(name: str, scope="project") -> None
def list_servers() -> Dict[str, dict]

# 连接接口  
async def connect(server: MCPServer) -> Client
async def call_tool(server_name: str, tool_name: str, args: dict) -> dict
```

### 3. Python特有优化

1. **异步处理**：
   - 使用asyncio替代Promise链
   - 支持SSE的异步流式处理

2. **配置管理**：
   - 使用Pydantic进行配置验证
   - 支持.env文件配置

3. **错误处理**：
   - 自定义异常体系
   - 重试机制装饰器

## 迁移路线图

1. **第一阶段**：功能对等实现
   - 保持现有接口不变
   - 实现核心管理类

2. **第二阶段**：Python优化
   - 引入异步IO
   - 添加类型注解
   - 性能优化

3. **第三阶段**：功能扩展
   - 添加gRPC支持
   - 实现热重载
   - 增强监控指标

## 注意事项

1. **差异处理**：
   - Node.js的process.env → Python的os.environ
   - 文件系统操作差异（fs → pathlib）
   - 日志系统替换

2. **测试策略**：
   - 保持接口测试不变
   - 添加Python特有单元测试
   - 集成测试覆盖所有传输方式

3. **性能考量**：
   - 连接池管理
   - 序列化优化
   - GIL处理方案
