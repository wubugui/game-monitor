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

`scripts/build_site.py` 只用 Python 标准库，可重复执行（每次整个重建 `data/`，并刷新首页「今日更新」列表）。缺失的图片会以 `WARN` 打印到 stderr，不会中断。`publish.sh` 会一并提交 `assets/`、`index.html`、`scripts/`，保证前端与数据同步上线。

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


### 4. 增量高亮（每日差分）

网站只高亮**最新一份日报日期**当天新写入的内容；已经在更早日报里出现过的内容保持普通样式，不会重复标黄。

**写法（state / 日报正文通用）：**

在每一段「首次写入」的事实、小节或截图**正上方**加一行 HTML 注释（保留在 Markdown 里）：

```markdown
<!-- added:2026-10-10 -->
- Steam 中文评测上线：特别好评（12 正 / 1 负）

<!-- added:2026-10-10 -->
![](frames/BV1xxx_05.jpg)
```

规则：
- `added` 日期 = 这条信息**第一次**写进仓库的日期（以后改措辞也不要改日期）。
- 建档日（第一份日报）把全部内容都标成当天的 `<!-- added:YYYY-MM-DD -->`，并在日报 front matter 写 `baseline: true`、标题带「初始版本」。
- **初始基线**：`baseline_only` 为真时，网站给这些块加「初始」灰标签，**不**黄底高亮（避免首日整页刷黄）。
- **次日及以后**：仅当 `added` == 最新日报日期时，显示黄底 + `NEW` 徽章；旧日期块不加样式。
- 历史条目 `## YYYY-MM-DD ...` 本身已按日期归档；条目内部新增句段仍用 `<!-- added:日期 -->` 标记。
- front matter 可写 `baseline: YYYY-MM-DD` 记录该项目的建档日。

`scripts/build_site.py` 会把 `baseline_only` / `latest_report_date` / `today_updates` 写入 `data/meta.json`；`assets/app.js` 首页用 `today_updates` 置顶「今日更新」，并在项目页与日报里根据注释包一层 `.added-block` 决定是否黄底高亮。


## 网站结构

- `#/` **首页「今日更新」**：只列当天 **新增** 或 **更新** 的游戏（竞品在前），带封面缩略图、一行变更说明，点进档案。未变动的旧项目不占首页，从「完整项目库」进入。其下是最新日报摘要与往期日报。
- `#/reports` 日报归档（按月分组，最新在前）；`#/report/<日期>` 单份日报（含目录、前后翻页、本期涉及项目）
- `#/projects` 项目库（完整数据库）：竞品/类型/开发者/状态筛选、搜索、按更新或发现日期排序（筛选条件保存在网址里）
- `#/project/<ID>` 项目页：档案、画面、全部更新时间线

### 首页「今日更新」怎么生成

每次 `python3 scripts/build_site.py`（`publish.sh` 会自动跑）会：

1. 读 `data/meta.json` 的 `latest_report_date`（最新日报日期）。
2. 扫每个 `state/<ID>.md` 里的 `<!-- added:YYYY-MM-DD -->` 标记，以及 `found` / `## YYYY-MM-DD` 历史条目。
3. **正常日**（日期晚于基线）：`found == 当天` → 新增；当天有新的 `added` 标记或 state 历史条目 → 更新。
4. **基线日 / 与基线同日的修订**：不把 100+ 份建档全堆上首页；只列最新日报涉及项、***、以及（若日报是竞品修订）全部竞品。
5. 结果写入 `meta.json` 的 `today_updates`（竞品优先）、`today_new` / `today_updated`、`today_banner`；`assets/app.js` 首页置顶渲染。

日常写档案时：只给**当天新写入**的块打 `<!-- added:当天日期 -->`；旧块不要改日期。这样第二天首页自然只高亮 diff。

## 每日任务硬规则（2026-10-09 修订）

1. **Step 0 必做**：启动后先只读刷新 `wubugui/***Story` 与 `wubugui/***`（`git fetch`/`pull`，**禁止**对这两仓 commit/push/PR/issue/触发 Actions），更新 `state/***.md`，再写任何竞品「综合评价」。
2. **只写 public 仓**：所有写入、提交、推送只针对 `wubugui/game-monitor`。
3. **档案正文化**：完整档案必须在正文里讲清楚内容；禁止用「去点这个链接」代替实质信息。链接最多当脚注。
4. **玩家评价**：必须有代表性原话与具体主题；禁止只用「好评/中评/差评」空标签。
5. **靠谱程度与综合评价必须看图**：用 Read 打开 `covers/`、`frames/`、`sheets/` 里的实际图片再写视觉判断，引用你看见的画面细节；禁止只根据文件名臆测。
6. **不编造**：查不到就写「未知」。
7. **增量高亮**：仅给当天新写入块打 `<!-- added:YYYY-MM-DD -->`；旧块不要改日期重盖章。

## 来源标记约定

每个 `state/*.md` 必须带来源信息（由 `scripts/backfill_sources.py` 回填，幂等，可重复运行；新项目建档时同样执行）：

- **front matter**：`discovery_platform`（B站 / 小红书 / X / Steam / TapTap / 用户指定 / 未知）、`discovery`（途径：B站搜索关键词「…」/ 相关视频滚雪 / 同名核验 / 每日发现，附种子视频标题 · UP · BV · 日期 · 播放）、`discovery_date`。查不到写「未知」，不编造。
- **文末「## 来源（发现与资料）」**：发现来源 + 资料来源清单（B站视频：标题 · UP主 · BV · 日期 · 播放；已剔除的同名/弱相关单独计数；Steam/TapTap/小红书/X/官网）。该节前置 `<!-- added:meta -->`，网页不作当日 diff 高亮。
- **行内标注**：「实际评价」里每条原话后加 `〔B站·BVxxx评论〕` `〔B站·BVxxx弹幕〕` `〔Steam评测〕` `〔小红书笔记〕`；「关注度与数据」节首注明数据口径。只按原始数据（tmp/comments、raw/steam、小红书扫描记录）匹配，匹配不到不打标签。
- **网页**：卡片和首页「今日更新」显示发现来源徽章；项目页显示「发现来源」；项目库可按发现来源筛选。

## 更新日志

- 2026-10-10：所有项目补充来源标记（元数据回填，不计入当日 diff 高亮）。
