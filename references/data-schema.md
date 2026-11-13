# 数据结构（data/YYYY-MM-DD.json）

一个 JSON 对应一期。文件名必须等于 `date`；渲染器按文件名排序生成合订本与前后期链接。

## 顶层

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `date` | string | ✅ | `YYYY-MM-DD`（北京时间）。与文件名一致 |
| `weekday` | string | ✅ | `周一`…`周日`；不写会按日期推算 |
| `issue` | number | ✅ | 期号，从 1 递增；补历史期时按日期先后重排即可 |
| `generated_at` | string | ✅ | 生成时间，如 `2026-11-13 09:30` |
| `headline` | object | ✅ | 当天最重要一条：`title`、`text`、`source` |
| `highlights` | object[] | 可选 | 头版「今日看点」3 条：`title`、`source`；缺省自动取国际/国内/其他各版首条 |
| `international` | object[] | ✅ | 按公司分组：`{company, items:[…]}`，建议覆盖 Anthropic / OpenAI / Google / xAI / Apple |
| `china` | object[] | ✅ | 国内条目数组，每条 `{title, text, source}` |
| `other` | object[] | ✅ | 其他动态，同上 |
| `market` | object | ✅ | 行情，见下 |
| `capital` | object | 可选 | 资本观察，见下；固定渲染为最后一版，为空则整版隐藏 |
| `models` | object | 可选 | 模型动态，见下；为空则整版隐藏 |
| `github` | object | 可选 | GitHub 热榜，见下 |
| `sites` | object | 可选 | 网站推荐，见下 |

## 条目（story）

`headline`、`international[].items[]`、`china[]`、`other[]` 共用：

```jsonc
{
  "title": "一句话说清发生了什么（15–30 字，结论先行）",
  "text": "60–150 字的摘要：谁、做了什么、关键数字、为什么重要",
  "source": { "label": "媒体名", "url": "https://原文链接" }
}
```

- `source` 也可以只写 URL 字符串，渲染器会显示「来源」。
- 标题不要堆术语；数字必须与来源一致；不确定的加「据媒体报道」。
- 同一件事只写一条；不同公司的同一事件可分别挂在各自公司下，但摘要不要复制粘贴。

## market

```jsonc
{
  "as_of": "行情时点：2026-11-13 09:35（北京时间）",
  "source": "CoinGecko / gold-api.com",
  "rows": [
    { "name": "BTC", "price": "$71,051", "change": "−3.54%", "dir": "down" },
    { "name": "黄金 XAU/USD", "price": "$3,910.60/oz", "change": "−1.57%", "dir": "down" }
  ],
  "note": "一段解读：为什么涨/跌，哪个变量在主导"
}
```

- `dir`：`up`（红）/ `down`（绿）/ `flat`（灰）。
- `name` 建议固定：BTC、ETH、SOL、黄金 XAU/USD、白银 XAG/USD。
- 拿不到数据时 `rows` 置空、`note` 写「暂缺」及原因。

## capital

```jsonc
{
  "title": "一句本版标题（可省略，版面名固定为「资本观察」）",
  "as_of": "数据来源与汇总时间",
  "paragraphs": ["第一段", "第二段", "…"],   // 合计 ≥500 字，建议 6–9 段
  "flows": [ { "label": "关键数字", "text": "一句话解释" } ]  // 3–4 条，渲染为表格行
}
```

## models

```jsonc
{
  "as_of": "收录 11-10 以来有公开出处的版本更新 · 汇总于 2026-11-13 09:50（北京时间）",
  "rows": [
    {
      "region": "国际",            // 国际 | 国内
      "vendor": "OpenAI",
      "name": "GPT-6.2",
      "date": "11-12",             // MM-DD，必须写
      "text": "参数/上下文、定价、是否开放权重、关键基准、可用渠道",
      "source": { "label": "OpenAI", "url": "" }
    }
  ]
}
```

## github

```jsonc
{
  "as_of": "热榜抓取：2026-11-13 09:35（北京时间）· 来源 github.com/trending（daily）",
  "rows": [
    {
      "repo": "owner/name",
      "url": "https://github.com/owner/name",
      "desc": "English description",
      "desc_zh": "40–70 字中文：它是干什么的、解决什么问题",
      "lang": "Python",
      "stars": "12,345",
      "today": "678"               // 今日新增 star，纯数字/逗号
    }
  ]
}
```

## sites

```jsonc
{
  "as_of": "站点均于 2026-11-13 09:50 实测返回 200 · 每天换新",
  "rows": [
    { "name": "Excalidraw", "url": "https://excalidraw.com", "tag": "工具", "desc": "40–70 字说明它解决什么问题" }
  ]
}
```

`tag` 建议：工具 / 科技 / 好玩 / 论文。

## 渲染命令

```bash
python3 "$SKILL_DIR/scripts/check_data.py" data/2026-11-14.json
python3 "$SKILL_DIR/scripts/render.py" --data data/2026-11-14.json --out reports
```

产物：`reports/2026-11-14.html`、`latest.html`、`index.html`，并回填历史各期。
