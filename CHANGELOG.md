# Changelog

All notable changes to this repository. Dates are ISO (`YYYY-MM-DD`).

## [Unreleased]

### Added

- `BUGHUNT-FINDINGS-visual-explainer-25.10.2026.md` — the first hunt for this repo
  (rotation slot 4/173): 2 HIGH claim-vs-data defects on the published page (the
  «хинди и санскрит» headline range drops Hindi's 1.57×; the script-control
  «halves / nearly neutral» ranges exclude the Russian column in the same table),
  6 MEDIUM (two stale example pages, `check.py` blind to single-quoted links and
  false-failing on `?query`/`tel:`, hardcoded chart geometry, no wired gate,
  playback desync) and 6 LOW. Findings only — no code changed in that pass.

_Dr. Mārcis Gasūns_
