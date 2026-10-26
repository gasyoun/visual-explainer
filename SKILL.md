---
name: visual-explainer
description: Turn a concept + committed data into a single-file HTML explainer — an argument with evidence, not a poster. Use when the user asks for a visual explainer, a concept page, an HTML one-pager, a data story, or "explain X visually"; builds via spec.json + build.py, enforces a trust block, mobile variant, print CSS, and a render-review loop.
license: MIT
metadata:
  opencode/autoinvoke: "false"
---

# visual-explainer

_Created: 24-10-2026 · Author: Dr. Mārcis Gasūns · Model: DeepSeek Flash (`deepseek-flash`)_

A visual explainer is **an argument with evidence**, not a poster. This skill
turns a concept and a committed dataset into one self-contained HTML page,
then forces you to look at the rendered page before delivering it.

The flagship is [`examples/token-tax`](examples/token-tax/index.html): why the
same meaning costs 1.42–2.46× tokens in Russian and 2.08–4.94× in Sanskrit.

## When to use

- A concept needs to be explained visually: tokenization, BPE, context
  windows, sandhi, a pipeline, a trade-off.
- A dataset needs a narrative page, not a dashboard.
- A lesson or assignment needs an artifact that demonstrates a method, not
  just a result.
- The output must be one file, shareable as a URL, printable, and readable on
  a phone.

**Not this skill:**

- A poster or social infographic image → `epic-infographics`.
- A feed-derived chart page → `viz-page`.
- A scroll-driven story with sticky figures → `scrollytelling`.
- A dashboard with filters and tables → build a dashboard; this is an
  explainer.
- A slide deck → build slides; this is a page.

## Contract

```
spec.json + data/*.json
        │
        ▼
tools/build.py  ──►  index.html   (inline CSS + inline JS, no external JS)
        │
        ▼
tools/check.py  ──►  PASS/FAIL
        │
        ▼
tools/render.py ──►  desktop.png + mobile.png
        │
        ▼
   look at the PNG, fix, publish

tools/verify.py ──►  the same gate across EVERY example, in CI:
                     gate self-test → build parity → check.py → chart probes
```

**One source, many outputs.** The page, its data table, its CSV, and its
screenshots all come from the same committed JSON. Hand-kept duplicates drift.

## Workflow

### 0. Brief before code

Pin four things in one paragraph:

- **Audience** — who reads this and what do they already know?
- **Claim** — one sentence that can be false. "Russian is expensive" is not a
  claim; "Russian costs 1.42× English on GPT-4o and 2.46× on GPT-4" is.
- **Evidence** — the committed dataset that can prove or refute the claim.
- **Action** — what should the reader do after the page? Pick a tokenizer,
  budget in tokens, run an A/B.

If the claim cannot be measured, stop and write a memo instead.

### 1. Storyboard 5–7 beats

One idea per beat. The default sequence:

1. **Hero** — claim + two or three numbers.
2. **Definition** — what the thing is (token, BPE, context window).
3. **Evidence** — the chart/table that proves the claim.
4. **Mechanism** — why it happens (bytes, merges, fallback).
5. **Consequence** — a calculator, a cost, a limit.
6. **Action** — 3–5 tactics, each with a measured basis and a caveat.
7. **Trust** — source, n, versions, date, links, caveats.

If a beat cannot cite data, cut it or mark it as opinion.

### 2. Commit the data

- Data lives next to the spec: `examples/<slug>/data/*.json` and `.csv`.
- Every number in prose resolves to a file. No hand-typed statistics.
- Record corpus, license, n, tokenizer/model revisions, library versions,
  and the date.
- Write the caveat into the trust beat, not into a footnote nobody reads.

### 3. Build from a spec

```bash
python tools/build.py examples/token-tax/spec.json
```

The spec is JSON:

```json
{
  "slug": "token-tax",
  "lang": "ru",
  "title": "Налог на токены",
  "description": "One sentence for the link preview.",
  "topnote": "опыт 06 · 24-10-2026",
  "data": "data/flores_results.json",
  "strips": "data/token_strips.json",
  "beats": [
    {"type": "hero", "kicker": "...", "title": "...", "standfirst": "...",
     "stats": [{"value": "1.42×", "label": "русский / английский"}],
     "note": "..."},
    {"type": "token-demo", "kicker": "...", "title": "...", "intro": "<p>...</p>",
     "default_lang": "RU", "default_enc": "o200k", "note": "..."},
    {"type": "bars", "kicker": "...", "title": "...", "intro": "<p>...</p>",
     "caption": "...", "findings": [{"n": "1.42×", "title": "...", "text": "..."}]},
    {"type": "bytes", "kicker": "...", "title": "...", "intro": "<p>...</p>",
     "table": [{"char": "क", "lang": "sa", "bytes": "3", "example": "..."}],
     "word": {"key": "word_sa", "lang": "SA", "text": "...", "rows": []},
     "outro": "<p>...</p>"},
    {"type": "calculator", "kicker": "...", "title": "...", "intro": "<p>...</p>",
     "hint": "...", "note": "..."},
    {"type": "tactics", "kicker": "...", "title": "...", "intro": "<p>...</p>",
     "items": [{"n": "01", "title": "...", "text": "...", "basis": "..."}]},
    {"type": "trust", "kicker": "...", "title": "...", "html": "<p>...</p>",
     "made_with": "..."}
  ],
  "footer": {"brand": "...", "note": "...", "links": []}
}
```

