#!/bin/bash
# =============================================================================
# HongHuangHou - 启动后端
# =============================================================================

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

# 激活虚拟环境。优先使用项目 venv；本机开发环境没有 venv 时，回退到 conda assistant。
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif command -v conda >/dev/null 2>&1; then
    CONDA_BASE="$(conda info --base)"
    # shellcheck source=/dev/null
    source "$CONDA_BASE/etc/profile.d/conda.sh"
    conda activate assistant
elif [ -x "/opt/anaconda3/envs/assistant/bin/python" ]; then
    export PATH="/opt/anaconda3/envs/assistant/bin:$PATH"
else
    echo "[错误] 未找到 venv，也无法激活 conda assistant 环境"
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

# 启动服务。这里不用 main.py 中的 reload=True，避免受文件监听权限影响。
python -m uvicorn main:app --host 0.0.0.0 --port 14600
