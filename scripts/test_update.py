#!/usr/bin/env python3
"""
新版本检查 / 更新 / 发布的离线测试：远端用本地目录和本地 git 仓库模拟，不联网

覆盖场景：
1. 版本号比较、CHANGELOG 解析
2. 有新版时提示版本号、更新内容和更新命令；GitHub 连不上时用镜像；
   已是最新、都连不上、关闭检查时不输出
3. 缓存：1 小时内不重复联网，过期后重新检查，连不上时沿用上次结果
4. generate_data.py 运行时打印新版提示（不依赖 cyaron）
5. 普通目录安装：下载压缩包整体替换，旧版进备份
6. git 安装：git pull 更新；有本地改动时停下不覆盖
7. release.py：改 VERSION / CHANGELOG、提交、打 tag、推送

运行：
    python3 scripts/test_update.py
"""

import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from contextlib import redirect_stdout
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

import check_update as cu  # noqa: E402
import update  # noqa: E402

CHANGELOG = """# 更新日志

## 1.1.0 - 2026-10-02

- 新功能乙

## 1.0.1 - 2026-10-01

- 修复甲

## 1.0.0 - 2026-09-01

- 首个版本
"""
CHANGELOG_120 = CHANGELOG.replace("## 1.1.0", "## 1.2.0 - 2026-10-03\n\n- 新功能丙\n\n## 1.1.0")


def sh(cmd, cwd=None):
    r = subprocess.run([str(c) for c in cmd], cwd=cwd, capture_output=True, text=True)
    assert r.returncode == 0, f"{' '.join(map(str, cmd))} 失败：{r.stderr}"
    return r.stdout


def copy_skill(dest, version):
    """复制一份当前技能（不含 .git）并把 VERSION 改成指定版本"""
    shutil.copytree(SKILL_DIR, dest, ignore=shutil.ignore_patterns(".git", "__pycache__", "output"))
    (dest / "VERSION").write_text(version + "\n", encoding="utf-8")
    return dest


def set_remote(remote, version, changelog=CHANGELOG):
    remote.mkdir(parents=True, exist_ok=True)
    (remote / "VERSION").write_text(version + "\n", encoding="utf-8")
    (remote / "CHANGELOG.md").write_text(changelog, encoding="utf-8")


