#!/usr/bin/env python3
"""Is an arm difference in firing rate real, or is it response LENGTH?

WHY THIS EXISTS
---------------
2026-09-03. Grading the bias study's model output produced the largest cross-instrument result
so far: `sourcing_asymmetry` fires on 0.332 of no-directive responses and 0.155 of directive
ones, about 2,000 documents per arm. That is a big effect with the counts to support it, and it
lines up with the study's own refusal finding from the other side.

It is also exactly the shape of a length artifact. This repository has already been bitten once:
before the density repair, `subculture_register`'s index correlated **-1.000** with document
length -- the score WAS the length. And a directive prompt plausibly changes how long a model
answers. So a rate difference between arms cannot be reported until it survives holding length
constant.

WHAT IT DOES
------------
Bins the pooled corpus by word count into equal-count strata, then compares each arm's firing
rate WITHIN each bin. If the difference is length, it collapses inside bins while the pooled
number stays. If it survives every bin, length is not the explanation.

Also prints each arm's length distribution, because the size of the confound is itself worth
seeing -- a difference that survives stratification when the arms barely differ in length was
never at much risk, and one that survives when they differ wildly is a stronger result.

    python eval/arm_rate_control.py --docs ~/corpora/model-output.jsonl \\
        --lens sourcing_asymmetry --lens institutional_permeation
"""
from __future__ import annotations

import argparse
import io
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from tradecraft.detect import detect                       # noqa: E402
from tradecraft.grader import grade_document_for_lens       # noqa: E402
from tradecraft.loader import load_lenses                   # noqa: E402

