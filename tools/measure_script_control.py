#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""measure_script_control.py — isolate the script effect from the language effect.

The main audit compares four *languages* (EN, RU, HI, SA). Hindi and Sanskrit
share Devanagari, which is a *script*, not a language. To test how much of the
token inflation is the script, rewrite the same sentences in Latin script:

* Russian: Cyrillic -> ASCII Latin (cyrtranslit);
* Hindi:   Devanagari -> HK (ASCII) and IAST (diacritics);
* Sanskrit: Devanagari -> HK (ASCII) and IAST (diacritics).

Then tokenize native and transliterated text with the same five tokenizers.
The ratio latin/native is the script effect *for that tokenizer*: 1.0 = no
saving, 0.5 = Latin costs half.

Caveat: transliteration changes orthography and diacritics. This is a
controlled test of script, not a proof that Latin is "better"; the residual
still contains language, vocabulary and training-data effects.

Run:
    uv run --with tiktoken --with transformers --with huggingface_hub \
        --with indic-transliteration --with cyrtranslit \
        python tools/measure_script_control.py
"""

from __future__ import annotations

import csv
import json
import sys
from datetime import date
from importlib.metadata import version
from pathlib import Path

import cyrtranslit
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

sys.path.insert(0, str(Path(__file__).resolve().parent))
from flores import LANGS, load_texts  # noqa: E402
from measure_tokens import count_tokens, load_tokenizers  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "examples" / "token-tax" / "data"
SCHEMES = {
    "RU": [("ASCII", None)],
    "HI": [("HK", sanscript.HK), ("IAST", sanscript.IAST)],
    "SA": [("HK", sanscript.HK), ("IAST", sanscript.IAST)],
}


def to_latin(lang: str, text: str, scheme: str | None) -> str:
    if lang == "RU":
        return cyrtranslit.to_latin(text, "ru")
    if lang in ("HI", "SA") and scheme is not None:
        return transliterate(text, sanscript.DEVANAGARI, scheme)
    raise ValueError(f"no transliteration for {lang}/{scheme}")


def main() -> None:
    texts = load_texts()
    n = len(texts["EN"])

    encoders, tokenizer_meta = load_tokenizers()
    results: dict[str, dict] = {}
    for name, enc in encoders.items():
        en_total = sum(count_tokens(name, enc, s) for s in texts["EN"])
        row: dict[str, dict] = {}
        for lang in ("RU", "HI", "SA"):
            native = sum(count_tokens(name, enc, s) for s in texts[lang])
            schemes: dict[str, dict] = {}
            for scheme, code in SCHEMES[lang]:
                latin = sum(count_tokens(name, enc, to_latin(lang, s, code)) for s in texts[lang])
                schemes[scheme] = {
                    "tokens_total": latin,
                    "latin_native": round(latin / native, 3),
                    "latin_en": round(latin / en_total, 3),
                }
            row[lang] = {
                "native_tokens": native,
                "native_en": round(native / en_total, 3),
                "schemes": schemes,
            }
        results[name] = row

    payload = {
        "meta": {
            "corpus": "FLORES-200 devtest",
            "n_sentences": n,
            "date": date.today().isoformat(),
            "schemes": {
                "RU": "cyrtranslit ASCII Latin",
                "HI": "HK (ASCII) + IAST (diacritics)",
                "SA": "HK (ASCII) + IAST (diacritics)",
            },
            "libraries": {
                "indic-transliteration": version("indic-transliteration"),
                "cyrtranslit": version("cyrtranslit"),
            },
            "tokenizers": tokenizer_meta,
            "caveat": "Transliteration changes orthography and diacritics; this is a "
                      "controlled test of script, not a proof that Latin is better. "
                      "The residual includes language, vocabulary and training-data effects.",
        },
        "results": results,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "script_control.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    with (OUT / "script_control.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow([
            "tokenizer", "lang", "scheme", "native_tokens", "latin_tokens",
            "latin_native", "native_en", "latin_en",
        ])
        for name, row in results.items():
            for lang, data in row.items():
                for scheme, s in data["schemes"].items():
                    writer.writerow([
                        name, lang, scheme, data["native_tokens"],
                        s["tokens_total"], s["latin_native"], data["native_en"], s["latin_en"],
                    ])

    print(f"FLORES-200 devtest · {n} sentences · script control")
    print(f"{'tokenizer':16} {'RU ASCII':>9} {'HI HK':>8} {'HI IAST':>8} {'SA HK':>8} {'SA IAST':>8}")
    for name, row in results.items():
        def r(lang, scheme):
            return row[lang]["schemes"][scheme]["latin_native"]
        print(f"{name:16} {r('RU','ASCII'):>9.2f} {r('HI','HK'):>8.2f} "
              f"{r('HI','IAST'):>8.2f} {r('SA','HK'):>8.2f} {r('SA','IAST'):>8.2f}")
    print("\nnative / EN (context):")
    for name, row in results.items():
        print(f"{name:16} RU {row['RU']['native_en']:.2f}  "
              f"HI {row['HI']['native_en']:.2f}  SA {row['SA']['native_en']:.2f}")
    print(f"\nwrote {OUT}/script_control.json and .csv")


if __name__ == "__main__":
    main()
