"""Network brokerage / centrality detection — the SECOND behavioral (graph) lens.

This is the structural sibling of structural.py. Where structural.py reads a single subject's
CAREER/FUNDING CHAIN, this reads the subject's POSITION IN THE WHOLE GRAPH — who sits on the
shortest paths between everyone else (the bridges), who has the most ties, and which structural
brokerage roles a node plays between sectors. It keeps the exact same ethic:

  * IDEOLOGY-BLIND. A node is scored by WHERE IT SITS in the topology, never by who it is or which
    side it is on. A high-betweenness gov node and a high-betweenness NGO node fire identically.
  * NEVER A VERDICT. Betweenness and brokerage are facts about STRUCTURE, not findings about
    coordination, intent, or guilt. A node on many shortest paths is structurally positioned to
    broker; that is NOT a claim that it does broker, conspires, or controls. The receipt is the
    set of BRIDGING EDGES (the actual ties that put it there) for HUMAN adjudication. The detector
    never decides — it shows the bridges and stops.
  * DEPENDENCY-FREE. stdlib + json only. No networkx, no numpy, no randomness. Betweenness is a
    hand-rollable, re-checkable Brandes BFS. Everything here can be verified by hand against the
    source graph.

Methods implemented:
  * Betweenness centrality via Brandes' algorithm (Ulrik Brandes, "A Faster Algorithm for
    Betweenness Centrality", Journal of Mathematical Sociology 25(2):163-177, 2001). Unweighted,
    undirected; single-source shortest-path BFS accumulation, normalized by (n-1)(n-2)/2.
  * Degree centrality: incident-edge count normalized by (n-1).
  * Gould-Fernandez brokerage roles (Roger V. Gould & Roberto M. Fernandez, "Structures of
    Mediation: A Formal Approach to Brokerage in Transaction Networks", Sociological Methodology
    19:89-126, 1989). For every brokered path a-B-c (B adjacent to both a and c, a and c not
    adjacent), B's role is classified by the GROUP MEMBERSHIP (node `sector`) of a, B, c:
        coordinator   : a, B, c all same group              (within-group broker)
        gatekeeper     : a in other group, B and c same group (broker INTO B's group)
        representative : a and B same group, c other group    (broker OUT of B's group)
        consultant     : B in one group, a and c same OTHER group (itinerant; a==c group != B)
        liaison        : a, B, c all three in DIFFERENT groups  (cross-everything bridge)
    (also called the "itinerant broker" for consultant.) These are STRUCTURAL POSITIONS, not roles
    anyone signed up for.

Edge model (research-entities.json): undirected for centrality/brokerage — every typed edge
(employed-by, funded-by, founded, member-of, authored, influenced, part-of, ...) is a tie. We do
not interpret direction here; position in the undirected tie graph is the signal.

Public API:
  build_graph(graph_path)                          -> Graph
  betweenness_centrality(graph)                    -> {node_id: 0..1}
  degree_centrality(graph)                         -> {node_id: 0..1}
  brokerage_roles(graph)                           -> {node_id: {role: count}}
  subject_network_hits(graph_path, subject_id)     -> list[DetectionHit]
  score_subject(graph_path, subject_id, taxonomy)  -> ModuleResult
"""
from __future__ import annotations

import json
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

from .schema import DetectionHit, ModuleResult
from .loader import load_taxonomy
from .grader import grade_document_for_lens

# Gould-Fernandez role names.
ROLES = ("coordinator", "gatekeeper", "representative", "consultant", "liaison")

# Brokerage roles that bridge ACROSS group (sector) boundaries — the cross-group set.
CROSS_GROUP_ROLES = ("gatekeeper", "representative", "consultant", "liaison")


# ----------------------------------------------------------------------------- graph container

@dataclass
class Graph:
    """An undirected graph with per-node sector labels. Built once, reused by every measure."""
    adj: dict[str, set] = field(default_factory=dict)   # node_id -> set(neighbor_id)
    sector: dict[str, Optional[str]] = field(default_factory=dict)
    name: dict[str, str] = field(default_factory=dict)

    @property
    def nodes(self) -> list[str]:
        return list(self.adj.keys())

    def degree(self, node: str) -> int:
        return len(self.adj.get(node, ()))


