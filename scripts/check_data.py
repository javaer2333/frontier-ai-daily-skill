#!/usr/bin/env python3
"""校验一期早报 JSON：结构、链接、必填字段与常用质量红线。

用法:
    python3 check_data.py data/2026-11-14.json
    python3 check_data.py                # 默认检查 data/ 里最新一期

退出码: 0 = 通过（可能有 warning），1 = 有 error，2 = 文件问题。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

DIRS = {"up", "down", "flat"}
COMPANIES = ["Anthropic", "OpenAI", "Google", "xAI", "Apple"]
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MMDD_RE = re.compile(r"^(0?[1-9]|1[0-2])-(0?[1-9]|[12]\d|3[01])$")

errors: list[str] = []
warnings: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def warn(msg: str) -> None:
    warnings.append(msg)


def is_url(value) -> bool:
    return isinstance(value, str) and value.startswith(("http://", "https://"))


def check_source(item: dict, where: str) -> None:
    src = item.get("source")
    if isinstance(src, dict):
        if not src.get("label"):
            err(f"{where} 缺少 source.label")
        if not is_url(src.get("url")):
            err(f"{where} 的 source.url 不是 http(s) 链接")
    elif isinstance(src, str):
        if not is_url(src):
            err(f"{where} 的 source 不是 http(s) 链接")
    else:
        err(f"{where} 缺少 source")


def check_story(item: dict, where: str) -> None:
    if not isinstance(item, dict):
        err(f"{where} 不是对象")
        return
    title = str(item.get("title") or "").strip()
    text = str(item.get("text") or "").strip()
    if not title:
        err(f"{where} 缺少 title")
    elif len(title) > 60:
        warn(f"{where} 标题偏长（{len(title)} 字）")
    if not text:
        err(f"{where} 缺少 text")
    elif len(text) < 30:
        warn(f"{where} 摘要偏短（{len(text)} 字）")
    check_source(item, where)


def main(argv: list[str]) -> int:
    if len(argv) > 1:
        path = Path(argv[1])
    else:
        files = sorted(Path("data").glob("*.json"))
        if not files:
            print("找不到 data/*.json，请传入数据文件路径", file=sys.stderr)
            return 2
        path = files[-1]

    if not path.exists():
        print(f"文件不存在：{path}", file=sys.stderr)
        return 2
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"JSON 解析失败：{exc}", file=sys.stderr)
        return 1

    date = str(data.get("date") or "")
    if not DATE_RE.match(date):
        err(f"date 格式应为 YYYY-MM-DD，实际：{date!r}")
    elif path.stem != date:
        err(f"文件名（{path.stem}）与 date（{date}）不一致")
    if not isinstance(data.get("issue"), int) or data.get("issue", 0) < 1:
        err("issue 应为 ≥1 的整数")
    if not str(data.get("generated_at") or "").strip():
        warn("缺少 generated_at")

    headline = data.get("headline") or {}
    if not str(headline.get("title") or "").strip():
        err("缺少 headline.title")
    check_source(headline, "headline")

    total = 1 if headline.get("title") else 0
    companies = []
    for i, block in enumerate(data.get("international") or []):
        company = str(block.get("company") or "").strip()
        if not company:
            err(f"international[{i}] 缺少 company")
        companies.append(company)
        items = block.get("items") or []
        if not items:
            warn(f"international[{i}]（{company}）没有条目")
        for j, item in enumerate(items):
            check_story(item, f"international[{i}].items[{j}]")
            total += 1
    missing = [c for c in COMPANIES if c not in companies]
    if missing:
        warn("国际版块未覆盖：" + "、".join(missing))

    for field in ("china", "other"):
        rows = data.get(field) or []
        if not rows:
            warn(f"{field} 为空")
        for i, item in enumerate(rows):
            check_story(item, f"{field}[{i}]")
            total += 1

    market = data.get("market") or {}
    rows = market.get("rows") or []
    if not rows:
        warn("market.rows 为空（行情暂缺时请写 note 说明）")
    for i, row in enumerate(rows):
        if row.get("dir") not in DIRS:
            err(f"market.rows[{i}].dir 应为 up/down/flat，实际：{row.get('dir')!r}")
        if not str(row.get("price") or "").strip():
            err(f"market.rows[{i}] 缺少 price")
    if rows and not str(market.get("as_of") or "").strip():
        warn("market 缺少 as_of（数据时点）")

    capital = data.get("capital") or {}
    paragraphs = capital.get("paragraphs") or []
    if paragraphs:
        chars = sum(len(str(p)) for p in paragraphs)
        if chars < 500:
            warn(f"capital 正文 {chars} 字，少于 500 字")
    for i, flow in enumerate(capital.get("flows") or []):
        if not flow.get("label") or not flow.get("text"):
            err(f"capital.flows[{i}] 缺少 label 或 text")

    models = data.get("models") or {}
    for i, row in enumerate(models.get("rows") or []):
        if row.get("region") not in {"国际", "国内"}:
            warn(f"models.rows[{i}].region 建议为 国际/国内")
        if not MMDD_RE.match(str(row.get("date") or "")):
            err(f"models.rows[{i}].date 应为 MM-DD")
        check_source(row, f"models.rows[{i}]")

    github = data.get("github") or {}
    for i, row in enumerate(github.get("rows") or []):
        if not is_url(row.get("url")):
            err(f"github.rows[{i}].url 不是链接")
        zh = str(row.get("desc_zh") or "").strip()
        if not zh:
            err(f"github.rows[{i}] 缺少 desc_zh（中文简介）")
        elif not 20 <= len(zh) <= 90:
            warn(f"github.rows[{i}].desc_zh 长度 {len(zh)}，建议 40–70 字")

    sites = data.get("sites") or {}
    for i, row in enumerate(sites.get("rows") or []):
        if not is_url(row.get("url")):
            err(f"sites.rows[{i}].url 不是链接")
        if not str(row.get("desc") or "").strip():
            err(f"sites.rows[{i}] 缺少 desc")

    if not (data.get("capital") or {}).get("paragraphs"):
        warn("缺少 capital（资本观察，压轴版面）")

    print(f"检查：{path}  ·  {date or '?'} 第 {data.get('issue', '?')} 期  ·  条目 {total} 条")
    for w in warnings:
        print(f"  warning  {w}")
    for e in errors:
        print(f"  ERROR    {e}")
    if errors:
        print(f"\n未通过：{len(errors)} 个错误，{len(warnings)} 个警告")
        return 1
    print(f"\n通过：{len(warnings)} 个警告")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
