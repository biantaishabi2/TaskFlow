# Claude CLI 异步交互设计方案

## 背景

当前的 `claude_cli.py` 只支持单次指令和响应，无法处理交互式命令行工具需要的多轮对话和用户确认。为了让大模型能够与 Claude 命令行工具进行有效交互，需要设计一个异步交互系统。

## 设计目标

1. 实现大模型与 Claude 命令行工具的异步交互
2. 自动识别 Claude 何时需要用户确认或输入
3. 在需要确认时将 Claude 输出传递给大模型处理
4. 接收大模型的决策并发送回 Claude
5. 支持长时间运行的任务而不阻塞

## 实现观察

通过对 Claude 命令行工具的测试，我们发现：

1. Claude CLI 默认是交互式的，可接收多轮对话
2. 使用 `-p/--print` 选项可获得非交互式输出（单次响应后退出）
3. Claude 交互过程中有多种需要用户确认的模式，如 `[y/n]` 提示
4. Claude 支持各种 slash 命令，如 `/exit`、`/clear`、`/compact` 等
5. 长时间运行的任务可能需要用户提供额外输入或确认

## 技术方案

### 1. 进程管理

可以使用两种方式实现：

```python
# 方式一：标准库 subprocess + 线程
def create_claude_process():
    process = subprocess.Popen(
        ['claude'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1  # 行缓冲
    )
    return process

# 方式二：异步 asyncio
async def create_claude_process():
    process = await asyncio.create_subprocess_exec(
        'claude',
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    return process
```

### 2. 输出解析器

基于测试发现，需要识别以下模式：

```python
def parse_claude_output(output):
    # 检测需要用户确认的模式
    confirmation_patterns = [
        r'Do you want to proceed\?',
        r'Shall I continue\?',
        r'\[y/n\]',
        r'Press Enter to continue',
        r'确认.*\?',
        r'您想要.*吗\?'
    ]
    
    # 检测命令完成的模式
    completion_patterns = [
        r'执行完成',
        r'任务已完成',
        r'Done',
        r'Completed'
    ]
    
    # 检测错误模式
    error_patterns = [
        r'Error:',
        r'错误:',
        r'Failed to',
        r'无法.*'
    ]
    
    for pattern in confirmation_patterns:
        if re.search(pattern, output):
            return {"state": "needs_confirmation", "message": output}
    
    for pattern in completion_patterns:
        if re.search(pattern, output):
            return {"state": "completed", "message": output}
            
    for pattern in error_patterns:
        if re.search(pattern, output):
            return {"state": "error", "message": output}
    
    return {"state": "waiting", "message": output}
```

### 3. 状态机

实现更完整的状态机：

```python
class ClaudeInteractionState(Enum):
    INITIALIZED = 0
    WAITING_FOR_CLAUDE = 1
    PROCESSING_OUTPUT = 2
    NEEDS_CONFIRMATION = 3
    WAITING_FOR_MODEL = 4
    SENDING_TO_CLAUDE = 5
    COMPLETED = 6
    ERROR = 7
```

### 4. 主交互循环

使用线程的同步版本：

```python
def interact_with_claude(initial_prompt, model_api):
    process = create_claude_process()
    state = ClaudeInteractionState.SENDING_TO_CLAUDE
    
    # 发送初始提示
    process.stdin.write(f"{initial_prompt}\n")
    process.stdin.flush()
    
    buffer = ""
    output_collector = []
    
    def read_output():
        nonlocal buffer, state
        while True:
            if process.poll() is not None:  # 进程已结束
                return
                
            output = process.stdout.readline()
            if not output:
                time.sleep(0.1)
                continue
                
            # 处理输出
            buffer += output
            output_collector.append(output.strip())
            print(f"Claude: {output.strip()}")
            
            # 检查是否需要确认
            result = parse_claude_output(output)
            if result["state"] == "needs_confirmation":
                state = ClaudeInteractionState.NEEDS_CONFIRMATION
                # 通知主线程处理确认
                confirmation_event.set()
            elif result["state"] == "completed":
                state = ClaudeInteractionState.COMPLETED
                completion_event.set()
            elif result["state"] == "error":
                state = ClaudeInteractionState.ERROR
                error_event.set()
    
    # 创建并启动读取线程
    confirmation_event = threading.Event()
    completion_event = threading.Event()
    error_event = threading.Event()
    
    output_thread = threading.Thread(target=read_output)
    output_thread.daemon = True
    output_thread.start()
    
    try:
        while True:
            # 等待事件发生
            if confirmation_event.wait(timeout=0.5):
                confirmation_event.clear()
                # 调用大模型做决策
                current_context = "\n".join(output_collector[-10:])  # 提供最近10行上下文
                decision = model_api.get_decision(current_context)
                
                # 将决策发送回Claude
                process.stdin.write(f"{decision}\n")
                process.stdin.flush()
                
                # 清空一部分缓冲区，保留一些历史
                output_collector = output_collector[-20:]
                
            elif completion_event.wait(timeout=0.1):
                completion_event.clear()
                # 任务完成，返回结果
                return {
                    "status": "completed",
                    "output": "\n".join(output_collector),
                    "final_state": buffer
                }
                
            elif error_event.wait(timeout=0.1):
                error_event.clear()
                # 发生错误
                return {
                    "status": "error",
                    "output": "\n".join(output_collector),
                    "final_state": buffer
                }
                
            # 检查进程是否仍在运行
            if process.poll() is not None:
                break
                
    finally:
        # 确保进程正确关闭
        if process.poll() is None:
            try:
                process.stdin.write("/exit\n")
                process.stdin.flush()
                process.wait(timeout=2)
            except:
                process.terminate()
```

