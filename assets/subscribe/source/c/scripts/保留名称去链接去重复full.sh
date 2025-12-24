#!/data/data/com.termux/files/usr/bin/bash

# 定义目标路径（与需求统一）
SOURCE_FILE="/storage/emulated/0/1314/output/full.txt"
BACKUP_FILE="${SOURCE_FILE}.bak"

# 配置存储权限（首次运行需保留，已配置可酌情删除）
termux-setup-storage

# 备份文件（仅当备份不存在时执行）
if [ ! -f "$BACKUP_FILE" ]; then
    cp "$SOURCE_FILE" "$BACKUP_FILE"
    # 备份失败时终止并提示
    if [ $? -ne 0 ]; then
        echo "❌ 备份失败：请检查源文件路径 $SOURCE_FILE 是否存在"
        exit 1
    fi
fi

# awk 核心逻辑：分组内去重 + 无分组全局去重，保留分组标识
awk -F ',' '
# 匹配分组标识行（如 #genre#电影）
/^#genre#/ {
    print $0;          # 原样输出分组标识
    in_group = 1;      # 标记进入分组模式
    delete seen;       # 清空当前分组的去重记录
    next;
}
# 分组内的行：仅保留 $1，且同分组内去重
in_group {
    if ($1 != "" && !($1 in seen)) {
        print $1;      # 输出去重后的名称
        seen[$1] = 1;  # 记录已出现的名称
    }
    next;
}
# 无分组的行：仅保留 $1，且全局去重
!in_group && $0 != "" {
    if ($1 != "" && !($1 in seen_global)) {
        print $1;          # 输出全局去重后的名称
        seen_global[$1] = 1; # 记录全局已出现的名称
    }
}
' "$BACKUP_FILE" > "$SOURCE_FILE"

# 检查 awk 执行结果
if [ $? -eq 0 ]; then
    echo "✅ 处理完成！原文件已备份为 $BACKUP_FILE"
else
    echo "❌ 处理失败：文件格式异常或路径错误"
fi
