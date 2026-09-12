"""Two harnesses, one file: neither may delete the other's floor.

`eval/graph_floor.py` measures `network_brokerage` and `eval/revolving_floor.py` measures
`revolving_door`, and they write the same `graph-floors.json`. They are separate harnesses
because their nulls are not interchangeable: brokerage reads an UNDIRECTED adjacency graph, so
flipping every edge must move the index by zero, while `revolving_door` is directional -- a
career move is an edge whose source is the subject -- so flipping turns a person's employment
history into their employers'. Giving one lens the other's floor would assert an invariant that
is false and then report the movement as noise.

The failure this pins is duller and was live for about ten minutes: `graph_floor.py` REPLACED
the file rather than updating its own key, so whichever harness ran last silently deleted the
other lens's floor, and `floors_contract.py` then reported that lens as having no graph floor
at all. A measured floor that vanishes on an unrelated re-run is worse than an unmeasured one.

Run with `pytest` or directly: `python tests/test_graph_floor_merge.py`.
"""
import io
import json
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FLOORS = os.path.join(ROOT, "eval", "graph-floors.json")
BROKERAGE = os.path.join(ROOT, "eval", "graph_floor.py")
REVOLVING = os.path.join(ROOT, "eval", "revolving_floor.py")


def _src(path):
    return io.open(path, encoding="utf-8").read()


def test_both_graph_lenses_have_a_recorded_floor():
    blob = json.load(io.open(FLOORS, encoding="utf-8"))
    lenses = blob.get("lenses", {})
    assert set(lenses) >= {"network_brokerage", "revolving_door"}, sorted(lenses)


def test_neither_harness_replaces_the_lenses_block():
    """Both must merge. A bare assignment to blob["lenses"] is the regression."""
    for path in (BROKERAGE, REVOLVING):
        src = _src(path)
        assert re.search(r'setdefault\(\s*"lenses"', src), (
            "%s must merge into the shared lenses block, not replace it"
            % os.path.basename(path))
        assert 'json.dump({"seed"' not in src, (
            "%s writes a fresh dict over the file, which deletes the other lens's floor"
            % os.path.basename(path))


def test_each_harness_declares_its_own_null():
    for lens_id, expect in (("network_brokerage", "edge-perturb"),
                            ("revolving_door", "edge-perturb")):
        blob = json.load(io.open(FLOORS, encoding="utf-8"))
        assert blob["lenses"][lens_id]["null"] == expect


def test_revolving_door_does_not_test_edge_flipping():
    """The distinction that justifies a second harness, asserted in the source.

    Flipping is an invariant for brokerage and a change of MEANING for revolving_door, so the
    directional lens must not inherit that perturbation.
    """
    src = _src(REVOLVING)
    names = re.findall(r'\(\s*"([a-z-]+)"\s*,\s*\w+\s*,\s*(?:True|False)\s*\)', src)
    assert "shuffle-edges" in names, names
    assert "flip-edges" not in names, (
        "revolving_door is directional; flipping its edges changes the meaning rather than "
        "testing an invariant")


def test_a_degenerate_null_records_no_mde():
    """Same rule as every other floor here: the search step is not a resolution."""
    blob = json.load(io.open(FLOORS, encoding="utf-8"))
    for lens_id, rec in blob["lenses"].items():
        if rec.get("mde") is None:
            assert rec.get("mde_note"), (
                "%s has no MDE and no reason recorded" % lens_id)
        else:
            assert rec["mde"] > 0, lens_id


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
