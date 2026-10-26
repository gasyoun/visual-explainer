#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify.py — prove that the published pages ARE their specs.

Usage:
    python tools/verify.py             # gate + build parity + chart probes
    python tools/verify.py --render    # also load every page in Chrome (needs playwright)

Exit code 0 = every step passed; 1 = at least one step failed.

Steps
-----
1. **self-test** — `check.py --self-test`: the gate must refuse seeded defects,
   not only pass clean pages.
2. **build parity** — rebuild every `examples/*/spec.json`; a committed
   `index.html` that changes is a failure. This is what catches a stale page and
   a hand-edited one.
3. **gate** — `check.py` on every generated page.
4. **probes** — `render_bars` must keep every mark inside its `viewBox` for 3, 5
   and 6 tokenizers and for a ratio above the current axis; the layout used to be
   hardcoded to five groups and a 5.2× axis.
5. **loader probes** — the FLORES loader must refuse a corpus whose files are not
   line-aligned (that used to be a silent per-sentence ratio bug).
6. **spec gate** — every spec must declare `lang: ru`: the builder's UI copy is
   Russian, so a page claiming another language would be mislabelled.

`--render` additionally loads each page in Chromium and fails on a JS error, so a
widget that throws on load cannot pass as "renders fine".
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import build  # noqa: E402  (local tool)
import check as gate  # noqa: E402  (local tool)
import flores  # noqa: E402  (local tool, stdlib only)

PAGES = sorted((ROOT / "examples").glob("*/spec.json"))


def step(name: str, ok: bool, detail: str = "") -> bool:
    print(f"{'PASS' if ok else 'FAIL'} {name}{': ' + detail if detail else ''}")
    return ok


def run_self_test() -> bool:
    return step("gate self-test", gate.main(["check.py", "--self-test"]) == 0)


def run_build_parity() -> bool:
    pages: list[Path] = []
    for spec in PAGES:
        out = build.build(spec)
        pages.append(out.relative_to(ROOT))
    if not pages:
        return step("build parity", False, "no examples/*/spec.json found")
    diff = subprocess.run(
        ["git", "diff", "--quiet", "--", *[str(p) for p in pages]],
        cwd=ROOT, check=False,
    )
    ok = diff.returncode == 0
    detail = (f"{len(pages)} page(s) rebuilt, byte-identical"
              if ok else "a committed page changed — rebuild its spec instead of editing the HTML")
    return step("build parity", ok, detail)


def run_gate() -> bool:
    ok = True
    for spec in PAGES:
        page = spec.parent / "index.html"
        rc = gate.main(["check.py", str(page)])
        ok &= step(f"gate {page.relative_to(ROOT)}", rc == 0)
    return ok


def chart_fits(svg: str) -> tuple[bool, str]:
    view = re.search(r'viewBox="0 0 (\d+) (\d+)"', svg)
    if not view:
        return False, "no viewBox"
    width, height = int(view.group(1)), int(view.group(2))
    ys = [float(v) for v in re.findall(r'<text x="0" y="([\d.]+)"', svg)]
    ys += [float(v) for v in re.findall(r'<line x1="0" y1="([\d.]+)"', svg)]
    rects = [(float(x), float(y), float(w))
             for x, y, w in re.findall(r'<rect x="([\d.]+)" y="([\d.]+)" width="([\d.]+)"', svg)]
    max_y = max(ys + [y + 12 for _, y, _ in rects])
    max_x = max(x + w for x, _, w in rects)
    ok = max_y <= height and max_x <= width
    return ok, f"viewBox={width}x{height} max_x={max_x:.0f} max_y={max_y:.0f}"


def run_probes() -> bool:
    data = json.loads((ROOT / "examples/token-tax/data/flores_results.json").read_text(encoding="utf-8"))
    beat = {"type": "bars", "kicker": "k", "title": "t", "intro": "", "findings": []}

    def variant(name: str, mutate) -> bool:
        clone = json.loads(json.dumps(data))
        mutate(clone)
        ok, detail = chart_fits(build.render_bars(beat, clone))
        return step(f"probe {name}", ok, detail)

    def add_sixth(d: dict) -> None:
        d["results"]["NewTokenizer"] = d["results"]["Mistral-7B"]

    def add_three(d: dict) -> None:
        del d["results"]["Mistral-7B"]
        del d["results"]["DeepSeek-V3"]

    def wide_ratio(d: dict) -> None:
        d["results"]["Qwen2.5"]["SA"]["ratio_total"] = 7.9

    ok = variant("5 tokenizers", lambda d: None)
    ok &= variant("6 tokenizers", add_sixth)
    ok &= variant("3 tokenizers", add_three)
    ok &= variant("ratio 7.9", wide_ratio)
    return ok


