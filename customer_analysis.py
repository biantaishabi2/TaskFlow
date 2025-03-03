import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.cluster import KMeans
from datetime import datetime, timedelta
from data_preprocessing import preprocess_data
import json
import os

# 设置matplotlib中文显示
plt.rcParams['font.sans-serif'] = ['SimHei']  # 指定默认字体
plt.rcParams['axes.unicode_minus'] = False    # 解决保存图像是负号'-'显示为方块的问题

def create_customer_data(df):
    """基于销售数据创建客户级别数据"""
    print("正在创建客户数据...")
    
    # 为演示目的，我们假设每个订单有一个唯一的customer_id
    # 在实际项目中，这通常是从订单数据中得到的
    np.random.seed(42)
    n_customers = 50  # 假设有50个不同的客户
    
    # 创建客户ID
    customer_ids = [f'C{i:03d}' for i in range(1, n_customers + 1)]
    
    # 创建客户属性：性别、年龄、会员等级等
    genders = np.random.choice(['Male', 'Female'], size=n_customers)
    ages = np.random.randint(18, 70, size=n_customers)
    member_levels = np.random.choice(['Bronze', 'Silver', 'Gold', 'Platinum'], 
                                    size=n_customers, 
                                    p=[0.4, 0.3, 0.2, 0.1])  # 设置不同等级的概率
    
    # 为每个订单随机分配一个客户
    df_with_customers = df.copy()
    df_with_customers['customer_id'] = np.random.choice(customer_ids, size=len(df))
    
    # 构建客户信息数据框
    customers_info = pd.DataFrame({
        'customer_id': customer_ids,
        'gender': genders,
        'age': ages,
        'member_level': member_levels,
        'registration_date': [datetime(2022, 1, 1) + timedelta(days=np.random.randint(0, 365)) for _ in range(n_customers)]
    })
    
    return df_with_customers, customers_info

def calculate_customer_metrics(df_with_customers, customers_info):
    """计算客户相关指标"""
    print("正在计算客户指标...")
    
    # 聚合每个客户的购买行为
    customer_purchase = df_with_customers.groupby('customer_id').agg({
        'date': ['min', 'max', 'count'],  # 首次购买日期、最近购买日期、购买次数
        'sales_amount': ['sum', 'mean']   # 总购买金额、平均订单金额
    })
    
    # 重命名列
    customer_purchase.columns = ['first_purchase', 'last_purchase', 'frequency', 'monetary', 'avg_order_value']
    
    # 计算每个客户的购买间隔（天）
    customer_purchase['recency'] = (pd.to_datetime('2023-05-01') - customer_purchase['last_purchase']).dt.days
    
    # 计算客户生命周期（天）
    customer_purchase['customer_life_cycle'] = (customer_purchase['last_purchase'] - customer_purchase['first_purchase']).dt.days
    
    # 计算平均购买频率（次/月）
    # 避免除以零，对生命周期为0的情况特殊处理
    customer_purchase['purchase_frequency_monthly'] = np.where(
        customer_purchase['customer_life_cycle'] > 0,
        customer_purchase['frequency'] / (customer_purchase['customer_life_cycle'] / 30),
        customer_purchase['frequency']  # 如果生命周期为0，就直接用购买次数
    )
    
    # 合并客户信息
    customer_metrics = customer_purchase.reset_index().merge(
        customers_info, on='customer_id', how='left')
    
    return customer_metrics

