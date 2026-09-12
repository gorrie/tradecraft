#!/usr/bin/env python
"""Does the detector fire the same on both political directions? Measure it.

WHY

`sourcing_asymmetry/taxonomy.yaml:14` says the lens flags "METHOD of imbalance, never the
position taken ... never a left/right". On 2026-08-26 the detection underneath that line
shipped eight cues, every one an epithet for a right-coded actor, with no mirror anywhere
in the taxonomy. Nothing caught it because nothing had ever asked.

A claim a file makes about itself in prose is exactly the claim that drifts from the data
underneath it. This turns the assertion into a number, and it is architecture-independent:
whatever the find stage becomes -- cues, embeddings, a fine-tuned encoder -- it answers the
same question the same way, so replacements can be compared on the axis that matters most.

WHAT IT DOES

`eval/mirror-pairs.json` holds pairs: one sentence twice, only the political valence
swapped. Same construction, same rhetorical move. A direction-neutral detection must fire
identically on both halves. Where it fires on one, the detector is measuring political
direction and reporting it as method.

CONTROLS ARE LOAD-BEARING. Pairs marked `control` use a non-political cue and MUST come out
symmetric. If a control fails, the harness is broken and no other row here means anything --
so a control failure is reported as a HARNESS error, not as a finding about the detector.

CAMP-INDEXED LENSES ARE EXEMPT, AND THE EXEMPTION IS DECLARED. `subculture_register` names
27 camps across the spectrum and never claims a given detection is neutral; it claims to
identify which register is speaking. Symmetry there is a property of the roster, reported
separately, not of any single detection. Exemptions live in the JSON with their reasons so
that "exempt" can never quietly become "untested".

    python tradecraft/eval/mirror_eval.py
    python tradecraft/eval/mirror_eval.py --json
    python tradecraft/eval/mirror_eval.py --strict    # exit 1 on any asymmetry
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PAIRS = Path(__file__).resolve().parent / "mirror-pairs.json"

#: NO left/right grouping. An earlier version of this file sorted subculture_register's 27
#: camps into "left" / "right" / "technocratic_or_other" and reported a balance across them.
#: That imposed exactly the captured left/right axis this project's standing rule rejects,
#: and it was my categorisation of the author's taxonomy rather than anything the taxonomy
#: says about itself. Removed. The camps carry avowed names -- revolutionary_left,
#: ethnonationalist, tradcath_integralist, maga_new_right -- and the roster is reported as
#: those names with their cue depth, so a reader can judge the spread without being handed
#: a binary.

def fired(text, lenses, lens_id):
    from tradecraft.detect import detect_cues
    tax = lenses[lens_id]
    return sorted({h.detection_id for h in detect_cues(text, tax)})


def roster(lenses) -> dict:
    """Camp-indexed lenses: report each camp and its cue depth, ungrouped.

    No families, no axis. The spread is shown as the avowed camp names and how many cues
    each carries; grouping them is the editorial act that got removed.
    """
    tax = lenses.get("subculture_register")
    if not tax:
        return {}
    return {m.id: sum(len(d.cues) for d in m.detections) for m in tax.markers}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 on any asymmetric pair, not only on a broken control")
    a = ap.parse_args(argv)

    from tradecraft.loader import load_lenses
    lenses = load_lenses(str(ROOT / "detectors"))
    spec = json.loads(PAIRS.read_text(encoding="utf-8"))

    rows, harness_broken = [], []
    for p in spec["pairs"]:
        lid = p["lens"]
        if lid not in lenses:
            rows.append({**{k: p[k] for k in ("id", "lens", "detection")},
                         "status": "LENS-MISSING"})
            continue
        L = fired(p["left"], lenses, lid)
        R = fired(p["right"], lenses, lid)
        sym = L == R
        # THREE outcomes, not two. A pair where NEITHER half fires is symmetric in the
        # trivial sense and tests nothing -- it cannot tell a balanced detector from one
        # with no vocabulary for either direction. Counting those as passes is how a
        # symmetry suite quietly becomes decoration, so they are reported VACUOUS and
        # excluded from the denominator.
        if not sym:
            status = "ASYMMETRIC"
        elif not L and not R:
            status = "vacuous"
        else:
            status = "symmetric"
        row = {"id": p["id"], "lens": lid, "detection": p["detection"],
               "control": bool(p.get("control")),
               "left_fired": L, "right_fired": R, "status": status}
        if p.get("control") and not sym:
            row["status"] = "HARNESS-BROKEN"
            harness_broken.append(p["id"])
        rows.append(row)

    live = [r for r in rows if not r["control"]]
    asym = [r for r in live if r["status"] == "ASYMMETRIC"]
    vac = [r for r in live if r["status"] == "vacuous"]
    tested = [r for r in live if r["status"] in ("symmetric", "ASYMMETRIC")]
    result = {
        "pairs": len(live), "controls": len(rows) - len(live),
        "informative_pairs": len(tested),
        "vacuous_pairs": [r["id"] for r in vac],
        "asymmetric": len(asym),
        "harness_broken": harness_broken,
        "exempt_lenses": spec.get("exempt_lenses", {}),
        "roster": roster(lenses),
        "rows": rows,
    }

    if a.json:
        print(json.dumps(result, indent=1))
    else:
        print(f"mirror pairs: {len(live)} directional, {result['controls']} controls\n")
        for r in rows:
            tag = {"symmetric": "  ok  ", "ASYMMETRIC": " ASYM ", "vacuous": " ---- ",
                   "HARNESS-BROKEN": " BROKE", "LENS-MISSING": " MISS "}.get(r["status"], "  ?   ")
            print(f"{tag} {r['id']:<26} {r['detection']:<28}")
            if r["status"] != "symmetric":
                print(f"         left  -> {r['left_fired'] or '(nothing)'}")
                print(f"         right -> {r['right_fired'] or '(nothing)'}")
        print(f"\n{len(asym)} of {len(tested)} INFORMATIVE directional pairs "
              f"are ASYMMETRIC  ({len(vac)} vacuous -- neither side fired, so they "
              f"test nothing)")
        if vac:
            print("  vacuous: " + ", ".join(r["id"] for r in vac))
            print("  a vacuous pair is a gap in the SUITE, not a pass: write one "
                  "whose cue the detector actually carries, or the suite "
                  "decorates rather than tests.")
        if harness_broken:
            print(f"HARNESS BROKEN on controls {harness_broken} -- no row above is "
                  f"trustworthy until a non-political pair fires the same both ways")
        r = result["roster"]
        if r:
            print()
            print(f"camp roster ({len(r)} camps, cue depth each) -- ungrouped on purpose:")
            for camp, n in sorted(r.items(), key=lambda kv: -kv[1]):
                print(f"    {n:>3}  {camp}")
        for lid, why in (spec.get("exempt_lenses") or {}).items():
            print(f"\nEXEMPT {lid}: {why[:200]}")

    if harness_broken:
        return 2
    return 1 if (a.strict and asym) else 0


if __name__ == "__main__":
    sys.exit(main())
