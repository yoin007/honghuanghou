#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RELEASE_DIR="$ROOT_DIR/release"
STAMP="$(date +%Y%m%d-%H%M%S)"
PACKAGE_NAME="honghuanghou-windows-$STAMP"
PACKAGE_DIR="$RELEASE_DIR/$PACKAGE_NAME"
ZIP_PATH="$RELEASE_DIR/$PACKAGE_NAME.zip"
API_BASE_URL="${1:-${VITE_API_BASE_URL:-http://localhost:14600}}"
FRONTEND_PORT="${FRONTEND_PORT:-3333}"
BACKEND_PORT="${BACKEND_PORT:-14600}"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "[错误] 未找到命令: $1"
    exit 1
  fi
}

echo "========================================"
echo " HongHuangHou Windows 部署包打包"
echo "========================================"
echo "项目目录: $ROOT_DIR"
echo "API 地址: $API_BASE_URL"
echo "输出目录: $PACKAGE_DIR"
echo

require_cmd npm
require_cmd rsync

mkdir -p "$RELEASE_DIR"
rm -rf "$PACKAGE_DIR" "$ZIP_PATH"
mkdir -p "$PACKAGE_DIR"

echo "[1/7] 构建前端静态文件..."
(
  cd "$ROOT_DIR/frontend"
  VITE_API_BASE_URL="$API_BASE_URL" npm run build
)

