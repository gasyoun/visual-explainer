#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""measure_language_mix.py — sample prompts and count script shares.

Question: what share of the text the models see is Russian / Devanagari /
Latin? The token-tax page uses a single language; this sampler estimates the
real mix from the local harness stores.

Privacy contract
----------------
* Reads prompt text only to classify its script; **never stores or prints a
  prompt body**, a session id, a project path, or a credential.
* Writes aggregate character counts per lane only.
* Skips tool results except Claude's, which are counted as a separate
  ``claude_tool`` lane (context proxy), never printed.
* Read-only SQLite (``mode=ro&immutable=1``); no writes to the stores.

Method
------
* Random samples: 200 Claude transcripts, 60 DSH sessions, 60 Codex rollouts,
  100 zcode sessions, 100 OpenCode sessions; up to 10 text blocks per session.
* Script counts are over Unicode letters only: Cyrillic, Devanagari, Latin,
  other. The prompt share is character-weighted (not per-prompt averaged).
* ``tax_factor`` = ru_share * (1 - 1/ru_ratio) + deva_share * (1 - 1/deva_ratio)
  for GPT-4o and GPT-4 ratios from the token-tax audit. It is the share of
  input cost that would disappear if the same meaning were English.
* Prompts are only part of the input: tool output, file contents and system
  prompts dilute the non-English share. Treat the prompt tax as an upper bound;
  ``claude_tool`` is a context proxy, not the fleet input mix.

Run:
    python tools/measure_language_mix.py [--json .cache/language_mix.json]
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sqlite3
import subprocess
import sys
from collections import Counter
from pathlib import Path

HOME = Path.home()
CYR = re.compile(r"[\u0400-\u04FF]")
DEVA = re.compile(r"[\u0900-\u097F]")
LAT = re.compile(r"[A-Za-z]")

RATIOS = {
    "gpt-4o": {"ru": 1.421, "deva": 2.08},
    "gpt-4": {"ru": 2.46, "deva": 4.938},
}

MAX_CHARS = 12000
SYSTEM_PREFIXES = (
    "Current runtime context",
    "Caveat:",
    "This session is being continued",
    "<local-command",
    "# AGENTS.md",
    "You are an AI",
    "You are Codex",
    "You are Claude",
    "The following skills are available",
    "Base directory for this skill",
    "[Request interrupted",
    "<system-reminder>",
    "system-reminder",
    "Tool results",
)
# Input-token weights, billions, 30d fleet census (Claude 6.58, zcode 17.36,
# opencode 5.71) + baseline Codex ~0.29 + DSH estimate 0.10. Mixed measures;
# used only to weight lane prompt shares, never summed as a bill.
LANE_WEIGHTS = {"claude": 6.58, "dsh": 0.10, "codex": 0.29, "zcode": 17.36, "opencode": 5.71}


def script_counts(text: str) -> Counter:
    cyr = len(CYR.findall(text))
    deva = len(DEVA.findall(text))
    lat = len(LAT.findall(text))
    letters = sum(1 for ch in text if ch.isalpha())
    return Counter({"cyr": cyr, "deva": deva, "lat": lat, "other": max(letters - cyr - deva - lat, 0)})


def add(agg: Counter, text: str) -> None:
    if not text or not text.strip():
        return
    stripped = text.lstrip()
    if len(text) > MAX_CHARS or any(stripped.startswith(p) for p in SYSTEM_PREFIXES):
        return
    agg.update(script_counts(text))
    agg["blocks"] += 1


def text_from_content(content) -> list[str]:
    """Extract text blocks from a Claude/Codex content field."""
    out: list[str] = []
    if isinstance(content, str):
        return [content]
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text")
                if isinstance(text, str):
                    out.append(text)
    return out


def tool_text_from_content(content) -> list[str]:
    out: list[str] = []
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_result":
                inner = block.get("content")
                if isinstance(inner, str):
                    out.append(inner)
                elif isinstance(inner, list):
                    for b in inner:
                        if isinstance(b, dict) and isinstance(b.get("text"), str):
                            out.append(b["text"])
    return out


def sample_claude(n_files: int, per_file: int, rng: random.Random):
    files = sorted((HOME / ".claude" / "projects").glob("**/*.jsonl"))
    rng.shuffle(files)
    if n_files > 0:
        files = files[:n_files]
    prompts, tools = Counter(), Counter()
    used = 0
    for path in files:
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        p_texts, t_texts = [], []
        for line in lines:
            if '"type":"user"' not in line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if obj.get("type") != "user" or obj.get("isMeta"):
                continue
            content = (obj.get("message") or {}).get("content")
            p_texts.extend(text_from_content(content))
            t_texts.extend(tool_text_from_content(content))
        for text in (p_texts if len(p_texts) <= per_file else rng.sample(p_texts, per_file)):
            add(prompts, text)
        for text in (t_texts if len(t_texts) <= per_file else rng.sample(t_texts, per_file)):
            add(tools, text)
        used += 1
    return prompts, tools, used