### 5. 大模型决策接口

更完善的决策系统：

```python
def get_model_decision(context):
    """
    根据Claude输出上下文，让大模型决定如何回应
    
    参数:
        context: Claude的输出上下文
        
    返回:
        决策结果: 如 "y", "n", "继续", 或其他用户输入
    """
    # 构建提示
    prompt = f"""
你是Claude命令行工具的智能助手。你需要分析以下Claude命令行的输出，并决定如何回应。
输出内容：
---
{context}
---

请分析Claude当前是否在等待用户输入，如果是，应该回复什么？
如果检测到:
1. 需要确认的问题(如 [y/n])，通常回复 "y"
2. 需要按Enter继续，回复一个空行
3. 需要用户输入信息，根据上下文分析应提供什么信息
4. 如果检测到错误提示，分析是否需要重试或提供不同参数

只回复你决定输入的内容，不要有任何其他解释。
"""

    # 调用大模型API
    response = call_llm_api(prompt)
    
    # 处理响应
    # 如果模型可能会生成解释,需要提取实际决策部分
    decision = response.strip()
    
    # 如果决策太长,可能不是有效的命令行输入
    if len(decision) > 100:
        # 尝试提取第一行或关键部分
        first_line = decision.split('\n')[0].strip()
        if first_line:
            decision = first_line
        else:
            # 默认确认
            decision = "y"
    
    return decision
```

## 实现考虑

1. **输出流处理**：Claude的输出可能不是按行完整返回的，需要缓冲处理
2. **特殊命令处理**：支持Claude的slash命令，如`/exit`、`/clear`等
3. **会话管理**：保持上下文并提供给大模型，使其能做出更好的决策
4. **超时与心跳**：处理长时间无响应的情况，增加心跳检测
5. **无阻塞UI**：提供状态更新回调，便于集成到UI中
6. **资源与异常处理**：完善的错误处理和资源清理机制

## 实际演示案例

我们创建了初步测试文件 `claude_cli_test.py` 验证基本交互流程：

1. 启动非交互模式的Claude进程
2. 通过线程监控输出并识别需要确认的模式
3. 模拟大模型决策并发送回Claude
4. 支持多轮持续对话

测试结果表明这种方法基本可行，但需要进一步完善输出解析和状态管理。

## 流程图

```
初始提示 -> Claude进程 -> 输出流处理 -> 状态识别 ----> 等待更多输出
                                       |
                                       ├─ 需要确认 -> 大模型决策 -> 发送回Claude
                                       |
                                       ├─ 任务完成 -> 返回结果
                                       |
                                       └─ 出错 -> 错误处理
```

## 待解决问题

在测试过程中，我们发现了以下关键问题需要解决：

1. **输入需求检测**：
   - 当前通过文本模式匹配来检测Claude何时需要用户输入
   - 这种方法不够健壮，可能错过某些交互提示
   - Claude可能使用各种不同形式请求输入，难以全部覆盖

2. **特殊键输入处理**：
   - 当前实现只支持普通文本输入和回车键
   - 无法处理方向键、Tab键、Ctrl组合键等特殊输入
   - 无法处理命令行编辑和历史导航功能

3. **伪终端需求**：
   - Claude命令行工具可能需要完整的伪终端(PTY)环境
   - 当前实现使用简单的管道，可能不足以支持复杂的终端交互
   - 控制序列和ANSI转义码的处理不完善

4. **输出解析挑战**：
   - Claude输出可能包含格式化文本、颜色和其他控制序列
   - 区分实际内容和控制序列很困难
   - 输出可能不是按完整行返回的

5. **超时与交互时机**：
   - 难以确定Claude何时完成了一轮输出、等待输入
   - 固定超时不适用于不同复杂度的任务
   - 需要更智能的活动检测机制

## 可能的解决方案

1. **使用专业工具**：
   - 考虑使用`pexpect`库替代基本的`subprocess`
   - `pexpect`专门设计用于自动化交互式命令行程序
   - 提供了模式匹配、超时控制和特殊键发送功能

2. **伪终端实现**：
   - 使用`pty`模块创建完整的伪终端环境
   - 处理终端大小、控制序列和特殊字符输入

3. **更复杂的状态检测**：
   - 结合多种技术检测交互状态：文本模式、超时、控制序列
   - 使用机器学习方法训练识别Claude的交互模式
   - 实现自适应等待策略

4. **用户界面考虑**：
   - 清晰区分Claude输出和系统消息
   - 提供取消和干预机制
   - 支持调试模式查看实际交互过程

## 后续优化

1. 增强模式识别能力，处理各种确认请求
2. 智能缓冲区管理，避免上下文过长
3. 增加异步API版本，支持现代Python应用
4. 支持中断和超时控制，优化资源使用
5. 增加会话历史记录，分析Claude的应答特点
6. 引入大模型确认策略的训练和完善
7. 添加完整的伪终端支持，处理特殊键输入
8. 改进输出解析，识别不同类型的Claude提示
9. 实现自适应等待策略，避免固定超时问题