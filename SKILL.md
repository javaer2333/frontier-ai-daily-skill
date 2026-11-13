---
name: frontier-ai-daily
description: 每日前沿 AI 早报。采集过去 24–48 小时国际/国内 AI 动态、加密与贵金属行情、GitHub 热榜、资本流向、模型版本与网站推荐，写成结构化 JSON，再渲染成 AIHOT 风格的报纸版式单页 HTML（报头与报眼点阵日历、头版、每版两栏、上一期/下一期）。Use when the user asks for 每日 AI 早报、日报、AI 新闻汇总，或要按报纸版式生成/更新一份每日简报页面.
metadata:
  version: "1.0.0"
  date: "2026-11-13"
---

# 前沿 AI 早报（frontier-ai-daily）

把「今天 AI 圈发生了什么」变成一份可直接阅读、可离线打开的**报纸版式日报**：
采集 → 写 JSON → 渲染成单文件 HTML（报头 / 报眼 / 头版 / 各版两栏 / 翻页 / 本期完）。

> 本文件里的相对路径都相对**技能目录**（如 `~/.agents/skills/frontier-ai-daily/`）；
> 数据与产物写在**当前工作区**的项目目录（默认 `data/` 与 `reports/`）。

## 适用场景

- 「生成今天的 AI 早报」「每日 AI 新闻汇总」「把这周的 AI 动态整理成日报」
- 需要固定栏目：国际大厂 / 国内大厂 / 其他动态 / 行情 / 资本流向 / 模型版本 / GitHub 热榜 / 网站推荐
- 需要能直接发出去、看起来像报纸的 HTML（不是 Markdown 列表）
- 需要每天重复执行（挂到定时任务或 cron）

不适用：实时行情交易信号、长篇深度研报、需要登录/付费墙的内容抓取。

## 安装

```bash
git clone git@github.com:javaer2333/frontier-ai-daily-skill.git ~/.agents/skills/frontier-ai-daily
# Claude Code 用户也可以放到 ~/.claude/skills/frontier-ai-daily
```

依赖：Python 3.10+（标准库即可）；`fetch_trending.py` 建议装 `lxml`，没有会自动回退正则。

## 输入

| 项 | 默认 | 说明 |
| --- | --- | --- |
| 项目目录 | 当前工作区 | 建议 `ai-daily/`，内含 `data/`、`reports/` |
| 日期 | 今天（北京时间） | 文件名即 `YYYY-MM-DD.json`，页面按它排序 |
| 站名 | 前沿 AI 早报 | 用 `--site` 可换成别的行业名（如「法律 AI 日报」） |
| 出刊时间 | 每天 09:30 出刊 | 用 `--edition` 改；只影响文案，不影响排程 |

能从上下文推断的（站名、时区、是否补历史期）不要追问。**期号**按上一期 +1；补历史期时插到对应日期，渲染器会自动重排前后链接。

## 工作流

下面命令里的 `SKILL_DIR` 指技能目录，先设置一次：

```bash
SKILL_DIR=~/.agents/skills/frontier-ai-daily   # 按实际安装位置改
```

### 1. 采集（web_search + web_fetch）

检索过去 24 小时（可放宽 48 小时）：
- **国际**：Anthropic、OpenAI、Google、xAI、Apple（Apple Intelligence、Siri、端侧模型、AI 硬件供应链、人事与监管）
- **国内**：DeepSeek、Kimi、阿里千问、字节豆包、腾讯混元、智谱、MiniMax、美团 LongCat、百度等
- **其他**：政策监管、芯片算力、机器人与具身智能、融资并购、论文与开源

规则：去重、核对日期；每条必须有 `source.label` 与 `source.url`；数字不确定写「据媒体报道」；**不编造**。
国际五家每家都要有条目；当天确实没有，就写一条「今日无重大动态」并说明核实过的信息源。

明细与可用来源见 [references/collection-playbook.md](references/collection-playbook.md)。

### 2. 行情（用接口，不靠搜索）

```bash
curl -s "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana&vs_currencies=usd&include_24hr_change=true"
curl -s https://api.gold-api.com/price/XAU
```

记下数据时点（北京时间）与来源；拿不到写「暂缺」，不要编价格。涨跌用 `dir: up|down|flat`。

### 3. GitHub 热榜

```bash
python3 "$SKILL_DIR/scripts/fetch_trending.py" --limit 8
```

每个仓库写 `desc_zh`（40–70 字，说清「它是干什么的、解决什么问题」，不要直译堆术语；涉及 AI Agent 要明说），保留英文 `desc` 作副行。
脚本失败时把 `github.rows` 置空并在 `as_of` 说明原因。

### 4. 资本流动方向（≥500 字）

用已核实数字写「钱在往哪流」：一级市场融资/估值、信贷与发债、IPO 定价、电力与芯片等物理层、
加密 ETF 与贵金属、中国侧开源模型支出份额。结尾给 2–3 个「接下来盯什么」的指标。
没有新料可整节省略（渲染器会自动隐藏该版）。

### 5. 模型动态

