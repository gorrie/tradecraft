"""PTC task-2 technique coverage: the label loader, and the counting rule that is easy to get wrong.

WHY THIS MATTERS
----------------
Technique coverage answers "which human-named techniques can this detector catch at all", and
it is reported as a percentage, which means an off-by-one counting rule produces a plausible
number rather than a crash.

The rule: coverage counts SPANS, not hits. Two detections landing on one annotated span is one
technique instance caught, not two. Counting hits would let a heavily-cued technique report
coverage above 100% -- a figure nobody would publish, arriving in a column everybody would.

The loader matters for the same reason the background-rate role manifest does. When the label
files are absent it must report unavailable, not zero: a zero-coverage table reads as "we catch
none of them", which is a finding, and it would be a fabricated one.

Run with `pytest` or directly: `python tests/test_census_techniques.py`.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "eval"))

import detection_census as DC  # noqa: E402


def test_techniques_at_returns_overlapping_names_only():
    spans = [("Loaded_Language", 10, 20), ("Doubt", 50, 60), ("Slogans", 15, 25)]
    assert DC.techniques_at(spans, 12, 18) == ["Loaded_Language", "Slogans"]
    assert DC.techniques_at(spans, 55, 58) == ["Doubt"]
    assert DC.techniques_at(spans, 30, 40) == []


def test_techniques_at_is_half_open_like_covered():
    """[a,b) touching a span's start boundary does not overlap it, matching covered()."""
    spans = [("Doubt", 20, 30)]
    assert DC.techniques_at(spans, 10, 20) == []
    assert DC.techniques_at(spans, 30, 40) == []
    assert DC.techniques_at(spans, 19, 21) == ["Doubt"]


def test_techniques_at_deduplicates_repeated_technique():
    """One technique annotated twice inside one hit is that technique once, not twice."""
    spans = [("Repetition", 10, 20), ("Repetition", 18, 28)]
    assert DC.techniques_at(spans, 12, 25) == ["Repetition"]


@pytest.mark.skipif(not os.path.exists(DC.TECH_LABELS) and not os.path.isdir(DC.TECH_LABELS_DIR),
                    reason="PTC task-2 labels not vendored in this checkout")
def test_task2_labels_load_and_are_well_formed():
    tech = DC.load_techniques()
    assert tech, "task-2 labels present on disk but nothing parsed"
    names, spans = set(), 0
    for aid, entries in tech.items():
        assert aid.isdigit(), aid
        for name, start, end in entries:
            assert end > start, (aid, name, start, end)
            names.add(name)
            spans += 1
    # The published PTC task-2 set: 14 technique classes after the merged labels.
    assert len(names) == 14, sorted(names)
    assert spans > 6000, spans


@pytest.mark.skipif(not os.path.exists(DC.TECH_LABELS) and not os.path.isdir(DC.TECH_LABELS_DIR),
                    reason="PTC task-2 labels not vendored in this checkout")
def test_every_labelled_article_id_is_reachable_as_a_filename():
    """A label keyed to an article we cannot open is a silently uncounted span."""
    tech = DC.load_techniques()
    missing = [aid for aid in list(tech)[:40]
               if not os.path.exists(os.path.join(DC.ARTICLES, "article%s.txt" % aid))]
    assert not missing, missing


def test_load_techniques_returns_empty_when_labels_absent(monkeypatch):
    """Absent labels must be reportable as unavailable, never as zero coverage."""
    monkeypatch.setattr(DC, "TECH_LABELS", os.path.join("nope", "missing.labels"))
    monkeypatch.setattr(DC, "TECH_LABELS_DIR", os.path.join("nope", "missing-dir"))
    assert DC.load_techniques() == {}


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
