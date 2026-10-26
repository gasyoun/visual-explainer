# Changelog

All notable changes to this repository. Dates are ISO (`YYYY-MM-DD`).

## [Unreleased]

### Added

- `tools/verify.py` — one tree-level gate: `check.py --self-test` → rebuild every
  `examples/*/spec.json` and fail if a committed page changes → `check.py` on each
  page → `render_bars` probes at 3 / 5 / 6 tokenizers and above-axis ratios.
  `--render` adds a Chromium pass that fails on any JS error or horizontal overflow.
- `.github/workflows/verify.yml` — runs `python tools/verify.py` on every push to
  `main` and on every pull request (stdlib only, Python 3.12).

### Changed

- `tools/flores.py` — one line-aligned loader for the measurement scripts (was duplicated
  in two files, and both filtered blank lines **per file** before aligning by index: one
  blank line anywhere would have shifted every later sentence). It now trims only trailing
  blanks and refuses an internal blank line or unequal file lengths; `verify.py` probes all
  four cases.
- `build.py` — the chart legend, bars, table columns, strip buttons and calculator options
  derive their languages from the committed JSON (were hardcoded RU/HI/SA), and colours come
  from an index palette (a new language no longer raises `KeyError`). Output for the current
  data is byte-identical.
- `measure_language_mix.py` — `deva` is a ratio **band** (Hindi 1.573×/4.759× …
  Sanskrit 2.085×/4.938×) instead of Sanskrit's value applied to both languages; the point
  estimate uses the midpoint and the report carries `tax_factor_band`. The OpenCode lane is
  sampled `ORDER BY RANDOM()` as documented (was "latest 100").

- `tools/check.py` rewritten on `html.parser` (was regex): single-quoted `href`/`src`
  are now seen, same-page `#anchor` targets and inlined `application/json` payloads
  are validated, and query strings / `tel:` / `mailto:` / `javascript:` no longer
  false-fail. `--self-test` runs ten fixtures — clean pages it must pass and seeded
  defects it must refuse.

### Fixed

- **L2–L6 of the 25.10.2026 hunt** — the loader alignment fix above; `render_bytes` now
  fails closed when a requested strips key or encoding is missing (it used to render an
  empty beat); inlined JSON payloads escape `<` so a `</script>` inside any text cannot
  close the block; the builder's Russian-only copy is stated in `SKILL.md` and enforced by
  `verify.py` (a spec may only declare `"lang": "ru"`).

- **M1 of the 25.10.2026 hunt** — `bpe-in-60-seconds` and `context-window` were stale
  builds (no `#demo-play` button, old CSS); all three examples are rebuilt from their
  specs and their `desktop`/`mobile` screenshots re-rendered.
- **M4 of the 25.10.2026 hunt** — `render_bars` derives the canvas height from the number
  of tokenizers and the axis from the largest ratio (a 6th tokenizer used to be clipped at
  y=520 in a 486-tall viewBox; a 7.9× ratio used to paint outside the canvas). The SVG
  title/desc now derive the count and the per-language ranges from the committed JSON.
- **M6 of the 25.10.2026 hunt** — a manual language pick resyncs the 10-second loop index
  (`SA → ▶ → EN`; it used to jump to `HI`).
- **L1 of the 25.10.2026 hunt** — an empty or zero volume renders `—` instead of `×0.00`.
- The table-row formatter no longer mangles `font-family="Libre Franklin, sans-serif"`
  into `Libre Franklin  sans-serif` (numbers are formatted with `fmt_int()`).
- **H1 of the 25.10.2026 hunt** — the «хинди и санскрит» headline range was
  `2.08–4.94×` (Sanskrit's floor), dropping Hindi's `1.573×` on GPT-4o. Corrected to
  **`1.57–4.94×`** in `spec.json` (hero stat, standfirst, closing beat, `<meta
  description>`), rebuilt into `index.html`, and mirrored in `README.md` (`1.6–4.9×`),
  `POST.md` and `PLAN.md`.
- **H2 of the 25.10.2026 hunt** — «GPT-4 режет почти вдвое (0.49–0.54×)» and «на DeepSeek
  разницы почти нет (0.84–0.98×)» were ranges over an unstated subset; the Russian column
  in the same table is 0.93× (GPT-4) and 1.42× (DeepSeek). All three verdicts now name
  **HK-запись деванагари** and state the Russian exception (`README.md`, `POST.md`,
  `docs/METHOD.md`, plus the audit finding and the script-control finding title on the page).
- Screenshots re-rendered after the rebuild: `desktop.png`, `mobile.png`, `post-hero.png`,
  `post-audit.png` (`post-calc` / `post-script` / `post-loop.gif` were unaffected).
- `DECISIONS_2026-10-24.md` keeps its original wording and gains a dated **Поправка
  26-10-2026** pointing at the two defects (decision log is append-only).

### Added

- `BUGHUNT-FINDINGS-visual-explainer-25.10.2026.md` — the first hunt for this repo
  (rotation slot 4/173): 2 HIGH claim-vs-data defects on the published page (the
  «хинди и санскрит» headline range drops Hindi's 1.57×; the script-control
  «halves / nearly neutral» ranges exclude the Russian column in the same table),
  6 MEDIUM (two stale example pages, `check.py` blind to single-quoted links and
  false-failing on `?query`/`tel:`, hardcoded chart geometry, no wired gate,
  playback desync) and 6 LOW. Findings only — no code changed in that pass.

_Dr. Mārcis Gasūns_
