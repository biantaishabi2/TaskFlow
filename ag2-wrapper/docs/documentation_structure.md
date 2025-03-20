# AG2-Agent 文档结构概述

本文档提供AG2-Agent项目文档的结构概览，帮助开发者和用户快速定位所需信息。

## 文档组织结构

AG2-Agent的文档采用模块化组织，分为以下主要部分：

### 1. 入门与安装 (`/home`, `/installation`)

- **首页与快速入门** (`/home`)
  - `home.mdx` - 项目概述和核心功能介绍
  - `quick-start.mdx` - 快速上手指南，包含基本示例

- **安装指南** (`/installation`)
  - `Installation.mdx` - 详细安装步骤和要求
  - `Optional-Dependencies.mdx` - 可选依赖项说明

### 2. 用户指南 (`/user-guide`)

- **入门指南** (`/getting-started`)
  - `Getting-Started.mdx` - 基础使用教程

- **基础概念** (`/basic-concepts`)
  - `conversable-agent.mdx` - 可交互Agent基础
  - `human-in-the-loop.mdx` - 人机交互模式
  - `installing-ag2.mdx` - 安装细节
  
  - **LLM配置** (`/llm-configuration`)
    - `llm-configuration.mdx` - LLM设置与参数
    - `structured-outputs.mdx` - 结构化输出格式
  
  - **协调模式** (`/orchestration`)
    - `orchestrations.mdx` - 协调模式概述
    - `sequential-chat.mdx` - 顺序对话模式
    - `nested-chat.mdx` - 嵌套对话模式
    - `ending-a-chat.mdx` - 对话终止方法
    - `swarm.mdx` - Swarm协作模式
  
  - **工具使用** (`/tools`)
    - `index.mdx` - 工具总览
    - `basics.mdx` - 基本工具使用
    - `tools-with-secrets.mdx` - 处理敏感信息
    - **互操作性** (`/interop`)
      - `langchain.mdx` - 与LangChain集成
      - `crewai.mdx` - 与CrewAI集成
      - `pydanticai.mdx` - 与PydanticAI集成

- **进阶概念** (`/advanced-concepts`)
  - `code-execution.mdx` - 代码执行功能
  - `conversation-patterns-deep-dive.mdx` - 深入对话模式
  - `llm-configuration-deep-dive.mdx` - LLM高级配置
  - `rag.mdx` - 检索增强生成
  
  - **群聊** (`/groupchat`)
    - `groupchat.mdx` - 群聊基础
    - `custom-group-chat.mdx` - 自定义群聊
    - `resuming-group-chat.mdx` - 恢复群聊会话
    - `tools.mdx` - 群聊中的工具使用
  
  - **实时Agent** (`/realtime-agent`)
    - `index.mdx` - 实时Agent概述
    - `websocket.mdx` - WebSocket实现
    - `webrtc.mdx` - WebRTC实现
    - `twilio.mdx` - Twilio集成
  
  - **Swarm** (`/swarm`)
    - `deep-dive.mdx` - Swarm深入解析
    - `concept-code.mdx` - 概念与代码实现
    - `nested-chat.mdx` - 嵌套对话在Swarm中的应用
    - `use-case.mdx` - 使用场景示例

- **模型支持** (`/models`)
  - 支持各种LLM服务的配置指南：
    - `openai.mdx` - OpenAI模型配置
    - `anthropic.mdx` - Anthropic Claude配置
    - `google-gemini.mdx` - Google Gemini配置
    - `google-vertexai.mdx` - Google VertexAI配置
    - `mistralai.mdx` - Mistral AI配置
    - `cohere.mdx` - Cohere配置
    - `amazon-bedrock.mdx` - AWS Bedrock配置
    - `litellm-proxy-server/*` - LiteLLM代理服务器配置
    - 以及多种其他模型和服务的配置指南

- **参考Agent** (`/reference-agents`)
  - `index.mdx` - 参考Agent总览
  - `reasoningagent.mdx` - 推理Agent
  - `captainagent.mdx` - 指挥Agent
  - `docagent.mdx` - 文档Agent
  - `websurferagent.mdx` - 网页浏览Agent
  - `deepresearchagent.mdx` - 深度研究Agent
  - **通讯平台** (`/communication-platforms`)
    - `overview.mdx` - 通讯平台概述
    - `discordagent.mdx` - Discord集成
    - `slackagent.mdx` - Slack集成
    - `telegramagent.mdx` - Telegram集成

