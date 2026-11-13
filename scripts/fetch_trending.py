#!/usr/bin/env python3
"""抓取 GitHub Trending（daily），输出 JSON。

用法:
    python3 fetch_trending.py                # 打印 JSON 数组
    python3 fetch_trending.py --limit 8      # 只要前 8 条
    python3 fetch_trending.py --since weekly # daily / weekly / monthly

依赖: lxml（只用于解析，失败时回退到正则）
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)


def fetch(since: str = "daily") -> str:
    url = f"https://github.com/trending?since={since}"
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en"})
    with urllib.request.urlopen(req, timeout=25) as resp:
        return resp.read().decode("utf-8", "replace")


def parse_lxml(html: str) -> list[dict]:
    from lxml import html as LH

    doc = LH.fromstring(html)
    out: list[dict] = []
    for art in doc.xpath('//article[contains(@class,"Box-row")]'):
        link = art.xpath('.//h2//a/@href')
        if not link:
            continue
        repo = link[0].strip("/")
        desc = art.xpath('.//p[contains(@class,"color-fg-muted")]/text()')
        lang = art.xpath('.//span[@itemprop="programmingLanguage"]/text()')
        stars = art.xpath('.//a[contains(@href,"/stargazers")]/text()')
        today_txt = ""
        for sp in art.xpath('.//span[contains(@class,"float-sm-right")]'):
            t = re.sub(r"\s+", " ", "".join(sp.itertext())).strip()
            if "star" in t:
                today_txt = t
                break
        out.append(
            {
                "repo": repo,
                "url": f"https://github.com/{repo}",
                "desc": " ".join(d.strip() for d in desc).strip(),
                "lang": lang[0].strip() if lang else "",
                "stars": stars[0].strip() if stars else "",
                "today": re.sub(r"[^\d,]", "", today_txt),
            }
        )
    return out


def parse_regex(html: str) -> list[dict]:
    out = []
    for block in re.split(r'<article class="Box-row"', html)[1:]:
        m = re.search(r'<h2[^>]*>.*?<a href="/([^"]+)"', block, re.S)
        if not m:
            continue
        repo = m.group(1).strip("/")
        d = re.search(r'<p class="[^"]*color-fg-muted[^"]*"[^>]*>(.*?)</p>', block, re.S)
        lang = re.search(r'itemprop="programmingLanguage"[^>]*>([^<]+)<', block)
        stars = re.search(r'href="/[^"]+/stargazers"[^>]*>\s*([\d,\.k]+)\s*<', block)
        today = re.search(r"([\d,]+)\s+stars\s+today", block)
        out.append(
            {
                "repo": repo,
                "url": f"https://github.com/{repo}",
                "desc": re.sub(r"<[^>]+>", "", d.group(1)).strip() if d else "",
                "lang": lang.group(1).strip() if lang else "",
                "stars": stars.group(1).strip() if stars else "",
                "today": f"{today.group(1)} stars today" if today else "",
            }
        )
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--since", default="daily", choices=["daily", "weekly", "monthly"])
    args = ap.parse_args()

    html = fetch(args.since)
    try:
        rows = parse_lxml(html)
    except Exception:  # noqa: BLE001 - 解析失败时退回正则
        rows = parse_regex(html)
    if not rows:
        print("[]")
        return
    json.dump(rows[: args.limit], sys.stdout, ensure_ascii=False, indent=1)
    print()


if __name__ == "__main__":
    main()
