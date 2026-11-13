#!/usr/bin/env python3
"""把每天的早报 JSON 渲染成 AIHOT 风格的报纸版式 HTML。

版式取自 AIHOT 开源框架（MIT）：报头 + 报眼、数据带、头版（头条 + 今日看点 + 版面索引）、
每版两栏、发丝线分隔、上一期 / 下一期与本期完。样式在 style/aihot.css，渲染时内联进 HTML，
所以产物仍是可离线打开的单文件。

用法:
    python3 render.py data/2026-11-13.json               # 渲染该期，并回填历史各期与存档页
    python3 render.py data/2026-11-13.json --no-history  # 只渲染该期
    python3 render.py --index                            # 只重建合订本

产物:
    reports/YYYY-MM-DD.html   当期
    reports/latest.html       最新一期
    reports/index.html        合订本（全部存档）
"""
from __future__ import annotations

import calendar
import html
import json
import shutil
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent

WEEKDAYS_CN = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
DEFAULT_SITE = "前沿 AI 早报"
DEFAULT_MOTTO = "值得关注的 AI 动态"
DEFAULT_EDITION = "每天 09:30 出刊"
REPO_URL = "https://github.com/javaer2333/AIHOT"

ARROW_UP_RIGHT = (
    '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path d="M7 17 17 7M9 7h8v8"/></svg>'
)
ARROW_LEFT = (
    '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path d="M19 12H5M12 19l-7-7 7-7"/></svg>'
)
ARROW_RIGHT = (
    '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path d="M5 12h14M12 5l7 7-7 7"/></svg>'
)
THEME_ICON = (
    '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="1.7" stroke-linecap="round" aria-hidden="true">'
    '<circle cx="12" cy="12" r="4.2"/><path d="M12 2.5v2M12 19.5v2M4.4 4.4l1.4 1.4M18.2 18.2l1.4 1.4'
    'M2.5 12h2M19.5 12h2M4.4 19.6l1.4-1.4M18.2 5.8l1.4-1.4"/></svg>'
)
THEME_SCRIPT = (
    '<script>(function(){try{var t=localStorage.getItem("aihot-theme");'
    'if(!t)t=matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light";'
    'document.documentElement.setAttribute("data-theme",t)}catch(e){}})();</script>'
)
TOGGLE_SCRIPT = (
    '<script>(function(){var btn=document.querySelector(".theme-toggle");'
    'function apply(t){document.documentElement.setAttribute("data-theme",t);'
    'try{localStorage.setItem("aihot-theme",t)}catch(e){}}'
    'if(btn)btn.addEventListener("click",function(){apply('
    'document.documentElement.getAttribute("data-theme")==="dark"?"light":"dark")});})();</script>'
)


# ---------------------------------------------------------------- helpers

def esc(value) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def read_css(path: Path) -> str:
    if not path.exists():
        raise SystemExit(f"缺少样式文件：{path}")
    return path.read_text(encoding="utf-8")


def logo_html(site: str) -> str:
    """站名里的 AI 用强调色，其余保持墨色。"""
    if "AI" in site:
        head, _, tail = site.partition("AI")
        return f"{esc(head)}<em>AI</em>{esc(tail)}"
    return esc(site)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def source_of(item) -> tuple[str, str]:
    """(label, url) from a source dict or a bare string."""
    src = item.get("source") if isinstance(item, dict) else None
    if isinstance(src, dict):
        return str(src.get("label") or "来源"), str(src.get("url") or "")
    if isinstance(src, str):
        return "来源", src
    return "来源", ""


def avatar(label: str) -> str:
    ch = (label or "?").strip()[:1]
    return f'<span class="avatar" aria-hidden="true">{esc(ch.upper() if ch.isascii() else ch)}</span>'


def original_link(url: str) -> str:
    if not url:
        return ""
    return (
        f'<a class="original" href="{esc(url)}" target="_blank" rel="noopener noreferrer">'
        f"原文 {ARROW_UP_RIGHT}</a>"
    )


