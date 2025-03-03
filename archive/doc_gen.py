"""
代码文档生成器 - 基础版

该模块提供了一个基础的代码文档生成器，用于自动生成代码文档。作为其他文档生成器的基类，
实现了核心的文档生成功能。

主要功能：
1. 基础文件读取和处理
2. OpenRouter API 集成
3. 标准化的文档生成流程
4. Markdown 格式文档输出
5. PHP文件专项支持

技术特点：
1. 异步API调用
2. 结构化的提示词模板
3. 统一的文档格式
4. 灵活的文件处理机制
5. 详细的错误处理

配置项：
- input_dir: 输入目录路径
- output_dir: 输出目录路径
- supported_extensions: 支持的文件扩展名（当前仅支持.php）
- OpenRouter API配置：
  - base_url
  - api_key
  - default_headers

注意事项：
1. 需要有效的OpenRouter API密钥
2. 确保输入输出目录的读写权限
3. 目前仅支持PHP文件处理
4. 生成的文档需要人工审核
5. 建议对大型文件进行预处理

依赖：
- openai: OpenRouter API调用
- aiohttp: 异步HTTP请求
- asyncio: 异步操作支持
- pathlib: 文件路径处理

作者：[作者名称]
版本：1.0.0
创建日期：[创建日期]
最后更新：[更新日期]
"""

import os
import json
from pathlib import Path
from typing import Dict, Optional
import openai
import asyncio
import aiohttp

class CodeDocumentGenerator:
    def __init__(self, input_dir: str, output_dir: str):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化 OpenRouter 客户端
        self.client = openai.OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key="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",
            default_headers={
                "HTTP-Referer": "http://localhost:3000",
                "X-Title": "biantaishabi"
            }
        )
        
        # 修改支持的文件类型，只包含 PHP
        self.supported_extensions = {'.php'}
    
    def read_file(self, file_path: Path) -> Optional[str]:
        """读取文件内容"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return None

    async def call_llm(self, prompt: str) -> str:
        """调用OpenRouter API生成响应"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer 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",
                        "HTTP-Referer": "http://localhost:3000",
                        "X-Title": "biantaishabi",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "qwen/qwen-2.5-coder-32b-instruct",
                        "messages": [
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ]
                    }
                ) as response:
                    result = await response.json()
                    
                    if "choices" not in result or not result["choices"]:
                        raise Exception("No completion choices returned")
                    
                    return result["choices"][0]["message"]["content"]
            
        except Exception as e:
            print(f"OpenRouter API调用错误: {str(e)}")
            return f"文档生成失败: {str(e)}"

    def get_prompt_template(self, file_path: str, content: str) -> str:
        """生成XML格式的提示词"""
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<prompt>
    <task>
        请为提供的代码生成详细的文档注释。注释应采用Markdown格式，并包含尽可能详细的信息，以便于后续向量化存储和检索。
    </task>

    <input>
        <file_path>{file_path}</file_path>
        <code_content>
{content}
        </code_content>
    </input>

    <output_format>
        <markdown_template>
            # 文件说明
            ## 基本信息
            - 文件路径: {file_path}
            - 文件名: {Path(file_path).name}
            - 主要功能: {{main_purpose}}

            ## 详细描述
            {{detailed_file_description}}
            - 核心功能和目的
            - 实现的主要特性
            - 关键依赖说明
            - 使用场景
            - 技术实现要点
            - 注意事项和限制

            ## 主要组件
            {{main_components_description}}
            - 包含的主要类/模块
            - 组件之间的关系
            - 核心设计思路

            ## 方法说明
            ### {{method_name}}
            #### 功能描述
            {{detailed_method_description}}

            #### 参数说明
            - `{{param_name}}`: {{param_description}}
              - 类型: {{param_type}}
              - 是否必须: {{required}}
              - 默认值: {{default_value}}
              - 取值范围: {{value_range}}
              - 使用注意: {{usage_notes}}

            #### 返回值
            - 类型: {{return_type}}
            - 说明: {{return_description}}
            - 可能的返回值: {{possible_returns}}

            #### 异常处理
            - 可能的异常: {{exceptions}}
            - 处理方式: {{exception_handling}}

            #### 使用示例
            ```python
            {{code_example}}
            ```

            #### 实现细节
            {{implementation_details}}
            - 算法说明
            - 性能考虑
            - 优化方案

            #### 注意事项
            {{usage_notes}}
            - 使用限制
            - 性能影响
            - 最佳实践
        </markdown_template>
    </output_format>

    <requirements>
        <requirement>描述应清晰、准确、专业</requirement>
        <requirement>包含充分的技术细节</requirement>
        <requirement>说明实现原理和注意事项</requirement>
        <requirement>提供具体的使用示例</requirement>
        <requirement>突出关键点和限制条件</requirement>
        <requirement>使用Markdown格式保证可读性</requirement>
        <requirement>内容应适合向量化存储和后续检索</requirement>
    </requirements>
