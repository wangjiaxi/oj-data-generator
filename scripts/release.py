#!/usr/bin/env python3
"""
维护者发布新版本（使用技能时用不到）

用法：
    python3 scripts/release.py patch "修复 xxx" "新增 yyy"
    python3 scripts/release.py 1.4.0 "更新内容"

第一个参数：patch / minor / major（在当前版本上加一），或具体版本号。
后面每个参数是一条更新内容，写进 CHANGELOG.md，别人收到新版提示时看到的就是这些。

依次做：跑测试 → 写 VERSION 和 CHANGELOG.md → git commit（包含当前所有改动）
→ 打 tag v<版本> → 推送 → 刷新 jsDelivr 镜像缓存 → 同步发布到 skillhub。
推送后，其他人最迟约 1 小时内（检查结果的缓存时间）使用技能时会看到提示。

skillhub 用本机 skillhub login 存下的凭证，这个脚本不经手令牌；没登录时只提示、不影响
GitHub 上的发布。不想同步 skillhub 加 --no-skillhub。
"""

import argparse
import datetime
import shutil
import subprocess
import sys

import check_update as cu

SKILL_DIR = cu.SKILL_DIR
TESTS = ["scripts/smoke_test.py", "scripts/test_update.py"]


def fail(msg):
    print(f"❌ {msg}")
    sys.exit(1)


def git(*args):
    r = subprocess.run(["git", "-C", str(SKILL_DIR), *args], capture_output=True, text=True)
    if r.returncode != 0:
        fail(f"git {' '.join(args)} 失败：\n{(r.stderr or r.stdout).strip()}")
    return r.stdout.strip()


def next_version(current, how):
    if how in ("major", "minor", "patch"):
        major, minor, patch = cu.parse_version(current)[:3]
        return {"major": f"{major + 1}.0.0",
                "minor": f"{major}.{minor + 1}.0",
                "patch": f"{major}.{minor}.{patch + 1}"}[how]
    if not cu.parse_version(how):
        fail(f"版本号格式不对：{how}（应为 patch / minor / major，或 1.4.0 这样的数字）")
    return how.lstrip("v")


def add_changelog(version, notes):
    """在最新一版前面插入新版本的条目"""
    path = SKILL_DIR / "CHANGELOG.md"
    text = path.read_text(encoding="utf-8") if path.exists() else "# 更新日志\n"
    entry = f"## {version} - {datetime.date.today():%Y-%m-%d}\n\n"
    entry += "".join(f"- {note}\n" for note in notes) + "\n"
    pos = text.find("\n## ")
    if pos == -1:
        text = text.rstrip("\n") + "\n\n" + entry
    else:
        text = text[:pos + 1] + entry + text[pos + 1:]
    path.write_text(text.rstrip("\n") + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="发布 oj-data-generator 新版本")
    parser.add_argument("version", help="patch / minor / major，或具体版本号如 1.4.0")
    parser.add_argument("notes", nargs="+", help="更新内容，每个参数一条")
    parser.add_argument("--skip-tests", action="store_true", help="不跑测试（不建议）")
    parser.add_argument("--no-skillhub", action="store_true", help="不同步发布到 skillhub")
    args = parser.parse_args()

    current = cu.read_local_version(SKILL_DIR)
    if not current:
        fail("VERSION 文件缺失或格式不对")
    new = next_version(current, args.version)
    if cu.parse_version(new) <= cu.parse_version(current):
        fail(f"新版本 {new} 必须大于当前版本 {current}")
    if not (SKILL_DIR / ".git").exists():
        fail(f"{SKILL_DIR} 不是 git 仓库")
    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    if branch != cu.BRANCH:
        fail(f"当前在 {branch} 分支，切到 {cu.BRANCH} 再发布")
    if git("tag", "--list", f"v{new}"):
        fail(f"tag v{new} 已经存在")

    if not args.skip_tests:
        for test in TESTS:
            print(f"▶ 运行 {test}")
            if subprocess.run([sys.executable, str(SKILL_DIR / test)], cwd=SKILL_DIR).returncode:
                fail(f"{test} 没通过，已停止发布（文件都没改）")

    (SKILL_DIR / "VERSION").write_text(new + "\n", encoding="utf-8")
    add_changelog(new, args.notes)
    git("add", "-A")
    print("▶ 本次提交的文件：\n" + git("status", "--short"))
    git("commit", "-m", f"v{new}：" + "；".join(args.notes))
    git("tag", "-a", f"v{new}", "-m", f"v{new}")

    print(f"▶ 推送到 origin/{cu.BRANCH}")
    push = subprocess.run(["git", "-C", str(SKILL_DIR), "push", "--follow-tags", "origin", cu.BRANCH])
    if push.returncode != 0:
        fail(f"推送失败。本地已提交并打好 tag，网络恢复后运行：git push --follow-tags origin {cu.BRANCH}")

    # 只有推到正式仓库才刷新镜像、同步 skillhub（测试时 origin 是本地仓库）
    if cu.REPO in git("remote", "get-url", "origin"):
        # jsDelivr 镜像会缓存几小时，主动刷新一下（失败不影响发布）
        for path in ("VERSION", "CHANGELOG.md"):
            cu.fetch(f"https://purge.jsdelivr.net/gh/{cu.REPO}@{cu.BRANCH}/{path}", timeout=10)
        if not args.no_skillhub:
            sync_skillhub()
    print(f"\n✅ 已发布 v{new}：其他人最迟约 1 小时内使用技能时会收到新版提示")


def sync_skillhub():
    """顺带同步发布到 skillhub；失败只提示，GitHub 上的发布已经完成"""
    if not shutil.which("skillhub"):
        return
    print("▶ 同步发布到 skillhub", flush=True)
    if subprocess.run([sys.executable, str(SKILL_DIR / "scripts" / "publish_skillhub.py")]).returncode:
        print("⚠️ skillhub 没同步上（GitHub 已发布，不受影响），处理好后运行：python3 scripts/publish_skillhub.py")


if __name__ == "__main__":
    main()
