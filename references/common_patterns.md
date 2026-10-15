# 常见 OJ 题型及 Cyaron 数据生成模式

本文档记录各类算法题型的典型输入格式、边界情况和对应的 cyaron 代码片段。

---

## 1. 排序 / 选择问题

### 典型输入格式
```
n m
a1 a2 a3 ... an
```
输出前 m 大/小的数。

### 关键边界
- m = 1（只取一个）
- m = n（全排序）
- n = 1（单元素）
- 数组已有序（正序/逆序）
- 所有元素相同
- 元素达到极值（INT_MIN/INT_MAX）

### Cyaron 片段
```python
# 生成数组的不同模式
if mode == "sorted_asc":
    arr = sorted(randvec(n, L, R))
elif mode == "sorted_desc":
    arr = sorted(randvec(n, L, R), reverse=True)
elif mode == "all_equal":
    val = randint(L, R)
    arr = [val] * n
else:  # random
    arr = randvec(n, L, R)

_io.input_writeln(*arr)
```

---

## 2. 最短路径 (Dijkstra/Bellman-Ford/Floyd)

### 典型输入格式
```
n m s
u1 v1 w1
u2 v2 w2
...
um vm wm
```
求 s 到各点的最短距离。

### 关键边界
- **链状图**：`Graph.chain(n, weight_limit=(1, 100))` — 最短路退化成链
- **星形图**：`Graph.flower(n, weight_limit=(1, 100))` — 所有路径经过中心
- **稠密图**：`Graph.complete(n, weight_limit=(1, 100))` — 边数接近 n²
- **稀疏图**：m = n-1（树）
- **不连通图**：部分点不可达
- **负权边**：如果题目允许，需包含负权情况
- **自环/重边**：如果题目允许
- **0 权边**：特殊权重

### Cyaron 片段
```python
if mode == "chain":
    g = Graph.chain(n, weight_limit=(1, 1000))
elif mode == "star":
    g = Graph.flower(n, weight_limit=(1, 1000))
elif mode == "dense":
    g = Graph.complete(n, weight_limit=(1, 1000))
elif mode == "tree":
    g = Graph.tree(n, weight_limit=(1, 1000))
else:
    g = Graph.graph(n, m, weight_limit=(1, 1000))

_io.input_writeln(n, len(g.edges), s)
for u, v, w in g.edges:
    _io.input_writeln(u, v, w)
```

---

## 3. 最小生成树 (MST/Kruskal/Prim)

### 典型输入格式同最短路

### 关键边界
- 图本身是树（MST 就是原图）— 用 `Graph.tree()`
- 完全图（边数最多）
- 所有权值相同
- 权值差距极大（需注意精度/类型溢出）
- 不连通图（无 MST）

---

## 4. 并查集 / 连通性问题

### 典型输入格式
```
n m
op1 x1 y1
op2 x2 y2
...
```
操作类型：合并/查询。

### 关键边界
- 全部合并操作（最终一个集合）
- 全部查询操作（不修改）
- 合并形成链状/星状结构
- 查询已连接的点
- 查询未连接的点
- n=1（单元素集合）

---

## 5. 动态规划 (DP)

#### 5.1 背包问题

**输入格式**：
```
n W
w1 v1
w2 v2
...
wn vn
```

**边界**：
- W = 0（背包容量为 0）
- 所有物品重量为 1
- 所有物品重量等于 W（只能选一个或零个）
- 总重量刚好等于 W
- 总重量远超 W
- n = 0（无物品）

**Cyaron**：
```python
weights = randvec(n, 1, W)
values = randvec(n, 1, 10**9)
for j in range(n):
    _io.input_writeln(weights[j], values[j])
```

#### 5.2 LCS / 编辑距离 / 序列 DP

**输入格式**：
```
str1
str2
```
或
```
n m
a1 a2 ... an
b1 b2 ... bm
```

**边界**：
- 一个串/序列为空
- 两串完全相同
- 两串完全不同（无公共字符）
- 一串是另一串的子串
- 回文串 vs 非回文串
- 全相同字符的串

**Cyaron**：
```python
s1 = randstr(n)
s2 = randstr(m)
_io.input_writeln(s1)
_io.input_writeln(s2)
```

#### 5.3 区间 DP

**输入**：一个序列，求最优分割/合并方案。

**边界**：
- n = 1（无需操作）
- n = 2（只有一种操作方式）
- 所有元素相同
- 单调递增/递减序列

---

## 6. 数学问题

#### 6.1 GCD / LCM / 质数

**边界**：
- 两个数相等
- 一个数是另一个的倍数
- 互质（gcd = 1）
- 其中一个为 0 或 1
- 大质数
- 完全平方数 / 完全立方数

**Cyaron**：
```python
# 互质对
a = randint(1, 10**9)
b = randint(1, 10**9)
while math.gcd(a, b) != 1:
    b = randint(1, 10**9)

# 倍数关系
base = randint(1, 10**5)
k = randint(2, 10**4)
a, b = base, base * k
```

