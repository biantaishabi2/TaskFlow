"""
并发代码文档生成器 - 选择性文件处理版本

该模块提供了一个并发文档生成器，用于为选定的代码文件自动生成文档。

主要功能：
1. 支持并发处理多个文件，通过信号量控制并发数
2. 使用阿里云 DashScope API (Qwen模型) 生成文档
3. 可以选择性处理指定的文件列表
4. 支持自定义文件大小范围和文件类型过滤
5. 生成标准化的 Markdown 格式文档

配置选项：
- input_path: 输入文件或目录的路径
- output_dir: 输出文档的目录
- files_to_process: 需要处理的文件列表
- max_concurrency: 最大并发数（默认2）
- model_name: 使用的模型名称（默认qwen-plus）

注意事项：
1. 需要配置有效的阿里云 API 密钥
2. 建议合理设置并发数，避免API限流
3. 生成的文档需要进行质量验证
4. 文件选择基于文件名和大小进行过滤
5. 支持处理单个文件或整个目录

依赖：
- openai: 用于调用 DashScope API
- aiohttp: 处理异步HTTP请求
- asyncio: 实现并发处理
- pathlib: 处理文件路径

作者：[作者名称]
版本：1.0.0
创建日期：[创建日期]
"""

import os
import json
from pathlib import Path
from typing import Dict, Optional, List
import openai
import asyncio
import aiohttp
from doc_gen import CodeDocumentGenerator
from openai import OpenAI
from file_count import count_files

