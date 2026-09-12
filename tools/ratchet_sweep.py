#!/usr/bin/env python3
"""Run ratchet_series across many measures and report the DISTRIBUTION of asymmetry.

WHY A SWEEP
-----------
One measure is an anecdote. Telemedicine flexibilities came back +1.000 with p = 0.0078, and
on its own that number cannot answer the question a reader will actually ask: is a one-way run
what this method finds everywhere, or does it discriminate?

The negative controls already run said it discriminates -- rescissions came back -1.000. But
four measures chosen by hand is still a hand-chosen four. A sweep over a list fixed in advance
produces a distribution, and a distribution is the only thing that makes a single +1.000
interpretable.

WHAT IT REPORTS
---------------
Per measure: forward, back, the asymmetry, the exact binomial p, whether it is resolvable, and
the ambiguity bound. Then across measures: how many resolve at all, the split between forward
and back among those that do, and the full spread.

If most measures come back resolvable and forward, that is a finding about administrative
process. If most come back unresolvable, that is a finding about this method's power at the
document counts a typical measure generates -- also worth having, and the honest outcome to
publish if it is what happens.

THE MEASURE LIST IS FIXED IN THIS FILE, on purpose. Choosing measures after seeing results is
how a sweep becomes a search for the number you wanted.

    python tools/ratchet_sweep.py                 # the fixed list
    python tools/ratchet_sweep.py --json
"""
from __future__ import annotations

import argparse
import json
import os
import statistics as st
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)

import ratchet_series as RS  # noqa: E402

DELAY = 2.0

# Fixed before any of them was run. Chosen as surfaces the series is about -- surveillance,
# identity, financial controls, emergency powers, content and speech -- plus deliberate
# controls at the end where a wind-down is known to have occurred.
MEASURES = [
    "telemedicine flexibilities",
    "geographic targeting order",
    "beneficial ownership information reporting",
    "entity list addition",
    "temporary protected status designation",
    "public health emergency declaration",
    "suspicious activity report requirement",
    "know your customer requirement",
    "advance passenger information",
    "biometric entry exit",
    "continued dumping duty",
    "conservation and landscape health",
    "brominated vegetable oil",
]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--per-page", type=int, default=100)
    args = ap.parse_args(argv)

    spec = RS.load_spec()
    rows = []
    for measure in MEASURES:
        try:
            docs = RS.fetch_series(measure, None, args.per_page)
        except Exception as exc:
            rows.append({"measure": measure, "error": str(exc)[:70]})
            print("  %-42s FETCH FAILED %s" % (measure[:42], str(exc)[:40]))
            time.sleep(DELAY)
            continue
        time.sleep(DELAY)
        r = RS.analyse(docs, spec, measure)
        b = r["ambiguity_bound"]
        rows.append({
            "measure": measure, "documents": r["documents"],
            "forward": r["forward"], "back": r["back"], "neither": r["neither"],
            "asymmetry": r["asymmetry"], "p": r["p_value"],
            "resolvable": r["resolvable"],
            "bound_forward": b["all_ambiguous_forward"], "bound_back": b["all_ambiguous_back"],
        })
        print("  %-42s %3d docs  %2df %2db  %-7s p=%-7s %s"
              % (measure[:42], r["documents"], r["forward"], r["back"],
                 ("-" if r["asymmetry"] is None else "%+.3f" % r["asymmetry"]),
                 r["p_value"], "RESOLVABLE" if r["resolvable"] else ""))

    good = [r for r in rows if r.get("resolvable")]
    moved = [r for r in rows if r.get("asymmetry") is not None]
    fwd = [r for r in good if r["asymmetry"] > 0]
    back = [r for r in good if r["asymmetry"] < 0]

    summary = {
        "measures": len(MEASURES),
        "with_any_directional_movement": len(moved),
        "resolvable": len(good),
        "resolvable_forward": len(fwd),
        "resolvable_back": len(back),
        "asymmetry_median_resolvable": (round(st.median([r["asymmetry"] for r in good]), 3)
                                        if good else None),
        "rows": rows,
    }

    if args.json:
        print(json.dumps(summary, indent=2))
        return 0

    print()
    print("ACROSS %d MEASURES" % len(MEASURES))
    print("  with any directional movement : %d" % summary["with_any_directional_movement"])
    print("  resolvable (>=5 moves, p<0.05): %d" % summary["resolvable"])
    print("    of those, forward           : %d" % summary["resolvable_forward"])
    print("    of those, back              : %d" % summary["resolvable_back"])
    print()
    if not good:
        print("NOTHING RESOLVED. At the document counts these measures generate, this method")
        print("cannot distinguish a one-way run from chance. That is a finding about the")
        print("method's power, and it is the honest thing to report when it is what happens.")
    elif len(back) == 0 and len(fwd) > 1:
        print("Every resolvable measure moved FORWARD. Before reading that as a ratchet, note")
        print("that the fixed list includes two measures selected as known wind-downs, and")
        print("check whether they resolved -- if they did not, the sweep has not been tested")
        print("against its own control and the result is one-sided by construction.")
    else:
        print("The method discriminates: resolvable measures fall on both sides.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
