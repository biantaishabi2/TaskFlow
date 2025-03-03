import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.preprocessing import LabelEncoder

# 1. 读取CSV数据 (模拟数据)
def create_sample_data(n=100):
    np.random.seed(42)
    
    # 创建日期范围
    date_range = pd.date_range(start='2023-01-01', periods=n, freq='D')
    
    # 创建产品ID和名称
    product_ids = [f'P{i:03d}' for i in np.random.randint(1, 21, size=n)]
    product_names = {
        'P001': 'Laptop', 'P002': 'Smartphone', 'P003': 'Tablet', 'P004': 'Monitor',
        'P005': 'Keyboard', 'P006': 'Mouse', 'P007': 'Headphones', 'P008': 'Speakers',
        'P009': 'Printer', 'P010': 'Scanner', 'P011': 'External HDD', 'P012': 'USB Drive',
        'P013': 'Router', 'P014': 'Webcam', 'P015': 'Microphone', 'P016': 'Graphics Card',
        'P017': 'RAM', 'P018': 'CPU', 'P019': 'Power Supply', 'P020': 'Case'
    }
    
    # 创建类别
    categories = {
        'P001': 'Computers', 'P002': 'Mobile', 'P003': 'Mobile', 'P004': 'Accessories',
        'P005': 'Accessories', 'P006': 'Accessories', 'P007': 'Audio', 'P008': 'Audio',
        'P009': 'Peripherals', 'P010': 'Peripherals', 'P011': 'Storage', 'P012': 'Storage',
        'P013': 'Networking', 'P014': 'Accessories', 'P015': 'Audio', 'P016': 'Components',
        'P017': 'Components', 'P018': 'Components', 'P019': 'Components', 'P020': 'Components'
    }
    
    # 创建销售量和单价，包含一些缺失值和异常值
    sales_quantity = np.random.randint(1, 100, size=n).astype(float)
    unit_price = np.random.uniform(10, 2000, size=n)
    
    # 添加一些缺失值
    sales_quantity[np.random.choice(n, int(n*0.1), replace=False)] = np.nan
    unit_price[np.random.choice(n, int(n*0.1), replace=False)] = np.nan
    
    # 添加一些异常值
    sales_quantity[np.random.choice(n, 5, replace=False)] = np.random.randint(500, 1000, size=5)
    unit_price[np.random.choice(n, 5, replace=False)] = np.random.uniform(5000, 10000, size=5)
    
    # 创建区域
    regions = np.random.choice(['North', 'South', 'East', 'West', 'Central'], size=n)
    
    # 创建DataFrame
    df = pd.DataFrame({
        'date': date_range,
        'product_id': product_ids,
        'product_name': [product_names[pid] for pid in product_ids],
        'category': [categories[pid] for pid in product_ids],
        'sales_quantity': sales_quantity,
        'unit_price': unit_price,
        'region': regions
    })
    
    # 将一些日期设置为非标准格式
    non_standard_dates = np.random.choice(n, int(n*0.1), replace=False)
    for idx in non_standard_dates:
        date_obj = df.loc[idx, 'date']
        if idx % 3 == 0:
            df.loc[idx, 'date'] = date_obj.strftime('%m/%d/%Y')
        else:
            df.loc[idx, 'date'] = date_obj.strftime('%d-%m-%Y')
    
    return df

# 2. 数据清洗
def clean_data(df):
    print("开始数据清洗...")
    
    # 创建副本以避免SettingWithCopyWarning
    df_cleaned = df.copy()
    
    # 处理日期格式
    date_format_counts = {}
    for idx, date_val in enumerate(df_cleaned['date']):
        if isinstance(date_val, str):
            # 尝试不同的日期格式
            try:
                df_cleaned.loc[idx, 'date'] = pd.to_datetime(date_val, format='%m/%d/%Y')
            except ValueError:
                try:
                    df_cleaned.loc[idx, 'date'] = pd.to_datetime(date_val, format='%d-%m-%Y')
                except ValueError:
                    print(f"无法解析日期: {date_val}")
    
    # 检查缺失值
    missing_values = df_cleaned.isna().sum()
    print(f"缺失值统计:\n{missing_values}")
    
    # 处理缺失值 - 使用均值填充销售量和单价
    df_cleaned['sales_quantity'].fillna(df_cleaned['sales_quantity'].mean(), inplace=True)
    df_cleaned['unit_price'].fillna(df_cleaned['unit_price'].mean(), inplace=True)
    
    # 处理异常值 - 使用IQR方法识别异常值
    # 处理销售量异常值
    Q1_sales = df_cleaned['sales_quantity'].quantile(0.25)
    Q3_sales = df_cleaned['sales_quantity'].quantile(0.75)
    IQR_sales = Q3_sales - Q1_sales
    lower_bound_sales = Q1_sales - 1.5 * IQR_sales
    upper_bound_sales = Q3_sales + 1.5 * IQR_sales
    
    print(f"销售量异常值边界: 下限={lower_bound_sales}, 上限={upper_bound_sales}")
    
    # 统计异常值数量
    outliers_sales = ((df_cleaned['sales_quantity'] < lower_bound_sales) | 
                      (df_cleaned['sales_quantity'] > upper_bound_sales)).sum()
    print(f"销售量中的异常值数量: {outliers_sales}")
    
    # 将异常值设定为边界值
    df_cleaned.loc[df_cleaned['sales_quantity'] < lower_bound_sales, 'sales_quantity'] = lower_bound_sales
    df_cleaned.loc[df_cleaned['sales_quantity'] > upper_bound_sales, 'sales_quantity'] = upper_bound_sales
    
    # 处理单价异常值
    Q1_price = df_cleaned['unit_price'].quantile(0.25)
    Q3_price = df_cleaned['unit_price'].quantile(0.75)
    IQR_price = Q3_price - Q1_price
    lower_bound_price = Q1_price - 1.5 * IQR_price
    upper_bound_price = Q3_price + 1.5 * IQR_price
    
    print(f"单价异常值边界: 下限={lower_bound_price}, 上限={upper_bound_price}")
    
    # 统计异常值数量
    outliers_price = ((df_cleaned['unit_price'] < lower_bound_price) | 
                      (df_cleaned['unit_price'] > upper_bound_price)).sum()
    print(f"单价中的异常值数量: {outliers_price}")
    
    # 将异常值设定为边界值
    df_cleaned.loc[df_cleaned['unit_price'] < lower_bound_price, 'unit_price'] = lower_bound_price
    df_cleaned.loc[df_cleaned['unit_price'] > upper_bound_price, 'unit_price'] = upper_bound_price
    
    print("数据清洗完成!")
    return df_cleaned

