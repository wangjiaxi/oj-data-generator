#!/usr/bin/env python3
"""
OJ 测试数据自动生成器 - 主脚本

用法：
    python3 generate_data.py --problem <name> [--cyaron-file <path>] [--std-file <path>] [--count 10]

功能：
    1. 使用 cyaron 生成 .in 测试数据文件（默认10组）
    2. 运行标程生成对应的 .out 文件
    3. 默认仅输出文件夹；用户要求时（--zip）打包为 ZIP

依赖：
    pip install cyaron
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description="OJ 测试数据生成器")
    parser.add_argument("--problem", required=True, help="题目名称，用于命名输出文件")
    parser.add_argument("--cyaron-file", default=None,
                        help="cyaron 生成脚本路径。若未提供则需在当前目录下有 gen_data.py")
    parser.add_argument("--std-file", default=None,
                        help="标程文件路径（支持 .py / .cpp）。若未提供则在当前目录找 std.py 或 std.cpp")
    parser.add_argument("--count", type=int, default=10, help="生成的测试数据组数（默认 10）")
    parser.add_argument("--seed", type=int, default=None, help="随机种子（用于可复现）")
    parser.add_argument("--output-dir", default="./output", help="输出目录（默认 ./output）")
    parser.add_argument("--zip", action="store_true",
                        help="打包 ZIP（默认不打包，仅输出文件夹）")
    parser.add_argument("--zip-mode", choices=["flat", "folder"], default="flat",
                        help="ZIP 内文件布局：flat=平铺 20 个文件；folder=按题目文件夹存放（默认 flat）")
    return parser.parse_args()


def resolve_path(path):
    """将路径解析为绝对路径"""
    if path is None:
        return None
    return os.path.abspath(path)


def find_cyaron_script(args):
    """定位 cyaron 生成脚本，返回绝对路径"""
    if args.cyaron_file and os.path.exists(args.cyaron_file):
        return resolve_path(args.cyaron_file)

    candidates = ["gen_data.py", "data_gen.py", "generate.py"]
    for c in candidates:
        if os.path.exists(c):
            return resolve_path(c)

    print("错误：未找到 cyaron 生成脚本。请使用 --cyaron-file 指定路径，或在当前目录放置 gen_data.py")
    sys.exit(1)


def find_std_program(args):
    """定位标程文件，返回绝对路径"""
    if args.std_file and os.path.exists(args.std_file):
        return resolve_path(args.std_file)

    # 按优先级查找
    candidates = ["std.py", "std.cpp", "std.cc", "solution.py", "solution.cpp"]
    for c in candidates:
        if os.path.exists(c):
            return resolve_path(c)

    print("警告：未找到标程文件。将仅生成 .in 文件，跳过 .out 生成。")
    return None


def compile_cpp(std_path):
    """编译 C++ 标程，返回编译后的可执行文件路径"""
    if shutil.which("g++") is None:
        print("错误：未找到 g++ 编译器，无法编译 C++ 标程。")
        return None

    exe_path = std_path.rsplit(".", 1)[0] + "_compiled"

    result = subprocess.run(
        ["g++", "-O2", "-o", exe_path, std_path, "-lm"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"C++ 编译失败：\n{result.stderr}")
        return None

    print(f"✅ C++ 标程编译成功 -> {exe_path}")
    return exe_path


def fallback_python(std_path):
    """C++ 标程不可用时，尝试回退到同目录下的 Python 标程"""
    candidates = [
        Path(std_path).with_suffix(".py"),
        Path(std_path).parent / "std.py",
        Path(std_path).parent / "solution.py",
    ]
    for c in candidates:
        if c.exists():
            print(f"⚠️ C++ 标程不可用，回退到 Python 标程: {c}")
            return str(c)
    print("❌ C++ 标程不可用，且未找到 Python 标程可回退。请在 std.py 中提供 Python 版本。")
    sys.exit(1)


def prepare_std_program(std_path):
    """准备标程执行方式，返回 (command_list, 运行目录)。
    C++ 编译失败时自动回退到 Python 标程。"""
    ext = os.path.splitext(std_path)[1].lower()
    std_dir = os.path.dirname(os.path.abspath(std_path))

    if ext in (".cpp", ".cc"):
        exe_path = compile_cpp(std_path)
        if exe_path is None:
            std_path = fallback_python(std_path)
            return [sys.executable, std_path], std_dir
        return [f"./{os.path.basename(exe_path)}"], std_dir

    if ext == ".py":
        return [sys.executable, std_path], std_dir

    print(f"不支持的标程格式: {ext}（仅支持 .py / .cpp / .cc）")
    sys.exit(1)


def run_cyaron_generator(cyaron_script, output_dir, count, seed):
    """运行 cyaron 脚本生成 .in 文件"""
    print(f"\n📝 正在使用 cyaron 生成 {count} 组测试数据...")

    # 将 cyaron 脚本复制到输出目录，避免路径解析不一致
    os.makedirs(output_dir, exist_ok=True)
    script_name = os.path.basename(cyaron_script)
    dest_script = os.path.join(output_dir, script_name)
    shutil.copy2(cyaron_script, dest_script)

    env = os.environ.copy()
    if seed is not None:
        env["CYARON_SEED"] = str(seed)
    # 传递输出目录给 cyaron 脚本（模板可通过 os.environ.get("CYARON_OUTPUT_DIR") 读取）
    env["CYARON_OUTPUT_DIR"] = str(output_dir)

    result = subprocess.run(
        [sys.executable, dest_script],
        cwd=output_dir,
        env=env,
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"cyaron 脚本执行失败：\n{result.stderr}")
        sys.exit(1)
    
    if result.stdout:
        print(result.stdout)
    
    # 验证 .in 文件是否生成成功
    in_files = sorted(Path(output_dir).glob("*.in"), key=lambda x: int(x.stem) if x.stem.isdigit() else 0)
    actual_count = len(in_files)
    
    if actual_count == 0:
        print("错误：未生成任何 .in 文件！请检查 cyaron 脚本。")
        sys.exit(1)

    if actual_count != count:
        print(f"❌ 期望生成 {count} 组数据，实际生成 {actual_count} 组。")
        print("   请同步调整 gen_data.py 中的 DATA_COUNT 与 --count 参数。")
        sys.exit(1)

    missing = [f"{i}.in" for i in range(1, count + 1)
               if not (Path(output_dir) / f"{i}.in").exists()]
    if missing:
        print(f"❌ 缺少预期测试点文件: {', '.join(missing)}")
        print("   请检查 gen_data.py 的文件命名是否为 1.in ~ {}.in".format(count))
        sys.exit(1)

    print(f"✅ 成功生成 {actual_count} 个 .in 文件（命名校验通过）")


def generate_outputs(output_dir, std_path, count):
    """运行标程生成 .out 文件，返回 (成功数, 失败测试点列表)"""
    if std_path is None:
        print("⚠️ 跳过 .out 生成（未找到标程）")
        return 0, []

    print(f"\n🔬 正在运行标程生成 {count} 组输出...")

    cmd_base, run_cwd = prepare_std_program(std_path)

    success = 0
    failed = []

    for i in range(1, count + 1):
        in_file = os.path.join(output_dir, f"{i}.in")
        out_file = os.path.join(output_dir, f"{i}.out")

        if not os.path.exists(in_file):
            print(f"  ⚠️ 第 {i} 组: 缺少 {i}.in，跳过")
            failed.append(i)
            continue

        try:
            with open(out_file, "w") as fout:
                with open(in_file, "r") as fin:
                    result = subprocess.run(
                        cmd_base,
                        stdin=fin,
                        stdout=fout,
                        stderr=subprocess.PIPE,
                        timeout=30,  # 单个测试点超时 30 秒
                        cwd=run_cwd
                    )

            if result.returncode != 0:
                print(f"  ⚠️ 第 {i} 组: 标程返回非零状态码 {result.returncode}")
                failed.append(i)
            else:
                success += 1

        except subprocess.TimeoutExpired:
            print(f"  ⏰ 第 {i} 组: 运行超时 (30s)")
            failed.append(i)
        except Exception as e:
            print(f"  ❌ 第 {i} 组: 执行出错 - {e}")
            failed.append(i)

    print(f"✅ 标程运行完成: {success} 组成功, {len(failed)} 组异常")
    return success, failed


def validate_data(output_dir, count):
    """自动校验：文件齐全、非空、UTF-8 可解码"""
    print("\n🧪 正在自动校验生成结果...")
    problems = []

    for i in range(1, count + 1):
        in_path = Path(output_dir) / f"{i}.in"
        out_path = Path(output_dir) / f"{i}.out"

        if not in_path.exists():
            problems.append(f"缺少 {i}.in")
            continue
        if not out_path.exists():
            problems.append(f"缺少 {i}.out")
            continue

        for p, tag in ((in_path, "in"), (out_path, "out")):
            if p.stat().st_size == 0:
                problems.append(f"{i}.{tag} 为空文件")
                continue
            try:
                with p.open("rb") as fh:
                    fh.read(1024).decode("utf-8")
            except UnicodeDecodeError:
                problems.append(f"{i}.{tag} 不是合法 UTF-8 编码")

    if problems:
        print("❌ 校验未通过：")
        for p in problems:
            print(f"   - {p}")
        return False

    print(f"✅ 校验通过：{count} 组 .in/.out 齐全、非空、UTF-8 编码")
    return True


def package_zip(output_dir, problem_name, count, zip_mode):
    """将当前批次的测试数据（1.in~N.in / 1.out~N.out）打包为 ZIP
    zip_mode: flat=平铺文件；folder=按题目文件夹存放"""
    zip_name = f"{problem_name}.zip"
    zip_path = os.path.join(output_dir, zip_name)

    mode_desc = "平铺 20 个文件" if zip_mode == "flat" else f"按文件夹 {problem_name}/ 存放"
    print(f"\n📦 正在打包为 {zip_name}（{mode_desc}）...")

    # 只收集当前批次的命名文件，避免混入旧批次残留
    expected = {f"{i}{ext}" for ext in (".in", ".out") for i in range(1, count + 1)}
    all_data = set(Path(output_dir).glob("*.in")) | set(Path(output_dir).glob("*.out"))
    files_to_pack = [f for f in sorted(all_data, key=lambda x: (int(x.stem), x.suffix))
                     if f.name in expected]
    extras = sorted(all_data - set(files_to_pack))
    if extras:
        print(f"⚠️ 忽略非当前批次文件（可能是旧数据）: {', '.join(f.name for f in extras)}")

    if not files_to_pack:
        print("错误：没有找到需要打包的文件！")
        sys.exit(1)

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for f in files_to_pack:
            arcname = f.name if zip_mode == "flat" else f"{problem_name}/{f.name}"
            zf.write(str(f), arcname)

    # ZIP 完整性校验
    with zipfile.ZipFile(zip_path) as zf:
        bad = zf.testzip()
    if bad is not None:
        print(f"❌ ZIP 完整性校验失败: {bad}")
        sys.exit(1)
    print("✅ ZIP 完整性校验通过")

    size_mb = os.path.getsize(zip_path) / (1024 * 1024)
    print(f"✅ 打包完成: {zip_path} ({size_mb:.2f} MB, {len(files_to_pack)} 个文件)")

    return zip_path


def show_summary(output_dir, count):
    """显示最终统计信息"""
    print(f"\n{'='*50}")
    print("📊 生成结果摘要")
    print(f"{'='*50}")
    
    in_files = list(Path(output_dir).glob("*.in"))
    out_files = list(Path(output_dir).glob("*.out"))
    zip_files = list(Path(output_dir).glob("*.zip"))
    
    print(f"📁 输出目录: {os.path.abspath(output_dir)}")
    print(f"📄 .in 文件数: {len(in_files)}")
    print(f"📄 .out 文件数: {len(out_files)}")
    
    if in_files:
        total_in_size = sum(f.stat().st_size for f in in_files)
        print(f"📊 输入数据总大小: {total_in_size / 1024:.1f} KB")
    
    if out_files:
        total_out_size = sum(f.stat().st_size for f in out_files)
        print(f"📊 输出数据总大小: {total_out_size / 1024:.1f} KB")
    
    if zip_files:
        for z in zip_files:
            size_mb = z.stat().st_size / (1024 * 1024)
            print(f"📦 压缩包: {z.name} ({size_mb:.2f} MB)")
    
    # 显示每个文件的简要信息
    print(f"\n📋 文件列表:")
    all_files = sorted(set(in_files + out_files), 
                       key=lambda x: (x.stem.isdigit() and int(x.stem), x.suffix))
    for f in all_files:
        size_kb = f.stat().st_size / 1024
        print(f"   {f.name:>10s}  {size_kb:>8.1f} KB")


def update_notice():
    """有新版本时返回提示文字；检查脚本缺失时返回 None（检查本身不会抛异常）"""
    try:
        from check_update import get_notice
    except ImportError:
        return None
    return get_notice()


def main():
    args = parse_args()
    
    # 创建输出目录（转成绝对路径：gen_data.py 会以输出目录为 cwd 运行，
    # 相对路径会被拼成 output/output/gen_data.py 而找不到文件）
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 50)
    print("🚀 OJ 测试数据生成器")
    print("=" * 50)
    print(f"题目名称: {args.problem}")
    print(f"测试点数量: {args.count}")
    print(f"随机种子: {args.seed or '未设置'}")
    print(f"打包 ZIP: {'是（' + args.zip_mode + ' 布局）' if args.zip else '否（默认输出文件夹）'}")
    print(f"输出目录: {output_dir.absolute()}")

    # 有新版本时提示（联网结果缓存 1 小时，连不上就跳过，不影响生成）
    notice = update_notice()
    if notice:
        print(f"\n{notice}")
    
    # 步骤 1: 定位并验证 cyaron 脚本
    cyaron_script = find_cyaron_script(args)
    print(f"\n📝 Cyaron 脚本: {cyaron_script}")
    
    # 步骤 2: 定位标程
    std_path = find_std_program(args)
    if std_path:
        print(f"🔬 标程文件: {std_path}")
    
    # 步骤 3: 运行 cyaron 生成 .in 文件
    run_cyaron_generator(cyaron_script, str(output_dir), args.count, args.seed)
    
    # 步骤 4: 运行标程生成 .out 文件
    _, failed = generate_outputs(str(output_dir), std_path, args.count)
    if failed:
        print(f"\n❌ {len(failed)} 组标程运行异常: {failed}")
        print("   为避免交付残缺数据，已中止打包。请修复标程或调整数据规模后重新生成。")
        sys.exit(1)

    # 步骤 5: 自动校验（文件齐全 / 非空 / UTF-8）
    if not validate_data(str(output_dir), args.count):
        sys.exit(1)

    # 步骤 6: 打包 ZIP（默认不打包，仅当用户明确要求时）
    zip_path = None
    if args.zip:
        zip_path = package_zip(str(output_dir), args.problem, args.count, args.zip_mode)
    else:
        print(f"\nℹ️ 默认不打包，测试数据已输出到文件夹: {output_dir.absolute()}")
        print("   如需 ZIP 请使用 --zip（--zip-mode flat|folder 控制布局）")

    # 步骤 7: 显示摘要
    show_summary(str(output_dir), args.count)

    if zip_path:
        print(f"\n✅ 全部完成！ZIP 文件位于: {zip_path}")
    else:
        print(f"\n✅ 全部完成！测试数据位于: {output_dir.absolute()}")


if __name__ == "__main__":
    main()
