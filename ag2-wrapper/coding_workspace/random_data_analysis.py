# filename: random_data_analysis.py
import numpy as np
import matplotlib.pyplot as plt

# 1. 生成随机数据集
np.random.seed(42)  # 设置随机种子以确保结果可复现
data = np.random.randn(1000)  # 生成1000个服从标准正态分布的随机数

# 2. 计算基本统计信息
mean_value = np.mean(data)
median_value = np.median(data)
std_dev = np.std(data)
min_value = np.min(data)
max_value = np.max(data)

# 3. 将结果可视化
plt.figure(figsize=(10, 6))  # 设置图像大小
plt.hist(data, bins=30, alpha=0.7, color='skyblue', edgecolor='black')  # 创建直方图
plt.title('Random Data Distribution')
plt.xlabel('Value')
plt.ylabel('Frequency')
plt.grid(axis='y', alpha=0.75)

# 在图上添加统计信息
textstr = '\n'.join((
    r'Mean: %.2f' % (mean_value, ),
    r'Median: %.2f' % (median_value, ),
    r'Std: %.2f' % (std_dev, ),
    r'Min: %.2f' % (min_value, ),
    r'Max: %.2f' % (max_value, )))

props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
plt.text(0.05, 0.95, textstr, transform=plt.gca().transAxes, fontsize=10,
        verticalalignment='top', bbox=props)

plt.tight_layout() # 调整布局，防止标签重叠
plt.savefig('random_data_histogram.png') # 保存图片
plt.show()