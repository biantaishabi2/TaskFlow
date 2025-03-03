"""
并发代码文档生成器 - 完整版

该模块提供了一个功能完整的并发文档生成器，用于批量处理代码文件并生成对应的文档。

主要功能：
1. 支持并发处理大量文件，通过信号量控制并发数
2. 智能模型选择：根据文件大小自动选择合适的模型
   - 小文件（<=100KB）：使用 qwen-2.5-coder-32b-instruct
   - 大文件（>100KB）：使用 qwen-plus
3. 支持多种API调用：
   - OpenRouter API：用于高性能模型调用
   - 阿里云 DashScope API：用于常规文档生成
4. 详细的PHP文件统计功能：
   - 按目录统计文件数量和行数
   - 计算平均行数
   - 生成层级化的统计报告

技术特点：
1. 异步并发处理，提高效率
2. 自动重试机制，提高可靠性
3. 详细的进度日志输出
4. 标准化的XML格式提示词模板
5. 灵活的文件路径处理

配置说明：
- max_concurrency: 最大并发数（默认50）
- supported_extensions: 支持的文件类型
- API密钥：需配置OpenRouter和DashScope的API密钥

注意事项：
1. 需要合理配置并发数，避免API限流
2. 建议定期检查统计信息，监控处理进度
3. 生成的文档需要进行质量验证
4. 请确保API密钥的安全性

依赖：
- openai: API调用
- aiohttp: 异步HTTP请求
- asyncio: 异步并发控制
- pathlib: 文件路径处理
- dashscope: 阿里云API调用

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
import dashscope

class ConcurrentCodeDocumentGenerator(CodeDocumentGenerator):
    """
    并发代码文档生成器类，支持大规模文件处理和智能模型选择。

    该类继承自 CodeDocumentGenerator，实现了高并发文档生成功能。
    特点：
    1. 支持并发处理多个文件
    2. 智能模型选择（基于文件大小）
    3. 支持多种API调用方式
    4. 详细的PHP文件统计

    属性：
        semaphore (asyncio.Semaphore): 控制并发数量的信号量
        is_single_file (bool): 是否处理单个文件
        php_file_stats (dict): 存储PHP文件统计信息的嵌套字典
        dashscope_client (OpenAI): 阿里云 API 客户端实例
    """

    def __init__(self, input_path: str, output_dir: str, max_concurrency: int = 50):
        # 调用父类的初始化方法
        super().__init__(input_path, output_dir)
        # 添加并发控制
        self.semaphore = asyncio.Semaphore(max_concurrency)
        # 判断输入路径是文件还是目录
        self.is_single_file = Path(input_path).is_file()
        # 使用嵌套字典存储更详细的统计信息
        self.php_file_stats = {}
        
        # 初始化阿里云客户端
        self.dashscope_client = OpenAI(
            api_key="sk-0ff567ec7e3f4afaa3edcaf39a45af6f",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        
    def update_php_stats(self, file_path: Path):
        """
        更新PHP文件的统计信息。

        参数：
            file_path (Path): PHP文件的路径

        功能：
            - 统计文件数量
            - 计算文件行数
            - 按目录组织统计信息
            - 存储每个文件的具体信息
        """
        if file_path.suffix.lower() == '.php':
            dir_path = str(file_path.parent)
            
            # 初始化目录统计信息
            if dir_path not in self.php_file_stats:
                self.php_file_stats[dir_path] = {
                    'file_count': 0,
                    'total_lines': 0,
                    'files': {}  # 存储每个文件的具体信息
                }
            
            # 计算文件行数
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    line_count = len(lines)
                    
                    # 更新统计信息
                    self.php_file_stats[dir_path]['file_count'] += 1
                    self.php_file_stats[dir_path]['total_lines'] += line_count
                    self.php_file_stats[dir_path]['files'][str(file_path.name)] = line_count
            except Exception as e:
                print(f"统计文件 {file_path} 行数时出错: {str(e)}")

    def print_php_stats(self):
        """
        打印PHP文件的统计信息。

        输出内容：
            - 按目录显示文件统计
            - 每个目录的文件数和总行数
            - 目录内文件的平均行数
            - 总体统计信息
        """
        print("\n=== PHP文件统计 ===")
        if not self.php_file_stats:
            print("没有找到PHP文件")
            return
            
        total_files = 0
        total_lines = 0
        
        # 打印表头
        print(f"{'目录':<50} {'文件数':<10} {'总行数':<10} {'平均行数':<10}")
        print("-" * 80)
        
        # 按目录名称排序输出统计信息
        for dir_path in sorted(self.php_file_stats.keys()):
            stats = self.php_file_stats[dir_path]
            file_count = stats['file_count']
            total_lines_in_dir = stats['total_lines']
            avg_lines = round(total_lines_in_dir / file_count if file_count > 0 else 0, 2)
            
            # 更新总计
            total_files += file_count
            total_lines += total_lines_in_dir
            
            # 打印目录统计信息
            print(f"{dir_path:<50} {file_count:<10} {total_lines_in_dir:<10} {avg_lines:<10}")
            
            # 打印每个文件的详细信息
            for file_name, line_count in stats['files'].items():
                print(f"  ├─ {file_name:<46} {line_count} 行")
            print("-" * 80)
        
        # 打印总计信息
        overall_avg = round(total_lines / total_files if total_files > 0 else 0, 2)
        print(f"\n总计:")
        print(f"- 文件总数: {total_files}")
        print(f"- 代码总行数: {total_lines}")
        print(f"- 平均每个文件行数: {overall_avg}")
        print("=" * 80)

    async def process_file(self, file_path: Path):
        """
        处理单个文件，包括模型选择和文档生成。

        参数：
            file_path (Path): 待处理的文件路径

        功能：
            - 根据文件大小选择合适的模型
            - 读取和处理文件内容
            - 生成和保存文档
            - 更新统计信息
        """
        async with self.semaphore:
            # 获取文件大小
            file_size_kb = file_path.stat().st_size / 1024
            model = "qwen/qwen-2.5-coder-32b-instruct" if file_size_kb <= 100 else "qwen-plus"

            # 修复相对路径显示
            try:
                relative_path = file_path.relative_to(Path(self.input_dir).parent.parent.parent / 'app')
            except ValueError:
                relative_path = file_path

            print(f"\n开始处理文件: {relative_path}, 大小: {file_size_kb:.2f} KB, 使用模型: {model}")
            content = self.read_file(file_path)
            if content is None:
                print(f"❌ 读取文件失败: {relative_path}")
                return
            
            print(f"✅ 文件读取成功，开始生成文档...")
            try:
                doc = await self.generate_doc(file_path, content, model)
                print(f"✅ 文档生成成功，准备保存...")
                
                # 构建输出文件名
                output_filename = file_path.name.replace(file_path.suffix, '.md')
                output_path = Path(self.output_dir) / output_filename
                
                self.save_doc(output_path, doc)
                print(f"✅ 文档已保存到: {output_path}")
            except Exception as e:
                print(f"❌ 处理文件时出错: {str(e)}")

    async def call_openrouter(self, prompt: str, model: str, max_retries: int = 3, timeout: int = 120) -> str:
        """
        调用OpenRouter API，支持重试机制。

        参数：
            prompt (str): 提示词
            model (str): 模型名称
            max_retries (int): 最大重试次数
            timeout (int): 超时时间（秒）

        返回：
            str: API响应的文本内容

        异常处理：
            - 支持指数退避重试
            - 超时和错误处理
        """
        for attempt in range(max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer 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",
                            "HTTP-Referer": "biantaishabi",
                            "X-Title": "biantaishabi",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": model,
                            "messages": [
                                {
                                    "role": "user",
                                    "content": prompt
                                }
                            ]
                        },
                        timeout=aiohttp.ClientTimeout(total=timeout)  # 添加timeout控制
                    ) as response:
                        result = await response.json()
                        if "choices" not in result or not result["choices"]:
                            raise Exception("No completion choices returned")
                        return result["choices"][0]["message"]["content"]
            except Exception as e:
                if attempt == max_retries - 1:  # 最后一次重试失败
                    print(f"OpenRouter API调用错误 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                    return f"文档生成失败: {str(e)}"
                else:
                    print(f"重试中 ({attempt + 1}/{max_retries})...")
                    await asyncio.sleep(2 ** attempt)  # 指数退避重试

    async def call_dashscope(self, prompt: str, max_retries: int = 3, timeout: int = 120) -> str:
        """
        调用阿里云 DashScope API。

        参数：
            prompt (str): 提示词
            max_retries (int): 最大重试次数
            timeout (int): 超时时间（秒）

        返回：
            str: 生成的文档内容

        特点：
            - 支持异步调用
            - 包含重试机制
            - 详细的日志输出
        """
        for attempt in range(max_retries):
            try:
                print(f"调用DashScope API (尝试 {attempt + 1}/{max_retries})...")
                print(f"使用模型: qwen-plus, 超时时间: {timeout} 秒")
                print(f"发送的提示词: {prompt[:100]}...")  # 只打印前100个字符以避免过长输出

                # 使用 DashScope SDK 进行调用
                response = await asyncio.to_thread(
                    dashscope.Generation.call,
                    api_key="sk-0ff567ec7e3f4afaa3edcaf39a45af6f",  # 使用现有的 key
                    model="qwen-plus",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    result_format='message'
                )
                
                print("API调用成功，返回结果处理中...")
                print(f"API 响应: {response}")  # 添加响应日志
                return response['output']['text'] if 'output' in response else response['choices'][0]['message']['content']
            except Exception as e:
                print(f"DashScope API调用错误 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                if attempt == max_retries - 1:  # 最后一次重试失败
                    return f"文档生成失败: {str(e)}"
                else:
                    print(f"重试中 ({attempt + 1}/{max_retries})...")
                    await asyncio.sleep(2 ** attempt)  # 指数退避重试

    async def call_llm(self, prompt: str, model: str) -> str:
        """
        根据模型选择不同的API调用方式。

        参数：
            prompt (str): 提示词
            model (str): 模型名称

        返回：
            str: 生成的文档内容

        说明：
            - qwen-2.5-coder-32b-instruct: 使用OpenRouter
            - 其他模型: 使用DashScope
        """
        if model == "qwen/qwen-2.5-coder-32b-instruct":
            return await self.call_openrouter(prompt, model)
        else:
            return await self.call_dashscope(prompt)

    async def generate_doc(self, file_path: Path, content: str, model: str) -> Dict:
        """
        使用LLM生成文档注释。

        参数：
            file_path (Path): 文件路径
            content (str): 文件内容
            model (str): 使用的模型名称

        返回：
            Dict: 包含文件信息和生成文档的字典
        """
        prompt = self.get_prompt_template(str(file_path), content)
        
        # 调用LLM生成文档，传入选择的模型
        markdown_doc = await self.call_llm(prompt, model)
        
        doc = {
            "file_path": str(file_path),
            "documentation": markdown_doc,
            "original_content": content
        }
        
        return doc

    async def process_directory(self):
        """
        并发处理整个目录或单个文件。

        功能：
            - 支持单文件或目录处理
            - 并发任务管理
            - 进度跟踪和统计
            - 结果汇总输出
        """
        if self.is_single_file:
            print(f"\n开始处理单个文件: {self.input_dir}")
            file_path = Path(self.input_dir)
            if file_path.suffix in self.supported_extensions:
                self.update_php_stats(file_path)  # 更新统计
                await self.process_file(file_path)
            else:
                print(f"不支持的文件类型: {file_path.suffix}")
            self.print_php_stats()  # 打印统计
            return

        print(f"\n开始处理目录: {self.input_dir}")
        print(f"输出目录: {self.output_dir}")
        print(f"支持的文件类型: {self.supported_extensions}")
        
        tasks: List[asyncio.Task] = []
        for file_path in self.input_dir.rglob('*'):
            if file_path.is_file() and file_path.suffix in self.supported_extensions:
                self.update_php_stats(file_path)  # 更新统计
                print(f"添加任务: {file_path}")
                task = asyncio.create_task(self.process_file(file_path))
                tasks.append(task)
        
        if tasks:
            await asyncio.gather(*tasks)
            print(f"\n处理完成! 共处理了 {len(tasks)} 个文件")
        else:
            print("没有找到需要处理的文件")
            
        self.print_php_stats()  # 打印统计

    def get_prompt_template(self, file_path: str, content: str) -> str:
        """
        生成XML格式的提示词模板。

        参数：
            file_path (str): 文件路径
            content (str): 文件内容

        返回：
            str: 格式化的XML提示词

        说明：
            生成的模板包含：
            - 任务说明
            - 输入内容
            - 输出格式
            - 具体要求
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

    def save_doc(self, output_path: Path, doc: Dict):
        """
        保存生成的文档到指定路径。

        参数：
            output_path (Path): 输出文件路径
            doc (Dict): 文档内容字典

        功能：
            - 自动创建输出目录
            - 支持字典或字符串格式的文档
            - UTF-8编码保存
        """
        # 确保输出目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 直接写入文件，不需要计算相对路径
        with open(output_path, 'w', encoding='utf-8') as f:
            if isinstance(doc, dict):
                f.write(doc['documentation'])
            else:
                f.write(doc)

async def main():
    """
    主函数，初始化并运行文档生成器。

    功能：
        - 设置输入输出路径
        - 创建生成器实例
        - 启动文档生成过程
        - 显示处理进度
    """
    # 设置输入输出目录
    input_path = "/Users/wangbo/Documents/opengrok/src/2.0/app/components/"
    output_dir = "/Users/wangbo/Documents/opengrok/src/2.0/doc_gen/components/"
    
    print(f"启动并发文档生成器...")
    print(f"输入路径: {input_path}")
    print(f"输出目录: {output_dir}")
    
    generator = ConcurrentCodeDocumentGenerator(input_path, output_dir)
    await generator.process_directory()

if __name__ == "__main__":
    asyncio.run(main()) 