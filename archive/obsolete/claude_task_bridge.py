#!/usr/bin/env python3
"""
Claude命令行任务执行桥接模块
扩展基础Claude桥接，添加任务执行特定功能
"""

import json
import re
import time
from claude_llm_bridge import ClaudeBridge, LLMBridge, ClaudeState

class TaskLLMBridge(LLMBridge):
    """
    扩展LLMBridge，添加任务执行特定功能
    """
    
    def __init__(self, api_key=None, api_url=None, model="gpt-4"):
        """初始化任务LLM桥接"""
        super().__init__(api_key, api_url, model)
        # 添加任务相关上下文
        self.task_context = {}
        
    def with_task_context(self, context):
        """
        设置任务上下文
        
        参数:
            context (dict): 任务上下文
            
        返回:
            self: 支持链式调用
        """
        self.task_context = context
        return self
        
    def get_task_decision(self, claude_output, task_goal, max_tokens=150):
        """
        根据任务目标获取大模型决策
        
        参数:
            claude_output (str): Claude的输出内容
            task_goal (str): 当前任务的目标
            max_tokens (int): 响应的最大令牌数
            
        返回:
            str: 大模型的决策
        """
        # 构建任务感知提示
        system_prompt = f"""
你是任务执行系统的决策者。你需要分析Claude命令行的输出并基于当前任务目标做出决策。
当Claude在等待用户输入时，你需要决定应该输入什么。

当前任务目标: {task_goal}

任务上下文:
- 任务ID: {self.task_context.get('task_id', 'unknown')}
- 任务类型: {self.task_context.get('task_type', 'general')}
- 执行阶段: {self.task_context.get('stage', 'unknown')}

决策指南:
1. 所有决策必须服务于完成当前任务目标
2. 如果Claude在提问或需要确认，基于任务目标做出合适的回应
3. 如果Claude请求特定信息，提供与任务相关的信息
4. 如果看到错误，决定是否需要重试或提供替代输入

只返回你决定的输入内容，不要有任何解释或额外文本。输入应该简短、明确。
"""
        # 调用基础方法获取决策
        self.add_message("system", system_prompt)
        return self.get_decision(claude_output, max_tokens)


