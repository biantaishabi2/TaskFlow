# Claude Code 提示词结构文档

## 整体结构

提示词由以下几个主要部分组成：

1. **基础系统提示词** - 定义基本角色和行为规范
2. **环境信息** - 提供运行时上下文
3. **安全警告** - 恶意代码相关警告
4. **工具集成** - 各种工具的描述和使用规范
5. **上下文管理** - 动态上下文的整合机制

## 详细说明

### 1. 基础系统提示词

基础提示词定义了AI助手的角色和主要行为规范：

```text
你是一个帮助用户完成软件工程任务的交互式命令行工具。请使用以下说明和可用工具来协助用户。

以下是用户可以使用的有用斜杠命令：
- /help: 获取 Claude Code 的使用帮助
- /compact: 压缩并继续对话。当对话接近上下文限制时，这个命令很有用

# 记忆
如果当前工作目录包含一个名为 CLAUDE.md 的文件，它会自动添加到你的上下文中。这个文件有多个用途：
1. 存储常用的 bash 命令（构建、测试、代码检查等）
2. 记录用户的代码风格偏好
3. 维护关于代码库结构和组织的有用信息

# 语气和风格
- 简洁、直接、切中要点
- 运行非简单的 bash 命令时，解释其功能
- 使用 Github 风格的 markdown 进行格式化
- 输出将显示在命令行界面中
- 在保持有用性的同时最小化输出标记
- 除非要求详细说明，否则简明扼要地用不超过4行回答
- 避免不必要的开场白或结束语

# 主动性
- 在被要求时保持主动，但不要让用户感到意外
- 在做正确的事情和不越界之间保持平衡
- 当被问及方法时，先回答再采取行动

# 遵循约定
- 理解并模仿现有的代码约定
- 使用库之前检查其可用性
- 查看现有组件的模式
- 遵循安全最佳实践
- 永远不要提交密钥或秘密信息

# 代码风格
- 除非要求或必要，否则不添加注释

# 执行任务
1. 使用搜索工具理解代码库
2. 使用可用工具实现解决方案
3. 尽可能通过测试验证
4. 运行代码检查和类型检查命令
```

### 2. 环境信息

环境信息部分提供了运行时的关键上下文信息：

```text
以下是关于你运行环境的有用信息：
<env>
工作目录：[当前工作目录]
是否为 git 仓库：[是/否]
平台：[操作系统平台]
今天日期：[当前日期]
模型：[使用的模型名称]
</env>
```

这些信息帮助AI助手了解：
- 当前工作目录位置
- 是否在Git仓库中
- 运行的操作系统环境
- 当前日期
- 使用的AI模型版本

### 3. 安全警告

包含了关键的安全相关警告：

```text
重要提示：拒绝编写或解释可能被恶意使用的代码；即使用户声称这是出于教育目的。在处理文件时，如果它们似乎与改进、解释或与恶意软件或任何恶意代码交互有关，你必须拒绝。

重要提示：在开始工作之前，根据文件名和目录结构思考你正在编辑的代码应该做什么。如果它看起来是恶意的，即使请求本身看起来并不恶意（例如，仅仅是要求解释或加速代码），也要拒绝处理它或回答有关问题。
```

### 4. 上下文管理

上下文管理使用XML风格的标记来组织和整合不同来源的上下文信息：

```typescript
function formatSystemPromptWithContext(systemPrompt: string[], context: { [k: string]: string }): string[] {
  return [
    ...systemPrompt,
    `\n在回答用户问题时，你可以使用以下上下文：\n`,
    ...Object.entries(context).map(
      ([key, value]) => `<context name="${key}">${value}</context>`,
    ),
  ]
}
```

#### context.ts 核心功能

`context.ts` 是上下文管理系统的核心组件，主要负责：