只收录**模型本身**的更新：新模型/新版本、参数与上下文、定价、是否开放权重、关键基准、可用渠道。
必须写日期（MM-DD）；传闻标注「据传/未官宣」。一般 5–8 条；没有新版本就省略整节。

### 6. 网站推荐

2–3 个「科技 / 工具 / 好玩」站点，**用 curl 实测返回 200** 才能推荐；不与最近 7 天重复；每条 40–70 字说明它解决什么问题。

### 7. 写数据文件

写到项目的 `data/YYYY-MM-DD.json`。完整字段见 [references/data-schema.md](references/data-schema.md)，最小形态：

```jsonc
{
  "date": "2026-11-14", "weekday": "周六", "issue": 10, "generated_at": "2026-11-14 09:30",
  "headline": { "title": "", "text": "", "source": { "label": "", "url": "" } },
  "highlights": [ { "title": "", "source": {} } ],
  "international": [ { "company": "Anthropic", "items": [ { "title": "", "text": "", "source": {} } ] } ],
  "china": [ { "title": "", "text": "", "source": {} } ],
  "other": [ { "title": "", "text": "", "source": {} } ],
  "market": { "as_of": "", "source": "", "rows": [ { "name": "BTC", "price": "", "change": "", "dir": "down" } ], "note": "" },
  "capital": { "title": "", "as_of": "", "paragraphs": ["…"], "flows": [ { "label": "", "text": "" } ] },
  "models": { "as_of": "", "rows": [ { "region": "国际", "vendor": "OpenAI", "name": "", "date": "11-13", "text": "", "source": {} } ] },
  "github": { "as_of": "", "rows": [ { "repo": "", "url": "", "desc": "", "desc_zh": "", "lang": "", "stars": "", "today": "" } ] },
  "sites": { "as_of": "", "rows": [ { "name": "", "url": "", "tag": "工具", "desc": "" } ] },
  "takeaway": ""
}
```

`headline` 是当天最重要的一条，单独写，**不要与各版条目重复**。`highlights` 可选，不写就自动取各版首条。

### 8. 校验 + 渲染

```bash
SKILL_DIR=~/.agents/skills/frontier-ai-daily
python3 "$SKILL_DIR/scripts/check_data.py" data/2026-11-14.json
python3 "$SKILL_DIR/scripts/render.py" --data data/2026-11-14.json --out reports
```

渲染器会自动：生成当期、覆盖 `latest.html`、重建合订本 `index.html`、**回填所有历史期**
（左侧合订本栏、报眼点阵日历、上一期/下一期都会更新）。

常用参数：

```bash
--site "前沿 AI 早报" --motto "值得关注的 AI 动态" --edition "每天 09:30 出刊"
--no-history     # 只渲染当期，不回填
--index          # 只重建合订本
--css path.css   # 换一份样式
```

### 9. 交付

1. 用 `present` 交付 `reports/YYYY-MM-DD.html`（单文件、可离线打开）；
2. 聊天里只给精简版：今日头条、行情表（BTC/ETH/SOL/黄金）、GitHub 前 3（中文简介）、网站推荐、一句话观察；
3. 不重复全文，全文在 HTML 里。

## 产物

```
reports/
├── YYYY-MM-DD.html   当期（AIHOT 风格报纸页）
├── latest.html       最新一期
└── index.html        合订本（按月分组）
```

页面能力：报头三行 + 报眼（期号 / 大号日期点阵 / 当月日历，**有刊的日期可点击切期**）、
数据带（要闻数 / 来源数 / 阅读分钟）、头版（头条 + 今日看点 + 版面索引）、各版两栏、末版观察、
上一期/下一期、深浅色切换、打印样式。

## 质量红线

- 不编造新闻、数字、引语；不确定就标注来源口径。
- 每条都要有可点的原文链接；行情必须有数据时点。
- 不抄全文：摘要用自己的话，长度约 60–150 字。
- 站名与 Logo 用你自己的；**不要使用 AIHOT 的名字和 Logo**。
- GitHub 热榜必须有中文简介；网站推荐必须实测可访问。

## 排障

| 现象 | 处理 |
| --- | --- |
| 报「缺少样式文件」 | 确认 `styles/aihot.css` 在技能目录下，或显式 `--css` |
| 页面日期不更新 | `data/` 里没有当天 JSON；补上重跑 |
| 左侧合订本/点阵没更新 | 跑最新一期（默认回填全部）；或删掉对应 HTML 重跑 |
| 历史期缺版块 | `capital` / `models` / `github` / `sites` 为空时整节隐藏，属于正常 |
| GitHub 抓取失败 | 网络或页面结构变化；把 `github.rows` 置空并在 `as_of` 说明，不编数据 |

## 版式与版权

版式语言取自 [AIHOT](https://github.com/javaer2333/AIHOT)（MIT，Copyright © 2026 数字生命卡兹克）：
暖白纸面、墨色文字、一个青色强调、发丝线分隔。渲染器与样式是本技能的实现，不依赖 AIHOT 的
Node / PostgreSQL / Docker 服务。再分发时请保留 [NOTICE](NOTICE) 与 [LICENSE](LICENSE)。