- **参考工具** (`/reference-tools`)
  - `index.mdx` - 工具总览
  - `browser-use.mdx` - 浏览器工具
  - `deep-research.mdx` - 深度研究工具
  - `crawl4ai.mdx` - 网页爬取工具
  - **通讯平台工具** (`/communication-platforms`)
    - `discord.mdx` - Discord工具
    - `slack.mdx` - Slack工具
    - `telegram.mdx` - Telegram工具

### 3. 使用案例 (`/use-cases`)

- **使用场景** (`/use-cases`)
  - `travel-planning.mdx` - 旅行规划案例
  - `game-design.mdx` - 游戏设计案例
  - `customer-service.mdx` - 客户服务案例

- **Jupyter笔记本** (`/notebooks`)
  - `Notebooks.mdx` - Jupyter笔记本示例集

- **社区展示** (`/community-gallery`)
  - `community-gallery.mdx` - 社区项目展示

### 4. 生态系统集成 (`/ecosystem`)

- 与各种外部工具和服务的集成指南：
  - `llamaindex.mdx` - LlamaIndex集成
  - `memgpt.mdx` - MemGPT集成
  - `ollama.mdx` - Ollama集成
  - `pgvector.mdx` - pgvector集成
  - `agentops.mdx` - AgentOps集成
  - `databricks.mdx` - Databricks集成
  - `microsoft-fabric.mdx` - Microsoft Fabric集成
  - `portkey.mdx` - Portkey集成
  - `promptflow.mdx` - PromptFlow集成
  - `composio.mdx` - Composio集成
  - `azure_cosmos_db.mdx` - Azure Cosmos DB集成
  - `mem0.mdx` - Mem0集成

### 5. 贡献者指南 (`/contributor-guide`)

- `contributing.mdx` - 贡献指南
- `documentation.mdx` - 文档编写规范
- `file-bug-report.mdx` - Bug报告流程
- `maintainer.mdx` - 维护者指南
- `pre-commit.mdx` - 预提交钩子配置
- `setup-development-environment.mdx` - 开发环境设置
- `tests.mdx` - 测试指南
- `Research.mdx` - 研究方向
- `Migration-Guide.mdx` - 迁移指南

- **构建指南** (`/building`)
  - `creating-an-agent.mdx` - Agent创建教程
  - `creating-a-tool.mdx` - 工具创建教程

- **AG2工作原理** (`/how-ag2-works`)
  - `overview.mdx` - 系统架构概述
  - `initiate-chat.mdx` - 对话初始化流程
  - `generate-reply.mdx` - 回复生成机制
  - `hooks.mdx` - 钩子系统

### 6. 博客文章 (`/_blogs`)

包含多篇按时间排序的技术文章，涵盖：
- LLM调优
- Agent评估
- 教学型Agent
- 多模态Agent
- AutoGen更新和生态系统
- FSM群聊
- StateFlow
- Reasoning Agent
- 实时通信Agent
- 网页浏览Agent
- 防御机制
- 工具互操作性
等主题

### 7. 用户案例 (`/user-stories`)

- `2025-02-11-NOVA/index.mdx` - NOVA项目案例研究

### 8. 常见问题 (`/faq`)

- `FAQ.mdx` - 常见问题解答

## 文档访问建议

1. **新用户**：从`/home/quick-start.mdx`开始，然后探索`/user-guide/getting-started`
   
2. **寻找具体功能**：
   - Agent相关 → `/user-guide/reference-agents`
   - 工具使用 → `/user-guide/reference-tools`
   - 模型配置 → `/user-guide/models`

3. **开发者与贡献者**：参考`/contributor-guide`的相关文档

4. **高级用例**：查看`/user-guide/advanced-concepts`和`/use-cases`

5. **集成需求**：浏览`/ecosystem`下的相关指南

## 文档更新周期

AG2-Agent文档持续更新，尤其在以下方面：
- 新功能和API变化
- 新的模型支持
- 社区贡献的工具和Agent
- 用例示例

建议定期检查文档更新，特别是在升级AG2-Agent版本后。