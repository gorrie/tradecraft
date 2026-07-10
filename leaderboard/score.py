#!/usr/bin/env python3
"""Capture leaderboard -- receipts scoreboard over curated capture-action records.

Internal-first. Each record is a documented ACTION against an institution, tagged with the
ACTOR (which faction did it), an ASSURANCE tier, receipts, and a self-correction credit. The
board never emits a single "evil score": it ranks by summed FACT-tier evidence, shows the
attributed/rumor band separately, segments each institution by actor, and credits the
institution's own self-correction. Marker ids are validated against the reference_capture lens
so the board and the detector speak one vocabulary.

Design: memory project_capture_leaderboard. Rank = Σ over FACT records of
severity·assurance_weight·(1 − self_correction). Every cell carries receipts.

Usage:  python leaderboard/score.py            # render markdown board + write OUTPUT.md/.json
"""
from __future__ import annotations
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)
from tradecraft.loader import load_lenses  # noqa: E402

ASSURANCE_W = {"FACT": 1.0, "ATTRIBUTED": 0.6, "RUMOR": 0.25}
DATA = os.path.join(HERE, "data", "leaderboard.jsonl")
DETECTORS = os.path.join(REPO, "detectors")


def record_score(r: dict) -> float:
    w = ASSURANCE_W[r["assurance"]]
    return round(float(r["severity"]) * w * (1.0 - float(r.get("self_correction", 0.0))), 4)


def load_records() -> list[dict]:
    out = []
    for line in open(DATA, encoding="utf-8"):
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def validate(records: list[dict]) -> list[str]:
    by_lens = {lid: {m.id for m in tax.markers} for lid, tax in load_lenses(DETECTORS).items()}
    warns = []
    for r in records:
        lens = r.get("lens")
        if lens not in by_lens:
            warns.append(f"unknown lens '{lens}' on {r['institution']} / {r.get('marker')}")
        elif r["marker"] not in by_lens[lens]:
            warns.append(f"marker '{r['marker']}' not in lens '{lens}' ({r['institution']})")
        if r["assurance"] not in ASSURANCE_W:
            warns.append(f"unknown assurance tier: {r['assurance']} ({r['institution']})")
        if not r.get("receipts"):
            warns.append(f"NO RECEIPT (defamation gate) on {r['institution']} / {r['marker']}")
    return warns


def aggregate(records: list[dict]) -> list[dict]:
    by_inst: dict[str, dict] = {}
    for r in records:
        inst = by_inst.setdefault(r["institution"], {
            "institution": r["institution"], "fact": 0.0, "unverified": 0.0,
            "by_actor": {}, "markers": set(), "records": [], "sc_credits": []})
        s = record_score(r)
        if r["assurance"] == "FACT":
            inst["fact"] += s
        else:
            inst["unverified"] += s
        inst["by_actor"][r["actor"]] = round(inst["by_actor"].get(r["actor"], 0.0) + s, 4)
        inst["markers"].add(r["marker"])
        if float(r.get("self_correction", 0.0)) > 0:
            inst["sc_credits"].append(float(r["self_correction"]))
        inst["records"].append({**r, "score": s})
    rows = []
    for inst in by_inst.values():
        inst["fact"] = round(inst["fact"], 3)
        inst["unverified"] = round(inst["unverified"], 3)
        inst["markers"] = sorted(inst["markers"])
        inst["self_correction_mean"] = round(sum(inst["sc_credits"]) / len(inst["sc_credits"]), 2) if inst["sc_credits"] else 0.0
        rows.append(inst)
    rows.sort(key=lambda x: x["fact"], reverse=True)
    return rows


def render_md(rows: list[dict]) -> str:
    L = ["# Capture Leaderboard (internal)", "",
         "*Receipts scoreboard over documented capture actions. Ranked by summed FACT-tier evidence "
         "(severity x assurance x (1 - self-correction)); the attributed/rumor band is shown separately and "
         "never drives the rank. Every row is backed by receipts; self-correction credit rewards an "
         "institution policing itself. Not a verdict -- an evidence density map.*", "",
         "| # | Institution | FACT | Unverified | Markers | Actors (segmented) | Self-corr |",
         "|---|-------------|-----:|-----------:|:--------|:-------------------|:---------:|"]
    for i, r in enumerate(rows, 1):
        actors = ", ".join(f"{a}:{v}" for a, v in sorted(r["by_actor"].items(), key=lambda kv: -kv[1]))
        L.append(f"| {i} | {r['institution']} | {r['fact']} | {r['unverified']} | "
                 f"{len(r['markers'])} | {actors} | {r['self_correction_mean']} |")
    L += ["", "## Per-institution receipts", ""]
    for r in rows:
        L.append(f"### {r['institution']}  (FACT {r['fact']} | unverified {r['unverified']})")
        for rec in sorted(r["records"], key=lambda x: -x["score"]):
            recs = " ".join(f"[src]({u})" for u in rec["receipts"])
            L.append(f"- **{rec['marker']}** [{rec['move']}] | actor={rec['actor']} | {rec['assurance']} "
                     f"| sev {rec['severity']} | self-corr {rec.get('self_correction',0.0)} | score {rec['score']} -- "
                     f"\"{rec['span']}\" {recs}")
        L.append("")
    return "\n".join(L)


def main() -> int:
    records = load_records()
    warns = validate(records)
    for w in warns:
        print(f"[WARN] {w}", file=sys.stderr)
    rows = aggregate(records)
    md = render_md(rows)
    open(os.path.join(HERE, "OUTPUT.md"), "w", encoding="utf-8", newline="\n").write(md + "\n")
    json.dump(rows, open(os.path.join(HERE, "leaderboard.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1, default=list)
    print(md)
    print(f"\n[{len(records)} records, {len(rows)} institutions, {len(warns)} warnings]", file=sys.stderr)
    return 1 if any("NO RECEIPT" in w for w in warns) else 0


if __name__ == "__main__":
    sys.exit(main())