#### 6.2 快速幂 / 矩阵幂

**边界**：
- 指数 = 0（结果应为 1 或单位矩阵）
- 指数 = 1
- 底数 = 0 / 1 / -1
- 模数 = 2（最小的质数）
- 大指数（如 10^18）

#### 6.3 组合数学

**边界**：
- C(n, 0) = C(n, n) = 1
- C(n, 1) = n
- n 较大但 k 很小（或反之）
- 结果需要取模的情况

---

## 7. 数据结构题

#### 7.1 线段树 / 树状数组

**输入格式**：
```
n q
a1 a2 ... an
op1 x1 [y1]
op2 x2 [y2]
...
```
操作：单点修改+区间查询 / 区间修改+单点查询 等。

**边界**：
- n = 1
- 只查询不修改
- 只修改不查询
- 修改同一个位置多次
- 区间长度为 1 的查询
- 查询整个区间 [1, n]
- 交替增删操作

**Cyaron**：
```python
arr = randvec(n, -10**9, 10**9)
_io.input_writeln(*arr)

for _ in range(q):
    op = randint(1, 2)
    l = randint(1, n)
    r = randint(l, n)  # 确保 l <= r
    if op == 1:  # 修改
        val = randint(-10**9, 10**9)
        _io.input_writeln(op, l, r, val)
    else:  # 查询
        _io.input_writeln(op, l, r)
```

#### 7.2 单调栈 / 单调队列

**边界**：
- 单调递增序列（栈/队不会弹出）
- 单调递减序列（每次都弹出）
- 先增后减 / 先减后增（山峰/山谷）
- 所有元素相同

---

## 8. 字符串处理

#### 8.1 KMP / Z函数 / 字符串匹配

**输入**：
```
text
pattern
```

**边界**：
- pattern 比 text 长（无法匹配）
- pattern 是 text 的前缀/后缀
- pattern 在 text 中出现多次
- pattern = text
- pattern 为空
- text 为空
- 无匹配
- 全部匹配（text = pattern * k）

#### 8.2 Manacher（最长回文）

**边界**：
- 整串是回文
- 无长度 > 1 的回文（如 "abcdef"）
- 全相同字符（每个位置都是回文中心）
- 奇数长度 / 偶数长度最长回文
- 单字符串

#### 8.3 后缀自动机 / 后缀数组

**边界**：
- 所有字符相同（"aaaa..."）
- 所有字符不同（排列）
- 回文字符串
- 两个相同的串拼接
- 极短 / 极长字符串

**Cyaron**：
```python
# 所有字符相同
s = "a" * n
# 所有字符不同（当字符集足够大时）
s = "".join(chr(ord('a') + i) for i in range(n))
```

---

## 9. 搜索类 (DFS/BFS/状态压缩)

### 边界
- 起点即终点
- 无解情况
- 有唯一解
- 有多解（验证输出任意解即可）
- 最大深度搜索
- 状态空间极大（需要剪枝才能通过）

---

## 10. 图论其他

#### 10.1 拓扑排序

**边界**：
- 已经是有序的（DAG 形成链）
- 完全无序（每层节点数相近）
- 孤立节点（无入度无出度）
- 单节点
- 环（如果题目保证 DAG 则不需要）

**Cyaron（生成 DAG）**：
```python
# 通过给排列加边的方式构造 DAG
p = perm(n)
edges = []
for i in range(m):
    u = randint(1, n-1)
    v = randint(u+1, n)  # 保证 u 在 p 中排在 v 前
    edges.append((p[u-1], p[v-1]))
```

#### 10.2 强连通分量 / 2-SAT

**边界**：
- 本身就是强连通图
- 无环图（每个 SCC 大小为 1）
- 两个 SCC 串联
- SCC 大小呈链式递减

#### 10.3 网络流

**边界**：
- 无法从源点到汇点（流量为 0）
- 只有唯一一条路径
- 完全瓶颈（某条边容量限制了总流量）
- 所有边容量相同
- 大流量（注意数值范围）

---

## 11. 几何计算

**边界**：
- 共线点
- 重合点
- 垂直 / 平行线
- 面积为 0 的多边形
- 点在边界上（不是内部也不是外部）
- 最小/最大坐标值的极端情况
- 精度问题（浮点数误差）

---

## 12. T 组测试用例

很多题目有 T 组数据：

```
T
[n 组数据...]
```

**边界**：
- T = 1（退化成单组）
- T 达到上限
- 每组数据规模差异大（一组极小 + 一组极大）
- 所有组的答案相同
- 各组数据有不同的特殊情况

**Cyaron**：
```python
T = randint(1, 10)  # 或固定值
_io.input_writeln(T)

for _ in range(T):
    n = randint(1, 100)
    _io.input_writeln(n)
    _io.input_writeln(*randvec(n, 1, 10**9))
```
