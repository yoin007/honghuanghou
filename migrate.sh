#!/bin/bash

# 一键迁移脚本 - 将项目打包为 zip 文件
# 忽略 .gitignore 中定义的文件和文件夹

set -e

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_NAME="$(basename "$SCRIPT_DIR")"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_FILE="${PROJECT_NAME}_${TIMESTAMP}.zip"

echo "开始打包项目: $PROJECT_NAME"
echo "输出文件: $OUTPUT_FILE"
echo ""

# 检查是否有未提交的更改
if ! git diff --quiet 2>/dev/null || ! git diff --cached --quiet 2>/dev/null; then
    echo "警告: 存在未提交的更改，这些更改不会被包含在打包文件中"
    echo ""
fi

# 使用 git archive 打包，自动忽略 .gitignore 中的文件
# --format=zip: 输出 zip 格式
# --output: 指定输出文件
# HEAD: 当前分支的最新提交
git archive --format=zip --output="$OUTPUT_FILE" HEAD

# 获取文件大小
FILE_SIZE=$(ls -lh "$OUTPUT_FILE" | awk '{print $5}')

echo "打包完成!"
echo "文件: $OUTPUT_FILE"
echo "大小: $FILE_SIZE"