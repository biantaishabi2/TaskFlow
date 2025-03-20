# 使用AG2Wrapper创建LLM驱动用户代理的自动编程示例

# 1. 导入必要的库
from ..ag2_wrapper.core.wrapper import AG2Wrapper
from ..ag2_wrapper.core.config import create_openrouter_config
from ..ag2_wrapper.chat_modes.llm_driven_agent import LLMDrivenUserProxy
import autogen
import os

# 2. 创建AG2Wrapper实例
wrapper = AG2Wrapper()

# 3. 定义LLM配置（使用OpenRouter的Gemini模型）
llm_config = create_openrouter_config(
    model="google/gemini-2.0-flash-lite-001",
    api_key=os.environ.get("OPENROUTER_API_KEY")
)

# 4. 配置助手和用户代理
assistant = autogen.AssistantAgent(
    name="程序员助手",
    llm_config=llm_config,
)

# 创建LLMDrivenUserProxy实例
user = LLMDrivenUserProxy(
    name="自动用户",
    human_input_mode="ALWAYS",
    code_execution_config={
        "work_dir": "coding_workspace",
        "use_docker": False  # 直接在本地环境执行
    }
)

# 6. 启动对话
initial_message = (
    "你好！我想学习如何创建一个Python程序，它能够：\n"
    "1. 生成一个随机数据集\n"
    "2. 计算一些基本统计信息，生成九张图片，在图片中使用英文注释和标题\n"
    "3. 将结果可视化保存在图片里面\n\n"
    "请帮我设计这个程序，并展示如何使用shell命令运行它。记住一次只要运行一个命令，等待命令执行完成后再运行下一个命令。"
)

# 使用正确的AutoGen API启动对话
chat_result = user.initiate_chat(
    assistant,
    message=initial_message
)

# 7. 打印对话历史
print("\n=== 完整对话历史 ===\n")
for message in chat_result.chat_history:
    role = message.get("role", "unknown")
    name = message.get("name", role)
    content = message.get("content", "")
    print(f"【{name}】: {content}\n")

print("=== 对话结束 ===") 