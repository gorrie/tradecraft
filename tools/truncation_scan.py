#!/usr/bin/env python3
"""Find silent truncation: a quantity that hit a cap and now looks like data.

WHY THIS EXISTS
---------------
Truncation is the most frequently recurring defect class in this project, and every instance
had the same signature: something stopped at a limit, the artifact stayed well-formed, and the
number derived from it went on being used. It is invisible precisely because nothing errors.

The instances, all real, all found by accident rather than by a check:

  2026-09-04  `corpus/_news-control/`: 94 of 95 background documents are EXACTLY 3,200 words
              and every one ends mid-sentence. They are fixed-size chunks of concatenated wire
              copy, not documents. Per-document background firing rates are computed as
              fired/n_docs, so the chunk size sets the rate: on identical prose, re-chunking to
              3,200 words moved `sourcing_asymmetry` from 2.1% to 12.5%. Undocumented, and it
              had been setting every background rate in the study.
  2026-09-04  `call_ollama` hardcoded `num_predict: 800` after a fork was resolved by taking
              the narrower side. A 62-item answer sheet does not fit in 800 tokens. Every
              local run would have come back short if the channel had not been broken outright.
  2026-09-04  The Wikinews media regex stopped at the first `]]`, truncating its own match and
              leaving `thumb|left|A file photo of...` in 6 of 95 documents.
  2026-08-30  `max_tokens` was never recorded, so truncation was being classified as refusal --
              fixed in 96e5fa5, which is the same defect one layer up.
  ongoing     `truncated` is a live failure class in the run classifier, which is the
              acknowledgement that this keeps happening.

A per-case patch does not generalise. The signature does:

  1. CAP SPIKE      a numeric distribution whose maximum is also its mode. A real length
                    distribution has a tail; a capped one has a wall. 94 of 95 at 3,200 is a
                    wall, and it is detectable without knowing what the cap was meant to be.
  2. ROUND CEILING  the maximum is a power of two, or a round multiple of 100/1000. Caps are
                    chosen by humans and humans choose round numbers.
  3. BROKEN TAIL    text that ends without terminal punctuation, or mid-word. A truncated
                    document is grammatical right up to where it stops.
  4. AT-CAP FIELDS  a record whose measured value sits within a hair of its own declared limit
                    (tokens_out vs max_tokens). This one is checkable exactly, when both
                    fields exist -- which is the argument for recording the limit alongside
                    the measurement in every producer.
  5. INTERIOR WALL  a value that repeats far more than its own neighbourhood warrants, wherever
                    it sits. Signatures 1 and 2 look only at the maximum, so a cap that was
                    later RAISED disappears: the fetchers append and skip ids they hold, so
                    one run at --chars 6000 and a later one at a higher limit leaves the old
                    wall buried under a new maximum, and the corpus reads as clean.

USAGE
-----
    python tools/truncation_scan.py corpus/_news-control            # a directory of text
    python tools/truncation_scan.py corpus/*.jsonl                  # JSONL, any text field
    python tools/truncation_scan.py ../research/bias-study/runs      # run records
    python tools/truncation_scan.py <paths> --check                 # exit 1 on any finding

`--check` is the gate form. It is deliberately loud rather than precise: a cap spike in a
corpus that is SUPPOSED to be chunked is a finding worth an explicit waiver in the caller, not
a threshold to tune until the warning stops.
"""
from __future__ import annotations

import argparse
import collections
import glob
import io
import json
import os
import re
import sys

#: A distribution is called capped when this share or more of its values sit at the maximum.
#: 0.5 rather than something tighter because the failures seen here are extreme -- 94 of 95 --
#: and a tight threshold on a small corpus fires on ordinary ties.
CAP_SHARE = 0.5

#: Minimum values needed before a distribution is judged at all.
MIN_N = 8

#: Text ending in one of these is finished. Anything else ends mid-thought.
_TERMINAL = tuple('.!?"”’\')]}') + (":", ";")

#: Fields that plausibly hold a document's text, in preference order.
TEXT_FIELDS = ("text", "body", "content", "response_text", "completion", "prose")

