import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from data_preprocessing import preprocess_data
import json
from datetime import datetime

# 设置matplotlib中文显示
plt.rcParams['font.sans-serif'] = ['SimHei']  # 指定默认字体
plt.rcParams['axes.unicode_minus'] = False    # 解决保存图像是负号'-'显示为方块的问题

def format_currency(value):
    """将数值格式化为货币形式"""
    return f"¥{value:,.2f}"

def calculate_basic_statistics(df):
    """计算基本统计指标"""
    print("正在计算基本统计指标...")
    
    # 1. 总销售额、平均订单金额
    total_sales = df['sales_amount'].sum()
    average_order = df['sales_amount'].mean()
    
    # 2. 各产品类别的销售占比
    category_sales = df.groupby('category')['sales_amount'].sum().sort_values(ascending=False)
    category_percentage = (category_sales / total_sales * 100).round(2)
    
    # 3. 不同区域的销售表现
    region_sales = df.groupby('region')['sales_amount'].sum().sort_values(ascending=False)
    region_percentage = (region_sales / total_sales * 100).round(2)
    
    basic_stats = {
        "total_sales": total_sales,
        "average_order": average_order,
        "category_sales": category_sales.to_dict(),
        "category_percentage": category_percentage.to_dict(),
        "region_sales": region_sales.to_dict(),
        "region_percentage": region_percentage.to_dict()
    }
    
    return basic_stats

def time_dimension_analysis(df):
    """时间维度分析"""
    print("正在进行时间维度分析...")
    
    # 确保日期列是日期时间类型
    df['date'] = pd.to_datetime(df['date'])
    
    # 1. 按月度的销售趋势
    monthly_sales = df.groupby(df['date'].dt.to_period('M'))['sales_amount'].sum()
    monthly_sales.index = monthly_sales.index.astype(str)
    
    # 2. 按季度的销售趋势
    df['quarter'] = df['date'].dt.to_period('Q')
    quarterly_sales = df.groupby('quarter')['sales_amount'].sum()
    quarterly_sales.index = quarterly_sales.index.astype(str)
    
    # 3. 按年度的销售趋势 (如果数据跨越多年)
    yearly_sales = df.groupby(df['date'].dt.year)['sales_amount'].sum()
    
    # 4. 计算环比增长率
    mom_growth = monthly_sales.pct_change() * 100
    
    # 5. 按工作日与周末的销售对比
    weekday_vs_weekend = df.groupby('is_weekend')['sales_amount'].sum()
    
    # 6. 按周几的销售分布
    day_of_week_sales = df.groupby('day_of_week')['sales_amount'].sum()
    day_names = {0: '周一', 1: '周二', 2: '周三', 3: '周四', 4: '周五', 5: '周六', 6: '周日'}
    day_of_week_sales.index = [day_names[day] for day in day_of_week_sales.index]
    
    time_analysis = {
        "monthly_sales": monthly_sales.to_dict(),
        "quarterly_sales": quarterly_sales.to_dict(),
        "yearly_sales": yearly_sales.to_dict(),
        "mom_growth": mom_growth.dropna().to_dict(),  # 去掉第一个月的NaN
        "weekday_vs_weekend": weekday_vs_weekend.to_dict(),
        "day_of_week_sales": day_of_week_sales.to_dict()
    }
    
    return time_analysis

