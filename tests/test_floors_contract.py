"""The shared floors contract: one record shape for every resolution object.

Four instruments measure "how small a difference can this see", in four shapes. Consumers --
the observatory digest, export_web, score.py, the paper's floor table -- each re-implemented
"what is this lens's resolution?" against whichever file they happened to read, which is how a
number reaches a page without the ruler that qualifies it.

The field that decides publication is `recomputable`: true only when a reader can rebuild the
corpus behind the number. A floor over material only we hold is internal calibration, and a
public surface prints an MDE only when it is true. Getting that backwards would publish a
figure nobody outside can check, on a project whose whole pitch is recompute-it-yourself.

Run with `pytest` or directly: `python tests/test_floors_contract.py`.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "eval"))

import floors_contract as FC  # noqa: E402

from tradecraft.loader import load_lenses  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _records():
    return FC.collect()


def test_records_exist_at_all():
    """Non-vacuity: an empty contract would report every consumer as satisfied."""
    assert len(_records()) > 10


def test_every_record_carries_every_contract_field():
    for r in _records():
        for field in FC.FIELDS:
            assert field in r, "%s missing %s" % (r.get("claim"), field)


def test_states_are_only_the_declared_ones():
    """`background_rate.py` writes `index-bearing`, which answers a different question and is
    normalised here. If an UNDECLARED name appears, a consumer will silently not match it.

    `series` was added 2026-09-06 for `ratchet_series`, which is an instrument rather than a
    lens: it counts one-way movements across an administrative series against a binomial null.
    It is a fourth state rather than a forced fit into `receipts-only`, which means something
    specific and different -- no index floor, publish the receipts. Both consumers of this
    field were checked when it was added: `export_web` matches claims against known lens ids
    so it never sees this record, and `leaderboard/score.py` now filters on
    `instrument == "lens"` rather than splitting every claim on whitespace."""
    states = {r["state"] for r in _records()}
    assert states <= {"index", "receipts-only", "graph", "series"}, states


def test_the_alias_actually_fires():
    """Guards the normalisation rather than assuming it: the raw file still says
    `index-bearing`, so if the mapping is dropped this test fails while the one above passes."""
    assert FC._STATE_ALIASES.get("index-bearing") == "index"
    raw = FC._load(FC.BACKGROUND) or {}
    raw_states = {r.get("state") for r in raw.get("floor_records", [])}
    assert "index-bearing" in raw_states, (
        "background-rates.json no longer uses the alias -- either it was renamed at source "
        "(delete the alias) or the file is stale")


def test_every_lens_has_at_least_one_resolution_record():
    lenses = set(load_lenses(os.path.join(REPO_ROOT, "detectors")))
    covered = set()
    for r in _records():
        for lens_id in lenses:
            if r["claim"].startswith(lens_id + " "):
                covered.add(lens_id)
    assert lenses <= covered, "lenses with no record: %s" % sorted(lenses - covered)


def test_recomputable_is_a_bool_never_a_guess():
    for r in _records():
        assert isinstance(r["recomputable"], bool), r["claim"]


def test_index_floors_are_not_marked_publishable():
    """The lens index floor is measured over corpus/, and 95 of those documents are vendored
    news text with no manifest and no fetcher. A reader cannot rebuild it, so these records
    must not claim recomputable -- that flag is what a public surface reads before printing
    an MDE.
    """
    for r in _records():
        if r["source"] == "eval/lens_floor.py":
            assert r["recomputable"] is False, r["claim"]


def test_check_mode_passes_on_the_current_tree(capsys):
    assert FC.main(["--check"]) == 0
    out = capsys.readouterr().out
    assert "resolution record" in out


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
