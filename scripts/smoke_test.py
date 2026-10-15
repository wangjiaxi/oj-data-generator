#!/usr/bin/env python3
"""
冒烟测试：端到端验证 generate_data.py 主流程

覆盖场景：
1. 默认不打包：仅输出 3 组 .in/.out 文件夹
2. --zip --zip-mode flat：平铺 6 个文件
3. --zip --zip-mode folder：按题目文件夹存放
4. 同一种子重复生成，结果可复现（.in 完全一致）
5. .out 失败应中止且不产生 ZIP
6. 不传 --output-dir（默认相对路径 ./output）也能正常生成

运行：
    python3 scripts/smoke_test.py

依赖：cyaron >= 0.7.0
"""

import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


GEN_DATA = """#!/usr/bin/env python3
import os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cyaron import *

_seed = os.environ.get("CYARON_SEED")
if _seed:
    random.seed(int(_seed))

DATA_COUNT = 3
OUTPUT_DIR = os.environ.get("CYARON_OUTPUT_DIR") or "output"

def generate_test_point(i: int, _io):
    n = i * 10
    arr = [randint(1, 100) for _ in range(n)]
    if i == 2:
        arr.sort()
    _io.input_writeln(n)
    _io.input_writeln(*arr)

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    for i in range(1, DATA_COUNT + 1):
        _io = IO(f"{i}.in", f"{i}.out")
        generate_test_point(i, _io)
    print(f"OK {DATA_COUNT} groups")

if __name__ == "__main__":
    main()
"""


STD_PY = """#!/usr/bin/env python3
import sys
data = sys.stdin.read().strip().split()
if not data:
    raise SystemExit(1)
n = int(data[0])
arr = sorted((int(x) for x in data[1:1+n]), reverse=True)
print("\\n".join(map(str, arr)))
"""


def run(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def main():
    script_dir = Path(__file__).resolve().parent
    generator = script_dir / "generate_data.py"

    with tempfile.TemporaryDirectory() as tmp:
        workdir = Path(tmp)
        (workdir / "gen_data.py").write_text(GEN_DATA, encoding="utf-8")
        (workdir / "std.py").write_text(STD_PY, encoding="utf-8")
        output = workdir / "out"

        # 1. 默认不打包：仅输出文件夹
        r = run([sys.executable, str(generator), "--problem", "smoke",
                 "--count", "3", "--seed", "42", "--output-dir", str(output)], workdir)
        if r.returncode != 0:
            print(r.stdout)
            print(r.stderr)
            sys.exit("FAIL: generate_data.py 主流程执行失败")

        for i in range(1, 4):
            for ext in (".in", ".out"):
                f = output / f"{i}{ext}"
                assert f.exists(), f"缺少 {f.name}"
                assert f.stat().st_size > 0, f"{f.name} 为空"
        assert not (output / "smoke.zip").exists(), "默认不应生成 ZIP"
        print("✅ 用例1：默认不打包，仅输出文件夹通过")

        # 2. --zip 平铺模式
        r = run([sys.executable, str(generator), "--problem", "smoke", "--zip",
                 "--zip-mode", "flat", "--count", "3", "--seed", "42",
                 "--output-dir", str(output)], workdir)
        assert r.returncode == 0, "flat 模式打包失败"
        zip_path = output / "smoke.zip"
        with zipfile.ZipFile(zip_path) as zf:
            assert zf.testzip() is None, "ZIP 完整性校验失败"
            names = zf.namelist()
            assert len(names) == 6, f"ZIP 应包含 6 个文件，实际 {len(names)}"
            assert all("/" not in n for n in names), "flat 模式不应有子目录"
        print("✅ 用例2：--zip flat 平铺 6 个文件通过")

        # 3. --zip 文件夹模式
        output3 = workdir / "out3"
        r = run([sys.executable, str(generator), "--problem", "smoke", "--zip",
                 "--zip-mode", "folder", "--count", "3", "--seed", "42",
                 "--output-dir", str(output3)], workdir)
        assert r.returncode == 0, "folder 模式打包失败"
        with zipfile.ZipFile(output3 / "smoke.zip") as zf:
            names = zf.namelist()
            assert len(names) == 6, f"ZIP 应包含 6 个文件，实际 {len(names)}"
            assert all(n.startswith("smoke/") for n in names), "folder 模式应放入题目文件夹"
        print("✅ 用例3：--zip folder 按文件夹存放通过")

        # 4. 种子可复现：再次生成到新目录，对比 1.in
        output2 = workdir / "out2"
        r = run([sys.executable, str(generator), "--problem", "smoke",
                 "--count", "3", "--seed", "42", "--output-dir", str(output2)], workdir)
        if r.returncode != 0:
            sys.exit("FAIL: 种子复现运行失败")
        for i in range(1, 4):
            a = (output / f"{i}.in").read_bytes()
            b = (output2 / f"{i}.in").read_bytes()
            assert a == b, f"第 {i} 组数据在同一种子下不一致"
        print("✅ 用例4：同一种子结果可复现通过")

        # 5. .out 失败应中止且不产生 ZIP（用会崩的标程）
        (workdir / "std.py").write_text("#!/usr/bin/env python3\nraise SystemExit(1)\n",
                                        encoding="utf-8")
        output4 = workdir / "out4"
        r = run([sys.executable, str(generator), "--problem", "smoke",
                 "--zip", "--count", "3", "--seed", "1",
                 "--output-dir", str(output4)], workdir)
        assert r.returncode != 0, "标程异常时应以非零退出码中止"
        assert not (output4 / "smoke.zip").exists(), "标程异常时不应打包 ZIP"
        print("✅ 用例5：.out 生成失败时中止且不打包通过")

        # 6. 不传 --output-dir：默认 ./output 是相对路径，曾被拼成 output/output/gen_data.py
        (workdir / "std.py").write_text(STD_PY, encoding="utf-8")
        r = run([sys.executable, str(generator), "--problem", "smoke",
                 "--count", "3", "--seed", "42"], workdir)
        if r.returncode != 0:
            print(r.stdout)
            print(r.stderr)
            sys.exit("FAIL: 默认 --output-dir（相对路径）执行失败")
        for i in range(1, 4):
            f = workdir / "output" / f"{i}.out"
            assert f.exists() and f.stat().st_size > 0, f"默认输出目录下缺少 {f.name} 或为空"
        print("✅ 用例6：默认相对路径 --output-dir 通过")

    print("\n🎉 冒烟测试全部通过")


if __name__ == "__main__":
    main()
