#!/bin/bash
# =============================================================================
# 红皇后校园综合管理系统 - Windows 部署打包脚本
# 用途: 将项目打包为 Windows 部署所需的 zip 文件（保持目录结构）
# 使用: ./scripts/package.sh [版本号]
# =============================================================================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

# 版本号
VERSION="${1:-$(date +%Y%m%d_%H%M%S)}"
PACKAGE_NAME="honghuanghou_${VERSION}"
PACKAGE_DIR="release/${PACKAGE_NAME}"

echo -e "${GREEN}=== 红皇后校园管理系统 - 打包开始 ===${NC}"
echo "版本: $VERSION"
echo "输出: $PACKAGE_DIR"
echo ""

# 清理旧的打包文件
rm -rf "$PACKAGE_DIR"
mkdir -p "$PACKAGE_DIR"

# ============================================================================
# 1. 复制后端文件 (lesson/) - 保持目录结构
# ============================================================================
echo -e "${YELLOW}复制后端文件...${NC}"

rsync -av --delete \
  --exclude='databases/' \
  --exclude='logs/' \
  --exclude='__pycache__/' \
  --exclude='.pytest_cache/' \
  --exclude='*.pyc' \
  --exclude='.DS_Store' \
  --exclude='tests/' \
  --exclude='test_*.py' \
  --exclude='backups/' \
  --exclude='*.bak' \
  --exclude='*副本*' \
  --exclude='*.yaml' \
  --exclude='setting.local.json' \
  --exclude='white_list.txt' \
  --exclude='*.db' \
  --exclude='*.db-shm' \
  --exclude='*.db-wal' \
  --exclude='docs/' \
  --exclude='scripts/' \
  lesson/ "$PACKAGE_DIR/lesson/"

# ============================================================================
# 2. 复制前端源码 (开发模式运行需要完整前端)
# ============================================================================
echo -e "${YELLOW}复制前端源码...${NC}"

rsync -av --delete \
  --exclude='node_modules/' \
  --exclude='dist/' \
  --exclude='__pycache__/' \
  --exclude='.pytest_cache/' \
  --exclude='.DS_Store' \
  --exclude='tests/' \
  --exclude='.env' \
  --exclude='.env.development' \
  --exclude='*.pem' \
  frontend/ "$PACKAGE_DIR/frontend/"

# ============================================================================
# 3. 复制 Windows 启动脚本
# ============================================================================
# echo -e "${YELLOW}复制启动脚本...${NC}"

# mkdir -p "$PACKAGE_DIR/scripts"
# cp scripts/windows/*.bat "$PACKAGE_DIR/scripts/"

# ============================================================================
# 4. 创建部署说明
# ============================================================================
echo -e "${YELLOW}创建部署说明...${NC}"

cat > "$PACKAGE_DIR/部署说明.txt" << 'EOF'
红皇后校园综合管理系统 - Windows 部署指南
============================================

## 目录结构

├── lesson/                 # 后端服务
│   ├── main.py            # 启动入口
│   ├── requirements.txt   # Python 依赖
│   ├── config/            # 配置文件
│   ├── models/            # 数据模型
│   └── utils/             # 工具函数
├── frontend/              # 前端源码（开发模式运行）
│   ├── package.json
│   ├── vite.config.js
│   └── src/
├── scripts/               # 启动脚本
│   ├── install.bat        # 安装依赖
│   ├── start-all.bat      # 启动全部服务
│   └── stop-all.bat       # 停止全部服务
└── 部署说明.txt

## 部署步骤

1. 安装 Python 3.10+ (勾选 "Add Python to PATH")
   安装 Node.js 18+ (勾选 "Add to PATH")

2. 解压到目标目录

3. 双击 scripts/install.bat 安装依赖
   - 创建 Python 虚拟环境
   - 安装后端依赖
   - 初始化数据库
   - 安装前端依赖 (npm install)

4. 配置 lesson/.env (复制 .env.example)

5. 双击 scripts/start-all.bat 启动服务
   - 后端: http://localhost:14600
   - 前端: http://localhost:3333

6. 访问 http://localhost:3333

## 注意事项

- 数据库需单独初始化或导入数据
- 首次启动检查 lesson/config/config.yaml
- 前端以开发模式运行 (npm run dev)
EOF

# ============================================================================
# 5. 打包
# ============================================================================
echo -e "${YELLOW}打包中...${NC}"

cd release
zip -r "${PACKAGE_NAME}.zip" "${PACKAGE_NAME}"
cd ..

# 统计
SIZE=$(du -h "release/${PACKAGE_NAME}.zip" | cut -f1)
FILE_COUNT=$(find "$PACKAGE_DIR" -type f | wc -l)

echo ""
echo -e "${GREEN}=== 打包完成 ===${NC}"
echo "文件: release/${PACKAGE_NAME}.zip"
echo "大小: $SIZE"
echo "文件数: $FILE_COUNT"
echo ""
echo "目录结构:"
ls -la "$PACKAGE_DIR"