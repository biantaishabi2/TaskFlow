#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
任务监控器
监控input目录中的任务文件，执行任务并将结果写入output目录
适用于通过共享卷与外部程序交互的场景
"""

import os
import json
import time
import logging
import traceback
from task_planner.core.task_decomposition_system import TaskDecompositionSystem
from task_planner.distributed.parallel_task_decomposition_system import ParallelTaskDecompositionSystem

# 获取项目根目录
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# 配置目录
INPUT_DIR = os.path.join(ROOT_DIR, "input")
OUTPUT_DIR = os.path.join(ROOT_DIR, "output")
LOG_DIR = os.path.join(ROOT_DIR, "logs")

# 配置日志
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(LOG_DIR, 'task_monitor.log'))
    ]
)
logger = logging.getLogger('task_monitor')

def process_task_file(file_path):
    """处理单个任务文件"""
    logger.info(f"开始处理任务文件: {file_path}")
    
    try:
        # 读取任务文件
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 提取任务信息
        task_id = data.get('id', 'unknown')
        task = data.get('task', '')
        parallel = data.get('parallel', False)
        
        if not task:
            raise ValueError("任务描述为空")
            
        logger.info(f"任务ID: {task_id}, 并行模式: {parallel}")
        logger.info(f"任务描述: {task[:100]}...")
        
        # 选择系统类型
        if parallel:
            system = ParallelTaskDecompositionSystem()
            logger.info("使用并行任务分解系统")
        else:
            system = TaskDecompositionSystem()
            logger.info("使用标准任务分解系统")
        
        # 执行任务
        result = system.execute_complex_task(task, save_results=True)
        
        # 输出结果
        output_path = os.path.join(OUTPUT_DIR, f"result_{task_id}.json")
        with open(output_path, 'w', encoding='utf-8') as out_f:
            json.dump({
                "id": task_id,
                "status": "completed",
                "result": result
            }, out_f, ensure_ascii=False, indent=2)
        
        logger.info(f"任务 {task_id} 完成, 结果保存至 {output_path}")
        
        # 写入状态文件（用于跟踪进度）
        status_path = os.path.join(OUTPUT_DIR, f"status_{task_id}.json")
        with open(status_path, 'w', encoding='utf-8') as status_f:
            json.dump({
                "id": task_id,
                "status": "completed",
                "timestamp": time.time()
            }, status_f, ensure_ascii=False, indent=2)
        
        # 删除已处理的输入文件
        os.remove(file_path)
        logger.info(f"已删除处理完毕的任务文件: {file_path}")
        
        return True
        
    except Exception as e:
        logger.error(f"处理任务文件 {file_path} 时出错: {str(e)}")
        logger.error(traceback.format_exc())
        
        # 写入错误信息
        try:
            data = json.load(open(file_path, 'r', encoding='utf-8'))
            task_id = data.get('id', 'unknown')
            
            error_path = os.path.join(OUTPUT_DIR, f"error_{task_id}.json")
            with open(error_path, 'w', encoding='utf-8') as err_f:
                json.dump({
                    "id": task_id,
                    "status": "failed",
                    "error": str(e),
                    "traceback": traceback.format_exc()
                }, err_f, ensure_ascii=False, indent=2)
                
            # 更新状态文件
            status_path = os.path.join(OUTPUT_DIR, f"status_{task_id}.json")
            with open(status_path, 'w', encoding='utf-8') as status_f:
                json.dump({
                    "id": task_id,
                    "status": "failed",
                    "error": str(e),
                    "timestamp": time.time()
                }, status_f, ensure_ascii=False, indent=2)
                
            logger.info(f"已写入错误信息到 {error_path}")
        except Exception as inner_e:
            logger.error(f"写入错误信息时出错: {str(inner_e)}")
        
        return False

def main():
    """主函数"""
    # 确保目录存在
    os.makedirs(INPUT_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    logger.info(f"任务监控器已启动，监控目录: {INPUT_DIR}，输出目录: {OUTPUT_DIR}")
    
    while True:
        try:
            # 检查输入目录中的文件
            files = [f for f in os.listdir(INPUT_DIR) if f.endswith('.json')]
            
            if files:
                logger.info(f"发现 {len(files)} 个任务文件")
                
                for filename in files:
                    file_path = os.path.join(INPUT_DIR, filename)
                    process_task_file(file_path)
            
            # 等待一段时间再次检查
            time.sleep(5)
            
        except Exception as e:
            logger.error(f"监控循环出错: {str(e)}")
            logger.error(traceback.format_exc())
            time.sleep(30)  # 出错后等待更长时间

if __name__ == "__main__":
    main()