#: (measured, limit) field pairs to compare when both are present in a record.
AT_CAP_PAIRS = (("tokens_out", "max_tokens"), ("words", "max_words"),
                ("n_tokens", "token_limit"))

#: How close to its limit a value must be to count as at-cap. Absolute, not proportional:
#: a generation stops within a token or two of its budget, not within a percentage of it.
AT_CAP_SLACK = 10


def is_power_of_two(n):
    return n > 0 and (n & (n - 1)) == 0


def round_ceiling(n):
    """Why `n` looks like a human-chosen cap, or None."""
    if n <= 0:
        return None
    if is_power_of_two(n):
        return "a power of two"
    for base in (1000, 500, 100):
        if n % base == 0:
            return "a round multiple of %d" % base
    return None


def cap_spike(values):
    """(share_at_max, max) when a distribution has a wall instead of a tail, else None."""
    vals = [v for v in values if isinstance(v, int) and v >= 0]
    if len(vals) < MIN_N:
        return None
    top = max(vals)
    if top == 0:
        return None
    share = sum(1 for v in vals if v == top) / float(len(vals))
    return (share, top) if share >= CAP_SHARE else None


#: A soft cap piles values NEAR the maximum without landing exactly on it, because the cutter
#: trimmed to a word or sentence boundary after slicing. `cap_spike` cannot see that -- it
#: tests for an exact mode at the max -- and it is the commoner shape of the two.
#:
#: Added after the first run of this tool: `advocacy-specimens.jsonl` holds 18 congressional
#: hearings with a median of 4,789 words and a maximum of 5,202, and 78% of them sit within
#: 10% of that maximum. A hearing transcript runs to tens of thousands of words, so those are
#: head slices at roughly 5,000 -- and head-slicing a hearing is a standing rule against in
#: this project, sitting undetected in the corpus. `method-specimens.jsonl` shows the same
#: shape at ~800 words.
#: 0.6 was chosen while `method-specimens.jsonl` sat at 38% of its WORD maximum, i.e. it was
#: set at a level that let a truncated corpus through -- the threshold-tuning this file's own
#: docstring forbids. The repair is not a different constant: that corpus is cut at 6,000
#: CHARACTERS, where 86% of it lies within the band and 54% sits exactly on the maximum, so
#: measuring the right unit finds it at any sane threshold. The constant stays where it is
#: because moving it to catch a word-count shadow of a character cut would be fitting to the
#: artifact instead of measuring it.
SOFT_CAP_BAND = 0.10
SOFT_CAP_SHARE = 0.6


def soft_cap(values):
    """(share_in_band, max) when values crowd just under the maximum, else None."""
    vals = [v for v in values if isinstance(v, int) and v > 0]
    if len(vals) < MIN_N:
        return None
    top = max(vals)
    band = sum(1 for v in vals if v >= top * (1 - SOFT_CAP_BAND))
    share = band / float(len(vals))
    return (share, top) if share >= SOFT_CAP_SHARE else None


#: A wall's neighbourhood is +/- this share of the value, never narrower than +/- this many
#: units. The floor exists because at small values a proportional band collapses to the value
#: itself and every tie becomes a 100% "wall"; a value whose band reaches zero has no left-hand
#: neighbourhood at all and is not judged. Measured 2026-09-04 on the run records: 52 responses
#: of exactly one character (`"\n"` from one model) would otherwise read as a wall at 1.
WALL_BAND = SOFT_CAP_BAND
WALL_MIN_HALF_WIDTH = 10


