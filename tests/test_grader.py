"""Deterministic tests for the grader. No YAML, no API — pure math on an inline taxonomy.

Run with `pytest` or directly: `python tests/test_grader.py`.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tradecraft.schema import (  # noqa: E402
    Taxonomy, Marker, Detection, GradingConfig, DetectionHit,
)
from tradecraft.grader import (  # noqa: E402
    grade_document_for_lens, grade_document, grade_subject,
)


def build_tax() -> Taxonomy:
    return Taxonomy(
        id="test",
        name="Test Lens",
        description="fixture",
        markers=[
            Marker("m1", "Marker One", 1.0, [
                Detection("d1", 1.0, "def", ["a"]),
                Detection("d2", 0.8, "def", ["b"]),
            ]),
            Marker("m2", "Marker Two", 1.0, [Detection("d3", 1.0, "def", ["c"])]),
            Marker("m3", "Marker Three", 0.5, [Detection("d4", 1.0, "def", ["d"])]),
        ],
        config=GradingConfig(),
    )


def test_single_marker_is_incidental():
    tax = build_tax()
    r = grade_document_for_lens(tax, [DetectionHit("d1", 0.5, "a")], token_count=1000)
    assert r.markers_present == ["m1"]
    assert r.breadth == round(1 / 3, 4)
    assert r.tier == "incidental"
    assert r.index < 35.0


def test_all_markers_dense_maxes_out():
    tax = build_tax()
    hits = [DetectionHit("d1", 1.0, "a"), DetectionHit("d3", 1.0, "c"), DetectionHit("d4", 1.0, "d")]
    r = grade_document_for_lens(tax, hits, token_count=300)
    assert r.breadth == 1.0
    assert r.intensity == 1.0
    assert r.density == 1.0
    assert r.index == 100.0
    assert r.tier == "dense tradecraft (review)"


def test_marker_score_caps_at_one():
    tax = build_tax()
    hits = [DetectionHit("d1", 1.0, "a"), DetectionHit("d2", 1.0, "b")]  # 1.0 + 0.8 -> capped
    r = grade_document_for_lens(tax, hits, token_count=1000)
    assert r.marker_scores["m1"] == 1.0


def test_unknown_detection_is_ignored_not_fatal():
    tax = build_tax()
    r = grade_document_for_lens(tax, [DetectionHit("does-not-exist", 1.0, "x")], token_count=1000)
    assert r.index == 0.0
    assert r.markers_present == []


def test_breadth_dominates_intensity():
    """Two markers lightly beat one marker maxed — co-occurrence is the load-bearing signal."""
    tax = build_tax()
    one_maxed = grade_document_for_lens(tax, [DetectionHit("d1", 1.0, "a")], 1000)
    two_light = grade_document_for_lens(
        tax, [DetectionHit("d1", 0.4, "a"), DetectionHit("d3", 0.4, "c")], 1000)
    assert two_light.breadth > one_maxed.breadth
    assert two_light.index > one_maxed.index


def test_subject_timeline_trend_rising():
    tax = build_tax()
    lenses = {"test": tax}
    profiles = []
    # escalating signal across four dated documents
    plans = [("2020-01-01", []),
             ("2021-01-01", [DetectionHit("d1", 0.5, "a")]),
             ("2022-01-01", [DetectionHit("d1", 1.0, "a"), DetectionHit("d3", 1.0, "c")]),
             ("2023-01-01", [DetectionHit("d1", 1.0, "a"), DetectionHit("d3", 1.0, "c"),
                             DetectionHit("d4", 1.0, "d")])]
    for date, hits in plans:
        profiles.append(grade_document(lenses, {"test": hits}, 400, doc_id=date, date=date))
    sp = grade_subject(profiles, subject="Test Subject")
    assert sp.n_documents == 4
    assert sp.per_lens["test"]["trend"] == "rising"
    assert sp.per_lens["test"]["max"] >= sp.per_lens["test"]["mean"]
    assert len(sp.timeline) == 4


def test_profile_keeps_lenses_separate():
    """Two lenses run together must not blend into one index."""
    tax_a = build_tax()
    tax_b = Taxonomy("other", "Other", "fixture",
                     [Marker("x", "X", 1.0, [Detection("dx", 1.0, "def", [])])], GradingConfig())
    prof = grade_document(
        {"test": tax_a, "other": tax_b},
        {"test": [DetectionHit("d1", 1.0, "a")], "other": []},
        1000,
    )
    assert set(prof.lenses) == {"test", "other"}
    assert prof.lenses["other"].index == 0.0
    assert prof.lenses["test"].index > 0.0


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"\n{len(fns)} passed")
