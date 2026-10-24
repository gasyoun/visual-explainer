#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build.py — spec-driven single-file HTML explainer builder.

Usage:
    python tools/build.py examples/token-tax/spec.json
    python tools/build.py examples/bpe-in-60-seconds/spec.json

Contract
--------
* The spec is JSON: title, description, lang, data paths, beats.
* Data and token strips are committed JSON next to the spec.
* The output is one self-contained index.html: inline CSS, inline JS, no
  external JavaScript. Google Fonts is the only optional network request.
* Every data beat must resolve to a committed file; the trust beat is
  mandatory in the spec.

The builder is deliberately small: six beat renderers, not a framework.
"""

from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS_PATH = ROOT / "templates" / "explainer.css"

PAGE = """<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{description}">
<meta name="color-scheme" content="light">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,600;0,9..144,900;1,9..144,400&family=Libre+Franklin:wght@400;500;600&display=swap" rel="stylesheet">
<style>
{css}
</style>
</head>
<body>
<a class="skip" href="#main">К содержанию</a>
<header class="topbar"><div class="wrap"><span class="brand">visual-explainer</span><span class="topnote">{topnote}</span></div></header>
<main id="main">
{body}
</main>
{footer}
<script>
{script}
</script>
</body>
</html>
"""


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def raw(value: str) -> str:
    """Spec-authored HTML. Never pass untrusted input here."""
    return value


def fmt_int(value: int | float) -> str:
    return f"{int(value):,}".replace(",", " ")


def plural(n: int, one: str, few: str, many: str) -> str:
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


DISPLAY = {
    "gpt-4o (o200k)": "GPT-4o (o200k)",
    "gpt-4 (cl100k)": "GPT-4 (cl100k)",
}


def display_name(name: str) -> str:
    return DISPLAY.get(name, name)


def chips(tokens: list[dict]) -> str:
    out = []
    for token in tokens:
        if token.get("t") is None:
            out.append(
                f'<span class="chip byte" title="byte fragment: {esc(token.get("hex", ""))}">'
                f'{esc(token.get("hex", ""))}</span>'
            )
        else:
            text = token["t"]
            cls = "chip space" if text.startswith("·") else "chip"
            if re.search(r"[\u0900-\u097F]", text):
                cls += " deva"
            out.append(f'<span class="{cls}">{esc(text)}</span>')
    return "".join(out)


def section_open(beat: dict, anchor: str) -> str:
    return (
        f'<section class="section" id="{esc(anchor)}"><div class="wrap">'
        f'<div class="kicker">{esc(beat.get("kicker", ""))}</div>'
        f'<h2>{raw(beat.get("title", ""))}</h2>'
    )


def intro_html(beat: dict) -> str:
    intro = beat.get("intro", "")
    return f'<div class="intro">{raw(intro)}</div>' if intro else ""


def render_hero(beat: dict) -> str:
    stats = "".join(
        f'<div class="stat"><b>{esc(item["value"])}</b><span>{esc(item["label"])}</span></div>'
        for item in beat.get("stats", [])
    )
    note = f'<p class="hero-note">{raw(beat["note"])}</p>' if beat.get("note") else ""
    return (
        '<section class="hero"><div class="wrap">'
        f'<div class="kicker">{esc(beat.get("kicker", ""))}</div>'
        f'<h1>{raw(beat.get("title", ""))}</h1>'
        f'<p class="standfirst">{raw(beat.get("standfirst", ""))}</p>'
        f'<div class="stats">{stats}</div>'
        f'{note}'
        "</div></section>"
    )


def render_token_demo(beat: dict, strips: dict) -> str:
    rows = strips.get("prompt", {})
    default_lang = beat.get("default_lang", "RU")
    default_enc = beat.get("default_enc", "o200k")
    row = rows[default_lang]["encodings"][default_enc]
    lang_buttons = "".join(
        f'<button type="button" data-strip-lang="{esc(lang)}" '
        f'aria-pressed="{"true" if lang == default_lang else "false"}">{esc(lang)}</button>'
        for lang in ("EN", "RU", "HI", "SA")
    )
    enc_buttons = "".join(
        f'<button type="button" data-strip-enc="{esc(enc)}" '
        f'aria-pressed="{"true" if enc == default_enc else "false"}">{esc(label)}</button>'
        for enc, label in (("o200k", "GPT-4o"), ("cl100k", "GPT-4"))
    )
    return (
        section_open(beat, "token")
        + intro_html(beat)
        + '<div class="demo">'
        + '<div class="demo-controls">'
        + f'<div><div class="seg" role="group" aria-label="Язык">{lang_buttons}</div></div>'
        + f'<div><div class="seg" role="group" aria-label="Токенизатор">{enc_buttons}</div></div>'
        + f'<div class="demo-meta" id="strip-meta"><b>{row["count"]}</b> '
          f'{plural(row["count"], "токен", "токена", "токенов")} · '
          f'{row["chars"]} {plural(row["chars"], "символ", "символа", "символов")} · '
          f'{row["tokens_per_100_chars"]} на 100 символов</div>'
        + "</div>"
        + f'<div class="chips" id="strip-chips">{chips(row["tokens"])}</div>'
        + '<div class="legend"><span><i></i>токен</span>'
          '<span><i class="byte"></i>обрывок UTF-8, не буква</span></div>'
        + "</div>"
        + f'<p class="note">{raw(beat.get("note", ""))}</p>'
        + "</div></section>"
        + f'<script type="application/json" id="strip-data">{json.dumps(rows, ensure_ascii=False)}</script>'
    )


def render_bars(beat: dict, data: dict) -> str:
    results = data["results"]
    names = list(results)
    width, height = 1000, 5 * 84 + 66
    label_x, chart_x, chart_w = 0, 190, 760
    top, group_h, max_ratio = 30, 84, 5.2
    scale = chart_w / max_ratio
    colors = {"RU": "#A32035", "HI": "#B07C1F", "SA": "#0D7F63"}
    bars = []
    # vertical gridlines + ticks
    for tick in range(1, 6):
        x = chart_x + tick * scale
        bars.append(f'<line x1="{x:.1f}" y1="{top - 6}" x2="{x:.1f}" y2="{height - 30}" '
                    f'stroke="#E7E0D2" stroke-width="1"/>')
        bars.append(f'<text x="{x:.1f}" y="{height - 12}" text-anchor="middle" '
                    f'font-family="Libre Franklin, sans-serif" font-size="11" fill="#6B6F76">'
                    f'{tick}×</text>')
    # EN baseline
    x1 = chart_x + scale
    bars.append(f'<line x1="{x1:.1f}" y1="{top - 6}" x2="{x1:.1f}" y2="{height - 30}" '
                f'stroke="#B9AF9C" stroke-width="1" stroke-dasharray="3 3"/>')
    bars.append(f'<text x="{x1 + 5:.1f}" y="{top - 12}" font-family="Libre Franklin, sans-serif" '
                f'font-size="10" letter-spacing="1" fill="#6B6F76">EN = 1×</text>')
    for i, name in enumerate(names):
        y = top + i * group_h
        row = results[name]
        bars.append(f'<text x="{label_x}" y="{y + 16}" font-family="Libre Franklin, sans-serif" '
                    f'font-size="14" font-weight="600" fill="#20242C">{esc(display_name(name))}</text>')
        bars.append(f'<text x="{label_x}" y="{y + 32}" font-family="Libre Franklin, sans-serif" '
                    f'font-size="10" letter-spacing="1" fill="#6B6F76">'
                    f'{row["EN"]["tokens_total"]:,} EN-токенов</text>'.replace(",", " "))
        for j, lang in enumerate(("RU", "HI", "SA")):
            ratio = row[lang]["ratio_total"]
            bar_y = y + 6 + j * 18
            bar_w = ratio * scale
            bars.append(f'<rect x="{chart_x}" y="{bar_y}" width="{bar_w:.1f}" height="12" '
                        f'fill="{colors[lang]}"/>')
            bars.append(f'<text x="{chart_x + bar_w + 7:.1f}" y="{bar_y + 10}" '
                        f'font-family="Libre Franklin, sans-serif" font-size="12" '
                        f'fill="#20242C">{ratio:.2f}×</text>')
        bars.append(f'<line x1="0" y1="{y + 70}" x2="{width}" y2="{y + 70}" '
                    f'stroke="#E7E0D2" stroke-width="1"/>')
    svg = (
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-labelledby="bars-title bars-desc">'
        f'<title id="bars-title">Отношение числа токенов к английскому по пяти токенизаторам</title>'
        f'<desc id="bars-desc">FLORES-200 devtest, 1012 предложений. Русский 1.42–2.46×, '
        f'хинди 1.57–4.76×, санскрит 2.08–4.94× к английскому.</desc>'
        + "".join(bars) + "</svg>"
    )
    table_rows = "".join(
        f'<tr><td>{esc(display_name(name))}</td>'
        f'<td class="num">{row["EN"]["tokens_total"]:,}</td>'
        f'<td class="num">{row["RU"]["ratio_total"]:.2f}×</td>'
        f'<td class="num">{row["HI"]["ratio_total"]:.2f}×</td>'
        f'<td class="num">{row["SA"]["ratio_total"]:.2f}×</td>'
        f'<td class="num">{row["SA"]["tokens_per_100_chars"]:.1f}</td></tr>'
        for name, row in results.items()
    ).replace(",", " ")
    mobile_groups = []
    for name, row in results.items():
        mobile_rows = []
        for lang in ("RU", "HI", "SA"):
            ratio = row[lang]["ratio_total"]
            mobile_rows.append(
                f'<div class="mrow"><span class="mlang">{lang}</span>'
                f'<div class="mtrack"><div class="mfill" style="width:{ratio / max_ratio * 100:.1f}%;'
                f'background:{colors[lang]}"></div></div>'
                f'<b>{ratio:.2f}×</b></div>'
            )
        mobile_groups.append(
            f'<div class="mgroup"><div class="mname">{esc(display_name(name))}</div>'
            + "".join(mobile_rows) + "</div>"
        )
    mobile_chart = f'<div class="mobile-chart">{"".join(mobile_groups)}</div>'
    findings = "".join(
        f'<div class="finding"><b>{esc(item["n"])}</b><div><h3>{raw(item["title"])}</h3>'
        f'<p>{raw(item["text"])}</p></div></div>'
        for item in beat.get("findings", [])
    )
    return (
        section_open(beat, "audit")
        + intro_html(beat)
        + '<div class="chart-legend"><span><i style="background:#A32035"></i>русский</span>'
          '<span><i style="background:#B07C1F"></i>хинди</span>'
          '<span><i style="background:#0D7F63"></i>санскрит</span>'
          '<span><i style="background:#C6BFB0"></i>английский = 1×</span></div>'
        + f'<div class="chart-wrap">{svg}</div>'
        + mobile_chart
        + f'<p class="note">{raw(beat.get("caption", ""))}</p>'
        + f'<div class="findings">{findings}</div>'
        + '<details class="data-table"><summary>Таблица с числами</summary><div class="table-wrap"><table>'
          '<thead><tr><th>Токенизатор</th><th class="num">EN, токенов</th><th class="num">RU / EN</th>'
          '<th class="num">HI / EN</th><th class="num">SA / EN</th><th class="num">SA на 100 симв.</th></tr></thead>'
          f'<tbody>{table_rows}</tbody></table></div></details>'
        + "</div></section>"
    )


def render_bytes(beat: dict, strips: dict) -> str:
    def char_td(row: dict) -> str:
        attrs = ""
        if row.get("lang"):
            attrs += f' lang="{esc(row["lang"])}"'
        if row.get("lang") == "sa" or re.search(r"[\u0900-\u097F]", row["char"]):
            attrs += ' class="deva"'
        return f'<td{attrs}>{esc(row["char"])}</td>'

    rows = "".join(
        f'<tr>{char_td(row)}<td>{esc(row["bytes"])}</td><td>{esc(row["example"])}</td></tr>'
        for row in beat.get("table", [])
    )
    word = beat.get("word", {})
    word_data = strips.get(word.get("key", ""), {}).get(word.get("lang", ""), {})
    word_rows = []
    for spec in word.get("rows", []):
        enc = spec["enc"]
        row = word_data.get("encodings", {}).get(enc)
        if not row:
            continue
        fragments = sum(1 for token in row["tokens"] if token.get("t") is None)
        word_rows.append(
            f'<div class="word-row"><div class="tag">{esc(spec["label"])}'
            f'<b>{row["count"]} токенов · {fragments} обрывков</b></div>'
            f'<div class="chips">{chips(row["tokens"])}</div></div>'
        )
    word_html = ""
    if word_rows:
        word_html = (
            '<div class="word-block">'
            f'<h3 class="deva">{esc(word.get("text", ""))}</h3>'
            f'<p class="word-sub">{raw(word.get("sub", ""))}</p>'
            + "".join(word_rows)
            + "</div>"
        )
    return (
        section_open(beat, "why")
        + intro_html(beat)
        + f'<table class="bytes-table"><thead><tr><th>Символ</th><th>UTF-8, байт</th>'
          f'<th>Пример</th></tr></thead><tbody>{rows}</tbody></table>'
        + word_html
        + f'<div class="intro" style="margin-top:26px">{raw(beat.get("outro", ""))}</div>'
        + "</div></section>"
    )


def render_calculator(beat: dict, data: dict) -> str:
    results = data["results"]
    names = list(results)
    options = "".join(
        f'<option value="{esc(name)}">{esc(display_name(name))}</option>' for name in names
    )
    lang_options = "".join(
        f'<option value="{esc(lang)}"{" selected" if lang == "RU" else ""}>{esc(label)}</option>'
        for lang, label in (("RU", "Русский"), ("HI", "Хинди"), ("SA", "Санскрит"))
    )
    calc_data = {
        "tokenizers": {
            name: {
                lang: {
                    "tpc": row[lang]["tokens_per_100_chars"],
                    "tpw": row[lang]["tokens_per_word"],
                }
                for lang in ("EN", "RU", "HI", "SA")
            }
            for name, row in results.items()
        },
        "default_price": 2.5,
        "context": 128000,
    }
    return (
        section_open(beat, "bill")
        + intro_html(beat)
        + '<div class="calc">'
          '<div class="calc-form">'
          '<div class="field"><label for="calc-chars">Символов в месяц</label>'
          '<input id="calc-chars" type="number" min="0" step="10000" value="1000000" inputmode="numeric"></div>'
          '<div class="field"><label for="calc-price">Цена за 1M токенов, $</label>'
          '<input id="calc-price" type="number" min="0" step="0.01" value="2.50" inputmode="decimal"></div>'
          f'<div class="field"><label for="calc-tok">Токенизатор</label><select id="calc-tok">{options}</select></div>'
          f'<div class="field"><label for="calc-lang">Язык</label><select id="calc-lang">{lang_options}</select></div>'
          f'<p class="hint">{raw(beat.get("hint", ""))}</p>'
          "</div>"
          '<div class="calc-out">'
          '<div class="calc-line"><span class="k">Токенов в месяц</span>'
          '<span class="v" id="out-tokens">—</span></div>'
          '<div class="calc-line accent"><span class="k">Стоимость в месяц</span>'
          '<span class="v" id="out-cost">—</span></div>'
          '<div class="calc-line green"><span class="k">Дороже английского</span>'
          '<span class="v" id="out-delta">—</span></div>'
          '<div class="calc-line"><span class="k">Запрос на 2 000 символов</span>'
          '<span class="v" id="out-request">—</span></div>'
          '<div class="calc-bar" aria-hidden="true">'
          '<div class="row"><span>EN</span><div class="track"><div class="fill" id="bar-en" style="width:0"></div></div>'
          '<span class="num" id="bar-en-num">—</span></div>'
          '<div class="row"><span id="bar-lang-label">RU</span><div class="track">'
          '<div class="fill lang" id="bar-lang" style="width:0"></div></div>'
          '<span class="num" id="bar-lang-num">—</span></div>'
          "</div>"
          f'<p class="note">{raw(beat.get("note", ""))}</p>'
          "</div></div>"
        + f'<script type="application/json" id="calc-data">{json.dumps(calc_data, ensure_ascii=False)}</script>'
        + "</div></section>"
    )


def render_tactics(beat: dict) -> str:
    items = "".join(
        f'<div class="tactic{" wide" if item.get("wide") else ""}"><div class="n">{esc(item["n"])}</div>'
        f'<h3>{raw(item["title"])}</h3><p>{raw(item["text"])}</p>'
        f'<span class="basis">{raw(item["basis"])}</span></div>'
        for item in beat.get("items", [])
    )
    return (
        section_open(beat, "do")
        + intro_html(beat)
        + f'<div class="tactics">{items}</div>'
        + "</div></section>"
    )


def render_prose(beat: dict) -> str:
    return (
        section_open(beat, beat.get("id", "prose"))
        + f'<div class="intro">{raw(beat.get("html", ""))}</div>'
        + "</div></section>"
    )


def render_trust(beat: dict, data: dict) -> str:
    rows = "".join(
        f'<tr><td>{esc(display_name(name))}</td>'
        f'<td class="num">{row["EN"]["tokens_per_100_chars"]:.1f}</td>'
        f'<td class="num">{row["RU"]["tokens_per_100_chars"]:.1f}</td>'
        f'<td class="num">{row["HI"]["tokens_per_100_chars"]:.1f}</td>'
        f'<td class="num">{row["SA"]["tokens_per_100_chars"]:.1f}</td></tr>'
        for name, row in data["results"].items()
    )
    links = beat.get("links") or [
        {"label": "CSV с замерами", "href": "data/flores_results.csv"},
        {"label": "JSON с ревизиями", "href": "data/flores_results.json"},
        {"label": "Скрипт замера", "href": "../../tools/measure_tokens.py"},
        {"label": "Скрипт полосок", "href": "../../tools/make_token_strips.py"},
    ]
    link_html = "".join(f'<a href="{esc(link["href"])}">{esc(link["label"])}</a>' for link in links)
    return (
        '<section class="trust" id="trust"><div class="wrap">'
        f'<div class="kicker">{esc(beat.get("kicker", ""))}</div>'
        f'<h2>{raw(beat.get("title", ""))}</h2>'
        f'<div class="trust-grid"><div>{raw(beat.get("html", ""))}'
        f'<div class="links">{link_html}</div></div>'
        '<div><p class="small">Токенов на 100 символов — длина-нормализованный вид. '
        'EN = английский; RU — русский; HI — хинди; SA — санскрит.</p>'
        '<div class="table-wrap"><table class="bytes-table"><thead><tr><th>Токенизатор</th>'
        '<th class="num">EN</th><th class="num">RU</th><th class="num">HI</th><th class="num">SA</th>'
        f'</tr></thead><tbody>{rows}</tbody></table></div>'
        f'<p class="small" style="margin-top:14px">{raw(beat.get("made_with", ""))}</p>'
        "</div></div></div></section>"
    )


def render_footer(footer: dict) -> str:
    links = "".join(
        f'<a href="{esc(link["href"])}">{esc(link["label"])}</a>'
        for link in footer.get("links", [])
    )
    return (
        '<footer class="footer"><div class="wrap"><div>'
        f'<div class="f-brand">{esc(footer.get("brand", "visual-explainer"))}</div>'
        f'<p>{raw(footer.get("note", ""))}</p>'
        "</div>"
        f'<div class="f-links">{links}</div>'
        "</div></footer>"
    )


SCRIPT = r"""
(function () {
  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];
    });
  }

  function plural(n, one, few, many) {
    n = Math.abs(n);
    if (n % 10 === 1 && n % 100 !== 11) return one;
    if (n % 10 >= 2 && n % 10 <= 4 && (n % 100 < 12 || n % 100 > 14)) return few;
    return many;
  }

  var stripEl = document.getElementById('strip-data');
  if (stripEl) {
    var strips = JSON.parse(stripEl.textContent);
    var lang = document.querySelector('[data-strip-lang][aria-pressed="true"]').dataset.stripLang;
    var enc = document.querySelector('[data-strip-enc][aria-pressed="true"]').dataset.stripEnc;
    var chipsEl = document.getElementById('strip-chips');
    var metaEl = document.getElementById('strip-meta');

    function chip(t) {
      if (t.t === null) {
        return '<span class="chip byte" title="byte fragment: ' + esc(t.hex) + '">' + esc(t.hex) + '</span>';
      }
      var cls = t.t.indexOf('·') === 0 ? 'chip space' : 'chip';
      if (/[\u0900-\u097F]/.test(t.t)) cls += ' deva';
      return '<span class="' + cls + '">' + esc(t.t) + '</span>';
    }

    function render() {
      var row = strips.prompt[lang].encodings[enc];
      chipsEl.innerHTML = row.tokens.map(chip).join('');
      metaEl.innerHTML = '<b>' + row.count + '</b> ' +
        plural(row.count, 'токен', 'токена', 'токенов') + ' · ' +
        row.chars + ' ' + plural(row.chars, 'символ', 'символа', 'символов') +
        ' · ' + row.tokens_per_100_chars + ' на 100 символов';
      document.querySelectorAll('[data-strip-lang]').forEach(function (b) {
        b.setAttribute('aria-pressed', b.dataset.stripLang === lang ? 'true' : 'false');
      });
      document.querySelectorAll('[data-strip-enc]').forEach(function (b) {
        b.setAttribute('aria-pressed', b.dataset.stripEnc === enc ? 'true' : 'false');
      });
    }

    document.querySelectorAll('[data-strip-lang]').forEach(function (b) {
      b.addEventListener('click', function () { lang = b.dataset.stripLang; render(); });
    });
    document.querySelectorAll('[data-strip-enc]').forEach(function (b) {
      b.addEventListener('click', function () { enc = b.dataset.stripEnc; render(); });
    });
  }

  var calcEl = document.getElementById('calc-data');
  if (calcEl) {
    var data = JSON.parse(calcEl.textContent);
    var chars = document.getElementById('calc-chars');
    var price = document.getElementById('calc-price');
    var tok = document.getElementById('calc-tok');
    var langSel = document.getElementById('calc-lang');
    var nf = new Intl.NumberFormat('ru-RU');
    var cf = new Intl.NumberFormat('ru-RU', {style: 'currency', currency: 'USD', minimumFractionDigits: 2, maximumFractionDigits: 2});

    function num(el) { var v = parseFloat(el.value); return isFinite(v) && v > 0 ? v : 0; }

    function calc() {
      var t = data.tokenizers[tok.value];
      var l = langSel.value;
      var c = num(chars);
      var p = num(price);
      var enTokens = c * t.EN.tpc / 100;
      var langTokens = c * t[l].tpc / 100;
      var enCost = enTokens / 1e6 * p;
      var langCost = langTokens / 1e6 * p;
      var delta = enTokens ? langTokens / enTokens : 0;
      var req = 2000 * t[l].tpc / 100;

      document.getElementById('out-tokens').textContent = nf.format(Math.round(langTokens));
      document.getElementById('out-cost').innerHTML = cf.format(langCost) +
        '<small>при $' + p.toFixed(2) + ' / 1M</small>';
      document.getElementById('out-delta').innerHTML = '×' + delta.toFixed(2) +
        '<small>на тот же объём</small>';
      document.getElementById('out-request').innerHTML = nf.format(Math.round(req)) +
        '<small>' + (req / data.context * 100).toFixed(1) + '% от 128k</small>';
      document.getElementById('bar-lang-label').textContent = l;
      var max = Math.max(enTokens, langTokens) || 1;
      document.getElementById('bar-en').style.width = (enTokens / max * 100) + '%';
      document.getElementById('bar-lang').style.width = (langTokens / max * 100) + '%';
      document.getElementById('bar-en-num').textContent = nf.format(Math.round(enTokens));
      document.getElementById('bar-lang-num').textContent = nf.format(Math.round(langTokens));
    }

    [chars, price].forEach(function (el) { el.addEventListener('input', calc); });
    [tok, langSel].forEach(function (el) { el.addEventListener('change', calc); });
    calc();
  }
})();
"""


def build(spec_path: Path) -> Path:
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    base = spec_path.parent
    data = json.loads((base / spec["data"]).read_text(encoding="utf-8"))
    strips = json.loads((base / spec["strips"]).read_text(encoding="utf-8"))

    renderers = {
        "hero": lambda b: render_hero(b),
        "token-demo": lambda b: render_token_demo(b, strips),
        "bars": lambda b: render_bars(b, data),
        "bytes": lambda b: render_bytes(b, strips),
        "calculator": lambda b: render_calculator(b, data),
        "tactics": lambda b: render_tactics(b),
        "prose": lambda b: render_prose(b),
        "trust": lambda b: render_trust(b, data),
    }
    body_parts = []
    for beat in spec["beats"]:
        renderer = renderers.get(beat["type"])
        if renderer is None:
            raise SystemExit(f"unknown beat type: {beat['type']}")
        body_parts.append(renderer(beat))

    page = PAGE.format(
        lang=esc(spec.get("lang", "ru")),
        title=esc(spec["title"]),
        description=esc(spec.get("description", "")),
        topnote=esc(spec.get("topnote", "")),
        css=CSS_PATH.read_text(encoding="utf-8"),
        body="\n".join(body_parts),
        footer=render_footer(spec.get("footer", {})),
        script=SCRIPT,
    )
    out = base / "index.html"
    out.write_text(page, encoding="utf-8")
    print(f"wrote {out} ({len(page):,} bytes)")
    return out


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: python tools/build.py <spec.json>")
    build(Path(sys.argv[1]).resolve())


if __name__ == "__main__":
    main()
