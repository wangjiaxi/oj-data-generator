# Cyaron 库完整参考 (v0.7.0)

Cyaron (CYaRon: Yet Another Random Olympic-iNformatics test data generator) 是一个用于生成 OJ 测试数据的 Python 库。

**最新版本**: v0.7.0
**项目地址**: https://github.com/luogu-dev/cyaron

## 安装

```bash
pip install cyaron>=0.7.0
```

> ⚠️ 版本要求：必须 v0.7.0+（当前最新版）。更早版本缺少 `weight_limit`、`Graph.flower()` 等新版 API。

### 随机种子（可复现）

cyaron 的 `randint` 等函数基于 Python `random` 模块。主流程 `generate_data.py --seed N` 会通过环境变量 `CYARON_SEED` 传入，模板脚本需在开头执行：

```python
import os, random
_seed = os.environ.get("CYARON_SEED")
if _seed:
    random.seed(int(_seed))
```

### 文件命名约定

主流程 `generate_data.py` 要求数据文件命名为 `1.in`~`N.in` / `1.out`~`N.out`，因此生成脚本中应使用：

```python
_io = IO(f"{i}.in", f"{i}.out")   # ✅ 与主流程约定一致
```

不要使用 `IO(file_prefix="data", data_id=i)`，那会生成 `data1.in` 而不是 `1.in`，导致 .out 无法生成。

## 核心模块导入

```python
from cyaron import *
```

---

## IO 类 - 输入输出管理

### 创建 IO 对象

```python
# 方式1：直接指定输入输出文件名
_io = IO("test1.in", "test1.out")

# 方式2：使用文件前缀（默认生成 test.in, test.out）
_io = IO(file_prefix="test")

# 方式3：带数据编号的批量生成（生成 test3.in, test3.out；仅限独立运行，配合 generate_data.py 时请用上方命名约定）
_io = IO(file_prefix="data", data_id=i)

# 方式4：自定义后缀（生成 test6.input, test6.answer）
_io = IO(file_prefix="test", data_id=6, input_suffix=".input", output_suffix=".answer")

# 方式5：只生成输入文件，输出为临时文件
_io = IO("test2.in")

# 方式6：禁用输出文件生成（仅生成 test5.in）
_io = IO(file_prefix="test", data_id=5, disable_output=True)
```

**构造函数参数**:
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `file_prefix` | str | - | 文件名前缀 |
| `data_id` | int | - | 数据点编号 |
| `input_suffix` | str | `.in` | 输入文件后缀 |
| `output_suffix` | str | `.out` | 输出文件后缀 |
| `disable_output` | bool | `False` | 是否禁用输出文件 |

### 写入数据方法 ✅ v0.7.0 语法

| 方法 | 说明 | 示例 |
|------|------|------|
| `_io.input_write(*args)` | 写入数据（不换行），默认空格分隔 | `_io.input_write(1, 2, 3)` → `1 2 3` |
| `_io.input_writeln(*args)` | 写入数据并换行 | `_io.input_writeln(1, 2, 3)` → `1 2 3\n` |
| `_io.output_write(*args)` | 写入输出文件（不换行） | `_io.output_write(42)` |
| `_io.output_writeln(*args)` | 写入输出文件并换行 | `_io.output_writeln(100)` |

> **重要变更**: 旧版使用 `_io.write()` / `_io.write_writeln()` / `_io.write_vec()`，新版已统一为 `input_*` 前缀。

### 获取程序输出 ✅ v0.7.0 新方法

```python
# 调用标程生成 .out 文件（推荐方式）
_io.output_gen("./std")                    # 运行可执行文件
_io.output_gen("C:\\Users\\user\\std.exe") # Windows 路径

# 直接写入图结构到输入文件
graph = Graph.graph(n, m, weight_limit=5)
_io.input_writeln(graph)                   # 自动输出 u v w 格式
```

### 完整示例

```python
from cyaron import *

for i in range(1, 11):
    _io = IO(file_prefix="data", data_id=i)
    
    n = randint(1, 100)
    m = randint(1, n)
    
    # 写入第一行：n 和 m
    _io.input_writeln(n, m)
    
    # 写入第二行：n 个随机整数
    arr = [randint(1, 1000) for _ in range(n)]
    _io.input_writeln(*arr)
    
    # 使用标程生成输出
    _io.output_gen("./std")
```