### 4. Check mechanically

```bash
python tools/check.py examples/token-tax/index.html
python tools/check.py --self-test          # the gate must refuse, not only pass
python tools/verify.py                     # every example: build parity + gate + probes
```

The check refuses: no title, no single h1, no viewport, no `lang`, no trust
block, no data table, external `<script src>`, `TODO`/`lorem`, broken local
links (single- or double-quoted, query strings included), a dangling `#anchor`,
and an inlined `application/json` payload that does not parse.

`verify.py` is the tree-level contract: it rebuilds every `examples/*/spec.json`
and fails if a committed page changes (so a stale or hand-edited page cannot
ship), runs the gate on each page, and probes `render_bars` at 3 / 5 / 6
tokenizers and above-axis ratios. `.github/workflows/verify.yml` runs it on every
push and PR.

### 5. Render, then look

```bash
python tools/render.py examples/token-tax/index.html
```

Open `screenshots/desktop.png` and `screenshots/mobile.png`. **A page you have
not looked at is not done.** Fix at least: overlapping labels, values clipped
at the canvas edge, wrong pluralisation, money rounded to `1$`, uppercase
`GPT-4O`, chart unreadable at 390 px.

### 6. Publish

- GitHub Pages, relative links, `.nojekyll`.
- The page must work from `file://` for a reviewer who downloads the repo.
- Post: three visuals, the URL, the one number. Do not paste the whole page.
- Add the example to `gallery/index.html`.

## Beat types

| Type | What it renders | Required data |
|---|---|---|
| `hero` | kicker, h1, standfirst, stats grid, note | — |
| `token-demo` | language/tokenizer switches, token chips, counts | `strips` JSON |
| `bars` | SVG chart + mobile mini-bars + findings + table | `data.results` |
| `bytes` | UTF-8 table + a word split into tokens | `strips` + spec |
| `calculator` | volume × price × tokenizer × language | `data.results` |
| `tactics` | 2-column cards, optional full-width caveat | spec |
| `trust` | prose + data table + links | `data.results` |
| `prose` | free HTML section | spec |

## Hard rules

1. **No number without a committed artifact.** A figure in prose that cannot
   be traced to a JSON/CSV row is a defect.
2. **No page without a trust block**: source, n, versions/revisions, date,
   script link, caveats.
3. **No external JavaScript.** Inline only. Fonts may be a CDN request with a
   system fallback; the page must still read offline.
4. **Mobile 390 px is a build target, not an afterthought.** No horizontal
   page scroll; a wide SVG gets a mobile variant (mini-bars), not a scrollbar.
5. **Print CSS**: controls hidden, white background, no clipped tables, page
   breaks at sections.
6. **Every chart has a data-table fallback** and a CSV link.
7. **One accent colour**, direct labels, no gradients, no card grid as the
   whole layout. Editorial tokens are in `templates/explainer.css`.
8. **No invented quotes, statistics, or testimonials.** Illustrative numbers
   are labelled as illustrations.
9. **Rights and privacy**: cite the corpus license; no personal data, private
   chat links, or participant names in a public artifact.
10. **Look at the render before delivery.** This is the rule the other nine
    depend on.

## Design language

Default: **editorial** — warm paper `#FAF7F2`, ink `#20242C`, oxblood
`#A32035`, emerald `#0D7F63`, ochre `#B07C1F`; Fraunces for display, Libre
Franklin for text; huge numerals, thin rules, no shadows. Alternative:
**blueprint** for a technical audit (grid, monospace, colder palette).

The visual identity carriers are: one huge number, one display serif, one
accent, direct labels. If you remove the text and the topic is still
recognizable, the design works.

## Files

```
SKILL.md
tools/build.py            # spec -> index.html
tools/check.py            # fail-closed mechanical checks
tools/render.py           # desktop + mobile screenshots
tools/measure_tokens.py   # token-tax data (example)
tools/make_token_strips.py
templates/explainer.css
examples/token-tax/
examples/bpe-in-60-seconds/
examples/context-window/
gallery/index.html
docs/METHOD.md
```

## Examples

- **token-tax** — the flagship: FLORES-200, five tokenizers, four languages,
  a calculator, a trust block.
- **bpe-in-60-seconds** — the smallest useful explainer: one concept, one
  token strip, one byte table.
- **context-window** — the same data, a different question: how much text
  actually fits in 128k tokens.

## Provenance

Built for the AI Builders sprint, assignment 6 («AI для визуализаций»). The
point of the skill is not this page: it is that the next explainer costs an
hour, not a day.
