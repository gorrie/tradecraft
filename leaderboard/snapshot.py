#!/usr/bin/env python3
"""Capture-leaderboard OBSERVATORY — timestamp a cut and diff it against the last.

The leaderboard is a standing longitudinal instrument, the same shape as the AI-bias study:
re-measure on a cadence, archive each cut, report the drift. This script archives the current
leaderboard.json as snapshots/leaderboard-<date>.json and emits DELTA.md — what moved since the
prior cut. The delta is the mailing-list digest payload ("this cycle's movement, with receipts").

Run after score.py:  python leaderboard/score.py && python leaderboard/snapshot.py 2026-07-08

Date is passed in (no wall-clock dependency, so runs are reproducible). Designed to be driven by
the shared observatory runner alongside the bias-study cut — see memory project_capture_leaderboard.
"""
from __future__ import annotations
import json, os, sys, glob

HERE = os.path.dirname(os.path.abspath(__file__))
CUR = os.path.join(HERE, "leaderboard.json")
SNAP_DIR = os.path.join(HERE, "snapshots")


def _by_inst(rows: list[dict]) -> dict[str, dict]:
    return {r["institution"]: r for r in rows}


def _prior_snapshot(exclude: str) -> str | None:
    snaps = sorted(p for p in glob.glob(os.path.join(SNAP_DIR, "leaderboard-*.json"))
                   if os.path.basename(p) != exclude)
    return snaps[-1] if snaps else None


def delta(prev: list[dict], cur: list[dict]) -> list[str]:
    p, c = _by_inst(prev), _by_inst(cur)
    L = []
    added = [i for i in c if i not in p]
    removed = [i for i in p if i not in c]
    if added:
        L.append(f"- **New on the board:** {', '.join(added)}")
    if removed:
        L.append(f"- **Dropped:** {', '.join(removed)}")
    for inst in sorted(set(p) & set(c)):
        pf, cf = p[inst]["fact"], c[inst]["fact"]
        pm, cm = len(p[inst]["markers"]), len(c[inst]["markers"])
        bits = []
        if abs(cf - pf) >= 0.01:
            bits.append(f"FACT {pf}->{cf} ({'+' if cf>=pf else ''}{round(cf-pf,2)})")
        if cm != pm:
            bits.append(f"markers {pm}->{cm}")
        if bits:
            L.append(f"- **{inst}:** {'; '.join(bits)}")
    return L or ["- No change since the prior cut."]


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python leaderboard/snapshot.py <YYYY-MM-DD>", file=sys.stderr)
        return 2
    date = sys.argv[1]
    cur = json.load(open(CUR, encoding="utf-8"))
    os.makedirs(SNAP_DIR, exist_ok=True)
    snap_name = f"leaderboard-{date}.json"
    snap_path = os.path.join(SNAP_DIR, snap_name)
    json.dump(cur, open(snap_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=list)

    prior = _prior_snapshot(exclude=snap_name)
    L = [f"# Capture Leaderboard - drift as of {date}", ""]
    if prior:
        prev = json.load(open(prior, encoding="utf-8"))
        L.append(f"*Change since {os.path.basename(prior).replace('leaderboard-','').replace('.json','')}:*")
        L.append("")
        L += delta(prev, cur)
    else:
        L.append(f"*Baseline cut established: {len(cur)} institutions, "
                 f"{sum(len(i['records']) for i in cur)} records. No prior cut to diff.*")
    open(os.path.join(HERE, "DELTA.md"), "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")
    print("\n".join(L))
    print(f"\n[snapshot: {snap_name}; prior: {os.path.basename(prior) if prior else 'none'}]", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
