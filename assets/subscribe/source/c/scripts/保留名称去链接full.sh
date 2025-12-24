#!/data/data/com.termux/files/usr/bin/bash

# 定义源文件路径（根据实际需求修改，确保路径正确）
SOURCE_FILE="/storage/emulated/0/.subscribe-main/output/full.txt"
# 备份文件路径，在源文件路径后加 .bak
BACKUP_FILE="${SOURCE_FILE}.bak"

# 执行存储权限配置（若已配置可按需保留或删除）
termux-setup-storage

# 仅在备份文件不存在时创建备份，避免覆盖
if [ ! -f "$BACKUP_FILE" ]; then
    cp "$SOURCE_FILE" "$BACKUP_FILE"
    if [ $? -ne 0 ]; then
        echo "❌ 备份文件失败，请检查源文件路径是否正确"
        exit 1
    fi
fi

# 使用 awk 处理文件，保留分组、提取名称且不去重
awk -F ',' '
# 匹配分组标识行（以 #genre# 开头），原样输出
/^#genre#/ {
    print $0;
    next;
}
# 处理非分组行，仅保留第一个字段（名称），空行跳过，不去重
{
    if ($0 != "" && $1 != "") {
        print $1;
    }
}
' "$BACKUP_FILE" > "$SOURCE_FILE"

# 检查 awk 处理后是否成功写入
if [ $? -eq 0 ]; then
    echo "✅ 处理完成！原文件已备份为 ${BACKUP_FILE}"
else
    echo "❌ 处理文件时出现错误，请检查文件内容格式"
fi
