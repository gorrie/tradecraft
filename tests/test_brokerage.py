"""network_brokerage, the lens that had no code: Brandes, degree, Gould-Fernandez.

It shipped as a taxonomy with three detections and six gold entries quoting computed figures,
and nothing in the repository could fire it -- `structural.py` implements the eight
`revolving_door` detections and does not mention this lens. The numbers in its gold had been
computed outside the tree.

The verification that matters is at the bottom: Anthropic's Gould-Fernandez census reproduces
the lens's own gold EXACTLY, and it is the one gold node whose degree did not change as the
graph grew from 172 to 182 nodes. The others moved precisely where the graph gained an edge.

Run with `pytest` or directly: `python tests/test_brokerage.py`.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tradecraft.brokerage import (  # noqa: E402
    adjacency, betweenness, detect_subject, gf_roles, graph_report, load_graph,
)
from tradecraft.structural import score_subject  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRAPH = os.path.join(REPO_ROOT, "data", "research-entities.json")
TAXONOMY = os.path.join(REPO_ROOT, "detectors", "network_brokerage", "taxonomy.yaml")


def _by_name():
    ents, _ = load_graph(GRAPH)
    return {(e.get("name") or "").lower(): i for i, e in ents.items()}


def test_graph_loads_with_no_dangling_edges():
    ents, edges = load_graph(GRAPH)
    _, dropped = adjacency(ents, edges)
    assert dropped == 0, "%d edge(s) reference an id not in entities" % dropped


def test_betweenness_of_a_path_graph_is_exact():
    """A--B--C: B is on the only a-c path, so normalised betweenness is 1.0."""
    adj = {"A": {"B"}, "B": {"A", "C"}, "C": {"B"}}
    bc = betweenness(adj)
    assert abs(bc["B"] - 1.0) < 1e-9
    assert abs(bc["A"]) < 1e-9 and abs(bc["C"]) < 1e-9


def test_betweenness_of_a_triangle_is_zero():
    """Every pair is directly tied, so nobody sits between anybody."""
    adj = {"A": {"B", "C"}, "B": {"A", "C"}, "C": {"A", "B"}}
    for v, val in betweenness(adj).items():
        assert abs(val) < 1e-9, v


def test_closed_triads_are_not_brokerage():
    """If the two ends are tied to each other, the middle brokers nothing."""
    adj = {"a": {"B", "c"}, "B": {"a", "c"}, "c": {"a", "B"}}
    roles, spans, _ = gf_roles(adj, lambda n: "same", "B")
    assert sum(roles.values()) == 0
    assert spans == set()


def test_liaison_needs_three_distinct_groups():
    adj = {"a": {"B"}, "B": {"a", "c"}, "c": {"B"}}
    sectors = {"a": "gov", "B": "tech", "c": "tank"}
    roles, spans, _ = gf_roles(adj, lambda n: sectors[n], "B")
    assert roles["liaison"] == 2          # ordered pairs: (a,c) and (c,a)
    assert spans == {"gov", "tank"}


def test_gatekeeper_and_representative_are_equal_by_construction():
    """The ordered-pair convention, which is what the gold was computed under.

    A triad a--B--c with a outside B's group and c inside it is a gatekeeper role read one
    way and a representative role read the other. An implementation that counts unordered
    pairs produces exactly half of each and does not reproduce the gold.
    """
    adj = {"a": {"B"}, "B": {"a", "c"}, "c": {"B"}}
    sectors = {"a": "gov", "B": "tech", "c": "tech"}
    roles, _, _ = gf_roles(adj, lambda n: sectors[n], "B")
    assert roles["gatekeeper"] == roles["representative"] == 1


def test_the_three_detections_fire_on_the_real_graph():
    """The whole point: this lens could not fire at all before brokerage.py existed."""
    hits = detect_subject(GRAPH, _by_name()["anthropic"])
    assert {h.detection_id for h in hits} == {
        "high-betweenness", "hub-degree", "cross-group-broker"}


def test_receipts_are_present_and_name_the_bridges():
    hits = {h.detection_id: h for h in detect_subject(GRAPH, _by_name()["anthropic"])}
    assert "rank" in hits["high-betweenness"].span
    assert "GF roles" in hits["cross-group-broker"].span
    assert "--" in hits["cross-group-broker"].span, "no bridging triad in the receipt"


def test_an_unremarkable_node_fires_nothing():
    ents, _ = load_graph(GRAPH)
    report = graph_report(GRAPH)
    quiet = [r for r in report["all"] if r["degree"] <= 1 and r["betweenness"] == 0.0]
    assert quiet, "no low-position node in the graph to test against"
    assert detect_subject(GRAPH, quiet[0]["id"]) == []


def test_scores_through_the_grader():
    r = score_subject(GRAPH, _by_name()["anthropic"], TAXONOMY)
    assert r.lens_id == "network_brokerage"
    assert r.index > 0 and r.receipts


def test_ranks_reproduce_the_gold_ordering():
    """Gold names Frontier Model Forum the top bridge and OpenAI the top-degree node."""
    report = graph_report(GRAPH, top=3)
    assert report["top"][0]["name"] == "Frontier Model Forum"
    by_degree = sorted(report["all"], key=lambda r: -r["degree"])
    assert by_degree[0]["name"] == "OpenAI"
    assert by_degree[1]["name"] == "Anthropic"


def test_anthropic_gf_census_reproduces_the_gold_exactly():
    """The verification this module exists to make possible.

    The lens's gold states: "Anthropic (tech) brokers across academia, gov, and tank -- GF
    roles coordinator:84, gatekeeper:29, representative:29, liaison:6". Computed here, from
    the shipped graph, independently of whatever produced that line.

    It holds to the digit -- and Anthropic is the one gold node whose degree (13) did not
    change as the graph grew from 172 to 182 nodes. OpenAI's degree went 17 -> 18 and its
    liaison count moved 30 -> 46; Frontier Model Forum's went 10 -> 11 and its betweenness
    moved. The figures that should have moved moved, and the one that should not did not.
    """
    ents, edges = load_graph(GRAPH)
    adj, _ = adjacency(ents, edges)
    sector_of = lambda nid: (ents.get(nid) or {}).get("sector") or "unknown"  # noqa: E731
    roles, spans, _ = gf_roles(adj, sector_of, _by_name()["anthropic"])
    assert roles["coordinator"] == 84
    assert roles["gatekeeper"] == 29
    assert roles["representative"] == 29
    assert roles["liaison"] == 6
    assert spans == {"academia", "gov", "tank"}


if __name__ == "__main__":
    raise SystemExit(pytest.main([os.path.abspath(__file__), "-q"]))
