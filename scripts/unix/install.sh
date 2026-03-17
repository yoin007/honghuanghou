#!/bin/bash
# =============================================================================
# HongHuangHou - 安装依赖
# =============================================================================

set -e

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

echo "========================================"
echo " HongHuangHou 项目依赖安装"
echo "========================================"
echo

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未找到 Python，请先安装 Python 3.10+"
    exit 1
fi

# 检查 Node.js
if ! command -v node &> /dev/null; then
    echo "[警告] 未找到 Node.js，前端将无法运行"
    echo "        如需运行前端，请安装 Node.js 18+"
fi

echo "[1/4] 创建 Python 虚拟环境..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "虚拟环境创建成功"
else
    echo "虚拟环境已存在"
fi

echo
echo "[2/4] 安装后端依赖..."
source venv/bin/activate
pip install -r lesson/requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

echo
echo "[3/4] 初始化数据库..."
cd lesson
python scripts/init_databases.py
cd ..

echo
echo "[4/4] 安装前端依赖..."
if [ -f "frontend/package.json" ]; then
    cd frontend
    npm install
    cd ..
else
    echo "前端目录不存在，跳过"
fi

echo
echo "========================================"
echo " 安装完成！"
echo "========================================"
echo
echo "下一步："
echo " 1. 修改 lesson/config/lesson.yaml 中的路径配置"
echo " 2. 运行 ./start-all.sh 启动项目"
echo