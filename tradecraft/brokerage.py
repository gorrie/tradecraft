"""Graph-position detection for the network_brokerage lens: Brandes, degree, Gould-Fernandez.

WHY THIS EXISTS
---------------
`network_brokerage` shipped as a taxonomy with three detections, six gold entries carrying
specific computed figures -- *"Frontier Model Forum: betweenness 0.087 (top of 172 nodes),
degree 10"*, *"OpenAI: degree 17"*, *"Anthropic ... coordinator:84, gatekeeper:29"* -- and
**no code able to fire any of them.** `structural.py` implements the eight `revolving_door`
detections and does not mention this lens. Whoever computed those numbers did it outside the
repository, so the lens declared `reads: graph` while nothing read a graph for it, and its
correctness was unverifiable by construction.

This is that missing half. Same ethic as structural.py, and it matters more here than anywhere
else in the repo:

  * IDEOLOGY-BLIND. A node is scored by WHERE IT SITS. A top-decile gov bridge and a
    top-decile NGO bridge trip the identical detection.
  * POSITION, NEVER ACTION. Betweenness and brokerage are facts about topology. **A node
    positioned to broker is not a node shown to broker.** Nothing here licenses a claim about
    coordination, intent, or guilt, and the receipts are the bridging edges so a human can see
    exactly what the arithmetic saw.
  * DETERMINISTIC. stdlib only, exact algorithms, no sampling. Brandes is exact; on a graph
    this size there is no reason to approximate and every reason not to.

THRESHOLDS
----------
Top decile, per the taxonomy's own definitions ("TOP DECILE of the graph"). Relative rather
than absolute on purpose: an absolute betweenness cut means something different on a 180-node
graph than on a 10,000-node one, and this graph grows every time a dossier lands.
"""
from __future__ import annotations

import json
from collections import deque

from .schema import DetectionHit

#: Gould-Fernandez (1989) triad roles, keyed on the sectors of (a, B, c) in an open triad
#: a--B--c where a and c are NOT tied. Cross-group roles are everything but coordinator.
CROSS_GROUP_ROLES = ("gatekeeper", "representative", "consultant", "liaison")

DECILE = 0.90