def build_graph(graph_path: str) -> Graph:
    """Build an undirected Graph from the research-entities.json edge layer.

    Only nodes that exist in `entities` get a sector/name. Edges referencing unknown ids still
    create adjacency (so the topology is complete) but carry sector=None for those endpoints.
    """
    with open(graph_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    ents = {e["id"]: e for e in data.get("entities", [])}

    g = Graph()
    for eid, ent in ents.items():
        g.adj.setdefault(eid, set())
        g.sector[eid] = ent.get("sector")
        g.name[eid] = ent.get("name", eid)

    for edge in data.get("edges", []):
        s, t = edge.get("source"), edge.get("target")
        if s is None or t is None or s == t:
            continue
        g.adj.setdefault(s, set()).add(t)
        g.adj.setdefault(t, set()).add(s)
        # Ensure endpoints we never saw in entities still have a (None) sector/name.
        g.sector.setdefault(s, None)
        g.sector.setdefault(t, None)
        g.name.setdefault(s, s)
        g.name.setdefault(t, t)
    return g


# ----------------------------------------------------------------------------- betweenness

def betweenness_centrality(graph: Graph, normalized: bool = True) -> dict[str, float]:
    """Betweenness centrality via Brandes' algorithm (2001). Pure-Python BFS, no deps.

    For each source s: BFS to find shortest-path counts sigma and predecessor lists, then
    accumulate dependency delta back-to-front. betweenness[v] += delta over all sources.
    Undirected: each unordered pair is counted from both ends, so we halve at the end.
    Normalized by (n-1)(n-2)/2 (the number of unordered pairs not involving v).
    """
    nodes = graph.nodes
    bc = {v: 0.0 for v in nodes}

    for s in nodes:
        stack: list[str] = []
        pred: dict[str, list] = {w: [] for w in nodes}
        sigma = {w: 0.0 for w in nodes}
        dist = {w: -1 for w in nodes}
        sigma[s] = 1.0
        dist[s] = 0
        queue: deque = deque([s])
        while queue:
            v = queue.popleft()
            stack.append(v)
            for w in graph.adj.get(v, ()):
                if dist[w] < 0:           # first time we reach w
                    dist[w] = dist[v] + 1
                    queue.append(w)
                if dist[w] == dist[v] + 1:  # shortest path to w via v
                    sigma[w] += sigma[v]
                    pred[w].append(v)
        # back-propagation of dependencies
        delta = {w: 0.0 for w in nodes}
        while stack:
            w = stack.pop()
            for v in pred[w]:
                delta[v] += (sigma[v] / sigma[w]) * (1.0 + delta[w])
            if w != s:
                bc[w] += delta[w]

    # undirected: each pair counted twice
    for v in bc:
        bc[v] /= 2.0

    if normalized:
        n = len(nodes)
        if n > 2:
            scale = 1.0 / ((n - 1) * (n - 2) / 2.0)
            for v in bc:
                bc[v] *= scale
    return bc


def degree_centrality(graph: Graph) -> dict[str, float]:
    """Degree centrality: incident edges / (n-1)."""
    n = len(graph.nodes)
    denom = (n - 1) if n > 1 else 1
    return {v: graph.degree(v) / denom for v in graph.nodes}


# ----------------------------------------------------------------------------- Gould-Fernandez

def brokerage_roles(graph: Graph) -> dict[str, dict]:
    """Gould-Fernandez (1989) brokerage-role counts per node, by `sector` group.

    For every ordered open triad a-B-c (a,c both neighbors of B; a,c NOT adjacent; a!=c), increment
    one role count for B based on the sectors of a, B, c. Ordered triads mean (a,c) and (c,a) are
    counted separately, matching the standard GF tabulation. Nodes with sector None are skipped as
    endpoints (group membership is required to classify a brokered tie).
    """
    counts = {v: {r: 0 for r in ROLES} for v in graph.nodes}
    for b in graph.nodes:
        gb = graph.sector.get(b)
        if gb is None:
            continue
        nbrs = [x for x in graph.adj.get(b, ()) if graph.sector.get(x) is not None]
        for a in nbrs:
            ga = graph.sector[a]
            for c in nbrs:
                if a == c:
                    continue
                if c in graph.adj.get(a, ()):     # a and c adjacent -> no brokerage (path closes)
                    continue
                gc = graph.sector[c]
                role = _classify(ga, gb, gc)
                counts[b][role] += 1
    return counts


def _classify(ga, gb, gc) -> str:
    """Classify a brokered triad a-B-c by group membership (Gould-Fernandez typology)."""
    if ga == gb == gc:
        return "coordinator"               # wholly within B's group
    if ga == gb != gc:
        return "representative"            # broker OUT of B's group
    if ga != gb == gc:
        return "gatekeeper"                # broker INTO B's group
    if gb != ga == gc:
        return "consultant"                # itinerant: a and c share a group, B is outside it
    return "liaison"                        # all three different groups


def cross_group_sectors(graph: Graph, node: str) -> set:
    """The distinct neighbor sectors a node bridges (its own sector excluded) — for the receipt."""
    own = graph.sector.get(node)
    out = {graph.sector.get(x) for x in graph.adj.get(node, ())}
    out.discard(None)
    out.discard(own)
    return out


# ----------------------------------------------------------------------------- decile helpers

def _decile_threshold(values: list[float], top_fraction: float) -> float:
    """Value at the top_fraction cut (e.g. 0.10 -> the 90th-percentile value). Inclusive '>='."""
    if not values:
        return float("inf")
    ordered = sorted(values)
    # index of the (1 - top_fraction) quantile
    idx = int(round((1.0 - top_fraction) * (len(ordered) - 1)))
    idx = max(0, min(len(ordered) - 1, idx))
    return ordered[idx]


def _percentile_rank(values: list[float], v: float) -> float:
    """Fraction of values <= v (0..1). Used only for human-readable 'top N%' in spans."""
    if not values:
        return 0.0
    return sum(1 for x in values if x <= v) / len(values)


# ----------------------------------------------------------------------------- the detector

def subject_network_hits(graph_path: str, subject_id: str) -> list[DetectionHit]:
    """Compute network_brokerage DetectionHits for one graph subject. Pure graph math.

    Emits hits for: high betweenness (top-decile bridge), hub degree (top-decile ties), and
    cross-group brokerage (gatekeeper/representative/liaison/consultant roles spanning >=2 sectors).
    span is the human-readable structural receipt; rationale states the structural fact and that it
    is a position, not a coordination or guilt claim.
    """
    g = build_graph(graph_path)
    if subject_id not in g.adj:
        return []

    bc = betweenness_centrality(g)
    dc = degree_centrality(g)
    roles = brokerage_roles(g)

    bc_vals = list(bc.values())
    dc_vals = list(dc.values())
    bc_cut = _decile_threshold(bc_vals, 0.10)
    dc_cut = _decile_threshold(dc_vals, 0.10)

    hits: list[DetectionHit] = []
    name = g.name.get(subject_id, subject_id)
    own_sector = g.sector.get(subject_id) or "?"

    # --- marker: high_betweenness ----------------------------------------------------------
    b = bc.get(subject_id, 0.0)
    if b > 0.0 and b >= bc_cut:
        pct = _percentile_rank(bc_vals, b)
        top_pct = max(1, round((1.0 - pct) * 100))
        bridged = sorted(cross_group_sectors(g, subject_id))
        span = (f"{name}: betweenness {b:.3f} (top {top_pct}% of {len(bc_vals)} nodes); "
                f"bridges sectors {', '.join(bridged) if bridged else own_sector}")
        # 90th pct -> ~0.8, scaling to 1.0 at the very top of the distribution.
        conf = min(1.0, 0.8 + 0.2 * (pct - 0.9) / 0.1) if pct > 0.9 else 0.8
        hits.append(DetectionHit(
            detection_id="high-betweenness",
            confidence=round(conf, 3),
            span=span,
            rationale=("Sits on a top-decile share of the graph's shortest paths — a structural "
                       "bridge. Position only; NOT a claim that it brokers, coordinates, or controls."),
        ))

    # --- marker: hub_degree ----------------------------------------------------------------
    d = dc.get(subject_id, 0.0)
    deg = g.degree(subject_id)
    if deg > 0 and d >= dc_cut:
        pct = _percentile_rank(dc_vals, d)
        top_pct = max(1, round((1.0 - pct) * 100))
        span = f"{name}: degree {deg} (centrality {d:.3f}, top {top_pct}% of {len(dc_vals)} nodes)"
        conf = min(1.0, 0.75 + 0.25 * (pct - 0.9) / 0.1) if pct > 0.9 else 0.75
        hits.append(DetectionHit(
            detection_id="hub-degree",
            confidence=round(conf, 3),
            span=span,
            rationale=("Top-decile number of direct ties — a hub. Count of connections only; says "
                       "nothing about what flows across them or who chose them."),
        ))

    # --- marker: cross_group_brokerage -----------------------------------------------------
    r = roles.get(subject_id, {})
    cross_total = sum(r.get(role, 0) for role in CROSS_GROUP_ROLES)
    bridged = sorted(cross_group_sectors(g, subject_id))
    if cross_total > 0 and len(bridged) >= 2:
        # report the role mix, dominant first
        role_mix = ", ".join(
            f"{role}:{r[role]}" for role in ROLES if r.get(role, 0) > 0
        )
        span = (f"{name} ({own_sector}) brokers across {len(bridged)} sectors "
                f"[{', '.join(bridged)}]; GF roles {{{role_mix}}}")
        # confidence scales with how many distinct sectors are bridged (2 -> 0.7 ... 4+ -> 1.0)
        conf = min(1.0, 0.7 + 0.15 * (len(bridged) - 2))
        hits.append(DetectionHit(
            detection_id="cross-group-broker",
            confidence=round(conf, 3),
            span=span,
            rationale=(f"Occupies Gould-Fernandez cross-group brokerage positions spanning "
                       f"{len(bridged)} sectors. A structural mediation POSITION between groups — "
                       f"never a coordination or guilt claim; the bridging ties are the receipt."),
        ))

    return hits


def score_subject(graph_path: str, subject_id: str, taxonomy_path: str) -> ModuleResult:
    """Run subject_network_hits through the existing grader. token_count=0 (w_density=0)."""
    taxonomy = load_taxonomy(taxonomy_path)
    hits = subject_network_hits(graph_path, subject_id)
    return grade_document_for_lens(taxonomy, hits, token_count=0)
