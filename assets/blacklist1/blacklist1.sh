#!/data/data/com.termux/files/usr/bin/bash
set -e 

# 配置（根据实际情况修改路径）
WORK_DIR="/storage/emulated/0/.subscribe-main/assets/blacklist1"  # 脚本实际目录
FFMPEG_NEEDED=true  # 需要ffmpeg支持

# 1. 轻量更新源（避免重复升级）
echo "===== 检查更新 ====="
pkg update -y

# 2. 按需安装依赖（已安装则跳过）
echo "===== 安装必要依赖 ====="
# 检查Python是否安装，未安装则安装
if ! command -v python &> /dev/null; then
    pkg install -y python
fi
# 检查ffmpeg是否需要且未安装，未安装则安装
if $FFMPEG_NEEDED && ! command -v ffmpeg &> /dev/null; then
    pkg install -y ffmpeg
fi

# 3. 进入工作目录
echo "===== 进入脚本目录 ====="
mkdir -p "$WORK_DIR"
cd "$WORK_DIR" || { echo "目录不存在！"; exit 1; }

# 4. 执行核心脚本
echo "===== 执行直播源检测 ====="
python blacklist1.py  

echo "===== 检测完成 ====="