def calculate_clv(customer_metrics, acquisition_cost=100, retention_cost_rate=0.1, discount_rate=0.1, time_horizon=24):
    """计算客户生命周期价值 (CLV)"""
    print("正在计算客户生命周期价值...")
    
    # 计算月度客户保持率 (简化模型，基于会员等级设定不同的保持率)
    retention_rates = {
        'Bronze': 0.70,
        'Silver': 0.80,
        'Gold': 0.90,
        'Platinum': 0.95
    }
    
    # 将保持率映射到客户
    customer_metrics['retention_rate'] = customer_metrics['member_level'].map(retention_rates)
    
    # 计算每个客户的预期CLV
    clv = []
    for idx, customer in customer_metrics.iterrows():
        # 处理可能的除以零或无穷大的情况
        if customer['customer_life_cycle'] > 0:
            monthly_value = customer['monetary'] / customer['customer_life_cycle'] * 30
        else:
            monthly_value = customer['monetary']  # 如果生命周期为0，直接使用总消费额作为月度值
        
        # 月度边际贡献（假设为月均消费的60%）
        margin = monthly_value * 0.6
        
        # 计算24个月内的CLV（使用有限时间视野）
        retention = customer['retention_rate']
        future_value = 0
        for t in range(1, time_horizon + 1):
            future_value += margin * (retention ** t) / ((1 + discount_rate / 12) ** t)
        
        # 总CLV = 未来价值 - 获取成本 + 已实现价值
        total_clv = future_value - acquisition_cost + customer['monetary'] * 0.6
        clv.append(total_clv)
    
    # 添加到客户指标中
    customer_metrics['clv'] = clv
    
    # 计算客户获取成本和维系成本
    acquisition_costs = pd.Series([acquisition_cost] * len(customer_metrics))
    retention_costs = customer_metrics['monetary'] * retention_cost_rate
    
    customer_metrics['acquisition_cost'] = acquisition_costs
    customer_metrics['retention_cost'] = retention_costs
    
    # 计算CLV/CAC比率（客户生命周期价值与获取成本比）
    customer_metrics['clv_cac_ratio'] = customer_metrics['clv'] / customer_metrics['acquisition_cost']
    
    return customer_metrics

def perform_rfm_analysis(customer_metrics):
    """进行RFM分析（Recency-Frequency-Monetary）"""
    print("正在进行RFM分析...")
    
    # 创建RFM指标副本
    rfm_df = customer_metrics[['customer_id', 'recency', 'frequency', 'monetary']].copy()
    
    # 将三个维度分别划分为5个等级
    # 对于Recency，值越小越好（越近）；对于Frequency和Monetary，值越大越好
    rfm_df['R_Score'] = pd.qcut(rfm_df['recency'], 5, labels=[5, 4, 3, 2, 1])
    rfm_df['F_Score'] = pd.qcut(rfm_df['frequency'].rank(method="first"), 5, labels=[1, 2, 3, 4, 5])
    rfm_df['M_Score'] = pd.qcut(rfm_df['monetary'].rank(method="first"), 5, labels=[1, 2, 3, 4, 5])
    
    # 计算综合RFM得分 (权重: R=0.3, F=0.3, M=0.4)
    rfm_df['RFM_Score'] = (0.3 * rfm_df['R_Score'].astype(int) + 
                          0.3 * rfm_df['F_Score'].astype(int) + 
                          0.4 * rfm_df['M_Score'].astype(int))
    
    # 客户分群
    rfm_df['Customer_Segment'] = pd.qcut(rfm_df['RFM_Score'], 4, 
                                        labels=['流失风险客户', '一般价值客户', '有增长潜力客户', '高价值客户'])
    
    # 合并回原始数据
    customer_metrics = customer_metrics.merge(
        rfm_df[['customer_id', 'R_Score', 'F_Score', 'M_Score', 'RFM_Score', 'Customer_Segment']], 
        on='customer_id')
    
    return customer_metrics

