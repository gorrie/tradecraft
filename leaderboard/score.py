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
# Which board an institution sits on: "captured" (acted upon) or "captor" (the
# apparatus doing it). A per-institution fact, not a per-record one, so it lives
# beside the ledger rather than being repeated on all 150 records.
ROLES = os.path.join(HERE, "data", "roles.json")
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


def load_actors() -> dict[str, str]:
    """The declared actor vocabulary. Empty dict when the file is absent, so an older
    checkout keeps working instead of hard-failing on a file it has never seen."""
    p = os.path.join(os.path.dirname(DATA), "actors.json")
    if not os.path.exists(p):
        return {}
    return (json.load(open(p, encoding="utf-8")) or {}).get("actors", {})


def load_roles() -> dict[str, str]:
    if not os.path.exists(ROLES):
        return {}
    return json.load(open(ROLES, encoding="utf-8"))


def validate(records: list[dict], roles: dict[str, str] | None = None) -> list[str]:
    by_lens = {lid: {m.id for m in tax.markers} for lid, tax in load_lenses(DETECTORS).items()}
    actors = load_actors()
    warns = []
    # The two-board layout filters on `role`; an institution missing from roles.json
    # silently vanishes from both boards, so surface it here rather than at render.
    if roles is not None:
        for inst in sorted({r["institution"] for r in records}):
            if inst not in roles:
                warns.append(f"no role (captured/captor) for {inst} -- it will not render on either board")
    for r in records:
        lens = r.get("lens")
        if lens not in by_lens:
            warns.append(f"unknown lens '{lens}' on {r['institution']} / {r.get('marker')}")
        elif r["marker"] not in by_lens[lens]:
            warns.append(f"marker '{r['marker']}' not in lens '{lens}' ({r['institution']})")
        # `actor` drives the segmented bar and had NO closed vocabulary, while `lens`
        # and `marker` were both validated. A typo or a freelance new faction would
        # silently split one bar into two and nothing anywhere would say so.
        if actors and r.get("actor") not in actors:
            warns.append(f"undeclared actor '{r.get('actor')}' on {r['institution']} / "
                         f"{r.get('marker')} -- declare it in data/actors.json first")
        if r["assurance"] not in ASSURANCE_W:
            warns.append(f"unknown assurance tier: {r['assurance']} ({r['institution']})")
        if not r.get("receipts"):
            warns.append(f"NO RECEIPT (defamation gate) on {r['institution']} / {r['marker']}")
    return warns


#: Gates 17 and 25. A rank is a claim that one row is above another, and that claim needs the
#: contributing lens to have a measured resolution. Eleven of sixteen lenses do not: they hold a
#: background firing rate instead, which supports "this fired, here is the receipt" and supports
#: no ordering at all. Summing them into a rank is the defect this project indicts elsewhere --
#: a number reported without the resolution of the instrument behind it.
#:
#: So a receipts-only lens's records are counted, shown, and NEVER summed into the rank. Read
#: from eval/floors.json, which is the one place that knows each lens's state, rather than from
#: a list here that would drift the first time a lens changed state.
FLOORS = os.path.join(REPO, "eval", "floors.json")


def lens_states() -> dict[str, str]:
    """lens id -> "index" | "receipts-only" | "graph", from the floors contract."""
    try:
        with open(FLOORS, encoding="utf-8") as fh:
            blob = json.load(fh)
    except (OSError, ValueError):
        return {}
    out: dict[str, str] = {}
    for rec in blob.get("records", []):
        # LENS RECORDS ONLY. The contract also carries instruments that are not lenses --
        # ratchet_series reads a SERIES of administrative actions, not a document -- and their
        # claims do not begin with a lens id. Splitting on whitespace regardless would enter
        # "ratchet_series:" here as a lens with a state no consumer knows, which is the silent
        # mismatch the contract's own state test warns about.
        if rec.get("instrument") != "lens":
            continue
        lid = (rec.get("claim") or "").split(" ", 1)[0]
        if not lid:
            continue
        if rec.get("state") == "index":
            out[lid] = "index"
        else:
            out.setdefault(lid, rec.get("state") or "receipts-only")
    return out


