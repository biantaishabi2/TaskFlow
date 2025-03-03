# Claude 命令行与大模型交互系统

## 1. 项目概述

本项目实现了一个自动化系统，让大型语言模型（LLM）能够控制 Claude 命令行工具进行交互，特别是处理需要用户确认和输入的场景。系统采用事件驱动设计，只在 Claude 需要用户输入时才调用大模型，提高效率和稳定性。

## 2. 关键特性

- **事件驱动**: 只在 Claude 等待输入时调用大模型
- **多种输入识别**: 自动检测确认请求、输入框、按键继续等多种交互类型
- **无超时机制**: 让 Claude 自然完成处理，无人为超时打断
- **历史记录**: 保存完整交互历史，便于分析和审计
- **错误恢复**: 提供基本的错误处理和进程管理功能

## 3. 系统组件

### 3.1 核心组件

1. **ClaudeBridge**: 管理与 Claude 命令行工具的交互
   - 负责启动、监控和关闭 Claude 进程
   - 识别 Claude 的各种交互状态
   - 发送命令和接收响应

2. **LLMBridge**: 与大模型交互
   - 分析 Claude 输出并决定如何回应
   - 维护对话上下文
   - 提供模拟或真实的 API 调用功能

### 3.2. 工作流程

```
用户提示 → Claude处理 → 检测需要输入 → 调用大模型 → 发送回应 → Claude继续处理 → ...
```

## 4. 技术实现

### 4.1 Claude 命令行交互 

使用 `pexpect` 库处理终端交互:

```python
# 创建 Claude 进程
child = pexpect.spawn('claude', encoding='utf-8')

# 等待输入请求
index = child.expect([
    r'╭─+╮.*>.*╰─+╯',  # 输入提示框
    r'\[y/n\]',         # 确认请求
    r'Press Enter to continue'  # 按键继续
], timeout=None)  # 无超时，一直等待

# 发送响应
child.sendline(response)
```

### 4.2 输入请求检测

通过模式匹配识别 Claude 需要输入的情况:

```python
wait_patterns = [
    r'╭─+╮.*>.*╰─+╯',  # 输入提示框
    r'\[y/n\]',         # 确认请求
    r'Press Enter to continue',  # 按键继续
    r'请按.*继续',        # 中文按键继续
    r'请输入',           # 中文输入提示
    r'Enter.*:',        # 英文输入提示
]
```

### 4.3 大模型决策

根据 Claude 输出决定如何回应:

```python
system_prompt = """
你是Claude命令行工具的智能助手。你需要分析Claude命令行的输出并做出决策。
当Claude在等待用户输入时，你需要决定应该输入什么。

1. 如果Claude在提问或需要确认(如[y/n])，通常回答"y"确认继续
2. 如果Claude要求按回车继续，提供一个空行
3. 如果Claude请求特定信息，根据上下文提供相关信息
4. 如果Claude显示错误，分析是否需要重试或提供不同输入

只返回你决定的输入内容，不要有任何解释或额外文本。
"""

# 调用大模型API获取决策
decision = call_llm_api(system_prompt, claude_output)
```

## 5. 使用指南

### 5.1 安装依赖

```bash
pip install pexpect
```

### 5.2 配置

1. 确保 Claude 命令行工具已安装并可访问
2. 如需使用真实大模型 API，更新 `LLMBridge` 类中的 API 配置

### 5.3 运行

基本用法:

```bash
python claude_llm_bridge_simple.py "请编写一个Python函数计算斐波那契数列"
```

带调试信息:

```bash
python claude_llm_bridge_simple.py --debug "请帮我优化这段代码"
```

保存交互记录:

```bash
python claude_llm_bridge_simple.py --output interaction.json "分析这个数据集"
```

## 6. 验证结果与改进方向

### 6.1 已验证行为

- ✅ Claude 命令行界面使用 Unicode 框线和 ANSI 控制序列
- ✅ 可通过模式匹配识别输入提示框和确认请求
- ✅ pexpect 能够成功与 Claude 交互并发送特殊键
- ✅ 事件驱动模式能有效减少不必要的 API 调用

### 6.2 改进方向

1. **输入识别增强**
   - 添加更多模式来识别各种输入请求
   - 使用机器学习方法改进识别准确性

2. **ANSI 处理**
   - 使用专门的库处理复杂的 ANSI 控制序列
   - 保留格式信息以便更好地分析

3. **大模型决策优化**
   - 提供更丰富的上下文
   - 支持特定领域的决策策略

4. **交互记录与分析**
   - 提供更详细的交互统计
   - 实现会话可视化

## 7. 实现版本

我们提供了两个主要实现版本：

### 7.1 基础版 (`claude_llm_bridge_simple.py`)

- 使用基本的正则表达式处理ANSI输出
- 简单的事件驱动设计
- 无超时限制，让Claude自然处理
- 适合快速集成的场景

### 7.2 增强版 (`claude_llm_bridge_rich.py`)

- 使用`rich`库处理ANSI转义序列
- 更精确的输出类型识别（基于文本样式和颜色）
- 美化的终端显示（彩色输出、面板、Markdown渲染）
- 更丰富的交互记录和统计功能
- 添加了会话事件记录（启动、结束、错误等）

关键改进示例:

```python
# 使用rich解析ANSI输出
text = Text.from_ansi(ansi_output)
            
# 获取纯文本内容
plain_text = text.plain
            
# 分析格式信息查找特定模式
styled_ranges = list(text.get_style_ranges())
            
# 检查是否有错误（通常是红色文本）
has_error = any(style and getattr(style, 'color', None) == "red" 
               for _, style, _ in styled_ranges)
```

## 8. 总结

通过 pexpect 与大模型的结合，我们成功实现了自动化控制 Claude 命令行工具的能力。事件驱动设计确保系统只在需要时调用大模型，使整个交互过程更加自然和高效。

增强版使用 rich 库处理 ANSI 控制序列，不仅能清除控制字符，还能解析其含义，实现更精确的交互状态检测和更友好的用户界面，适合长期使用和定制化场景。

这个系统可以显著减少用户在使用交互式命令行工具时的手动介入，让大模型代替人工处理各种确认和输入请求。