def cluster_customers(customer_metrics):
    """使用K-means进行客户聚类分析"""
    print("正在进行客户聚类分析...")
    
    # 选择用于聚类的特征
    cluster_features = ['recency', 'frequency', 'monetary', 'age', 'clv']
    
    # 复制数据并处理缺失值
    cluster_data = customer_metrics[cluster_features].copy()
    cluster_data = cluster_data.fillna(cluster_data.mean())
    
    # 标准化数据
    from sklearn.preprocessing import StandardScaler
    scaler = StandardScaler()
    scaled_data = scaler.fit_transform(cluster_data)
    
    # 使用K-means聚类
    kmeans = KMeans(n_clusters=4, random_state=42)
    customer_metrics['Cluster'] = kmeans.fit_predict(scaled_data)
    
    # 分析各聚类特征
    cluster_analysis = customer_metrics.groupby('Cluster').agg({
        'recency': 'mean',
        'frequency': 'mean',
        'monetary': 'mean',
        'age': 'mean',
        'clv': 'mean',
        'customer_id': 'count'  # 每个聚类的客户数量
    }).rename(columns={'customer_id': 'count'})
    
    # 根据CLV对聚类进行命名
    cluster_ranking = cluster_analysis.sort_values('clv', ascending=False)
    cluster_mapping = {
        cluster_ranking.index[0]: '钻石客户',
        cluster_ranking.index[1]: '金牌客户',
        cluster_ranking.index[2]: '银牌客户',
        cluster_ranking.index[3]: '铜牌客户'
    }
    
    # 添加聚类名称
    customer_metrics['Cluster_Name'] = customer_metrics['Cluster'].map(cluster_mapping)
    
    return customer_metrics, cluster_analysis, cluster_mapping

def create_customer_visualizations(customer_metrics, cluster_analysis, cluster_mapping):
    """创建客户分析可视化"""
    print("正在创建客户分析可视化...")
    
    # 确保输出目录存在
    if not os.path.exists('output/figures'):
        os.makedirs('output/figures')
    
    # 设置图表风格
    sns.set(style="whitegrid")
    
    # 1. CLV分布直方图
    plt.figure(figsize=(10, 6))
    sns.histplot(customer_metrics['clv'], bins=20, kde=True)
    plt.title('客户生命周期价值(CLV)分布')
    plt.xlabel('生命周期价值')
    plt.ylabel('客户数量')
    plt.tight_layout()
    plt.savefig('output/figures/clv_distribution.png')
    plt.close()
    
    # 2. RFM客户分群占比饼图
    plt.figure(figsize=(10, 6))
    segment_counts = customer_metrics['Customer_Segment'].value_counts()
    plt.pie(segment_counts, labels=segment_counts.index, autopct='%1.1f%%')
    plt.title('RFM客户分群占比')
    plt.axis('equal')
    plt.tight_layout()
    plt.savefig('output/figures/rfm_segments_pie.png')
    plt.close()
    
    # 3. 聚类客户的特征雷达图
    plt.figure(figsize=(12, 10))
    
    # 准备雷达图数据
    cluster_radar = cluster_analysis[['recency', 'frequency', 'monetary', 'age', 'clv']]
    # 标准化数据使其在雷达图上可比
    from sklearn.preprocessing import MinMaxScaler
    scaler = MinMaxScaler()
    cluster_radar_scaled = pd.DataFrame(scaler.fit_transform(cluster_radar), 
                                        columns=cluster_radar.columns,
                                        index=cluster_radar.index)
    
    # 转置数据便于绘图
    cluster_radar_scaled = cluster_radar_scaled.T
    
    # 使用更好的颜色方案
    colors = ['#FF5733', '#33FF57', '#3357FF', '#F333FF']
    
    # 设置雷达图的角度
    categories = cluster_radar.columns
    N = len(categories)
    angles = np.linspace(0, 2*np.pi, N, endpoint=False).tolist()
    angles += angles[:1]  # 闭合图形
    
    # 创建子图
    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(polar=True))
    
    # 绘制每个聚类的雷达图
    for i, cluster in enumerate(cluster_radar_scaled.columns):
        values = cluster_radar_scaled[cluster].values.tolist()
        values += values[:1]  # 闭合图形
        ax.plot(angles, values, color=colors[i], linewidth=2, label=f"聚类 {cluster} ({cluster_mapping[cluster]})")
        ax.fill(angles, values, color=colors[i], alpha=0.1)
    
    # 设置刻度标签
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories)
    
    # 添加图例和标题
    plt.legend(loc='upper right')
    plt.title('客户聚类特征雷达图', size=15)
    plt.tight_layout()
    plt.savefig('output/figures/customer_clusters_radar.png')
    plt.close()
    
    # 4. CLV与购买频率和金额的关系散点图
    plt.figure(figsize=(12, 8))
    scatter = plt.scatter(
        customer_metrics['frequency'], 
        customer_metrics['monetary'],
        c=customer_metrics['clv'], 
        s=100, 
        alpha=0.6,
        cmap='viridis'
    )
    plt.colorbar(scatter, label='客户生命周期价值(CLV)')
    plt.xlabel('购买频率(次数)')
    plt.ylabel('消费金额')
    plt.title('购买频率-金额与客户生命周期价值(CLV)的关系')
    plt.tight_layout()
    plt.savefig('output/figures/frequency_monetary_clv.png')
    plt.close()
    
    # 5. 不同会员等级的CLV对比条形图
    plt.figure(figsize=(10, 6))
    sns.barplot(x='member_level', y='clv', data=customer_metrics, order=['Bronze', 'Silver', 'Gold', 'Platinum'])
    plt.title('不同会员等级的平均客户生命周期价值')
    plt.xlabel('会员等级')
    plt.ylabel('平均CLV')
    plt.tight_layout()
    plt.savefig('output/figures/clv_by_member_level.png')
    plt.close()
    
    # 6. 年龄与CLV的关系
    plt.figure(figsize=(10, 6))
    sns.regplot(x='age', y='clv', data=customer_metrics, scatter_kws={'alpha':0.5})
    plt.title('客户年龄与生命周期价值的关系')
    plt.xlabel('年龄')
    plt.ylabel('CLV')
    plt.tight_layout()
    plt.savefig('output/figures/age_vs_clv.png')
    plt.close()
    
    return {
        "clv_distribution": "output/figures/clv_distribution.png",
        "rfm_segments_pie": "output/figures/rfm_segments_pie.png",
        "customer_clusters_radar": "output/figures/customer_clusters_radar.png",
        "frequency_monetary_clv": "output/figures/frequency_monetary_clv.png",
        "clv_by_member_level": "output/figures/clv_by_member_level.png",
        "age_vs_clv": "output/figures/age_vs_clv.png",
    }

