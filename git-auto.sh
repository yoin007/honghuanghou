#!/bin/bash
# 项目版本管理自动化脚本
# 用法: ./git-auto.sh "提交描述"

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 检查参数
if [ -z "$1" ]; then
    echo -e "${RED}错误: 请提供提交描述${NC}"
    echo "用法: $0 \"提交描述\""
    exit 1
fi

MESSAGE="$1"
REPO_PATH="$(cd "$(dirname "$0")" && pwd)"

echo -e "${YELLOW}开始自动提交...${NC}"

cd "$REPO_PATH"

# 检查是否有修改
if git diff --quiet && git diff --cached --quiet; then
    echo -e "${YELLOW}没有需要提交的修改${NC}"
    exit 0
fi

# 添加所有修改
echo -e "${YELLOW}添加文件...${NC}"
git add -A

# 提交
echo -e "${YELLOW}提交: $MESSAGE${NC}"
git commit -m "$MESSAGE"

# 推送
if git remote -v | grep -q "push"; then
    echo -e "${YELLOW}推送到远程...${NC}"
    git push
else
    echo -e "${YELLOW}未配置远程仓库，跳过推送${NC}"
    echo -e "${YELLOW}如需推送，请先添加远程仓库:${NC}"
    echo -e "  git remote add origin <你的仓库地址>"
fi

echo -e "${GREEN}完成!${NC}"
