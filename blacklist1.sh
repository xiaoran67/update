#!/data/data/com.termux/files/usr/bin/bash
set -e 

# 配置（根据实际情况改）
WORK_DIR="$HOME/your_project_dir"  # 项目本地目录
PYTHON_VERSION="3.10"
FFMPEG_NEEDED=true  # 是否需要 ffmpeg，需要就设为 true

# 1. 安装依赖
echo "===== 安装依赖 ====="
pkg update -y && pkg upgrade -y
pkg install -y python$PYTHON_VERSION 
if $FFMPEG_NEEDED; then
    pkg install -y ffmpeg
fi

# 2. 准备工作目录
echo "===== 准备工作目录 ====="
mkdir -p "$WORK_DIR"
cd "$WORK_DIR" || exit 1

# 3. 配置 Python 虚拟环境（如果有依赖隔离需求）
echo "===== 配置虚拟环境 ====="
pip install --user --force-reinstall pipenv
export PATH="$HOME/.local/bin:$PATH"
pipenv --rm || true 
pipenv --python $PYTHON_VERSION
# 如果有项目依赖文件（比如 requirements.txt），解开下面注释
# pipenv install -r requirements.txt  

# 4. 执行核心脚本（替换成实际脚本路径）
echo "===== 执行直播源检测 ====="
pipenv run python assets/blacklist1/blacklist1.py  

echo "===== 执行完毕 ====="