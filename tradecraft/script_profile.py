"""Character-set and script profile: OSINT signal that needs no vocabulary at all.

WHY THIS EXISTS
---------------
Every other detector here needs to know what words to look for, which caps it at what its
author thought to type -- measured on 2026-09-03 as a hard ceiling
(`eval/RESULTS-2026-09-03-cue-enumeration-ceiling.md`). This one needs no vocabulary, works in
every language including ones nobody here reads, and is fully deterministic: it reads which
WRITING SYSTEMS a text uses and how they are mixed.

That makes it the natural first layer for diaspora analysis, where the interesting signal is
often not which words appear but which script they appear in, whether a Latin transliteration
is being used in place of the native script, and whether scripts are being mixed inside single
words.

WHAT IT REPORTS, AND WHY EACH IS TRADECRAFT RATHER THAN TRIVIA
--------------------------------------------------------------
  scripts          Share of letters per Unicode script. A document that is 8% Arabic and 92%
                   Latin is a different object from either a monolingual Arabic document or a
                   monolingual English one -- it is usually diaspora or translation-adjacent
                   prose, and knowing that before reading is worth having.

  mixed_script     Words combining two scripts. Occasionally legitimate (a brand, a citation),
                   frequently EVASION: swapping a Cyrillic "а" into a Latin word defeats a
                   keyword filter while remaining perfectly readable. This is the single most
                   operationally useful line here and it is why filters get bypassed.

  confusables      Mixed-script words whose non-Latin characters are Latin look-alikes -- the
                   deliberate subset of the above. `Кiev` with a Cyrillic К reads as Latin and
                   matches no Latin cue.

  invisibles       Zero-width joiners/non-joiners/spaces and bidi overrides. Zero-width
                   characters break substring matching invisibly, and bidi overrides can make
                   displayed text read differently from its byte order. Any nonzero count here
                   is worth a human look.

  diacritic_rate   Combining-mark density. Separates native orthography from stripped
                   transliteration, which matters when the same community writes both ways.

DISCIPLINE, unchanged from the rest of the repository
-----------------------------------------------------
**Flag with receipts, never a verdict.** Every flag carries the offending strings so a human
adjudicates. Mixed script is not proof of evasion -- it is proof of mixed script. And nothing
here is a lens: it produces no index, contributes no leaderboard rank, and is not scored.
It is a profile that tells an analyst which instrument to reach for next.

Analysis lives here so the package can use it; the CLI is tools/script_profile.py.
"""
from __future__ import annotations

import re
import unicodedata

#: Unicode block prefixes are a good-enough proxy for script, and stdlib-only. `unicodedata`
#: exposes no script property, so the name of each character is used: every Cyrillic letter's
#: name begins "CYRILLIC", every Arabic letter's "ARABIC", and so on.
def script_of(ch):
    if not ch.isalpha():
        return None
    try:
        name = unicodedata.name(ch)
    except ValueError:
        return "UNNAMED"
    return name.split()[0]


#: Characters that are invisible or reorder display. Any of these in prose is worth seeing.
INVISIBLES = {
    "​": "ZERO WIDTH SPACE",
    "‌": "ZERO WIDTH NON-JOINER",
    "‍": "ZERO WIDTH JOINER",
    "⁠": "WORD JOINER",
    "﻿": "ZERO WIDTH NO-BREAK SPACE (BOM)",
    "­": "SOFT HYPHEN",
    "‪": "LEFT-TO-RIGHT EMBEDDING",
    "‫": "RIGHT-TO-LEFT EMBEDDING",
    "‭": "LEFT-TO-RIGHT OVERRIDE",
    "‮": "RIGHT-TO-LEFT OVERRIDE",
    "⁦": "LEFT-TO-RIGHT ISOLATE",
    "⁧": "RIGHT-TO-LEFT ISOLATE",
}

#: Non-Latin characters that read as Latin letters. Not exhaustive -- the operationally common
#: ones. A word mixing these with Latin is the classic keyword-filter bypass.
CONFUSABLE = {
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c",
    "у": "y", "х": "x", "А": "A", "В": "B", "Е": "E",
    "К": "K", "М": "M", "Н": "H", "О": "O", "Р": "P",
    "С": "C", "Т": "T", "Х": "X", "і": "i", "І": "I",
    "ο": "o", "α": "a", "ε": "e", "Α": "A", "Β": "B",
    "Ε": "E", "Κ": "K", "Μ": "M", "Ν": "N", "Ο": "O",
    "Ρ": "P", "Τ": "T", "Χ": "X",
    # Added after the first run flagged `ruѕѕian` as mixed-script but not as confusable: the
    # Cyrillic dze reads as a Latin s and was missing. If a look-alike is absent from this map
    # the word still surfaces under mixed_script, so a gap costs specificity, not recall.
    "ѕ": "s", "ј": "j", "һ": "h", "ԁ": "d", "ӏ": "l",
    "ν": "v", "ι": "i", "κ": "k", "ρ": "p", "τ": "t",
    "υ": "u", "γ": "y", "Ι": "I", "Η": "H", "Ζ": "Z",
    "Υ": "Y", "Ϲ": "C", "Ѵ": "V", "Ԛ": "Q", "Ԝ": "W",
}

WORD = re.compile(r"[^\s\d\W]+", re.UNICODE)


def profile(text):
    letters = [c for c in text if c.isalpha()]
    counts = {}
    for ch in letters:
        s = script_of(ch)
        if s:
            counts[s] = counts.get(s, 0) + 1
    total = max(1, len(letters))
    scripts = {s: round(n / total, 4) for s, n in
               sorted(counts.items(), key=lambda kv: -kv[1])}

    mixed, confus = [], []
    for m in WORD.finditer(text):
        w = m.group(0)
        ss = {script_of(c) for c in w if c.isalpha()}
        ss.discard(None)
        if len(ss) > 1:
            entry = {"word": w, "scripts": sorted(ss), "offset": m.start()}
            mixed.append(entry)
            if any(c in CONFUSABLE for c in w) and "LATIN" in ss:
                confus.append(dict(entry, latin_lookalikes=sorted(
                    {"%s->%s" % (c, CONFUSABLE[c]) for c in w if c in CONFUSABLE})))

    invis = {}
    for ch, name in INVISIBLES.items():
        n = text.count(ch)
        if n:
            invis[name] = n

    marks = sum(1 for c in text if unicodedata.category(c) == "Mn")

    return {
        "letters": len(letters),
        "scripts": scripts,
        "dominant_script": next(iter(scripts), None),
        "script_count": len(scripts),
        "mixed_script_words": mixed[:50],
        "mixed_script_total": len(mixed),
        "confusable_words": confus[:50],
        "confusable_total": len(confus),
        "invisibles": invis,
        "diacritic_rate": round(marks / total, 4),
    }
