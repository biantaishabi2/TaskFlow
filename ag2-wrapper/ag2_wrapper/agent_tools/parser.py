"""
LLM 响应解析器模块

主要功能:
- 提供标准化的LLM响应解析框架
- 支持自然语言思考过程提取
- 支持结构化数据(JSON)解析
- 实现API调用场景的专用解析器

核心组件:
1. ParsedResponse: 标准化解析结果容器
   - 包含自然语言思考过程(thought)
   - 支持工具调用(tool_calls)、内容输出(content)、API调用(api_call)的存储

2. BaseResponseParser: 解析器抽象基类
   - 定义统一的parse接口
   - 支持不同场景的解析器实现

3. 内置解析器实现:
   - ApiCallResponseParser: API调用场景专用解析器
   - DefaultResponseParser: 基础响应解析器

设计理念:
1. 开闭原则: 通过继承BaseResponseParser扩展新解析器
2. 单一职责: 每个解析器只处理特定格式的响应
3. 防御式编程: 包含完整的格式验证和错误处理

使用示例:
>>> parser = ApiCallResponseParser()
>>> response = '''思考过程...```json{"api_call": ...}```'''
>>> parsed = parser.parse(response)
>>> print(parsed.thought)  # 自然语言思考过程
>>> print(parsed.api_call)  # 结构化API调用信息
"""

from abc import ABC, abstractmethod
import json
import re
from typing import Dict, Any, Optional
from dataclasses import dataclass
import logging
import ast

@dataclass
class ParsedResponse:
    thought: str
    tool_calls: Optional[list] = None
    content: Optional[str] = None
    api_call: Optional[Dict[str, Any]] = None  # 新增API调用字段

class BaseResponseParser(ABC):
    @abstractmethod
    def parse(self, response: str) -> ParsedResponse:
        """解析LLM响应"""
        pass

class ApiCallResponseParser(BaseResponseParser):
    """专用于API调用场景的响应解析器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def parse(self, response: str) -> ParsedResponse:
        result = ParsedResponse(thought="", tool_calls=None, api_call=None)
        
        # 添加调试日志
        self.logger.debug(f"开始解析响应:\n{response}")
        
        # 提取自然语言思考过程
        non_code_content = re.sub(r'```.*?```', '', response, flags=re.DOTALL)
        result.thought = '\n'.join([line.strip() for line in non_code_content.split('\n') if line.strip()])
        
        # 使用更宽松的正则表达式匹配 JSON 块
        json_blocks = re.findall(r'```(?:json)?\s*({\s*"tool_calls"[\s\S]*?})\s*```', response, flags=re.DOTALL)
        self.logger.debug(f"找到的 JSON 块: {json_blocks}")  # 添加调试日志
        
        for block in json_blocks:
            try:
                cleaned_block = block.strip()
                self.logger.debug(f"尝试解析 JSON 块:\n{cleaned_block}")  # 添加调试日志
                parsed = json.loads(cleaned_block)
                
                if "tool_calls" in parsed:
                    for tc in parsed["tool_calls"]:
                        if self._is_valid_tool_call(tc):
                            validated_call = {
                                "tool_name": tc["tool_name"],
                                "parameters": tc["parameters"]
                            }
                            result.tool_calls = [validated_call]
                            
                            if tc["tool_name"] == "api_call":
                                result.api_call = tc["parameters"]
                                self.logger.debug(f"成功解析出 API 调用: {tc['parameters']}")  # 添加调试日志
                            break
            except Exception as e:
                self.logger.debug(f"JSON解析失败: {str(e)}")
                continue
        
        return result

    def _is_valid_tool_call(self, tool_call: Dict) -> bool:
        """基础格式验证（所有工具通用）
        - 必须有 url 和 method
        - body 是可选的，根据实际 API 需求决定
        """
        # 基础结构验证
        if not (isinstance(tool_call, dict) and
                "tool_name" in tool_call and
                isinstance(tool_call.get("tool_name"), str) and
                "parameters" in tool_call and
                isinstance(tool_call["parameters"], dict)):
            return False
        
        # 验证必需的 url 和 method
        params = tool_call["parameters"]
        if not (isinstance(params.get("url"), str) and
                isinstance(params.get("method"), str)):
            return False
        
        return True

class DefaultResponseParser(BaseResponseParser):
    def parse(self, response: str) -> ParsedResponse:
        """默认解析器实现"""
        import logging
        
        logger = logging.getLogger(__name__)
        
        # 初始化结果
        thought = ""
        tool_calls = None
        
        try:
            # 1. 先找到最后一个 json 代码块
            last_json_block_end = response.rfind('```')
            if last_json_block_end != -1:
                # 从结尾往前找到对应的开始标记
                last_json_block_start = response.rfind('```json', 0, last_json_block_end)
                if last_json_block_start != -1:
                    # 提取 JSON 内容
                    json_str = response[last_json_block_start + 7:last_json_block_end].strip()
                    logger.debug(f"提取到的 JSON 字符串长度: {len(json_str)}")
                    
                    # 解析 JSON
                    parsed = json.loads(json_str)
                    if isinstance(parsed, dict) and "tool_calls" in parsed:
                        tool_calls = parsed["tool_calls"]
                        logger.debug(f"成功解析出 tool_calls")
                    
                    # 提取思考过程（JSON块之前的所有内容）
                    thought = response[:last_json_block_start].strip()
                else:
                    # 没有找到 ```json 开始标记，可能是普通文本响应
                    thought = response.strip()
            else:
                # 没有代码块，整个响应都是思考过程
                thought = response.strip()
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败: {str(e)}")
            # JSON 解析失败时，将整个响应视为思考过程
            thought = response.strip()
        except Exception as e:
            logger.error(f"解析过程发生异常: {str(e)}")
            thought = response.strip()
        
        return ParsedResponse(
            thought=thought,
            tool_calls=tool_calls,
            content=None
        ) 