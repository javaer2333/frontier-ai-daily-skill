#!/usr/bin/env python3
"""渲染器冒烟测试：从技能目录运行，生成两期并检查关键结构。

运行: python3 -m unittest discover -s tests
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
RENDER = SKILL / "scripts" / "render.py"
SAMPLE = SKILL / "examples" / "2026-01-05.json"


class RenderTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "data").mkdir()
        base = json.loads(SAMPLE.read_text(encoding="utf-8"))

        day1 = dict(base, date="2026-01-04", weekday="周日", issue=1)
        day2 = dict(base, date="2026-01-05", weekday="周一", issue=2)
        day2["headline"] = dict(base["headline"], title="示例头条：第二天的测试标题")
        for name, payload in (("2026-01-04", day1), ("2026-01-05", day2)):
            (self.root / "data" / f"{name}.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_render(self, *extra: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(RENDER), "--data", "data/2026-01-05.json", "--out", "reports", *extra],
            cwd=self.root,
            capture_output=True,
            text=True,
        )

    def test_renders_report_and_archive(self) -> None:
        proc = self.run_render()
        self.assertEqual(proc.returncode, 0, proc.stderr)

        report = (self.root / "reports" / "2026-01-05.html").read_text(encoding="utf-8")
        self.assertIn('class="logo"', report)
        self.assertIn("示例头条：第二天的测试标题", report)
        self.assertIn("01", report)  # 版面编号
        self.assertIn("今日看点", report)
        self.assertIn("（本期完）", report)
        self.assertNotIn("None", report)
        # 点击报眼点阵可切到前一天
        self.assertIn('href="2026-01-04.html"', report)
        self.assertIn('aria-current="page"', report)

        latest = (self.root / "reports" / "latest.html").read_text(encoding="utf-8")
        self.assertIn("示例头条：第二天的测试标题", latest)

        index = (self.root / "reports" / "index.html").read_text(encoding="utf-8")
        self.assertIn("2026-01-04.html", index)
        self.assertIn("2026-01-05.html", index)

    def test_custom_site_and_edition(self) -> None:
        proc = self.run_render("--site", "法律 AI 日报", "--edition", "每天 08:00 出刊")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        report = (self.root / "reports" / "2026-01-05.html").read_text(encoding="utf-8")
        self.assertIn("法律 <em>AI</em> 日报", report)
        self.assertIn("每天 08:00 出刊", report)

    def test_index_only(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(RENDER), "--index", "--out", "reports", "--data-dir", "data"],
            cwd=self.root,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue((self.root / "reports" / "index.html").exists())


if __name__ == "__main__":
    unittest.main()
