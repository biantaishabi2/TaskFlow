# Claude_code_client
A Python Toolkit for Interacting with Claude via Command Line

English | [中文](README_CN.md)

## Overview

ClaudeClient is a Python toolkit designed to simplify interactions with the Claude command-line tool. Built upon the `pexpect` library, it enables programmatic access to Claude's conversational capabilities without requiring manual command-line operations.

## Versions

The toolkit offers multiple implementations:

1. **Basic Client (ClaudeClient)**: Simple request-response interactions
2. **Enhanced Client (EnhancedClaudeClient)**: Adds task completion analysis and auto-follow-up
3. **Gemini-Enhanced Client**: Uses Google's Gemini model to determine task completion

## Key Features

* **Automated Claude Process Management:** Handles the lifecycle of the Claude process
* **State Transition Handling:** Manages all state transitions and confirms actions
* **Request/Response Management:** Sends requests and retrieves responses
* **Task Completion Analysis:** Determines if Claude has fully completed a task
* **Auto-follow-up:** Continues conversations until tasks are completed
* **Conversation History:** Maintains complete dialogue records
* **Gemini Integration:** Uses Gemini for intelligent analysis of response completeness

## Requirements

* Python 3.6+
* `pexpect` library
* Claude command-line tool installed
* For Gemini features: `google-generativeai` package and API key

## Quick Start

```python
# Basic usage
from claude_client import ClaudeClient

client = ClaudeClient()
client.start()
response = client.send_request("Write a Python function")
print(response)
client.close()

# Gemini-enhanced usage
from enhanced_claude_client import EnhancedClaudeClient
from agent_tools import GeminiTaskAnalyzer

analyzer = GeminiTaskAnalyzer(api_key="YOUR_API_KEY")
client = EnhancedClaudeClient(analyzer=analyzer)
client.start()
response, history = client.send_request("Explain Python features")
print(response)
client.close()
```

## Example Files

* `claude_client_example.py`: Basic client examples
* `enhanced_claude_example.py`: Enhanced client examples
* `gemini_claude_example.py`: Gemini integration examples

This toolkit provides a convenient way to integrate Claude's powerful language processing capabilities into your applications with intelligent interaction handling.

