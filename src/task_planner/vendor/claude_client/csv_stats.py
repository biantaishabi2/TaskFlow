import pandas as pd
import numpy as np

def calculate_csv_stats(file_path):
    """
    解析CSV文件并计算每列的统计数据
    
    Args:
        file_path: CSV文件路径
        
    Returns:
        字典，键为列名，值为该列的统计数据字典
    """
    # 读取CSV文件
    df = pd.read_csv(file_path)
    
    # 存储结果的字典
    stats = {}
    
    # 计算每列的统计数据
    for column in df.columns:
        column_data = df[column]
        
        # 判断列的数据类型
        if np.issubdtype(column_data.dtype, np.number):
            # 数值型列
            stats[column] = {
                "count": column_data.count(),
                "mean": column_data.mean(),
                "std": column_data.std(),
                "min": column_data.min(),
                "25%": column_data.quantile(0.25),
                "50%": column_data.quantile(0.5),
                "75%": column_data.quantile(0.75),
                "max": column_data.max(),
                "missing": column_data.isna().sum()
            }
        else:
            # 非数值型列
            stats[column] = {
                "count": column_data.count(),
                "unique_values": column_data.nunique(),
                "most_common": column_data.value_counts().index[0] if not column_data.empty else None,
                "most_common_count": column_data.value_counts().iloc[0] if not column_data.empty else 0,
                "missing": column_data.isna().sum()
            }
    
    return stats


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python csv_stats.py <csv_file_path>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    stats = calculate_csv_stats(file_path)
    
    # 打印统计结果
    for column, column_stats in stats.items():
        print(f"\n统计数据 - {column}:")
        for stat_name, stat_value in column_stats.items():
            print(f"  {stat_name}: {stat_value}")