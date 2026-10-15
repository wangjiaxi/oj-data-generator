# 基线评估报告：oj-data-generator

评估日期：2026-05-31
评估模式：dry_run + 代码审查

---

## 评分详情

### 结构维度（60分）

#### 1️⃣ Frontmatter质量（权重8）— 9/10 → 7.2分
- ✅ name 规范（kebab-case）
- ✅ 描述包含做什么 + 何时用 + 触发词
- ✅ ≤1024字符
- ⚠️ "一键生成"略有夸张，实际需多步操作

#### 2️⃣ 工作流清晰度（权重15）— 8/10 → 12分
- ✅ 6个步骤明确有序号
- ✅ 每步输入/输出清晰
- ✅ 有参考资源指引
- ⚠️ 缺少分支流程（如用户没提供数据范围怎么办）
- ⚠️ 缺少回退路径（cyaron安装失败、编译失败等）

#### 3️⃣ 边界条件覆盖（权重10）— 7/10 → 7分
- ✅ 测试点边界策略详尽
- ⚠️ 缺少对工具链异常的处理（cyaron未安装、C++编译器缺失、磁盘空间不足）
- ⚠️ 缺少对用户输入不完整/歧义的处理

#### 4️⃣ 检查点设计（权重7）— 5/10 → 3.5分
- ✅ 有第6步交付验证
- ⚠️ 关键决策前缺少用户确认（如测试点策略设计好后应让用户确认）
- ⚠️ 自动执行无暂停点
- ⚠️ 生成脚本全部自动化，用户无干预机会

#### 5️⃣ 指令具体性（权重15）— 7/10 → 10.5分
- ✅ cyaron API用法有具体代码示例
- ✅ 测试点分布表清晰
- ✅ 有模板文件可参考
- ❌ **references/common_patterns.md 大量使用旧版API**（9处 write_writeln、3处 write_vec、Graph.star/rand_tree/complete_graph、8处 weight=），与SKILL.md宣称的v0.7.0不一致
- ⚠️ generate_data.py 路径逻辑依赖"当前目录"，易混淆

#### 6️⃣ 资源整合度（权重5）— 9/10 → 4.5分
- ✅ references/ 和 scripts/ 路径正确可访问
- ✅ 模板文件齐全
- ⚠️ SKILL.md 中的 cyaron 速查与 cyaron_guide.md 大量重复

### 效果维度（40分）

#### 7️⃣ 整体架构（权重15）— 7/10 → 10.5分
- ✅ 结构层次清晰
- ✅ 中文为主，符合花叔风格
- ❌ **common_patterns.md 与 SKILL.md 的 API 版本矛盾**，这是核心质量问题
- ⚠️ SKILL.md 的 cyaron 部分与 references/ 内容高度重复

#### 8️⃣ 实测表现（权重25）— 7/10 → 17.5分（dry_run）
- ✅ 流程设计合理
- ⚠️ generate_data.py 中 run_cyaron_generator 用 cwd=output_dir 运行脚本，但 cyaron 脚本路径是调用前解析的，可能路径不一致
- ⚠️ gen_data_template.py 的 OUTPUT_DIR 硬编码为脚本所在目录，与主脚本的 output_dir 参数可能冲突
- ⚠️ 标程搜索逻辑在当前目录查找，但用户可能在任意目录运行

---

## 总分：72.7 / 100

| 维度 | 得分 | 权重 | 加权得分 |
|------|------|------|---------|
| 1. Frontmatter质量 | 9 | 8 | 7.2 |
| 2. 工作流清晰度 | 8 | 15 | 12.0 |
| 3. 边界条件覆盖 | 7 | 10 | 7.0 |
| 4. 检查点设计 | 5 | 7 | 3.5 |
| 5. 指令具体性 | 7 | 15 | 10.5 |
| 6. 资源整合度 | 9 | 5 | 4.5 |
| 7. 整体架构 | 7 | 15 | 10.5 |
| 8. 实测表现 | 7 | 25 | 17.5 |
| **总分** | | **100** | **72.7** |

## 关键问题（按优先级）

### P0：API 版本不一致（维度5、7）
`references/common_patterns.md` 大量使用 cyaron 旧版 API（v0.7.0 之前的写法），而 SKILL.md 明确要求 v0.7.0。用户参考 common_patterns.md 会写出不兼容的代码。

**涉及范围**：25处旧API使用（write_writeln×9、write_vec×3、star×2、rand_tree×2、complete_graph×1、weight=×8）

### P1：路径依赖模糊（维度8）
`generate_data.py` 的 `find_cyaron_script()` 和 `find_std_program()` 依赖"当前目录"，在自动化流程中容易定位失败。cyaron 脚本用 `cwd=output_dir` 运行但路径在运行前解析，可能不一致。

### P2：缺少检查点（维度4）
全自动化流程缺少用户确认环节，用户无法在关键节点（如测试点策略确认）进行干预。

### P3：内容重复（维度6、7）
SKILL.md 中的 cyaron 使用说明与 `references/cyaron_guide.md` 大量重复，应精简 SKILL.md 并引导用户查阅 references。
