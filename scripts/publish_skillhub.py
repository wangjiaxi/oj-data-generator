#!/usr/bin/env python3
"""
维护者把当前版本同步发布到 skillhub（使用技能时用不到）

用法：
    python3 scripts/publish_skillhub.py            # 发布 VERSION 对应的 tag
    python3 scripts/publish_skillhub.py --dry-run  # 只做本地预检，不上传

要先登录：skillhub login --key skh_xxx（令牌在 skillhub.cn 网页上生成）

做的事：用 git archive 导出 tag v<VERSION> 的文件，在导出的 SKILL.md 头部补上
skillhub 要的 slug / displayName / summary / homepage，再执行 skillhub publish，
changelog 取 CHANGELOG.md 里这一版的条目。这些字段不写进仓库里的 SKILL.md，
免得 claude.ai 上传技能时校验头部字段不通过。
"""

import argparse
import io
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import check_update as cu

SLUG = "oj-data-generator"
DISPLAY_NAME = "OJ测试数据生成"
HOMEPAGE = "https://github.com/" + cu.REPO


def fail(msg):
    print(f"❌ {msg}")
    sys.exit(1)


def add_skillhub_fields(skill_md):
    """在 SKILL.md 头部补上 skillhub 要的字段；summary 沿用 description（skillhub 页面上的简介）"""
    text = skill_md.read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    desc = re.search(r"^description:\s*(.+)$", m.group(1), re.M) if m else None
    if not desc:
        fail("SKILL.md 头部格式不对或缺 description")
    extra = (f"slug: {SLUG}\ndisplayName: {DISPLAY_NAME}\n"
             f"summary: {desc.group(1).strip()}\nhomepage: {HOMEPAGE}")
    skill_md.write_text(f"---\n{m.group(1)}\n{extra}\n---\n" + text[m.end():], encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="把当前版本同步发布到 skillhub")
    parser.add_argument("--dry-run", action="store_true", help="只做本地预检，不上传")
    args = parser.parse_args()

    skillhub = shutil.which("skillhub")
    if not skillhub:
        fail("没装 skillhub 命令行")
    version = cu.read_local_version(cu.SKILL_DIR)
    if not version:
        fail("VERSION 文件缺失或格式不对")
    archive = subprocess.run(["git", "-C", str(cu.SKILL_DIR), "archive", "--format=zip", f"v{version}"],
                             capture_output=True)
    if archive.returncode != 0:
        fail(f"导出 tag v{version} 失败，先用 release.py 发布这一版：\n"
             f"{archive.stderr.decode('utf-8', 'replace').strip()}")

    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp) / SLUG
        with zipfile.ZipFile(io.BytesIO(archive.stdout)) as zf:
            zf.extractall(dest)
        gitignore = dest / ".gitignore"
        if gitignore.exists():
            gitignore.unlink()
        add_skillhub_fields(dest / "SKILL.md")
        changelog_md = dest / "CHANGELOG.md"
        notes = cu.parse_changelog(changelog_md.read_text(encoding="utf-8")).get(version, []) \
            if changelog_md.exists() else []
        cmd = [skillhub, "--skip-self-upgrade", "publish", str(dest), "--version", version,
               "--changelog", "；".join(notes) or f"v{version}"]
        if args.dry_run:
            cmd.append("--dry-run")
        print(f"▶ {'预检' if args.dry_run else '发布'} {SLUG}@{version} 到 skillhub", flush=True)
        code = subprocess.run(cmd).returncode
    sys.exit(code)


if __name__ == "__main__":
    main()
