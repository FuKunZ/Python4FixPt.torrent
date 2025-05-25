import bencodepy
import os
import shutil

# 配置参数
torrent_path = "/data/test.torrent"        # 替换为你的种子文件路径
local_root = r"/data/down/"               # 替换为你的本地混乱文件存放目录

print(f"种子文件路径: {torrent_path}")
print(f"本地文件目录: {local_root}")

# 初始化统计数据
total_matched_size = 0  # 已匹配文件的总大小（字节）
total_unmatched_size = 0  # 未匹配文件的总大小（字节）

# 检查种子文件和本地目录是否存在
if not os.path.exists(torrent_path):
    print(f"错误：种子文件 {torrent_path} 不存在。")
elif not os.path.exists(local_root):
    print(f"错误：本地文件目录 {local_root} 不存在。")
else:
    try:
        # 解析种子文件
        with open(torrent_path, "rb") as f:
            torrent_data = bencodepy.decode(f.read())
    except Exception as e:
        print(f"解析种子文件 {torrent_path} 时出错: {e}")
    else:
        # 提取文件列表和大小
        info = torrent_data[b'info']
        files = []
        if b'files' in info:
            # 多文件模式（含文件夹）
            for file_entry in info[b'files']:
                path = os.path.join(*[p.decode('utf-8', errors='ignore').strip('\x00') for p in file_entry[b'path']])  # 过滤空字符
                file_size = file_entry[b'length']
                files.append((path, file_size))
        else:
            # 单文件模式
            path = info[b'name'].decode('utf-8', errors='ignore').strip('\x00')  # 过滤空字符
            file_size = info[b'length']
            files.append((path, file_size))

        # 生成文件大小到路径的映射
        size_map = {file_size: path for path, file_size in files}

        # 遍历本地文件并重命名（修复空字符问题）
        for root, dirs, filenames in os.walk(local_root):
            # 过滤含空字符的目录和文件名
            dirs[:] = [d for d in dirs if '\x00' not in d]
            filenames[:] = [f for f in filenames if '\x00' not in f]

            for filename in filenames:
                local_file = os.path.join(root, filename)
                if os.path.isdir(local_file) or '\x00' in local_file:
                    continue

                try:
                    # 获取本地文件大小
                    local_file_size = os.path.getsize(local_file)
                    print(f"本地文件 {local_file} 的大小: {local_file_size}")
                    if local_file_size in size_map:
                        print(f"匹配到文件大小，目标路径: {size_map[local_file_size]}")
                        target_path = os.path.join(local_root, size_map[local_file_size])
                        os.makedirs(os.path.dirname(target_path), exist_ok=True)
                        if os.path.exists(target_path):
                            print(f"警告：目标文件 {target_path} 已存在，跳过移动。")
                        else:
                            try:
                                shutil.move(local_file, target_path)
                                print(f"已修复：{filename} → {target_path}")
                                total_matched_size += local_file_size  # 累加已匹配文件大小
                            except PermissionError:
                                print(f"错误：没有权限移动文件 {local_file} 到 {target_path}")
                    else:
                        print(f"未匹配到文件大小，跳过文件 {local_file}")
                        total_unmatched_size += local_file_size  # 累加未匹配文件大小
                except FileNotFoundError:
                    print(f"错误：文件 {local_file} 未找到。")
                except PermissionError:
                    print(f"错误：没有权限获取文件 {local_file} 的大小。")
                except Exception as e:
                    print(f"跳过文件 {local_file}（错误：{e}）")

        # 统计信息转换函数
        def format_size(bytes_size):
            units = ['B', 'KB', 'MB', 'GB', 'TB']
            unit_index = 0
            while bytes_size >= 1024 and unit_index < len(units) - 1:
                bytes_size /= 1024
                unit_index += 1
            return f"{bytes_size:.2f} {units[unit_index]}"

        # 输出统计结果
        print("\n===== 统计结果 =====")
        print(f"已正确识别并归类的数据量: {format_size(total_matched_size)}")
        print(f"未被识别到归类的数据量: {format_size(total_unmatched_size)}")
