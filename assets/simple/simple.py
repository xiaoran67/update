import os
import datetime

def process_file(filename, keep_lines, output_dir):
    """处理单个文件：按 #genre# 分组去重 + 追加更新标记"""
    with open(filename, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # 按 "#genre#" 分组
    groups = []
    current_group = []
    for line in lines:
        if ",#genre#" in line:
            if current_group:
                groups.append(current_group)
            current_group = [line]
        else:
            current_group.append(line)
    if current_group:
        groups.append(current_group)

    # 组内去重（保留前 N 个重复频道）
    output_lines = []
    for group in groups:
        seen = {}
        for line in group:
            if ",#genre#" in line:
                output_lines.append(line)
                continue
            parts = line.strip().split(",", 1)
            if len(parts) < 2:
                output_lines.append(line)
                continue
            name = parts[0].strip()
            if seen.get(name, 0) < keep_lines:
                output_lines.append(line)
                seen[name] = seen.get(name, 0) + 1

    # 写入输出文件（输出到 output/simple，保留原文件名）
    output_path = os.path.join(output_dir, os.path.basename(filename))
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"# 更新标记: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.writelines(output_lines)
    print(f"✅ 处理完成: {filename} → {output_path}")


def main():
    """主逻辑：遍历 output 目录下的 .txt 文件"""
    keep_lines = int(os.environ.get("KEEP_LINES", "1"))
    input_dir = "output"  # 输入目录改为 output
    output_dir = "output/simple"  # 输出目录
    os.makedirs(output_dir, exist_ok=True)

    # 遍历 output 目录下的 .txt 文件
    if os.path.exists(input_dir) and os.path.isdir(input_dir):
        for filename in os.listdir(input_dir):
            if filename.endswith(".txt"):
                process_file(
                    filename=os.path.join(input_dir, filename),
                    keep_lines=keep_lines,
                    output_dir=output_dir
                )
    else:
        print(f"警告：输入目录不存在 - {input_dir}")


if __name__ == "__main__":
    main()