def build_customer_profiles(customer_metrics):
    """构建客户画像"""
    print("正在构建客户画像...")
    
    # 高价值客户画像
    high_value_customers = customer_metrics[customer_metrics['Customer_Segment'] == '高价值客户']
    
    # 分析高价值客户的共同特征
    high_value_profile = {
        "平均年龄": high_value_customers['age'].mean(),
        "性别分布": high_value_customers['gender'].value_counts().to_dict(),
        "会员等级分布": high_value_customers['member_level'].value_counts().to_dict(),
        "平均购买频率": high_value_customers['frequency'].mean(),
        "平均消费金额": high_value_customers['monetary'].mean(),
        "平均CLV": high_value_customers['clv'].mean(),
        "首次购买距今平均天数": (pd.to_datetime('2023-05-01') - high_value_customers['first_purchase']).dt.days.mean()
    }
    
    # 按客户分群分析购买行为
    segment_behavior = customer_metrics.groupby('Customer_Segment').agg({
        'frequency': 'mean',
        'monetary': 'mean',
        'recency': 'mean',
        'clv': 'mean',
        'customer_id': 'count'
    }).rename(columns={'customer_id': 'count'})
    
    # 按聚类分析分析购买路径
    cluster_paths = {}
    # 使用Cluster_Name而不是依赖cluster_mapping
    for cluster_name in customer_metrics['Cluster_Name'].unique():
        cluster_customers = customer_metrics[customer_metrics['Cluster_Name'] == cluster_name]
        
        cluster_paths[cluster_name] = {
            "平均首次购买距今天数": (pd.to_datetime('2023-05-01') - cluster_customers['first_purchase']).dt.days.mean(),
            "平均购买频率(月)": cluster_customers['purchase_frequency_monthly'].mean(),
            "平均订单金额": cluster_customers['avg_order_value'].mean(),
            "客户生命周期平均天数": cluster_customers['customer_life_cycle'].mean(),
            "主要会员等级": cluster_customers['member_level'].mode()[0]
        }
    
    # 构建不同客户群的营销建议
    marketing_recommendations = {
        "高价值客户": [
            "实施VIP奖励计划，提供专属优惠和服务",
            "开发会员专属产品和限量版产品",
            "定期举办高端客户答谢活动，增强品牌忠诚度",
            "为高价值客户提供专属客户经理，提供一对一服务"
        ],
        "有增长潜力客户": [
            "提供阶梯式的升级激励，鼓励增加购买频率和金额",
            "根据购买历史进行产品交叉销售和向上销售",
            "设计会员积分加速计划，加速客户向高价值群体迁移",
            "提供限时专属优惠，增加客户粘性"
        ],
        "一般价值客户": [
            "定期推送个性化产品推荐，提高购买转化率",
            "设计'首次尝试'促销活动，鼓励尝试新品类",
            "实施适度的邮件营销和社交媒体互动",
            "提供数量型优惠（如买二送一），提高单次购买量"
        ],
        "流失风险客户": [
            "发送'我们想念你'电子邮件，附带特别回购优惠",
            "进行客户调研，了解流失原因",
            "提供免费试用或样品吸引客户回购",
            "简化购买流程，降低再次购买的门槛"
        ]
    }
    
    return {
        "high_value_profile": high_value_profile,
        "segment_behavior": segment_behavior.to_dict(),
        "cluster_purchase_paths": cluster_paths,
        "marketing_recommendations": marketing_recommendations
    }