---

## 随机数生成

### 基础随机数

```python
randint(a, b)           # 随机整数 [a, b] (闭区间)
randrange([a], b [, step])  # 随机整数（支持步长）
uniform(a, b)           # 随机实数 [a, b]
random()                # [0, 1) 范围的随机浮点数
choice(seq)             # 从序列中随机选择一个元素
```

### 数组/列表操作

```python
ati([0, 5, 100, 1E4])  # 将数组元素转为整型（支持科学计数法）
```

### 排列与组合

```python
perm(n)              # [1..n] 的随机排列
permu(n, start=0)    # [start..start+n-1] 的随机排列
```

### 序列生成器 ✅ v0.7.0 特性

```python
# 显式公式生成序列
seq = Sequence(lambda i, f: 2*i + 1)

# 递归公式生成序列（需要初始值）
seq = Sequence(lambda i, f: f(i-1) + f(i-2), [0, 1])  # 斐波那契数列

# 获取序列值
seq.get(3)            # 获取第3项
seq.get(4, 6)         # 获取第4~6项的列表
_io.input_write(seq.get(7, 10))  # 直接写入IO对象
```

---

## 图论结构 ✅ v0.7.0 API

### Graph 类基础

#### 手动建图

```python
# 初始化图
g = Graph(10)                 # 10个节点的无向图（节点从1开始编号）
g = Graph(10, directed=True)  # 有向图

# 添加边
g.add_edge(1, 5)              # 边权默认为1
g.add_edge(1, 6, weight=3)    # 指定边权为3

# 遍历边
for edge in g.iterate_edges():
    print(edge.start, edge.end, edge.weight)

# 输出图
print(g)                              # 默认格式：每行 "u v w"
print(g.to_str(shuffle=True))         # 打乱边顺序输出
print(g.to_str(output=Edge.unweighted_edge))  # 无权图格式："u v"
```

### 自动生成图（类方法）

所有方法均支持以下通用参数：
- `directed`: 是否有向图（默认 `False`）
- `weight_limit`: 边权限制（元组 `(min, max)` 或单个整数）
- `weight_gen`: 自定义权重生成函数
- `self_loop`: 是否允许自环（默认允许）
- `repeated_edges`: 是否允许重边（默认允许）

#### 常用图结构生成方法

```python
# ===== 随机图 =====
Graph.graph(n, m, weight_limit=5)              # n点m边随机图
Graph.graph(n, m, directed=True, weight_limit=(1, 100))  # 有向带权图

# ===== 树结构 =====
Graph.tree(n)                                   # 随机树
Graph.tree(n, 0.4, 0.35)                        # 40%链状 + 35%菊花状 + 25%随机
Graph.binary_tree(n)                             # 随机二叉树
Graph.chain(n)                                   # 链状结构 (等价于 tree(n, 1, 0))
Graph.flower(n)                                  # 菊花图 (等价于 tree(n, 0, 1))

# ===== 特殊图 =====
Graph.complete(n, weight_limit=5)               # 完全图
Graph.DAG(n, m)                                  # 有向无环图（默认连通）
Graph.DAG(n, m, loop=True)                       # 有环图
Graph.UDAG(n, m)                                 # 无向连通图（不支持 directed）
Graph.hack_spfa(n)                               # 卡SPFA的图（1.5n条边）
Graph.hack_spfa(n, extra_edge=m)                 # 卡SPFA + 额外m条边
```

### 图的使用示例

```python
from cyaron import *

for i in range(1, 11):
    _io = IO(file_prefix="data", data_id=i)
    
    n = randint(2, 100000)
    m = randint(n-1, min(n*(n-1)//2, 200000))
    
    _io.input_writeln(n, m)
    
    if i == 1:
        # 链状图
        graph = Graph.chain(n, weight_limit=10)
    elif i == 2:
        # 菊花图
        graph = Graph.flower(n, weight_limit=10)
    elif i == 3:
        # 完全二叉树
        graph = Graph.binary_tree(n, weight_limit=(1, 100))
    else:
        # 随机图
        graph = Graph.graph(n, m, weight_limit=(1, 1000))
    
    # 直接写入图结构
    _io.input_writeln(graph)
```

