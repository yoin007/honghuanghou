#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""增量部署打包脚本（deploy-pack skill）。

把变动文件按原始目录结构打包为 ZIP，附 _deploy/ 四件套：
filelist.txt / deploy.bat / restore.bat / 部署说明.txt

用法:
    python3 pack_changes.py --files files.txt --out deploy_xxx.zip [--root .] [--note "..."]
"""

import argparse
import subprocess
import sys
import zipfile
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent

# 被 gitignore 忽略、但服务器运行必需的文件——无论清单里有没有都强制打包。
# 仅限"启动时只做种子、不覆盖服务器已有配置"的文件（DB 是权限唯一权威，
# 覆盖 yaml 不影响运行时）。服务器私有配置（setting.local.json 等）严禁加入。
IGNORED_INCLUDE_WHITELIST = [
    "lesson/config/api_permissions.yaml",
]


def git_ignored(root: Path, rel: str) -> bool:
    """用 git check-ignore 判断文件是否被 gitignore 忽略"""
    try:
        result = subprocess.run(
            ["git", "check-ignore", "-q", rel],
            cwd=str(root),
            capture_output=True,
        )
        return result.returncode == 0
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser(description="增量部署打包")
    parser.add_argument("--files", required=True, help="文件清单（每行一个仓库相对路径）")
    parser.add_argument("--out", required=True, help="输出 ZIP 路径")
    parser.add_argument("--root", default=".", help="项目根目录")
    parser.add_argument("--note", default="", help="部署说明中的一句话变更描述")
    parser.add_argument("--extra-steps", default="", help="部署后额外步骤说明（追加到部署说明）")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    files_path = Path(args.files).resolve()
    if not files_path.exists():
        sys.exit(f"清单文件不存在: {files_path}")

    entries = []
    missing = []
    ignored = []
    for line in files_path.read_text(encoding="utf-8").splitlines():
        rel = line.strip().replace("\\", "/")
        if not rel or rel.startswith("#"):
            continue
        target = root / rel
        if not target.is_file():
            missing.append(rel)
            continue
        entries.append(rel)
        if git_ignored(root, rel):
            ignored.append(rel)

    if missing:
        sys.exit("以下文件不存在，请修正清单:\n  " + "\n  ".join(missing))

    # 白名单强制纳入：gitignore 文件不进 git 但影响部署，防止清单遗漏
    auto_added = []
    for rel in IGNORED_INCLUDE_WHITELIST:
        if rel not in entries and (root / rel).is_file():
            entries.append(rel)
            auto_added.append(rel)
    if not entries:
        sys.exit("清单为空")

    out = Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    deploy_dir = SKILL_DIR / "scripts"
    filelist = "\n".join(entries) + "\n"

    note_lines = [
        "增量部署包 - 部署说明",
        "=" * 40,
        f"变更内容: {args.note or '（见 filelist.txt）'}",
        "",
        "文件清单:",
        *(f"  {e}" for e in entries),
        "",
    ]
    if ignored:
        note_lines += [
            "以下文件被 .gitignore 忽略（不会随 git 同步，已包含在本包中，服务器上直接覆盖）:",
            *(f"  {e}" for e in ignored),
            "",
        ]
    note_lines += [
        "服务器操作步骤:",
        "  1. 把本 ZIP 解压到服务器任意临时目录（解压后 _deploy 与 lesson/frontend 同级，保持此结构）",
        "  2. 进入解压后的 _deploy 目录，运行: deploy.bat <项目根目录>（例如 deploy.bat D:\\projects\\honghuanghou）",
        "     - 脚本先备份将被覆盖的旧文件到 backup_时间戳/，确认后执行部署",
        "  3. 重启后端服务（python main.py）",
        "  4. 浏览器强刷（Ctrl+Shift+R）",
        "  5. 数据库表/权限配置在启动时自动迁移，禁止用本地数据库覆盖服务器数据库",
        "",
        "回滚:",
        f"  运行备份目录中的 restore.bat，按提示输入备份目录和项目根目录:",
        "  restore.bat <backup_时间戳目录> <项目根目录>",
        "",
    ]
    if args.extra_steps:
        note_lines += ["部署后额外步骤:", args.extra_steps, ""]

    def bat_bytes(path: Path) -> bytes:
        """BAT 统一转 GBK+CRLF（中文 Windows cmd 原生解析，禁止 UTF-8）。

        源文件可能是 UTF-8 或已是 GBK，两种都能正确读入后归一化。
        """
        data = path.read_bytes()
        for enc in ("utf-8", "gbk"):
            try:
                text = data.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        return text.replace("\r\n", "\n").replace("\n", "\r\n").encode("gbk")

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel in entries:
            zf.write(root / rel, rel)
        zf.writestr("_deploy/filelist.txt", filelist)
        zf.writestr("_deploy/deploy.bat", bat_bytes(deploy_dir / "deploy.bat"))
        zf.writestr("_deploy/restore.bat", bat_bytes(deploy_dir / "restore.bat"))
        zf.writestr("_deploy/verify.bat", bat_bytes(deploy_dir / "verify.bat"))
        zf.writestr("_deploy/deploy_notes.txt", "\n".join(note_lines))

    size = out.stat().st_size / 1024
    print(f"已生成 {out}（{size:.0f} KB，{len(entries)} 个业务文件）")
    if ignored:
        print("包含被 gitignore 忽略的文件（不会随 git 同步，服务器需覆盖）:")
        for rel in ignored:
            mark = "（白名单自动纳入）" if rel in auto_added else ""
            print(f"  {rel}{mark}")


if __name__ == "__main__":
    main()