def story(item: dict, company: str | None = None) -> str:
    label, url = source_of(item)
    title = str(item.get("title") or "").strip()
    text = str(item.get("text") or "").strip()
    title_html = f'<a href="{esc(url)}" target="_blank" rel="noopener noreferrer">{esc(title)}</a>' if url else esc(title)
    meta = [avatar(label), f'<span class="source-name">{esc(label)}</span>']
    if company and company not in label:
        meta.append(f'<span class="badge badge-accent">{esc(company)}</span>')
    parts = [
        '<article class="story">',
        f'<div class="story-meta">{"".join(meta)}</div>',
        f"<h3>{title_html}</h3>" if title else "",
    ]
    if text:
        parts.append(f'<p class="summary">{esc(text)}</p>')
    foot = original_link(url)
    if foot:
        parts.append(f'<div class="story-foot">{foot}</div>')
    parts.append("</article>")
    return "".join(parts)


def rows_html(items: list[str]) -> str:
    if not items:
        return ""
    out = ['<div class="rows">']
    for i in range(0, len(items), 2):
        out.append('<div class="row">')
        out.extend(items[i:i + 2])
        out.append("</div>")
    out.append("</div>")
    return "".join(out)


def section(no: int, sid: str, label: str, count_text: str, body: str, note: str | None = None) -> str:
    note_html = f'<p class="page-note">{note}</p>' if note else ""
    return (
        f'<section class="page" id="{sid}" aria-labelledby="{sid}-t">'
        f'<header class="page-head"><span class="page-no">{no:02d}</span>'
        f'<h2 id="{sid}-t">{esc(label)}</h2>'
        f'<span class="page-count">{esc(count_text)}</span></header>'
        f"{note_html}{body}</section>"
    )


def collect_items(data: dict) -> list[dict]:
    """All editorial items in reading order (counts, sources, highlights)."""
    out: list[dict] = []
    for block in data.get("international") or []:
        out.extend(block.get("items") or [])
    out.extend(data.get("china") or [])
    out.extend(data.get("other") or [])
    return out


def unique_sources(data: dict) -> int:
    labels: set[str] = set()
    for item in collect_items(data):
        labels.add(source_of(item)[0])
    for row in (data.get("models") or {}).get("rows") or []:
        labels.add(source_of(row)[0])
    if (data.get("github") or {}).get("rows"):
        labels.add("GitHub")
    return len([x for x in labels if x and x != "来源"])


def reading_minutes(data: dict) -> int:
    chars = sum(len(str(i.get("text") or "")) + len(str(i.get("title") or "")) for i in collect_items(data))
    cap = data.get("capital") or {}
    chars += sum(len(str(p)) for p in cap.get("paragraphs") or [])
    chars += len(str(data.get("takeaway") or ""))
    chars += sum(len(str(r.get("text") or "")) for r in (data.get("models") or {}).get("rows") or [])
    return max(3, round(chars / 450))


def headline_of(issue: dict) -> str:
    h = issue.get("headline") or {}
    return str(h.get("title") or "").strip() or f"第 {issue.get('issue', '')} 期"


# ---------------------------------------------------------------- archive

def all_issues(data_dir: Path) -> list[dict]:
    rows = []
    for path in sorted(data_dir.glob("*.json")):
        try:
            data = load(path)
        except Exception:
            continue
        if not data.get("date"):
            continue
        rows.append({
            "key": data["date"],
            "issue": data.get("issue") or "",
            "title": headline_of(data),
            "count": len(collect_items(data)) + (1 if data.get("headline") else 0),
        })
    rows.sort(key=lambda r: r["key"])
    return rows


def archive_sidebar(issues: list[dict], current: str, site: str) -> str:
    groups: list[tuple[str, list[dict]]] = []
    for row in reversed(issues):
        month = row["key"][:7]
        if not groups or groups[-1][0] != month:
            groups.append((month, [row]))
        else:
            groups[-1][1].append(row)
    out = [
        '<aside class="archive" aria-label="日报合订本">',
        '<div class="archive-brand"><b>{}</b><span>合订本 · ARCHIVE</span></div>'.format(esc(site)),
    ]
    for month, rows in groups:
        yy, mm = month.split("-")
        out.append(f'<div class="archive-group">{yy} 年 {int(mm)} 月</div><ul class="archive-list">')
        for row in rows:
            cur = ' aria-current="page"' if row["key"] == current else ""
            out.append(
                f'<li><a href="{row["key"]}.html"{cur}>'
                f'<span class="archive-day num">{row["key"][8:10]}</span>'
                f'<span class="archive-title">{esc(row["title"])}</span></a></li>'
            )
        out.append("</ul>")
    out.append(
        '<div class="archive-foot">每天 09:30 出刊。<br>共 '
        f"{len(issues)} 期 · 版式取自 AIHOT 开源框架。</div>"
    )
    out.append("</aside>")
    return "".join(out)


