#!/usr/bin/env python3
"""Harvest candidate gold from real documents the lenses already fire on.

WHY THIS EXISTS
---------------
The gold check went from 84 to 134 of 157 by repairing cues and writing examples. That number
is INTERNAL CONSISTENCY, not precision: the same hand wrote the specimen and the cue, so the
lens detecting it proves only self-consistency. Every genuine defect found tonight -- a cue
firing on a regatta, on a churchgoing aside, on a conditional in a DEA notice -- came from
outside text, not from gold.

So gold should come from the wild wherever it can. This harvests candidates from documents
already in the corpus: where a lens fires, the surrounding sentence is a real instance with a
real citation, and it is a far better gold entry than anything composed to order.

WHAT IT DOES NOT DO
-------------------
It does not promote anything automatically. Every candidate is written to a review file with
its source, its matched cue and its surrounding sentence, and a human decides. A harvester that
promoted its own hits would be writing gold that its own cue list is guaranteed to detect,
which is the circularity this is meant to escape.

    python tools/harvest_gold.py --lens legibility
    python tools/harvest_gold.py                    # every text lens
"""
from __future__ import annotations

import argparse
import glob
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from tradecraft.corpus_docs import documents  # noqa: E402
from tradecraft.detect import detect_cues   # noqa: E402
from tradecraft.loader import load_lenses    # noqa: E402

# Structural lenses read a graph, not prose, so there is nothing here to harvest from them.
# This was a hardcoded set until 2026-09-01, one of three across the repo -- each a copy of a
# fact about a lens kept somewhere other than the lens. Ask the taxonomy: `tax.is_structural`.
OUT = os.path.join(ROOT, "eval", "gold-candidates.jsonl")


def sentences(text):
    flat = " ".join(text.split())
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", flat) if len(s.split()) >= 6]


EXCERPT = 400


def around(sent, hit):
    """An excerpt CENTRED ON THE MATCH, so a receipt always contains its own evidence.

    2026-09-01. This recorded `sent[:400]` -- the first 400 characters of the sentence,
    regardless of where the cue was. When the cue sat past that boundary the candidate carried
    no trace of what fired, and a human reading it saw a passage with nothing wrong in it.

    That produced a false accusation, not just a bad excerpt. `pejorative-actor-label` was
    written up as a precision defect -- "fires where no pejorative appears" -- on a document
    that says "Cardinal Kevin Farrell and his Vatican cronies". The cue was right. The
    excerpt was 190 characters of adjacent prose, and the cue list took the blame.

    In an instrument whose first rule is flag-and-show-the-receipts, a receipt that omits its
    own evidence is the worst available failure: it looks like diligence and it misleads.
    """
    start = getattr(hit, "char_start", None)
    end = getattr(hit, "char_end", None)
    if start is None or end is None or not (0 <= start <= len(sent)):
        return sent[:EXCERPT]
    if len(sent) <= EXCERPT:
        return sent
    span = max(0, end - start)
    pad = max(0, (EXCERPT - span) // 2)
    lo = max(0, start - pad)
    hi = min(len(sent), lo + EXCERPT)
    lo = max(0, hi - EXCERPT)
    out = sent[lo:hi]
    if lo > 0:
        out = "..." + out
    if hi < len(sent):
        out = out + "..."
    return out


def sources():
    """Real documents already in the repo, with their provenance.

    2026-09-01: this named `method-specimens.jsonl` in code, so the advocacy corpus fetched
    the same night -- the argumentative prose these lenses were written for -- was invisible
    to the harvester by virtue of its filename. Enumeration now lives in one place and no
    consumer knows what the corpus files are called.
    """
    return [(d.name, d.text, d.source_url) for d in documents()]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--lens", action="append")
    ap.add_argument("--max-per-detection", type=int, default=3)
    args = ap.parse_args(argv)

    lenses = load_lenses(os.path.join(ROOT, "detectors"))
    lenses = {k: v for k, v in lenses.items() if not v.is_structural}
    if args.lens:
        lenses = {k: v for k, v in lenses.items() if k in set(args.lens)}

    docs = sources()
    print("scanning %d real document(s) for candidate gold" % len(docs))

    found = []
    per_det = {}
    misaligned = []
    for lens_id, tax in sorted(lenses.items()):
        for name, text, url in docs:
            for sent in sentences(text):
                hits = detect_cues(sent, tax)
                for h in hits:
                    key = (lens_id, h.detection_id)
                    if per_det.get(key, 0) >= args.max_per_detection:
                        continue
                    per_det[key] = per_det.get(key, 0) + 1
                    cue = getattr(h, "evidence", None) or getattr(h, "span", None)
                    excerpt = around(sent, h)
                    if cue and cue.lower() not in excerpt.lower():
                        # Should be impossible now. Counted rather than ignored, because the
                        # whole value of a receipt is that it contains its own evidence.
                        misaligned.append((lens_id, h.detection_id, cue))
                    found.append({
                        "lens": lens_id,
                        "detection": h.detection_id,
                        "text": excerpt,
                        "source_document": name,
                        "source_url": url,
                        "matched_cue": cue,
                        "status": "CANDIDATE -- a human must read this before it becomes gold",
                    })

    io.open(OUT, "w", encoding="utf-8", newline="\n").write(
        "".join(json.dumps(f, ensure_ascii=False) + "\n" for f in found))

    by_lens = {}
    for f in found:
        by_lens.setdefault(f["lens"], set()).add(f["detection"])
    print()
    print("%-28s %8s %s" % ("lens", "cands", "detections with a real-world candidate"))
    for lens_id in sorted(lenses):
        c = [f for f in found if f["lens"] == lens_id]
        n_det = sum(len(m.detections) for m in lenses[lens_id].markers)
        print("%-28s %8d %d of %d" % (lens_id, len(c), len(by_lens.get(lens_id, ())), n_det))
    print()
    print("wrote %d candidate(s) to %s" % (len(found), os.path.relpath(OUT, ROOT)))
    if misaligned:
        print()
        print("RECEIPT ALIGNMENT FAILURE on %d candidate(s) -- the excerpt does not contain"
              % len(misaligned))
        print("the cue that fired. Do not review these; the bug is here, not in the cue list.")
        for lens_id, det, cue in misaligned[:8]:
            print("   %-26s %-28s %r" % (lens_id, det, cue))
        return 1
    print("every candidate's excerpt contains the cue that fired")
    print()
    print("NOTHING IS PROMOTED AUTOMATICALLY. A harvester that promoted its own hits would")
    print("write gold its own cue list is guaranteed to match, which is the circularity this")
    print("exists to escape. Read them, keep the real instances, discard the rest.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
