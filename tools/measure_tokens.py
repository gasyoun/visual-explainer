#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""measure_tokens.py — reproducible token-inflation audit for the token-tax page.

Corpus
------
FLORES-200 devtest: 1,012 professionally translated, aligned sentences
(CC-BY-SA 4.0, https://github.com/facebookresearch/flores).
Languages: English (eng_Latn), Russian (rus_Cyrl), Hindi (hin_Deva),
Sanskrit (san_Deva).

Tokenizers
----------
GPT-4o (o200k_base), GPT-4 (cl100k_base), Qwen2.5-7B, DeepSeek-V3,
Mistral-7B-v0.3. The HF revisions are recorded in the output JSON so the
number can be reproduced exactly.

Run
---
    uv run --with tiktoken --with transformers --with huggingface_hub \
        python tools/measure_tokens.py

Outputs
-------
    examples/token-tax/data/flores_results.json
    examples/token-tax/data/flores_results.csv
    examples/token-tax/data/case_studies.json

Notes
-----
* A tokenizer is not a model: this measures token cost, not quality.
* FLORES sentences are translations, so lengths differ. We report both the
  total ratio vs English and per-sentence median / p10 / p90, plus
  tokens-per-character (the length-normalised view).
* The two case studies (chat prompt, Bhagavad Gita 2.47) are illustrative,
  hand-written parallel texts, not part of the FLORES audit.
"""

from __future__ import annotations

import argparse
import csv
import json
import platform
import statistics
import sys
from datetime import date
from pathlib import Path

import tiktoken
import tokenizers
import transformers
from huggingface_hub import HfApi
from transformers import AutoTokenizer

sys.path.insert(0, str(Path(__file__).resolve().parent))
from flores import LANGS, load_texts  # noqa: E402  (line-aligned loader, shared)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "examples" / "token-tax" / "data"
HF_REPOS = {
    "Qwen2.5": "Qwen/Qwen2.5-7B",
    "DeepSeek-V3": "deepseek-ai/DeepSeek-V3",
    "Mistral-7B": "mistralai/Mistral-7B-v0.3",
}
TIKTOKEN_ENCODINGS = {
    "gpt-4o (o200k)": "o200k_base",
    "gpt-4 (cl100k)": "cl100k_base",
}

# Illustrative case studies — deliberately NOT used for the headline numbers.
CASE_TEXTS = {
    "prompt": {
        "EN": "Please analyze this dataset and explain the three most important trends in simple language.",
        "RU": "Пожалуйста, проанализируй этот датасет и объясни три самые важные тенденции простым языком.",
        "HI": "कृपया इस डेटासेट का विश्लेषण करें और तीन सबसे महत्वपूर्ण रुझानों को सरल भाषा में समझाएं।",
        "SA": "कृपया एतत् दत्तांशसमूहं विश्लेष्य त्रीणि प्रमुखाणि प्रवृत्तीनि सरलभाषया व्याख्यातु।",
    },
    "verse": {
        "SA": "कर्मण्येवाधिकारस्ते मा फलेषु कदाचन। मा कर्मफलहेतुर्भूर्मा ते सङ्गोऽस्त्वकर्मणि॥",
        "EN": "You have a right to action alone, never to its fruits. Do not let the fruits of action be your motive, nor let your attachment be to inaction.",
        "RU": "Ты имеешь право только на действие, но не на его плоды. Пусть плоды действия не будут твоим мотивом, и пусть у тебя не будет привязанности к бездействию.",
        "HI": "तुम्हारा अधिकार केवल कर्म करने में है, उसके फल में नहीं। फल को अपना उद्देश्य मत बनाओ, और अकर्म में भी आसक्ति मत रखो।",
    },
}


def load_tokenizers() -> tuple[dict[str, object], dict[str, dict]]:
    encoders: dict[str, object] = {}
    meta: dict[str, dict] = {}
    for name, encoding in TIKTOKEN_ENCODINGS.items():
        encoders[name] = tiktoken.get_encoding(encoding)
        meta[name] = {
            "kind": "tiktoken",
            "encoding": encoding,
            "version": tiktoken.__version__,
        }

    api = HfApi()
    for name, repo in HF_REPOS.items():
        try:
            enc = AutoTokenizer.from_pretrained(repo, use_fast=True)
        except Exception:
            enc = AutoTokenizer.from_pretrained(repo, use_fast=True, trust_remote_code=True)
        encoders[name] = enc
        try:
            revision = api.model_info(repo).sha
        except Exception as exc:  # network failure must not lose the measurement
            revision = f"unavailable: {exc}"
        meta[name] = {
            "kind": "hf",
            "repo": repo,
            "revision": revision,
            "vocab_size": enc.vocab_size,
        }
    return encoders, meta


def count_tokens(name: str, enc: object, text: str) -> int:
    if name.startswith("gpt-"):
        return len(enc.encode(text))  # type: ignore[attr-defined]
    return len(enc.encode(text, add_special_tokens=False))  # type: ignore[attr-defined]


def summarise(counts: dict[str, list[int]], chars: dict[str, list[int]],
              words: dict[str, list[int]]) -> dict[str, dict]:
    n = len(counts["EN"])
    per_sentence = {
        lang: [counts[lang][i] / counts["EN"][i] for i in range(n) if counts["EN"][i]]
        for lang in LANGS
    }
    result: dict[str, dict] = {}
    for lang in LANGS:
        ratios = sorted(per_sentence[lang])
        total_chars = sum(chars[lang])
        result[lang] = {
            "tokens_total": sum(counts[lang]),
            "tokens_mean": round(statistics.mean(counts[lang]), 2),
            "chars_total": total_chars,
            "tokens_per_char": round(sum(counts[lang]) / total_chars, 4),
            "tokens_per_100_chars": round(100 * sum(counts[lang]) / total_chars, 2),
            "tokens_per_word": round(sum(counts[lang]) / max(sum(words[lang]), 1), 2),
            "ratio_total": round(sum(counts[lang]) / sum(counts["EN"]), 3),
            "ratio_median": round(statistics.median(ratios), 3),
            "ratio_p10": round(ratios[int(0.10 * (len(ratios) - 1))], 3),
            "ratio_p90": round(ratios[int(0.90 * (len(ratios) - 1))], 3),
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0,
                        help="use only the first N sentences (0 = all 1012)")
    args = parser.parse_args()

    texts = load_texts(args.limit)
    n = len(texts["EN"])
    encoders, tokenizer_meta = load_tokenizers()

    results: dict[str, dict] = {}
    for name, enc in encoders.items():
        counts = {lang: [count_tokens(name, enc, s) for s in texts[lang]] for lang in LANGS}
        chars = {lang: [len(s) for s in texts[lang]] for lang in LANGS}
        words = {lang: [len(s.split()) for s in texts[lang]] for lang in LANGS}
        results[name] = summarise(counts, chars, words)

    OUT.mkdir(parents=True, exist_ok=True)
    payload = {
        "meta": {
            "corpus": "FLORES-200 devtest",
            "corpus_url": "https://github.com/facebookresearch/flores",
            "corpus_license": "CC-BY-SA 4.0",
            "n_sentences": n,
            "languages": LANGS,
            "date": date.today().isoformat(),
            "python": platform.python_version(),
            "transformers": transformers.__version__,
            "tokenizers_lib": tokenizers.__version__,
            "tiktoken": tiktoken.__version__,
            "tokenizers": tokenizer_meta,
            "caveat": "A tokenizer is not a model; this measures token cost, not quality. "
                      "FLORES sentences are translations, so lengths differ; see ratio_median "
                      "and tokens_per_char for length-normalised views.",
        },
        "results": results,
    }
    (OUT / "flores_results.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    with (OUT / "flores_results.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow([
            "tokenizer", "lang", "tokens_total", "tokens_per_100_chars",
            "tokens_per_word", "ratio_total", "ratio_median", "ratio_p10", "ratio_p90",
        ])
        for name, row in results.items():
            for lang in LANGS:
                r = row[lang]
                writer.writerow([
                    name, lang, r["tokens_total"], r["tokens_per_100_chars"],
                    r["tokens_per_word"], r["ratio_total"], r["ratio_median"],
                    r["ratio_p10"], r["ratio_p90"],
                ])

    case_results: dict[str, dict] = {}
    for name, enc in encoders.items():
        case_results[name] = {
            register: {lang: count_tokens(name, enc, text) for lang, text in langs.items()}
            for register, langs in CASE_TEXTS.items()
        }
    (OUT / "case_studies.json").write_text(
        json.dumps({
            "note": "Illustrative hand-written parallel texts; not part of the FLORES audit.",
            "texts": CASE_TEXTS,
            "results": case_results,
        }, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )

    print(f"\nFLORES-200 devtest · {n} aligned sentences")
    print(f"{'tokenizer':16} {'EN tok':>7} {'RU x':>6} {'HI x':>6} {'SA x':>6} "
          f"{'RU med':>7} {'HI med':>7} {'SA med':>7}")
    for name, row in results.items():
        print(f"{name:16} {row['EN']['tokens_total']:>7} "
              f"{row['RU']['ratio_total']:>6.2f} {row['HI']['ratio_total']:>6.2f} "
              f"{row['SA']['ratio_total']:>6.2f} {row['RU']['ratio_median']:>7.2f} "
              f"{row['HI']['ratio_median']:>7.2f} {row['SA']['ratio_median']:>7.2f}")
    print(f"\nwrote {OUT}/flores_results.json, .csv, case_studies.json")


if __name__ == "__main__":
    main()
