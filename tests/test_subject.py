"""Tests for the texts-by-person lane (subject.py) and the deterministic cue backend.

These run fully OFFLINE — backend="cues", no API key, no Ollama — against the REAL text lenses
shipped in detectors/. They assert the three load-bearing contracts:

  * the cue backend fires the right detections on literal cue phrases,
  * the graph lenses (revolving_door, network_brokerage) are excluded from the text lane,
  * grading is PER LENS and aggregated PER SUBJECT — never blended into one score.

Run with `pytest` or directly: `python tests/test_subject.py`.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tradecraft.loader import load_lenses  # noqa: E402
from tradecraft.detect import detect_cues  # noqa: E402
from tradecraft.subject import grade_person, grade_text, text_lenses, GRAPH_LENSES  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DETECTORS = os.path.join(REPO_ROOT, "detectors")

# A text stuffed with literal cue phrases from the inevitability_framing lens.
INEVITABILITY_TEXT = (
    "Let us be clear: there is no alternative. We must be on the right side of history, "
    "because the future is already here and resistance is futile. The train has left the station; "
    "those who refuse to adapt or die will simply be left behind by progress."
)


def _lenses():
    return load_lenses(DETECTORS)


def test_detectors_present():
    L = _lenses()
    assert "inevitability_framing" in L
    assert GRAPH_LENSES <= set(L), "expected the graph lenses to exist in detectors/"


def test_cue_backend_fires_on_literal_cues():
    tax = _lenses()["inevitability_framing"]
    hits = detect_cues(INEVITABILITY_TEXT, tax)
    fired = {h.detection_id for h in hits}
    assert "no-alternative" in fired, fired
    assert "historys-side" in fired, fired
    # spans + offsets are real receipts: the quoted span sits at its reported offset.
    for h in hits:
        assert h.char_start is not None and h.char_end is not None
        assert INEVITABILITY_TEXT[h.char_start:h.char_end] == h.span


def test_cue_backend_silent_on_clean_text():
    tax = _lenses()["inevitability_framing"]
    assert detect_cues("The weather was mild and the meeting adjourned early.", tax) == []


def test_text_lenses_excludes_graph_lenses():
    TL = text_lenses(_lenses())
    assert not (set(TL) & GRAPH_LENSES), "graph lenses must not be in the text lane"
    assert "adept_speech" in TL and "institutional_permeation" in TL


def test_grade_text_is_per_lens_never_blended():
    prof = grade_text(_lenses(), INEVITABILITY_TEXT, doc_id="t1", backend="cues")
    # one ModuleResult per TEXT lens, no graph lens, no single combined score.
    assert set(prof.lenses) == set(text_lenses(_lenses()))
    assert GRAPH_LENSES.isdisjoint(prof.lenses)
    inev = prof.lenses["inevitability_framing"]
    assert inev.index > 0.0, "the inevitability lens should register on this text"
    assert inev.markers_present, "at least one marker should be present"


def test_grade_person_aggregates_per_subject():
    texts = [
        {"id": "doc-a", "text": INEVITABILITY_TEXT, "date": "2020-01-01"},
        {"id": "doc-b", "text": INEVITABILITY_TEXT, "date": "2024-01-01"},
        {"id": "doc-c", "text": "An unremarkable note about lunch.", "date": "2022-01-01"},
    ]
    profile, docs = grade_person(_lenses(), "TestSubject", texts, backend="cues")
    assert profile.subject == "TestSubject"
    assert profile.n_documents == 3
    assert len(docs) == 3
    # per-lens axes preserved on the aggregate; inevitability has signal.
    assert "inevitability_framing" in profile.per_lens
    assert profile.per_lens["inevitability_framing"]["max"] > 0.0
    # timeline is built from dated docs, in date order (escalation view).
    dates = [row["date"] for row in profile.timeline]
    assert dates == sorted(dates)
    # graph lenses never appear on a text-lane profile.
    assert GRAPH_LENSES.isdisjoint(profile.per_lens)


def test_grade_person_skips_empty_texts():
    texts = [{"id": "x", "text": "  "}, {"id": "y", "text": INEVITABILITY_TEXT}]
    profile, docs = grade_person(_lenses(), "S", texts, backend="cues")
    assert len(docs) == 1 and docs[0].doc_id == "y"


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
