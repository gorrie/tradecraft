#!/usr/bin/env python3
"""W4.1 — one record shape for every resolution object this project measures.

WHY
---
Four instruments measure "how small a difference can this thing see", and all four emit a
different shape:

    eval/lens-floors.json        index MDE per lens, from perturbing documents
    eval/graph-floors.json       edge-perturbation invariance, per subject
    eval/background-rates.json   firing rate vs a measured background, per lens
    scripts/power.py             the bias study's detection limits, per null

Consumers have to know all four: the observatory digest, `tools/export_web.py`,
`leaderboard/score.py`, and the paper's floor table. Every one of them re-implements "what is
this lens's resolution?" against whichever file it happens to read, which is how a number ends
up on a page without the ruler that qualifies it.

THE CONTRACT (the plan's section 2a)

    {"claim", "instrument", "state", "statistic", "null",
     "n", "threshold_p95", "mde", "measured", "recomputable", "source"}

`recomputable` is the one that decides what may be published: true only when a reader can
rebuild the corpus behind the number. A floor measured over material only we hold is internal
calibration, and a public surface prints an MDE only when this is true.

WHAT THIS IS NOT
----------------
Not a new measurement. It reads what the emitters already wrote and normalises it, so there is
exactly one place that knows each file's private shape. A number with no record here does not
publish -- and `--check` is what makes that enforceable rather than aspirational.

    python eval/floors_contract.py              # every record, grouped
    python eval/floors_contract.py --json       # the normalised records
    python eval/floors_contract.py --check      # every lens has at least one record
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

from tradecraft.loader import load_lenses  # noqa: E402

LENS_FLOORS = os.path.join(HERE, "lens-floors.json")
GRAPH_FLOORS = os.path.join(HERE, "graph-floors.json")
BACKGROUND = os.path.join(HERE, "background-rates.json")
OUT = os.path.join(HERE, "floors.json")

FIELDS = ("claim", "instrument", "state", "statistic", "null", "n",
          "threshold_p95", "mde", "measured", "recomputable", "source")


def _load(path):
    if not os.path.exists(path):
        return None
    try:
        return json.load(io.open(path, encoding="utf-8"))
    except ValueError:
        return None


def from_lens_floors():
    """Index MDEs. `recomputable` is FALSE: the floor is measured over corpus/, and 95 of the
    background documents are vendored news text a reader cannot rebuild (see
    eval/background_rate.py ROLES). Marking these true would publish an MDE nobody can check."""
    blob = _load(LENS_FLOORS)
    if not blob:
        return []
    out = []
    for lens_id, rec in sorted(blob.get("lenses", {}).items()):
        out.append({
            "claim": "%s index difference is real" % lens_id,
            "instrument": "lens",
            "state": "index",
            "statistic": "index-points",
            "null": "reorder",
            "n": rec.get("n_docs"),
            "threshold_p95": rec.get("threshold_p95"),
            "mde": rec.get("mde"),
            "measured": blob.get("measured"),
            "recomputable": False,
            "source": "eval/lens_floor.py",
        })
    return out


#: The contract declares three states. `background_rate.py` writes its own ELIGIBLE state,
#: which is a different question -- "does this lens hold an index floor?" -- and answers it
#: with `index-bearing`. Both names are right in their own file and wrong together, so the
#: mapping happens here, once, rather than every consumer learning both vocabularies.
_STATE_ALIASES = {"index-bearing": "index"}


def from_background():
    """Firing rates. Already emitted in contract shape by background_rate.py; passed through
    so there is one reader rather than two, with the state name normalised."""
    blob = _load(BACKGROUND)
    if not blob:
        return []
    out = []
    for rec in blob.get("floor_records", []):
        rec = dict(rec)
        rec["state"] = _STATE_ALIASES.get(rec.get("state"), rec.get("state"))
        out.append(rec)
    return out


def from_graph_floors():
    """Edge-perturbation invariance for the graph lenses.

    `graph-floors.json` records subjects and perturbations rather than per-lens floors, and as
    of 2026-09-03 it holds ZERO lenses -- so this yields nothing and the graph lenses appear
    here only through their background rates. That is the honest state (CP5 is unbuilt), and
    it is visible rather than papered over: --check reports which lenses have no index or
    graph record at all.
    """
    blob = _load(GRAPH_FLOORS)
    if not blob:
        return []
    out = []
    for lens_id, rec in sorted((blob.get("lenses") or {}).items()):
        out.append({
            "claim": "%s graph position is above perturbation noise" % lens_id,
            "instrument": "graph",
            "state": "graph",
            "statistic": "asymmetry-ratio",
            "null": "edge-perturb",
            "n": rec.get("subjects") or blob.get("subjects"),
            "threshold_p95": rec.get("threshold_p95"),
            "mde": rec.get("mde"),
            "measured": blob.get("measured"),
            "recomputable": False,
            "source": "eval/graph_floor.py",
        })
    return out


#: INSTRUMENTS THAT PUBLISH A FINDING BUT ARE NOT LENSES.
#:
#: This gate iterated `blob["lenses"]` and reported "all 16 lenses carry a resolution record",
#: which was true and was not the whole question. `tools/ratchet_series.py` is not a lens -- it
#: reads a SERIES of administrative actions and counts one-way movement, which is the object
#: `rollback_asymmetry` was ruled out of measuring -- and it emits findings marked provisional
#: with no null of any kind. Its own docstring says so ("no measured floor yet ... Backlog item
#: 30") and nothing in the contract could see it, because the contract only knew about lenses.
#:
#: An instrument that makes a claim needs a resolution object on the same terms as a lens. It
#: does not get to be exempt by not being in the loop. Listed here so the gate fails loudly
#: until each one has a null, rather than passing by not looking.
#:
#: RESOLVED the same day it was found, and it turned out the instrument already had most of
#: what it needed. `ratchet_series` tests one-way movement with an exact two-sided binomial
#: against a null of 0.5, which IS a resolution object -- it simply never reached this contract.
#: Its detection limit falls straight out of that test: a perfectly one-way series is p = 2/2**n,
#: so five movements with no reversal give p = 0.0625 and report nothing, and six give 0.0312.
#: MDE 6. See `from_ratchet_series()`.
#:
#: What it still lacks is in KNOWN_MISSING_NULLS below and is about RETRIEVAL rather than
#: counting. Those are named rather than guessed.
PUBLISHING_INSTRUMENTS = {
    "ratchet_series": "tools/ratchet_series.py -- counts one-way movement across an "
                      "administrative series, tested against a binomial null. MDE 6 movements.",
}

#: Nulls a listed instrument still lacks, named so the gap is a fact rather than an omission.
#: These do not fail the gate -- the instrument has A resolution object -- but they are the
#: reason its output stays marked provisional.
KNOWN_MISSING_NULLS = {
    "ratchet_series": ("docket-match error rate (did the series retrieve the right documents?) "
                       "and coverage-gap rate (is an action missing?). Both are properties of "
                       "the retrieval rather than the counting, and neither is measurable from "
                       "the fixtures alone."),
}


def from_ratchet_series():
    """The series detector's resolution object, which it already had and never emitted.

    `tools/ratchet_series.py` counts one-way movements across an administrative series and tests
    them with an exact two-sided binomial against a null of 0.5 -- a document is as likely to
    loosen a rule as to tighten it. That IS a resolution object, and the contract could not see
    it because the contract only read lenses.

    THE DETECTION LIMIT FALLS OUT OF THE TEST AND IS WORTH STATING PLAINLY. For a perfectly
    one-way series (every movement forward, none back) the p-value is 2 / 2**n, so:

        n = 5 movements, all one way -> p = 0.0625   reports NOTHING
        n = 6 movements, all one way -> p = 0.0312   the first that clears 0.05

    A five-step ratchet with no reversals is not resolvable by this instrument, however obvious
    it looks in prose. Six is the floor, and a series with any reversal in it needs more.

    Two nulls this detector still does NOT have, and they are recorded as null rather than
    guessed: the docket-match error rate (did the series retrieve the right documents?) and the
    coverage-gap rate (is an action missing from the series?). Both are properties of the
    retrieval, not of the counting, and neither is measurable from the fixtures alone.
    """
    return [{
        "claim": "ratchet_series: this series moves one way beyond chance",
        "instrument": "ratchet_series",
        "state": "series",
        "statistic": "one-way movements",
        "null": "binomial p=0.5 per directional movement",
        "n": None,
        "threshold_p95": 0.05,
        "mde": 6,
        "measured": "2026-09-06",
        "recomputable": True,
        "source": "tools/ratchet_series.py",
    }]


def collect():
    records = (from_lens_floors() + from_background() + from_graph_floors()
               + from_ratchet_series())
    for r in records:
        missing = [f for f in FIELDS if f not in r]
        if missing:
            for f in missing:
                r[f] = None
    return records


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if any lens has no resolution record at all")
    args = ap.parse_args(argv)

    records = collect()
    lenses = sorted(load_lenses(os.path.join(ROOT, "detectors")))

    payload = {
        "_note": ("Every resolution object this project measures, in one record shape (the "
                  "plan's section 2a). Derived: regenerate with python "
                  "eval/floors_contract.py. A number with no record here does not publish."),
        "fields": list(FIELDS),
        "records": records,
    }
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n")

    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    have = {}
    for r in records:
        for lens_id in lenses:
            if r["claim"].startswith(lens_id + " "):
                have.setdefault(lens_id, set()).add(r["state"])

    if args.check:
        naked = [l for l in lenses if l not in have]
        if naked:
            print("LENSES WITH NO RESOLUTION RECORD: %s" % ", ".join(naked))
            print("Regenerate the emitters, then re-run this.")
            return 1
        print("all %d lens(es) carry at least one resolution record" % len(lenses))

        # INSTRUMENTS, on the same terms. A claim is a claim whatever emits it.
        claimed = {r.get("instrument") for r in records}
        bare = sorted(i for i in PUBLISHING_INSTRUMENTS if i not in claimed)
        if bare:
            print("")
            print("INSTRUMENT(S) THAT PUBLISH WITH NO RESOLUTION RECORD: %s" % ", ".join(bare))
            for i in bare:
                print("  %-16s %s" % (i, PUBLISHING_INSTRUMENTS[i]))
            print("")
            print("These are not lenses, so the lens loop above cannot see them -- which is why")
            print("this gate reported everything green while one of them emitted provisional")
            print("findings with no null at all. Give it a floor, or stop it publishing.")
            return 1
        print("all %d publishing instrument(s) carry a resolution record too"
              % len(PUBLISHING_INSTRUMENTS))
        for i, why in sorted(KNOWN_MISSING_NULLS.items()):
            if i in claimed:
                print("  %s still lacks: %s" % (i, why))
        no_index = sorted(l for l in lenses if "index" not in have.get(l, ()))
        if no_index:
            print("  %d of them carry NO index floor and publish as receipts-only: %s"
                  % (len(no_index), ", ".join(no_index)))
        return 0

    by_state = {}
    for r in records:
        by_state.setdefault(r["state"], []).append(r)
    print("FLOORS CONTRACT -- %d record(s) across %d instrument(s)"
          % (len(records), len({r["instrument"] for r in records})))
    for state in sorted(by_state):
        rows = by_state[state]
        pub = sum(1 for r in rows if r.get("recomputable"))
        print("  %-14s %3d record(s), %d publishable with an MDE (recomputable)"
              % (state, len(rows), pub))
    print("")
    print("wrote %s" % os.path.relpath(OUT, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
