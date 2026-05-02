#!/bin/bash
# 逐字稿提取 - Mac 一键安装脚本
set -e

echo ""
echo "╔══════════════════════════════════════╗"
echo "║   逐字稿提取工具 · Mac 一键安装       ║"
echo "╚══════════════════════════════════════╝"
echo ""

GIST_RAW="REPLACE_WITH_YOUR_GIST_URL"   # whisper_app.py 的 raw 地址

# 1. 检测 Homebrew
if ! command -v brew &>/dev/null; then
    echo "[1/4] 安装 Homebrew（需要密码）..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
else
    echo "[1/4] Homebrew 已安装 ✓"
fi

# 2. 检测 Python 3.11 + tk
if ! /opt/homebrew/bin/python3.11 --version &>/dev/null; then
    echo "[2/4] 安装 Python 3.11..."
    brew install python@3.11 python-tk@3.11
else
    echo "[2/4] Python 3.11 已安装 ✓"
fi

# 3. 检测 ffmpeg
if ! command -v ffmpeg &>/dev/null; then
    echo "[3/4] 安装 ffmpeg..."
    brew install ffmpeg
else
    echo "[3/4] ffmpeg 已安装 ✓"
fi

# 4. 安装 Whisper + 下载主程序
echo "[4/4] 安装 Whisper 和主程序..."
/opt/homebrew/bin/python3.11 -m pip install --upgrade pip --quiet
/opt/homebrew/bin/python3.11 -m pip install openai-whisper torch --quiet

mkdir -p ~/逐字稿提取
curl -fsSL "$GIST_RAW" -o ~/逐字稿提取/whisper_app.py

# 创建桌面快捷方式
cat > ~/Desktop/逐字稿提取.command << 'EOF'
#!/bin/bash
/opt/homebrew/bin/python3.11 ~/逐字稿提取/whisper_app.py
EOF
chmod +x ~/Desktop/逐字稿提取.command

echo ""
echo "╔══════════════════════════════════════╗"
echo "║          安装完成！✓                  ║"
echo "╚══════════════════════════════════════╝"
echo ""
echo "  双击桌面上的「逐字稿提取.command」即可使用"
echo ""
