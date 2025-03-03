# Claude UI模式匹配指南

## Claude UI状态机
### 状态定义
1. INITIAL （初始状态）：
   - 启动后的首个状态。
   - 分支条件：
     - 若是首次运行：等待用户确认信任文件 → 进入 WAIT_CONFIRM
     - 若非首次运行：直接等待输入文字 → 进入 WAIT_INPUT

2. WAIT_CONFIRM （等待确认）：
   - 显示确认提示。
   - 分支条件：
     - 用户发送确认（如回车）→ 触发系统开始工作 → 进入 WORKING

3. WAIT_INPUT （等待输入）：
   - 没有在工作状态也没有等待确认就是等待输入。
   - 分支条件：
     - 用户输入文字并回车 → 触发系统开始工作 → 进入 WORKING

4. WORKING （工作状态）：
   - 系统正在处理，状态行存在（如 ∗ Percolating… (11s · esc to interrupt)）。
   - 退出工作状态：
     - 状态行消失 → 检测后续提示：
       - 若出现确认提示的匹配 → 进入 WAIT_CONFIRM
       - 若无等待确认提示的匹配则进入 WAIT_INPUT


## Claude UI状态示例
### 状态1：初始状态
1.1 首次启动
**描述**：首次启动时，Claude会显示信任文件确认对话框。该界面包含明显的安全提示信息，列出当前工作目录，并提供"Yes, proceed"和"No, exit"两个选项。底部显示"Enter to confirm · Esc to exit"的操作提示。

```
╭───────────────────────────────────────────────────────────────────────────────────────────────────────╮
│                                                                                                       │
│ Do you trust the files in this folder?                                                                │
│                                                                                                       │
│ /home/wangbo/document/pipelines                                                                       │
│                                                                                                       │
│ Claude Code may read files in this folder. Reading untrusted files may lead Claude Code to behave in  │
│ an unexpected ways.                                                                                   │
│                                                                                                       │
│ With your permission Claude Code may execute files in this folder. Executing untrusted code is        │
│ unsafe.                                                                                               │
│                                                                                                       │
│ https://docs.anthropic.com/s/claude-code-security                                                     │
│                                                                                                       │
│ ❯ Yes, proceed                                                                                        │
│   No, exit                                                                                            │
│                                                                                                       │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────╯
   Enter to confirm · Esc to exit
```

1.2 非首次启动：等待输入
**描述**：非首次启动时，Claude直接进入等待输入状态。界面顶部显示欢迎信息和当前工作目录，中间部分为空白区域，底部有输入提示框，显示默认提示文本。底部还有命令模式切换提示。

```
╭────────────────────────────────────────────╮
│ ✻ Welcome to Claude Code research preview! │
│                                            │
│   /help for help                           │
│                                            │
│   cwd: /home/wangbo/document/wangbo/dev    │
╰────────────────────────────────────────────╯

╭───────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ > Try "fix lint errors"                                                                               │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────╯
  ! for bash mode · / for commands · esc to undo                                         \⏎ for newline
```
### 状态2：等待确认
**描述**：等待确认状态与首次启动类似，显示文件操作或命令执行确认对话框。用户需要确认是否信任当前目录下的文件。光标默认位于"Yes, proceed"选项上，等待用户按Enter确认。

```
╭───────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ Edit file                                                                                             │
│ ╭───────────────────────────────────────────────────────────────────────────────────────────────────╮ │
│ │ CONTRIBUTING.md                                                                                   │ │
│ │                                                                                                   │ │
│ │ 47                                                                                                │ │
│ │ 48  ## 🙏 Thank You!                                                                              │ │
│ │ 49                                                                                                │ │
│ │ 50  Your contributions are invaluable to Pipelines' success! We are excited to see what you br    │ │
│ │    ing to the project. Together, we can create a powerful and versatile framework for extendin    │ │
│ │    g OpenAI capabilities. 🌟                                                                      │ │
│ │ 50 \ No newline at end of file                                                                    │ │
│ │ 51  Your contributions are invaluable to Pipelines' success! We are excited to see what you br    │ │
│ │    ing to the project. Together, we can create a powerful and versatile framework for extendin    │ │
│ │    g OpenAI capabilities. 🌟                                                                      │ │
│ │ 52                                                                                                │ │
│ │ 53  你好                                                                                          │ │
│ │ 54 \ No newline at end of file                                                                    │ │
│ ╰───────────────────────────────────────────────────────────────────────────────────────────────────╯ │
│ Do you want to make this edit to CONTRIBUTING.md?                                                     │
│ ❯ Yes                                                                                                 │
│   Yes, and don't ask again this session                                                               │
│   No, and tell Claude what to do differently (esc)                                                    │
│                                                                                                       │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────╯
────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```
也可能是bash 命令执行确认对话框
```
╭───────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ Bash command                                                                                          │
│                                                                                                       │
│   python /home/wangbo/document/pipelines/main.py                                                      │
│   Runs Python script located in specified document pipeline directory                                 │
│                                                                                                       │
│ Do you want to proceed?                                                                               │
│ ❯ Yes                                                                                                 │
│   Yes, and don't ask again for python commands in /home/wangbo/document/pipelines                     │
│   No, and tell Claude what to do differently (esc)                                                    │
│                                                                                                       │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### 状态3：等待输入（输入框上方没有工作状态行，而是这种输出的文字响应）
**描述**：此状态显示Claude已准备好接收新的输入。界面上方是Claude的文字响应或问候，下方是一个空的输入框，底部显示各种命令模式快捷键提示。这个状态表明Claude已完成先前任务，准备接收新指令。请注意这个是否文字输入框上方没有工作状态的进度计时状态行，而是这种输出的文字响应。

```
● Claude Code，Anthropic 的命令行工具助手。我可以帮您完成软件工程任务。您需要什么帮助？

