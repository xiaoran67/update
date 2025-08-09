#!/data/data/com.termux/files/usr/bin/bash
set -e  # 严格模式，报错即停

#######################################
# 0. 全局配置（根据项目调整）
#######################################
WORK_DIR="/storage/emulated/0/.subscribe-main"  # 工作目录
PYTHON_VERSION="3.12"                            # 已装版本，放弃 3.13
RETAIN_DAYS=7                                    # 归档保留天数
FILES_TO_ARCHIVE=("output/result.txt" "output/result.m3u")  # 归档文件
OPEN_DRIVER=false                                # 浏览器驱动开关

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
# 2. 执行主脚本（确保不卡依赖）
#######################################
echo "===== 运行 main1.py ====="
cd "$WORK_DIR" || exit 1  # 切工作目录
export FINAL_FILE="$WORK_DIR/output/result.txt"
export CACHE_FILE="$WORK_DIR/output/cache.pkl"

# 执行脚本，失败重试
pipenv run python main1.py || {
  echo "首次失败，重试 → 清理缓存后再试"
  rm -f "$CACHE_FILE"  # 删缓存文件
  pipenv run python main1.py || {
    echo "错误：脚本持续失败，检查 main1.py 逻辑"
    exit 1
  }
}

#######################################
# 3. 归档 + 清理（收尾工作）
#######################################
echo "===== 归档与清理 ====="
mkdir -p "$WORK_DIR/history/main1"
# 删除超期归档
find "$WORK_DIR/history/main1" -name "*.zip" -type f -mtime +$RETAIN_DAYS -delete

# 生成今日归档（文件有变化时）
need_archive=false
for file in "${FILES_TO_ARCHIVE[@]}"; do
  [ -s "$file" ] && need_archive=true && break
done

if $need_archive; then
  current_datetime=$(date +"%Y%m%d_%H%M%S")
  zip_filename="$WORK_DIR/history/main1/${current_datetime}_archive.zip"
  zip -j "$zip_filename" "${FILES_TO_ARCHIVE[@]}"
  echo "归档成功 → $zip_filename"
else
  echo "无变化，跳过归档"
fi

echo "===== 全流程执行完毕！ ====="
