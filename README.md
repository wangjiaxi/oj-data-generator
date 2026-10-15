# oj-data-generator

给 OJ 算法题造测试数据的 Claude Code 技能。它读题面、判断题型，用 [cyaron](https://github.com/luogu-dev/cyaron) 生成 10 组 `.in`，再跑标程得到 `.out`。默认输出一个文件夹，要求打包时才出 ZIP。具体流程见 [SKILL.md](SKILL.md)。

## 安装

需要 Python 3 和 cyaron 0.7.0 以上：

```bash
pip3 install "cyaron>=0.7.0"
git clone https://github.com/wangjiaxi/oj-data-generator.git ~/.claude/skills/oj-data-generator
```

也可以直接对 Claude 说：「帮我安装这个技能 https://github.com/wangjiaxi/oj-data-generator 」。

没有 git 的话，在 GitHub 页面点 Code → Download ZIP，解压后把文件夹改名为 `oj-data-generator`，放进 `~/.claude/skills/`。

之前从 skillhub 装过 1.2.0 或更早版本的：那些版本还没有新版提示功能，要先把旧的 `~/.claude/skills/oj-data-generator` 移走，按上面的方法重装一次。之后就能自动收到更新提示了。

## 新版本提示

每次用这个技能，Claude 都会先看一下 GitHub 上有没有新版。1 小时内只联网检查一次，连不上就跳过，不影响使用。有新版时，它会告诉你版本号和更新内容，你同意后它会运行：

```bash
python3 ~/.claude/skills/oj-data-generator/scripts/update.py
```

- git clone 装的：执行 `git pull`。如果你在本地改过技能文件，它会停下来提醒，不会覆盖你的改动。
- 下载 ZIP 或从 skillhub 装的：下载新版整体替换，旧版备份在 `~/.cache/oj-data-generator/backup/`。

不想检查更新的话，设置环境变量 `OJ_DATA_GENERATOR_NO_UPDATE_CHECK=1`。

## 维护者：发布新版

改完技能后，在技能目录运行：

```bash
python3 scripts/release.py patch "修复 xxx" "新增 yyy"
```

第一个参数填 `patch` / `minor` / `major`，或者直接写版本号。后面每个参数是一条更新内容，会写进 CHANGELOG.md，别人收到的新版提示里显示的就是这几条。

脚本会依次跑测试、改 VERSION 和 CHANGELOG.md、提交、打 tag、推送。推送后，其他人最迟约 1 小时内使用技能时就会看到提示。

只改了 README 这类文件、不想打扰别人的话，正常 commit 和 push 就行，不用跑 release.py。

同步到 skillhub（可选）：先在终端登录一次 `skillhub login --key skh_你的令牌`，再运行：

```bash
python3 scripts/publish_skillhub.py
```

它会把当前版本连同 skillhub 页面上的名称、简介一起发上去。
