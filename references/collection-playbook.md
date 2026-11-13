# 采集手册

目标：每个工作日在 60–90 分钟内产出一期「有出处、不重复、判断克制」的早报。

## 1. 时间窗与去重

- 主窗口：过去 **24 小时**；周末/节假日可放宽到 **48 小时**，并在导语里说明覆盖区间。
- 先在纸上（或临时文件）列「事件」而不是「文章」：同一件事的多篇报道只留信息量最大的一篇。
- 与上一期对比，已报过且没有新进展的事件不再写；有新进展就写「跟进」，并在摘要里点明新在哪。
- 日期核对：中文媒体常写「昨日」「日前」，务必换算成具体日期；跨时区的发布以官方稿时间为准。

## 2. 国际（Anthropic / OpenAI / Google / xAI / Apple）

优先一手来源，其次主流媒体：

| 公司 | 一手入口 | 常看媒体 |
| --- | --- | --- |
| Anthropic | `anthropic.com/news`、`claude.com/blog` | The Information、Reuters、TechCrunch、彭博 |
| OpenAI | `openai.com/news`、`openai.com/index` | The Verge、Wired、Reuters |
| Google | `blog.google/technology/ai/`、`deepmind.google/discover/blog` | 9to5Google、The Verge、TechCrunch |
| xAI | `x.ai/news`、X 上的 @xai / @grok | Reuters、The Verge |
| Apple | `apple.com/newsroom`、开发者文档更新 | 9to5Mac、MacRumors、彭博（Gurman） |

Apple 的关注面：Apple Intelligence 功能与国行进展、Siri 改版、端侧模型、AI 硬件与供应链、相关人事与监管。

## 3. 国内

常看：机器之心、量子位、36 氪、晚点 LatePost、财联社、界面新闻、澎湃科技、第一财经、新浪科技、IT 之家。
公司口径优先：DeepSeek、月之暗面（Kimi）、阿里云/通义、字节 Seed/豆包、腾讯混元、智谱、MiniMax、美团 LongCat、百度、商汤、科大讯飞。

检索关键词模板（中英各来一轮）：

```text
"Anthropic" OR "OpenAI" OR "Google DeepMind" news <日期>
"DeepSeek" OR "Kimi" OR "通义" OR "豆包" 发布 <日期>
"融资" OR "估值" AI <日期>
"AI Act" OR "芯片出口" OR "算力" <日期>
```

## 4. 其他动态

政策监管（欧盟 AI Act、美国出口管制、国内备案与标准）、芯片与算力（英伟达、台积电、存储、电力）、
机器人与具身智能、融资并购、论文与开源（arXiv 热门、Hugging Face 趋势、GitHub）。

## 5. 行情（直接调接口）

```bash
curl -s "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana&vs_currencies=usd&include_24hr_change=true"
curl -s https://api.gold-api.com/price/XAU
```

- 记录 BTC / ETH / SOL 的 USD 价格与 24h 涨跌幅；黄金、白银为现货 USD/oz。
- 时点统一写北京时间；两次取数间隔超过 30 分钟就重取一次。
- 解读只写「主导变量」（实际利率、流动性、风险偏好、ETF 流向），不要预测点位。

## 6. GitHub 热榜

```bash
python3 "$SKILL_DIR/scripts/fetch_trending.py" --limit 8 [--since daily|weekly|monthly]
```

- 输出 JSON：`repo`、`url`、`desc`、`lang`、`stars`、`today`。
- 需要补 `desc_zh`：先读懂仓库 README 的第一段，再用自己的话写「它是什么 + 解决什么问题」，40–70 字。
- 与 AI 无关的经典项目（react、rails）可以保留，但中文简介要说明它和当下 AI 工作流的关系，或直接换成更相关的前 8 名。

## 7. 网站推荐

- 来源：Product Hunt 日榜、Hacker News Show HN、少数派、GitHub Trending、Toolify、Futurepedia。
- **实测**：`curl -sI -m 10 <url>` 返回 200（或 30x 到 200）才可推荐。
- 最近 7 天推荐过的站点不要重复（可维护 `data/sites-history.json`，或人工比对）。
- 每条写清「它替读者省掉哪一步」，不要写「很强大、值得一试」这种空话。

## 8. 资本流向

可写的东西：融资额与估值、领投方、发债与信贷、capex 指引、IPO 定价与认购、数据中心与电力约束、
加密 ETF 净流入、黄金白银、国内产业资本入股与开源模型支出份额。

写法：
1. 先给一组「互相矛盾」的信号（例如一级市场抢份额、二级市场在卖）；
2. 分别解释两端的钱从哪来、要求什么回报；
3. 用同一口径的数字比较（同比/环比、占收入比、隐含估值倍数）；
4. 结尾给 2–3 个可验证的观察指标，不写投资建议。

## 9. 交付前自检

- [ ] 头条与各版不重复；国际五家都有条目或明确说明
- [ ] 每条都有原文链接，摘要 60–150 字
- [ ] 行情有价格、涨跌、时点、来源
- [ ] 模型动态都带 MM-DD 与出处；传闻有标注
- [ ] GitHub 8 条都有中文简介
- [ ] 网站 2–3 个，均实测 200，与近 7 天不重复
- [ ] 资本流向 ≥500 字，数字都能在本期其它位置对上
- [ ] `check_data.py` 无 error；`reports/latest.html` 已更新
