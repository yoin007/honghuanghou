#!/bin/bash
# =============================================================================
# HongHuangHou - 启动后端
# =============================================================================

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

# 激活虚拟环境
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "[错误] 虚拟环境不存在，请先运行 install.sh"
    exit 1
fi

# 进入后端目录
cd lesson

# 设置环境变量
export CORS_ORIGINS="http://localhost:3333,https://localhost:3333"
export FORCE_HTTPS=false

echo "========================================"
echo " 启动后端服务 (端口 14600)"
echo "========================================"
echo

# 启动服务
python main.py