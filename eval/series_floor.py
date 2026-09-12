#!/usr/bin/env python3
"""Does a ratchet_series result survive the way it was asked for?

WHY THIS EXISTS
---------------
`eval/lens_floor.py` measures a text lens's floor by perturbing the text. That does not
transfer to a counting detector: `ratchet_series` never reads prose, so sentence order and
whitespace are meaningless to it. Its nuisance factors are entirely different and were named in
the detector's README before they were measured:

  docket matching   is this document about the same measure, or does it merely mention it?
                    The API term search is full text, and the title filter that narrows it is
                    crude. A measure titled inconsistently across its series reads as fewer
                    movements than it had.
  coverage gaps     did the search see every document in the series? An early run ordered
                    oldest with a page cap, fetched 1996-1999 documents for a measure whose
                    extensions were all 2021-2025, and reported zero movement in either
                    direction -- a coverage gap presented as an absence of a ratchet.

So this harness perturbs the QUERY rather than the text: word subsets, singular and plural,
different page caps, different date floors. Same measure, differently asked. A result that
changes sign or loses significance when the question is rephrased is a property of the question.

WHAT PASSING MEANS
------------------
The sign of the asymmetry holds across every variant, and the variant that finds the fewest
documents still clears the resolvability bar. Anything less is reported, not hidden.

    python eval/series_floor.py --measure "telemedicine flexibilities"
    python eval/series_floor.py --measure "..." --json

Costs one API call per variant, serial, two seconds apart.
"""
from __future__ import annotations

import argparse
import itertools
import json
import os
import statistics as st
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, ROOT)

import ratchet_series as RS  # noqa: E402

DELAY = 2.0


def term_variants(measure):
    """Ways of naming the same measure. Each should find the same series."""
    words = measure.split()
    out = [measure]
    if len(words) > 1:
        out.append(" ".join(words[:-1]))          # drop the last word
        out.append(" ".join(words[1:]))           # drop the first word
        out.append(" ".join(reversed(words)))     # order should not matter to a search
    # crude singular/plural, since a series can be titled either way
    if measure.endswith("s"):
        out.append(measure[:-1])
    else:
        out.append(measure + "s")
    seen, uniq = set(), []
    for t in out:
        t = t.strip()
        if t and t.lower() not in seen:
            seen.add(t.lower())
            uniq.append(t)
    return uniq


def window_variants():
    """Page caps and date floors. Coverage should not depend on either."""
    return [(100, None), (40, None), (200, None), (100, "2015")]


def run(measure, spec, per_page, since):
    docs = RS.fetch_series(measure, since, per_page)
    time.sleep(DELAY)
    return RS.analyse(docs, spec, measure)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--measure", required=True)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    spec = RS.load_spec()
    rows = []

    for term in term_variants(args.measure):
        try:
            r = run(term, spec, 100, None)
        except Exception as exc:
            rows.append({"kind": "term", "variant": term, "error": str(exc)[:80]})
            continue
        rows.append({"kind": "term", "variant": term, "documents": r["documents"],
                     "forward": r["forward"], "back": r["back"],
                     "asymmetry": r["asymmetry"], "p": r["p_value"],
                     "resolvable": r["resolvable"]})

    for per_page, since in window_variants():
        label = "per_page=%d%s" % (per_page, (" since=%s" % since) if since else "")
        try:
            r = run(args.measure, spec, per_page, since)
        except Exception as exc:
            rows.append({"kind": "window", "variant": label, "error": str(exc)[:80]})
            continue
        rows.append({"kind": "window", "variant": label, "documents": r["documents"],
                     "forward": r["forward"], "back": r["back"],
                     "asymmetry": r["asymmetry"], "p": r["p_value"],
                     "resolvable": r["resolvable"]})

    good = [r for r in rows if "asymmetry" in r and r["asymmetry"] is not None]
    signs = {1 if r["asymmetry"] > 0 else (-1 if r["asymmetry"] < 0 else 0) for r in good}
    asyms = [r["asymmetry"] for r in good]
    verdict = {
        "measure": args.measure,
        "variants_run": len(rows),
        "variants_with_movement": len(good),
        "sign_stable": len(signs) <= 1,
        "asymmetry_spread": (round(max(asyms) - min(asyms), 3) if asyms else None),
        "asymmetry_median": (round(st.median(asyms), 3) if asyms else None),
        "all_resolvable": all(r.get("resolvable") for r in good) if good else False,
        "rows": rows,
    }

    if args.json:
        print(json.dumps(verdict, indent=2))
        return 0 if verdict["sign_stable"] else 1

    print("SERIES FLOOR -- same measure, differently asked")
    print("measure: %s" % args.measure)
    print()
    print("%-8s %-34s %5s %4s %4s %8s %8s %s"
          % ("kind", "variant", "docs", "fwd", "back", "asym", "p", "resolvable"))
    for r in rows:
        if "error" in r:
            print("%-8s %-34s  ERROR %s" % (r["kind"], r["variant"][:34], r["error"]))
            continue
        a = "-" if r["asymmetry"] is None else "%+.3f" % r["asymmetry"]
        print("%-8s %-34s %5d %4d %4d %8s %8s %s"
              % (r["kind"], r["variant"][:34], r["documents"], r["forward"], r["back"],
                 a, r["p"], "yes" if r["resolvable"] else "no"))
    print()
    print("sign stable across variants: %s" % ("YES" if verdict["sign_stable"] else "NO"))
    print("asymmetry spread:            %s" % verdict["asymmetry_spread"])
    print("every variant resolvable:    %s" % ("yes" if verdict["all_resolvable"] else "no"))
    print()
    if verdict["sign_stable"] and verdict["all_resolvable"]:
        print("The result does not depend on how the measure was named or how far the search")
        print("reached. That is what this harness can establish, and it is the last of the")
        print("three nuisance factors the detector's README named.")
    elif verdict["sign_stable"] and verdict["asymmetry_spread"] == 0.0:
        thin = [r for r in good if not r.get("resolvable")]
        print("Sign and magnitude are invariant -- every variant that locates the series")
        print("returns the same asymmetry. What is NOT invariant is significance: %d variant(s)"
              % len(thin))
        print("find too few movements to clear the bar:")
        for r in thin:
            print("  %-34s %d directional movements, p = %s"
                  % (r["variant"][:34], r["forward"] + r["back"], r["p"]))
        print()
        print("That is a COVERAGE gap, not an unstable result: a truncated search sees fewer")
        print("movements than the series contains, and fewer movements cannot reach the same p.")
        print("Publish the number with the search depth it requires, not without it.")
    else:
        print("The result is sensitive to how it was asked. Report the spread with the number,")
        print("or narrow the claim to the variant set that holds. Do not publish the best one.")
    return 0 if verdict["sign_stable"] else 1


if __name__ == "__main__":
    sys.exit(main())
