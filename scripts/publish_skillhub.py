#!/usr/bin/env python3
"""
维护者把当前版本同步发布到 skillhub（使用技能时用不到）

用法：
    python3 scripts/publish_skillhub.py            # 发布 VERSION 对应的 tag
    python3 scripts/publish_skillhub.py --dry-run  # 只做本地预检，不上传

要先在终端登录一次（令牌在 skillhub.cn 个人中心 → API keys 创建）：
    skillhub login --key skh_xxx --host https://api.skillhub.cn

做的事：核对登录的是作者账号 → 用 git archive 导出 tag v<VERSION> 的文件，在导出的
SKILL.md 头部补上 skillhub 要的 slug / displayName / version / summary / homepage，
去掉 VERSION（skillhub 不收没扩展名的文件）→ 执行 skillhub publish，changelog 取
skillhub 上架版本之后的全部条目。发布后要等 skillhub 审核，通过后新版本才上架。
这些字段不写进仓库里的 SKILL.md，免得 claude.ai 上传技能时校验头部字段不通过。
"""

import argparse
import io
import json
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
OWNER_HANDLE = "user_b89a4d0a"  # skillhub 上这个技能的作者账号；换账号发布会变成另一个技能


def fail(msg):
    print(f"❌ {msg}")
    sys.exit(1)


def check_account(skillhub):
    """确认本机 skillhub 登录的是作者账号"""
    r = subprocess.run([skillhub, "--skip-self-upgrade", "auth", "whoami"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        fail("skillhub 没登录，先在终端运行：skillhub login --key skh_xxx --host https://api.skillhub.cn")
    m = re.search(r"^handle\s*:\s*@?(\S+)", r.stdout, re.M)
    handle = m.group(1) if m else "未知账号"
    if handle != OWNER_HANDLE:
        fail(f"skillhub 登录的是 {handle}，不是这个技能的作者 {OWNER_HANDLE}，已停止发布")


def add_skillhub_fields(skill_md, version):
    """在 SKILL.md 头部补上 skillhub 要的字段；summary 沿用 description（skillhub 页面上的简介）"""
    text = skill_md.read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    desc = re.search(r"^description:\s*(.+)$", m.group(1), re.M) if m else None
    if not desc:
        fail("SKILL.md 头部格式不对或缺 description")
    extra = (f"slug: {SLUG}\ndisplayName: {DISPLAY_NAME}\nversion: {version}\n"
             f"summary: {desc.group(1).strip()}\nhomepage: {HOMEPAGE}")
    skill_md.write_text(f"---\n{m.group(1)}\n{extra}\n---\n" + text[m.end():], encoding="utf-8")


def prepare_package(dest, version):
    """把从 tag 导出的目录改成 skillhub 收的样子：skillhub 不收没扩展名的文件，
    去掉 VERSION，版本号写进 SKILL.md 头部（check_update.py 找不到 VERSION 时读它）"""
    for name in (".gitignore", "VERSION"):
        path = dest / name
        if path.exists():
            path.unlink()
    add_skillhub_fields(dest / "SKILL.md", version)


def published_version():
    """skillhub 上当前上架的版本号，取不到返回 None"""
    data = cu.fetch(f"https://api.skillhub.cn/api/v1/skills/{SLUG}?namespace={OWNER_HANDLE}", timeout=10)
    try:
        return json.loads(data)["latestVersion"]["version"] if data else None
    except (ValueError, KeyError, TypeError):
        return None


def changelog_since_published(changelog, version):
    """skillhub 用户可能跨几个版本升级，changelog 写上架版本之后的全部条目"""
    since = published_version()
    notes = cu.notes_between(changelog, since, version, limit=50) if since else []
    return notes or cu.parse_changelog(changelog).get(version, [])


def main():
    parser = argparse.ArgumentParser(description="把当前版本同步发布到 skillhub")
    parser.add_argument("--dry-run", action="store_true", help="只做本地预检，不上传")
    args = parser.parse_args()

    skillhub = shutil.which("skillhub")
    if not skillhub:
        fail("没装 skillhub 命令行")
    if not args.dry_run:
        check_account(skillhub)
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
        prepare_package(dest, version)
        changelog_md = dest / "CHANGELOG.md"
        notes = changelog_since_published(changelog_md.read_text(encoding="utf-8"), version) \
            if changelog_md.exists() else []
        cmd = [skillhub, "--skip-self-upgrade", "publish", str(dest), "--version", version,
               "--changelog", "；".join(notes) or f"v{version}"]
        if args.dry_run:
            cmd.append("--dry-run")
        print(f"▶ {'预检' if args.dry_run else '发布'} {SLUG}@{version} 到 skillhub", flush=True)
        code = subprocess.run(cmd).returncode
    if code == 0 and not args.dry_run:
        print("已提交 skillhub，审核通过后新版本才上架（个人中心 → 我的 Skill 可看状态）")
    sys.exit(code)


if __name__ == "__main__":
    main()
