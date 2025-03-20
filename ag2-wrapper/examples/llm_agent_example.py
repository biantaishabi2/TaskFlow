# 使用AssistantAgent和LLMDrivenUserProxy的自动编程示例

# 1. 导入必要的库
from autogen import AssistantAgent
from ..ag2_wrapper.chat_modes.llm_driven_agent import LLMDrivenUserProxy
import os

# 2. 定义LLM配置（使用OpenRouter的Gemini模型）
llm_config = {
    "api_type": "openai",
    "base_url": "https://openrouter.ai/api/v1",
    "api_key": os.environ.get("OPENROUTER_API_KEY"),
    "model": "google/gemini-2.0-flash-lite-001"
}

# 3. 创建AssistantAgent（使用默认系统提示词）
assistant = AssistantAgent(
    name="程序员助手",
    llm_config=llm_config,
    # 默认system_message，不需要指定
)

# 4. 创建我们的LLMDrivenUserProxy（不需要llm_config）
auto_user = LLMDrivenUserProxy(
    name="自动用户",
    human_input_mode="ALWAYS",  # 虽然设置为ALWAYS，但由于重写了get_human_input方法，实际不会请求输入
    code_execution_config={
        "work_dir": "coding_workspace",
        "use_docker": False  # 直接在本地环境执行
    },
    # 不需要llm_config
)

# 5. 启动对话
chat_result = auto_user.initiate_chat(
    assistant,
    message="你好！我想学习如何创建一个Python程序，它能够：\n1. 生成一个随机数据集\n2. 计算一些基本统计信息\n3. 将结果可视化\n\n请帮我设计这个程序，并展示如何使用shell命令运行它。"
)

# 6. 打印对话历史
print("\n=== 完整对话历史 ===\n")
for message in chat_result.chat_history:
    role = message.get("role", "unknown")
    name = message.get("name", role)
    content = message.get("content", "")
    print(f"【{name}】: {content}\n")

print("=== 对话结束 ===")