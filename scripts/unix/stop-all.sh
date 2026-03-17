#!/bin/bash
# =============================================================================
# HongHuangHou - 停止服务
# =============================================================================

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

echo "========================================"
echo " 停止所有服务"
echo "========================================"
echo

# 停止后端
if [ -f "logs/backend.pid" ]; then
    BACKEND_PID=$(cat logs/backend.pid)
    if kill -0 $BACKEND_PID 2>/dev/null; then
        kill $BACKEND_PID
        echo "后端已停止 (PID: $BACKEND_PID)"
    else
        echo "后端进程未运行"
    fi
    rm -f logs/backend.pid
else
    echo "后端 PID 文件不存在"
fi

# 停止前端
if [ -f "logs/frontend.pid" ]; then
    FRONTEND_PID=$(cat logs/frontend.pid)
    if kill -0 $FRONTEND_PID 2>/dev/null; then
        kill $FRONTEND_PID
        echo "前端已停止 (PID: $FRONTEND_PID)"
    else
        echo "前端进程未运行"
    fi
    rm -f logs/frontend.pid
else
    echo "前端 PID 文件不存在"
fi

# 额外清理：查找并停止相关进程
echo
echo "清理残留进程..."

# 停止 main.py
pkill -f "python.*main.py" 2>/dev/null && echo "已停止 main.py 进程"

# 停止 vite
pkill -f "vite" 2>/dev/null && echo "已停止 vite 进程"

echo
echo "所有服务已停止"
echo