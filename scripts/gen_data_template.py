#!/usr/bin/env python3
"""
Cyaron 测试数据生成脚本 - 模板 (v0.7.0)

使用说明：
1. 复制此文件为 gen_data.py
2. 根据题目要求修改 generate_test_point(i) 函数中的逻辑
3. 确保覆盖各种边界情况
4. 配合 std.py/std.cpp 标程使用

运行方式：
    python3 scripts/generate_data.py --problem <题目名>
    或手动：
    python3 gen_data.py  # 在 output/ 目录下生成 .in 文件

依赖版本：cyaron >= 0.7.0
"""

import os
import random
import sys

# 添加 cyaron 到路径（如果需要）
try:
    from cyaron import *
except ImportError:
    print("错误：未安装 cyaron。请执行: pip install cyaron>=0.7.0")
    sys.exit(1)


# ==================== 题目配置 ====================
# 根据实际情况修改以下参数
PROBLEM_NAME = "template"          # 题目名称
DATA_COUNT = 10                    # 测试点数量 (默认10组，需与 generate_data.py 的 --count 一致)
# 输出目录：优先使用环境变量（由 generate_data.py 传入），否则使用脚本所在目录
OUTPUT_DIR = os.environ.get("CYARON_OUTPUT_DIR") or os.path.dirname(os.path.abspath(__file__)) or "output"

# 随机种子：由 generate_data.py --seed 通过 CYARON_SEED 环境变量传入，保证可复现
_seed = os.environ.get("CYARON_SEED")
if _seed:
    random.seed(int(_seed))
    print(f"已固定随机种子: {_seed}")

# 数据范围常量（根据题目要求设置）
MIN_N = 1
MAX_N = 100000
MIN_VAL = 1
MAX_VAL = int(1e9)
# ==================================================


def generate_test_point(i: int, _io):
    """
    生成第 i 组测试数据 (1-indexed)

    参数:
        i: 测试点编号 (1 ~ DATA_COUNT)
        _io: cyaron 的 IO 对象，用于写入数据

    重要：必须根据题目类型设计合理的测试点分布！

    推荐的测试点分布策略:
        #1   最小规模基础测试     n=1 或最小值
        #2-3 小规模边界情况       特殊构造、极端值
        #4-6 中等规模随机+典型    正常随机 + 已知模式
        #7-8 大规模性能压力       接近上限的数据
        #9-10 极端边界            最大数据 + 特殊构造
    """

    if i == 1:
        # ===== 第1组：最小规模基础测试 =====
        n = MIN_N
        m = min(n, 5)  # 如果有第二个参数

    elif i == 2:
        # ===== 第2组：边界情况 - 全相等元素 =====
        n = max(10, MIN_N)
        m = n

    elif i == 3:
        # ===== 第3组：边界情况 - 已排序 / 逆序 =====
        n = 100
        m = randint(1, n)

    elif 4 <= i <= 6:
        # ===== 第4~6组：中等规模随机 =====
        n = randint(500, 5000)
        m = randint(1, min(n, 100))

    elif 7 <= i <= 8:
        # ===== 第7~8组：大规模性能压力 =====
        n = randint(MAX_N // 2, MAX_N)
        m = randint(1, n)

    else:  # i == 9 or i == 10
        # ===== 第9~10组：极端边界 =====
        n = MAX_N
        m = n // 2 if i == 9 else n

    # ========== 写入输入数据（根据题目格式修改）==========

    _io.input_writeln(n)  # ✅ 使用新版 API: input_writeln

    # 示例：第二行写 n 个整数
    if i == 2:  # 全相等
        val = randint(MIN_VAL, MAX_VAL)
        arr = [val] * n
    elif i == 3:  # 已排序升序
        arr = sorted([randint(MIN_VAL, MAX_VAL) for _ in range(n)])
    elif i == 4:  # 逆序
        arr = sorted([randint(MIN_VAL, MAX_VAL) for _ in range(n)], reverse=True)
    else:  # 随机
        arr = [randint(MIN_VAL, MAX_VAL) for _ in range(n)]

    # ✅ 使用新版 API: input_writeln(*arr) 展开数组
    _io.input_writeln(*arr)

    # ====================================================

    # 可选：使用标程直接生成输出（✅ 新版 API: output_gen）
    # _io.output_gen("./std")


def main():
    """主函数：遍历所有测试点并生成"""

    print(f"开始生成 {PROBLEM_NAME} 的测试数据 ({DATA_COUNT} 组)")
    print(f"输出目录: {os.path.abspath(OUTPUT_DIR)}")

    # 创建输出目录
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for i in range(1, DATA_COUNT + 1):
        # 文件命名必须与 generate_data.py 约定一致：{i}.in / {i}.out
        _io = IO(f"{i}.in", f"{i}.out")
        generate_test_point(i, _io)

        print(f"正在生成第 {i}/{DATA_COUNT} 组... -> {i}.in")

    print(f"\n✅ 成功生成 {DATA_COUNT} 个 .in 文件")


if __name__ == "__main__":
    main()
