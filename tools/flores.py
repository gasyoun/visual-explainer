#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""flores.py — the FLORES-200 devtest loader, line-aligned by construction.

The four devtest files are line-aligned: sentence *i* is the same sentence in
every language. Any filter that runs per file (dropping blank lines, trimming
per-line content) therefore shifts every later sentence against the others and
silently poisons `ratio_median`, `ratio_p10`/`p90` and any per-sentence ratio.

So the loader refuses to guess: it keeps one line per index, trims only trailing
blank lines at the end of a file, and raises `FloresError` on an internal blank
line or on unequal file lengths.

Stdlib only, so `tools/verify.py` can test it in CI without tiktoken or
transformers.
"""

from __future__ import annotations

import sys
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".cache"
FLORES_URL = "https://dl.fbaipublicfiles.com/nllb/flores200_dataset.tar.gz"
LANGS = {"EN": "eng_Latn", "RU": "rus_Cyrl", "HI": "hin_Deva", "SA": "san_Deva"}


class FloresError(ValueError):
    """The corpus cannot be used as an aligned parallel set."""


def ensure_flores(cache: Path = CACHE) -> Path:
    """Download and extract FLORES-200 once; return the devtest directory."""
    cache.mkdir(parents=True, exist_ok=True)
    archive = cache / "flores200_dataset.tar.gz"
    if not archive.exists():
        print(f"downloading {FLORES_URL} ...", file=sys.stderr)
        urllib.request.urlretrieve(FLORES_URL, archive)
    root = cache / "flores200_dataset"
    if not (root / "devtest" / "eng_Latn.devtest").exists():
        print("extracting FLORES-200 ...", file=sys.stderr)
        with tarfile.open(archive) as tar:
            tar.extractall(cache, filter="data")
    return root / "devtest"


def read_devtest(base: Path) -> dict[str, list[str]]:
    """Read the four devtest files 1:1, or raise `FloresError`."""
    texts: dict[str, list[str]] = {}
    for lang, code in LANGS.items():
        path = base / f"{code}.devtest"
        if not path.exists():
            raise FloresError(f"missing devtest file: {path}")
        lines = path.read_text(encoding="utf-8").splitlines()
        while lines and not lines[-1].strip():      # a trailing newline is not a sentence
            lines.pop()
        if not lines:
            raise FloresError(f"empty devtest file: {path}")
        blanks = [i + 1 for i, line in enumerate(lines) if not line.strip()]
        if blanks:
            raise FloresError(
                f"{path.name}: blank line(s) at {blanks[:5]} — the files are line-aligned; "
                "filtering one file shifts every later sentence"
            )
        texts[lang] = [line.strip() for line in lines]
    lengths = {lang: len(v) for lang, v in texts.items()}
    if len(set(lengths.values())) != 1:
        raise FloresError(f"devtest files are not aligned: {lengths}")
    return texts


def load_texts(limit: int = 0, base: Path | None = None) -> dict[str, list[str]]:
    """The aligned corpus, optionally truncated to the first `limit` sentences."""
    texts = read_devtest(base or ensure_flores())
    n = min(len(v) for v in texts.values())
    if limit:
        n = min(n, limit)
    if n == 0:
        raise FloresError("FLORES devtest is empty")
    return {lang: lines[:n] for lang, lines in texts.items()}
