# filename: write_test.py
with open('test.txt', 'w', encoding='utf-8') as f:
    f.write('测试一下')
print("文件写入完成，内容为：")
with open('test.txt', 'r', encoding='utf-8') as f:
    print(f.read())