╭───────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ >                                                                                                     │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────╯
  ! for bash mode · / for commands · esc to undo                                         \⏎ for newline

```

### 状态4：工作中（状态栏会显示在输入框上方）
**描述**：工作中状态下，输入框上方会出现明显的状态行，显示当前进行的操作（如"Percolating..."）、已用时间（如"11s"）和中断选项（"esc to interrupt"）。这表明Claude正在处理用户提交的请求，用户可以按Esc键中断处理过程。这个状态行是固定的，中间的词会随机变化，但我们应该关注状态行的通用格式特征，而不是特定词汇。

```
∗ Percolating… (11s · esc to interrupt)
╭───────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ >                                                                                                     │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────╯
  ! for bash mode · / for commands · esc to undo                                         \⏎ for newline

```
注意：状态行的格式是固定的，中间的词会随机变化，但我们应该关注状态行的通用格式特征，而不是特定词汇。


## 响应匹配策略

根据Claude UI的状态机定义，我们可以采用以下匹配策略：

1. **INITIAL状态识别**：
   - 检测是否为首次运行，可通过检查欢迎信息和信任文件确认对话框来判断
   - 首次运行特征：
     - 显示"Do you trust the files in this folder?"确认对话框
     - 包含工作目录路径和安全提示信息
     - 提供"Yes, proceed"和"No, exit"选项
     - 底部显示"Enter to confirm · Esc to exit"操作提示
   - 非首次运行特征：
     - 显示欢迎信息如"✻ Welcome to Claude Code research preview!"
     - 显示当前工作目录信息
     - 底部有输入提示框，显示默认提示文本
     - 欢迎信息框和输入框之间有空行，但是没有别的字符

2. **WAIT_CONFIRM状态识别**：
   - 检测确认对话框的存在，通常包含"Do you want to..."等提示语
   - 特征包括选项列表，默认选中"Yes"或"Yes, proceed"
   - 可能出现在文件编辑确认或命令执行确认场景

3. **WAIT_INPUT状态识别**：
   - 检查输入框存在且上方无工作状态行（这是最重要的特征）
   - 输入框上方可能显示Claude的回复内容，如"● Claude Code，Anthropic 的命令行工具助手。我可以帮您完成软件工程任务。您需要什么帮助？"等文字信息

4. **WORKING状态识别**：
   - 关键特征是状态行的存在，格式为"∗ [动词]... ([时间]s · esc to interrupt)"
   - 动词可能变化，但格式固定

## 正则表达式匹配模式
### 1. INITIAL状态识别
需要区分首次运行和非首次运行：
#### 首次运行特征 - 信任文件确认对话框
首次运行_pattern = r"Do you trust the files in this folder\?.*Yes, proceed.*No, exit.*Enter to confirm · Esc to exit"

#### 非首次运行特征 - 欢迎信息
非首次运行_pattern = r"✻ Welcome to Claude Code research preview!.*cwd:.*\n\n╭─+\n│ >.*\n╰─+\n"

### 2. WORKING状态识别
工作状态的关键特征是状态行的存在：
工作状态_pattern = r"∗ [动词]... ([时间]s · esc to interrupt)"

### 3. WAIT_CONFIRM状态识别
等待确认状态的特征是确认对话框：
确认对话框_pattern = r"Do you want to...*Yes.*Yes, proceed.*No, and tell Claude what to do differently (esc)"

### 4. WAIT_INPUT状态识别
这个状态不需要识别，我们在工作状态结束后匹配不到等待确认的状态，就进入等待输入状态。

## 状态转换逻辑
### 初始状态判断
检查界面是否匹配首次运行模式，如果是，则进入WAIT_CONFIRM
如果匹配非首次运行模式，则进入WAIT_INPUT
### 工作状态识别与转换
当在等待输入状态下用户输入或者等待确认状态下用户回车确认后，进入WORKING状态，这是开始循环检测匹配工作状态栏
当工作状态行消失时，检查是否出现确认对话框：
如果匹配等待确认模式，进入WAIT_CONFIRM
如果没有匹配到等待确认模式，进入WAIT_INPUT
### 等待确认状态转换
用户确认后，系统会再次进入WORKING状态（无需匹配）
### 等待输入状态转换
用户输入并提交后，系统进入WORKING状态（无需匹配）