def sample_dsh(n_sessions: int, per_session: int, rng: random.Random):
    files = sorted((HOME / ".dsh" / "sessions").glob("**/session.v4.jsonl.zstd"))
    rng.shuffle(files)
    agg = Counter()
    used = 0
    for path in files[:n_sessions]:
        try:
            proc = subprocess.run(["zstd", "-dc", str(path)], capture_output=True, timeout=60)
        except (OSError, subprocess.TimeoutExpired):
            continue
        if proc.returncode != 0:
            continue
        texts = []
        for line in proc.stdout.decode("utf-8", errors="replace").splitlines():
            if '"type":"user/message"' not in line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            data = obj.get("data") or {}
            source = data.get("source") or {}
            if source.get("kind") != "user":
                continue
            content = data.get("content")
            if isinstance(content, list):
                texts.extend(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
        for text in (texts if len(texts) <= per_session else rng.sample(texts, per_session)):
            add(agg, text)
        used += 1
    return agg, used


def sample_codex(n_files: int, per_file: int, rng: random.Random):
    files = sorted((HOME / ".codex" / "archived_sessions").glob("*.jsonl"))
    rng.shuffle(files)
    agg = Counter()
    used = 0
    for path in files[:n_files]:
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        texts = []
        for line in lines:
            if '"UserMessage"' not in line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            payload = obj.get("payload") or {}
            item = payload.get("item") or {}
            if item.get("type") != "UserMessage":
                continue
            content = item.get("content")
            texts.extend(text_from_content(content))
        for text in (texts if len(texts) <= per_file else rng.sample(texts, per_file)):
            add(agg, text)
        used += 1
    return agg, used


def _sqlite_ro(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True, timeout=10)


def sample_zcode(n_sessions: int, per_session: int, rng: random.Random):
    db = HOME / ".zcode" / "cli" / "db" / "db.sqlite"
    if not db.exists():
        return Counter(), 0
    conn = _sqlite_ro(db)
    try:
        sessions = [row[0] for row in conn.execute("SELECT id FROM session ORDER BY RANDOM() LIMIT ?", (n_sessions,))]
        agg = Counter()
        for sid in sessions:
            rows = conn.execute(
                """SELECT p.data FROM message m JOIN part p ON p.message_id = m.id
                   WHERE m.session_id = ?
                     AND json_extract(m.data, '$.role') = 'user'
                     AND json_extract(m.data, '$.semantics.kind') = 'user_prompt'
                     AND json_extract(p.data, '$.type') = 'text'
                   LIMIT ?""",
                (sid, per_session),
            )
            for (data,) in rows:
                try:
                    text = json.loads(data).get("text", "")
                except json.JSONDecodeError:
                    continue
                add(agg, text)
        return agg, len(sessions)
    finally:
        conn.close()


def sample_opencode(n_sessions: int, per_session: int, rng: random.Random):
    db = HOME / ".local" / "share" / "opencode" / "opencode.db"
    if not db.exists():
        return Counter(), 0
    conn = _sqlite_ro(db)
    try:
        sessions = [row[0] for row in conn.execute("SELECT id FROM session ORDER BY time_created DESC LIMIT ?", (n_sessions,))]
        agg = Counter()
        for sid in sessions:
            rows = conn.execute(
                """SELECT p.data FROM message m JOIN part p ON p.message_id = m.id
                   WHERE m.session_id = ?
                     AND json_extract(m.data, '$.role') = 'user'
                     AND json_extract(p.data, '$.type') = 'text'
                   LIMIT ?""",
                (sid, per_session),
            )
            for (data,) in rows:
                try:
                    text = json.loads(data).get("text", "")
                except json.JSONDecodeError:
                    continue
                add(agg, text)
        return agg, len(sessions)
    finally:
        conn.close()


def shares(agg: Counter) -> dict:
    total = sum(agg[k] for k in ("cyr", "deva", "lat", "other")) or 1
    return {
        "blocks": agg["blocks"],
        "chars": total,
        "ru_pct": round(100 * agg["cyr"] / total, 2),
        "deva_pct": round(100 * agg["deva"] / total, 2),
        "latin_pct": round(100 * agg["lat"] / total, 2),
        "other_pct": round(100 * agg["other"] / total, 2),
    }


def tax_factor(share: dict, model: str) -> float:
    ratios = RATIOS[model]
    return (share["ru_pct"] / 100) * (1 - 1 / ratios["ru"]) + (share["deva_pct"] / 100) * (1 - 1 / ratios["deva"])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=".cache/language_mix.json")
    ap.add_argument("--claude-files", type=int, default=200)
    ap.add_argument("--sessions", type=int, default=60)
    ap.add_argument("--per-session", type=int, default=10)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--max-chars", type=int, default=12000)
    args = ap.parse_args()
    global MAX_CHARS
    MAX_CHARS = args.max_chars
    rng = random.Random(args.seed)

    claude, claude_tool, claude_files = sample_claude(args.claude_files, args.per_session, rng)
    dsh, dsh_sessions = sample_dsh(args.sessions, args.per_session, rng)
    codex, codex_files = sample_codex(args.sessions, args.per_session, rng)
    zcode, zcode_sessions = sample_zcode(100, args.per_session, rng)
    opencode, opencode_sessions = sample_opencode(100, args.per_session, rng)

    lanes = {
        "claude_prompt": claude,
        "claude_tool": claude_tool,
        "dsh_prompt": dsh,
        "codex_prompt": codex,
        "zcode_prompt": zcode,
        "opencode_prompt": opencode,
    }
    overall = Counter()
    for name in ("claude_prompt", "dsh_prompt", "codex_prompt", "zcode_prompt", "opencode_prompt"):
        overall.update(lanes[name])

    wsum = sum(LANE_WEIGHTS.values())
    weighted_share = {
        "ru_pct": round(sum(shares(lanes[f"{lane}_prompt"])["ru_pct"] * w for lane, w in LANE_WEIGHTS.items()) / wsum, 2),
        "deva_pct": round(sum(shares(lanes[f"{lane}_prompt"])["deva_pct"] * w for lane, w in LANE_WEIGHTS.items()) / wsum, 2),
        "latin_pct": round(sum(shares(lanes[f"{lane}_prompt"])["latin_pct"] * w for lane, w in LANE_WEIGHTS.items()) / wsum, 2),
        "other_pct": round(sum(shares(lanes[f"{lane}_prompt"])["other_pct"] * w for lane, w in LANE_WEIGHTS.items()) / wsum, 2),
    }
    weighted_tax = {model: round(100 * tax_factor(weighted_share, model), 2) for model in RATIOS}
    weighted_usd = {model: round(99_787_974 / 1e6 * 2.5 * tax_factor(weighted_share, model), 2) for model in RATIOS}

    report = {
        "method": "random sample; character-weighted script shares; no bodies stored",
        "seed": args.seed,
        "coverage": {
            "claude_files": claude_files,
            "dsh_sessions": dsh_sessions,
            "codex_files": codex_files,
            "zcode_sessions": zcode_sessions,
            "opencode_sessions": opencode_sessions,
        },
        "lanes": {name: shares(agg) for name, agg in lanes.items()},
        "overall_prompt": shares(overall),
        "lane_weights_bn_input_tokens": LANE_WEIGHTS,
        "weighted_prompt": weighted_share,
        "tax_factor": {model: round(100 * tax_factor(shares(overall), model), 2) for model in RATIOS},
        "weighted_tax_factor": weighted_tax,
        "weighted_tax_usd": weighted_usd,
        "tax_factor_by_lane": {
            name: {model: round(100 * tax_factor(shares(agg), model), 2) for model in RATIOS}
            for name, agg in lanes.items()
        },
        "volume": {
            "generated_tokens": 99_787_974,
            "price_per_m": 2.5,
        },
    }
    for model in RATIOS:
        report["volume"][model] = {
            "tax_usd": round(99_787_974 / 1e6 * 2.5 * tax_factor(shares(overall), model), 2),
            "tax_pct": report["tax_factor"][model],
        }

    out = Path(args.json)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"{'lane':18} {'blocks':>7} {'chars':>12} {'RU%':>6} {'DEVA%':>6} {'LAT%':>6} {'other%':>7}")
    for name, share in report["lanes"].items():
        print(f"{name:18} {share['blocks']:>7} {share['chars']:>12,} "
              f"{share['ru_pct']:>6.2f} {share['deva_pct']:>6.2f} "
              f"{share['latin_pct']:>6.2f} {share['other_pct']:>7.2f}")
    o = report["overall_prompt"]
    print(f"{'OVERALL prompt':18} {o['blocks']:>7} {o['chars']:>12,} "
          f"{o['ru_pct']:>6.2f} {o['deva_pct']:>6.2f} {o['latin_pct']:>6.2f} {o['other_pct']:>7.2f}")
    w = report["weighted_prompt"]
    print(f"{'LANE-WEIGHTED':18} {'':>7} {'':>12} "
          f"{w['ru_pct']:>6.2f} {w['deva_pct']:>6.2f} {w['latin_pct']:>6.2f} {w['other_pct']:>7.2f}")
    print("\ntax factor (share of input cost that disappears in English):")
    for model, pct in report["tax_factor"].items():
        print(f"  {model}: {pct:.2f}% (prompt-char) · {report['weighted_tax_factor'][model]:.2f}% (lane-weighted)")
    print("\n99,787,974 generated tokens at $2.50/M:")
    for model, row in report["volume"].items():
        if isinstance(row, dict):
            print(f"  {model}: tax ${row['tax_usd']:.2f} (prompt-char) · "
                  f"${report['weighted_tax_usd'][model]:.2f} (lane-weighted)")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