# 3. 数据转换
def transform_data(df_cleaned):
    print("开始数据转换...")
    
    # 创建副本
    df_transformed = df_cleaned.copy()
    
    # 创建销售额字段
    df_transformed['sales_amount'] = df_transformed['sales_quantity'] * df_transformed['unit_price']
    
    # 从日期中提取更多特征
    df_transformed['year'] = df_transformed['date'].dt.year
    df_transformed['month'] = df_transformed['date'].dt.month
    df_transformed['week'] = df_transformed['date'].dt.isocalendar().week
    df_transformed['day_of_week'] = df_transformed['date'].dt.dayofweek
    df_transformed['is_weekend'] = df_transformed['day_of_week'].apply(lambda x: 1 if x >= 5 else 0)
    
    # 对类别和区域进行编码
    label_encoder = LabelEncoder()
    df_transformed['category_encoded'] = label_encoder.fit_transform(df_transformed['category'])
    category_mapping = dict(zip(df_transformed['category'], df_transformed['category_encoded']))
    
    df_transformed['region_encoded'] = label_encoder.fit_transform(df_transformed['region'])
    region_mapping = dict(zip(df_transformed['region'], df_transformed['region_encoded']))
    
    print("编码映射:")
    print(f"类别映射: {category_mapping}")
    print(f"区域映射: {region_mapping}")
    
    print("数据转换完成!")
    return df_transformed

# 4. 运行整个预处理流程
def preprocess_data():
    # 创建模拟数据
    df_raw = create_sample_data()
    print("原始数据样本:")
    print(df_raw.head())
    print(f"原始数据形状: {df_raw.shape}")
    
    # 清洗数据
    df_cleaned = clean_data(df_raw)
    
    # 转换数据
    df_transformed = transform_data(df_cleaned)
    
    print("\n预处理后的数据样本:")
    print(df_transformed.head(10))
    print(f"处理后数据形状: {df_transformed.shape}")
    
    return {
        "raw_data": df_raw,
        "cleaned_data": df_cleaned,
        "transformed_data": df_transformed,
        "preprocessing_summary": {
            "original_shape": df_raw.shape,
            "final_shape": df_transformed.shape,
            "new_features": ["sales_amount", "year", "month", "week", "day_of_week", "is_weekend", 
                            "category_encoded", "region_encoded"]
        }
    }

# 5. 生成预处理结果和总结
def generate_results():
    results = preprocess_data()
    transformed_data = results["transformed_data"]
    
    # 生成10条处理后的记录样本，转换为可序列化格式
    sample_data = transformed_data.head(10).copy()
    
    # 将日期列转换为字符串
    sample_data['date'] = sample_data['date'].dt.strftime('%Y-%m-%d')
    
    # 转换为字典记录
    sample_records = sample_data.to_dict('records')
    
    # 生成总结
    summary = {
        "task_id": "DATA_PREPROCESS_001",
        "success": True,
        "result": {
            "summary": "成功完成数据预处理，包括清洗和转换步骤",
            "details": "处理了缺失值、异常值，并新增了多个衍生特征"
        },
        "artifacts": {
            "raw_shape": str(results["preprocessing_summary"]["original_shape"]),
            "processed_shape": str(results["preprocessing_summary"]["final_shape"]),
            "new_features": results["preprocessing_summary"]["new_features"],
            "sample_records": sample_records
        },
        "next_steps": [
            "进行探索性数据分析",
            "使用预处理后的数据构建预测模型",
            "创建数据可视化报告"
        ]
    }
    
    return summary

if __name__ == "__main__":
    import json
    results = generate_results()
    print(json.dumps(results, indent=2, ensure_ascii=False))