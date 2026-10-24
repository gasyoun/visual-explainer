#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render.py — render a page to desktop + mobile full-page PNGs.

Usage:
    python tools/render.py examples/token-tax/index.html

Requires Playwright with a Chrome/Chromium browser. The script prefers the
system Chrome (`channel="chrome"`) and falls back to Playwright's Chromium.

Output:
    <page-dir>/screenshots/desktop.png
    <page-dir>/screenshots/mobile.png
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Playwright is not installed. Run:")
    print("  uv run --with playwright python tools/render.py <index.html>")
    raise SystemExit(2)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python tools/render.py <index.html>")
        return 2
    page_path = Path(sys.argv[1]).resolve()
    if not page_path.exists():
        print(f"file not found: {page_path}")
        return 1
    out_dir = page_path.parent / "screenshots"
    out_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="chrome")
        except Exception:
            browser = p.chromium.launch()
        for name, width, height, is_mobile in (
            ("desktop", 1440, 1000, False),
            ("mobile", 390, 844, True),
        ):
            page = browser.new_page(
                viewport={"width": width, "height": height},
                device_scale_factor=1,
                is_mobile=is_mobile,
            )
            errors: list[str] = []
            page.on("pageerror", lambda exc: errors.append(str(exc)))
            page.goto(page_path.as_uri(), wait_until="networkidle")
            page.evaluate("document.fonts.ready")
            page.wait_for_timeout(600)
            target = out_dir / f"{name}.png"
            page.screenshot(path=str(target), full_page=True)
            size = page.evaluate("({w:document.documentElement.scrollWidth,h:document.documentElement.scrollHeight})")
            print(f"{name}: {target} ({size['w']}x{size['h']})")
            if errors:
                print(f"  page errors: {errors}")
            page.close()
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