#: Equal-count length strata. Four is enough to show a collapse and keeps per-cell counts
#: usable at a few thousand documents; more bins would trade the thing being measured for
#: resolution nobody asked for.
BINS = 4


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d
    return (max(0.0, c - h), min(1.0, c + h))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--docs", required=True, help="JSONL from corpus/to_bias_study.py")
    ap.add_argument("--lens", action="append", default=[],
                    help="lens id; repeatable. Default: every text lens")
    ap.add_argument("--arm-field", default="condition")
    ap.add_argument("--arms", default="A,B", help="the two arms to compare")
    ap.add_argument("--bins", type=int, default=BINS)
    args = ap.parse_args(argv)

    arm_a, arm_b = [a.strip() for a in args.arms.split(",")][:2]
    docs = []
    for line in io.open(args.docs, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        if rec.get(args.arm_field) in (arm_a, arm_b):
            rec["_words"] = len((rec.get("text") or "").split())
            docs.append(rec)
    if not docs:
        print("no documents in arms %r / %r" % (arm_a, arm_b))
        return 1

    lenses = load_lenses(os.path.join(ROOT, "detectors"))
    if args.lens:
        lenses = {k: v for k, v in lenses.items() if k in set(args.lens)}
    if not lenses:
        print("no lenses matched")
        return 1

    a_words = sorted(d["_words"] for d in docs if d[args.arm_field] == arm_a)
    b_words = sorted(d["_words"] for d in docs if d[args.arm_field] == arm_b)

    def med(xs):
        return xs[len(xs) // 2] if xs else 0

    print("ARM LENGTH CONTROL -- %d document(s), arms %r (n=%d) and %r (n=%d)"
          % (len(docs), arm_a, len(a_words), arm_b, len(b_words)))
    print("  median words: %s=%d, %s=%d   (the size of the confound)"
          % (arm_a, med(a_words), arm_b, med(b_words)))

    # Equal-count strata over the POOLED corpus, so both arms are cut at the same boundaries.
    pooled = sorted(d["_words"] for d in docs)
    edges = [pooled[int(len(pooled) * i / args.bins)] for i in range(1, args.bins)]

    def stratum(words):
        for i, e in enumerate(edges):
            if words < e:
                return i
        return args.bins - 1

    for lens_id, tax in sorted(lenses.items()):
        fired = {}
        total = {}
        # PER-DETECTION counts alongside the per-lens ones. `index > 0` means "something in
        # this lens fired", which is the level the arm difference was reported at -- and it
        # hides whether the difference is the lens's CONCEPT moving or one phrase appearing
        # less often. That distinction is the whole claim: `sourcing_asymmetry`'s enumeration
        # ceiling means its best detections rest on very few cues, so a halving driven by a
        # single cue is a fact about that cue's wording, not about sourcing asymmetry.
        det_fired = {}
        for d in docs:
            arm = d[args.arm_field]
            key = (arm, stratum(d["_words"]))
            total[key] = total.get(key, 0) + 1
            try:
                hits = detect(d["text"], tax, backend="cues")
            except Exception:
                continue
            if grade_document_for_lens(tax, hits, max(1, d["_words"])).index > 0:
                fired[key] = fired.get(key, 0) + 1
            # Once per document per detection, not once per hit: a rate of documents, matching
            # the per-lens statistic above. Counting hits would let one verbose document set
            # a detection's rate.
            for det_id in {h.detection_id for h in hits}:
                det_fired[(det_id, arm)] = det_fired.get((det_id, arm), 0) + 1

        pa = sum(fired.get((arm_a, i), 0) for i in range(args.bins))
        na = sum(total.get((arm_a, i), 0) for i in range(args.bins))
        pb = sum(fired.get((arm_b, i), 0) for i in range(args.bins))
        nb = sum(total.get((arm_b, i), 0) for i in range(args.bins))
        print("")
        print("%s" % lens_id)
        print("  pooled:  %s %.3f (%d/%d)   %s %.3f (%d/%d)   ratio %s"
              % (arm_a, pa / na if na else 0, pa, na,
                 arm_b, pb / nb if nb else 0, pb, nb,
                 "%.2fx" % ((pb / nb) / (pa / na)) if na and nb and pa else "n/a"))
        print("  %-14s %18s %18s   %s" % ("stratum (words)", arm_a, arm_b, "survives?"))
        survived = 0
        judged = 0
        for i in range(args.bins):
            na_i, nb_i = total.get((arm_a, i), 0), total.get((arm_b, i), 0)
            if not na_i or not nb_i:
                continue
            ra = fired.get((arm_a, i), 0) / na_i
            rb = fired.get((arm_b, i), 0) / nb_i
            lo_a, hi_a = wilson(fired.get((arm_a, i), 0), na_i)
            lo_b, hi_b = wilson(fired.get((arm_b, i), 0), nb_i)
            # Same direction as pooled AND intervals that do not overlap.
            same_dir = (rb < ra) == ((pb / nb) < (pa / na)) if na and nb else False
            disjoint = hi_b < lo_a or hi_a < lo_b
            judged += 1
            survived += 1 if (same_dir and disjoint) else 0
            label = "yes" if (same_dir and disjoint) else ("direction only" if same_dir else "NO")
            lo = 0 if i == 0 else edges[i - 1]
            hi = edges[i] if i < len(edges) else max(pooled)
            print("  %-14s %6.3f (%4d/%4d) %6.3f (%4d/%4d)   %s"
                  % ("%d-%d" % (lo, hi), ra, fired.get((arm_a, i), 0), na_i,
                     rb, fired.get((arm_b, i), 0), nb_i, label))
        print("  -> survives length control in %d of %d judgeable stratum/strata" % (survived, judged))
        if judged and survived == judged:
            print("     The pooled difference is NOT explained by length.")
        elif survived == 0:
            print("     The pooled difference COLLAPSES inside every bin: it is length.")
        else:
            print("     Partial. Report the strata, not the pooled number.")

        # WHICH DETECTION MOVED. A lens-level rate answers "did anything fire"; this answers
        # "did the concept move, or did one phrase". Sorted by the size of the arm gap, so the
        # driver is the first row rather than something to hunt for.
        ids = sorted({k[0] for k in det_fired})
        if ids:
            rows = []
            for det_id in ids:
                fa = det_fired.get((det_id, arm_a), 0)
                fb = det_fired.get((det_id, arm_b), 0)
                ra = fa / na if na else 0.0
                rb = fb / nb if nb else 0.0
                rows.append((abs(ra - rb), det_id, fa, ra, fb, rb))
            rows.sort(reverse=True)
            print("  per detection (document rate within each arm, whole corpus):")
            print("    %-34s %16s %16s %8s" % ("detection", arm_a, arm_b, "gap"))
            for gap, det_id, fa, ra, fb, rb in rows:
                print("    %-34s %6.3f (%4d) %6.3f (%4d) %8.3f"
                      % (det_id[:34], ra, fa, rb, fb, ra - rb))
            top = rows[0]
            total_gap = sum(r[0] for r in rows) or 1.0
            share = top[0] / total_gap
            print("    -> largest single gap is %r at %.3f, %.0f%% of the summed gap"
                  % (top[1], top[0], 100 * share))
            if share >= 0.6:
                print("       ONE DETECTION DOMINATES. Report this as a finding about that")
                print("       detection's wording, not about the lens's concept, until a")
                print("       second detection moves the same way.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
