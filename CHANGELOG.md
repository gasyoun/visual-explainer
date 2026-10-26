# Changelog

All notable changes to this repository. Dates are ISO (`YYYY-MM-DD`).

## [Unreleased]

### Fixed

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
