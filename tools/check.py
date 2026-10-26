#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check.py — fail-closed mechanical checks for a visual-explainer page.

Usage:
    python tools/check.py examples/token-tax/index.html
    python tools/check.py --self-test

Exit code 0 = all checks pass; 1 = at least one failure; 2 = usage error.

Links are parsed, not regex-matched: single-quoted attributes, query strings,
`tel:`/`mailto:`/`javascript:` schemes and same-page `#anchor` targets are all
handled. `--self-test` runs the gate against fixtures it must pass AND fixtures
it must refuse — a gate that cannot fail is not a gate.
"""

from __future__ import annotations

import json
import re
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

# Schemes that never name a local file. Anything else with an unknown scheme is
# a failure: the gate refuses to guess what it cannot resolve.
EXTERNAL_SCHEMES = {
    "http", "https", "mailto", "tel", "sms", "data", "javascript", "ftp", "geo", "irc",
}
LINK_ATTRS = ("href", "src")
LINK_TAGS = {"a", "link", "img", "script", "iframe", "source", "video", "audio", "embed"}
PLACEHOLDER = re.compile(r"TODO|FIXME|lorem ipsum", re.I)
LANG = re.compile(r"^[A-Za-z]{2,3}(-[A-Za-z0-9]+)*$")


class Page(HTMLParser):
    """One pass over the document: tags, ids, links, inlined JSON payloads."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tags: list[tuple[str, dict[str, str]]] = []
        self.ids: set[str] = set()
        self.links: list[str] = []
        self.payloads: list[str] = []
        self.title = ""
        self._in_title = False
        self._title_done = False
        self._in_json = False
        self._buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {k: (v or "") for k, v in attrs}
        self.tags.append((tag, attr))
        if attr.get("id"):
            self.ids.add(attr["id"])
        if tag == "a" and attr.get("name"):
            self.ids.add(attr["name"])
        if tag in LINK_TAGS:
            self.links.extend(attr[a] for a in LINK_ATTRS if attr.get(a))
        if tag == "title" and not self._title_done:
            self._in_title = True
        if tag == "script" and attr.get("type", "").lower() == "application/json":
            self._in_json = True
            self._buffer = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "title" and self._in_title:
            self._in_title = False
            self._title_done = True
        if tag == "script" and self._in_json:
            self.payloads.append("".join(self._buffer))
            self._in_json = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data
        if self._in_json:
            self._buffer.append(data)


def classes(attr: dict[str, str]) -> set[str]:
    return set(attr.get("class", "").split())


def resolve_links(page: Path, parsed: Page) -> tuple[list[str], int]:
    """Return (missing links, count of local links checked)."""
    missing: list[str] = []
    checked = 0
    for url in parsed.links:
        url = url.strip()
        if not url:
            continue
        parts = urlsplit(url)
        if parts.scheme and parts.scheme not in EXTERNAL_SCHEMES and parts.scheme != "file":
            missing.append(url)          # unknown scheme: the gate refuses to guess
            continue
        if parts.scheme in EXTERNAL_SCHEMES or parts.netloc:
            continue
        path_part = unquote(parts.path)
        if not path_part:                # same-page anchor
            checked += 1
            if parts.fragment and parts.fragment not in parsed.ids:
                missing.append(url)
            continue
        checked += 1
        target = (page.parent / path_part).resolve()
        if not target.exists():
            missing.append(url)
            continue
        if parts.fragment and target.suffix.lower() in (".html", ".htm"):
            try:
                other = Page()
                other.feed(target.read_text(encoding="utf-8"))
                other.close()
            except (OSError, UnicodeDecodeError):
                continue
            if parts.fragment not in other.ids:
                missing.append(url)
    return missing, checked


