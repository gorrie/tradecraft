#!/usr/bin/env python3
"""Build the payload for THE CAPTOR'S DESK — the reader plays the captor.

Design: website/_design/FOURTH-INSTRUMENT.md. Pick a target, spend five moves from the
marker taxonomy, then the reveal: every move you chose has already been run, by name,
with a receipt. Then your playbook is Jaccard-matched against the 36 documented
institutions and paired with the two most IDEOLOGICALLY DISTANT matches -- different
flags, same desk. That is method-not-ideology executed on the reader instead of
explained to them.

Runs entirely on data already published: the capture leaderboard (36 institutions /
150 receipted records, with move / actor / assurance / severity / self_correction) and
the 13 detector taxonomies (91 markers). Nothing new is asserted about anyone.

    python tools/export_desk.py
    python tools/export_desk.py --check
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
SERIES = Path(os.environ.get("SERIES_ROOT") or REPO.parent)
LEDGER = REPO / "leaderboard" / "data" / "leaderboard.jsonl"
ROLES = REPO / "leaderboard" / "data" / "roles.json"
OUT = SERIES / "website" / "static" / "tech" / "desk"

sys.path.insert(0, str(REPO))
from tradecraft.loader import load_lenses  # noqa: E402


def build():
    records = [json.loads(l) for l in open(LEDGER, encoding="utf-8") if l.strip()]
    roles = json.load(open(ROLES, encoding="utf-8")) if ROLES.exists() else {}
    lenses = load_lenses(str(REPO / "detectors"))

    # marker -> its home lens + definition, from the taxonomies (never hand-typed)
    marker_meta = {}
    for lid, tax in lenses.items():
        for m in tax.markers:
            marker_meta[m.id] = {
                "id": m.id, "name": m.name, "lens": lid,
                "lens_label": getattr(tax, "name", None) or lid.replace("_", " ").title(),
                "definition": next((d.definition for d in m.detections if d.definition), ""),
            }

    # Which institutions ran which marker, and the receipts that prove it.
    by_marker = defaultdict(list)
    by_inst = defaultdict(set)
    for r in records:
        by_marker[r["marker"]].append({
            "institution": r["institution"], "span": r.get("span"),
            "assurance": r.get("assurance"), "severity": r.get("severity"),
            "self_correction": r.get("self_correction", 0),
            "actor": r.get("actor"), "move": r.get("move"),
            "receipts": r.get("receipts") or [],
        })
        by_inst[r["institution"]].add(r["marker"])

    # Cards. A marker with zero records is KEPT and shown as unrun -- the honest-failure
    # surface: nobody running it and nobody being caught running it look identical here,
    # and the card says so rather than quietly disappearing.
    cards = []
    for mid, meta in sorted(marker_meta.items()):
        runs = by_marker.get(mid, [])
        moves = Counter(x["move"] for x in runs if x.get("move"))
        cards.append({
            **meta,
            "move": moves.most_common(1)[0][0] if moves else None,
            "n_records": len(runs),
            "run_by": sorted({x["institution"] for x in runs}),
            "exemplar": max(runs, key=lambda x: (x.get("severity") or 0)) if runs else None,
        })

    institutions = []
    for inst, markers in sorted(by_inst.items()):
        recs = [r for r in records if r["institution"] == inst]
        sc = [float(r.get("self_correction") or 0) for r in recs]
        institutions.append({
            "institution": inst, "role": roles.get(inst),
            "markers": sorted(markers), "n_records": len(recs),
            "actors": sorted({r.get("actor") for r in recs if r.get("actor")}),
            "fact_records": sum(1 for r in recs if r.get("assurance") == "FACT"),
            "self_correction_mean": round(sum(sc) / len(sc), 3) if sc else 0.0,
            "self_corrected": sum(1 for v in sc if v > 0),
        })

    unrun = [c["id"] for c in cards if not c["n_records"]]
    return {
        "generated_by": "tradecraft/tools/export_desk.py",
        "counts": {
            "markers": len(cards), "markers_unrun": len(unrun),
            "institutions": len(institutions), "records": len(records),
            "moves": dict(Counter(r.get("move") for r in records if r.get("move"))),
        },
        "budget": 5,
        "cards": cards,
        "institutions": institutions,
        # Two registers, because the desk had exactly one and it was the wrong one.
        #
        # These five statements are the methodology, and the UI was rendering all of them,
        # in full, as .dk-honest blocks in the primary view. Ian, on the demo set: "a bunch
        # of explainations about hidden details no one cares about." He is right -- a reader
        # came to pick five moves and see who already runs them, not to read a defence brief.
        #
        # So `honesty` is now the caption-length version the UI shows, and `honesty_full`
        # keeps the full statements for a methods page or an audit. Nothing is deleted: the
        # discipline is still stated, it just stops being the first thing on the screen.
        "honesty": {
            "unrun": (f"{len(unrun)} of {len(cards)} markers have no record against any "
                      "institution -- unrun, not absolved."),
            "assurance": "FACT and ATTRIBUTED records are never flattened together.",
            "denominator": "Every similarity shows its denominator, never a bare percentage.",
            "self_correction": ("Self-correction credits are counted separately, not "
                                "hidden."),
            "not_a_verdict": ("Overlap with a documented playbook is not a claim about "
                              "you."),
        },
        "honesty_full": {
            "unrun": (f"{len(unrun)} of {len(cards)} markers have no record against any "
                      "institution. That does not mean nobody runs them. It means nobody "
                      "has been caught running them and we cannot tell those two apart."),
            "assurance": ("FACT and ATTRIBUTED records are never flattened together. The "
                          "FACT-only toggle visibly drops your match scores, which is the "
                          "point: a weaker evidentiary bar produces a stronger-looking result."),
            "denominator": ("Every similarity is shown as a fraction with its denominator, "
                            "never as a bare percentage."),
            "self_correction": ("Records with a self-correction credit are where the immune "
                                "system actually fired -- an institution catching itself. "
                                "They are counted separately, not hidden."),
            "not_a_verdict": ("Matching a documented institution's playbook says your five "
                              "chosen moves overlap with what that institution has been "
                              "caught doing. It is not a claim about you, and the "
                              "institution's total is not a verdict on it either."),
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    p = build()
    c = p["counts"]
    print(f"markers {c['markers']} ({c['markers_unrun']} unrun) · "
          f"institutions {c['institutions']} · records {c['records']}")
    print(f"moves: {c['moves']}")
    dest = OUT / "desk.json"
    blob = json.dumps(p, ensure_ascii=False, separators=(",", ":"))
    if a.check:
        if not dest.exists() or dest.read_text(encoding="utf-8") != blob:
            print("DRIFT: desk.json differs from a fresh build", file=sys.stderr)
            return 1
        return 0
    OUT.mkdir(parents=True, exist_ok=True)
    dest.write_text(blob, encoding="utf-8", newline="")
    print(f"wrote {dest.relative_to(SERIES)}  {dest.stat().st_size / 1024:.0f} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
