#!/usr/bin/env python3
"""
检查 oj-data-generator 有没有新版本

用法：
    python3 scripts/check_update.py           # 有新版时打印提示，否则什么都不输出
    python3 scripts/check_update.py --force   # 忽略缓存，立即联网检查

- 本地版本看技能目录下的 VERSION，最新版本看 GitHub 上 main 分支的 VERSION
- 有新版时附上 CHANGELOG.md 里新增的条目和更新命令
- 联网结果缓存 1 小时（~/.cache/oj-data-generator/update-check.json），
  连不上 GitHub 就静默跳过；退出码恒为 0，不影响正常使用
- 设置环境变量 OJ_DATA_GENERATOR_NO_UPDATE_CHECK=1 关闭自动检查（--force 仍会检查）
- generate_data.py 每次运行开头也会调用这里的 get_notice()
"""

import argparse
import json
import os
import re
import shutil
import ssl
import subprocess
import threading
import time
import urllib.request
from pathlib import Path

REPO = "wangjiaxi/oj-data-generator"
BRANCH = "main"
# GitHub 原始文件 + jsDelivr 镜像（国内直连 GitHub 不稳时兜底，镜像可能晚几小时）
RAW_URLS = [
    "https://raw.githubusercontent.com/" + REPO + "/" + BRANCH + "/{path}",
    "https://fastly.jsdelivr.net/gh/" + REPO + "@" + BRANCH + "/{path}",
]
SKILL_DIR = Path(__file__).resolve().parent.parent
TIMEOUT = 3          # 联网最多等几秒
CACHE_TTL = 3600     # 联网结果缓存几秒
OPT_OUT_ENV = "OJ_DATA_GENERATOR_NO_UPDATE_CHECK"

_VERSION_RE = re.compile(r"^v?(\d+(?:\.\d+){1,3})$")
_HEADING_RE = re.compile(r"^##\s+\[?v?(\d+(?:\.\d+){1,3})\]?")
_BULLET_RE = re.compile(r"^[-*]\s+")


def parse_version(text):
    """'1.3.0' → (1, 3, 0, 0)；不是合法版本号返回 None"""
    m = _VERSION_RE.match((text or "").strip())
    if not m:
        return None
    nums = [int(x) for x in m.group(1).split(".")]
    return tuple(nums + [0] * (4 - len(nums)))