def walls(values):
    """[(count, value, share_of_neighbourhood)] for every value that is a wall, anywhere.

    A wall is a value that (a) at least MIN_N documents sit on exactly and (b) accounts for
    at least CAP_SHARE of every document within its own +/- WALL_BAND neighbourhood. The two
    guards are against the two ways ordinary data ties: (a) chance -- the largest chance tie in
    any real corpus here is 5 (method-specimens, 5 documents at 802 words, out of 155) -- and
    (b) discreteness -- 1,000 documents spread over 500..900 words tie 9 deep at the mode, but
    that mode is 9 of ~200 in its band. A cut concentrates: the 84 documents at 6,000
    characters in method-specimens are 84 of the 134 within +/-10%, and buried under 90
    uncapped longer documents (where cap_spike sees 48% at the max and says nothing) they are
    84 of 91. Both constants are the existing ones on purpose; a third threshold to tune would
    be the fitting-to-the-artifact this file's docstring forbids.

    Returns every wall including one at the maximum; scan() skips the one cap_spike already
    reported so the same cut is not counted twice. A wall that is a MINORITY of its own
    neighbourhood is not called -- that is the known blind spot, stated rather than tuned away.
    """
    vals = [v for v in values if isinstance(v, int) and v > 0]
    if len(vals) < MIN_N:
        return []
    counts = collections.Counter(vals)
    out = []
    for value, count in counts.items():
        if count < MIN_N:
            continue
        half = max(int(value * WALL_BAND), WALL_MIN_HALF_WIDTH)
        if value - half <= 0:
            continue
        near = sum(k for x, k in counts.items() if abs(x - value) <= half)
        share = count / float(near)
        if share >= CAP_SHARE:
            out.append((count, value, share))
    return sorted(out, reverse=True)


#: A final line that is an ENUMERATED ITEM means the text is structured output -- an answer
#: sheet, a numbered list, a table -- and its last line is supposed to end on a word with no
#: full stop.
#:
#: Added immediately after the first run against run records, which reported 27 of 32
#: forced-choice answer sheets as "ends mid-sentence on 'Disagree'". They end on
#: `62. Strongly Disagree`, which is a complete and correct sheet. A scanner that flags correct
#: data is a scanner someone switches off, and then it catches nothing at all -- the same
#: reasoning that keeps the B&N gate reporting n/a rather than failing over a channel nobody
#: uploads to.
_ENUMERATED_TAIL = re.compile(r"(?m)^\s*\(?\d{1,3}[.):\]]\s*\S.*$")

#: Likewise a bullet, a key: value line, or a bare heading.
_STRUCTURED_TAIL = re.compile(r"(?m)^\s*(?:[-*•]|\w[\w \t-]{0,40}:)\s*\S.*$")


#: Document types whose genuine ending is not a sentence. A Federal Register notice closes
#: with its filing line and a billing code -- `[FR Doc. 2026-17238 Filed 8-21-26; 9:00 pm]
#: BILLING CODE 7710-12-P` -- which is the true end of the document and not a cut.
#:
#: Added after the first run flagged 18 of 20 `_calibration-cache` notices as truncated. They
#: are complete. This is the second false-positive class the scanner produced, after the
#: answer sheets, and both were found by reading what it flagged rather than trusting the
#: count -- which is the only way a detector like this earns its output.
_KNOWN_TERMINATORS = (
    # `[\dA-Z-]+`, not `[\d-]+[A-Z]?`: real codes are 7710-12-P, 4810-AL-P, 6325-39-P -- the
    # letter segments run to two characters and appear mid-code, and the narrow first version
    # matched 19 of 20 and left one file flagged, which reads as a genuine finding.
    re.compile(r"(?i)billing\s+code\s+[\dA-Z-]+\s*$"),
    re.compile(r"(?i)\[FR\s+Doc\.[^\]]*\]\s*$"),
    re.compile(r"(?i)\b(?:end\s+of\s+document|###|-30-)\s*$"),
)


def known_terminator(text):
    """True when the text ends the way its document type is supposed to end."""
    t = (text or "").rstrip()
    return any(p.search(t) for p in _KNOWN_TERMINATORS)


def looks_structured(text):
    """True when the LAST non-empty line is a list item, not a sentence."""
    lines = [ln for ln in (text or "").splitlines() if ln.strip()]
    if not lines:
        return False
    last = lines[-1]
    return bool(_ENUMERATED_TAIL.match(last) or _STRUCTURED_TAIL.match(last))