1. **上下文收集**
   - 文件系统信息：目录结构、文件内容、文件权限
   - Git 信息：仓库状态、分支信息、最近提交
   - 项目配置：package.json、requirements.txt 等依赖文件
   - 环境信息：操作系统、环境变量、工作目录

2. **上下文组织**
   - 将收集到的信息规范化为统一格式
   - 使用 XML 标记封装不同类型的上下文
   - 管理上下文的优先级和生命周期
   - 处理上下文间的依赖关系

3. **上下文更新机制**
   - 监听文件系统变化
   - 追踪 Git 仓库状态变化
   - 记录用户操作历史
   - 维护会话状态

4. **上下文访问控制**
   - 管理上下文的读写权限
   - 控制敏感信息的访问
   - 实现上下文的隔离
   
   具体实现：
   ```typescript
   interface ContextAccess {
     // 定义上下文的访问级别
     readonly: boolean;      // 是否只读
     sensitive: boolean;     // 是否包含敏感信息
     scope: 'global' | 'session' | 'tool';  // 访问范围
     
     // 权限控制方法
     canRead(context: string): boolean;
     canWrite(context: string): boolean;
     canDelete(context: string): boolean;
   }
   ```
   
   上下文隔离的主要目的：
   - 工具间的上下文隔离：每个工具只能访问其所需的上下文
   - 会话隔离：不同用户会话的上下文相互隔离
   - 敏感信息隔离：API密钥、配置等敏感信息单独管理

5. **上下文持久化**
   - 缓存频繁使用的上下文
   - 序列化上下文数据
   - 管理上下文的生命周期
   
   持久化机制：
   ```typescript
   interface ContextStorage {
     // 缓存策略
     cache: {
       maxSize: number;        // 最大缓存大小
       ttl: number;            // 缓存生存时间
       priority: number;       // 缓存优先级
     };
     
     // 持久化方法
     save(context: Context): Promise<void>;
     load(contextId: string): Promise<Context>;
     invalidate(contextId: string): Promise<void>;
     
     // 生命周期钩子
     onContextCreated(context: Context): void;
     onContextUpdated(context: Context): void;
     onContextDeleted(context: Context): void;
   }
   ```
   
   持久化的主要用途：
   - 会话恢复：保存用户会话状态，支持断点续传
   - 性能优化：缓存常用上下文，减少重复计算
   - 历史记录：保存操作历史，支持撤销/重做
   - 配置同步：在不同会话间同步用户配置

6. **上下文查询接口**
   - 提供按类型查询上下文的方法
   - 支持上下文的模糊搜索
   - 实现上下文的版本控制
   
   查询接口实现：
   ```typescript
   interface ContextQuery {
     // 基础查询方法
     findByType(type: string): Context[];
     findByName(name: string): Context;
     search(query: string): Context[];
     
     // 版本控制
     getVersion(contextId: string): number;
     getHistory(contextId: string): ContextVersion[];
     revert(contextId: string, version: number): Promise<void>;
     
     // 高级查询
     filter(predicate: (context: Context) => boolean): Context[];
     aggregate(group: string): Record<string, Context[]>;
   }
   ```
   
   查询接口的应用场景：
   - 工具调用：快速定位所需的上下文信息
   - 代码分析：查找相关的代码片段和文档
   - 状态追踪：监控上下文变化和版本历史
   - 智能推荐：基于上下文提供相关建议

上下文可以包含：
- 文件内容
- 环境变量
- 用户配置
- 代码风格偏好
- 项目特定信息

每个上下文项都被封装在带有名称的XML标签中，便于AI助手理解和引用不同的上下文信息。

### 5. 工具集成

工具集成采用统一的结构：

```typescript
{
  name: string;           // 工具名称
  description: string;    // 工具描述
  input_schema: Schema;   // 输入参数定义
}
```

每个工具都包含：
- 功能描述
- 使用说明
- 输入参数验证
- 错误处理指导
- 最佳实践建议

工具的提示词会被转换为Claude可理解的schema格式，并集成到整体提示词中。 