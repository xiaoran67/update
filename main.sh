#!/data/data/com.termux/files/usr/bin/bash
set -e  # 遇到错误终止脚本

#######################################
# 核心路径配置（根据需求修改）
#######################################
WORK_DIR="/storage/emulated/0/.subscribe-main"  # 工作目录
OUTPUT_DIR="$WORK_DIR/output"                   # 输出目录
HISTORY_DIR="$WORK_DIR/history"                 # 归档目录

#######################################
# 1. 强制修复环境（解决所有依赖问题）
#######################################
echo "===== 暴力修复环境 ====="
# 确保 ~/.local/bin 在 PATH（解决 pipenv 找不到）
export PATH="$HOME/.local/bin:$PATH"
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# 强制重装 pipenv + 核心依赖
pip install --user --force-reinstall pipenv
pipenv --rm || true  # 删旧虚拟环境
pipenv --python "$PYTHON_VERSION"  # 重建虚拟环境
pipenv install pytz  # 装核心依赖
# 浏览器驱动依赖（按需启用）
if [ "$OPEN_DRIVER" = "true" ]; then
  pkg install -y chrome chromedriver
  pipenv install selenium
fi

#######################################
# 其他配置参数
#######################################
RETAIN_DAYS=7  # 归档保留天数
# 需要归档的文件列表（相对于工作目录）
FILES_TO_ARCHIVE=(
  "$OUTPUT_DIR/full.txt"
  "$OUTPUT_DIR/simple.txt"
  "$OUTPUT_DIR/others.txt"
  "$OUTPUT_DIR/sports.html"
  "$OUTPUT_DIR/custom.txt"
)
# 需要校验的关键文件
CRITICAL_FILES=(
  "$OUTPUT_DIR/full.txt"
  "$OUTPUT_DIR/custom.txt"
)
# 关键内容校验规则
CRITICAL_CONTENT="🌐央视频道,#genre#"
CRITICAL_CONTENT_FILE="$OUTPUT_DIR/custom.txt"

#######################################
# 1. 检查工作目录
#######################################
echo "===== 检查工作目录 ====="
if [ ! -d "$WORK_DIR" ]; then
  echo "错误：工作目录不存在 → $WORK_DIR"
  echo "请手动创建目录后重试"
  exit 1
fi
cd "$WORK_DIR"  # 进入工作目录

#######################################
# 2. 环境准备（Termux 专属依赖安装）
################################

# 创建输出和归档目录（确保存在）
mkdir -p "$OUTPUT_DIR" "$HISTORY_DIR"



#######################################
# 4. 执行主脚本生成本地文件
#######################################
echo "===== 生成目标文件 ====="
# 检查 main.py 是否存在
if [ ! -f "$WORK_DIR/main.py" ]; then
  echo "错误：未找到 main.py → $WORK_DIR/main.py"
  exit 1
fi

# 运行 Python 脚本（失败重试）
python "$WORK_DIR/main.py" || {
  echo "首次生成失败，重试一次..."
  python "$WORK_DIR/main.py" || {
    echo "错误：生成文件失败，终止流程"
    exit 1
  }
}

#######################################
# 5. 本地文件完整性校验
#######################################
echo "===== 校验文件完整性 ====="
# 检查关键文件是否存在且非空
for file in "${CRITICAL_FILES[@]}"; do
  if [ ! -s "$file" ]; then
    echo "错误：文件为空或不存在 → $file"
    exit 1
  fi
done

# 检查关键内容是否存在
if ! grep -q "$CRITICAL_CONTENT" "$CRITICAL_CONTENT_FILE"; then
  echo "错误：缺失关键内容 → $CRITICAL_CONTENT_FILE"
  exit 1
fi

#######################################
# 6. 本地历史归档管理
#######################################
echo "===== 管理历史归档 ====="
# 删除超过保留天数的旧归档
find "$HISTORY_DIR" -name "*.zip" -type f -mtime +$RETAIN_DAYS -delete || {
  echo "警告：删除旧归档失败，继续执行"
}

# 检测文件是否更新，决定是否生成新归档
latest_archive=$(ls -t "$HISTORY_DIR"/*.zip 2>/dev/null | head -n 1)
need_archive=0  # 默认不需要归档

if [ -z "$latest_archive" ]; then
  # 无历史归档，直接生成
  need_archive=1
else
  # 对比当前文件与最新归档的差异
  temp_dir=$(mktemp -d)
  unzip -q -o "$latest_archive" -d "$temp_dir"
  
  # 检查每个文件是否有变化
  for file in "${FILES_TO_ARCHIVE[@]}"; do
    filename=$(basename "$file")
    if ! diff -q "$file" "$temp_dir/$filename" &> /dev/null; then
      need_archive=1  # 有变化则需要归档
      break
    fi
  done
  rm -rf "$temp_dir"  # 清理临时目录
fi

# 生成新归档（如有更新）
if [ $need_archive -eq 1 ]; then
  current_datetime=$(date +"%Y%m%d_%H%M%S")
  zip_filename="$HISTORY_DIR/${current_datetime}_archive.zip"
  zip -j "$zip_filename" "${FILES_TO_ARCHIVE[@]}"  # 打包文件（忽略目录）
  echo "已生成新归档 → $zip_filename"
else
  echo "文件未更新，无需生成新归档"
fi

echo "===== 所有本地任务执行完成 ====="
