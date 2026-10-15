#!/usr/bin/env python3
"""
把 oj-data-generator 更新到 GitHub 上的最新版

用法：
    python3 scripts/update.py

- git clone 装的：git pull --ff-only；技能文件有本地改动时停下，不覆盖
- 其他方式装的（下载 ZIP 解压、skillhub）：下载新版压缩包整体替换，
  旧版整个目录备份到 ~/.cache/oj-data-generator/backup/
"""

import argparse
import io
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path

import check_update as cu

ARCHIVE_URLS = [
    "https://codeload.github.com/" + cu.REPO + "/tar.gz/refs/tags/v{version}",
    "https://codeload.github.com/" + cu.REPO + "/tar.gz/refs/heads/" + cu.BRANCH,
]
MAX_ARCHIVE_BYTES = 20 * 1024 * 1024
# Claude 应用自己同步/管理的目录，本地改了会被覆盖回去
MANAGED_MARKERS = ("local-agent-mode-sessions", "skills-plugin",
                   os.path.join(".claude", "plugins"))
INSTALL_CMD = f"git clone https://github.com/{cu.REPO}.git ~/.claude/skills/oj-data-generator"


def git(skill_dir, *args):
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")  # 要输密码时直接失败，不卡住
    return subprocess.run(["git", "-C", str(skill_dir), *args],
                          capture_output=True, text=True, env=env)


def update_by_git(skill_dir):
    print(f"安装方式：git 仓库（{skill_dir}）")
    if not shutil.which("git"):
        print("❌ 找不到 git 命令")
        return False
    status = git(skill_dir, "status", "--porcelain", "--untracked-files=no")
    if status.returncode != 0:
        print(f"❌ git status 失败：{status.stderr.strip()}")
        return False
    if status.stdout.strip():
        print("❌ 技能目录里有改过的文件，为了不覆盖你的改动，已停止更新：")
        print(status.stdout.rstrip())
        print(f'   确定不要这些改动的话，先运行 git -C "{skill_dir}" checkout -- . 再更新')
        return False
    pull = git(skill_dir, "pull", "--ff-only")
    if pull.returncode != 0:
        print(f"❌ git pull 失败：\n{(pull.stderr or pull.stdout).strip()}")
        print("   常见原因：git 连不上 GitHub（git 不走系统代理，要单独配），或本地有自己的提交。")
        return False
    return True


def extract_archive(data, dest):
    """安全解压 tar.gz：只解普通文件和目录，拒绝绝对路径和 ..；返回唯一的顶层目录"""
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        for member in tar.getmembers():
            path = Path(member.name)
            if not path.parts or path.is_absolute() or ".." in path.parts:
                raise ValueError(f"压缩包里有可疑路径：{member.name}")
            target = dest.joinpath(*path.parts)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                target.parent.mkdir(parents=True, exist_ok=True)
                with tar.extractfile(member) as src, open(target, "wb") as out:
                    shutil.copyfileobj(src, out)
                os.chmod(target, 0o755 if member.mode & 0o111 else 0o644)
            # 符号链接、设备文件之类一律跳过
    tops = [p for p in dest.iterdir() if p.is_dir()]
    if len(tops) != 1:
        raise ValueError("压缩包顶层应该只有一个目录")
    return tops[0]


def update_by_archive(skill_dir, version, archive_urls):
    print(f"安装方式：普通目录（{skill_dir}），下载新版压缩包整体替换")
    data = None
    for url in archive_urls:
        data = cu.fetch(url.format(version=version), timeout=30, max_bytes=MAX_ARCHIVE_BYTES)
        if data:
            break
    if not data:
        print("❌ 新版压缩包下载失败，检查网络或代理后再试。")
        return False

    old_version = cu.read_local_version(skill_dir) or "unknown"
    backup = cu.cache_file().parent / "backup" / f"{time.strftime('%Y%m%d-%H%M%S')}-{old_version}"
    with tempfile.TemporaryDirectory() as tmp:
        try:
            new_dir = extract_archive(data, Path(tmp))
        except (tarfile.TarError, ValueError, OSError) as e:
            print(f"❌ 压缩包解压失败，原技能没动：{e}")
            return False
        if not (new_dir / "SKILL.md").is_file() or not cu.read_local_version(new_dir):
            print("❌ 压缩包里缺 SKILL.md 或 VERSION，已停止，原技能没动。")
            return False
        try:
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(skill_dir), str(backup))
        except OSError as e:
            print(f"❌ 备份旧版失败，原技能没动：{e}")
            return False
        try:
            shutil.move(str(new_dir), str(skill_dir))
        except OSError as e:
            shutil.rmtree(skill_dir, ignore_errors=True)  # 清掉复制了一半的新版
            shutil.move(str(backup), str(skill_dir))
            print(f"❌ 替换失败，已恢复旧版：{e}")
            return False
    print(f"旧版已备份到：{backup}")
    return True


def update(skill_dir=cu.SKILL_DIR, raw_urls=None, archive_urls=None):
    """更新技能目录，返回退出码：0 已是最新或更新成功，1 失败"""
    skill_dir = Path(skill_dir)
    current = cu.read_local_version(skill_dir)
    latest, changelog = cu.fetch_remote(timeout=10, raw_urls=raw_urls)
    if latest is None:
        print("❌ 连不上 GitHub，没取到最新版本号。检查网络或代理后再试。")
        return 1
    cu.save_cache(latest, changelog)
    print(f"当前版本：{current or '未知'}，最新版本：{latest}")
    if current and cu.parse_version(current) >= cu.parse_version(latest):
        print("✅ 已是最新版本")
        return 0

    if any(marker in str(skill_dir) for marker in MANAGED_MARKERS):
        print(f"❌ 这份技能在 Claude 应用管理的目录里（{skill_dir}），本地改了会被同步覆盖。")
        print(f"   请到当初安装的地方更新，或改用 git 安装：{INSTALL_CMD}")
        return 1

    if (skill_dir / ".git").exists():
        ok = update_by_git(skill_dir)
    else:
        ok = update_by_archive(skill_dir, latest, archive_urls or ARCHIVE_URLS)
    if not ok:
        return 1

    new_version = cu.read_local_version(skill_dir)
    print(f"\n✅ 已更新：{current or '未知'} → {new_version}")
    try:
        new_changelog = (skill_dir / "CHANGELOG.md").read_text(encoding="utf-8")
    except OSError:
        new_changelog = changelog
    notes = cu.notes_between(new_changelog, current, new_version)
    if notes:
        print("更新内容：")
        for note in notes:
            print(f"  - {note}")
    print("技能文件已换成新版，Claude 需重新读取 SKILL.md 再继续。")
    return 0


def main():
    argparse.ArgumentParser(description="把 oj-data-generator 更新到 GitHub 上的最新版").parse_args()
    sys.exit(update())


if __name__ == "__main__":
    main()