class TaskClaudeBridge(ClaudeBridge):
    """
    扩展Claude桥接，添加任务执行特定功能
    """
    
    def __init__(self, llm_bridge=None, debug=False):
        """初始化任务Claude桥接"""
        self.llm_bridge = llm_bridge or TaskLLMBridge()
        super().__init__(self.llm_bridge, debug)
        
    def task_controlled_session(self, initial_prompt, task_context, max_turns=10, timeout=300):
        """
        运行针对特定任务的Claude会话
        
        参数:
            initial_prompt (str): 初始提示
            task_context (dict): 任务上下文
            max_turns (int): 最大交互轮次
            timeout (int): 总超时时间(秒)
            
        返回:
            list: 交互记录
        """
        # 设置任务上下文
        if isinstance(self.llm_bridge, TaskLLMBridge):
            self.llm_bridge.with_task_context(task_context)
            
        # 创建增强版初始提示，包含任务上下文
        enhanced_prompt = self._create_task_enhanced_prompt(initial_prompt, task_context)
        
        # 调用基本的LLM控制会话
        interactions = self.llm_controlled_session(
            enhanced_prompt,
            max_turns=max_turns,
            timeout=timeout
        )
        
        # 解析结果，提取结构化数据和工件
        results = self._parse_task_results(interactions, task_context)
        
        # 添加结果到交互记录中
        interactions.append({
            "role": "system",
            "content": json.dumps(results, ensure_ascii=False, indent=2),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        })
        
        return interactions
    
    def _create_task_enhanced_prompt(self, initial_prompt, task_context):
        """
        创建增强版提示，包含任务上下文
        
        参数:
            initial_prompt (str): 原始提示
            task_context (dict): 任务上下文
            
        返回:
            str: 增强版提示
        """
        task_id = task_context.get('task_id', 'unknown')
        task_type = task_context.get('task_type', 'general')
        
        # 构建增强版提示
        prompt_parts = [
            f"# 任务执行: {task_id} ({task_type})",
            "请根据以下指令完成任务，并在完成后提供结构化输出。",
            
            "## 任务指令",
            initial_prompt,
        ]
        
        # 添加上下文信息
        if 'context' in task_context:
            prompt_parts.append("\n## 任务上下文")
            context_str = json.dumps(task_context['context'], ensure_ascii=False, indent=2)
            prompt_parts.append(f"```json\n{context_str}\n```")
            
        # 添加工件信息
        if 'artifacts' in task_context:
            prompt_parts.append("\n## 可用工件")
            for name, artifact in task_context['artifacts'].items():
                prompt_parts.append(f"\n### {name}:")
                if 'content' in artifact:
                    content = artifact['content']
                    # 如果内容太长，截断显示
                    if isinstance(content, str) and len(content) > 1000:
                        content = content[:997] + "..."
                    prompt_parts.append(f"```\n{content}\n```")
        
        # 添加输出格式要求
        prompt_parts.append("\n## 输出格式要求")
        prompt_parts.append("""
请按以下格式提供结构化输出:

```json
{
  "task_id": "任务ID",
  "success": true或false,
  "result": {
    "summary": "任务执行摘要",
    "details": "详细结果"
  },
  "artifacts": {
    "artifact_name": "工件内容",
    ...
  },
  "next_steps": [
    "建议的后续步骤1",
    "建议的后续步骤2",
    ...
  ]
}
```

确保在最后提供上述JSON格式的输出。
""")
        
        # 组合所有部分
        return "\n\n".join(prompt_parts)
    
    def _parse_task_results(self, interactions, task_context):
        """
        解析任务执行结果
        
        OBSOLETE: 这个方法使用了不可靠的正则表达式解析方式，已被新的结构化输出处理取代
        建议使用新的上下文管理机制
        
        参数:
            interactions (list): 交互记录
            task_context (dict): 任务上下文
            
        返回:
            dict: 解析后的结果
        """
        # 如果没有交互记录，返回失败结果
        if not interactions:
            return {
                "task_id": task_context.get('task_id', 'unknown'),
                "success": False,
                "error": "没有交互记录",
                "result": {
                    "summary": "任务执行失败",
                    "details": "未能与Claude进行交互"
                }
            }
            
        # 获取最后的Claude输出
        claude_outputs = [i['content'] for i in interactions if i['role'] == 'claude']
        last_output = claude_outputs[-1] if claude_outputs else ""
        
        # 提取JSON结果
        json_results = re.findall(r'```json\n(.*?)\n```', last_output, re.DOTALL)
        if json_results:
            try:
                # 解析找到的最后一个JSON
                result = json.loads(json_results[-1])
                # 添加任务ID（如果缺失）
                if 'task_id' not in result:
                    result['task_id'] = task_context.get('task_id', 'unknown')
                return result
            except json.JSONDecodeError:
                # JSON解析失败
                pass
                
        # 提取代码块
        code_blocks = re.findall(r'```(\w*)\n(.*?)```', last_output, re.DOTALL)
        artifacts = {}
        for i, (lang, code) in enumerate(code_blocks):
            artifact_name = f"code_block_{i+1}"
            if lang:
                artifact_name = f"{lang}_code_{i+1}"
            artifacts[artifact_name] = code.strip()
            
        # 构造默认结果
        return {
            "task_id": task_context.get('task_id', 'unknown'),
            "success": True,  # 假设成功，除非有明确错误
            "result": {
                "summary": "任务执行完成，但未提供结构化输出",
                "details": last_output[:500] + ("..." if len(last_output) > 500 else "")
            },
            "artifacts": artifacts,
            "raw_output": last_output
        }