def quiet(func, *args, **kwargs):
    """调用 func 并收起它的输出，返回 (返回值, 输出文本)"""
    buf = io.StringIO()
    with redirect_stdout(buf):
        result = func(*args, **kwargs)
    return result, buf.getvalue()


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        # 隔离：缓存写进临时目录；git 不读用户的全局配置（提交签名、默认分支等）
        os.environ.update({
            "XDG_CACHE_HOME": str(root / "cache"),
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "test@example.com",
            "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "test@example.com",
        })
        os.environ.pop(cu.OPT_OUT_ENV, None)
        remote = root / "remote"
        raw = [remote.as_uri() + "/{path}"]

        # 1. 版本号比较、CHANGELOG 解析
        assert cu.parse_version("1.10.0") > cu.parse_version("1.9.9")
        assert cu.parse_version("1.3") == cu.parse_version("1.3.0")
        assert cu.parse_version("<html>") is None and cu.parse_version("") is None
        assert cu.notes_between(CHANGELOG, "1.0.1", "1.1.0") == ["新功能乙"]
        assert cu.notes_between(CHANGELOG, "1.0.0", "1.1.0") == ["[1.1.0] 新功能乙", "[1.0.1] 修复甲"]
        print("✅ 用例1：版本号比较、CHANGELOG 解析通过")

        # 2. 有新版才提示；已是最新、连不上、关闭检查时不输出
        user = copy_skill(root / "user" / "oj-data-generator", "1.0.0")
        set_remote(remote, "1.1.0")
        notice = cu.get_notice(force=True, skill_dir=user, raw_urls=raw)
        assert notice and "1.0.0 → 1.1.0" in notice, notice
        assert "新功能乙" in notice and "修复甲" in notice and "首个版本" not in notice, notice
        assert str(user / "scripts" / "update.py") in notice, notice

        (user / "VERSION").write_text("1.1.0\n", encoding="utf-8")
        assert cu.get_notice(force=True, skill_dir=user, raw_urls=raw) is None, "已是最新不应提示"

        cu.cache_file().unlink()
        dead = [(root / "nowhere").as_uri() + "/{path}"]
        start = time.monotonic()
        assert cu.get_notice(force=True, skill_dir=user, raw_urls=dead) is None, "连不上时不应提示"
        assert time.monotonic() - start < 5, "连不上时不应卡住"

        (user / "VERSION").write_text("1.0.0\n", encoding="utf-8")
        cu.cache_file().unlink()
        os.environ[cu.OPT_OUT_ENV] = "1"
        assert cu.get_notice(skill_dir=user, raw_urls=raw) is None, "关闭检查后不应提示"
        del os.environ[cu.OPT_OUT_ENV]

        notice = cu.get_notice(force=True, skill_dir=user, raw_urls=dead + raw)
        assert notice and "1.0.0 → 1.1.0" in notice and "新功能乙" in notice, "第一个来源连不上时应改用后面的镜像"
        print("✅ 用例2：有新版才提示、镜像兜底，已是最新 / 连不上 / 关闭检查时不输出通过")

        # 3. 缓存：期内不联网，过期重新检查，连不上沿用上次结果
        assert "→ 1.1.0" in cu.get_notice(skill_dir=user, raw_urls=raw)
        set_remote(remote, "1.2.0", CHANGELOG_120)
        assert "→ 1.1.0" in cu.get_notice(skill_dir=user, raw_urls=raw), "缓存期内不应重新联网"
        cache = json.loads(cu.cache_file().read_text(encoding="utf-8"))
        cache["checked_at"] -= cu.CACHE_TTL + 1
        cu.cache_file().write_text(json.dumps(cache), encoding="utf-8")
        assert "→ 1.2.0" in cu.get_notice(skill_dir=user, raw_urls=raw), "缓存过期后应重新检查"
        shutil.rmtree(remote)
        assert "→ 1.2.0" in cu.get_notice(force=True, skill_dir=user, raw_urls=raw), "连不上时应沿用上次结果"
        print("✅ 用例3：缓存期内不联网、过期重查、连不上沿用上次结果通过")

        # 4. generate_data.py 运行时打印新版提示（缓存里放一个更高的版本，不联网）
        cu.save_cache("99.0.0", "## 99.0.0 - 2099-01-01\n\n- 测试用新版\n")
        work = root / "gen"
        work.mkdir()
        (work / "gen_data.py").write_text(
            "for i in range(1, 4):\n"
            "    with open(f'{i}.in', 'w') as f:\n"
            "        f.write(f'{i}\\n')\n", encoding="utf-8")
        (work / "std.py").write_text("print(int(input()) * 2)\n", encoding="utf-8")
        cmd = [sys.executable, str(SCRIPT_DIR / "generate_data.py"), "--problem", "t",
               "--count", "3", "--output-dir", str(work / "out")]
        r = subprocess.run(cmd, cwd=work, capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr
        assert "有新版本" in r.stdout and "99.0.0" in r.stdout and "测试用新版" in r.stdout, r.stdout
        env = dict(os.environ, **{cu.OPT_OUT_ENV: "1"})
        r = subprocess.run(cmd, cwd=work, capture_output=True, text=True, env=env)
        assert r.returncode == 0 and "有新版本" not in r.stdout, r.stdout
        print("✅ 用例4：generate_data.py 运行时打印新版提示通过")

        # 5. 普通目录安装：下载压缩包整体替换，旧版进备份
        new = copy_skill(root / "build" / "oj-data-generator-1.1.0", "1.1.0")
        (new / "CHANGELOG.md").write_text(CHANGELOG, encoding="utf-8")
        (new / "NEW_FILE.md").write_text("新版才有的文件\n", encoding="utf-8")
        set_remote(remote, "1.1.0")
        with tarfile.open(remote / "v1.1.0.tar.gz", "w:gz") as tar:
            tar.add(str(new), arcname=new.name)
        archive = [remote.as_uri() + "/v{version}.tar.gz"]
        plain = copy_skill(root / "plain" / "oj-data-generator", "1.0.0")
        (plain / "my_notes.txt").write_text("用户自己放的文件\n", encoding="utf-8")
        code, out = quiet(update.update, plain, raw_urls=raw, archive_urls=archive)
        assert code == 0, out
        assert cu.read_local_version(plain) == "1.1.0" and (plain / "NEW_FILE.md").exists(), out
        assert "新功能乙" in out, out
        backups = list((cu.cache_file().parent / "backup").iterdir())
        assert any((b / "my_notes.txt").exists() and cu.read_local_version(b) == "1.0.0"
                   for b in backups), backups
        code, out = quiet(update.update, plain, raw_urls=raw, archive_urls=archive)
        assert code == 0 and "已是最新" in out, out
        print("✅ 用例5：普通目录安装整体替换、旧版进备份通过")

        # 6. git 安装：git pull 更新；有本地改动时停下不覆盖
        bare = root / "origin.git"
        sh(["git", "init", "-q", "--bare", "-b", "main", bare])
        seed = copy_skill(root / "seed", "1.0.0")
        sh(["git", "init", "-q", "-b", "main"], cwd=seed)
        sh(["git", "add", "-A"], cwd=seed)
        sh(["git", "commit", "-qm", "1.0.0"], cwd=seed)
        sh(["git", "remote", "add", "origin", bare], cwd=seed)
        sh(["git", "push", "-q", "origin", "main"], cwd=seed)
        clone = root / "clone" / "oj-data-generator"
        sh(["git", "clone", "-q", bare, clone])

        def publish(version):
            (seed / "VERSION").write_text(version + "\n", encoding="utf-8")
            sh(["git", "commit", "-qam", version], cwd=seed)
            sh(["git", "push", "-q", "origin", "main"], cwd=seed)
            set_remote(remote, version)

        publish("1.0.1")
        code, out = quiet(update.update, clone, raw_urls=raw)
        assert code == 0 and cu.read_local_version(clone) == "1.0.1", out

        publish("1.0.2")
        with open(clone / "SKILL.md", "a", encoding="utf-8") as f:
            f.write("\n本地改动\n")
        code, out = quiet(update.update, clone, raw_urls=raw)
        assert code == 1 and "改过的文件" in out, out
        assert cu.read_local_version(clone) == "1.0.1", "有本地改动时不应更新"
        assert "本地改动" in (clone / "SKILL.md").read_text(encoding="utf-8"), "不应覆盖本地改动"
        print("✅ 用例6：git 安装 git pull 更新、有本地改动时不覆盖通过")

        # 7. release.py：改 VERSION / CHANGELOG、提交、打 tag、推送
        sh(["git", "checkout", "-q", "--", "."], cwd=clone)
        sh(["git", "pull", "-q", "--ff-only"], cwd=clone)
        r = subprocess.run([sys.executable, str(clone / "scripts" / "release.py"),
                            "patch", "测试发布条目", "--skip-tests"],
                           cwd=clone, capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr
        assert sh(["git", "--git-dir", bare, "show", "main:VERSION"]).strip() == "1.0.3"
        assert "v1.0.3" in sh(["git", "--git-dir", bare, "tag"]).split()
        changelog = sh(["git", "--git-dir", bare, "show", "main:CHANGELOG.md"])
        newest = changelog.split("\n## ")[1]
        assert newest.startswith("1.0.3 - ") and "- 测试发布条目" in newest, changelog
        print("✅ 用例7：release.py 改版本号、写 CHANGELOG、提交、打 tag、推送通过")

    print("\n🎉 更新相关测试全部通过")


if __name__ == "__main__":
    main()
