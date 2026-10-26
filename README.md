# visual-explainer

A personal skill that turns a concept + data into a single-file HTML explainer —
and `token-tax`, the page it generated as its first case.

**Live:** <https://gasyoun.github.io/visual-explainer/>
**Skill:** [SKILL.md](SKILL.md)

## token-tax

The same meaning costs **1.4–2.5×** more tokens in Russian and **1.6–4.9×** more
in Hindi and Sanskrit, depending on the tokenizer. Measured on 1,012 aligned
FLORES-200 sentences across five openly available tokenizers:

| Tokenizer | EN | RU | HI | SA |
|---|---:|---:|---:|---:|
| GPT-4o (o200k) | 26,873 | 1.42× | 1.57× | 2.08× |
| GPT-4 (cl100k) | 27,182 | 2.46× | 4.76× | 4.94× |
| Qwen2.5-7B | 27,621 | 1.75× | 4.42× | 4.51× |
| DeepSeek-V3 | 27,041 | 1.58× | 2.79× | 2.86× |
| Mistral-7B-v0.3 | 29,997 | 1.85× | 4.55× | 4.60× |

The finding is not "Russian is expensive" — it is that the newest OpenAI
tokenizer learned Russian but not Hindi and Sanskrit; DeepSeek is the most
Devanagari-friendly of the five (2.86×), while Qwen is 4.51× despite its
multilingual positioning.

A **script control** — the same sentences in Latin script (ASCII for Russian,
HK/IAST for Hindi and Sanskrit) — shows the effect is tokenizer-dependent:
**0.49–1.62×** Latin/native. On GPT-4o transliteration does not help
(1.06–1.62×); on GPT-4 it halves Devanagari (0.49–0.54×) but leaves Russian
alone (0.93×); on DeepSeek it is neutral for Devanagari (0.84–0.98×) and dearer
for Russian (1.42×). Devanagari is a script, not a language: the script
sets a floor, the tokenizer's vocabulary decides the bill.

The calculator accepts **characters or tokens**; in token mode the English
equivalent is `tokens / ratio`, so a real all-time token volume can be plugged
in directly.

## What's inside

| Path | What it is |
|---|---|
| [`SKILL.md`](SKILL.md) | the skill: contract, workflow, hard rules |
| [`tools/build.py`](tools/build.py) | `spec.json` → one HTML file |
| [`tools/check.py`](tools/check.py) | fail-closed checks (trust block, links, anchors, JSON payloads, mobile, external JS); `--self-test` proves it refuses |
| [`tools/verify.py`](tools/verify.py) | one command over every example: gate self-test → build parity → checks → chart probes (CI runs it) |
| [`tools/render.py`](tools/render.py) | desktop + mobile PNGs for the render review |
| [`tools/flores.py`](tools/flores.py) | the line-aligned FLORES-200 loader (refuses a misaligned corpus) |
| [`tools/measure_tokens.py`](tools/measure_tokens.py) | reproducible FLORES-200 audit |
| [`tools/measure_script_control.py`](tools/measure_script_control.py) | script control: the same sentences in Latin |
| [`tools/measure_language_mix.py`](tools/measure_language_mix.py) | sample prompt script shares (counts only) |
| [`examples/token-tax/data/script_control.csv`](examples/token-tax/data/script_control.csv) | Latin/native ratios per tokenizer |
| [`examples/token-tax/`](examples/token-tax/) | flagship: the token tax |
| [`examples/bpe-in-60-seconds/`](examples/bpe-in-60-seconds/) | mini: one concept, one strip |
| [`examples/context-window/`](examples/context-window/) | mini: 128k tokens on four languages |
| [`index.html`](index.html) | the gallery / landing page |
| [`docs/METHOD.md`](docs/METHOD.md) | corpus, metrics, caveats |

## Reproduce

```bash
uv run --with tiktoken --with transformers --with huggingface_hub \
  python tools/measure_tokens.py
```

Outputs: `examples/token-tax/data/flores_results.json`, `.csv`,
`case_studies.json`. Corpus: FLORES-200 devtest, CC-BY-SA 4.0. Tokenizer
revisions and library versions are recorded in the JSON.

Script control:

```bash
uv run --with tiktoken --with transformers --with huggingface_hub \
  --with indic-transliteration --with cyrtranslit \
  python tools/measure_script_control.py
```

Outputs: `examples/token-tax/data/script_control.json`, `.csv`.

Build a page:

```bash
python tools/build.py examples/token-tax/spec.json
python tools/check.py examples/token-tax/index.html
python tools/render.py examples/token-tax/index.html
```

## Verify

One command proves the committed pages are their specs — it rebuilds every
`examples/*/spec.json` and fails if a page changes, runs the gate (and the gate's
own self-test) on each page, and probes the chart renderer at 3 / 5 / 6
tokenizers and above-axis ratios:

```bash
python tools/verify.py            # CI runs exactly this (no dependencies)
python tools/verify.py --render   # + load each page in Chrome, fail on a JS error
```

`.github/workflows/verify.yml` runs it on every push and pull request. The gallery
`index.html` is hand-written, not generated, and is outside the gate.

Two limits worth knowing: the builder's UI copy is **Russian only** (a spec may
declare `"lang": "ru"` and nothing else until those strings move into the spec),
and the script-control table is a scheme-level view whose column headers are
written for RU/HI/SA rather than derived.

## License

Code: MIT. Data: FLORES-200 is CC-BY-SA 4.0; the derived measurements inherit
that license. Text and design: CC-BY-SA 4.0.

_Dr. Mārcis Gasūns_
