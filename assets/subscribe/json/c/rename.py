import os

# 目标文件夹路径
folder_path = "/storage/emulated/0/.aaa/backups/lib/json/A/a"

# 检查文件夹是否存在
if not os.path.exists(folder_path):
    print(f"错误：文件夹不存在 - {folder_path}")
else:
    # 获取文件夹内所有文件（排除子文件夹）
    files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
    
    if not files:
        print("文件夹内没有文件可重命名")
    else:
        # 字母序列（a-z）
        letters = [chr(ord('a') + i) for i in range(26)]
        renamed_count = 0
        
        for i, filename in enumerate(files):
            # 循环使用字母（超过26个文件时从a重新开始）
            letter = letters[i % 26]
            # 新文件名（xxx + 字母 + .txt）
            new_filename = f"xxx{letter}.txt"
            old_path = os.path.join(folder_path, filename)
            new_path = os.path.join(folder_path, new_filename)
            
            # 避免覆盖已存在的文件（若有重名则跳过）
            if not os.path.exists(new_path):
                os.rename(old_path, new_path)
                renamed_count += 1
                print(f"重命名：{filename} → {new_filename}")
            else:
                print(f"跳过：{new_filename} 已存在")
        
        print(f"完成！共重命名 {renamed_count} 个文件")
