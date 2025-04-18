#!/usr/bin/env python
import argparse
import sys
import os
import importlib.util
import time
import json
import asyncio
from datetime import datetime
import logging
import warnings
import anyio

# 抑制Pydantic和Autogen警告
warnings.filterwarnings("ignore", 
                       message="Valid config keys have changed in V2", 
                       module="pydantic")
# 抑制Autogen模型价格警告
warnings.filterwarnings("ignore", 
                       message="Model .* is not found. The cost will be 0.*", 
                       module="autogen.oai.client")

# 尝试导入AG2相关模块
try:
    from ag2_wrapper.core.ag2_two_agent_executor import AG2TwoAgentExecutor
    from ag2_wrapper.core.config import ConfigManager
    _HAS_AG2 = True
except ImportError:
    _HAS_AG2 = False

# 定义一个共用函数来处理chat和agent两个子命令
async def handle_ag2_chat(command, args, use_human_input, base_dir):
    """
    处理chat和agent命令的通用函数 (异步版本)
    
    Args:
        command: 子命令名称 ('chat' 或 'agent')
        args: 解析后的命令行参数
        use_human_input: 是否使用标准UserProxyAgent与真人交互
        base_dir: 基础目录路径
    """
    # 检查AG2是否可用
    if not _HAS_AG2:
        print("错误: 未能导入AG2相关模块，请确保ag2-wrapper已正确安装")
        print("提示: 请尝试在项目根目录执行 'pip install -e ag2-wrapper'")
        return 1
        
    executor = None # 初始化 executor 变量
    try:
        # 确保能找到AG2模块
        sys.path.insert(0, base_dir)
        
        # 确定交互模式
        mode_desc = "真人输入" if use_human_input else "LLM驱动"
        print(f"正在初始化AG2对话执行器... (模式: {mode_desc})")
        
        # 确保日志目录存在
        os.makedirs(args.logs_dir, exist_ok=True)
        
        # 使用用户指定的温度参数创建配置
        from ag2_wrapper.core.config import ConfigManager
        config = ConfigManager()
        config.set_config('temperature', args.temperature)
        
        # 打印温度参数
        print(f"使用温度参数: {args.temperature}")
        
        # 添加更多配置信息
        print("开始设置MCP配置...")
        from ag2_wrapper.agent_tools.MCPTool.config import list_servers
        available_servers = list_servers()
        print(f"发现MCP服务器配置: {list(available_servers.keys()) if available_servers else '无'}")
        
        # --- 移除调试块：单独测试 MCP 连接和 list_tools ---
        # if 'time' in available_servers:
        #     ...
        # else:
        #     ...
        # --- 调试结束 ---

        # 创建AG2执行器实例，根据模式设置use_human_input参数
        print("开始创建AG2执行器...")
        executor = await AG2TwoAgentExecutor.create(
            config=config,
            use_human_input=use_human_input
        )
        print("AG2执行器创建完成")
        
        # 获取 Agent 实例 (假设 executor 结构)
        user_proxy = executor.executor
        assistant = executor.assistant

        # 定义助手回复处理函数 (保持同步，因为它只处理结果)
        def process_and_print_response(chat_result):
            """处理AG2返回结果并打印到控制台"""
            if not chat_result:
                 print("(无返回结果)")
                 return

            # 尝试获取最后一条助手消息
            if hasattr(chat_result, 'chat_history') and chat_result.chat_history:
                assistant_message = None
                # 获取最后一条来自助手或其代理的消息
                last_message = chat_result.chat_history[-1]
                # 根据角色或名称判断是否是助手的回复
                # 注意: 可能需要根据实际的Agent名称调整
                # if last_message.get('role') == 'assistant' or last_message.get('name') in ['助手代理', '任务助手', 'task_assistant', '助手']:
                if last_message.get('role') != 'user': # 简化：非用户的最后一条消息视为助手回复
                     content = last_message.get('content')
                     if isinstance(content, str):
                         assistant_message = content
                     elif isinstance(content, list): # 处理 tool_calls 的情况
                         # 尝试提取文本或调用信息
                         texts = [item.get('text') for item in content if isinstance(item, dict) and 'text' in item]
                         calls = [f"调用: {item['function']['name']}({item['function']['arguments']})" for item in content if isinstance(item, dict) and 'function' in item]
                         if texts:
                             assistant_message = "\n".join(texts)
                         elif calls:
                              assistant_message = "\n".join(calls)
                         else:
                             assistant_message = str(content) # 回退到字符串表示
                     else:
                         assistant_message = str(content) # 其他类型转为字符串

                if assistant_message:
                    print("\n" + assistant_message)
                else:
                    # 如果最后一条是用户的，可能表示Agent没有回复或者正在等待工具调用
                    if chat_result.summary:
                        print(f"\n(对话总结: {chat_result.summary})")
                    else:
                        print("(Agent无新回复)")
            elif hasattr(chat_result, 'summary'):
                 print(f"(对话总结: {chat_result.summary})")
            else:
                print("(无法获取对话历史或总结)")

        # 如果提供了初始提示，发送它
        if args.prompt:
            print("\n" + "-" * 40)
            print(f"发送初始提示: {args.prompt}")
            print("-" * 40)
            
            # 使用异步方法
            chat_result = await user_proxy.a_initiate_chat(
                assistant,
                message=args.prompt,
                # clear_history=True # 默认 initiate 会清理
            )
            process_and_print_response(chat_result)
        
        # --- 不再需要手动交互循环 --- 
        # AutoGen 的 UserProxyAgent 在 human_input_mode='ALWAYS' 时会自行处理用户输入
        print("\n" + "=" * 60)
        print(f"AG2对话模式已启动 ({mode_desc}模式)。UserProxyAgent 将处理输入。输入 'exit' 或 'quit' 退出对话。")
        print("=" * 60)

        # 如果没有初始提示，也需要启动对话让 UserProxyAgent 等待第一次输入
        if not args.prompt:
            # 发起一个空的对话，让 UserProxyAgent 进入等待状态
            # 注意：这里可能需要根据 UserProxyAgent 的具体行为调整
            # 尝试直接 initiate chat，它应该会要求输入
             await user_proxy.a_initiate_chat(
                 assistant,
                 message=None # 或者一个默认的开场白？
             )
        else:
             # 如果有初始提示， initiate_chat 已经调用过了，后续由 AutoGen 处理
             pass

        # --- 手动循环和 a_send 已移除 ---
        
        # 等待 AutoGen 对话自然结束 (用户输入 exit)
        # 这里不需要额外的代码，a_initiate_chat 会阻塞直到对话结束
        print(f"\nAG2对话模式 ({mode_desc}) 已结束。")
            
    except ImportError as e:
        print(f"Error: 无法导入必要的模块: {e}")
        return 1
    except Exception as e: # 添加顶层异常捕获
         print(f"初始化或执行过程中发生严重错误: {e}")
         logger.error(f"handle_ag2_chat 失败: {e}", exc_info=True)
         return 1
    finally:
         # 确保 executor 和可能的 MCP 连接被清理
         if executor and hasattr(executor, 'close') and callable(getattr(executor, 'close')):
              try:
                   logger.info("Calling executor.close()...")
                   await executor.close() # 调用 AG2TwoAgentExecutor 的 close 方法
                   print("AG2 Executor 资源已清理。")
              except Exception as close_e:
                   logger.error(f"调用 executor.close() 时出错: {close_e}", exc_info=True)
         else:
            logger.warning("Executor 不存在或没有可调用的 close 方法，跳过显式清理。")
         # print("资源清理已跳过 (AG2TwoAgentExecutor 需要实现 close 方法)。") # 移除旧的占位符消息

