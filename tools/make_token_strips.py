#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""make_token_strips.py — pre-tokenise the examples shown on the page.

The page is a single self-contained HTML file, so it does not run a tokenizer
in the browser. This script produces the token chips once, for GPT-4o
(o200k) and GPT-4 (cl100k), and writes them to
examples/token-tax/data/token_strips.json.

Run:
    uv run --with tiktoken python tools/make_token_strips.py
"""

from __future__ import annotations

import json
from pathlib import Path

import tiktoken

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "examples" / "token-tax" / "data" / "token_strips.json"

TEXTS = {
    "prompt": {
        "EN": "Please analyze this dataset and explain the three most important trends in simple language.",
        "RU": "Пожалуйста, проанализируй этот датасет и объясни три самые важные тенденции простым языком.",
        "HI": "कृपया इस डेटासेट का विश्लेषण करें और तीन सबसे महत्वपूर्ण रुझानों को सरल भाषा में समझाएं।",
        "SA": "कृपया एतत् दत्तांशसमूहं विश्लेष्य त्रीणि प्रमुखाणि प्रवृत्तीनि सरलभाषया व्याख्यातु।",
    },
    "word_sa": {"SA": "कर्मण्येवाधिकारस्ते"},
    "word_ru": {"RU": "достоинство"},
}

ENCODINGS = {"o200k": "o200k_base", "cl100k": "cl100k_base"}


def display(raw: bytes) -> dict:
    """Return a displayable token: text if valid UTF-8, hex if it is a byte fragment."""
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return {"t": None, "hex": " ".join(f"{b:02x}" for b in raw)}
    text = text.replace("\n", "↵").replace("\t", "⇥").replace(" ", "·")
    return {"t": text, "hex": None}


def main() -> None:
    result: dict[str, dict] = {}
    for key, langs in TEXTS.items():
        result[key] = {}
        for lang, text in langs.items():
            result[key][lang] = {"text": text, "encodings": {}}
            for name, encoding in ENCODINGS.items():
                enc = tiktoken.get_encoding(encoding)
                ids = enc.encode(text)
                tokens = []
                for token_id in ids:
                    raw = enc.decode_single_token_bytes(token_id)
                    tokens.append({"id": token_id, **display(raw)})
                result[key][lang]["encodings"][name] = {
                    "tokens": tokens,
                    "count": len(ids),
                    "chars": len(text),
                    "tokens_per_100_chars": round(100 * len(ids) / len(text), 1),
                }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    for key, langs in result.items():
        for lang, row in langs.items():
            counts = {n: v["count"] for n, v in row["encodings"].items()}
            print(f"{key:8} {lang}: {counts}  {row['text'][:60]}")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
