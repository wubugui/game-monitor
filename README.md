# game-monitor

每日游戏项目监控数据库（B 站 + X），网站：<https://wubugui.github.io/game-monitor/>

- `tracked_projects.md`：项目总表
- `state/`：每个项目一份档案 + 历次更新（用来做每日对比）
- `reports/`：每日日报，**永久保留，永不删除**
- `covers/`、`frames/`、`sheets/`、`x/`、`images/`：图片
- `data/`：网站用的 JSON，由脚本生成，**不要手改**
- `index.html` + `assets/`：网站本体（纯静态，GitHub Pages 从 main 分支根目录发布，`.nojekyll` 关闭 Jekyll）

## 每日任务怎么更新网站

写完当天的数据（日报、state、图片、总表）后，在仓库根目录执行：

```bash
bash scripts/publish.sh "YYYY-MM-DD：新增 N 个，更新 M 个"
```

它会依次：`git pull --rebase --autostash` → `python3 scripts/build_site.py` → 只 `git add` 数据目录（总表、state、reports、图片、data）→ 有变化才提交 → push。只想重建不提交时运行 `python3 scripts/build_site.py`。

`scripts/build_site.py` 只用 Python 标准库，可重复执行（每次整个重建 `data/`）。缺失的图片会以 `WARN` 打印到 stderr，不会中断。

## 数据格式约定

### 1. `tracked_projects.md`（总表）

一张 Markdown 表格，按表头名取列（列顺序随意，可加列）：

| 列 | 说明 |
|---|---|
| `名称` | 必填。竞品在名字前加 `⚠️ ` |
| `类型` | 自由文本，如 `中式民俗恐怖 ARPG`；网站会自动归到筛选标签（恐怖、民俗/国风、叙事/剧情、悬疑/解谜、互动影游、肉鸽/构筑、动作、RPG、模拟经营、策略、多人/合作、AI 驱动、工具/行业） |
| `开发者类型` | 以 `个人` / `小团队` / `中型厂商` / `大厂` / `未知` 开头，后面括号写具体名字 |
| `发现日期` | `YYYY-MM-DD` |
| `B站链接` 或 `链接` | 含 BV 号的 B 站链接，或 X 链接 |
| `备注` | 一句话 |
| 可选：`状态`、`最后更新`、`ID`、`来源` | |

项目 ID：链接里的 BV 号；没有 BV 号就用 `ID` 列；都没有则按名称生成。

### 2. `state/<ID>.md`（项目档案，推荐每个项目一份）

文件名用项目 ID（B 站项目就是 BV 号，X 项目用短英文名如 `akarolls`）。

```markdown
---
id: BV1mSa76yEor            # 与总表一致；也可以只写 name 由名称匹配
name: 乌合之众
competitor: true            # 竞品
genre: 中式民俗悬疑/黑色幽默剧情
developer: 小团队（NanZhai Games）
status: 即将发售            # 建议用：首曝 / 开发中 / Demo / 众筹中 / 抢先体验 / 即将发售 / 已发售 / 停更
platform: Steam
release: 2027-03
link: https://www.bilibili.com/video/BV1mSa76yEor
found: 2026-10-09
cover: covers/BV1mSa76yEor.jpg   # 可省略，默认找 covers|frames|sheets|x|images/<ID>.jpg
images: [frames/BV1mSa76yEor_1.jpg, frames/BV1mSa76yEor_2.jpg]   # 可省略，frames/<ID>_*.jpg 自动收录
tags: [恐怖, 民俗/国风]      # 可选，额外的筛选标签
aliases: [Fools, Maniacs and Liars]   # 可选，日报里的别名，用于把日报段落关联到项目
---
项目档案正文（题材、玩法、美术、团队、数据、玩家反应……），可以插图：
![](covers/BV1mSa76yEor.jpg)

## 2026-10-10 第二支 PV
当天更新的内容，可以插图。
![](frames/BV1mSa76yEor_2.jpg)

## 2026-10-09 首次发现
定档 2027 年 3 月。
```

规则：
- front matter 里的字段覆盖总表里的同名信息；没写 `status` 时网站根据备注推测，并在卡片上显示 `?`。
- 正文里第一个 `## YYYY-MM-DD 标题` 之前是档案；每个 `## YYYY-MM-DD ...` 是一条历史更新，**只追加，不要删旧条目**，新的写在最上面或最下面都行（网站按日期排序）。
- 项目的“最后更新”= 所有历史条目和日报提及中最新的日期。

### 3. `reports/YYYY-MM-DD.md`（日报）

- 文件名必须以日期开头（同一天多份可用 `2026-10-10-2.md`）。
- 可选 front matter：`title`、`summary`（首页摘要；不写就取第一段正文）。
- 第一行建议 `# 标题`；用 `## 竞品专区`、`## B 站全部游戏`、`## AI 新玩法`、`## X 海外亮点` 等二级标题分区（会生成目录）。
- 每个项目最好用 `### 项目名`（和总表名称一致，可带 `⚠️`）开一个小节，网站会把这一节自动挂到该项目的时间线上；用列表项写也能识别（列表项里出现项目名即可）。
- 图片用仓库相对路径：`![](covers/BVxxx.jpg)` 或 `![](../covers/BVxxx.jpg)` 都可以；也可用 `https://` 外链。
- 历史日报**永不删除、不改名**。

## 网站结构

- `#/` 首页：最新日报摘要、竞品专区、最近更新项目、往期日报
- `#/reports` 日报归档（按月分组，最新在前）；`#/report/<日期>` 单份日报（含目录、前后翻页、本期涉及项目）
- `#/projects` 项目库：竞品/类型/开发者/状态筛选、搜索、按更新或发现日期排序（筛选条件保存在网址里）
- `#/project/<ID>` 项目页：档案、画面、全部更新时间线
