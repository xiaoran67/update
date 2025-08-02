import os
import sys
from datetime import datetime

# 输出到脚本所在目录（assets/streaming/ 目录）
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))  # 当前脚本所在目录
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "streaming_output.txt")    # 结果文件放在同目录

# 数据源和依赖文件路径
RAW_SOURCES = os.path.join(SCRIPT_DIR, "sources.txt")  # 原始数据源
RENAME_FILE = os.path.join(SCRIPT_DIR, "rename.txt") # 容错文件


def main():
    # 确保依赖文件存在（容错用）
    if not os.path.exists(RENAME_FILE):
        with open(RENAME_FILE, "w", encoding="utf-8") as f:
            f.write("")  # 空文件也可
    
    try:
        # 读取原始数据源
        with open(RAW_SOURCES, "r", encoding="utf-8") as f:
            sources = f.readlines()
        
        # 处理逻辑：去重（保留顺序）
        unique_sources = list(dict.fromkeys(sources))
        
        # 写入目标文件（强制添加时间戳，确保内容必变）
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            # 先写入处理后的数据源
            f.writelines(unique_sources)
            # 强制添加一行时间戳（关键：确保每次运行内容不同）
            f.write(f"\n最后更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")  # 精确到毫秒
        
        print(f"✅ 处理完成，文件已保存到：{OUTPUT_FILE}")
        sys.exit(0)
    
    except Exception as e:
        print(f"❌ 错误：{str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