def issue_dots(issue_key: str, issues: list[dict]) -> str:
    """报眼右侧的点阵日历：有刊的日期可以直接点进对应一期。"""
    y, m, d = (int(x) for x in issue_key.split("-"))
    prefix = f"{y:04d}-{m:02d}-"
    by_key = {row["key"]: row for row in issues if row["key"].startswith(prefix)}
    cells = []
    for day in range(1, calendar.monthrange(y, m)[1] + 1):
        key = f"{prefix}{day:02d}"
        row = by_key.get(key)
        if row:
            cls = "today" if key == issue_key else "on"
            label = f"{m} 月 {day} 日 · 第 {row['issue']} 期 · {row['title']}"
            current = ' aria-current="page"' if key == issue_key else ""
            cells.append(
                f'<a class="{cls}" href="{key}.html" title="{esc(label)}" '
                f'aria-label="{esc(label)}"{current}></a>'
            )
        else:
            cells.append(f'<i title="{m} 月 {day} 日 · 暂无" aria-hidden="true"></i>')
    return (
        '<div class="eye-dots">'
        f'<nav class="dots-grid" aria-label="{m} 月各期">{"".join(cells)}</nav>'
        f'<span class="dots-caption"><b>点日期切期</b> · {m} 月</span>'
        "</div>"
    )


# ---------------------------------------------------------------- page

