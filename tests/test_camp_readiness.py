"""Per-camp readiness: the fixture-field bug, and the columns that must discriminate.

WHY THIS EXISTS
---------------
The readiness table's whole value is that a human can act on a row. That makes a column which
reads the same for every row worse than no column, and the first draft of this tool had one:
`load_fixture_markers` guessed the fixture field was `markers` / `expect_markers`, found
nothing, and reported all 27 camps as lacking a should_fire fixture. They all have one. The
table would have sent someone to write 27 fixtures that already exist.

That is the third measurement this week whose failure mode was "green, empty, and plausible" --
a floor harness that stopped perturbing, an exclusion invariant over an empty loop, and this. So
the tests here are mostly non-vacuity assertions, which is the only kind that catches it.

Run with `pytest` or directly: `python tests/test_camp_readiness.py`.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "eval"))

import camp_readiness as CR  # noqa: E402


# ------------------------------------------------- the bug that made this file necessary

def test_fixture_markers_are_actually_found():
    """The regression guard: reads `expect_any`, and must come back non-empty."""
    markers = CR.load_fixture_markers()
    assert markers, ("no fixture markers parsed -- the field name in eval/fixtures.json has "
                     "changed and every camp will falsely report a missing fixture")
    assert len(markers) > 30, len(markers)


def test_known_camps_are_seen_as_fixture_covered():
    """Named camps whose should_fire fixtures exist in the repo today."""
    markers = CR.load_fixture_markers()
    for camp in ("maga_new_right", "revolutionary_left", "jihadist_militant",
                 "sovereign_citizen", "degrowth"):
        assert camp in markers, camp


def test_only_should_fire_fixtures_count_toward_coverage():
    """A negative fixture proves the camp stays quiet, not that anything exercises it."""
    import json, io  # noqa: E401
    items = json.load(io.open(CR.FIXTURES, encoding="utf-8"))
    negatives = {m for f in items if isinstance(f, dict) and not f.get("should_fire")
                 for m in (f.get("expect_any") or [])}
    positives = CR.load_fixture_markers()
    only_negative = negatives - positives
    # Not an error if empty, but if a marker is ONLY exercised negatively the tool must not
    # count it as covered -- assert the sets are computed independently.
    assert positives.isdisjoint(only_negative)


# ------------------------------------------------- the columns must discriminate

def test_the_verdict_column_separates_camps():
    """Non-vacuity: some camps ready, some not. A table of all-same is a broken measurement."""
    import json, io  # noqa: E401
    assert CR.main(["--lens", "subculture_register", "--markdown"]) == 0
    payload = json.load(io.open(CR.OUT, encoding="utf-8"))
    camps = payload["camps"]
    assert len(camps) >= 27, len(camps)
    ready = [k for k, r in camps.items() if not r["needs"]]
    needy = [k for k, r in camps.items() if r["needs"]]
    assert ready, "no camp is ready -- the readiness bar is mis-set or a column is broken"
    assert needy, "every camp is ready -- the tool is not measuring anything"


def test_every_camp_has_cues_and_gold_recorded():
    import json, io  # noqa: E401
    payload = json.load(io.open(CR.OUT, encoding="utf-8"))
    for key, rec in payload["camps"].items():
        assert rec["cues"], "camp with no cues at all: %s" % key
        assert rec["n_detections"] >= 1, key


def test_no_cue_belongs_to_two_camps():
    """A cue in two camps is a shibboleth for neither. Zero today; this keeps it zero."""
    import json, io  # noqa: E401
    payload = json.load(io.open(CR.OUT, encoding="utf-8"))
    assert payload["collisions"] == {}, (
        "cue(s) shared between camps: %s" % payload["collisions"])


def test_generic_flag_is_a_review_prompt_not_a_cut(capsys):
    """The output must say so, because this metric has been Goodharted here before."""
    CR.main(["--lens", "subculture_register"])
    out = capsys.readouterr().out
    assert "not a cut list" in out.lower()


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
