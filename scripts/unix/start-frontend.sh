#!/bin/bash
# =============================================================================
# HongHuangHou - 启动前端
# =============================================================================

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT/frontend"

# 检查 node_modules
if [ ! -d "node_modules" ]; then
    echo "[错误] node_modules 不存在，请先运行 install.sh"
    exit 1
fi

echo "========================================"
echo " 启动前端开发服务 (端口 3333)"
echo "========================================"
echo

# 启动前端
npm run dev