# 更新日志

每个版本一节，最新的在最上面。`scripts/check_update.py` 会把用户当前版本之后的条目放进新版提示里，所以每条写成用户看得懂的一句话。发版用 `scripts/release.py`，它会自动在这里加一节。

## 1.3.0 - 2026-10-15

- 新增新版本提示：使用技能时自动检查 GitHub 上的版本，有新版会说明更新了什么，同意后一条命令更新（scripts/update.py）
- 修复不传 --output-dir（默认 ./output）或传相对路径时找不到 gen_data.py、直接报错的问题
- 修正 cyaron_guide.md 里不存在的 seed() 写法，改为 random.seed()
- 改到 GitHub 维护：https://github.com/wangjiaxi/oj-data-generator

## 1.2.0 - 2026-08-02

- 默认只输出文件夹，加 --zip 才打包，--zip-mode flat|folder 选择 ZIP 布局
- 生成后自动校验：文件齐全、非空、UTF-8，打包时校验 ZIP 完整性
- C++ 标程编译失败自动回退同目录的 Python 标程；--seed 固定种子可复现
- 新增 scripts/smoke_test.py 冒烟测试

更早的改动见 optimization-report.md。