def build_page(data: dict, issues: list[dict], site: str, motto: str, edition: str, css: str) -> str:
    key = data["date"]
    y, m, d = key.split("-")
    weekday = data.get("weekday") or WEEKDAYS_CN[date.fromisoformat(key).weekday()]
    keys = [r["key"] for r in issues]
    issue_no = data.get("issue") or (keys.index(key) + 1 if key in keys else 1)
    headline = data.get("headline") or {}
    h_title = str(headline.get("title") or "")
    h_text = str(headline.get("text") or "")
    h_label, h_url = source_of(headline)
    total = len(collect_items(data)) + (1 if h_title else 0)
    sources = unique_sources(data)
    minutes = reading_minutes(data)

    # --- 今日看点
    highlights: list[dict] = list(data.get("highlights") or [])[:3]
    if not highlights:
        candidates: list[dict] = []
        for block in (data.get("international") or [])[:2]:
            if block.get("items"):
                candidates.append(block["items"][0])
        candidates.extend((data.get("china") or [])[:1])
        candidates.extend((data.get("other") or [])[:1])
        seen: set[str] = set()
        for c in candidates:
            title = str(c.get("title") or "")
            if title and title != h_title and title not in seen:
                seen.add(title)
                highlights.append(c)
            if len(highlights) == 3:
                break

    # --- 各版
    sections: list[str] = []
    index_entries: list[tuple[str, str, str]] = []
    no = 0

    intl_items, intl_count = [], 0
    for block in data.get("international") or []:
        company = str(block.get("company") or "")
        for item in block.get("items") or []:
            intl_items.append(story(item, company=company))
            intl_count += 1
    if intl_items:
        no += 1
        sid = f"s-{no}"
        index_entries.append((sid, "国际", f"{intl_count} 条"))
        sections.append(section(no, sid, "国际", f"{intl_count} 条", rows_html(intl_items)))

    for field, label in (("china", "国内"), ("other", "其他动态")):
        rows = data.get(field) or []
        if not rows:
            continue
        no += 1
        sid = f"s-{no}"
        index_entries.append((sid, label, f"{len(rows)} 条"))
        sections.append(section(no, sid, label, f"{len(rows)} 条", rows_html([story(r) for r in rows])))

    market = data.get("market") or {}
    if market.get("rows"):
        no += 1
        sid = f"s-{no}"
        index_entries.append((sid, "市场行情", f"{len(market['rows'])} 项"))
        trs = []
        for row in market["rows"]:
            direction = str(row.get("dir") or "flat")
            cls = {"up": "dir-up", "down": "dir-down"}.get(direction, "dir-flat")
            arrow = {"up": " ↑", "down": " ↓"}.get(direction, "")
            trs.append(
                f'<tr><td class="name">{esc(row.get("name"))}</td>'
                f'<td class="price">{esc(row.get("price"))}</td>'
                f'<td class="{cls}">{esc(row.get("change"))}{arrow}</td></tr>'
            )
        note = str(market.get("note") or "")
        asof = " · ".join(x for x in [str(market.get("as_of") or ""), str(market.get("source") or "")] if x)
        body = (
            '<div class="market-wrap"><table class="market">'
            "<thead><tr><th>品种</th><th>价格</th><th>24 小时 / 日涨跌</th></tr></thead>"
            f'<tbody>{"".join(trs)}</tbody></table>'
            + (f'<p class="market-note">{esc(note)}</p>' if note else "")
            + (f'<p class="market-asof">{esc(asof)}</p>' if asof else "")
            + "</div>"
        )
        sections.append(section(no, sid, "市场行情", f"{len(market['rows'])} 项", body))

    capital = data.get("capital") or {}
    if capital.get("paragraphs"):
        no += 1
        sid = f"s-{no}"
        index_entries.append((sid, "资本流动方向", f"{len(capital['paragraphs'])} 段"))
        ps = "".join(f"<p>{esc(p)}</p>" for p in capital["paragraphs"])
        flows = capital.get("flows") or []
        flows_html = ""
        if flows:
            lis = "".join(
                f'<li><span class="flow-label">{esc(f.get("label"))}</span>'
                f'<span class="flow-text">{esc(f.get("text"))}</span></li>'
                for f in flows
            )
            flows_html = f'<ul class="flows">{lis}</ul>'
        cap_title = str(capital.get("title") or "")
        note_bits = [esc(cap_title)] if cap_title else []
        if capital.get("as_of"):
            note_bits.append(esc(capital["as_of"]))
        note = '<span class="accent">本版导读</span>' + " · ".join(note_bits) if note_bits else None
        body = f'<div class="prose" style="padding:22px 0 0">{ps}{flows_html}</div>'
        sections.append(section(no, sid, "资本流动方向", "综述", body, note=note))

    models = data.get("models") or {}
    if models.get("rows"):
        no += 1
        sid = f"s-{no}"
        index_entries.append((sid, "模型动态", f"{len(models['rows'])} 个"))
        lis = []
        for row in models["rows"]:
            region = str(row.get("region") or "")
            _, url_ = source_of(row)
            lis.append(
                '<li class="model">'
                f'<span class="model-region{" cn" if region == "国内" else ""}">{esc(region)}</span>'
                '<div><div class="model-head">'
                f'<span class="model-name">{esc(row.get("name"))}</span>'
                f'<span class="model-vendor">{esc(row.get("vendor"))}</span>'
                f'<span class="model-date">{esc(row.get("date"))}</span></div>'
                f'<p class="model-text">{esc(row.get("text"))}</p>'
                + (f'<div class="model-src">{original_link(url_)}</div>' if url_ else "")
                + "</div></li>"
            )
        body = f'<ul class="models" style="padding-top:8px">{"".join(lis)}</ul>'
        note = esc(models.get("as_of")) if models.get("as_of") else None
        sections.append(section(no, sid, "模型动态", f"{len(models['rows'])} 个", body, note=note))

    github = data.get("github") or {}
    if github.get("rows"):
        no += 1
        sid = f"s-{no}"
        index_entries.append((sid, "GitHub 热榜", f"{len(github['rows'])} 个"))
        lis = []
        for i, row in enumerate(github["rows"], start=1):
            top = " top" if i <= 3 else ""
            desc_zh = str(row.get("desc_zh") or "").strip()
            desc = str(row.get("desc") or "").strip()
            meta = " · ".join(
                x for x in [
                    str(row.get("lang") or ""),
                    f"{row.get('stars')} stars" if row.get("stars") else "",
                    f"+{row.get('today')} today" if row.get("today") else "",
                ] if x
            )
            show_orig = desc and desc != desc_zh and not any("\u4e00" <= ch <= "\u9fff" for ch in desc)
            lis.append(
                f'<li class="repo{top}"><span class="rank num">{i:02d}</span><div class="repo-body">'
                '<div class="repo-head">'
                f'<a class="repo-name" href="{esc(row.get("url"))}" target="_blank" rel="noopener noreferrer">{esc(row.get("repo"))}</a>'
                f'<span class="repo-lang">{esc(meta)}</span></div>'
                + (f'<p class="repo-desc">{esc(desc_zh)}</p>' if desc_zh else "")
                + (f'<p class="repo-orig">{esc(desc)}</p>' if show_orig else "")
                + "</div></li>"
            )
        body = f'<ul class="repos" style="padding-top:6px">{"".join(lis)}</ul>'
        note = esc(github.get("as_of")) if github.get("as_of") else None
        sections.append(section(no, sid, "GitHub 热榜", f"{len(github['rows'])} 个", body, note=note))

    sites = data.get("sites") or {}
    if sites.get("rows"):
        no += 1
        sid = f"s-{no}"
        index_entries.append((sid, "网站推荐", f"{len(sites['rows'])} 个"))
        lis = []
        for row in sites["rows"]:
            lis.append(
                '<div class="site">'
                f'<a class="site-name" href="{esc(row.get("url"))}" target="_blank" rel="noopener noreferrer">{esc(row.get("name"))}</a>'
                f'<span class="site-tag badge badge-amber">{esc(row.get("tag"))}</span>'
                f'<p class="site-desc">{esc(row.get("desc"))}</p>'
                f'<span class="site-url">{esc(row.get("url"))}</span></div>'
            )
        body = f'<div class="sites" style="padding-top:8px">{"".join(lis)}</div>'
        note = esc(sites.get("as_of")) if sites.get("as_of") else None
        sections.append(section(no, sid, "网站推荐", f"{len(sites['rows'])} 个", body, note=note))

    takeaway = str(data.get("takeaway") or "").strip()
    if takeaway:
        index_entries.append(("s-takeaway", "一句话观察", ""))
        sections.append(
            '<section class="page" id="s-takeaway" aria-labelledby="s-takeaway-t">'
            '<header class="page-head"><span class="page-no">末</span>'
            '<h2 id="s-takeaway-t">一句话观察</h2><span class="page-count">趋势判断</span></header>'
            f'<div class="closing"><div class="kicker">观察</div>'
            f"<blockquote>{esc(takeaway)}</blockquote>"
            f"<cite>—— {esc(site)} · 第 {issue_no} 期</cite></div></section>"
        )

    # --- 头版
    hl_html = ""
    if highlights:
        lis = []
        for i, h in enumerate(highlights, start=1):
            label_, url_ = source_of(h)
            lis.append(
                f'<li><span class="n num">{i:02d}</span><span>'
                f'<a class="t" href="{esc(url_)}" target="_blank" rel="noopener noreferrer">{esc(h.get("title"))}</a>'
                f'<span class="s">{esc(label_)}</span></span></li>'
            )
        hl_html = '<div class="kicker">今日看点</div><ol class="highlights">' + "".join(lis) + "</ol>"

    pages_html = ""
    if index_entries:
        lis = "".join(
            f'<li><a href="#{sid}"><span class="no">{i:02d}</span>'
            f'<span class="label">{esc(label_)}</span>'
            f'<span class="n">{esc(count)}</span></a></li>'
            for i, (sid, label_, count) in enumerate(index_entries, start=1)
        )
        pages_html = f'<nav class="pages" aria-label="本期版面"><div class="kicker">本期版面</div><ol>{lis}</ol></nav>'

    lead_meta = "".join([avatar(h_label), f'<span class="source-name">{esc(h_label)}</span>', original_link(h_url)])

    # --- 前后期
    pos = keys.index(key) if key in keys else -1
    title_map = {r["key"]: r["title"] for r in issues}
    neighbours = '<nav class="neighbours" aria-label="前后各期">'
    if pos > 0:
        pk = keys[pos - 1]
        neighbours += (
            f'<a class="neighbour prev" href="{pk}.html">'
            f'<span class="dir">{ARROW_LEFT} 上一期 · {pk}</span>'
            f'<span class="title">{esc(title_map.get(pk, ""))}</span></a>'
        )
    else:
        neighbours += '<span class="neighbour prev"></span>'
    if 0 <= pos < len(keys) - 1:
        nk = keys[pos + 1]
        neighbours += (
            f'<a class="neighbour next" href="{nk}.html">'
            f'<span class="dir">下一期 · {nk} {ARROW_RIGHT}</span>'
            f'<span class="title">{esc(title_map.get(nk, ""))}</span></a>'
        )
    else:
        neighbours += '<span class="neighbour next"></span>'
    neighbours += "</nav>"

    generated = str(data.get("generated_at") or "")
    meta_desc = (h_text or h_title)[:120]
    title_text = f"{site} · {key} 第 {issue_no} 期"

    return f"""<!doctype html>
<html lang="zh-CN" data-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="color-scheme" content="light dark">
<meta name="description" content="{esc(meta_desc)}">
<meta property="og:title" content="{esc(title_text)}">
<meta property="og:description" content="{esc(meta_desc)}">
<meta property="og:type" content="article">
<title>{esc(title_text)}</title>
{THEME_SCRIPT}
<style>{css}</style>
</head>
<body>
<a class="sr-only" href="#report-start">跳到正文</a>
<div class="shell">
{archive_sidebar(issues, key, site)}
<div class="paper-wrap">
<article class="paper" id="report-start">
<header class="masthead">
  <div class="masthead-top">
    <span class="date-line">{y} 年 {int(m)} 月 {int(d)} 日 · {esc(weekday)}</span>
    <span class="motto">{esc(motto)}</span>
    <span class="edition">{esc(edition)}</span>
  </div>
  <div class="nameplate-row">
    <div class="nameplate">
      <h1 class="logo">{logo_html(site)}</h1>
      <p class="imprint">FRONTIER AI DAILY · 第 {issue_no} 期</p>
    </div>
    <div class="eye" aria-label="本期报眼">
      <div class="eye-date">
        <span class="eye-issue">第 {issue_no} 期</span>
        <span class="eye-figure num">{int(d)}</span>
        <span class="eye-year">{y} 年 {int(m)} 月</span>
        <span class="eye-week">{esc(weekday)}</span>
      </div>
      {issue_dots(key, issues)}
    </div>
  </div>
  <div class="metrics">
    <span class="metric"><b class="num">{total}</b><span>件要闻</span></span>
    <span class="metric"><b class="num">{sources}</b><span>个来源</span></span>
    <span class="metric"><b class="num">{minutes}</b><span>分钟读完</span></span>
    <span class="metric-read">{esc(edition)} · 全部原文可点</span>
  </div>
</header>

<section class="front" aria-label="头版">
  <div class="lead">
    <div class="kicker">头条</div>
    <h2>{esc(h_title)}</h2>
    {f'<p class="dek">{esc(h_text)}</p>' if h_text else ''}
    <div class="lead-meta">{lead_meta}</div>
  </div>
  <aside class="front-aside" aria-label="看点与版面">
    {hl_html}
    {pages_html}
  </aside>
</section>

{''.join(sections)}

{neighbours}

<footer class="colophon">
  <div class="end">（本期完）</div>
  <p>{esc(site)}根据公开报道自动整理，每条都附原文 · 行情为快照，不构成投资建议<br>
  版式取自 <a href="{REPO_URL}" target="_blank" rel="noopener">AIHOT 开源框架</a> · <a href="index.html">日报合订本</a></p>
  {f'<p>生成于 {esc(generated)}</p>' if generated else ''}
</footer>
</article>
</div>
</div>
<button class="theme-toggle" type="button" aria-label="切换深浅色" title="切换深浅色">{THEME_ICON}</button>
{TOGGLE_SCRIPT}
</body>
</html>
"""


