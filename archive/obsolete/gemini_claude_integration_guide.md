# Gemini 控制 Claude CLI 集成测试指南

本文档提供了使用 Gemini 2.0 Flash API 实际控制 Claude CLI 进行交互的完整测试流程。

## 介绍

这个集成测试演示了一个真实场景：**让一个大语言模型(Gemini)自动控制另一个大语言模型(Claude)的命令行界面**。这是一个高级自动化示例，展示了如何通过API在不同LLM系统之间建立桥接。

测试过程将记录和可视化整个交互过程，包括：
1. Claude的输出
2. Gemini的决策
3. Claude对Gemini输入的响应

## 测试环境准备

### 前提条件

1. **Gemini API密钥**:
   ```bash
   export GEMINI_API_KEY="your_api_key_here"
   ```

2. **安装依赖**:
   ```bash
   pip install requests rich pexpect
   ```

3. **Claude CLI**:
   确保已安装官方Claude命令行工具，并且正常工作。

### 测试脚本

测试脚本位于`tests/gemini_claude_integration_test.py`，它包含完整的集成测试代码。

## 运行测试

### 基本用法

```bash
cd /path/to/code_rag
python tests/gemini_claude_integration_test.py
```

默认情况下，测试会使用预设的提示："帮我写一个Python函数，用递归和动态规划两种方式实现斐波那契数列计算，并比较它们的性能差异"

### 自定义提示

你可以提供自己的提示作为命令行参数：

```bash
python tests/gemini_claude_integration_test.py "解释量子计算的基本原理，并给出一个简单的量子算法示例"
```

## 测试流程

测试的执行流程如下：

1. **初始化**: 
   - 创建Gemini API桥接
   - 创建Claude桥接
   - 准备实时显示界面

2. **启动Claude**:
   - 使用pexpect启动Claude CLI进程
   - 等待Claude启动完成

3. **发送初始提示**:
   - 将用户提供的提示发送给Claude

4. **主交互循环**:
   - Claude生成回复
   - 分析Claude的输出类型(提示、确认、继续等)
   - Gemini分析Claude输出并生成决策
   - 将Gemini的决策发送给Claude
   - 重复这个过程，直到达到最大交互次数或用户中断

5. **结束和统计**:
   - 关闭Claude进程
   - 保存完整交互记录
   - 显示统计信息(交互次数、总耗时、平均决策时间等)

## 实时界面

测试运行时会显示一个实时更新的表格，包含以下信息：

- **时间**: 每条消息的时间戳
- **角色**: USER/CLAUDE/GEMINI/事件
- **内容**: 消息内容或事件描述
- **输出类型**: (仅适用于Claude输出)显示检测到的输出类型

## 交互记录

测试完成后，完整的交互记录将保存为JSON文件：`tests/gemini_claude_interaction_{timestamp}.json`

这个记录包含：
- 所有Claude的输出及其类型
- 所有Gemini的决策及其响应时间
- 事件记录(启动、错误、会话结束等)
- 统计数据(总耗时、交互次数等)

## 分析测试结果

通过分析交互记录，你可以评估：

1. **Gemini决策质量**: Gemini是否能正确理解Claude的输出并做出合适决策
2. **响应时间**: Gemini生成决策的平均时间
3. **交互效率**: 整个系统的端到端交互效率
4. **系统稳定性**: 是否有错误或意外行为

## 常见问题

### Claude启动失败

确保Claude CLI已正确安装并可以直接在命令行运行。可能需要先手动运行`claude`命令进行身份验证。

### Gemini API错误

检查API密钥是否正确设置，以及是否有足够的API调用配额。

### 交互卡住

默认设置的超时时间为30秒。如果交互似乎卡住，可能是因为Claude生成较长回复需要更多时间，或网络延迟导致API调用较慢。

### Gemini生成代码或完整答案

如果发现Gemini直接生成代码或完整答案，而不是只控制Claude命令行界面，这是系统提示设置的问题。请检查`gemini_bridge_test.py`文件中的`system_prompt`部分，确保已明确限制Gemini只能发送控制命令，而不能生成任务解决方案。

正确的设计是Gemini只负责界面控制（确认、回车、方向键等），让Claude负责实际任务的解决，而不是Gemini直接提供答案。

## 结论

这个集成测试展示了一个强大的自动化场景：使用一个LLM(Gemini)完全控制另一个LLM(Claude)的命令行界面。这种技术可用于：

1. 自动化测试LLM工具
2. 创建LLM代理系统
3. 构建更复杂的多LLM交互系统
4. 自动化数据收集和评估

从测试结果可以看出，Gemini能够很好地理解Claude的各种输出类型，并提供合适的响应，创建了一个流畅的自动化体验。