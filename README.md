# visual-explainer

A personal skill that turns a concept + data into a single-file HTML explainer —
plus `token-tax`, the first artifact it generated.

**Status:** build in progress · deadline 25-10-2026 20:00 MSK.

## token-tax

The same meaning costs **1.4–2.5×** more tokens in Russian and **2.1–4.9×** more
in Sanskrit, depending on the tokenizer. Measured on 1,012 aligned FLORES-200
sentences across five openly available tokenizers:

| Tokenizer | EN | RU | HI | SA |
|---|---:|---:|---:|---:|
| GPT-4o (o200k) | 26,873 | 1.42× | 1.57× | 2.08× |
| GPT-4 (cl100k) | 27,182 | 2.46× | 4.76× | 4.94× |
| Qwen2.5-7B | 27,621 | 1.75× | 4.42× | 4.51× |
| DeepSeek-V3 | 27,041 | 1.58× | 2.79× | 2.86× |
| Mistral-7B-v0.3 | 29,997 | 1.85× | 4.55× | 4.60× |

The finding is not "Russian is expensive" — it is that the newest OpenAI
tokenizer learned Russian but not Devanagari, DeepSeek is the most
Devanagari-friendly of the five, and Qwen is the least, despite its
multilingual positioning.

## Reproduce

```bash
uv run --with tiktoken --with transformers --with huggingface_hub \
  python tools/measure_tokens.py
```

Outputs: `examples/token-tax/data/flores_results.json`, `.csv`,
`case_studies.json`. Corpus: FLORES-200 devtest, CC-BY-SA 4.0. Tokenizer
revisions and library versions are recorded in the JSON.

## Layout

```
tools/measure_tokens.py      # reproducible audit
examples/token-tax/data/     # measured data
DECISIONS_2026-10-24.md      # the ten decisions behind the build
PLAN.md                      # scope, method, schedule, acceptance
```

## License

Code: MIT. Data: FLORES-200 is CC-BY-SA 4.0; the derived measurements inherit
that license. Text and design: CC-BY-SA 4.0.

_Dr. Mārcis Gasūns_