---

## 字符串生成

```python
randstr(length)                    # 随机小写字母字符串
randstr(length, charset="abc123")  # 指定字符集
randword(length)                   # 随机"单词"（首字母可能大写）
randsentence(word_count)           # 随机句子
randparagraph(sentence_count)       # 随机段落
```

---

## 高级功能

### 设置随机种子

```python
import random
random.seed(value)  # cyaron 没有自己的 seed()；它的 randint 等函数用的就是 random 模块的全局随机源
```

### 概率控制

```python
if probability(0.3):  # 30% 概率执行
    ...

weighted_choice([(item1, weight1), (item2, weight2)])  # 加权随机选择
```

---

## 多边形 ✅ v0.7.0 支持

```python
from cyaron import Polygon

p = Polygon(n)                    # 随机 n 边形
p.area                            # 面积
p.perimeter                       # 周长
p.vertices                        # 顶点坐标列表
```

---

## 对拍功能 ✅ v0.7.0 支持

```python
from cyaron import Compare

# 对比两个程序的输出
c = Compare("./std", "./brute")
c.run(IO("test.in"))              # 运行单组测试
c.run_many(100)                   # 自动运行多组测试并对比
```

---

## 完整示例：排序题测试数据生成（v0.7.0）

```python
#!/usr/bin/env python3
"""
排序题测试数据生成示例
使用 cyaron v0.7.0 最新语法
"""
from cyaron import *

for i in range(1, 11):
    _io = IO(file_prefix="data", data_id=i)
    
    # 设计测试点分布
    if i == 1:       # 最小规模
        n, m = 1, 1
    elif i == 2:     # m=n
        n, m = 5, 5
    elif i == 3:     # m=1
        n, m = 10, 1
    elif i <= 6:     # 中等规模随机
        n = randint(100, 1000)
        m = randint(1, min(n, 50))
    else:            # 大规模
        n = randint(50000, 100000)
        m = randint(1, n)
    
    _io.input_writeln(n, m)
    
    # 构造特殊数据
    if i == 4:       # 已排序升序
        arr = sorted([randint(1, 10**9) for _ in range(n)])
    elif i == 5:     # 逆序
        arr = sorted([randint(1, 10**9) for _ in range(n)], reverse=True)
    elif i == 6:     # 全相等
        val = randint(1, 10**9)
        arr = [val] * n
    else:            # 随机
        arr = [randint(1, 10**9) for _ in range(n)]
    
    # 使用 input_writeln 写入数组
    _io.input_writeln(*arr)
    
    # 调用标程生成输出
    _io.output_gen("./std")
```

---

## 旧版 vs 新版 API 对照表

| 功能 | 旧版语法 | v0.7.0 新语法 |
|------|----------|---------------|
| 创建 IO | `IO(f"{i}.in")` | `IO(file_prefix="data", data_id=i)` |
| 写入数据 | `_io.write(x)` | `_io.input_write(x)` |
| 写入+换行 | `_io.write_writeln(x)` | `_io.input_writeln(x)` |
| 写入向量 | `_io.write_vec(vec)` | `_io.input_writeln(*vec)` |
| 生成输出 | `_io.output_at(path, cmd)` | `_io.output_gen(cmd)` |
| 图权重参数 | `weight=(1, 10)` | `weight_limit=(1, 10)` |
| 星形图 | `Graph.star(n)` | `Graph.flower(n)` |
| 随机树参数 | `children_range=...` | `tree(n, chain_prob, flower_prob)` |

---

## 注意事项

1. **版本要求**: 必须安装 `cyaron>=0.7.0`（当前最新版）
2. **节点编号**: Graph 默认节点编号从 **1** 开始
3. **边的遍历**: 使用 `iterate_edges()` 方法获取 Edge 对象
4. **图的输出**: 可以直接将 Graph 对象传给 `input_writeln()`，自动格式化为 `u v w`
5. **临时文件模式**: `IO()` 不传参时创建全临时文件，适合对拍场景
6. **路径处理**: Windows 路径中的反斜杠需转义或使用原始字符串