def product_region_analysis(df):
    """产品与区域分析"""
    print("正在进行产品与区域分析...")
    
    # 1. 产品分析
    # 按产品销售额排序
    product_sales = df.groupby('product_name')['sales_amount'].sum().sort_values(ascending=False)
    top_products = product_sales.head(5)
    bottom_products = product_sales.tail(5)
    
    # 按产品销售量排序
    product_quantity = df.groupby('product_name')['sales_quantity'].sum().sort_values(ascending=False)
    
    # 2. 区域分析
    # 按区域和产品类别的交叉分析
    region_category = df.pivot_table(
        values='sales_amount', 
        index='region', 
        columns='category', 
        aggfunc='sum',
        fill_value=0
    ).to_dict()
    
    # 3. 产品组合分析 - 找出经常一起出现的产品类别
    # 简化：按区域查看每个类别的销售额占比
    category_by_region = {}
    for region in df['region'].unique():
        region_data = df[df['region'] == region]
        total_region_sales = region_data['sales_amount'].sum()
        category_sales = region_data.groupby('category')['sales_amount'].sum()
        category_percentage = (category_sales / total_region_sales * 100).round(2)
        category_by_region[region] = category_percentage.to_dict()
    
    product_analysis = {
        "top_products": top_products.to_dict(),
        "bottom_products": bottom_products.to_dict(),
        "product_quantity": product_quantity.head(10).to_dict(),
        "region_category_sales": region_category,
        "category_by_region": category_by_region
    }
    
    return product_analysis

def create_visualizations(df, basic_stats, time_analysis, product_analysis):
    """创建数据可视化"""
    print("正在创建数据可视化...")
    
    # 创建保存图表的目录
    import os
    if not os.path.exists('output/figures'):
        os.makedirs('output/figures')
    
    # 设置图表风格
    sns.set(style="whitegrid")
    plt.figure(figsize=(15, 10))
    
    # 1. 类别销售额占比饼图
    plt.figure(figsize=(10, 6))
    plt.pie(
        list(basic_stats['category_percentage'].values()),
        labels=list(basic_stats['category_percentage'].keys()),
        autopct='%1.1f%%',
        startangle=90,
        shadow=True
    )
    plt.title('各产品类别销售占比')
    plt.axis('equal')  # 确保饼图是圆的
    plt.tight_layout()
    plt.savefig('output/figures/category_sales_pie.png')
    plt.close()
    
    # 2. 区域销售额柱状图
    plt.figure(figsize=(10, 6))
    regions = list(basic_stats['region_sales'].keys())
    sales = list(basic_stats['region_sales'].values())
    plt.bar(regions, sales, color=sns.color_palette("viridis", len(regions)))
    plt.title('各区域销售额')
    plt.xlabel('区域')
    plt.ylabel('销售额')
    plt.tight_layout()
    plt.savefig('output/figures/region_sales_bar.png')
    plt.close()
    
    # 3. 月度销售趋势线图
    plt.figure(figsize=(12, 6))
    months = list(time_analysis['monthly_sales'].keys())
    values = list(time_analysis['monthly_sales'].values())
    plt.plot(months, values, marker='o', linestyle='-')
    plt.title('月度销售趋势')
    plt.xlabel('月份')
    plt.ylabel('销售额')
    plt.xticks(rotation=45)
    plt.grid(True)
    plt.tight_layout()
    plt.savefig('output/figures/monthly_sales_trend.png')
    plt.close()
    
    # 4. 环比增长率柱状图
    plt.figure(figsize=(12, 6))
    months = list(time_analysis['mom_growth'].keys())
    growth_rates = list(time_analysis['mom_growth'].values())
    colors = ['green' if x >= 0 else 'red' for x in growth_rates]
    plt.bar(months, growth_rates, color=colors)
    plt.title('月度销售环比增长率')
    plt.xlabel('月份')
    plt.ylabel('增长率 (%)')
    plt.xticks(rotation=45)
    plt.axhline(y=0, color='black', linestyle='-', alpha=0.3)
    plt.grid(True)
    plt.tight_layout()
    plt.savefig('output/figures/mom_growth_rate.png')
    plt.close()
    
    # 5. 周几销售分布柱状图
    plt.figure(figsize=(10, 6))
    days = list(time_analysis['day_of_week_sales'].keys())
    day_sales = list(time_analysis['day_of_week_sales'].values())
    plt.bar(days, day_sales, color=sns.color_palette("Set2", len(days)))
    plt.title('各工作日销售额分布')
    plt.xlabel('星期')
    plt.ylabel('销售额')
    plt.tight_layout()
    plt.savefig('output/figures/day_of_week_sales.png')
    plt.close()
    
    # 6. 最畅销产品柱状图
    plt.figure(figsize=(12, 6))
    top_prod = list(product_analysis['top_products'].keys())
    top_sales = list(product_analysis['top_products'].values())
    plt.barh(top_prod, top_sales, color=sns.color_palette("Reds_r", len(top_prod)))
    plt.title('销售额最高的产品')
    plt.xlabel('销售额')
    plt.ylabel('产品名称')
    plt.tight_layout()
    plt.savefig('output/figures/top_products.png')
    plt.close()
    
    # 7. 热力图：区域-类别销售关系
    # 转换字典为DataFrame
    region_category_df = pd.DataFrame(product_analysis['region_category_sales'])
    
    plt.figure(figsize=(12, 8))
    sns.heatmap(region_category_df, annot=True, fmt=".0f", cmap="YlGnBu")
    plt.title('区域-产品类别销售额热力图')
    plt.tight_layout()
    plt.savefig('output/figures/region_category_heatmap.png')
    plt.close()
    
    return {
        "category_sales_pie": "output/figures/category_sales_pie.png",
        "region_sales_bar": "output/figures/region_sales_bar.png",
        "monthly_sales_trend": "output/figures/monthly_sales_trend.png",
        "mom_growth_rate": "output/figures/mom_growth_rate.png",
        "day_of_week_sales": "output/figures/day_of_week_sales.png",
        "top_products": "output/figures/top_products.png",
        "region_category_heatmap": "output/figures/region_category_heatmap.png",
    }

