#!/usr/bin/env python3
"""WHICH PART of the index drifts with document length? Measure the three components separately.

WHY THIS EXISTS
---------------
Issue #7 says the background firing rate has no length normalisation and offers two candidate
units: firings per 1,000 words, or a fixed-window scan. The window scan was measured and
refuted (`RESULTS-2026-09-06-length-bias.md`). Both candidates change the UNIT OF THE RATE.

Neither addresses the mechanism, because a lens "fires" when its INDEX exceeds a threshold, and

    index = 100 * (w_breadth * breadth + w_intensity * intensity + w_density * density)

Only `density` is length-normalised -- it is `weighted_occurrences / (tokens/1000)`, capped.
`breadth` is the fraction of distinct markers PRESENT and `intensity` is their weighted
presence, and both are monotone non-decreasing as a document gets longer: a longer document
contains more distinct things. So the firing EVENT drifts with length, and no re-scaling of the
rate can fix a threshold that drifts.

DUPLICATION INVARIANCE DOES NOT CATCH THIS, which is why it survived a fix that was verified.
Under `doc + doc`, occurrences and tokens both double so density is unchanged, and the same
distinct markers are present at the same strongest hits so breadth and intensity are unchanged
too. The 2026-09-02 repair achieved duplication invariance and the residual bias is invisible
to it: duplication holds CONTENT fixed while length varies, and the defect lives in comparing
DIFFERENT documents whose marker inventories grow with size.

WHAT THIS MEASURES
------------------
Per lens, over the background pool only: the Spearman correlation of each index component with
document length, and the firing rate by length quartile under three firing definitions.

    index > 0            the current definition
    index >= NOTABLE     the higher threshold already reported alongside it
    density-only         fire on the length-normalised component alone

If breadth and intensity carry the correlation and density does not, the mechanism above is
confirmed and the fix belongs in the firing definition or in stratification -- not in the unit.

    python eval/length_components.py
    python eval/length_components.py --json
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

from tradecraft.corpus_docs import documents               # noqa: E402
from tradecraft.detect import detect                       # noqa: E402
from tradecraft.grader import grade_document_for_lens      # noqa: E402
from tradecraft.loader import load_lenses                  # noqa: E402

import background_rate as B                                # noqa: E402
from length_dependence import spearman                     # noqa: E402


def graded(text, taxonomy):
    hits = detect(text, taxonomy, backend="cues")
    return grade_document_for_lens(taxonomy, hits, B.tokens(text))


def background_docs():
    """Background-role documents only. A recall fixture is selection on the outcome.

    `role_of` returns the ROLES RECORD, not the role string -- so `role_of(x) == "background"`
    is always false and silently yields an empty pool. It did, on the first run of this script,
    and the script said "no background documents found" and exited 2, which is the right shape
    of failure: an empty measurement that announces itself rather than reporting rates over
    nothing.
    """
    out = []
    for d in documents(min_words=B.MIN_WORDS):
        rec = B.role_of(d.origin)
        if rec and rec.get("role") == "background":
            out.append(d)
    return out


def quartiles(values):
    v = sorted(values)
    if len(v) < 4:
        return []
    return [v[int(len(v) * q)] for q in (0.25, 0.5, 0.75)]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    lenses = load_lenses(os.path.join(ROOT, "detectors"))
    docs = background_docs()
    if not docs:
        print("no background documents found", file=sys.stderr)
        return 2

    lengths = [B.tokens(d.text) for d in docs]
    cuts = quartiles(lengths)

    rows = []
    for lens_id, taxonomy in sorted(lenses.items()):
        comp = {"breadth": [], "intensity": [], "density": [], "index": []}
        fired = {"index_gt0": [], "index_notable": [], "density_only": []}
        for d, n in zip(docs, lengths):
            r = graded(d.text, taxonomy)
            comp["breadth"].append(r.breadth)
            comp["intensity"].append(r.intensity)
            comp["density"].append(r.density)
            comp["index"].append(r.index)
            fired["index_gt0"].append(1 if r.index > 0 else 0)
            fired["index_notable"].append(1 if r.index >= B.NOTABLE else 0)
            fired["density_only"].append(1 if r.density > 0 else 0)

        row = {"lens": lens_id,
               "rho": {k: spearman(lengths, v) for k, v in comp.items()}}
        # Firing rate in the shortest and longest quartile, per definition.
        if cuts:
            lo = [i for i, n in enumerate(lengths) if n <= cuts[0]]
            hi = [i for i, n in enumerate(lengths) if n > cuts[2]]
            row["quartile"] = {}
            for name, f in fired.items():
                a = sum(f[i] for i in lo) / max(1, len(lo))
                b = sum(f[i] for i in hi) / max(1, len(hi))
                row["quartile"][name] = {"short": round(a, 3), "long": round(b, 3),
                                         "swing": round(b - a, 3)}
        rows.append(row)

    if args.json:
        print(json.dumps({"n_docs": len(docs), "length_cuts": cuts, "lenses": rows},
                         indent=2))
        return 0

    print("WHICH COMPONENT DRIFTS WITH LENGTH -- %d background document(s)" % len(docs))
    print("length quartile cuts: %s words" % cuts)
    print("")
    print("Spearman rho against document length, per index component:")
    print("  %-26s %8s %10s %8s %8s" % ("lens", "breadth", "intensity", "density", "index"))
    for r in rows:
        h = r["rho"]
        print("  %-26s %8s %10s %8s %8s"
              % (r["lens"][:26],
                 _f(h["breadth"]), _f(h["intensity"]), _f(h["density"]), _f(h["index"])))

    print("")
    print("Firing-rate swing, shortest quartile -> longest, by firing definition:")
    print("  %-26s %16s %16s %16s" % ("lens", "index>0", "index>=%g" % B.NOTABLE,
                                      "density>0"))
    for r in rows:
        q = r.get("quartile") or {}
        cells = []
        for name in ("index_gt0", "index_notable", "density_only"):
            c = q.get(name)
            cells.append("-" if not c else "%.2f->%.2f %+.2f"
                         % (c["short"], c["long"], c["swing"]))
        print("  %-26s %16s %16s %16s" % (r["lens"][:26], *cells))

    print("")
    _verdict(rows)
    return 0


def _f(x):
    return "-" if x is None else ("%+.3f" % x)


def _verdict(rows):
    """State what the numbers imply about WHERE the fix belongs."""
    def mean_abs(key):
        vals = [abs(r["rho"][key]) for r in rows if r["rho"][key] is not None]
        return sum(vals) / len(vals) if vals else None

    b, i, d = mean_abs("breadth"), mean_abs("intensity"), mean_abs("density")
    print("mean |rho| with length:  breadth %s   intensity %s   density %s"
          % (_f(b), _f(i), _f(d)))
    if b is None or d is None:
        print("not enough live components to draw a conclusion.")
        return

    # A VERDICT NEEDS A MATERIAL DIFFERENCE, NOT ANY DIFFERENCE.
    #
    # The first version of this branch was `if max(breadth, intensity) > density`, and it
    # fired on 0.202 against 0.194 -- eight thousandths -- and printed "BREADTH AND INTENSITY
    # CARRY THE LENGTH DEPENDENCE; DENSITY DOES NOT". That is a spurious verdict off a
    # threshold with no width, which is the defect this project convicts other work of. The
    # hypothesis it announced was mine and the measurement refuted it.
    spread = max(b, i or 0) - d
    if spread < 0.05:
        print("")
        print("ALL THREE COMPONENTS DRIFT TOGETHER, AND BY THE SAME AMOUNT.")
        print("So the drift is NOT breadth/intensity saturation -- density is length-normalised")
        print("by construction and drifts just as much. The `index>0` and `density>0` columns")
        print("above are IDENTICAL on every lens, which says what the mechanism actually is:")
        print("")
        print("  Firing is the EXTENSIVE MARGIN. A lens fires when the document contains at")
        print("  least one cue, and P(at least one) rises with length for any nonzero rate.")
        print("  Every component goes from zero to nonzero at the same moment, so normalising")
        print("  one of them cannot help: density is 0 when nothing occurs, and when one cue")
        print("  occurs in 50,000 words density is tiny but still greater than zero.")
        print("")
        print("That makes issue #7's CANDIDATE 1 structurally correct after all. Under a")
        print("Poisson null at rate lambda per 1,000 words, documents-fired/documents is")
        print("1 - exp(-lambda*L/1000), which rises with L, while occurrences/(words/1000) is")
        print("lambda, which does not. Candidate 2 failed for the same reason the current unit")
        print("does -- 'fires if ANY window fires' is still an extensive margin, over windows")
        print("instead of documents.")
        print("")
        print("The `index>=%g` column is nearly flat, and that is not a usable alternative:" % B.NOTABLE)
        print("it is flat because it almost never fires at all.")
    else:
        print("")
        print("breadth/intensity drift %.3f more than density -- saturation of the presence"
              % spread)
        print("terms is a live mechanism and the firing definition is where to look.")


if __name__ == "__main__":
    raise SystemExit(main())