def build_index(issues: list[dict], site: str, edition: str, css: str) -> str:
    groups: list[tuple[str, list[dict]]] = []
    for row in reversed(issues):
        month = row["key"][:7]
        if not groups or groups[-1][0] != month:
            groups.append((month, [row]))
        else:
            groups[-1][1].append(row)
    blocks = []
    for month, rows in groups:
        yy, mm = month.split("-")
        items = "".join(
            f'<li><a href="{row["key"]}.html"><span class="day num">{row["key"][8:10]}</span>'
            f'<span class="headline">{esc(row["title"])}</span>'
            f'<span class="meta">{esc(row["key"])} · 第 {esc(row["issue"])} 期 · {row["count"]} 件</span></a></li>'
            for row in rows
        )
        blocks.append(
            f'<section class="archive-month"><h2>{yy} 年 {int(mm)} 月</h2>'
            f'<ul class="archive-entries">{items}</ul></section>'
        )
    latest_key = issues[-1]["key"] if issues else ""
    latest = f'<a href="{latest_key}.html">最新一期</a>' if latest_key else ""
    return f"""<!doctype html>
<html lang="zh-CN" data-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>{esc(site)} · 日报合订本</title>
{THEME_SCRIPT}
<style>{css}</style>
</head>
<body class="archive-page">
<div class="shell">
<div class="paper-wrap">
<article class="paper">
<header class="masthead">
  <div class="masthead-top">
    <span>日报合订本 · ARCHIVE</span>
    <span>{esc(edition)}</span>
  </div>
  <div class="nameplate-row">
    <div class="nameplate">
      <h1 class="logo">{logo_html(site)}</h1>
      <p class="imprint">FRONTIER AI DAILY · 共 {len(issues)} 期</p>
    </div>
  </div>
  <p class="archive-lead">每天一份：国际与国内大厂动态、其他要闻、BTC / ETH / SOL 与金银行情、
  资本流向、模型版本、GitHub 热榜与网站推荐。点日期读当期，{latest}。</p>
</header>
<div class="archive-years">
{''.join(blocks)}
</div>
<footer class="colophon">
  <div class="end">（合订本）</div>
  <p>版式取自 <a href="{REPO_URL}" target="_blank" rel="noopener">AIHOT 开源框架</a></p>
</footer>
</article>
</div>
</div>
<button class="theme-toggle" type="button" aria-label="切换深浅色" title="切换深浅色">{THEME_ICON}</button>
{TOGGLE_SCRIPT}
</body>
</html>
"""