def broken_tail(text):
    """Why this text looks cut off, or None."""
    t = (text or "").rstrip()
    if not t:
        return None
    if t[-1] in _TERMINAL:
        return None
    if looks_structured(t) or known_terminator(t):
        return None
    # A trailing word fragment is stronger evidence than a missing full stop: a heading or a
    # list item legitimately ends without punctuation, mid-word never does.
    last = t.split()[-1] if t.split() else ""
    if len(last) > 1 and last[-1].isalpha():
        return "ends mid-sentence on %r" % last[-24:]
    return "ends without terminal punctuation"


def at_cap(record):
    """Measured values sitting on their own declared limit."""
    out = []
    for measured, limit in AT_CAP_PAIRS:
        m, lim = record.get(measured), record.get(limit)
        if isinstance(m, int) and isinstance(lim, int) and lim > 0:
            if m >= lim - AT_CAP_SLACK:
                out.append("%s=%d is at its %s=%d" % (measured, m, limit, lim))
    return out


#: A directory of plain .txt files has nowhere to put a per-record `truncated` flag, so a
#: DELIBERATELY chunked corpus stays permanently HIGH and the gate gets switched off wholesale.
#: `corpus/_news-control` is exactly that: 94 files at exactly 3,200 words, fully written up in
#: `eval/background_rate.ROLES` -- documented in the one place a reader of the RATES would look,
#: and invisible to the scanner reading the FILES.
#:
#: So a directory may declare itself, in a sidecar the data sits next to:
#:
#:     {"unit": "words", "cap": 3200, "why": "...", "see": "eval/background_rate.py"}
#:
#: THE DECLARATION IS VERIFIED, NOT TRUSTED. `scan` re-measures and reports [HIGH]
#: declaration-mismatch when the cap on disk is not the cap declared -- so this cannot be used
#: to wave a scanner off a real cut, which is the one repair this project does not make. A
#: verified declaration moves the finding from HIGH to INFO; it never removes it.
SIDECAR = ".truncation.json"


def sidecar(directory):
    """The directory's own truncation declaration, or {}."""
    p = os.path.join(directory, SIDECAR)
    if not os.path.isfile(p):
        return {}
    try:
        d = json.load(io.open(p, encoding="utf-8"))
    except (ValueError, OSError):
        return {}
    if not isinstance(d, dict) or not isinstance(d.get("cap"), int):
        return {}
    if d.get("unit") not in ("words", "characters"):
        return {}
    return d


def load_texts(path, declared_by=None):
    """[(name, text, record)] from a directory of text files, or a JSONL, or one file."""
    out = []
    if os.path.isdir(path):
        # Resolved PER FILE, from the directory the file actually lives in, with an enclosing
        # declaration as the fallback. Reading only `path`'s own sidecar looks right and is
        # not: this tool is pointed at `corpus/`, and the bucket that needs to declare itself
        # is `corpus/_news-control/` one level down -- so the declaration would have been
        # silently ignored exactly when it was pointed at the way CI points at it.
        decl = declared_by or sidecar(path) or None
        seen = {}
        for p in sorted(glob.glob(os.path.join(path, "**", "*"), recursive=True)):
            if os.path.isfile(p) and os.path.splitext(p)[1] in (".txt", ".md", ".jsonl"):
                d = os.path.dirname(p)
                if d not in seen:
                    seen[d] = sidecar(d) or decl
                out += load_texts(p, declared_by=seen[d])
        return out
    if path.endswith(".jsonl"):
        for i, line in enumerate(io.open(path, encoding="utf-8", errors="replace")):
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if not isinstance(rec, dict):
                continue
            text = next((rec[f] for f in TEXT_FIELDS
                         if isinstance(rec.get(f), str) and rec[f]), "")
            name = str(rec.get("id") or rec.get("title") or rec.get("model")
                       or "%s:%d" % (os.path.basename(path), i + 1))
            if declared_by and rec.get("truncated") is not True:
                rec = dict(rec, _dir_declared=declared_by)
            out.append((name, text, rec))
        return out
    text = io.open(path, encoding="utf-8", errors="replace").read()
    rec = {"_dir_declared": declared_by} if declared_by else {}
    out.append((os.path.basename(path), text, rec))
    return out


