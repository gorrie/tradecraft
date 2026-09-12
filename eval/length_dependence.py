#!/usr/bin/env python3
"""Does a lens score a document for what it says, or for how long it is?

WHY THIS EXISTS
---------------
`eval/lens_floor.py` reported that `institutional_permeation` moves up to 6.7 index points
under DUPLICATION -- the same text twice -- against 0.0 for reordering, re-chunking and
whitespace. Duplication is the one perturbation where the answer is not arguable: a document
concatenated with itself has exactly the same RATE of method-marking, so any measure that
claims to be a rate must return the same number.

Tracing it produced a defect that is worse than duplication sensitivity, and it is the join
between two individually reasonable decisions:

  * `detect_cues` fires ONCE PER DETECTION by design -- "one firing per detection is enough;
    move to the next detection". So the hit count is bounded by how many distinct detections
    matched, and says nothing about how often the method appears.

  * `grade_document_for_lens` computes `density = weighted_hits / (tokens/1000)`, capped, and
    the grader's own docstring calls it "weighted hits per 1k tokens".

Together, with one hit per detection, density is not a rate. It is `detections_that_fired /
document_length`, which is dominated by the denominator. Measured on the corpus:

    Fabian tract, 102 words, 1 hit  ->  density 0.8987   (index 22.56)
    Federal Register doc, 28,677 words, 1 hit  ->  density 0.0029   (index 8.60)

`w_density` is 0.15 for that lens, so roughly 13 of the tract's 22 index points come from its
being short. The highest-scoring document in the corpus scores high substantially because it
is brief. For an instrument meant to grade institutions across document sets of wildly
different lengths, that is a systematic bias in favour of whoever writes shorter documents.

WHAT THIS MEASURES
------------------
Two things no other script here measures:

  duplication invariance -- index of `doc` against index of `doc+doc`. A rate must not move.
      This is a NULL: any movement is a defect, not a finding.

  length correlation -- Spearman correlation between document length and index, across every
      document a lens fires on. A lens measuring rhetoric should show no systematic relation;
      a strong negative one means the score is reporting brevity.

Neither is fixed here. The repair is a scoring change -- either the matcher counts occurrences
so density becomes a real rate, or density stops dividing by total length -- and it moves every
grade the engine has ever produced. That is an author's decision, and this is the instrument
that makes it a measured one.

    python eval/length_dependence.py
    python eval/length_dependence.py --lens institutional_permeation
    python eval/length_dependence.py --check      # exit 1 if any lens fails duplication
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from tradecraft.corpus_docs import documents                # noqa: E402
from tradecraft.detect import detect                        # noqa: E402
from tradecraft.grader import grade_document_for_lens        # noqa: E402
from tradecraft.loader import load_lenses                    # noqa: E402

OUT = os.path.join(HERE, "length-dependence.json")

# A rate is a rate. Anything above this under duplication is a defect in the measure, and the
# threshold is deliberately tight rather than set to whatever the current code produces --
# picking it to fit the present behaviour is how a gate becomes a rubber stamp.
DUP_TOLERANCE = 0.05


def graded(text, taxonomy):
    hits = detect(text, taxonomy, backend="cues")
    return grade_document_for_lens(taxonomy, hits, len(text.split()))


def spearman(xs, ys):
    """Rank correlation, ties averaged. Small n here, so no scipy and no approximations."""
    n = len(xs)
    if n < 4:
        return None

    def ranks(vals):
        order = sorted(range(n), key=lambda i: vals[i])
        out = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and vals[order[j + 1]] == vals[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                out[order[k]] = avg
            i = j + 1
        return out

    rx, ry = ranks(xs), ranks(ys)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((rx[i] - mx) * (ry[i] - my) for i in range(n))
    dx = sum((rx[i] - mx) ** 2 for i in range(n)) ** 0.5
    dy = sum((ry[i] - my) ** 2 for i in range(n)) ** 0.5
    if dx == 0 or dy == 0:
        return None
    return num / (dx * dy)


def measure(taxonomy, docs):
    firing = []
    worst = None
    dup_deltas = []
    for doc in docs:
        base = graded(doc.text, taxonomy)
        if base.index <= 0:
            continue
        dup = graded(doc.text.strip() + "\n\n" + doc.text.strip(), taxonomy)
        delta = abs(dup.index - base.index)
        dup_deltas.append(delta)
        firing.append((len(doc.text.split()), base.index))
        if worst is None or delta > worst["delta"]:
            worst = {"delta": round(delta, 2), "document": doc.name,
                     "words": len(doc.text.split()),
                     "base": {"index": base.index, "breadth": base.breadth,
                              "intensity": base.intensity, "density": base.density,
                              "hits": len(base.receipts)},
                     "duplicated": {"index": dup.index, "breadth": dup.breadth,
                                    "intensity": dup.intensity, "density": dup.density,
                                    "hits": len(dup.receipts)}}
    if not firing:
        return None
    lengths = [f[0] for f in firing]
    indices = [f[1] for f in firing]
    return {"documents_firing": len(firing),
            "dup_max": round(max(dup_deltas), 2),
            "dup_median": round(sorted(dup_deltas)[len(dup_deltas) // 2], 2),
            "length_index_spearman": (None if spearman(lengths, indices) is None
                                      else round(spearman(lengths, indices), 3)),
            "shortest_words": min(lengths), "longest_words": max(lengths),
            "worst_duplication": worst}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--lens", action="append", default=None)
    ap.add_argument("--docs", type=int, default=None, help="cap the corpus (default: all)")
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if any lens moves under duplication")
    args = ap.parse_args(argv)

    lenses = load_lenses(os.path.join(ROOT, "detectors"))
    if args.lens:
        lenses = {k: v for k, v in lenses.items() if k in set(args.lens)}
        if not lenses:
            print("no such lens")
            return 1

    docs = documents(limit=args.docs, min_words=40)
    print("LENGTH DEPENDENCE -- is the score about the text or about its size?")
    print("%d corpus document(s); duplication tolerance %.2f index points"
          % (len(docs), DUP_TOLERANCE))
    print()
    print("%-28s %5s %8s %8s %9s" % ("lens", "docs", "dup med", "dup max", "len corr"))

    results = {}
    failing = []
    for lens_id, taxonomy in sorted(lenses.items()):
        got = measure(taxonomy, docs)
        if got is None:
            print("%-28s %5s %8s %8s %9s   (never fires)" % (lens_id, "-", "-", "-", "-"))
            continue
        results[lens_id] = got
        corr = got["length_index_spearman"]
        print("%-28s %5d %8.2f %8.2f %9s"
              % (lens_id, got["documents_firing"], got["dup_median"], got["dup_max"],
                 "n/a" if corr is None else "%+.3f" % corr))
        if got["dup_max"] > DUP_TOLERANCE:
            failing.append((lens_id, got))

    if failing:
        print()
        print("DUPLICATION IS A NULL AND %d LENS(ES) FAIL IT." % len(failing))
        for lens_id, got in failing:
            w = got["worst_duplication"]
            print()
            print("  %s -- worst case %s (%d words), %.2f index points"
                  % (lens_id, w["document"][:52], w["words"], w["delta"]))
            print("      %-12s %8s %8s %8s %6s" % ("", "index", "breadth", "intens", "dens"))
            for label in ("base", "duplicated"):
                c = w[label]
                print("      %-12s %8.2f %8.4f %8.4f %6.4f"
                      % (label, c["index"], c["breadth"], c["intensity"], c["density"]))
            print("      hits: %d -> %d" % (w["base"]["hits"], w["duplicated"]["hits"]))
            moved = [name for name in ("breadth", "intensity", "density")
                     if abs(w["base"][name] - w["duplicated"][name]) > 1e-6]
            print("      component(s) that moved: %s" % (", ".join(moved) or "none"))
            if moved == ["density"] and w["base"]["hits"] == w["duplicated"]["hits"]:
                print("      DIAGNOSIS: the hit count did not change while the token count")
                print("      doubled, so this 'per 1k tokens' term is measuring 1/length.")
                print("      Cause is the join of two choices, not either one: detect_cues")
                print("      fires once per detection, and the grader divides by total")
                print("      tokens. Fixing it moves every grade -- author's call.")

    with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"tolerance": DUP_TOLERANCE, "corpus_documents": len(docs),
                   "lenses": results}, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print()
    print("wrote %s" % os.path.relpath(OUT, ROOT))

    if args.check and failing:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