def run_preflight() -> bool:
    """No unrendered page variable: every lang/enc the renderers assume exists."""
    data = json.loads((ROOT / "examples/token-tax/data/flores_results.json").read_text(encoding="utf-8"))
    langs = ("EN", "RU", "HI", "SA")
    ok = True
    for name, row in data["results"].items():
        missing = [lang for lang in langs if lang not in row]
        ok &= step(f"data {name} has {','.join(langs)}", not missing, str(missing) if missing else "")
    return ok


def run_loader_probes() -> bool:
    """L2: an unaligned corpus must fail closed, not shift sentences silently."""

    def write(base: Path, per_lang: dict[str, list[str]]) -> None:
        for code, lines in per_lang.items():
            (base / f"{code}.devtest").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def aligned(n: int) -> dict[str, list[str]]:
        return {code: [f"{code} {i}" for i in range(n)] for code in flores.LANGS.values()}

    def case(name: str, per_lang: dict[str, list[str]], should_raise: bool) -> bool:
        with tempfile.TemporaryDirectory() as tmp:
            write(Path(tmp), per_lang)
            try:
                got = flores.read_devtest(Path(tmp))
                raised = False
            except flores.FloresError:
                raised = True
                got = {}
        detail = "refused" if raised else f"{len(next(iter(got.values())))} lines each"
        return step(f"loader {name}", raised == should_raise, detail)

    ok = case("aligned corpus", aligned(3), False)
    trailing = aligned(3)
    trailing[flores.LANGS["RU"]] += ["", ""]          # a trailing newline is not a sentence
    ok &= case("trailing blank lines", trailing, False)
    gaps = aligned(3)
    gaps[flores.LANGS["RU"]][1] = ""                   # internal blank: must refuse
    ok &= case("internal blank line", gaps, True)
    short = aligned(3)
    short[flores.LANGS["SA"]] = short[flores.LANGS["SA"]][:2]
    ok &= case("unequal length", short, True)
    return ok


def run_spec_lang() -> bool:
    """L6: the builder's copy is Russian; a spec may not claim another language yet."""
    ok = True
    for spec in PAGES:
        declared = json.loads(spec.read_text(encoding="utf-8")).get("lang", "ru")
        ok &= step(f"spec lang {spec.parent.name}", declared == "ru",
                   "" if declared == "ru"
                   else f"'{declared}' — the UI copy is Russian; add i18n before declaring it")
    return ok


def run_render() -> bool:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("SKIP render: playwright is not installed "
              "(uv run --with playwright python tools/verify.py --render)")
        return True
    ok = True
    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch(channel="chrome")
        except Exception:
            browser = pw.chromium.launch()
        for spec in PAGES:
            page_path = (spec.parent / "index.html").resolve()
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            errors: list[str] = []
            page.on("pageerror", lambda exc: errors.append(str(exc)))
            page.goto(page_path.as_uri(), wait_until="networkidle")
            page.wait_for_timeout(400)
            overflow = page.evaluate(
                "({sw: document.documentElement.scrollWidth, iw: window.innerWidth})")
            ok &= step(f"render {page_path.parent.name}", not errors,
                       f"js errors: {errors}" if errors else "no js errors")
            ok &= step(f"no horizontal overflow {page_path.parent.name}",
                       overflow["sw"] <= overflow["iw"],
                       f"scrollWidth {overflow['sw']} / innerWidth {overflow['iw']}")
            page.close()
        browser.close()
    return ok


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--render", action="store_true", help="also load pages in Chrome (needs playwright)")
    ap.add_argument("--no-build", action="store_true", help="skip the build-parity step")
    args = ap.parse_args()

    print(f"verify: {len(PAGES)} page(s) under {ROOT}")
    ok = run_self_test()
    if not args.no_build:
        ok &= run_build_parity()
    ok &= run_gate()
    ok &= run_preflight()
    ok &= run_probes()
    ok &= run_loader_probes()
    ok &= run_spec_lang()
    if args.render:
        ok &= run_render()
    print()
    print("OK: specs, pages and gate agree" if ok else "FAILED: see the FAIL lines above")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
