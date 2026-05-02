#!/bin/bash
# 项目打包脚本 - 打包所有必要文件用于 Windows 部署
# 使用方法: ./pack_for_windows.sh [输出目录]

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
OUTPUT_DIR="${1:-${PROJECT_DIR}/../honghuanghou_deploy}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PACKAGE_NAME="honghuanghou_${TIMESTAMP}"
PACKAGE_DIR="${OUTPUT_DIR}/${PACKAGE_NAME}"

echo "=== 项目打包脚本 ==="
echo "项目目录: ${PROJECT_DIR}"
echo "输出目录: ${PACKAGE_DIR}"

# 创建输出目录
mkdir -p "${PACKAGE_DIR}"

# ============================================
# 1. 打包后端 - 所有文件（排除缓存、日志等）
# ============================================
echo "[1/3] 打包后端代码..."
cd "${PROJECT_DIR}/lesson"
rsync -av \
    --exclude='__pycache__' \
    --exclude='*/__pycache__' \
    --exclude='.pytest_cache' \
    --exclude='*/.pytest_cache' \
    --exclude='logs' \
    --exclude='logs/*' \
    --exclude='backups' \
    --exclude='backups/*' \
    --exclude='storage' \
    --exclude='storage/*' \
    --exclude='.DS_Store' \
    --exclude='*.pyc' \
    --exclude='*.log' \
    --exclude='*.bak' \
    --exclude='temp.db' \
    --exclude='.env' \
    --include='*.py' \
    --include='*.yaml' \
    --include='*.yml' \
    --include='*.json' \
    --include='*.txt' \
    --include='*.md' \
    --include='*.example' \
    --include='*.toml' \
    --include='*.db' \
    --include='*.sql' \
    --include='*/' \
    . "${PACKAGE_DIR}/lesson/"

# ============================================
# 2. 打包前端 - dist + src + 配置
# ============================================
echo "[2/3] 打包前端代码..."
cd "${PROJECT_DIR}/frontend"

# 复制构建产物
if [ -d "dist" ]; then
    rsync -av dist/ "${PACKAGE_DIR}/frontend/dist/"
else
    echo "警告: frontend/dist 目录不存在"
fi

# 复制源代码（排除 node_modules）
rsync -av \
    --exclude='node_modules' \
    --exclude='__pycache__' \
    --exclude='.pytest_cache' \
    --exclude='.DS_Store' \
    src/ "${PACKAGE_DIR}/frontend/src/"

# 复制 public 目录
if [ -d "public" ]; then
    rsync -av public/ "${PACKAGE_DIR}/frontend/public/"
fi

# 复制配置文件（生产部署用）
cp -f package.json "${PACKAGE_DIR}/frontend/"
cp -f package-lock.json "${PACKAGE_DIR}/frontend/" 2>/dev/null || echo "无 package-lock.json"
cp -f vite.config.js "${PACKAGE_DIR}/frontend/"
cp -f vitest.config.js "${PACKAGE_DIR}/frontend/" 2>/dev/null || true
cp -f index.html "${PACKAGE_DIR}/frontend/"
cp -f .env.example "${PACKAGE_DIR}/frontend/" 2>/dev/null || true
cp -f .env.production "${PACKAGE_DIR}/frontend/" 2>/dev/null || true
cp -f .eslintrc.cjs "${PACKAGE_DIR}/frontend/" 2>/dev/null || true
cp -f .prettierrc "${PACKAGE_DIR}/frontend/" 2>/dev/null || true
cp -f README.md "${PACKAGE_DIR}/frontend/" 2>/dev/null || true

# 创建 Windows 本地开发配置（如果用户要用开发模式）
cat > "${PACKAGE_DIR}/frontend/.env.development.local.example" << 'EOF'
# Windows 本地开发配置示例
# 复制为 .env.development.local 使用
VITE_API_BASE_URL=http://localhost:14600
VITE_DEV_HTTPS=false
VITE_DEV_HOST=localhost
VITE_DEV_HTTP_PORT=3333
EOF

# ============================================
# 3. 打包根目录文档和脚本
# ============================================
echo "[3/3] 打包文档和脚本..."
cd "${PROJECT_DIR}"