def read_local_version(skill_dir=SKILL_DIR):
    """读技能目录下的 VERSION，缺失或格式不对返回 None"""
    try:
        text = (Path(skill_dir) / "VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return text if parse_version(text) else None


def parse_changelog(text):
    """CHANGELOG.md → {'1.3.0': ['条目', ...], ...}，保持文件顺序（新的在前）"""
    entries, current = {}, None
    for line in (text or "").splitlines():
        if line.startswith("## "):
            m = _HEADING_RE.match(line)
            current = entries.setdefault(m.group(1), []) if m else None
        elif current is not None and _BULLET_RE.match(line):
            current.append(_BULLET_RE.sub("", line, count=1).strip())
    return entries


def notes_between(changelog, local, latest, limit=6):
    """本地版本之后、最新版本及之前的更新条目；跨多个版本时条目前标版本号"""
    low = parse_version(local) or (0, 0, 0, 0)
    high = parse_version(latest)
    if not high:
        return []
    picked = [(v, items) for v, items in parse_changelog(changelog).items()
              if low < parse_version(v) <= high]
    notes = []
    for version, items in picked:
        prefix = f"[{version}] " if len(picked) > 1 else ""
        notes += [prefix + item for item in items]
    if len(notes) > limit:
        notes = notes[:limit] + [f"……共 {len(notes)} 条，完整见 CHANGELOG.md"]
    return notes


def _is_ssl_error(e):
    return isinstance(e, ssl.SSLError) or isinstance(getattr(e, "reason", None), ssl.SSLError)


def fetch(url, timeout=TIMEOUT, max_bytes=1024 * 1024):
    """GET 一个 URL，返回内容 bytes；失败或超过 max_bytes 返回 None。
    优先用 urllib（会走环境变量和 macOS 系统代理）；python.org 版 Python 没装根证书时
    会证书校验失败，这时改用系统自带的 curl"""
    request = urllib.request.Request(url, headers={"User-Agent": "oj-data-generator"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            data = resp.read(max_bytes + 1)
        return data if len(data) <= max_bytes else None
    except Exception as e:
        if not _is_ssl_error(e) or not shutil.which("curl"):
            return None
    try:
        r = subprocess.run(["curl", "-fsSL", "--max-time", str(timeout), url],
                           capture_output=True, timeout=timeout + 5)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout if r.returncode == 0 and len(r.stdout) <= max_bytes else None


def fetch_all(urls, timeout=TIMEOUT):
    """并发 GET，总共最多等 timeout+1 秒，返回与 urls 一一对应的结果（失败为 None）。
    用守护线程而不是线程池：DNS 卡住时进程照样能立刻退出"""
    results = [None] * len(urls)

    def worker(i, url):
        results[i] = fetch(url, timeout)

    threads = [threading.Thread(target=worker, args=(i, u), daemon=True)
               for i, u in enumerate(urls)]
    for t in threads:
        t.start()
    deadline = time.monotonic() + timeout + 1
    for t in threads:
        t.join(max(0.0, deadline - time.monotonic()))
    return list(results)


def fetch_remote(timeout=TIMEOUT, raw_urls=None):
    """读各来源的 VERSION 和 CHANGELOG.md，返回 (最新版本号, CHANGELOG 文本)。
    取各来源里最大的版本号（镜像可能落后）；全部失败时返回 (None, "")"""
    raw_urls = raw_urls or RAW_URLS
    urls = [u.format(path=p) for u in raw_urls for p in ("VERSION", "CHANGELOG.md")]
    texts = [b.decode("utf-8", "replace") if b else "" for b in fetch_all(urls, timeout)]
    versions = [t.strip() for t in texts[0::2] if parse_version(t)]
    if not versions:
        return None, ""
    latest = max(versions, key=parse_version)
    # 优先用写了这个版本的 CHANGELOG（镜像那份可能还没更新）
    changelog = next((c for c in texts[1::2]
                      if any(parse_version(v) == parse_version(latest)
                             for v in parse_changelog(c))), "")
    return latest, changelog


def cache_file():
    base = os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    return Path(base) / "oj-data-generator" / "update-check.json"


def load_cache():
    try:
        data = json.loads(cache_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save_cache(latest, changelog):
    path = cache_file()
    data = {"checked_at": time.time(), "latest": latest, "changelog": changelog}
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        os.replace(str(tmp), str(path))
    except OSError:
        pass


def latest_info(force=False, timeout=TIMEOUT, raw_urls=None):
    """返回 (最新版本号, CHANGELOG 文本)：1 小时内用缓存，否则联网；连不上时沿用上次结果"""
    cache = load_cache()
    try:
        age = time.time() - float(cache.get("checked_at") or 0)
    except (TypeError, ValueError):
        age = -1
    if not force and 0 <= age < CACHE_TTL:
        return cache.get("latest"), cache.get("changelog") or ""
    latest, changelog = fetch_remote(timeout, raw_urls)
    if latest is None:  # 这次没连上：沿用上次结果，过 1 小时再试
        latest, changelog = cache.get("latest"), cache.get("changelog") or ""
    save_cache(latest, changelog)
    return latest, changelog


def format_notice(local, latest, changelog, skill_dir=SKILL_DIR):
    lines = [f"⬆️ oj-data-generator 有新版本：{local or '未知'} → {latest}"]
    notes = notes_between(changelog, local, latest)
    if notes:
        lines.append("更新内容：")
        lines += [f"  - {note}" for note in notes]
    update_script = Path(skill_dir) / "scripts" / "update.py"
    lines.append(f'更新命令：python3 "{update_script}"')
    return "\n".join(lines)


def get_notice(force=False, skill_dir=SKILL_DIR, timeout=TIMEOUT, raw_urls=None):
    """有新版时返回提示文字，否则返回 None；任何异常都吞掉，不影响调用方"""
    if not force and os.environ.get(OPT_OUT_ENV, "").strip() not in ("", "0"):
        return None
    try:
        local = read_local_version(skill_dir)
        latest, changelog = latest_info(force, timeout, raw_urls)
        if not parse_version(latest):
            return None
        if local and parse_version(local) >= parse_version(latest):
            return None
        return format_notice(local, latest, changelog, skill_dir)
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(description="检查 oj-data-generator 有没有新版本")
    parser.add_argument("--force", action="store_true", help="忽略缓存，立即联网检查")
    args = parser.parse_args()
    notice = get_notice(force=args.force)
    if notice:
        print(notice)


if __name__ == "__main__":
    main()
