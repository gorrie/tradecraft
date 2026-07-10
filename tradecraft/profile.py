"""The combined profile: one subject, every applicable lane, each on its own axis.

This ties the two lanes together. For a subject who appears in BOTH the entity graph and the texts
store, it runs:

  * the GRAPH lenses on the topology (both port to the ratchet graph: ``network_brokerage`` from
    adjacency + sector; ``revolving_door`` from the subject's affiliation edges, read as cross-sector
    affiliation breadth — each receipt is annotated that an untyped graph shows breadth, not a
    proven time-ordered trajectory), and
  * the TEXT lenses on the subject's own words (``subject.grade_person``).

It returns a profile — a per-lens vector across both lanes — and **never blends them into one
number**. A high network-brokerage position and a high inevitability-framing register are different
facts about a person; the tool keeps them on separate axes and shows the receipts for each, the same
ideology-blind, never-a-verdict ethic as every other lane.

Graph lenses score a path (research-entities or a converted ratchet graph — see
``adapters.write_ratchet_graph``); the text lane scores the subject's texts.
"""
from __future__ import annotations

import os
from dataclasses import asdict, is_dataclass
from typing import Optional

from .loader import load_lenses
from .subject import grade_person, text_lenses
from . import structural, network

# Both graph lenses now port to the ratchet graph. network_brokerage reads betweenness/degree/
# sector-brokerage from adjacency + sector. revolving_door reads cross-sector spread from the
# subject's affiliation edges (it treats untyped person->institution links as affiliations and
# annotates each receipt that this is affiliation breadth, not a time-ordered trajectory).
_GRAPH_SCORERS = {
    "network_brokerage": network.score_subject,
    "revolving_door": structural.score_subject,
}


def _plain(obj):
    if is_dataclass(obj):
        return {k: _plain(v) for k, v in asdict(obj).items()}
    if isinstance(obj, dict):
        return {k: _plain(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_plain(v) for v in obj]
    return obj


def profile_subject(
    subject_id: str,
    *,
    detectors_dir: str,
    graph_path: Optional[str] = None,
    graph_lenses: tuple[str, ...] = ("network_brokerage", "revolving_door"),
    texts: Optional[list[dict]] = None,
    backend: str = "cues",
    model: Optional[str] = None,
) -> dict:
    """Profile one subject across the graph lane (if ``graph_path`` given) and the text lane (if
    ``texts`` given). Returns ``{subject, graph, text}`` — per lens, never blended, never a verdict.

    ``graph_lenses`` defaults to both graph lenses. On an untyped graph revolving_door reports
    cross-sector affiliation breadth (annotated as such); on a rel-typed graph it reports the
    career-move trajectory.
    """
    out: dict = {"subject": subject_id, "graph": {}, "text": None,
                 "note": "Per-lens, two-lane profile + receipts for human review. The axes are "
                         "never blended into a single score; a profile is not a verdict."}

    if graph_path:
        for lens_id in graph_lenses:
            scorer = _GRAPH_SCORERS.get(lens_id)
            if scorer is None:
                continue
            tax_path = os.path.join(detectors_dir, lens_id, "taxonomy.yaml")
            mr = scorer(graph_path, subject_id, tax_path)
            out["graph"][lens_id] = _plain(mr)

    if texts:
        lenses = text_lenses(load_lenses(detectors_dir))
        subj_profile, docs = grade_person(lenses, subject_id, texts, backend=backend, model=model)
        out["text"] = {"subject": _plain(subj_profile), "documents": [_plain(d) for d in docs]}

    return out