def scan(path):
    items = load_texts(path)
    if not items:
        return None
    findings = []

    # SUPPRESSION IS PER RECORD, NOT PER INPUT. It was `if not declared` over the whole file,
    # so ONE record carrying `truncated: true` switched cap-spike and soft-cap off for every
    # other record in the input. Both fetchers open their output in APPEND mode and skip ids
    # they already have, so the very next fetch would have written a handful of declared
    # records beside 155 undeclared ones and blinded the scanner to all 155. A gate that a
    # single row can disable is not a gate.
    # A DIRECTORY-LEVEL DECLARATION IS VERIFIED BEFORE IT SUPPRESSES ANYTHING.
    #
    # Re-measure the cap the sidecar claims. If the files are cut somewhere else, the
    # declaration is WRONG and is reported as its own HIGH finding, with every record left
    # undeclared -- so a stale or invented sidecar makes the output worse, not quieter. That
    # asymmetry is the whole design: the only way a declaration helps is by being true.
    dir_decl = next((r["_dir_declared"] for _, _, r in items if r.get("_dir_declared")), None)
    dir_ok = False
    if dir_decl:
        unit, cap = dir_decl["unit"], dir_decl["cap"]
        sized = [(len(t.split()) if unit == "words" else len(t))
                 for _, t, r in items if r.get("_dir_declared")]
        hits = sum(1 for v in sized if v == cap)
        dir_ok = bool(sized) and hits >= 0.5 * len(sized)
        if not dir_ok:
            most = collections.Counter(sized).most_common(1)
            findings.append({
                "kind": "declaration-mismatch",
                "detail": "%s declares a cap of %d %s, but only %d of %d file(s) are that "
                          "long (most common: %s). The declaration does not describe the data "
                          "-- fix one or the other; it suppresses nothing until it is true."
                          % (SIDECAR, cap, unit, hits, len(sized),
                             ("%d words x%d" % (most[0][0], most[0][1])) if most else "n/a"),
                "severity": "high"})

    undeclared = [(n, t, r) for n, t, r in items
                  if r.get("truncated") is not True
                  and not (dir_ok and r.get("_dir_declared"))]
    declared = len(items) - len(undeclared)

    # MEASURE CHARACTERS AS WELL AS WORDS. This tool looked only at word counts, and the cut
    # it was written to find is a CHARACTER cut: `fetch_federal_register` sliced
    # `[:args.chars]` at 6,000, so `method-specimens.jsonl` is 84 of 155 documents at exactly
    # 6,000 characters -- 54%, well over CAP_SHARE -- and 1 of 155 at its maximum word count.
    # The tool reported "no truncation signature" on the corpus its own commit message called
    # truncated. A cap is imposed in whatever unit the cutter used; measure both or miss the
    # ones that do not match your guess.
    measures = (("words", [len(t.split()) for _, t, _ in undeclared]),
                ("characters", [len(t) for _, t, _ in undeclared]))
    lengths = measures[0][1] or [0]

    spike = None
    spike_tops = {}
    for unit, vals in measures:
        got = cap_spike(vals)
        if not got:
            continue
        spike = got
        share, top = got
        spike_tops[unit] = top
        why = round_ceiling(top)
        findings.append({
            "kind": "cap-spike",
            "detail": "%d of %d undeclared document(s) are exactly %d %s long%s"
                      % (int(round(share * len(vals))), len(vals), top, unit,
                         " -- %s" % why if why else ""),
            "severity": "high" if why else "medium"})

    # A WALL BELOW THE MAXIMUM. Both detectors above test the top of the distribution, so a cap
    # that has since been raised is invisible to them: `fetch_federal_register.py` appends to
    # its output and skips ids it already holds, so a run at --chars 6000 followed by one at a
    # higher limit leaves the 84 documents cut at 6,000 under a new maximum. Measured on that
    # shape (84 at exactly 6,000 characters + 90 uncapped documents spread 6,100..20,000):
    # cap_spike None -- 48% at the max, under CAP_SHARE -- soft_cap None, walls() 84 of 91.
    #
    # Documents at the wall that are STRUCTURED OUTPUT are not a cut: an answer sheet's word
    # count is fixed by its answers, and `runs/calibration` holds 20 gemma2 sheets of which 10
    # are exactly 125 words, all 10 structured. Documents at a real cut are prose stopped
    # mid-line: 0 of 84 (method-specimens at 6,000 chars), 0 of 94 (_news-control at 3,200
    # words), 1 of 15 (advocacy-specimens at 30,000 chars) look structured. Half is the line.
    for unit, vals in measures:
        for count, value, share in walls(vals):
            if spike_tops.get(unit) == value:
                continue
            at_wall = [t for (_, t, _), v in zip(undeclared, vals) if v == value]
            if sum(1 for t in at_wall if looks_structured(t)) * 2 >= len(at_wall):
                continue
            top = max(vals)
            why = round_ceiling(value)
            findings.append({
                "kind": "wall",
                "detail": "%d of %d undeclared document(s) are exactly %d %s long -- %d%% of "
                          "everything within %d%% of that length, %s the maximum of %d%s"
                          % (count, len(vals), value, unit, round(share * 100),
                             round(WALL_BAND * 100),
                             "below" if value < top else "at", top,
                             " -- %s" % why if why else ""),
                "severity": "high" if why else "medium"})

    # `fetch_federal_register.py` and `fetch_govinfo.py` were changed on 2026-09-04 to WRITE
    # `truncated` / `truncated_at_chars` / `full_words`. NO ARTIFACT ON DISK CARRIES THEM YET
    # -- 18 of 18 hearings and 155 of 155 Federal Register specimens have the key absent,
    # because both fetchers skip ids they already hold, so only deleting a file and refetching
    # can retrofit it. An earlier version of this comment said the specimens "now carry" the
    # fields, which is true of the producer and false of the data: the artifact is what a
    # reader has. Nothing in eval/ reads these fields yet either.
    if declared:
        findings.append({
            "kind": "declared-truncation",
            "detail": "%d of %d record(s) DECLARE their own truncation%s -- documented and "
                      "VERIFIED against the data, not a finding"
                      % (declared, len(items),
                         (", %d of them via %s (cap %d %s, re-measured and it matches)"
                          % (sum(1 for _, _, r in items if r.get("_dir_declared")),
                             SIDECAR, dir_decl["cap"], dir_decl["unit"]))
                         if dir_ok else " (truncated_at_chars / full_words)"),
            "severity": "info"})

    if not spike:
        for unit, vals in measures:
            got = soft_cap(vals)
            if not got:
                continue
            share, top = got
            why = round_ceiling(top)
            findings.append({
                "kind": "soft-cap",
                "detail": "%d%% of undeclared document(s) sit within %d%% of the %d-%s "
                          "maximum%s"
                          % (round(share * 100), round(SOFT_CAP_BAND * 100), top, unit,
                             " -- %s" % why if why
                             else ", so the cutter trimmed to a boundary"),
                "severity": "high"})
            break

    # A record that declares its own truncation has a cut tail BY DECLARATION. Reporting that
    # as a finding would mean the disclosure earns the producer a warning, which is a perverse
    # incentive: the honest fetcher gets flagged and the silent one does not.
    tails = [(n, broken_tail(t)) for n, t, _ in undeclared]
    cut = [(n, w) for n, w in tails if w and "mid-sentence" in w]
    if cut:
        findings.append({
            "kind": "broken-tail",
            # Denominator is the documents actually TESTED, not every document in the input.
            # Declared-truncation records are excluded above, so dividing by len(items) would
            # report "3 of 155" for a corpus where only 3 were examined.
            "detail": "%d of %d tested document(s) end mid-sentence, e.g. %s: %s"
                      % (len(cut), len(tails), cut[0][0][:40], cut[0][1]),
            "severity": "high" if len(cut) > len(tails) * 0.5 else "medium"})

    capped = [(n, msgs) for n, _, r in items for msgs in [at_cap(r)] if msgs]
    if capped:
        findings.append({
            "kind": "at-cap",
            "detail": "%d record(s) sit on a declared limit, e.g. %s: %s"
                      % (len(capped), capped[0][0][:40], "; ".join(capped[0][1])),
            "severity": "high"})

    return {"path": path, "n": len(items),
            "words": sum(lengths),
            "median": sorted(lengths)[len(lengths) // 2] if lengths else 0,
            "max": max(lengths) if lengths else 0,
            "findings": findings}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--check", action="store_true",
                    help="exit 1 on a HIGH finding (a cap signature)")
    ap.add_argument("--strict", action="store_true",
                    help="with --check, also fail on MEDIUM (broken tails), which have a "
                         "known genuine population -- prose that ends on a signature")
    args = ap.parse_args(argv)

    reports = [r for r in (scan(p) for p in args.paths) if r]
    if not reports:
        print("nothing readable in: %s" % ", ".join(args.paths))
        return 0

    total = 0
    print("TRUNCATION SCAN -- a quantity that hit a cap still looks like data")
    print()
    for rep in reports:
        print("%s" % rep["path"])
        print("  %d document(s), %d words, median %d, max %d"
              % (rep["n"], rep["words"], rep["median"], rep["max"]))
        if not rep["findings"]:
            print("  no truncation signature")
        for f in rep["findings"]:
            # WHAT BLOCKS A PIPELINE IS NARROWER THAN WHAT IS WORTH REPORTING.
            #
            # An `info` line is a disclosure, not a defect. `medium` is `broken-tail`, and
            # broken-tail ALONE is not evidence of a cut: prose genuinely ends without terminal
            # punctuation. Measured 2026-09-05 on `advocacy-comments.jsonl`, 14 of its 38
            # documents "end mid-sentence" and every one of them ends on a SIGNATURE --
            # `Sincerely, Ms. Barbara Green`, `Thank you.ScottMaine`. That fetcher has no length
            # cap and no wall in its length distribution. They are real comments, correctly
            # stored, and they are 4.7% of the corpus that will never go away.
            #
            # So `--check` gates on HIGH -- the cap signatures (cap-spike, soft-cap, wall,
            # at-cap, declaration-mismatch) -- and `--strict` gates on MEDIUM as well for
            # anyone auditing rather than gating. Nothing is hidden either way: every finding
            # still prints at its own severity.
            #
            # THIS IS A SCOPE DECISION, NOT A LOOSENED DETECTOR, and the test that settles the
            # difference is `test_a_truncated_corpus_still_fails_the_default_check`: the
            # 6,000-character cut this tool was written to find is HIGH, so it fails --check
            # with or without this clause. A narrower gate that still catches the thing it was
            # built for is a gate; one that stops catching it is a retreat.
            if f["severity"] == "high" or (args.strict and f["severity"] == "medium"):
                total += 1
            print("  [%s] %s: %s" % (f["severity"].upper(), f["kind"], f["detail"]))
        print()

    if not total:
        # Say what was NOT gated on, so a green line never reads as "nothing was found".
        lesser = sum(1 for rep in reports for f in rep["findings"]
                     if f["severity"] == "medium")
        print("no cap signature in %d input(s)%s"
              % (len(reports),
                 "" if args.strict or not lesser
                 else "; %d MEDIUM finding(s) above are reported, not gated (--strict gates "
                      "them)" % lesser))
        return 0

    print("%d gating finding(s) across %d input(s)." % (total, len(reports)))
    print()
    print("A cap spike is not automatically a defect -- a deliberately chunked corpus has one")
    print("by construction. It IS automatically undocumented until someone writes down that")
    print("the chunking is deliberate and what it does to every rate computed per document.")
    return 1 if args.check else 0


if __name__ == "__main__":
    raise SystemExit(main())