class ConcurrentCodeDocumentGeneratorSelectedFiles(CodeDocumentGenerator):
    """
    并发代码文档生成器类，用于选择性地处理指定文件并生成文档。

    该类继承自 CodeDocumentGenerator，实现了并发文档生成的核心功能。
    通过信号量控制并发数量，使用阿里云 DashScope API 生成文档。

    属性：
        files_to_process (List[str]): 需要处理的文件名列表
        semaphore (asyncio.Semaphore): 控制并发数量的信号量
        is_single_file (bool): 是否处理单个文件
        model (str): 使用的模型名称
        dashscope_client (OpenAI): 阿里云 API 客户端实例
    """

    def __init__(self, input_path: str, output_dir: str, files_to_process: List[str], max_concurrency: int = 2):
        super().__init__(input_path, output_dir)
        self.files_to_process = files_to_process
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.is_single_file = Path(input_path).is_file()
        self.model = "qwen-plus"
        # 初始化阿里云客户端
        self.dashscope_client = OpenAI(
            api_key="sk-0ff567ec7e3f4afaa3edcaf39a45af6f",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )

    async def call_dashscope(self, prompt: str, max_retries: int = 3, timeout: int = 120) -> str:
        """
        调用阿里云 DashScope API 生成文档。

        参数：
            prompt (str): 发送给模型的提示词
            max_retries (int): 最大重试次数，默认3次
            timeout (int): API调用超时时间，默认120秒

        返回：
            str: 模型生成的文档内容

        异常：
            在重试次数用尽后，返回错误信息字符串
        """
        for attempt in range(max_retries):
            try:
                # 使用线程池执行同步API调用
                loop = asyncio.get_event_loop()
                completion = await loop.run_in_executor(
                    None,
                    lambda: self.dashscope_client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": "You are a helpful assistant."},
                            {"role": "user", "content": prompt}
                        ],
                        timeout=timeout
                    )
                )
                return completion.choices[0].message.content
            except Exception as e:
                if attempt == max_retries - 1:
                    print(f"DashScope API调用错误 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                    return f"文档生成失败: {str(e)}"
                else:
                    print(f"重试中 ({attempt + 1}/{max_retries})...")
                    await asyncio.sleep(2 ** attempt)

    def get_prompt_template(self, file_path: str, content: str) -> str:
        """
        生成用于文档生成的XML格式提示词模板。

        参数：
            file_path (str): 待处理文件的路径
            content (str): 文件内容

        返回：
            str: 格式化后的XML提示词
        """
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
            - 文件类型: [类型]
            - 主要功能: [功能概述]
            
            ## 详细说明
            ### 代码结构
            [描述代码的主要结构和组织方式]
            
            ### 核心功能
            [详细说明主要功能点和实现方式]
            
            ### 依赖关系
            [说明代码依赖的类、库或其他资源]
            
            ### 使用示例
            [提供具体的使用示例和代码片段]
            
            ### 注意事项
            [列出使用时需要注意的关键点和限制条件]
            
            ## 补充信息
            [其他需要说明的内容]
        </markdown_template>
    </output_format>

    <requirements>
        <requirement>详细分析代码结构和功能</requirement>
        <requirement>说明实现原理和注意事项</requirement>
        <requirement>提供具体的使用示例</requirement>
        <requirement>突出关键点和限制条件</requirement>
        <requirement>使用Markdown格式保证可读性</requirement>
        <requirement>内容应适合向量化存储和后续检索</requirement>
    </requirements>
</prompt>
"""

    async def generate_doc(self, file_path: Path, content: str) -> Dict:
        """
        使用LLM为指定文件生成文档注释。

        参数：
            file_path (Path): 文件路径
            content (str): 文件内容

        返回：
            Dict: 包含文件路径、生成的文档和原始内容的字典
        """
        prompt = self.get_prompt_template(str(file_path), content)
        markdown_doc = await self.call_dashscope(prompt)
        
        doc = {
            "file_path": str(file_path),
            "documentation": markdown_doc,
            "original_content": content
        }
        
        return doc

    async def process_file(self, file_path: Path):
        """
        处理单个文件，生成对应的文档。

        参数：
            file_path (Path): 待处理的文件路径

        说明：
            - 仅处理 files_to_process 列表中的文件
            - 使用信号量控制并发
            - 处理结果会保存到指定的输出目录
        """
        file_name_without_ext = file_path.stem
        
        if file_name_without_ext in self.files_to_process:
            async with self.semaphore:
                # 修复相对路径显示
                try:
                    relative_path = file_path.relative_to(Path(self.input_dir).parent.parent.parent / 'app')
                except ValueError:
                    relative_path = file_path

                print(f"\n开始处理文件: {relative_path}, 使用模型: {self.model}")
                content = self.read_file(file_path)
                if content is None:
                    print(f"❌ 读取文件失败: {relative_path}")
                    return
                
                print(f"✅ 文件读取成功，开始生成文档...")
                try:
                    doc = await self.generate_doc(file_path, content)
                    print(f"✅ 文档生成成功，准备保存...")
                    
                    output_filename = file_path.name.replace(file_path.suffix, '.md')
                    output_path = Path(self.output_dir) / output_filename
                    
                    self.save_doc(output_path, doc)
                    print(f"✅ 文档已保存到: {output_path}")
                except Exception as e:
                    print(f"❌ 处理文件时出错: {str(e)}")
        else:
            print(f"跳过已处理的文件: {file_path}")
            return

    async def process_directory(self):
        """
        并发处理整个目录或单个文件。

        功能：
            - 支持处理单个文件或整个目录
            - 使用异步任务并发处理多个文件
            - 仅处理支持的文件类型
            - 输出处理进度和结果统计
        """
        if self.is_single_file:
            file_path = Path(self.input_dir)
            if file_path.suffix in self.supported_extensions:
                await self.process_file(file_path)
            else:
                print(f"不支持的文件类型: {file_path.suffix}")
            return

        print(f"\n开始处理目录: {self.input_dir}")
        print(f"输出目录: {self.output_dir}")
        print(f"待处理文件数量: {len(self.files_to_process)}")
        
        tasks: List[asyncio.Task] = []
        for file_path in self.input_dir.rglob('*'):
            if file_path.is_file() and file_path.suffix in self.supported_extensions:
                task = asyncio.create_task(self.process_file(file_path))
                tasks.append(task)
        
        if tasks:
            await asyncio.gather(*tasks)
            print(f"\n处理完成! 共处理了 {len(tasks)} 个文件")
        else:
            print("没有找到需要处理的文件")

async def main():
    """
    主函数，用于初始化和启动文档生成器。

    功能：
        - 设置输入输出路径
        - 获取待处理的文件列表
        - 创建并运行文档生成器实例
    """
    # 设置输入输出目录
    input_path = "/Users/wangbo/Documents/opengrok/src/2.0/app/plugins/"
    output_dir = "/Users/wangbo/Documents/opengrok/src/2.0/doc_gen/plugins/"
    
    # 从 file_count.py 获取需要处理的文件列表（小于1KB的文件）
    files_to_process, _ = count_files(output_dir)  # 解包返回值，只取小文件列表
    
    print(f"启动选择性并发文档生成器...")
    print(f"输入路径: {input_path}")
    print(f"输出目录: {output_dir}")
    print(f"待处理的小文件列表（<1KB）: {files_to_process}")
    
    generator = ConcurrentCodeDocumentGeneratorSelectedFiles(
        input_path, 
        output_dir,
        files_to_process
    )
    await generator.process_directory()

if __name__ == "__main__":
    asyncio.run(main()) 