def extract_insights(basic_stats, time_analysis, product_analysis):
    """提取关键洞察和业务建议"""
    
    # 获取最畅销和最不畅销的产品
    top_product = list(product_analysis['top_products'].keys())[0]
    bottom_product = list(product_analysis['bottom_products'].keys())[0]
    
    # 获取销售最高和最低的区域
    top_region = list(basic_stats['region_sales'].keys())[0]
    bottom_region = list(basic_stats['region_sales'].keys())[-1]
    
    # 获取最畅销的产品类别
    top_category = list(basic_stats['category_sales'].keys())[0]
    
    # 获取销售增长最高的月份
    if time_analysis['mom_growth']:
        mom_growth_values = list(time_analysis['mom_growth'].values())
        mom_growth_months = list(time_analysis['mom_growth'].keys())
        highest_growth_month = mom_growth_months[mom_growth_values.index(max(mom_growth_values))]
        highest_growth_rate = max(mom_growth_values)
    else:
        highest_growth_month = "N/A"
        highest_growth_rate = 0
    
    # 确定周末和工作日的销售情况
    weekday_sales = time_analysis['weekday_vs_weekend'].get(0, 0)
    weekend_sales = time_analysis['weekday_vs_weekend'].get(1, 0)
    weekend_weekday_ratio = weekend_sales / weekday_sales if weekday_sales > 0 else 0
    
    insights = [
        f"最畅销产品是 {top_product}，贡献了显著销售额，应考虑增加库存和促销力度。",
        f"销售额最高的区域是 {top_region}，应深入研究其成功因素并复制到其他区域。",
        f"销售额最低的区域是 {bottom_region}，需要分析原因并采取针对性措施提升销售。",
        f"产品类别中，{top_category} 表现最佳，占总销售额的 {basic_stats['category_percentage'][top_category]}%。",
        f"最不畅销的产品是 {bottom_product}，需要评估是否调整定价或停止销售。"
    ]
    
    if highest_growth_month != "N/A":
        insights.append(f"{highest_growth_month} 销售增长最快，环比增长 {highest_growth_rate:.2f}%，应分析增长原因。")
    
    if weekend_weekday_ratio > 1.2:
        insights.append("周末销售明显高于工作日，可考虑在周末加大促销力度。")
    elif weekend_weekday_ratio < 0.8:
        insights.append("工作日销售明显高于周末，应重点关注工作日的客户体验和服务。")
    
    # 提取不同区域产品类别偏好
    region_category_insights = []
    for region, categories in product_analysis['category_by_region'].items():
        top_category_in_region = max(categories, key=categories.get)
        region_category_insights.append(f"{region} 区域最受欢迎的产品类别是 {top_category_in_region}，占该区域销售的 {categories[top_category_in_region]:.2f}%。")
    
    insights.extend(region_category_insights)
    
    # 业务行动建议
    recommendations = [
        f"优化库存管理：增加 {top_product} 和 {top_category} 类别的库存，减少 {bottom_product} 的库存。",
        f"区域策略调整：分析 {top_region} 的成功经验，在 {bottom_region} 实施针对性的销售策略。",
        "产品组合优化：根据各区域的产品类别偏好，调整各区域的产品组合和促销策略。",
        "时间营销策略：根据日/周/月销售模式，在销售高峰期增加营销力度，淡季推出特别促销活动。",
        "客户细分：深入分析不同区域、不同时间的客户群体特征，实施精准营销。"
    ]
    
    return {
        "key_insights": insights,
        "recommendations": recommendations
    }

