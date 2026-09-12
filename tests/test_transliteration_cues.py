"""T3.3 — how a transliteration pair must be declared, and why the obvious way is wrong.

THE TRAP, MEASURED
------------------
An idiom that exists in two scripts (`dar al-harb` / `دار الحرب`) can be declared two ways, and
they do not score the same. On one document containing the SAME idiom once in each script:

    one detection, one cue per script    index  86.50   intensity 0.550
    two sibling detections               index 100.00   intensity 1.000

The grader accumulates marker score per DETECTION -- `marker_scores[marker] += contribution`,
once per detection at its strongest hit. Two sibling detections therefore add twice for a
single idiom, inflating intensity and the index. The receipt is equally precise either way,
because a hit carries the matched span, so the split buys nothing and costs correctness.

`BACKLOG-shibboleth-corpus-study.md` T3.3 originally specified the wrong one -- "different cues
for the same idiom and should not be conflated in one detection." Corrected 2026-09-03 against
this measurement, before any non-Latin cue shipped. T3.1 landed the same day, which is what made
the trap live.

THE RULE, therefore: **one detection per idiom, one cue per script.** These tests hold it, so it
is enforced rather than merely written down.

Run with `pytest` or directly: `python tests/test_transliteration_cues.py`.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tradecraft.detect import detect_cues  # noqa: E402
from tradecraft.grader import grade_document_for_lens  # noqa: E402
from tradecraft.schema import Detection, GradingConfig, Marker, Taxonomy  # noqa: E402

ARABIC = "دار الحرب"
LATIN = "dar al-harb"
BILINGUAL = ("They wrote of " + ARABIC + " and elsewhere of " + LATIN +
             ", the same idiom twice.")


def _tax(detections):
    return Taxonomy(id="t", name="t", description="d",
                    markers=[Marker(id="m", name="m", base_weight=1.0,
                                    detections=detections)],
                    config=GradingConfig())


ONE_DETECTION = _tax([Detection(id="idiom", weight=1.0,
                                definition="one idiom, two scripts",
                                cues=[LATIN, ARABIC])])
SIBLINGS = _tax([Detection(id="idiom-latin", weight=1.0, definition="transliterated",
                           cues=[LATIN]),
                 Detection(id="idiom-arabic", weight=1.0, definition="native script",
                           cues=[ARABIC])])


def _grade(tax, text=BILINGUAL):
    hits = detect_cues(text, tax)
    return hits, grade_document_for_lens(tax, hits, len(text.split()))


def test_both_scripts_are_found_either_way():
    """The split is not about recall: both declarations find both forms."""
    for tax in (ONE_DETECTION, SIBLINGS):
        hits, _ = _grade(tax)
        spans = {h.span for h in hits}
        assert LATIN in spans and ARABIC in spans, spans


def test_siblings_double_count_a_single_idiom():
    """The measured trap. Two detections add to the marker twice for one idiom."""
    _, one = _grade(ONE_DETECTION)
    _, split = _grade(SIBLINGS)
    assert split.intensity > one.intensity, (one.intensity, split.intensity)
    assert split.index > one.index, (one.index, split.index)


def test_one_detection_per_idiom_is_the_declared_rule():
    """Pins the numbers, so a future grader change that erases the difference is visible."""
    _, one = _grade(ONE_DETECTION)
    _, split = _grade(SIBLINGS)
    assert round(one.intensity, 3) == 0.55
    assert round(split.intensity, 3) == 1.0


def test_the_receipt_still_names_the_script_that_matched():
    """The only argument for splitting was receipt clarity, and it does not hold: the hit
    carries the matched span, so which script fired is visible without a separate detection."""
    hits, _ = _grade(ONE_DETECTION)
    assert {h.detection_id for h in hits} == {"idiom"}
    assert {h.span for h in hits} == {LATIN, ARABIC}


def test_a_monolingual_document_scores_the_same_under_either_declaration():
    """The inflation is specific to a document using BOTH forms, which is what makes it easy
    to miss: every single-script corpus scores identically and nothing looks wrong."""
    for text in ("They wrote of " + ARABIC + " only.", "They wrote of " + LATIN + " only."):
        _, one = _grade(ONE_DETECTION, text)
        _, split = _grade(SIBLINGS, text)
        assert round(one.index, 2) == round(split.index, 2), text


def test_no_shipped_taxonomy_splits_a_transliteration_pair():
    """The rule, enforced against the live taxonomies rather than only against fixtures.

    A pair is flagged when two detections in the SAME marker have cue sets in different
    scripts and neither shares a cue -- the shape a transliteration split takes.
    """
    from tradecraft.loader import load_lenses
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    offenders = []
    for lens_id, tax in sorted(load_lenses(os.path.join(root, "detectors")).items()):
        for marker in tax.markers:
            def scripts_of(det):
                out = set()
                for cue in det.cues:
                    for ch in cue:
                        if ch.isalpha():
                            out.add("latin" if ch.isascii() else "non-latin")
                return out
            for i, a in enumerate(marker.detections):
                for b in marker.detections[i + 1:]:
                    sa, sb = scripts_of(a), scripts_of(b)
                    if sa and sb and sa.isdisjoint(sb):
                        offenders.append("%s/%s: %s vs %s"
                                         % (lens_id, marker.id, a.id, b.id))
    assert not offenders, (
        "detections in one marker split across scripts -- declare one detection per idiom "
        "with one cue per script, or a bilingual document double-counts it: %s" % offenders)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
