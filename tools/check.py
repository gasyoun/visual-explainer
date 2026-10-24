#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check.py — fail-closed mechanical checks for a visual-explainer page.

Usage:
    python tools/check.py examples/token-tax/index.html

Exit code 0 = all checks pass; 1 = at least one failure.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python tools/check.py <index.html>")
        return 2
    page = Path(sys.argv[1]).resolve()
    if not page.exists():
        print(f"FAIL file not found: {page}")
        return 1
    html = page.read_text(encoding="utf-8")
    failures: list[str] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        print(f"{'PASS' if ok else 'FAIL'} {name}{': ' + detail if detail else ''}")
        if not ok:
            failures.append(name)

    title = re.search(r"<title>(.*?)</title>", html, re.S)
    check("title", bool(title and title.group(1).strip()), (title.group(1).strip() if title else ""))
    check("meta description", bool(re.search(r'<meta[^>]+name="description"[^>]+content="[^"]+"', html)))
    check("viewport", bool(re.search(r'<meta[^>]+name="viewport"', html)))
    check("lang", bool(re.search(r'<html[^>]+lang="[a-z-]+"', html)))
    h1_count = len(re.findall(r"<h1\b", html))
    check("single h1", h1_count == 1, f"{h1_count} found")
    check("trust block", ('class="trust"' in html) or ('id="trust"' in html))
    check("table fallback", len(re.findall(r"<table\b", html)) >= 1)
    check("no external script", not re.search(r"<script[^>]+src=", html))
    check("no placeholders", not re.search(r"TODO|FIXME|lorem ipsum", html, re.I))
    if '<div class="chart-wrap"' in html:
        check("mobile chart variant", 'class="mobile-chart"' in html)
        check("chart data table", 'class="data-table"' in html)

    local_links = 0
    missing: list[str] = []
    for match in re.finditer(r'(?:href|src)="([^"]+)"', html):
        url = match.group(1).strip()
        if url.startswith(("http://", "https://", "mailto:", "#", "data:")):
            continue
        target = (page.parent / url.split("#")[0]).resolve()
        local_links += 1
        if not target.exists():
            missing.append(url)
    check("local links resolve", not missing, f"{local_links} checked; missing: {missing}" if missing else f"{local_links} checked")

    print()
    if failures:
        print(f"FAILED: {len(failures)} check(s): {', '.join(failures)}")
        return 1
    print("OK: all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