# 配置日志 - 临时设置为INFO级别用于调试
logging.basicConfig(
    level=logging.INFO,  # 显示INFO级别及以上的日志
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 特别设置autogen.oai.client的日志级别
logging.getLogger("autogen.oai.client").setLevel(logging.INFO)
logger = logging.getLogger('task_planner_cli')

# 这个函数用于动态导入模块
def import_module_from_path(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def main():
    parser = argparse.ArgumentParser(
        description='任务拆分与执行系统CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例用法:
  # 执行单个任务
  task-planner execute "设计一个Python Web应用程序"
  task-planner execute -f task_description.txt --logs-dir my_logs
  
  # 仅进行任务规划拆分
  task-planner plan "开发一个数据分析流程" 
  task-planner plan -f complex_task.txt --output custom_output
  
  # 执行已拆分的子任务
  task-planner run-subtasks -f subtasks.json
  
  # 启动交互式对话模式（与真人交互）
  task-planner chat
  task-planner chat --prompt "帮我分析当前项目结构"
  
  # 启动自动化对话模式（LLM驱动模式）
  task-planner agent
  task-planner agent --prompt "帮我分析当前项目结构"
  
  # 运行分布式任务系统
  task-planner distributed --mode master --api-port 5000 --task "创建一个博客系统"
  task-planner distributed --mode worker --api-port 5001
  
  # 运行可视化服务器
  task-planner visualization --port 8080 --api-url http://localhost:5000
'''
    )
    # 添加全局日志级别选项
    parser.add_argument(
        '--log-level', 
        default='ERROR', # <-- 修改默认级别为 ERROR
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help='设置日志级别 (默认: ERROR)'
    )
    subparsers = parser.add_subparsers(dest='command', help='要运行的命令')
    
    # API服务器命令
    api_parser = subparsers.add_parser('api', 
        help='运行任务API服务器',
        description='运行任务API服务器，提供HTTP接口访问任务系统功能',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  # 在默认端口(9000)运行API服务器
  task-planner api
  
  # 在指定端口运行API服务器
  task-planner api --port 8000
  
  # 指定日志目录
  task-planner api --port 8000 --logs-dir custom_logs
'''
    )
    api_parser.add_argument('--port', type=int, default=9000,
                           help='API服务端口号(默认: 9000)')
    api_parser.add_argument('--logs-dir', default='logs',
                           help='日志目录(默认: logs)')
    
    # 可视化服务器命令
    viz_parser = subparsers.add_parser('visualization', 
        help='运行可视化服务器',
        description='运行任务可视化Web服务器，用于展示任务执行状态和结果',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  # 在8080端口运行可视化服务器，连接到本地API
  task-planner visualization --port 8080 --api-url http://localhost:5000
  
  # 连接到远程API服务
  task-planner visualization --port 8080 --api-url http://192.168.1.100:5000
'''
    )
    viz_parser.add_argument('--port', type=int, required=True,
                           help='Web服务器端口号')
    viz_parser.add_argument('--api-url', type=str, required=True,
                           help='任务API服务URL地址')
                           
    # 交互式对话命令 - 与真人交互
    chat_parser = subparsers.add_parser('chat',
        help='开始与AG2执行器的交互式对话（真人输入模式）',
        description='启动交互式对话模式，与AG2执行器直接交互，使用真人输入',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  # 启动交互式对话（真人输入模式）
  task-planner chat
  
  # 指定初始提示
  task-planner chat --prompt "帮我分析当前目录的Python代码"
  
  # 设置模型参数
  task-planner chat --temperature 0.7
'''
    )
    chat_parser.add_argument('--prompt', type=str,
                           help='对话的初始提示(可选)')
    chat_parser.add_argument('--temperature', type=float, default=0.1,
                           help='生成文本的随机性(0.0-1.0，默认0.1)')
    chat_parser.add_argument('--logs-dir', help='日志保存目录(默认: logs)', 
                           default='logs')
    
    # 自动化代理对话命令 - 使用LLM驱动的代理
    agent_parser = subparsers.add_parser('agent',
        help='开始与AG2执行器的自动化对话（LLM驱动模式）',
        description='启动自动化对话模式，与AG2执行器交互，使用LLM驱动的用户代理',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  # 启动自动化对话（LLM驱动模式）
  task-planner agent
  
  # 指定初始提示
  task-planner agent --prompt "帮我分析当前目录的Python代码"
  
  # 设置模型参数
  task-planner agent --temperature 0.7
'''
    )
    agent_parser.add_argument('--prompt', type=str,
                           help='对话的初始提示(可选)')
    agent_parser.add_argument('--temperature', type=float, default=0.1,
                           help='生成文本的随机性(0.0-1.0，默认0.1)')
    agent_parser.add_argument('--logs-dir', help='日志保存目录(默认: logs)', 
                           default='logs')
    
    # 单个任务执行命令
    task_parser = subparsers.add_parser('execute', 
        help='执行单个任务',
        description='执行单个复杂任务，包括任务分析、拆分和执行',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  # 直接输入任务描述
  task-planner execute "设计一个Python Web应用程序"
  
  # 从文件读取任务描述
  task-planner execute -f task_description.txt
  
  # 指定自定义日志目录
  task-planner execute "创建数据分析报告" --logs-dir my_project_logs
  
  # 从文件读取任务并指定日志目录
  task-planner execute -f complex_task.txt --logs-dir custom_logs
  
  # 使用Claude执行器而不是默认的AG2
  task-planner execute "创建数据分析报告" --use-claude
'''
    )
    task_parser.add_argument('task', nargs='?', 
                            help='任务描述文本(如不提供，将提示输入)')
    task_parser.add_argument('-f', '--file', 
                            help='任务描述文件路径，从文件读取任务内容')
    task_parser.add_argument('--logs-dir', help='日志保存目录(默认: logs)', 
                            default='logs')
    task_parser.add_argument('--use-claude', action='store_true',
                            help='使用Claude作为执行器(默认使用AG2)')
    
    # 任务规划命令
    plan_parser = subparsers.add_parser('plan', 
        help='仅规划任务分解',
        description='进行任务分析和拆分，但不执行任务',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  # 直接输入任务描述进行规划
  task-planner plan "开发一个数据分析流程"
  
  # 从文件读取任务描述
  task-planner plan -f complex_task.txt
  
  # 指定自定义输出目录
  task-planner plan "设计一个电子商务网站" --output ecommerce_plan
  
  # 规划结果将保存为两个JSON文件:
  # - task_analysis.json: 包含任务的综合分析
  # - task_breakdown.json: 包含拆分后的子任务列表
'''
    )
    plan_parser.add_argument('task', nargs='?', 
                            help='任务描述文本(如不提供，将提示输入)')
    plan_parser.add_argument('-f', '--file', 
                            help='任务描述文件路径，从文件读取任务内容')
    plan_parser.add_argument('--output', help='结果输出目录(默认: output)', 
                            default='output')
    
    # 执行预定义子任务命令
    subtasks_parser = subparsers.add_parser('run-subtasks',
        help='执行子任务列表',
        description='执行已分解的子任务列表',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  # 执行子任务文件中的所有任务
  task-planner run-subtasks subtasks.json
  
  # 指定自定义日志目录
  task-planner run-subtasks subtasks.json --logs-dir my_subtasks_logs
  
  # 使用Claude执行器而不是默认的AG2
  task-planner run-subtasks subtasks.json --use-claude
'''
    )
    subtasks_parser.add_argument('subtasks_file',
                                help='包含子任务列表的JSON文件路径')
    subtasks_parser.add_argument('--logs-dir', help='日志保存目录(默认: logs)',
                                default='logs')
    subtasks_parser.add_argument('--use-claude', action='store_true',
                                help='使用Claude作为执行器(默认使用AG2)')
    subtasks_parser.add_argument('--start-from', 
                                help='指定从哪个子任务ID开始执行',
                                default=None)
    
    args = parser.parse_args()
    
    # 设置日志级别
    log_level = getattr(logging, args.log_level.upper(), logging.ERROR) # <-- 默认使用 ERROR
    logging.getLogger().setLevel(log_level)
    # 对特定模块设置更高级别日志，减少干扰 (确保至少为 ERROR)
    logging.getLogger("autogen.oai.client").setLevel(max(log_level, logging.ERROR))
    logging.getLogger("autogen.agentchat.agent").setLevel(max(log_level, logging.ERROR))
    # UserProxyAgent 的 INFO 可能包含输入提示，也设为 ERROR
    logging.getLogger("autogen.agentchat.user_proxy_agent").setLevel(max(log_level, logging.ERROR)) 
    # 抑制函数工具警告
    logging.getLogger("autogen.tools.function_utils").setLevel(logging.ERROR) 
    # 抑制 MCPClient_SDK 的 INFO 和 WARNING (如果需要更干净的输出)
    logging.getLogger("MCPClient_SDK").setLevel(logging.ERROR)
    # 抑制我们自己的 AG2 Wrapper 的 INFO 和 WARNING
    logging.getLogger("ag2_wrapper").setLevel(max(log_level, logging.ERROR)) 
    # task_planner 本身的日志级别由全局控制
    logger.info(f"设置全局日志级别为: {args.log_level.upper()}") # 这条 info 可能不会显示了

    # 获取项目根目录 (上一级目录)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    if args.command == 'api':
        # 导入API服务器模块
        sys.path.insert(0, base_dir)
        from task_planner.server.task_api_server import app

        # 确保日志目录存在
        os.makedirs(args.logs_dir, exist_ok=True)
        
        # 启动API服务器
        print(f"启动任务API服务器，端口: {args.port}")
        app.run(host='0.0.0.0', port=args.port)
            
    elif args.command == 'visualization':
        # 动态导入模块
        module_path = os.path.join(base_dir, 'src', 'server', 'task_visualization_server.py')
        viz_module = import_module_from_path('visualization', module_path)
        
        # 重构命令行参数
        sys.argv = [sys.argv[0]]
        for k, v in vars(args).items():
            if k not in ['command'] and v is not None:
                if isinstance(v, bool):
                    if v:
                        sys.argv.append(f'--{k}')
                else:
                    sys.argv.append(f'--{k}')
                    sys.argv.append(str(v))
                    
        # 调用原始模块的main函数
        if hasattr(viz_module, 'main'):
            viz_module.main()
        else:
            print("Error: 找不到可视化服务器模块的main函数")
    
    elif args.command == 'execute':
        try:
            # 动态导入TaskDecompositionSystem
            sys.path.insert(0, base_dir)
            from task_planner.core.task_decomposition_system import TaskDecompositionSystem
            
            # 获取任务文本
            task_text = ""
            if args.file:
                with open(args.file, 'r', encoding='utf-8') as f:
                    task_text = f.read()
            elif args.task:
                task_text = args.task
            else:
                task_text = input("请输入任务描述: ")
                
            # 创建日志目录
            os.makedirs(args.logs_dir, exist_ok=True)
            
            # 初始化任务拆分系统
            system = TaskDecompositionSystem(
                logs_dir=args.logs_dir,
                use_claude=args.use_claude
            )
            
            # 执行任务
            print(f"开始执行任务...\n{'-'*40}\n{task_text}\n{'-'*40}")
            print(f"使用{'Claude' if args.use_claude else 'AG2'}执行器")
            start_time = time.time()
            
            result = system.execute_complex_task(task_text)
            
            # 显示结果
            execution_time = time.time() - start_time
            print(f"\n任务执行完成，总耗时: {execution_time:.2f}秒")
            
            success = result.get('success', False)
            status = "成功" if success else "失败"
            print(f"任务状态: {status}")
            
            if 'result' in result and 'summary' in result['result']:
                print("\n结果摘要:")
                print("-" * 40)
                print(result['result']['summary'])
                print("-" * 40)
            
            # 显示任务拆分情况
            if 'result' in result and 'details' in result['result'] and 'subtasks' in result['result']['details']:
                subtasks = result['result']['details']['subtasks']
                print("\n任务拆分:")
                print("-" * 40)
                for i, subtask in enumerate(subtasks):
                    status = "成功" if subtask.get('success', False) else "失败"
                    print(f"{i+1}. {subtask.get('name', f'子任务 {i+1}')} - {status}")
                print("-" * 40)
            
            # 显示结果保存位置
            task_id = result.get('task_id', f"task_{int(time.time())}")
            result_dir = os.path.join(args.logs_dir, task_id)
            if os.path.exists(result_dir):
                print(f"\n结果已保存到: {result_dir}")
        
        except ImportError as e:
            print(f"Error: 无法导入必要的模块: {e}")
    
    elif args.command == 'plan':
        try:
            # 动态导入TaskPlanner
            sys.path.insert(0, base_dir)
            from task_planner.core.task_planner import TaskPlanner
            from task_planner.core.context_management import ContextManager
            import json
            
            # 获取任务文本
            task_text = ""
            if args.file:
                with open(args.file, 'r', encoding='utf-8') as f:
                    task_text = f.read()
            elif args.task:
                task_text = args.task
            else:
                task_text = input("请输入任务描述: ")
            
            # 创建输出目录
            os.makedirs(args.output, exist_ok=True)
            
            # 初始化上下文管理器
            context_manager = ContextManager()
            
            # 创建规划器实例
            planner = TaskPlanner(task_text, context_manager=context_manager)
            
            # 执行任务分析
            print("\n===== 任务分析中... =====")
            analysis = planner.analyze_task()
            
            # 执行任务拆分
            print("\n===== 任务拆分中... =====")
            subtasks = planner.break_down_task(analysis)
            
            # 显示拆分结果
            for i, subtask in enumerate(subtasks):
                print(f"\n子任务 {i+1}:")
                print(f"  名称: {subtask['name']}")
                print(f"  描述: {subtask['description']}")
                print(f"  优先级: {subtask.get('priority', 'normal')}")
                if 'dependencies' in subtask and subtask['dependencies']:
                    print(f"  依赖: {', '.join(subtask['dependencies'])}")
            
            # 保存结果到文件
            with open(os.path.join(args.output, "task_analysis.json"), "w", encoding="utf-8") as f:
                json.dump(analysis, f, indent=2, ensure_ascii=False)
            
            with open(os.path.join(args.output, "task_breakdown.json"), "w", encoding="utf-8") as f:
                json.dump(subtasks, f, indent=2, ensure_ascii=False)
            
            print("\n分析和拆分结果已保存到:")
            print(f"- {os.path.join(args.output, 'task_analysis.json')}")
            print(f"- {os.path.join(args.output, 'task_breakdown.json')}")
            
        except ImportError as e:
            print(f"Error: 无法导入必要的模块: {e}")
    
    elif args.command == 'run-subtasks':
        try:
            # 动态导入需要的模块
            sys.path.insert(0, base_dir)
            from task_planner.core.task_decomposition_system import TaskDecompositionSystem
            import json
            
            # 读取子任务文件
            with open(args.subtasks_file, 'r', encoding='utf-8') as f:
                subtasks = json.load(f)
                
            # 如果指定了起始任务
            if args.start_from:
                # 找到起始任务的索引
                start_index = next((i for i, task in enumerate(subtasks) 
                                  if task['id'] == args.start_from), None)
                if start_index is None:
                    logger.error(f"找不到指定的起始任务ID: {args.start_from}")
                    return 1
                # 只执行从该任务开始的子任务
                subtasks = subtasks[start_index:]
                logger.info(f"从任务 {args.start_from} 开始执行，共 {len(subtasks)} 个任务")
            
            # 执行子任务
            system = TaskDecompositionSystem(
                logs_dir=args.logs_dir,
                use_claude=args.use_claude
            )
            final_result = system.execute_predefined_subtasks(subtasks)
            
            # 输出结果摘要
            print("\n执行结果摘要:")
            print(f"总子任务数: {len(subtasks)}")
            print(f"成功: {final_result['success_count']}")
            print(f"失败: {final_result['failure_count']}")
            print(f"最终状态: {'成功' if final_result['success'] else '失败'}")
            
            return 0
            
        except Exception as e:
            logger.error(f"子任务执行失败: {str(e)}")
            return 1
    
    # 处理chat命令（真人输入模式）
    elif args.command == 'chat':
        return asyncio.run(handle_ag2_chat('chat', args, use_human_input=True, base_dir=base_dir))
            
    # 处理agent命令（LLM驱动模式）
    elif args.command == 'agent':
        return asyncio.run(handle_ag2_chat('agent', args, use_human_input=False, base_dir=base_dir))
            
    else:
        parser.print_help()
        
    return 0 # 默认成功退出

if __name__ == '__main__':
    sys.exit(main())