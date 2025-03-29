# filename: coding/content_tool_call_agent.py
import json
import logging
from autogen.agentchat.conversable_agent import ConversableAgent
import uuid
import traceback
import tenacity  # 需要安装pip install tenacity
from openai import APIError  # 新增导入
import requests.exceptions as requests_exceptions  # 新增网络异常处理
from autogen.messages.agent_messages import ToolResponse  # 新增导入
from typing import Union, Optional, Dict, List # 导入 Dict 和 List
import os
from datetime import datetime
from autogen import Agent # 导入 Agent

logger = logging.getLogger(__name__)

class ContentToolCallAgent(ConversableAgent):
    """专用于处理DeepSeek响应格式的代理"""

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(3),  # 最大重试次数
        wait=tenacity.wait_fixed(2),  # 重试间隔
        # 扩展异常类型
        retry=tenacity.retry_if_exception_type((
            APIError,  # OpenAI官方异常
            requests_exceptions.Timeout,
            requests_exceptions.ConnectionError,
            TimeoutError  # 内置超时异常
        )),
        before_sleep=tenacity.before_sleep_log(logger, logging.WARNING)
    )
    def send(self, message, recipient, request_reply=None, silent=None):
        """重写发送方法处理原始响应"""
        try:
            # 自定义消息预处理
            processed_msg = self._format_message(message)
            return super().send(processed_msg, recipient, request_reply, silent)
        except Exception as e:
            logger.error(f"请求失败: {str(e)}")
            raise  # 触发重试

    def _is_deepseek_format(self, message) -> bool:
        """判断是否是DeepSeek格式的消息（content中包含tool calls的JSON代码块）"""
        if not isinstance(message, dict):
            return False
        
        content = message.get("content", "")
        # 只检查content是否包含带tool_calls的JSON代码块
        if isinstance(content, str) and content.strip().startswith("```json"):
            try:
                json_str = content.strip()[7:-3].strip()  # 去除```json标记
                json_data = json.loads(json_str)
                return "tool_calls" in json_data
            except Exception:
                return False
        return False

    def _is_tool_result(self, message) -> bool:
        """判断是否是工具执行结果"""
        return (
            isinstance(message, dict) 
            and "success" in message
        )

    def _format_message(self, message):
        """将DeepSeek响应格式转换为AutoGen兼容格式"""
        # 先判断是否是DeepSeek格式，不是的话直接返回原消息
        if not self._is_deepseek_format(message):
            return message
            
        # 处理DeepSeek格式的消息
        content = message.get("content", "")
        try:
            json_str = content.strip()[7:-3].strip()  # 去除```json标记
            json_data = json.loads(json_str)
            
            if "tool_calls" in json_data:
                # 创建ToolResponse对象列表
                tool_responses = []
                for call in json_data["tool_calls"]:
                    if not isinstance(call.get("function"), dict):
                        logger.warning("非法工具调用格式，跳过")
                        continue
                        
                    func_name = call["function"].get("name")
                    if not func_name:
                        logger.error("工具调用缺少name字段")
                        continue
                        
                    # 生成工具ID
                    tool_id = f"toolu_vrtx_{uuid.uuid4().hex[:25]}"
                    
                    # 创建ToolResponse对象
                    tool_response = ToolResponse(
                        tool_call_id=tool_id,
                        role="tool",
                        content=str(call["function"].get("arguments", "{}"))
                    )
                    tool_responses.append(tool_response)
                
                # 返回正确格式的消息
                return {
                    "role": "tool",
                    "content": "",  # 清空content避免触发代码执行
                    "tool_responses": tool_responses
                }
        except Exception as e:
            logger.error(f"JSON解析失败: {traceback.format_exc()}")
            return message  # 解析失败时返回原消息

    def _append_oai_message(self, message, role, conversation_id, is_sending):
        """最终消息存储前的格式保障（修复字符串类型问题）"""
        # 如果不是DeepSeek格式，直接调用父类方法
        if not self._is_deepseek_format(message):
            return super()._append_oai_message(message, role, conversation_id, is_sending)
            
        # 以下是DeepSeek格式的特殊处理
        # 统一消息格式为字典
        if isinstance(message, str):
            message = {"content": message}
        elif not isinstance(message, dict):
            message = {"content": str(message)}
        
        # 确保必须字段存在
        safe_msg = {
            "content": message.get("content", ""),
            "role": role,
            "tool_calls": message.get("tool_calls"),
            "function_call": message.get("function_call")
        }
        
        # 兜底内容设置
        if not safe_msg["content"] and not safe_msg["tool_calls"] and not safe_msg["function_call"]:
            safe_msg["content"] = "[无有效响应内容]"
        
        # 处理JSON代码块（DeepSeek的特殊响应格式）
        content = safe_msg["content"]
        if content.strip().startswith("```json"):
            try:
                json_str = content.strip()[7:-3].strip()  # 去除```json标记
                json_data = json.loads(json_str)
                
                if "tool_calls" in json_data:
                    safe_msg["tool_calls"] = []
                    for call in json_data["tool_calls"]:
                        # 防御性检查函数调用结构
                        if not isinstance(call.get("function"), dict):
                            logger.warning("非法工具调用格式，跳过")
                            continue
                            
                        func_name = call["function"].get("name")
                        if not func_name:
                            logger.error("工具调用缺少name字段")
                            continue
                            
                        # 生成工具ID
                        tool_id = f"toolu_vrtx_{uuid.uuid4().hex[:25]}"
                        
                        # 处理参数
                        args = call["function"].get("arguments", {})
                        if isinstance(args, dict):
                            args = json.dumps(args, ensure_ascii=False)
                        
                        safe_msg["tool_calls"].append({
                            "id": tool_id,
                            "type": "function",
                            "function": {
                                "name": func_name,
                                "arguments": args
                            }
                        })
                    safe_msg["content"] = ""  # 清空content避免触发代码执行
                    
            except Exception as e:
                logger.error(f"JSON解析失败: {traceback.format_exc()}")
        
        # 处理JSON代码块后添加空列表初始化
        safe_msg.setdefault("tool_calls", [])
        
        # 最终格式保障
        if "tool_calls" in safe_msg:
            # 确保始终是列表类型
            safe_msg["tool_calls"] = safe_msg["tool_calls"] or []
            for tool_call in safe_msg["tool_calls"]:
                tool_call.setdefault("type", "function")
                if isinstance(tool_call["function"].get("arguments"), dict):
                    tool_call["function"]["arguments"] = json.dumps(tool_call["function"]["arguments"])
        
        # 调用父类存储
        return super()._append_oai_message(safe_msg, role, conversation_id, is_sending)

    @staticmethod
    def _validate_message(msg):
        """扩展验证逻辑支持tool_calls"""
        if msg.get("content") or msg.get("function_call") or msg.get("tool_calls"):
            return msg
        raise ValueError("消息必须包含以下至少一项：content/function_call/tool_calls")

    def _validate_response(self, response):
        """新增响应验证逻辑"""
        if not response or not response.choices:
            raise ValueError("空响应")
        return response