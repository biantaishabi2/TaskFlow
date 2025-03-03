#!/usr/bin/env python3
# 示例程序：展示如何在Python程序中使用Claude命令行

# 导入Claude API
from claude_cli import claude_api

def main():
    print("Claude API调用示例程序")
    
    # 示例1：简单查询
    question = "请解释一下Python中的装饰器"
    print(f"\n问题: {question}")
    
    print("正在查询Claude...")
    response = claude_api(question)
    
    print("\n回答:")
    print(response)
    
    # 示例2：代码生成
    code_request = "写一个简单的Python函数，计算斐波那契数列的第n个数"
    print(f"\n问题: {code_request}")
    
    print("正在查询Claude...")
    code_response = claude_api(code_request)
    
    print("\n回答:")
    print(code_response)
    
    # 示例3：带上下文的查询
    context = """
    我有一个电子商务网站，其数据库包含以下表：
    - users(id, name, email, password, created_at)
    - products(id, name, description, price, stock, category_id)
    - categories(id, name)
    - orders(id, user_id, status, created_at)
    - order_items(id, order_id, product_id, quantity, price)
    """
    
    db_question = f"{context}\n\n请写一个SQL查询，找出购买最多商品的前5名用户"
    print("\n问题: SQL查询问题（包含上下文信息）")
    
    print("正在查询Claude...")
    db_response = claude_api(db_question)
    
    print("\n回答:")
    print(db_response)

if __name__ == "__main__":
    main()