"""The embedding find stage's stdlib-only half: windowing and anchor collection.

WHY ONLY HALF, AND WHY THAT IS STATED HERE
------------------------------------------
`embed_find.py` deliberately imports numpy and sentence_transformers INSIDE its functions,
because `requirements.txt` promises that "core grader + tests need only the stdlib" and neither
package is in it. So the module imports fine in CI and most of it cannot run there: anything
touching `build_anchors`, `load_anchors`, `_score_windows`, `calibrate` or `detect_embed` needs
numpy present and a real or faked embedding model.

What IS reachable with the stdlib is the part where the measured bugs were, and both are
regression-tested below:

  windows() tracked offsets against the ORIGINAL string rather than recomputing them from the
  joined window -- the discipline detect_cues learned when lowercasing shifted every span after
  a Turkish dotted I.

  windows() reads WINDOW_SENTENCES and WINDOW_STRIDE from module globals INSIDE the body. A
  default argument binds once at definition time, so setting `embed_find.WINDOW_SENTENCES = 1`
  from outside silently did nothing, and a recalibration run "at 1 sentence" produced
  byte-identical 3-sentence thresholds. Only comparing the numbers caught it. That is exactly
  the class of defect a test must hold, because the run still succeeds and the output still
  looks like an answer.

Run with `pytest` or directly: `python tests/test_embed_find.py`.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tradecraft import embed_find as EF  # noqa: E402

THREE = ("The council normalised the schema. Officials said the patchwork was messy. "
         "A single standard will be recorded centrally.")


# ------------------------------------------------- windows(): offsets

def test_window_offsets_index_the_original_text():
    """A receipt quotes the document, so the offsets must resolve in the document."""
    for start, end, chunk in EF.windows(THREE, n=1, stride=1):
        assert THREE[start:end] == chunk, (start, end, chunk)


def test_window_offsets_survive_irregular_whitespace():
    text = "First one here.   Second one follows.\n\nThird arrives late."
    for start, end, chunk in EF.windows(text, n=1, stride=1):
        assert text[start:end] == chunk


def test_multi_sentence_window_spans_from_first_to_last():
    got = list(EF.windows(THREE, n=2, stride=1))
    start, end, chunk = got[0]
    assert chunk.startswith("The council")
    assert "patchwork" in chunk
    # The span covers both sentences in the original, so the receipt can be quoted whole.
    assert THREE[start:end].startswith("The council")
    assert "patchwork" in THREE[start:end]


# ------------------------------------------------- windows(): shape

def test_stride_controls_overlap():
    dense = list(EF.windows(THREE, n=2, stride=1))
    sparse = list(EF.windows(THREE, n=2, stride=2))
    assert len(dense) > len(sparse)


def test_window_larger_than_the_text_still_yields_one_window():
    """A short document must produce a window, not silently score nothing."""
    got = list(EF.windows("Only one sentence here.", n=5, stride=1))
    assert len(got) == 1
    assert "Only one sentence" in got[0][2]


def test_text_without_terminal_punctuation_still_windows():
    got = list(EF.windows("no full stop anywhere in this line", n=1, stride=1))
    assert len(got) == 1


def test_empty_text_yields_nothing_rather_than_an_empty_window():
    assert list(EF.windows("", n=1, stride=1)) == []


# ------------------------------------------------- the default-argument trap

def test_module_globals_are_read_at_call_time_not_bound_at_definition():
    """The measured bug: setting the module global must actually change the windowing.

    If these were signature defaults they would bind once at import and this test would see
    identical output for both settings -- which is precisely what a recalibration "at 1
    sentence" did while reporting 3-sentence thresholds.
    """
    old_n, old_stride = EF.WINDOW_SENTENCES, EF.WINDOW_STRIDE
    try:
        EF.WINDOW_SENTENCES, EF.WINDOW_STRIDE = 1, 1
        ones = list(EF.windows(THREE))
        EF.WINDOW_SENTENCES = 3
        threes = list(EF.windows(THREE))
        assert len(ones) != len(threes), (len(ones), len(threes))
        assert len(ones) == 3
    finally:
        EF.WINDOW_SENTENCES, EF.WINDOW_STRIDE = old_n, old_stride


# ------------------------------------------------- collect_anchors()

def test_collect_anchors_returns_definitions_and_gold_from_the_real_taxonomy():
    anchors = EF.collect_anchors()
    assert anchors, "no anchors collected from detectors/"
    kinds = {a.kind for a in anchors}
    assert kinds == {"definition", "gold"}, kinds
    # The stated premise of this module: the taxonomy's assets are its definitions and its
    # sourced exemplars, so both arms must be non-trivially populated.
    assert sum(1 for a in anchors if a.kind == "definition") > 50
    assert sum(1 for a in anchors if a.kind == "gold") > 50


def test_every_anchor_carries_its_lens_detection_and_text():
    for a in EF.collect_anchors():
        assert a.lens and a.detection and a.text.strip()


def test_gold_anchors_keep_their_source_receipt():
    """An embedding receipt reads "scores 0.71 against Webb 1923" -- so the source must survive."""
    gold = [a for a in EF.collect_anchors() if a.kind == "gold"]
    assert gold
    assert sum(1 for a in gold if a.source) > len(gold) // 2, (
        "most gold anchors lost their source attribution")


def test_collect_anchors_accepts_an_explicit_detectors_dir(tmp_path):
    """The seam that lets a caller point this at a fixture tree rather than the live taxonomy."""
    lens = tmp_path / "toy_lens"
    lens.mkdir()
    (lens / "taxonomy.yaml").write_text(
        "id: toy_lens\n"
        "name: Toy\n"
        "description: A fixture lens.\n"
        "reads: text\n"
        "cue_matching: supported\n"
        "markers:\n"
        "- id: toy_marker\n"
        "  name: Toy marker\n"
        "  base_weight: 1.0\n"
        "  detections:\n"
        "  - id: toy-detection\n"
        "    weight: 1.0\n"
        "    definition: A fixture definition that anchors nothing in particular.\n"
        "    cues:\n"
        "    - fixture phrase\n"
        "    gold:\n"
        "    - text: the fixture gold exemplar\n"
        "      source: illustrative fixture\n"
        "    - text: '   '\n"
        "      source: blank, must be skipped\n",
        encoding="utf-8")

    anchors = EF.collect_anchors(str(tmp_path))
    assert {a.kind for a in anchors} == {"definition", "gold"}
    # The whitespace-only gold entry contributes no anchor: an empty anchor would embed to
    # something, and that something would score against real documents.
    assert [a.text for a in anchors if a.kind == "gold"] == ["the fixture gold exemplar"]
    assert all(a.lens == "toy_lens" for a in anchors)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