def format_output(basic_stats, time_analysis, product_analysis, visualizations, insights_recommendations):
    """格式化输出结果为规定的JSON结构"""
    
    # 格式化货币数值
    formatted_total_sales = format_currency(basic_stats['total_sales'])
    formatted_average_order = format_currency(basic_stats['average_order'])
    
    # 构建详细分析结果
    analysis_details = {
        "basic_statistics": {
            "total_sales": formatted_total_sales,
            "average_order": formatted_average_order,
            "category_sales_percentage": basic_stats['category_percentage'],
            "region_sales_percentage": basic_stats['region_percentage']
        },
        "time_analysis": {
            "monthly_trend": time_analysis['monthly_sales'],
            "quarterly_trend": time_analysis['quarterly_sales'],
            "mom_growth": time_analysis['mom_growth'],
            "day_of_week_distribution": time_analysis['day_of_week_sales']
        },
        "product_region_analysis": {
            "top_products": {k: format_currency(v) for k, v in product_analysis['top_products'].items()},
            "bottom_products": {k: format_currency(v) for k, v in product_analysis['bottom_products'].items()},
            "category_by_region": product_analysis['category_by_region']
        }
    }
    
    # 构建完整输出
    output = {
        "task_id": "SALES_ANALYSIS_001",
        "success": True,
        "result": {
            "summary": "成功完成销售数据分析，包括基本统计、时间维度分析和产品与区域分析",
            "details": analysis_details
        },
        "artifacts": {
            "visualizations": visualizations,
            "key_insights": insights_recommendations['key_insights'],
            "recommendations": insights_recommendations['recommendations']
        },
        "next_steps": [
            "实施推荐的业务优化策略",
            "建立销售预测模型",
            "开展详细的客户细分分析",
            "制定基于分析结果的营销计划"
        ]
    }
    
    return output

def run_sales_analysis():
    """运行完整的销售分析流程"""
    
    # 1. 获取预处理后的数据
    preprocessing_results = preprocess_data()
    df = preprocessing_results["transformed_data"]
    
    # 2. 计算基本统计指标
    basic_stats = calculate_basic_statistics(df)
    
    # 3. 进行时间维度分析
    time_analysis = time_dimension_analysis(df)
    
    # 4. 进行产品与区域分析
    product_analysis = product_region_analysis(df)
    
    # 5. 创建数据可视化
    visualizations = create_visualizations(df, basic_stats, time_analysis, product_analysis)
    
    # 6. 提取洞察和建议
    insights_recommendations = extract_insights(basic_stats, time_analysis, product_analysis)
    
    # 7. 格式化输出结果
    output = format_output(basic_stats, time_analysis, product_analysis, visualizations, insights_recommendations)
    
    return output

if __name__ == "__main__":
    # 确保输出目录存在
    import os
    if not os.path.exists('output'):
        os.makedirs('output')
    
    # 运行分析并获取结果
    output = run_sales_analysis()
    
    # 保存结果到JSON文件
    with open('output/sales_analysis_results.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    # 打印最终结果
    print(json.dumps(output, ensure_ascii=False, indent=2))