cp -f AGENTS.md "${PACKAGE_DIR}/" 2>/dev/null || true
cp -f CLAUDE.md "${PACKAGE_DIR}/" 2>/dev/null || true
cp -f README.md "${PACKAGE_DIR}/" 2>/dev/null || true

if [ -d "docs" ]; then
    rsync -av --exclude='.DS_Store' docs/ "${PACKAGE_DIR}/docs/"
fi

if [ -d "scripts" ]; then
    rsync -av scripts/ "${PACKAGE_DIR}/scripts/"
fi

# 创建部署说明
cat > "${PACKAGE_DIR}/DEPLOY_README.md" << 'EOF'
# 红皇后系统 Windows 部署说明

## 目录结构

```
honghuanghou/
├── lesson/               # 后端代码
│   ├── main.py           # 启动文件
│   ├── config/           # 配置文件（yaml）
│   ├── models/           # API 模块
│   ├── utils/            # 工具模块
│   ├── databases/        # 数据库文件
│   └── requirements.txt  # Python 依赖
├── frontend/
│   ├── dist/             # 前端构建产物（生产部署用）
│   ├── src/              # 前端源代码（开发用）
│   ├── public/           # 静态资源
│   └── package.json      # npm 配置
└── docs/                 # 文档
```

## 重要说明

**生产部署**：使用 `frontend/dist/` 目录，由 nginx 托管。**不要**运行 `npm run dev`。

**开发部署**：需要修改配置文件，后端先启动，再启动前端。

---

## 生产部署（推荐）

### 1. 后端部署

```powershell
cd lesson

# 创建虚拟环境
python -m venv venv
.\venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量（可选）
copy .env.example .env

# 启动服务（默认端口 14600）
python main.py
```

### 2. 前端部署（nginx）

前端已构建为静态文件，用 nginx 托管：

```nginx
# nginx.conf
server {
    listen 80;
    server_name localhost;

    # 前端静态文件
    root D:/honghuanghou/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # API 代理到后端
    location /api {
        proxy_pass http://127.0.0.1:14600;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # 静态资源代理
    location /static {
        proxy_pass http://127.0.0.1:14600;
    }
}
```

---

## 开发部署（调试用）

如果需要调试前端代码：

### 1. 修改前端配置

```powershell
cd frontend

# 创建本地开发配置（覆盖 Mac 环境配置）
# 编辑 .env.development.local：
VITE_API_BASE_URL=http://localhost:14600
VITE_DEV_HTTPS=false
VITE_DEV_HOST=localhost
```

### 2. 安装依赖并启动

```powershell
npm install
npm run dev
```

### 3. 确保后端已启动

```powershell
cd lesson
python main.py  # 必须先启动，端口 14600
```

---

## 配置文件修改

编辑 `lesson/config/lesson.yaml` 或 `lesson.yaml`，修改路径：

```yaml
lesson_dir: C:/Users/YourName/Desktop/BDsync/temp/lesson
```

---

## 常见问题

### Q: npm run dev 报 ECONNREFUSED 错误？
**原因**：后端未启动，或配置地址错误。
**解决**：
1. 确保 `python main.py` 已启动
2. 检查 `.env.development.local` 配置 `localhost:14600`

### Q: 页面空白？
**原因**：API 地址配置错误。
**解决**：生产部署用 nginx，检查 proxy_pass 配置。
EOF

# ============================================
# 4. 打包为 zip
# ============================================
echo "打包为 zip..."
cd "${OUTPUT_DIR}"
zip -r "${PACKAGE_NAME}.zip" "${PACKAGE_NAME}"

PYTHON_COUNT=$(find "${PACKAGE_DIR}/lesson" -name "*.py" 2>/dev/null | wc -l | tr -d ' ')
PACKAGE_SIZE=$(du -sh "${PACKAGE_NAME}.zip" | cut -f1)

echo ""
echo "=== 打包完成 ==="
echo "Python 文件数: ${PYTHON_COUNT}"
echo "输出文件: ${OUTPUT_DIR}/${PACKAGE_NAME}.zip"
echo "文件大小: ${PACKAGE_SIZE}"