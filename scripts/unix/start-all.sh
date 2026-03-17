#!/bin/bash
# =============================================================================
# HongHuangHou - 启动全部服务
# =============================================================================

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

# 检查虚拟环境
if [ ! -f "venv/bin/activate" ]; then
    echo "[错误] 虚拟环境不存在，请先运行 install.sh"
    exit 1
fi

# 检查前端依赖
if [ ! -d "frontend/node_modules" ]; then
    echo "[错误] 前端依赖未安装，请先运行 install.sh"
    exit 1
fi

# 创建日志目录
mkdir -p logs

echo "========================================"
echo " 启动后端服务 (后台运行)"
echo "========================================"
source venv/bin/activate
cd lesson
nohup python main.py > ../logs/backend.log 2>&1 &
BACKEND_PID=$!
echo "后端 PID: $BACKEND_PID"
echo $BACKEND_PID > ../logs/backend.pid
cd ..

echo "等待后端启动..."
sleep 3

echo "========================================"
echo " 启动前端服务 (后台运行)"
echo "========================================"
cd frontend
nohup npm run dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo "前端 PID: $FRONTEND_PID"
echo $FRONTEND_PID > ../logs/frontend.pid
cd ..

echo
echo "========================================"
echo " 服务启动完成"
echo "========================================"
echo
echo "后端: http://localhost:14600"
echo "前端: http://localhost:3333"
echo
echo "日志文件:"
echo "  logs/backend.log"
echo "  logs/frontend.log"
echo
echo "停止服务: ./stop-all.sh"
echo