echo "[2/7] 合并 SQLite WAL 数据..."
if command -v sqlite3 >/dev/null 2>&1; then
  for db_file in "$ROOT_DIR"/lesson/databases/*.db; do
    [ -e "$db_file" ] || continue
    sqlite3 "$db_file" "PRAGMA wal_checkpoint(FULL);" >/dev/null || {
      echo "[警告] WAL checkpoint 失败: $db_file"
      echo "       如果服务正在运行，请停止服务后重新打包，以免数据库不是最新状态。"
    }
  done
else
  echo "[提示] 未找到 sqlite3，跳过 WAL checkpoint。请确保打包前后端服务已停止。"
fi

echo "[3/7] 复制后端代码..."
rsync -a "$ROOT_DIR/lesson/" "$PACKAGE_DIR/lesson/" \
  --exclude "__pycache__/" \
  --exclude ".pytest_cache/" \
  --exclude "*.pyc" \
  --exclude "*.pyo" \
  --exclude ".DS_Store" \
  --exclude "logs/" \
  --exclude "storage/" \
  --exclude "databases/*.db-wal" \
  --exclude "databases/*.db-shm" \
  --exclude "databases/*_副本.db" \
  --exclude "databases/*.raw_pwd_backup*"

echo "[4/7] 复制前端源码和构建产物..."
mkdir -p "$PACKAGE_DIR/frontend" "$PACKAGE_DIR/frontend-dist"
rsync -a "$ROOT_DIR/frontend/" "$PACKAGE_DIR/frontend/" \
  --exclude "node_modules/" \
  --exclude "dist/" \
  --exclude ".pytest_cache/" \
  --exclude ".vscode/" \
  --exclude ".env" \
  --exclude ".env.development" \
  --exclude ".env.production" \
  --exclude "localhost+*.pem" \
  --exclude "localhost+*-key.pem" \
  --exclude ".DS_Store"
rsync -a "$ROOT_DIR/frontend/dist/" "$PACKAGE_DIR/frontend-dist/"

echo "[5/7] 复制文档和现有脚本..."
rsync -a "$ROOT_DIR/scripts/" "$PACKAGE_DIR/scripts/" \
  --exclude ".DS_Store"
if [ -d "$ROOT_DIR/docs" ]; then
  rsync -a "$ROOT_DIR/docs/" "$PACKAGE_DIR/docs/" \
    --exclude ".DS_Store"
fi
cp "$ROOT_DIR/README.md" "$PACKAGE_DIR/README.md" 2>/dev/null || true

echo "[6/7] 生成 Windows 部署脚本..."
cat > "$PACKAGE_DIR/install.bat" <<'EOF'
@echo off
chcp 65001 >nul
setlocal
title HongHuangHou - 安装依赖
cd /d %~dp0

echo ========================================
echo  HongHuangHou Windows 部署依赖安装
echo ========================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.10 或 3.11，并勾选 Add Python to PATH。
    pause
    exit /b 1
)

if not exist "venv" (
    echo [1/3] 创建 Python 虚拟环境...
    python -m venv venv
) else (
    echo [1/3] Python 虚拟环境已存在，跳过创建。
)

echo.
echo [2/3] 安装后端 Python 依赖...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r lesson\requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
if errorlevel 1 (
    echo [错误] 后端依赖安装失败。
    pause
    exit /b 1
)

echo.
echo [3/3] 检查数据库目录...
if not exist "lesson\databases" mkdir lesson\databases

echo.
echo ========================================
echo  安装完成
echo ========================================
echo  运行 start-all.bat 启动系统。
echo.
pause
EOF

cat > "$PACKAGE_DIR/start-backend.bat" <<EOF
@echo off
chcp 65001 >nul
setlocal
title HongHuangHou Backend
cd /d %~dp0

if not exist "venv\\Scripts\\activate.bat" (
    echo [错误] 虚拟环境不存在，请先运行 install.bat
    pause
    exit /b 1
)

call venv\\Scripts\\activate.bat
set PYTHONUTF8=1
set FORCE_HTTPS=false
set CORS_ORIGINS=http://localhost:$FRONTEND_PORT,http://127.0.0.1:$FRONTEND_PORT

cd lesson
echo ========================================
echo  启动后端服务: http://localhost:$BACKEND_PORT
echo ========================================
python -m uvicorn main:app --host 0.0.0.0 --port $BACKEND_PORT
pause
EOF

cat > "$PACKAGE_DIR/frontend-server.py" <<'EOF'
# -*- coding: utf-8 -*-
import argparse
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


class SpaHandler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        raw_path = super().translate_path(path)
        if os.path.exists(raw_path):
            return raw_path
        return os.path.join(os.getcwd(), "index.html")

    def end_headers(self):
        if self.path == "/" or self.path.endswith("index.html"):
            self.send_header("Cache-Control", "no-store")
        super().end_headers()


def main():
    parser = argparse.ArgumentParser(description="Serve built Vue SPA with history fallback.")
    parser.add_argument("--directory", default="frontend-dist")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=3333)
    args = parser.parse_args()
    os.chdir(args.directory)
    server = ThreadingHTTPServer((args.host, args.port), SpaHandler)
    print(f"Frontend: http://localhost:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
EOF

cat > "$PACKAGE_DIR/start-frontend.bat" <<EOF
@echo off
chcp 65001 >nul
setlocal
title HongHuangHou Frontend
cd /d %~dp0

python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.10 或 3.11。
    pause
    exit /b 1
)

if not exist "frontend-dist\\index.html" (
    echo [错误] frontend-dist\\index.html 不存在，部署包可能不完整。
    pause
    exit /b 1
)

echo ========================================
echo  启动前端服务: http://localhost:$FRONTEND_PORT
echo ========================================
python frontend-server.py --directory frontend-dist --host 0.0.0.0 --port $FRONTEND_PORT
pause
EOF

cat > "$PACKAGE_DIR/start-all.bat" <<EOF
@echo off
chcp 65001 >nul
setlocal
cd /d %~dp0

if not exist "venv\Scripts\activate.bat" (
    echo [错误] 虚拟环境不存在，请先运行 install.bat
    pause
    exit /b 1
)

start "HongHuangHou Backend" cmd /c "%~dp0start-backend.bat"
timeout /t 3 /nobreak >nul
start "HongHuangHou Frontend" cmd /c "%~dp0start-frontend.bat"

echo.
echo ========================================
echo  服务正在启动
echo ========================================
echo  后端: http://localhost:$BACKEND_PORT
echo  前端: http://localhost:$FRONTEND_PORT
echo.
echo  关闭本窗口不会停止服务；停止请运行 stop-all.bat。
echo.
pause
EOF

cat > "$PACKAGE_DIR/stop-all.bat" <<'EOF'
@echo off
chcp 65001 >nul
title HongHuangHou - 停止服务

echo ========================================
echo  停止 HongHuangHou 服务
echo ========================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python' -and ($_.CommandLine -match 'uvicorn main:app' -or $_.CommandLine -match 'frontend-server.py') } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"

echo 已发送停止命令。
echo.
pause
EOF

cat > "$PACKAGE_DIR/README-WINDOWS.md" <<EOF
# HongHuangHou Windows 部署包

## 运行环境

- Windows 10/11 或 Windows Server
- Python 3.10/3.11，安装时勾选 Add Python to PATH
- 首次安装依赖需要能访问 Python 包源

## 启动步骤

1. 解压本 ZIP。
2. 双击 \`install.bat\` 安装后端依赖。
3. 双击 \`start-all.bat\` 启动系统。
4. 浏览器打开 \`http://localhost:$FRONTEND_PORT\`。

## 端口

- 后端 API: \`http://localhost:$BACKEND_PORT\`
- 前端页面: \`http://localhost:$FRONTEND_PORT\`
- 本包前端构建时写入的 API 地址: \`$API_BASE_URL\`

## 数据库

SQLite 数据库位于 \`lesson\\databases\`。迁移到新机器前请确保旧机器服务已停止，避免复制 \`.db-wal\` 和 \`.db-shm\` 的未合并状态。本打包脚本默认只复制主 \`.db\` 文件，排除了 WAL/SHM 临时文件。

## 配置

- 主要配置目录: \`lesson\\config\`
- 如需接入微信、AI、第三方接口，请检查 \`lesson\\config\\token.yaml\`、\`wechat.yaml\` 等文件。
- 如果 Windows 机器不是本机访问，重新打包时传入 API 地址，例如：

\`\`\`bash
./scripts/package-windows.sh http://192.168.1.10:$BACKEND_PORT
\`\`\`

## 停止服务

运行 \`stop-all.bat\`。
EOF

echo "[7/7] 生成 ZIP 压缩包..."
if command -v zip >/dev/null 2>&1; then
  (
    cd "$RELEASE_DIR"
    zip -qr "$ZIP_PATH" "$PACKAGE_NAME"
  )
  echo
  echo "打包完成: $ZIP_PATH"
else
  echo "[提示] 未找到 zip 命令，已生成目录: $PACKAGE_DIR"
fi

echo
echo "Windows 部署包目录: $PACKAGE_DIR"