# ---------------------------------------------------------------- main

def main(argv: list[str]) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="render.py",
        description="把每日早报 JSON 渲染成 AIHOT 风格的报纸版式 HTML（可离线打开的单文件）。",
    )
    parser.add_argument("data", nargs="?", help="当日数据 JSON；不给则只配合 --index 使用")
    parser.add_argument("--data", dest="data_opt", metavar="JSON", help="同位置参数：当日数据 JSON")
    parser.add_argument("--out", help="产物目录（默认：数据文件同级的 reports/）")
    parser.add_argument("--data-dir", help="存档目录，扫描其中全部 JSON（默认：数据文件所在目录）")
    parser.add_argument("--site", default=DEFAULT_SITE, help=f"站名（默认：{DEFAULT_SITE}）")
    parser.add_argument("--motto", default=DEFAULT_MOTTO, help="报头格言")
    parser.add_argument("--edition", default=DEFAULT_EDITION, help="出刊时间文案")
    parser.add_argument("--css", help="样式文件路径（默认找脚本旁的 style/aihot.css 或 ../styles/aihot.css）")
    parser.add_argument("--no-history", action="store_true", help="只渲染当期，不回填历史页")
    parser.add_argument("--index", action="store_true", help="只重建合订本")
    args = parser.parse_args(argv[1:])

    css_path = Path(args.css) if args.css else (ROOT / "style" / "aihot.css")
    if not css_path.exists() and not args.css:
        alt = ROOT.parent / "styles" / "aihot.css"
        if alt.exists():
            css_path = alt
    css = read_css(css_path)

    data_arg = args.data_opt or args.data
    data_path = Path(data_arg) if data_arg else None
    if data_path is not None and not data_path.is_absolute():
        data_path = (Path.cwd() / data_path).resolve()
    data_dir = Path(args.data_dir) if args.data_dir else (data_path.parent if data_path else Path.cwd() / "data")
    if not data_dir.is_absolute():
        data_dir = (Path.cwd() / data_dir).resolve()
    out_dir = Path(args.out) if args.out else data_dir.parent / "reports"
    if not out_dir.is_absolute():
        out_dir = (Path.cwd() / out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.index:
        issues = all_issues(data_dir)
        (out_dir / "index.html").write_text(build_index(issues, args.site, args.edition, css), encoding="utf-8")
        print(f"已重建合订本：{out_dir / 'index.html'}")
        return 0

    if data_path is None:
        parser.print_help()
        return 2
    if not data_path.exists():
        raise SystemExit(f"找不到数据文件：{data_path}")

    data = load(data_path)
    issues = all_issues(data_dir)
    out = out_dir / f"{data['date']}.html"

    if args.no_history:
        out.write_text(build_page(data, issues, args.site, args.motto, args.edition, css), encoding="utf-8")
        print(f"已生成：{out}")
    else:
        for row in issues:
            path = data_dir / f"{row['key']}.json"
            page = build_page(load(path), issues, args.site, args.motto, args.edition, css)
            (out_dir / f"{row['key']}.html").write_text(page, encoding="utf-8")
        print(f"已生成：{out}（并回填 {len(issues)} 期历史页）")

    shutil.copyfile(out, out_dir / "latest.html")
    (out_dir / "index.html").write_text(build_index(issues, args.site, args.edition, css), encoding="utf-8")
    print(f"已更新：{out_dir / 'latest.html'}、{out_dir / 'index.html'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