</prompt>
"""

    async def generate_doc(self, file_path: Path, content: str) -> Dict:
        """使用LLM生成文档注释"""
        # 构建提示词
        prompt = self.get_prompt_template(str(file_path), content)
        
        # 调用LLM生成文档
        markdown_doc = await self.call_llm(prompt)
        
        # 返回生成的文档
        doc = {
            "file_path": str(file_path),
            "documentation": markdown_doc,
            "original_content": content
        }
        
        return doc

    def save_doc(self, file_path: Path, doc: Dict):
        """保存生成的文档"""
        # 将输出文件扩展名改为.md，直接放在输出目录下
        output_path = self.output_dir / file_path.with_suffix('.md').name
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(doc["documentation"])

    async def process_file(self, file_path: Path):
        """处理单个文件"""
        print(f"\n开始处理文件: {file_path}")
        content = self.read_file(file_path)
        if content is None:
            print(f"❌ 读取文件失败: {file_path}")
            return
        
        print(f"✅ 文件读取成功，开始生成文档...")
        try:
            doc = await self.generate_doc(file_path, content)
            print(f"✅ 文档生成成功，准备保存...")
            
            self.save_doc(file_path, doc)
            print(f"✅ 文档已保存到: {self.output_dir / file_path.with_suffix('.md').name}")
        except Exception as e:
            print(f"❌ 处理文件时出错: {str(e)}")

    async def process_directory(self):
        """处理整个目录"""
        print(f"\n开始处理目录: {self.input_dir}")
        print(f"输出目录: {self.output_dir}")
        print(f"支持的文件类型: {self.supported_extensions}")
        
        files_processed = 0
        for file_path in self.input_dir.rglob('*'):
            print(f"发现文件: {file_path}")
            if file_path.is_file():
                print(f"文件后缀: {file_path.suffix}")
                if file_path.suffix in self.supported_extensions:
                    print(f"处理符合条件的文件: {file_path}")
                    await self.process_file(file_path)
                    files_processed += 1
                else:
                    print(f"跳过不支持的文件类型: {file_path}")
        
        print(f"\n处理完成! 共处理了 {files_processed} 个文件")

async def main():
    # 设置输入输出目录
    input_dir = "/Users/wangbo/Documents/opengrok/src/upfit-fit365-2.0.0-a0e2374aa54fbe52bf0887755cba1a239b2a0a10/app/controllers/goods"
    output_dir = "/Users/wangbo/Documents/opengrok/src/upfit-fit365-2.0.0-a0e2374aa54fbe52bf0887755cba1a239b2a0a10/app/controllers/goods"
    
    print(f"启动文档生成器...")
    print(f"输入目录: {input_dir}")
    print(f"输出目录: {output_dir}")
    
    # 创建生成器实例并处理
    generator = CodeDocumentGenerator(input_dir, output_dir)
    await generator.process_directory()

if __name__ == "__main__":
    asyncio.run(main())