# Claude代码客户端
通过命令行与Claude交互的Python工具包

[English](README.md) | 中文

## 概述

ClaudeClient是一个专为简化与Claude命令行工具交互而设计的Python工具包。基于`pexpect`库构建，它可以实现对Claude会话能力的编程访问，无需手动操作命令行界面。

## 版本

该工具包提供多种实现方式：

1. **基础客户端 (ClaudeClient)**: 简单的请求-响应交互
2. **增强客户端 (EnhancedClaudeClient)**: 增加任务完成分析和自动跟进功能
3. **Gemini增强客户端**: 使用Google的Gemini模型判断任务完成状态

## 主要特性

* **自动Claude进程管理:** 处理Claude进程的生命周期
* **状态转换处理:** 管理所有状态转换并确认操作
* **请求/响应管理:** 发送请求并获取响应
* **任务完成分析:** 判断Claude是否已完全完成任务
* **自动跟进:** 持续对话直到任务完成
* **对话历史:** 维护完整的对话记录
* **Gemini集成:** 使用Gemini对响应完整性进行智能分析

## 环境要求

* Python 3.6+
* `pexpect`库
* 已安装Claude命令行工具
* Gemini功能需要：`google-generativeai`包和API密钥

## 快速开始

```python
# 基础用法
from claude_client import ClaudeClient

client = ClaudeClient()
client.start()
response = client.send_request("编写一个Python函数")
print(response)
client.close()

# Gemini增强用法
from enhanced_claude_client import EnhancedClaudeClient
from agent_tools import GeminiTaskAnalyzer

analyzer = GeminiTaskAnalyzer(api_key="YOUR_API_KEY")
client = EnhancedClaudeClient(analyzer=analyzer)
client.start()
response, history = client.send_request("解释Python的特点")
print(response)
client.close()
```

## 示例文件

* `claude_client_example.py`: 基础客户端示例
* `enhanced_claude_example.py`: 增强客户端示例
* `gemini_claude_example.py`: Gemini集成示例

这个工具包提供了一种便捷的方式，将Claude强大的语言处理能力与智能交互处理集成到您的应用程序中。