def load_graph(graph_path):
    with open(graph_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    entities = {e["id"]: e for e in (data.get("entities") or [])}
    edges = data.get("edges") or []
    return entities, edges


def adjacency(entities, edges):
    """Undirected adjacency over the whole link layer.

    UNDIRECTED because betweenness and brokerage are about who sits between whom, and an
    `employed-by` arrow's direction does not change whether a path runs through a node. Edges
    touching an id that is not in `entities` are dropped rather than inventing a node -- a
    dangling edge is a graph defect and should not quietly add a degree-1 phantom.
    """
    adj = {eid: set() for eid in entities}
    dropped = 0
    for e in edges:
        s, t = e.get("source"), e.get("target")
        if s in adj and t in adj and s != t:
            adj[s].add(t)
            adj[t].add(s)
        else:
            dropped += 1
    return adj, dropped


def betweenness(adj):
    """Exact betweenness centrality, Brandes (2001), unweighted and undirected.

    Normalised by (n-1)(n-2)/2 so the figure is a share of all node pairs and is comparable
    across graph sizes -- which is what the gold's "0.087" is quoted as.
    """
    nodes = list(adj)
    bc = {v: 0.0 for v in nodes}
    for s in nodes:
        stack, preds, sigma, dist = [], {v: [] for v in nodes}, {v: 0 for v in nodes}, {}
        sigma[s] = 1
        dist[s] = 0
        queue = deque([s])
        while queue:
            v = queue.popleft()
            stack.append(v)
            for w in adj[v]:
                if w not in dist:
                    dist[w] = dist[v] + 1
                    queue.append(w)
                if dist[w] == dist[v] + 1:
                    sigma[w] += sigma[v]
                    preds[w].append(v)
        delta = {v: 0.0 for v in nodes}
        while stack:
            w = stack.pop()
            for v in preds[w]:
                delta[v] += (sigma[v] / sigma[w]) * (1.0 + delta[w])
            if w != s:
                bc[w] += delta[w]
    n = len(nodes)
    if n > 2:
        # The raw accumulation runs every node as a source, so each UNORDERED pair is counted
        # twice: raw/2 is the pair count. Dividing that by the (n-1)(n-2)/2 pairs that exclude
        # the node gives raw/((n-1)(n-2)).
        #
        # This shipped for one run as 2/((n-1)(n-2)), i.e. four times too large, and the
        # A--B--C unit test caught it: B sits on the only path between the other two, so its
        # normalised betweenness is 1.0 by definition and the code said 2.0. Worth noting how
        # invisible that was on the real graph -- every node was inflated by the same factor,
        # so every RANK was correct and the whole ordering looked right.
        scale = 1.0 / ((n - 1) * (n - 2))
        for v in bc:
            bc[v] *= scale
    return bc


def gf_roles(adj, sector_of, node):
    """Gould-Fernandez brokerage census for one node, over OPEN triads a--node--c.

    Open only: if a and c are tied to each other the node is not brokering anything between
    them, it is a third party to an existing relationship. That distinction is the whole
    content of the measure.

    ORDERED PAIRS, which is the canonical Gould-Fernandez convention and not a detail. The
    first implementation here counted each unordered pair once and produced exactly half the
    figures the lens's own gold quotes -- coordinator 42 against gold's 84, liaison 3 against
    6. The tell that settled it: gold reports `gatekeeper:29, representative:29`, and those
    two counts are EQUAL BY CONSTRUCTION under the ordered convention, because a triad
    a--B--c with a outside B's group and c inside it is a gatekeeper role read one way and a
    representative role read the other. Equal counts are the signature; the gold was right
    and this function was wrong.
    """
    roles = {"coordinator": 0, "gatekeeper": 0, "representative": 0,
             "consultant": 0, "liaison": 0}
    spans = set()
    receipts = []
    neighbours = sorted(adj[node])
    b_sec = sector_of(node)
    for a in neighbours:
        for c in neighbours:
            if a == c or c in adj[a]:
                continue                       # self, or a closed triad: not brokerage
            a_sec, c_sec = sector_of(a), sector_of(c)
            if a_sec == b_sec == c_sec:
                role = "coordinator"
            elif a_sec == c_sec and a_sec != b_sec:
                role = "consultant"            # itinerant: both ends outside, same group
            elif a_sec != b_sec and b_sec == c_sec:
                role = "gatekeeper"            # from outside, into B's own group
            elif a_sec == b_sec and c_sec != b_sec:
                role = "representative"        # from B's own group, out
            else:
                role = "liaison"               # all three groups different
            roles[role] += 1
            if role != "coordinator":
                spans.add(a_sec)
                spans.add(c_sec)
                if len(receipts) < 6:
                    receipts.append("%s(%s) --%s(%s)-- %s(%s) [%s]"
                                    % (a, a_sec, node, b_sec, c, c_sec, role))
    spans.discard(b_sec)
    return roles, spans, receipts


def detect_subject(graph_path, subject_id, confidence=0.9):
    """DetectionHits for one node's structural position. Empty list if it is unremarkable."""
    entities, edges = load_graph(graph_path)
    if subject_id not in entities:
        return []
    adj, _ = adjacency(entities, edges)

    def sector_of(nid):
        return (entities.get(nid) or {}).get("sector") or "unknown"

    bc = betweenness(adj)
    deg = {v: len(adj[v]) for v in adj}
    n = len(adj)

    def decile_cut(values):
        vals = sorted(values)
        if not vals:                  # pragma: no cover - unreachable while the subject exists
            # `adjacency()` seeds an entry for every entity, so this population is empty only
            # when the graph has no entities at all -- and the caller has already returned by
            # then, because the subject could not have been found in it. Kept as a guard
            # because indexing an empty list here would take down the whole graph lane.
            return 0.0
        return vals[min(int(DECILE * len(vals)), len(vals) - 1)]

    bc_cut = decile_cut(bc.values())
    deg_cut = decile_cut(deg.values())

    hits = []
    my_bc, my_deg = bc.get(subject_id, 0.0), deg.get(subject_id, 0)

    if my_bc > 0 and my_bc >= bc_cut:
        rank = 1 + sum(1 for v in bc.values() if v > my_bc)
        hits.append(DetectionHit(
            detection_id="high-betweenness", confidence=confidence,
            span="betweenness %.4f, rank %d of %d nodes (top-decile cut %.4f)"
                 % (my_bc, rank, n, bc_cut),
            char_start=0, char_end=0,
            rationale="Brandes exact betweenness over the undirected link layer. POSITION "
                      "ONLY: being on the shortest paths is not a claim that anything is "
                      "brokered, coordinated or controlled."))

    if my_deg > 0 and my_deg >= deg_cut:
        rank = 1 + sum(1 for v in deg.values() if v > my_deg)
        hits.append(DetectionHit(
            detection_id="hub-degree", confidence=confidence,
            span="degree %d, centrality %.4f, rank %d of %d nodes (top-decile cut %d)"
                 % (my_deg, (my_deg / (n - 1)) if n > 1 else 0.0, rank, n, deg_cut),
            char_start=0, char_end=0,
            rationale="Direct ties only. Says nothing about what flows across them or who "
                      "chose them."))

    roles, spans, receipts = gf_roles(adj, sector_of, subject_id)
    cross = sum(roles[r] for r in CROSS_GROUP_ROLES)
    if cross and len(spans) >= 2:
        summary = ", ".join("%s:%d" % (r, roles[r]) for r in CROSS_GROUP_ROLES if roles[r])
        hits.append(DetectionHit(
            detection_id="cross-group-broker", confidence=confidence,
            span="GF roles %s across sectors %s | %s"
                 % (summary, "+".join(sorted(spans)), " ; ".join(receipts)),
            char_start=0, char_end=0,
            rationale="Gould-Fernandez (1989) triad census on open triads, sector as the "
                      "group attribute. A node POSITIONED to broker is not a node shown to "
                      "broker."))
    return hits


def graph_report(graph_path, top=10):
    """Whole-graph ranking, for checking computed gold against the shipped graph."""
    entities, edges = load_graph(graph_path)
    adj, dropped = adjacency(entities, edges)
    bc = betweenness(adj)
    deg = {v: len(adj[v]) for v in adj}
    rows = []
    for nid in adj:
        rows.append({"id": nid,
                     "name": (entities.get(nid) or {}).get("name") or nid,
                     "sector": (entities.get(nid) or {}).get("sector") or "unknown",
                     "betweenness": round(bc[nid], 4),
                     "degree": deg[nid]})
    rows.sort(key=lambda r: (-r["betweenness"], -r["degree"]))
    return {"nodes": len(adj), "edges_used": sum(len(v) for v in adj.values()) // 2,
            "edges_dropped": dropped, "top": rows[:top], "all": rows}