def format_customer_analysis_output(customer_metrics, customer_profiles, visualizations, cluster_analysis):
    """格式化客户分析输出为JSON格式"""
    
    # 准备摘要数据
    total_customers = len(customer_metrics)
    avg_clv = customer_metrics['clv'].mean()
    max_clv = customer_metrics['clv'].max()
    min_clv = customer_metrics['clv'].min()
    avg_retention_rate = customer_metrics['retention_rate'].mean()
    avg_frequency = customer_metrics['frequency'].mean()
    avg_monetary = customer_metrics['monetary'].mean()
    
    # 客户分群分布
    segment_distribution = customer_metrics['Customer_Segment'].value_counts().to_dict()
    
    # CLV等级分布
    clv_distribution = pd.qcut(customer_metrics['clv'], 4, 
                               labels=['低CLV', '中低CLV', '中高CLV', '高CLV']).value_counts().to_dict()
    
    # 示例代码
    rfm_code_example = """
# RFM分析代码示例
def perform_rfm_analysis(customer_data):
    # 计算RFM指标
    rfm_df = customer_data.copy()
    
    # 1. Recency - 客户最近一次购买距今的天数
    today = pd.to_datetime('today')
    rfm_df['Recency'] = (today - rfm_df['last_purchase_date']).dt.days
    
    # 2. Frequency - 客户购买的总次数
    # 假设已经计算
    
    # 3. Monetary - 客户消费的总金额
    # 假设已经计算
    
    # 对RFM进行评分 (1-5分)
    rfm_df['R_Score'] = pd.qcut(rfm_df['Recency'], 5, labels=[5, 4, 3, 2, 1])
    rfm_df['F_Score'] = pd.qcut(rfm_df['Frequency'].rank(method="first"), 5, labels=[1, 2, 3, 4, 5])
    rfm_df['M_Score'] = pd.qcut(rfm_df['Monetary'].rank(method="first"), 5, labels=[1, 2, 3, 4, 5])
    
    # 计算总RFM得分 (加权)
    rfm_df['RFM_Score'] = (0.3 * rfm_df['R_Score'] + 
                           0.3 * rfm_df['F_Score'] + 
                           0.4 * rfm_df['M_Score'])
    
    # 客户分群
    rfm_df['Customer_Segment'] = pd.qcut(rfm_df['RFM_Score'], 4, 
                                       labels=['流失风险客户', '一般价值客户', 
                                               '增长潜力客户', '高价值客户'])
    
    return rfm_df
"""
    
    clv_code_example = """
# 客户生命周期价值计算代码示例
def calculate_clv(customer_data, discount_rate=0.1, time_horizon=24):
    clv_df = customer_data.copy()
    
    # 1. 计算月均边际贡献
    monthly_margin = clv_df['avg_monthly_spending'] * 0.6  # 假设60%是毛利
    
    # 2. 设定每个客户的预期留存率
    retention_rates = {'Bronze': 0.7, 'Silver': 0.8, 'Gold': 0.9, 'Platinum': 0.95}
    clv_df['retention_rate'] = clv_df['member_level'].map(retention_rates)
    
    # 3. 计算有限时间视野内的CLV
    clv_values = []
    
    for idx, customer in clv_df.iterrows():
        future_value = 0
        for t in range(1, time_horizon + 1):
            future_value += (customer['monthly_margin'] * 
                            (customer['retention_rate'] ** t) / 
                            ((1 + discount_rate/12) ** t))
        
        # 总CLV = 未来价值 - 获取成本 + 已实现价值
        total_clv = future_value - 100 + customer['total_spending'] * 0.6
        clv_values.append(total_clv)
    
    clv_df['CLV'] = clv_values
    return clv_df
"""
    
    # 构建完整输出
    output = {
        "task_id": "CUSTOMER_ANALYSIS_001",
        "success": True,
        "result": {
            "summary": f"成功完成客户分析，分析了{total_customers}位客户的价值和行为特征",
            "details": {
                "clv_metrics": {
                    "average_clv": avg_clv,
                    "max_clv": max_clv,
                    "min_clv": min_clv,
                    "clv_distribution": clv_distribution
                },
                "behavioral_metrics": {
                    "average_retention_rate": avg_retention_rate,
                    "average_purchase_frequency": avg_frequency,
                    "average_monetary_value": avg_monetary,
                    "segment_distribution": segment_distribution
                },
                "high_value_customer_profile": customer_profiles['high_value_profile'],
                "customer_segments_behavior": customer_profiles['segment_behavior'],
                "customer_purchase_paths": customer_profiles['cluster_purchase_paths']
            }
        },
        "artifacts": {
            "visualizations": visualizations,
            "code_examples": {
                "rfm_analysis": rfm_code_example,
                "clv_calculation": clv_code_example
            },
            "marketing_recommendations": customer_profiles['marketing_recommendations']
        },
        "next_steps": [
            "实施针对不同客户群的个性化营销策略",
            "建立预测性客户流失模型",
            "开发自动化客户细分系统",
            "设计客户价值提升路径"
        ]
    }
    
    return output

