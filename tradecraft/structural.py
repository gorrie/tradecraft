"""Structural (graph-based) detection for the revolving_door lens.

This is the BEHAVIORAL counterpart to detect.py. Where detect.py reads PROSE with an LLM,
this reads the GRAPH with pure arithmetic. It shares detect.py's ethic exactly:

  * IDEOLOGY-BLIND. A move is scored by its STRUCTURE (career/funding topology), never by who
    made it or which side they are on. A gov->Google crossing and a gov->ACLU crossing fire the
    same detection. The watcher->watched edge is the signal, not the politics on either end.
  * NEVER A VERDICT. A revolving door is a fact about topology, not a finding about a person.
    The detector emits DetectionHits whose span is the EDGE-CHAIN RECEIPT — the exact moves that
    made it fire — for HUMAN adjudication. The grader keeps every hit.
  * DETERMINISTIC. stdlib + json only. No network, no LLM, no randomness. Re-runnable and
    checkable by hand against the source graph.

Edge model (research-entities.json):
  entities: {id, name, type, sector, ...}   sector in
            {academia, fin, gov, imf, intel, labor, media, occult, tank, tech}
  edges:    {source, target, rel, ...}
            career-move rels (person -> institution):
              employed-by, moved-to, founded, member-of, appointed-by, recruited
            funding rel: `source funded-by target`  => TARGET is the FUNDER, source the recipient.

Public API:
  detect_subject(graph_path, subject_id)               -> list[DetectionHit]
  score_subject(graph_path, subject_id, taxonomy_path) -> ModuleResult
"""
from __future__ import annotations

import json
from dataclasses import replace
from typing import Optional

from .schema import DetectionHit, ModuleResult
from .loader import load_taxonomy
from .grader import grade_document_for_lens

# Career-move relations that constitute a "move" in a person's trajectory.
MOVE_RELS = {"employed-by", "moved-to", "founded", "member-of", "appointed-by", "recruited"}

# Sector roles (method, not ideology — these are structural categories, not teams).
MONITOR_SECTORS = {"tank", "intel", "media"}   # watchdog / investigative / research roles
INDUSTRY_SECTORS = {"tech", "fin"}             # the monitored / regulated industry
GOV_SECTORS = {"gov"}


# ----------------------------------------------------------------------------- graph helpers