def aggregate(records: list[dict], roles: dict[str, str] | None = None) -> list[dict]:
    roles = roles or {}
    states = lens_states()
    by_inst: dict[str, dict] = {}
    for r in records:
        inst = by_inst.setdefault(r["institution"], {
            "institution": r["institution"], "role": roles.get(r["institution"]),
            "fact": 0.0, "unverified": 0.0,
            "receipts_only": 0.0, "receipts_only_n": 0, "receipts_only_lenses": set(),
            "by_actor": {}, "markers": set(), "records": [], "sc_credits": []})
        s = record_score(r)
        state = states.get(r.get("lens"), "unknown")
        if state != "index":
            # Counted and shown, never ranked. `unknown` lands here too: a lens with no
            # record in the floors contract has no demonstrated resolution either, and the
            # safe reading of "we do not know" is "does not order anything".
            inst["receipts_only"] += s
            inst["receipts_only_n"] += 1
            inst["receipts_only_lenses"].add("%s (%s)" % (r.get("lens"), state))
            inst["markers"].add(r["marker"])
            inst["records"].append({**r, "score": s, "ranked": False, "lens_state": state})
            continue
        if r["assurance"] == "FACT":
            inst["fact"] += s
        else:
            inst["unverified"] += s
        inst["by_actor"][r["actor"]] = round(inst["by_actor"].get(r["actor"], 0.0) + s, 4)
        inst["markers"].add(r["marker"])
        if float(r.get("self_correction", 0.0)) > 0:
            inst["sc_credits"].append(float(r["self_correction"]))
        inst["records"].append({**r, "score": s, "ranked": True, "lens_state": "index"})
    rows = []
    for inst in by_inst.values():
        inst["fact"] = round(inst["fact"], 3)
        inst["unverified"] = round(inst["unverified"], 3)
        inst["receipts_only"] = round(inst["receipts_only"], 3)
        inst["receipts_only_lenses"] = sorted(inst["receipts_only_lenses"])
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

    # GATE 17, stated rather than faked. The plan asks the board to refuse a rank gap below
    # the contributing lens's MDE. Those MDEs are in INDEX POINTS PER DOCUMENT; this board's
    # unit is summed severity x assurance x (1 - self-correction) over curated records. They
    # do not convert, so quoting a lens MDE beside a rank gap would be a resolution borrowed
    # from a different measurement -- the same mistake the /tech/instrument renderer nearly
    # shipped. The honest form of the gate is that this board's own unit has NO measured
    # floor, so adjacent rows are not claimed to differ.
    ranked_lenses = sorted({rec["lens"] for r in rows for rec in r["records"]
                            if rec.get("ranked")})
    ro_total = sum(r["receipts_only_n"] for r in rows)
    L += ["",
          "**What the rank is, and is not.** Ordering sums FACT-tier evidence from "
          "index-bearing lenses only — " + (", ".join(f"`{l}`" for l in ranked_lenses) or "none")
          + ". A lens with no measured index floor cannot order anything, so its records are "
          "counted and shown below the board and never summed into a position.",
          "",
          "**No gap between adjacent rows is claimed as a finding.** The lens MDEs are in index "
          "points per document; this board's unit is summed record evidence. They do not "
          "convert, and borrowing one measurement's resolution for another is exactly the "
          "error this project documents in others. This board is an evidence-density map with "
          "receipts, not a ranking with a resolution."]
    if ro_total:
        L += ["",
              "## Receipts-only findings — outside the rank",
              "",
              f"{ro_total} record(s) from lenses that hold a background firing rate rather than "
              "an index floor. Each is a documented action with receipts; none contributes to a "
              "position, because a rate supports *this fired, here is the receipt* and supports "
              "no ordering.",
              "",
              "| Institution | Records | Evidence (unranked) | Lens (state) |",
              "|-------------|--------:|--------------------:|:-------------|"]
        for r in sorted(rows, key=lambda x: -x["receipts_only"]):
            if not r["receipts_only_n"]:
                continue
            L.append(f"| {r['institution']} | {r['receipts_only_n']} | {r['receipts_only']} | "
                     f"{', '.join(r['receipts_only_lenses'])} |")
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
    roles = load_roles()
    warns = validate(records, roles)
    for w in warns:
        print(f"[WARN] {w}", file=sys.stderr)
    rows = aggregate(records, roles)
    md = render_md(rows)
    open(os.path.join(HERE, "OUTPUT.md"), "w", encoding="utf-8", newline="\n").write(md + "\n")
    json.dump(rows, open(os.path.join(HERE, "leaderboard.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1, default=list)
    # Also write the website copy directly so it can never silently drift from source.
    # tradecraft lives at <series>/tradecraft/, so the series root is REPO's parent.
    # SERIES_ROOT env var overrides; skip cleanly if the website tree isn't present
    # (the public standalone tradecraft repo has no website/).
    series = os.environ.get("SERIES_ROOT") or os.path.dirname(REPO)
    web = os.path.join(series, "website", "data", "capture_leaderboard.json")
    if os.path.isdir(os.path.dirname(web)):
        json.dump(rows, open(web, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1, default=list)
        print(f"[synced website copy: {web}]", file=sys.stderr)
    print(md)
    print(f"\n[{len(records)} records, {len(rows)} institutions, {len(warns)} warnings]", file=sys.stderr)
    return 1 if any("NO RECEIPT" in w for w in warns) else 0


if __name__ == "__main__":
    sys.exit(main())
