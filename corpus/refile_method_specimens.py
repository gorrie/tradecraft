#!/usr/bin/env python3
"""W1.9 — refile method-specimens.jsonl to the instrument it actually belongs to, and de-HTML it.

WHAT WAS WRONG
--------------
All 68 records carry `lens: rollback_asymmetry`. They are Federal Register measures, and
`rollback_asymmetry` is a **prose** lens: it reads irreversibility off text that ARGUES.
`detectors/ratchet_series/README.md` settled this before the file existed --

    "ALP Express Pilot to Permanent Status" scores 0.0. "Fourth Temporary Extension of
    COVID-19 Telemedicine Flexibilities" scores 0.0. Both are ratchets. Neither document says
    anything ratcheting. The pattern is not in the document.

Filing FR measures against a prose lens is what made a settled scoping decision look like a
live capability gap: the lens fires on 1 of the 68, which reads as a detector failure and is
actually a corpus mislabel. `ratchet_series` is the instrument for an administrative ratchet --
it reads a SERIES and counts one-way movement, which is where these documents belong.

Two further corrections while the file is open:

  * `instrument: ratchet_series` replaces the misleading `lens` key, and `role:
    unadjudicated-candidate` records what these actually are. Every record is `arm: null` with
    `labeled_by: null` -- they were retrieved by topical search, never adjudicated, and the
    retrieval term appears in only 13 of the 68 texts. Calling them a recall fixture overstates
    them; W2.3's hand-labelling is what would turn them into ground truth.

  * The bodies are stored as raw HTML -- `<html>`, `<head>`, `<pre>`, `<a href>` plus GPO
    boilerplate -- while every other corpus file is clean. Measured 2026-09-03, the
    contamination is cosmetic rather than load-bearing (median 805 -> 803 words, firing count
    unchanged), but a token count inflated by markup feeds the density term, and the next lens
    pointed here may not be as lucky.

Idempotent: running it twice changes nothing the second time.

    python corpus/refile_method_specimens.py --check    # report, change nothing
    python corpus/refile_method_specimens.py --apply
"""
from __future__ import annotations

import argparse
import html as html_mod
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TARGET = os.path.join(HERE, "method-specimens.jsonl")


def de_html(text):
    """Strip markup and GPO boilerplate wrappers, leaving the notice's prose.

    Delegates to `textnorm.clean`, which is the one implementation the fetchers use. This was
    a fourth private copy, and it differed: it mapped EVERY tag to a space, so `H<INF>2</INF>O`
    became three tokens. Kept as a wrapper rather than deleted, because de-forking by taking
    one side wholesale has silently broken callers in this repo five times.
    """
    import textnorm
    return textnorm.clean(text)


def refile(record):
    """Return (new_record, changed_flags)."""
    changed = []
    out = dict(record)

    if "lens" in out:
        out.pop("lens")
        out["instrument"] = "ratchet_series"
        changed.append("instrument")
    elif out.get("instrument") != "ratchet_series":
        out["instrument"] = "ratchet_series"
        changed.append("instrument")

    if out.get("role") != "unadjudicated-candidate":
        out["role"] = "unadjudicated-candidate"
        changed.append("role")

    body = out.get("text") or ""
    if "<" in body and ">" in body:
        cleaned = de_html(body)
        if cleaned and cleaned != body:
            out["text"] = cleaned
            changed.append("de-html")

    return out, changed


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--apply", action="store_true", help="write the file; otherwise report only")
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if any record still needs refiling")
    args = ap.parse_args(argv)

    if not os.path.exists(TARGET):
        print("missing %s" % os.path.relpath(TARGET, ROOT))
        return 1

    records = [json.loads(l) for l in io.open(TARGET, encoding="utf-8") if l.strip()]
    results = [refile(r) for r in records]
    pending = [c for _, c in results if c]

    counts = {}
    for _, ch in results:
        for c in ch:
            counts[c] = counts.get(c, 0) + 1

    print("%d record(s); %d need refiling" % (len(records), len(pending)))
    for key, n in sorted(counts.items()):
        print("   %-14s %d" % (key, n))

    if args.check:
        if pending:
            print("Run: python corpus/refile_method_specimens.py --apply")
            return 1
        print("method-specimens.jsonl is filed against ratchet_series and free of markup")
        return 0

    if not args.apply:
        print("(dry run -- pass --apply to write)")
        return 0

    words_before = sum(len((r.get("text") or "").split()) for r in records)
    with io.open(TARGET, "w", encoding="utf-8", newline="\n") as fh:
        for rec, _ in results:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    words_after = sum(len((r.get("text") or "").split()) for r, _ in results)
    print("wrote %s  (%d -> %d words)"
          % (os.path.relpath(TARGET, ROOT), words_before, words_after))
    return 0


if __name__ == "__main__":
    sys.exit(main())
