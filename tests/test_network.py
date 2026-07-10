"""Tests for the network_brokerage structural (graph) lens.

Runs against the REAL graph file shipped with the research site, so the exhibits are the actual
computed centralities (OpenAI, Anthropic, Frontier Model Forum the top bridges/hubs). Pure graph
math — no network, no LLM. Asserts betweenness is computed (a known bridge node scores above a
leaf), Gould-Fernandez roles classify, the lens loads via loader.load_lenses, and a low-degree leaf
stays incidental.

Run with `pytest` or directly: `python tests/test_network.py`.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tradecraft.network import (  # noqa: E402
    build_graph, betweenness_centrality, degree_centrality, brokerage_roles,
    subject_network_hits, score_subject, _classify,
)
from tradecraft.schema import DetectionHit  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# evil-robots-series/tradecraft/  ->  evil-robots-series/website/data/research-entities.json
SERIES_ROOT = os.path.dirname(REPO_ROOT)
GRAPH = os.path.join(SERIES_ROOT, "website", "data", "research-entities.json")
TAXONOMY = os.path.join(REPO_ROOT, "detectors", "network_brokerage", "taxonomy.yaml")


def _fired(hits, detection_id):
    return any(h.detection_id == detection_id for h in hits)


def _ids(hits):
    return sorted(h.detection_id for h in hits)


def test_graph_file_present():
    assert os.path.isfile(GRAPH), f"real graph not found at {GRAPH}"
    assert os.path.isfile(TAXONOMY), f"taxonomy not found at {TAXONOMY}"


def test_betweenness_is_computed_bridge_beats_leaf():
    """A known bridge node (OpenAI / Frontier Model Forum) scores far above a degree-1 leaf."""
    g = build_graph(GRAPH)
    bc = betweenness_centrality(g)
    # ONS is a documented degree-1 leaf (gov) — it sits on no shortest paths.
    assert g.degree("ONS") == 1
    assert bc["ONS"] == 0.0, bc["ONS"]
    # OpenAI is a high-degree, central bridge.
    assert bc["OpenAI"] > bc["ONS"]
    assert bc["OpenAI"] > 0.0
    # Frontier Model Forum is the computed top bridge in this graph.
    top = max(bc, key=bc.get)
    assert top == "FrontierModelForum", top


def test_betweenness_normalized_range():
    g = build_graph(GRAPH)
    bc = betweenness_centrality(g, normalized=True)
    assert all(0.0 <= v <= 1.0 for v in bc.values())


def test_degree_centrality_openai_is_top_hub():
    g = build_graph(GRAPH)
    dc = degree_centrality(g)
    assert max(dc, key=dc.get) == "OpenAI", max(dc, key=dc.get)
    assert dc["OpenAI"] > dc["ONS"]


def test_gould_fernandez_roles_classify():
    """The five GF roles classify by group membership of the a-B-c triad."""
    assert _classify("tech", "tech", "tech") == "coordinator"     # all same group
    assert _classify("gov", "tech", "tech") == "gatekeeper"       # into B's group
    assert _classify("tech", "tech", "gov") == "representative"   # out of B's group
    assert _classify("tech", "gov", "tech") == "consultant"       # itinerant: a==c group, B outside
    assert _classify("gov", "tech", "academia") == "liaison"      # all three different


def test_brokerage_roles_present_for_central_node():
    g = build_graph(GRAPH)
    roles = brokerage_roles(g)
    # OpenAI bridges multiple sectors -> non-trivial cross-group brokerage role counts.
    assert "OpenAI" in roles
    cross = sum(roles["OpenAI"][r] for r in ("gatekeeper", "representative", "consultant", "liaison"))
    assert cross > 0, roles["OpenAI"]


def test_central_node_fires_all_three_markers():
    hits = subject_network_hits(GRAPH, "OpenAI")
    assert _fired(hits, "high-betweenness"), _ids(hits)
    assert _fired(hits, "hub-degree"), _ids(hits)
    assert _fired(hits, "cross-group-broker"), _ids(hits)
    # the receipt carries the bridged sectors
    assert any("bridges" in h.span or "brokers across" in h.span for h in hits), [h.span for h in hits]


def test_leaf_node_stays_incidental():
    """A degree-1 leaf produces no network-position signal -> index 0 -> incidental."""
    hits = subject_network_hits(GRAPH, "ONS")
    assert hits == [], _ids(hits)
    result = score_subject(GRAPH, "ONS", TAXONOMY)
    assert result.index == 0.0
    assert result.tier == "incidental"
    assert result.markers_present == []


def test_grader_returns_module_result_with_receipts():
    """The grader runs on the network hits and keeps the structural spans as receipts."""
    result = score_subject(GRAPH, "OpenAI", TAXONOMY)
    assert result.lens_id == "network_brokerage"
    assert 0.0 <= result.index <= 100.0
    assert result.receipts, "expected the structural DetectionHits to be carried through"
    assert all(isinstance(h, DetectionHit) for h in result.receipts)
    # OpenAI should land at least 'notable' given three co-occurring markers.
    assert result.index >= 35.0, result.index
    assert "high_betweenness" in result.markers_present
    assert "cross_group_brokerage" in result.markers_present


def test_loader_loads_the_lens():
    """The new lens loads via loader.load_lenses alongside the others."""
    from tradecraft.loader import load_lenses
    lenses = load_lenses(os.path.join(REPO_ROOT, "detectors"))
    assert "network_brokerage" in lenses
    tax = lenses["network_brokerage"]
    assert tax.config.w_density == 0.0
    assert {m.id for m in tax.markers} == {
        "high_betweenness", "hub_degree", "cross_group_brokerage",
    }


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"\n{len(fns)} passed")