def run_customer_analysis():
    """运行完整的客户分析流程"""
    
    # 1. 获取销售数据
    preprocessing_results = preprocess_data()
    sales_df = preprocessing_results["transformed_data"]
    
    # 2. 创建客户数据
    df_with_customers, customers_info = create_customer_data(sales_df)
    
    # 3. 计算客户指标
    customer_metrics = calculate_customer_metrics(df_with_customers, customers_info)
    
    # 4. 计算客户生命周期价值
    customer_metrics = calculate_clv(customer_metrics)
    
    # 5. 进行RFM分析
    customer_metrics = perform_rfm_analysis(customer_metrics)
    
    # 6. 进行客户聚类
    customer_metrics, cluster_analysis, cluster_mapping = cluster_customers(customer_metrics)
    
    # 7. 创建可视化
    visualizations = create_customer_visualizations(customer_metrics, cluster_analysis, cluster_mapping)
    
    # 8. 构建客户画像
    customer_profiles = build_customer_profiles(customer_metrics)
    
    # 9. 格式化输出
    output = format_customer_analysis_output(customer_metrics, customer_profiles, visualizations, cluster_analysis)
    
    return output, customer_metrics

if __name__ == "__main__":
    # 确保输出目录存在
    if not os.path.exists('output'):
        os.makedirs('output')
    
    # 运行分析并获取结果
    output, customer_data = run_customer_analysis()
    
    # 保存客户数据
    customer_data.to_csv('output/customer_data.csv', index=False)
    
    # 保存结果到JSON文件
    with open('output/customer_analysis_results.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    # 打印最终结果
    print(json.dumps(output, ensure_ascii=False, indent=2))