def run(html: str, page: Path) -> list[tuple[str, bool, str]]:
    """Run every check; return [(name, ok, detail)] in print order."""
    parsed = Page()
    parsed.feed(html)
    parsed.close()
    results: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append((name, bool(ok), detail))

    def metas(name: str) -> list[str]:
        return [a.get("content", "") for t, a in parsed.tags
                if t == "meta" and a.get("name", "").lower() == name]

    html_attrs = next((a for t, a in parsed.tags if t == "html"), {})
    lang = html_attrs.get("lang", "").strip()

    check("title", bool(parsed.title.strip()), parsed.title.strip())
    check("meta description", any(c.strip() for c in metas("description")))
    check("viewport", bool(metas("viewport")))
    check("lang", bool(lang) and bool(LANG.match(lang)), "" if LANG.match(lang) else lang)
    h1 = sum(1 for t, _ in parsed.tags if t == "h1")
    check("single h1", h1 == 1, f"{h1} found")
    check("trust block", any("trust" in classes(a) or a.get("id") == "trust"
                             for _, a in parsed.tags))
    check("table fallback", any(t == "table" for t, _ in parsed.tags))
    check("no external script", not any(t == "script" and a.get("src")
                                        for t, a in parsed.tags))
    check("no placeholders", not PLACEHOLDER.search(html))

    bad_payloads = []
    for payload in parsed.payloads:
        try:
            json.loads(payload)
        except json.JSONDecodeError as exc:
            bad_payloads.append(str(exc))
    check("json payloads parse", not bad_payloads,
          f"{len(parsed.payloads)} payload(s); {bad_payloads[:1]}" if bad_payloads else "")

    if any("chart-wrap" in classes(a) for _, a in parsed.tags):
        check("mobile chart variant", any("mobile-chart" in classes(a) for _, a in parsed.tags))
        check("chart data table", any("data-table" in classes(a) for _, a in parsed.tags))

    missing, checked = resolve_links(page, parsed)
    check("local links resolve", not missing,
          f"{checked} checked; missing: {missing}" if missing else f"{checked} checked")
    return results


def report(results: list[tuple[str, bool, str]]) -> int:
    failures = [name for name, ok, _ in results if not ok]
    for name, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'} {name}{': ' + detail if detail else ''}")
    print()
    if failures:
        print(f"FAILED: {len(failures)} check(s): {', '.join(failures)}")
        return 1
    print("OK: all checks passed")
    return 0


GOOD = """<!doctype html><html lang="ru"><head><title>T</title>
<meta name="description" content="d"><meta name="viewport" content="width=device-width">
</head><body><h1>H</h1><div id="top"></div>
<div class="trust" id="trust">t</div><table><tr><td>1</td></tr></table>
<p><a href="#top">jump</a></p>
<script type="application/json" id="j">{"a": 1}</script>
</body></html>"""


def self_test() -> int:
    """The gate must pass clean pages and refuse every seeded defect class."""
    cases: list[tuple[str, str, list[str], str]] = [
        # name, html, expected failures, extra file to create in the temp dir
        ("clean page", GOOD, [], ""),
        ("single-quoted broken link",
         GOOD.replace('<p><a href="#top">jump</a></p>', "<p><a href='nope.html'>x</a></p>"),
         ["local links resolve"], ""),
        ("query string on an existing file",
         GOOD.replace('<p><a href="#top">jump</a></p>', '<p><a href="data.csv?v=2">x</a></p>'),
         [], "data.csv"),
        ("tel / mailto / javascript",
         GOOD.replace('<p><a href="#top">jump</a></p>',
                      '<p><a href="tel:+123">t</a><a href="mailto:a@b.c">m</a>'
                      '<a href="javascript:void(0)">j</a></p>'), [], ""),
        ("missing anchor", GOOD.replace('href="#top"', 'href="#nope"'),
         ["local links resolve"], ""),
        ("broken json payload", GOOD.replace('{"a": 1}', '{"a": "</script>"}'),
         ["json payloads parse"], ""),
        ("external script", GOOD.replace("<h1>H</h1>",
                                         '<h1>H</h1><script src="https://example.com/x.js"></script>'),
         ["no external script"], ""),
        ("no trust block", GOOD.replace('<div class="trust" id="trust">t</div>', ""),
         ["trust block"], ""),
        ("two h1", GOOD.replace("<h1>H</h1>", "<h1>H</h1><h1>H2</h1>"),
         ["single h1"], ""),
        ("placeholder text", GOOD.replace("<h1>H</h1>", "<h1>H</h1><p>TODO</p>"),
         ["no placeholders"], ""),
    ]
    ok = True
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "index.html"
        for name, html, expected, extra in cases:
            extra_path = Path(tmp) / extra if extra else None
            if extra_path:
                extra_path.write_text("a,b\n", encoding="utf-8")
            page.write_text(html, encoding="utf-8")
            failures = [n for n, passed, _ in run(html, page) if not passed]
            good = failures == expected
            ok &= good
            print(f"{'PASS' if good else 'FAIL'} self-test: {name} -> {failures or 'no failures'}")
            if extra_path:
                extra_path.unlink()
    print()
    print("OK: gate passes clean pages and refuses every seeded defect" if ok
          else "FAILED: self-test expectations not met")
    return 0 if ok else 1


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python tools/check.py <index.html> | --self-test")
        return 2
    if argv[1] == "--self-test":
        return self_test()
    page = Path(argv[1]).resolve()
    if not page.exists():
        print(f"FAIL file not found: {page}")
        return 1
    return report(run(page.read_text(encoding="utf-8"), page))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
