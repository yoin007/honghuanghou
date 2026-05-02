# _*_ coding: utf-8 _*_
# 密码哈希迁移脚本
# 将 teacher_template 中的明文密码转换为 bcrypt 哈希

import os
import sys
import pandas as pd
from passlib.context import CryptContext

# 设置工作目录为 lesson 目录
lesson_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(lesson_dir)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def migrate_passwords():
    """将明文密码迁移为 bcrypt 哈希"""
    # 读取 teacher_template
    template_path = "databases/teacher_template.xlsx"

    if not os.path.exists(template_path):
        print(f"错误: 文件不存在 {template_path}")
        return

    df = pd.read_excel(template_path)

    if "pwd" not in df.columns:
        print("错误: 未找到 pwd 列")
        return

    migrated_count = 0
    skipped_count = 0

    for idx, row in df.iterrows():
        pwd = str(row.get("pwd", ""))

        if not pwd or pwd == "nan":
            skipped_count += 1
            continue

        # 检查是否已经是哈希格式
        if pwd.startswith(('$2a$', '$2b$', '$2y$')):
            print(f"[跳过] {row['name']}: 已是哈希格式")
            skipped_count += 1
            continue

        # 转换为哈希
        hashed = pwd_context.hash(pwd)
        df.at[idx, "pwd"] = hashed
        migrated_count += 1
        print(f"[迁移] {row['name']}: {pwd[:4]}*** -> {hashed[:20]}***")

    # 保存
    df.to_excel(template_path, index=False)
    print(f"\n迁移完成: {migrated_count} 个密码已迁移, {skipped_count} 个跳过")
    print(f"文件已保存: {template_path}")


if __name__ == "__main__":
    print("开始密码迁移...")
    print("=" * 50)
    migrate_passwords()
