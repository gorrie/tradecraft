#!/usr/bin/env python
"""Does the same method appear under different flags? Counted from the ledger's own labels.

WHAT THIS IS FOR

"Method not ideology" is the load-bearing claim of the Evil Robots series: that the same
institutional manoeuvre recurs across actors who agree about nothing else. This counts it
from the capture ledger -- 150 receipted records, each carrying a marker, an actor family,
an institution, a verbatim span, and source URLs. No model, no benchmark, no score.

NO IMPOSED POLITICAL TAXONOMY. THIS IS THE POINT.

The first version of this file invented six ideological "blocs" (marxist_leninist,
progressive, religious_traditionalist, corporate, administrative, unaligned), assigned the
ledger's actor families to them, and then DECLARED which blocs count as enemies. It
reported "7 of 17 markers span an opposed pair" -- a number that was as much a function of
my groupings as of the data. Change the groupings, change the headline.

That was wrong twice over. It imposed a left/right frame the author's own standing rule
rejects as captured, and it laundered an editorial judgement about who opposes whom into
what looked like a measurement.

So: the only labels used here are the ones the ledger already carries, which are AVOWED
identifications -- `state_leninist`, `religious_right`, `hindu_nationalist`,
`commercial_pr`, `trust_safety`. Those are what each actor calls itself or what a sourced
record calls it. The count is the number of distinct actor families attesting a marker.
Nothing is grouped, nothing is declared opposed, and the reader can see the family names
and judge the distance between them for themselves.

A marker attested across many self-declared families is the claim demonstrated. A marker
confined to one family is the claim NOT demonstrated for that marker, and is printed as
such rather than averaged away.

THE CIRCULARITY, STATED UP FRONT

The ledger was assembled by the author of the thesis it supports. Records selected to show
cross-actor recurrence would show cross-actor recurrence. Not fixable by argument, so:

  1. Every record carries `receipts` (source URLs) and a FACT/ATTRIBUTED tier. The evidence
     is checkable by a hostile reader, which is the only defence that works.
  2. The gaps are printed as loudly as the hits.
  3. No prevalence claim is made or possible -- 150 curated records have no denominator.
     This says the claim is ATTESTED here, never how often it happens in the world.

    python tradecraft/leaderboard/cross_faction.py
    python tradecraft/leaderboard/cross_faction.py --marker permeation --receipts
    python tradecraft/leaderboard/cross_faction.py --json
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
LEDGER = HERE / "data" / "leaderboard.jsonl"

#: How many distinct self-declared actor families a marker needs before it is reported as
#: recurring across actors. Four, not two: two families can be close neighbours, and the
#: claim is about recurrence across genuinely different actors. Stated here rather than
#: tuned, and the full per-marker counts print regardless so the cut is visible.
BREADTH = 4


def load():
    if not LEDGER.is_file():
        sys.exit(f"missing ledger: {LEDGER}")
    return [json.loads(l) for l in LEDGER.read_text(encoding="utf-8").splitlines() if l.strip()]


def analyse(rows):
    by = defaultdict(lambda: {"actors": set(), "institutions": set(), "records": []})
    for r in rows:
        m = r.get("marker")
        if not m:
            continue
        e = by[m]
        if r.get("actor"):
            e["actors"].add(r["actor"])
        if r.get("institution"):
            e["institutions"].add(r["institution"])
        e["records"].append(r)
    out = []
    for m, e in by.items():
        out.append({
            "marker": m,
            "records": len(e["records"]),
            "actor_families": sorted(e["actors"]),
            "institutions": sorted(e["institutions"]),
            "fact_records": sum(1 for r in e["records"] if r.get("assurance") == "FACT"),
        })
    out.sort(key=lambda r: (-len(r["actor_families"]), -r["records"]))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--marker", help="show one marker's receipts in full")
    ap.add_argument("--receipts", action="store_true", help="print spans and source URLs")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    rows = load()
    res = analyse(rows)

    if a.marker:
        hit = next((r for r in res if r["marker"] == a.marker), None)
        if not hit:
            sys.exit(f"no marker {a.marker!r}; try: {', '.join(r['marker'] for r in res[:8])}")
        print(f"{hit['marker']}  --  {hit['records']} records, "
              f"{len(hit['actor_families'])} actor families, "
              f"{len(hit['institutions'])} institutions")
        print(f"  families: {', '.join(hit['actor_families'])}")
        for r in [x for x in rows if x.get("marker") == a.marker]:
            print(f"\n  [{r.get('assurance')}] {r.get('actor')}  --  {r.get('institution')}")
            if a.receipts:
                sp = (r.get("span") or "").strip().replace("\n", " ")
                print(f"    span: {sp[:240]}")
                for u in (r.get("receipts") or [])[:3]:
                    print(f"    src : {u if isinstance(u, str) else u.get('url')}")
        return 0

    if a.json:
        print(json.dumps({"breadth_threshold": BREADTH, "markers": res}, indent=1))
        return 0

    broad = [r for r in res if len(r["actor_families"]) >= BREADTH]
    single = [r for r in res if len(r["actor_families"]) == 1]
    fams = Counter(r.get("actor") for r in rows)

    print(f"capture ledger: {len(rows)} receipted records, {len(res)} markers, "
          f"{len(fams)} self-declared actor families")
    print("no bloc grouping and no declared oppositions -- only the ledger's own labels\n")
    print(f"  {'marker':<34} {'recs':>4} {'families':>8} {'insts':>6}")
    for r in res:
        n = len(r["actor_families"])
        mark = "**" if n >= BREADTH else ("  " if n > 1 else "!!")
        print(f"{mark}{r['marker']:<34} {r['records']:>4} {n:>8} {len(r['institutions']):>6}")
    print()
    print(f"THE CLAIM, COUNTED: {len(broad)} of {len(res)} markers are attested across "
          f"{BREADTH} or more self-declared actor families.")
    print(f"  {len(single)} marker(s) sit in a SINGLE family -- the claim is NOT "
          f"demonstrated for those:")
    for r in single:
        print(f"    !! {r['marker']:<32} only {r['actor_families'][0]} "
              f"({r['records']} records)")
    print("\nrecords per actor family (this is the corpus's real shape, and it is uneven):")
    for f, n in fams.most_common():
        print(f"    {n:>4}  {f}")
    print("\nNo prevalence claim is made: 150 curated records have no denominator. This says "
          "the claim is ATTESTED here, with receipts a reader can check, never how often it "
          "happens in the world.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
