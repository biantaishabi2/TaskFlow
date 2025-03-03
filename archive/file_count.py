import os

def count_files(directory):
    large_files_count = 0
    small_files = []

    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            file_size = os.path.getsize(file_path)

            if file_size > 1024:
                large_files_count += 1
            else:
                file_name_without_extension = os.path.splitext(file)[0]
                small_files.append(file_name_without_extension)

    # 返回小于1KB的文件列表和大于1KB的文件数量
    return small_files, large_files_count

# 使用示例
if __name__ == "__main__":
    directory_path = '/Users/wangbo/Documents/opengrok/src/2.0/doc_gen/library/'
    small_files, large_files_count = count_files(directory_path)
    print("小于1KB的文件列表：")
    for file_name in small_files:
        print(file_name)
    print(f"\n大于1KB的文件总数: {large_files_count}")
    print(f"小于1KB的文件总数: {len(small_files)}")