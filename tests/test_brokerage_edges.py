"""Graph-lane edge paths: dropped edges, the Gould-Fernandez role census, unknown subjects.

`network_brokerage` scores topology rather than prose, so its failure modes leave no span to
inspect -- a silently dropped edge or a mis-assigned role just changes a number. The role census
in particular has a measured history: counting unordered pairs produced exactly half the figures
the lens's own gold quotes, and the tell was that gatekeeper and representative counts are equal
by construction under the ordered convention.

These are the branches no fixture graph currently reaches.

Run with `pytest` or directly: `python tests/test_brokerage_edges.py`.
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tradecraft import brokerage as B  # noqa: E402


def _graph(tmp_path, entities, edges):
    p = tmp_path / "g.json"
    p.write_text(json.dumps({"entities": entities, "edges": edges}), encoding="utf-8")
    return str(p)


def _sector_of(mapping):
    return lambda nid: mapping.get(nid, "unknown")


# ------------------------------------------------- edges that cannot be used

def test_edges_naming_unknown_entities_are_counted_as_dropped():
    """A dangling edge must be COUNTED, not silently ignored: it is the difference between a
    sparse graph and a broken export, and only the count distinguishes them."""
    entities = {"a": {"id": "a", "sector": "gov"}, "b": {"id": "b", "sector": "industry"}}
    adj, dropped = B.adjacency(entities, [
        {"source": "a", "target": "b"},
        {"source": "a", "target": "ghost"},
        {"source": "nobody", "target": "either"},
    ])
    assert dropped == 2
    assert adj["a"] == {"b"} and adj["b"] == {"a"}


# ------------------------------------------------- the role census

def test_coordinator_when_all_three_share_a_sector():
    adj = {"a": {"b"}, "b": {"a", "c"}, "c": {"b"}}
    roles, _spans, _r = B.gf_roles(adj, _sector_of({"a": "gov", "b": "gov", "c": "gov"}), "b")
    assert roles["coordinator"] > 0
    assert roles["consultant"] == 0 and roles["gatekeeper"] == 0


def test_consultant_when_both_ends_share_a_sector_the_broker_lacks():
    """Itinerant broker: a and c inside one group, B outside it."""
    adj = {"a": {"b"}, "b": {"a", "c"}, "c": {"b"}}
    roles, _spans, _r = B.gf_roles(adj, _sector_of({"a": "gov", "b": "industry", "c": "gov"}), "b")
    assert roles["consultant"] > 0
    assert roles["coordinator"] == 0


def test_gatekeeper_and_representative_are_equal_by_construction():
    """The property that settled the ordered-pairs question, asserted rather than recalled.

    A triad a--B--c with a outside B's group and c inside it is a gatekeeper role read one way
    and a representative role read the other, so under the canonical ordered convention the two
    counts must match. If they ever diverge the census has silently reverted to unordered pairs
    and every figure it reports is half.
    """
    adj = {"a": {"b"}, "b": {"a", "c"}, "c": {"b"}}
    roles, _spans, _r = B.gf_roles(adj, _sector_of({"a": "gov", "b": "industry", "c": "industry"}), "b")
    assert roles["gatekeeper"] == roles["representative"]
    assert roles["gatekeeper"] > 0


def test_a_closed_triad_is_not_brokerage():
    """If a and c are tied to each other, B brokers nothing -- that distinction is the measure."""
    adj = {"a": {"b", "c"}, "b": {"a", "c"}, "c": {"a", "b"}}
    roles, _spans, receipts = B.gf_roles(adj, _sector_of({"a": "gov", "b": "gov", "c": "gov"}), "b")
    assert sum(roles.values()) == 0
    assert receipts == []


# ------------------------------------------------- subjects that are not in the graph

def test_an_unknown_subject_returns_nothing_rather_than_raising(tmp_path):
    """Asking about someone absent from the graph is an ordinary outcome -- a dossier subject
    who simply is not in it -- and must read as "nothing to say", not as an error."""
    path = _graph(tmp_path,
                  [{"id": "a", "sector": "gov"}, {"id": "b", "sector": "industry"}],
                  [{"source": "a", "target": "b"}])
    assert B.detect_subject(path, "not-in-this-graph") == []


def test_a_subject_present_but_with_no_usable_edges_scores_nothing(tmp_path):
    """A real state, not a contrived one: an entity seeded into the graph before any edge is
    known, or one whose every edge names a node absent from the export.

    Such a subject must score nothing and say so, rather than raising or reporting a position
    it does not have. (The decile guard inside detect_subject is NOT reached here -- adjacency
    seeds an entry per entity, so the population is never empty while the subject exists.)
    """
    path = _graph(tmp_path,
                  [{"id": "lonely", "sector": "gov"}, {"id": "b", "sector": "industry"}],
                  [{"source": "lonely", "target": "ghost-not-in-entities"}])
    assert B.detect_subject(path, "lonely") == []


def test_a_star_centre_is_detected_as_structurally_notable(tmp_path):
    """A node every path runs through is the case the lens exists for."""
    entities = [{"id": "hub", "sector": "gov"}] + [
        {"id": "s%d" % i, "sector": "industry"} for i in range(8)]
    edges = [{"source": "hub", "target": "s%d" % i} for i in range(8)]
    path = _graph(tmp_path, entities, edges)
    assert B.detect_subject(path, "hub")


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