def _load_graph(graph_path: str) -> tuple[dict, list[dict]]:
    with open(graph_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    ents = {e["id"]: e for e in data.get("entities", [])}
    edges = data.get("edges", [])
    return ents, edges


def _sector(ents: dict, eid: str) -> Optional[str]:
    return (ents.get(eid) or {}).get("sector")


def _name(ents: dict, eid: str) -> str:
    return (ents.get(eid) or {}).get("name", eid)


def _career_moves(ents: dict, edges: list[dict], subject_id: str) -> list[dict]:
    """Outgoing career-move edges for a subject, in graph order (the trajectory).

    An edge counts as a move if its ``rel`` is a career-move type, OR if it carries no ``rel`` at
    all — an *affiliation* edge from an untyped graph (e.g. the ratchet person->institution layer,
    which records affiliations without typing or ordering them). Typed graphs are unaffected:
    non-move rels (funded-by, allied-with, authored, ...) still carry a rel and stay excluded.
    """
    return [
        e for e in edges
        if e.get("source") == subject_id and (e.get("rel") in MOVE_RELS or not e.get("rel"))
    ]


def _funded_recipients(edges: list[dict], subject_id: str) -> list[dict]:
    """Edges where subject is the FUNDER (i.e. the target of a `funded-by` edge)."""
    return [
        e for e in edges
        if e.get("rel") == "funded-by" and e.get("target") == subject_id
    ]


def _chain_label(ents: dict, edges: list[dict]) -> str:
    """Human-readable receipt: 'DFRLab (tank) -> Meta (tech) -> ...'."""
    parts = []
    for e in edges:
        tgt = e["target"]
        parts.append(f"{_name(ents, tgt)} ({_sector(ents, tgt) or '?'})")
    return " -> ".join(parts)


# ----------------------------------------------------------------------------- the detector

def detect_subject(graph_path: str, subject_id: str) -> list[DetectionHit]:
    """Compute revolving_door DetectionHits for one graph subject. Pure graph math.

    confidence scales with how strongly each detection fires (capped at 1.0). span is the
    edge-chain receipt; rationale states the structural fact, never a verdict.
    """
    ents, edges = _load_graph(graph_path)
    if subject_id not in ents:
        return []

    hits: list[DetectionHit] = []

    moves = _career_moves(ents, edges, subject_id)
    # Affiliation mode: the subject's moves are all untyped (an affiliation graph, no rel/ordering).
    # The sector-spanning structure is still real; the time-ordered "trajectory" claim is not, so we
    # annotate every receipt to keep that distinction honest.
    untyped_mode = bool(moves) and all(not m.get("rel") for m in moves)
    aff_note = ("  [affiliation graph: links are untyped/unordered — cross-sector affiliation "
                "breadth, not a proven time-ordered trajectory]") if untyped_mode else ""
    move_targets = [m["target"] for m in moves]
    sectors_seq = [_sector(ents, t) for t in move_targets]
    sectors = {s for s in sectors_seq if s}
    n_moves = len(moves)
    chain = _chain_label(ents, moves) if moves else ""

    # --- marker: multi_sector_career --------------------------------------------------------
    n_sectors = len(sectors)
    if n_sectors >= 3:
        span = f"{chain} [{n_moves} moves, {n_sectors} sectors: {', '.join(sorted(sectors))}]"
        # 3 sectors -> 0.85, scaling toward 1.0 by 4+ (rare in practice).
        hits.append(DetectionHit(
            detection_id="spans-three-sectors",
            confidence=min(1.0, 0.85 + 0.05 * (n_sectors - 3)),
            span=span,
            rationale=f"Career moves traverse {n_sectors} distinct sectors "
                      f"({', '.join(sorted(sectors))}). Structural spread only — not a judgment.",
        ))
    if n_sectors >= 4:
        span = f"{chain} [{n_moves} moves, {n_sectors} sectors: {', '.join(sorted(sectors))}]"
        hits.append(DetectionHit(
            detection_id="spans-four-plus-sectors",
            confidence=1.0,
            span=span,
            rationale=f"Career moves traverse {n_sectors} sectors — a four-plus-sector spread.",
        ))

    # --- marker: serial_migration -----------------------------------------------------------
    if n_moves >= 3:
        span = f"{chain} [{n_moves} moves]"
        # 3 moves -> 0.8, 4 -> 0.9, 5+ -> 1.0
        hits.append(DetectionHit(
            detection_id="three-plus-moves",
            confidence=min(1.0, 0.8 + 0.1 * (n_moves - 3)),
            span=span,
            rationale=f"{n_moves} documented career moves — frequency of circulation only.",
        ))
    if n_moves >= 5:
        span = f"{chain} [{n_moves} moves]"
        hits.append(DetectionHit(
            detection_id="five-plus-moves",
            confidence=1.0,
            span=span,
            rationale=f"{n_moves} documented career moves — sustained high-frequency circulation.",
        ))

    # --- marker: monitor_to_industry --------------------------------------------------------
    touches_monitor = bool(sectors & MONITOR_SECTORS)
    touches_industry = bool(sectors & INDUSTRY_SECTORS)
    if touches_monitor and touches_industry:
        mon = sorted(sectors & MONITOR_SECTORS)
        ind = sorted(sectors & INDUSTRY_SECTORS)
        span = f"{chain} [monitor: {', '.join(mon)} -> industry: {', '.join(ind)}]"
        hits.append(DetectionHit(
            detection_id="watchdog-then-join",
            confidence=1.0,
            span=span,
            rationale=f"Career touches a monitoring sector ({', '.join(mon)}) and an industry "
                      f"node ({', '.join(ind)}) it would have been positioned to monitor.",
        ))

    # --- marker: gov_industry_crossing ------------------------------------------------------
    touches_gov = bool(sectors & GOV_SECTORS)
    if touches_gov and touches_industry:
        ind = sorted(sectors & INDUSTRY_SECTORS)
        span = f"{chain} [crosses gov <-> industry: {', '.join(ind)}]"
        hits.append(DetectionHit(
            detection_id="crosses-gov-industry",
            confidence=1.0,
            span=span,
            rationale=f"Career connects a government node and an industry node "
                      f"({', '.join(ind)}). Direction-agnostic; ideology-blind.",
        ))

    # --- marker: funder_multiple_recipients -------------------------------------------------
    funded = _funded_recipients(edges, subject_id)
    if funded:
        recipients = [f["source"] for f in funded]
        recip_sectors = {_sector(ents, r) for r in recipients}
        recip_sectors.discard(None)
        recip_label = ", ".join(f"{_name(ents, r)} ({_sector(ents, r) or '?'})" for r in recipients)
        n_recip = len(recipients)
        if n_recip >= 3:
            hits.append(DetectionHit(
                detection_id="funds-three-plus",
                confidence=min(1.0, 0.8 + 0.05 * (n_recip - 3)),
                span=f"{_name(ents, subject_id)} funds: {recip_label} [{n_recip} recipients]",
                rationale=f"Funds {n_recip} recipients — concentration of funding, cause-neutral.",
            ))
        # recipient AND evaluator: spans an industry/tech project AND a standards/evaluation
        # (tank) body in the same hand.
        if (recip_sectors & INDUSTRY_SECTORS) and ("tank" in recip_sectors):
            hits.append(DetectionHit(
                detection_id="funds-recipient-and-evaluator",
                confidence=1.0,
                span=f"{_name(ents, subject_id)} funds both an industry node and a "
                     f"standards/evaluation body: {recip_label}",
                rationale="Same funder pays both a project (industry/tech) and a "
                          "standards/evaluation body (tank) — recipient and evaluator.",
            ))
        elif "tank" in recip_sectors and n_recip >= 2:
            # Multiple tank recipients can include both worked-on projects and the evaluator;
            # fire the (weaker presence via funds-three-plus already), but only assert the
            # evaluator overlap when an industry+tank pairing is present (above). No extra hit here.
            pass

    if aff_note:
        hits = [replace(h, rationale=h.rationale + aff_note) for h in hits]
    return hits


def score_subject(graph_path: str, subject_id: str, taxonomy_path: str) -> ModuleResult:
    """Run detect_subject through the existing grader. token_count=0 (w_density=0 for this lens)."""
    taxonomy = load_taxonomy(taxonomy_path)
    hits = detect_subject(graph_path, subject_id)
    return grade_document_for_lens(taxonomy, hits, token_count=0)
