# Bug hunt — visual-explainer — 25.10.2026

_Created: 25-10-2026 · Run: interactive day-mode `/bughunt` (rotation slot 4/173, `NEXT`) · Base: `main` @ `7428395` (25-10-2026) · Elapsed: ~35 min · Model: DeepSeek Flash (`deepseek-flash`)._

Static read of all six tool scripts (~1,850 LOC: `build.py`, `check.py`, `render.py`,
`measure_tokens.py`, `measure_script_control.py`, `measure_language_mix.py`, plus
`make_token_strips.py`) and live browser probes (Chrome via Playwright) on the three
generated pages. Read-only: the only write in this pass is this report and the
`CHANGELOG.md` stub, both through a worktree.

## Verdict at a glance

| # | Sev | Finding | Status |
|---|---|---|---|
| H1 | HIGH | The headline range **2.08–4.94×** for «хинди и санскрит» drops Hindi's **1.57×** (GPT-4o) — it is the hero stat on the page, line 11 of the README, and line 9 of the Telegram post; the page's own finding three beats later and the README's own table print 1.57 | **FIXED** 26-10-2026 (fix pass) |
| H2 | HIGH | The script-control verdicts «GPT-4 режет почти вдвое (0.49–0.54×)» and «на DeepSeek разницы почти нет (0.84–0.98×)» are ranges over an **unstated subset**: the Russian column printed in the same table is 0.93× (GPT-4) and **1.42×** (DeepSeek) | **FIXED** 26-10-2026 (fix pass) |
| M1 | MEDIUM | Two of three published pages (`bpe-in-60-seconds`, `context-window`) are **stale**: a fresh `build.py` run does not reproduce them, and the live site serves the stale `bpe` page (`grep -c demo-play` → 0) | reported |
| M2 | MEDIUM | `check.py` never sees **single-quoted** `href`/`src`, so a broken local link ships green; `#anchor` targets and the inlined `<script type="application/json">` payloads are never validated either | reported (probe reproduced) |
| M3 | MEDIUM | `check.py` **false-FAILs** valid links that carry a query string (`data.csv?v=2`) or a `tel:` scheme | reported (probe reproduced) |
| M4 | MEDIUM | `render_bars` hardcodes five groups and `max_ratio = 5.2` while iterating the data: a 6th tokenizer is drawn **below the viewBox** (y=520 vs height 486), a ratio above 5.2 paints a 1,154 px bar past the 1,000 px viewBox | reported (probe reproduced) |
| M5 | MEDIUM | **No gate is wired**: no `.github/workflows`, no pre-commit, no tests — `check.py`/`render.py` are advisory only; `check.py` even fails on the repo's own gallery `index.html` | reported |
| M6 | MEDIUM | The 10-second strip loop desyncs after a manual language pick: selecting **SA** and pressing ▶ advances to **HI** (order is EN→RU→HI→SA), because `idx` is captured once at load | reported (probe reproduced) |
| L1 | LOW | Zero or empty volume renders «Дороже английского **×0.00**» instead of «—» | reported |
| L2 | LOW | Both FLORES loaders strip blank lines **per file, then align by index** — a blank line in any one language file silently misaligns every later sentence; the loader is duplicated in two scripts | reported |
| L3 | LOW | `measure_language_mix.py` collapses Hindi and Sanskrit into one `deva` ratio (Sanskrit's 2.08/4.938), overstating Hindi-heavy mixes (Hindi is 1.573/4.759); its OpenCode lane is documented as random but is «latest 100» | reported |
| L4 | LOW | `render_bytes` silently drops a word block when the strips key is missing, contradicting the builder's own «every data beat must resolve» contract | reported |
| L5 | LOW | `json.dumps` is inlined into `<script type="application/json">` without escaping `<`; any `</script>` inside a token or case-study text breaks the page | reported |
| L6 | LOW | The builder is Russian-only and hardcodes four strip languages / five chart languages; the spec's `lang` only sets `<html lang>` | reported |

Severity: HIGH = a wrong number published on the flagship artefact; MEDIUM = broken
gate, wrong edge case, or artefact drift; LOW = latent.

## What verified green in this pass

- **Data internal consistency** — `flores_results.json`: `ratio_total` recomputes from
  `tokens_total` to three decimals on all 5 tokenizers × 3 languages; `tokens_per_100_chars`
  recomputes; p10 ≤ median ≤ p90 holds for all 15 cells.
- **Script control consistency** — `latin_en = latin_native × native_en` for all 25 cells
  (max deviation < 0.02, rounding only).
- **Token strips are reproducible** — re-running the `make_token_strips.py` tokenisation
  against committed `token_strips.json` gives **0 mismatches** on 6 strip cells (ids, text,
  hex fragments, counts, chars, density).
- **The flagship page is reproducible** — `python tools/build.py examples/token-tax/spec.json`
  on a clean `git archive` of `HEAD` writes a **byte-identical** `index.html` (80,611 bytes).
- **`check.py` is green on all three generated pages** (13 local links on the flagship;
  mobile chart variant + data table present).
- **Calculator math is right** (live probe): 1,000,000 chars · RU · GPT-4o → 268,700 tokens,
  $0.67, ×1.32, +$0.16 (hand-check 26.87/20.36 = 1.32); token mode · 1,000,000 SA · GPT-4o →
  $2.50, ×2.08, +$1.30; the case-study table (4.37 M / $10.92 / $5.24 / +$5.68) recomputes
  from `flores_results.json` cell by cell, and «за год +$68 и +$250» = 12 × the monthly tax.
- **No JS errors, no horizontal overflow** — `pageerror` empty on load and after every
  interaction; `scrollWidth == innerWidth` at 1440 px and at 390 px; the mobile bar chart
  renders (screenshot reviewed), the `<details>` data table is present.
- **Screenshots track the page** — `desktop.png`/`mobile.png` are committed in the same
  commit as the current page; the post screenshots' numbers still match the live default
  state.
- **Hygiene** — no secrets, no `TODO/FIXME/lorem`, no external `<script src>`, all 43 tracked
  files accounted for.

## H1 — The headline range drops Hindi's GPT-4o value (HIGH)

Committed data, `examples/token-tax/data/flores_results.json`:

```
gpt-4o (o200k)   EN 26 873   RU 1.421   HI 1.573   SA 2.085
gpt-4 (cl100k)   EN 27 182   RU 2.462   HI 4.759   SA 4.938
Qwen2.5          EN 27 621   RU 1.755   HI 4.415   SA 4.507
DeepSeek-V3      EN 27 041   RU 1.582   HI 2.795   SA 2.856
Mistral-7B       EN 29 997   RU 1.855   HI 4.554   SA 4.599
```

The range over **Hindi + Sanskrit together** is **1.57–4.94×** (floor: Hindi on GPT-4o).
The page and the prose claim **2.08–4.94×** — Sanskrit's floor, not the pair's:

- hero stat `"value": "2.08–4.94×", "label": "хинди и санскрит / английский"` —
  [`examples/token-tax/spec.json:26-27`](https://github.com/gasyoun/visual-explainer/blob/main/examples/token-tax/spec.json#L26-L27),
  rendered into the page's first screen;
- standfirst, same spec —
  [`spec.json:15`](https://github.com/gasyoun/visual-explainer/blob/main/examples/token-tax/spec.json#L15);
- bottom line —
  [`spec.json:205`](https://github.com/gasyoun/visual-explainer/blob/main/examples/token-tax/spec.json#L205);
- [`README.md:11`](https://github.com/gasyoun/visual-explainer/blob/main/README.md#L11) —
  «**1.4–2.5×** more tokens in Russian and **2.1–4.9×** more in Hindi and Sanskrit»;
- [`POST.md:9`](https://github.com/gasyoun/visual-explainer/blob/main/POST.md#L9) — the
  Telegram body.

It is refuted twice from inside the artefacts themselves:

1. The page's own third finding, three beats below the hero, prints
   `1.57–4.76× у хинди, 2.08–4.94× у санскрита`
   ([`spec.json:68`](https://github.com/gasyoun/visual-explainer/blob/main/examples/token-tax/spec.json#L68)) —
   i.e. the correct pair range is 1.57–4.94, and the hero contradicts it on the same screen
   scroll.
2. The README table ten lines below the sentence prints `| GPT-4o (o200k) | 26,873 | 1.42× |
   **1.57×** | 2.08× |`, and `POST.md:12` prints `хинди и санскрит (1.57–2.08×)` — so the
   same post carries both ranges.

Fix shape: `2.08–4.94×` → **`1.57–4.94×`** (or re-label the stat «санскрит / английский» and
add a Hindi line). Four files, one number, plus a rebuild of `examples/token-tax/index.html`.
Owner: MG — the headline claim is authorial voice, not a mechanical edit.

**Fixed 26-10-2026** (MG: «fix h1 h2»): the range is now **1.57–4.94×** in the hero stat,
the standfirst, the closing beat and the page `<meta description>`; `README.md` reads
**1.6–4.9×**; `POST.md` and `PLAN.md` carry the corrected pair range; `DECISIONS_2026-10-24.md`
keeps the original wording and gains a dated amendment. `index.html` was rebuilt from the spec
(byte-reproducible), `check.py` green, and the four affected screenshots (`desktop`, `mobile`,
`post-hero`, `post-audit`) were re-rendered so no published image still shows 2.08–4.94.

## H2 — «Halves» / «nearly neutral» ranges exclude the Russian column in the same table (HIGH)

`docs/METHOD.md` prints the script-control table and then, eight lines later, a verdict that
excludes its first column:

```
| GPT-4 (cl100k) | 0.93× | 0.54× | 0.69× | 0.49× | 0.73× |
| DeepSeek-V3    | 1.42× | 0.91× | 0.98× | 0.84× | 0.94× |
                                      (RU ASCII  HI HK  HI IAST  SA HK  SA IAST)

2. На GPT-4 транслитерация режет почти вдвое: санскрит HK 0.49×, хинди HK 0.54×.
3. На DeepSeek разницы почти нет (0.84–0.98×) …
```

- [`docs/METHOD.md:85-87`](https://github.com/gasyoun/visual-explainer/blob/main/docs/METHOD.md#L85-L87)
  (table) vs [`docs/METHOD.md:94-96`](https://github.com/gasyoun/visual-explainer/blob/main/docs/METHOD.md#L94-L96)
  (verdict).
- [`README.md:31-32`](https://github.com/gasyoun/visual-explainer/blob/main/README.md#L31-L32) —
  «on GPT-4 it halves the count (0.49–0.54×); on DeepSeek it is nearly neutral (0.84–0.98×)».
- [`POST.md:14`](https://github.com/gasyoun/visual-explainer/blob/main/POST.md#L14) — «на GPT-4
  — режет почти вдвое (0.49–0.54×)», in the same sentence whose first parenthetical
  (1.06–1.62×) *does* span all five schemes.

True full ranges from `examples/token-tax/data/script_control.json`:

```
gpt-4o (o200k)  1.057 … 1.620     RU 1.48  HI HK 1.52  HI IAST 1.62  SA HK 1.06  SA IAST 1.18
gpt-4 (cl100k)  0.495 … 0.928     RU 0.93  HI HK 0.54  HI IAST 0.69  SA HK 0.49  SA IAST 0.73
Qwen2.5         0.536 … 1.290     RU 1.29  …
DeepSeek-V3     0.838 … 1.416     RU 1.42  HI HK 0.91  HI IAST 0.98  SA HK 0.84  SA IAST 0.94
Mistral-7B      0.518 … 1.216     RU 1.22  …
```

So on DeepSeek, Latin transliteration is **not neutral for Russian — it is 42 % dearer**;
on GPT-4 it is neutral for Russian (0.93×), not «halved». The page body is honest about this
(its own script-control note says «русская транслитерация даёт диграфы …, поэтому она дороже
кириллицы», [`spec.json` script-control `note`]) — the README and the post are not.

Fix shape: state the range over the five schemes (0.49–0.93× / 0.84–1.42×) or scope the
sentence to «HK/IAST на деванагари». Owner: MG.

**Fixed 26-10-2026** (MG: «fix h1 h2»), by scoping rather than widening, because the
Devanagari/HK effect is the real finding: `README.md` now reads «on GPT-4 it halves
Devanagari (0.49–0.54×) but leaves Russian alone (0.93×); on DeepSeek it is neutral for
Devanagari (0.84–0.98×) and dearer for Russian (1.42×)»; `docs/METHOD.md` points 2–4 say
the same and point 4 no longer claims «дороже везде» (GPT-4's 0.93× is the exception);
`POST.md` gained «а русский не трогает (0.93×)». On the page, the audit finding and the
script-control finding title now say **HK-запись деванагари** instead of a bare «режет
вдвое». The page's own script-control table and note were already honest and are unchanged.

## M1 — Two of three published pages are not reproducible from the builder (MEDIUM)

```
$ git archive HEAD | tar -x -C /tmp/ve-repro
$ cd /tmp/ve-repro && python3 tools/build.py examples/*/spec.json
$ diff examples/bpe-in-60-seconds/index.html    ~/GitHub/visual-explainer/examples/bpe-in-60-seconds/index.html
$ diff examples/context-window/index.html       ~/GitHub/visual-explainer/examples/context-window/index.html
```

`token-tax` → **identical**. The other two differ: the committed pages carry an older
`templates/explainer.css` (no `.demo-play`, `.plain-*`, `.case-*`, `.gloss` rules) and no
`#demo-play` button/script, i.e. they were built before the «token loop» commit (`7428395`)
touched `build.py` + CSS. Today nothing is visibly broken (those pages don't use the new
classes), but:

- the live site serves the stale artefact — `curl https://gasyoun.github.io/visual-explainer/examples/bpe-in-60-seconds/ | grep -c demo-play` → **0**, while a rebuild emits one;
- the repo's own rule («One source, many outputs … Hand-kept duplicates drift», `SKILL.md`)
  is unenforced — a rebuild would silently republish two changed pages.

Fix shape: rebuild all three examples in CI (or a pre-commit hook) and fail on a dirty tree.

## M2 — `check.py` is blind to single-quoted links, anchors and inlined JSON (MEDIUM)

```python
51:    for match in re.finditer(r'(?:href|src)="([^"]+)"', html):
53:        if url.startswith(("http://", "https://", "mailto:", "#", "data:")):
```

[`tools/check.py:51-59`](https://github.com/gasyoun/visual-explainer/blob/main/tools/check.py#L51-L59).
Probe page (in `/tmp/gate/page.html`) with `href='missing-single-quoted.html'`,
`href="#does-not-exist"`, `href="tel:+123"` and a `</script>` inside the JSON payload:

```
PASS local links resolve: 3 checked   ← the single-quoted broken link is invisible
FAIL … missing: ['data.csv?v=2', 'javascript:void(0)', 'tel:+123']
```

So the gate is **fail-open in the direction that matters** (a broken relative link can ship)
and fail-closed on shapes that are legitimate. `href="#id"` is skipped entirely, so a skip
link to a non-existent `#main` would pass.

Fix shape: parse with `html.parser`/`selectolax` instead of a regex; resolve `urlparse()`
(scheme/netloc/query) and, for same-page anchors, assert the `id` exists.

## M3 — `check.py` false-FAILs query strings and `tel:` (MEDIUM)

Same probe: `data.csv?v=2` and `tel:+123` are reported missing because
`url.split("#")[0]` is treated as a path ([`check.py:55`](https://github.com/gasyoun/visual-explainer/blob/main/tools/check.py#L55)).
Any page that links a versioned CSV, or a phone number, goes red for no reason — and a red
gate everywhere is a gate nobody reads.

## M4 — `render_bars` hardcodes the shape of the data (MEDIUM)

```python
183:    width, height = 1000, 5 * 84 + 66
185:    top, group_h, max_ratio = 30, 84, 5.2
186:    scale = chart_w / max_ratio
```
[`tools/build.py:183-186`](https://github.com/gasyoun/visual-explainer/blob/main/tools/build.py#L183-L186),
then `for i, name in enumerate(names)` over whatever the JSON contains. Probes on a copy of
the data:

- **6th tokenizer**: `viewBox` stays `1000 486` but the last row separator lands at
  **y = 520** and the last label at y = 482 — everything below 486 is clipped by the viewport,
  so the new tokenizer silently disappears from a page that still renders «пять
  токенизаторов».
- **ratio 7.9** (a plausible future tokenizer): the bar is **1,154.6 px** wide starting at
  x = 190 → right edge 1,344.6 against a 1,000 px viewBox; the bar and its label are cut off.
  The mobile chart has the same constant (`width:{ratio / max_ratio * 100:.1f}%`, L245 →
  152 %).

Fix shape: derive `height` from `len(names)`, and `max_ratio` from
`max(ceil(max ratio), 1)` (+ a right gutter sized for the label).

## M5 — Nothing runs the gates (MEDIUM)

- `ls .github` → absent; `git ls-files | grep -E 'test|workflow|conftest|Makefile'` → nothing.
- `check.py` and `render.py` are invoked by hand; `render.py` even **collects `pageerror`
  and returns 0** ([`render.py:54-65`](https://github.com/gasyoun/visual-explainer/blob/main/tools/render.py#L54-L65)),
  so a page that throws on load still «renders fine».
- `check.py` on the repo's own gallery: `FAILED: 2 check(s): trust block, table fallback`
  (that page is hand-written, so the contract mismatch is defensible — but nothing states
  which pages the gate covers, and nothing covers the gallery at all).

This is the root cause of M1 and of H1/H2 surviving: every number in this repo is
hand-carried from JSON into prose, and no mechanical step compares them.

Fix shape: one workflow — build all specs into a temp tree, `git diff --exit-code` on the
committed pages, run `check.py` on each, fail on `pageerror` in `render.py`. Then a
`claims_check.py` that recomputes the hero/finding ranges from `flores_results.json` and
grep-asserts them in `spec.json` + `README.md`.

## M6 — The 10-second loop starts from the wrong language (MEDIUM)

```js
557:    var order = ['EN', 'RU', 'HI', 'SA'];
558:    var idx = order.indexOf(lang);      // captured once, at load
569:      idx = (idx + 1) % order.length;   // manual clicks never update idx
```
[`tools/build.py:556-576`](https://github.com/gasyoun/visual-explainer/blob/main/tools/build.py#L556-L576).
Live probe on the flagship page: click **SA**, press ▶, wait 2.4 s → the strip switches to
**HI** (the order says SA → EN). Sequence observed: `RU (default) → [click SA] → SA → ▶ →
HI`. The first frame of the loop therefore replays a language out of order — and from EN it
skips RU entirely.

Fix shape: in the language click handler, set `idx = order.indexOf(b.dataset.stripLang)`.

## L1 — «Дороже английского ×0.00» on an empty input (LOW)

`var delta = enTokens ? langTokens / enTokens : 0;` ([`build.py:621`](https://github.com/gasyoun/visual-explainer/blob/main/tools/build.py#L621))
feeds `'×' + delta.toFixed(2)` unconditionally (L631). Live probe with volume `0` and with an
empty field: tokens `0`, cost `0,00 $`, delta **`×0.00`**. Fix: render «—» when the volume is
empty/zero.

## L2 — Blank-line filtering before index alignment (LOW)

[`measure_tokens.py:110-115`](https://github.com/gasyoun/visual-explainer/blob/main/tools/measure_tokens.py#L110-L115)
(and the copy at [`measure_script_control.py:63-69`](https://github.com/gasyoun/visual-explainer/blob/main/tools/measure_script_control.py#L63-L69)):

```python
lines = [line.strip() for line in (...).splitlines() if line.strip()]
...
n = min(len(v) for v in texts.values());  return {lang: lines[:n] ...}
```

Each file is filtered independently and then aligned **by index**. FLORES devtest happens to
have no blank lines today (1,012 everywhere, n recorded and consistent), but one blank line
anywhere shifts every later sentence of that language against the others — silently, with
`ratio_median` and `ratio_p10/p90` quietly nonsense. The loader is duplicated in two scripts,
so a fix must land twice. Fix: keep 1:1 line arrays (no filtering), assert equal lengths, and
`raise` on a length mismatch and on an empty line.

## L3 — One `deva` ratio for two languages; a lane that is not random (LOW)

[`measure_language_mix.py:52-55`](https://github.com/gasyoun/visual-explainer/blob/main/tools/measure_language_mix.py#L52-L55):

```python
RATIOS = {"gpt-4o": {"ru": 1.421, "deva": 2.08}, "gpt-4": {"ru": 2.46, "deva": 4.938}}
```

`deva` is the **Sanskrit** ratio; Hindi is 1.573 (GPT-4o) / 4.759 (GPT-4), so a Hindi-heavy
mix is over-taxed by up to 33 % (GPT-4o). Since the sampler cannot tell Hindi from Sanskrit
(Devanagari is Devanagari), either use the Devanagari-pair mean and say so, or report a
band [1.57, 2.09].

Also [`measure_language_mix.py:262`](https://github.com/gasyoun/visual-explainer/blob/main/tools/measure_language_mix.py#L262)
— OpenCode sessions are taken `ORDER BY time_created DESC` while the docstring promises a
random sample (zcode, ten lines above, does use `ORDER BY RANDOM()`). That biases the lane
toward the current season, which is exactly the kind of drift the note about lane weights
warns about.

## L4 — A missing data beat renders as nothing (LOW)

[`build.py:333-346`](https://github.com/gasyoun/visual-explainer/blob/main/tools/build.py#L333-L346):
`word_data = strips.get(word.get("key", ""), {}).get(...)` → `if not row: continue` → and if
`word_rows` is empty, `word_html = ""`. A typo in `word.key` therefore ships a page with a
silent hole in the «Почему» beat, while the module docstring promises «Every data beat must
resolve to a committed file». Fix: raise `SystemExit` when a requested key/encoding is absent.

## L5 — JSON inlined without escaping `<` (LOW)

`f'<script type="application/json" id="strip-data">{json.dumps(strips, ensure_ascii=False)}</script>'`
([`build.py:176`](https://github.com/gasyoun/visual-explainer/blob/main/tools/build.py#L176))
and the calculator twin at [L427](https://github.com/gasyoun/visual-explainer/blob/main/tools/build.py#L427).
`json.dumps` does not escape `<`, so a token whose text contains `</script>` terminates the
block: the page loses its widget and the remainder of the JSON renders as text. Data is
trusted (spec-authored), so this is a robustness bug, not an XSS finding — but the same
builder escapes everything else, so the asymmetry is worth closing: `json.dumps(...).replace("<", "\\u003c")`.

## L6 — The builder is Russian-only (LOW)

`section_open`/renderers hardcode Russian copy («Токена…», «Таблица с числами», the skip link
«К содержанию»), the strip demo iterates `("EN", "RU", "HI", "SA")`
([`build.py:150`](https://github.com/gasyoun/visual-explainer/blob/main/tools/build.py#L150)) and
the chart iterates `("RU", "HI", "SA")` with a fixed colour map
([`build.py:187`](https://github.com/gasyoun/visual-explainer/blob/main/tools/build.py#L187)).
`spec["lang"]` only reaches `<html lang>`, and `check.py` then *validates* that attribute —
so a spec declaring `"lang": "en"` produces a Russian page with an English `lang`, an
accessibility defect the gate happily certifies. Fix: state the limitation in `SKILL.md` and
make `check.py` warn when `lang != "ru"`; or move the strings into the spec.

## Suggested order of work

1. **H1 + H2** — four files, one number each, plus a rebuild. MG decides the wording.
2. **M5** — the single workflow (rebuild + `check.py`), because it prevents M1 recurring.
3. **M2 + M3** — rewrite the link check on a parser; one PR.
4. **M4 + M6 + L1** — the builder's three live defects; one PR with the probes from this
   report as the after-state.
5. **L2 + L4 + L5** — fail-closed hardening of the measurement/builder paths.
6. **L3 + L6** — method notes; L6 is a documented limitation rather than code.

_Dr. Mārcis Gasūns_
