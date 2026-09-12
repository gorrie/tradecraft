#!/usr/bin/env python3
"""Does each lens detect its own gold examples?

WHY THIS EXISTS
---------------
Every detection in every taxonomy may carry `gold` entries — the text the lens author wrote
down as an instance of that marker. They are the closest thing this repository has to a
per-lens positive corpus, and nothing has ever checked them.

The check is not decorative. A lens that does not fire on its own gold has one of two problems,
and they need different fixes:

  cue gap        the gold example is a real instance and the cue list does not cover the way it
                 is worded. The lens under-detects, and the fix is a cue.
  gold drift     the cue list moved and the gold example no longer illustrates it, or never did.
                 The fix is the example.

Either way it is a defect, and either way the gold is the seed of the positive corpus that
`eval/lens_floor.py` needs — a floor cannot be measured over documents that all score zero, and
right now the only corpus in the repo fires on 19 of 600 lens-document cells.

This runs on the deterministic `cues` backend, so it is free, offline, and CI-safe. A gold
example that the cue backend misses may still be caught by the LLM read; that is reported as
`cues-miss` rather than as a failure, because the two backends are different instruments and
conflating them is how this repo previously deleted good cues on the strength of a corpus that
measured something else.

    python eval/gold_check.py                 # every lens
    python eval/gold_check.py --lens legibility
    python eval/gold_check.py --strict        # exit 1 if any lens misses its own gold
"""
from __future__ import annotations

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from tradecraft.detect import detect_cues   # noqa: E402
from tradecraft.loader import load_lenses    # noqa: E402


# Lenses that read a GRAPH, not prose. tradecraft/structural.py emits their detection ids
# (crosses-gov-industry, five-plus-moves, funds-three-plus, high-betweenness ...) from career
# and funding edges, so their gold examples are trajectories -- "Ben Nimmo: DFRLab -> Graphika
# -> Meta -> OpenAI [4 moves]" -- and not sentences containing cue phrases.
#
# Running the cue backend against them and calling the result a miss would be exactly the error
# this repo keeps finding elsewhere: the wrong instrument applied confidently. The first run of
# this script did it and reported 0 of 9 for revolving_door as a defect.
#
# That "reads" field now exists. 2026-09-01: this was a hardcoded set here, another in
# tools/harvest_gold.py, and a third in tools/export_web.py -- and the third silently decided
# which engine features got parity-tested, letting a real detect.py/engine.js divergence pass
# the gate. Ask the lens.
#     if tax.is_structural: ...   -- see the loop below


def gold_entries(taxonomy):
    """Yield (marker_id, detection_id, text, source) for every gold example in a lens."""
    for marker in taxonomy.markers:
        for det in marker.detections:
            for g in (getattr(det, "gold", None) or []):
                text = g.get("text") if isinstance(g, dict) else str(g)
                src = g.get("source", "") if isinstance(g, dict) else ""
                if text:
                    yield marker.id, det.id, text, src


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--lens", action="append")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--show-misses", action="store_true", default=True)
    args = ap.parse_args(argv)

    lenses = load_lenses(os.path.join(ROOT, "detectors"))
    if args.lens:
        lenses = {k: v for k, v in lenses.items() if k in set(args.lens)}

    total_gold = 0
    total_hit = 0
    misses = []
    no_gold = []
    structural = []

    print("GOLD CHECK — does each lens detect the examples its own author wrote down?")
    print("cues backend only; an LLM read may catch more, which is why a miss is a defect")
    print("report and not a verdict.")
    print()
    print("%-26s %6s %6s %s" % ("lens", "gold", "hit", "detections covered"))

    for lens_id, tax in sorted(lenses.items()):
        entries = list(gold_entries(tax))
        n_dets = sum(len(m.detections) for m in tax.markers)
        if tax.is_structural:
            structural.append((lens_id, len(entries)))
            print("%-26s %6d %6s  STRUCTURAL -- reads a graph, not prose; cue check N/A"
                  % (lens_id, len(entries), "n/a"))
            continue
        if not entries:
            no_gold.append((lens_id, n_dets))
            print("%-26s %6s %6s  NO GOLD EXAMPLES (%d detections)"
                  % (lens_id, "-", "-", n_dets))
            continue
        hit = 0
        covered = set()
        for marker_id, det_id, text, src in entries:
            total_gold += 1
            hits = detect_cues(text, tax)
            got = {h.detection_id for h in hits}
            if det_id in got:
                hit += 1
                total_hit += 1
                covered.add(det_id)
            else:
                misses.append((lens_id, det_id, text, src, sorted(got)))
        print("%-26s %6d %6d  %d of %d" % (lens_id, len(entries), hit, len(covered), n_dets))

    print()
    print("TOTAL: %d of %d gold examples detected by their own detection id" % (total_hit, total_gold))
    if structural:
        print("(excludes %d structural lens(es) -- %s -- whose gold is graph data, not prose)"
              % (len(structural), ", ".join(k for k, _ in structural)))

    if no_gold:
        print()
        print("%d lens(es) ship NO gold examples at all:" % len(no_gold))
        for lens_id, n in no_gold:
            print("  %-26s %d detections, 0 examples" % (lens_id, n))
        print("These cannot be checked, cannot seed a positive corpus, and cannot have a floor.")

    if misses and args.show_misses:
        print()
        print("MISSES — gold the lens does not detect under its own detection id:")
        for lens_id, det_id, text, src, got in misses[:20]:
            print("  %s / %s" % (lens_id, det_id))
            print("      %s" % (" ".join(text.split())[:96]))
            print("      matched instead: %s" % (", ".join(got) if got else "nothing"))
        if len(misses) > 20:
            print("  ... and %d more" % (len(misses) - 20))

    if args.strict and (misses or no_gold):
        print()
        print("STRICT: %d miss(es), %d lens(es) without gold." % (len(misses), len(no_gold)))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
