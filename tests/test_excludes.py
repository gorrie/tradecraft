"""Cue exclusions: they must suppress boilerplate and must not cost a real firing.

An exclusion is the only mechanism in this repository that can make a lens fire LESS. That
makes it the only mechanism whose misuse is invisible in a precision sweep -- a lens that has
quietly stopped detecting things looks exactly like a lens with good precision. So it is
tested from both ends: the boilerplate it was added for stops firing, and the move the cue
exists for still fires.

The three real cases below are the ones measured on 2026-09-01, with their sources.

Run with `pytest` or directly: `python tests/test_excludes.py`.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tradecraft.detect import detect_cues, _suppressed, EXCLUDE_WINDOW  # noqa: E402
from tradecraft.loader import load_lenses  # noqa: E402
from tradecraft.schema import Detection  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LENSES = load_lenses(os.path.join(REPO_ROOT, "detectors"))

# Executive Order 12988's mandatory paragraph. Present in a large share of US rulemakings,
# which is why the cue "eliminate ambiguity" was scoring nearly every federal rule.
EO_12988 = ("Executive Order 12988 (Civil Justice Reform): This rulemaking meets applicable "
            "standards to minimize litigation, eliminate ambiguity, and reduce burden as set "
            "forth in sections 3(a) and 3(b)(2) of the Executive Order.")

# The same words doing the work the marker was written for.
REAL_LEGIBILITY = ("The council argued the local patchwork was indefensible and that we must "
                   "eliminate ambiguity between parishes once and for all.")


def fired(lens_id, text):
    return {h.detection_id for h in detect_cues(text, LENSES[lens_id])}


def test_eo_12988_boilerplate_does_not_fire_legibility():
    assert "erase-local-knowledge" not in fired("legibility", EO_12988)


def test_the_same_cue_still_fires_on_argument():
    assert "erase-local-knowledge" in fired("legibility", REAL_LEGIBILITY)


def test_exclusion_is_match_local_not_document_level():
    """Boilerplate in one paragraph must not silence a real instance in another.

    A document-level exclusion would have been simpler and wrong: rulemakings carry the
    EO 12988 paragraph as a matter of course, so any genuine standardisation argument in the
    same document would have been suppressed along with it.
    """
    both = EO_12988 + (" " * (EXCLUDE_WINDOW + 50)) + REAL_LEGIBILITY
    assert "erase-local-knowledge" in fired("legibility", both)


def test_proprietary_narrowing_rejects_the_routine_legal_term():
    routine = ("CBP is required to promulgate regulations that protect the privacy of "
               "business proprietary and any other confidential cargo information.")
    assert "attribution-gap" not in fired("institutional_permeation", routine)


def test_proprietary_narrowing_keeps_the_decision_machinery():
    real = ("The score came from a proprietary model and there is no record of who set "
            "the threshold.")
    assert "attribution-gap" in fired("institutional_permeation", real)


def test_spread_across_narrowing_rejects_geography():
    geographic = ("The criminal gang has already spread across Denmark from its base in "
                  "Copenhagen and now looks to Sweden.")
    assert "hidden-or-deferred-cost" not in fired("institutional_permeation", geographic)


def test_spread_across_narrowing_keeps_diffuse_cost():
    cost = ("The cost is spread across every future taxpayer, so no one organizes "
            "against it.")
    assert "hidden-or-deferred-cost" in fired("institutional_permeation", cost)


def test_suppressed_is_inert_without_excludes():
    """A detection with no `excludes` must behave exactly as before this feature existed."""
    plain = Detection(id="x", weight=1.0, definition="d", cues=["anything"])
    assert _suppressed(plain, "anything at all", (0, 8)) is False


def test_excludes_can_only_suppress():
    """An exclusion must never CREATE a firing -- the mechanism is one-directional."""
    det = Detection(id="x", weight=1.0, definition="d", cues=["needle"],
                    excludes=["haystack"])
    assert _suppressed(det, "needle in a haystack", (0, 6)) is True
    assert _suppressed(det, "needle in a field", (0, 6)) is False


# ------------------------------------------------- the invariant that covers every exclusion

def test_no_detection_gold_is_suppressed_by_its_own_excludes():
    """A detection's own gold example must never be silenced by that detection's excludes.

    The three cases above are hand-checked pairs. This is the general form, and it is what
    makes an exclusion safe to add without re-deriving the whole eval suite: suppression may
    never be the reason a gold example fails to fire. A gold whose cue is simply absent is a
    separate matter and gold_check's business; here the cue matches and the exclusion must
    keep its hands off it.

    Added 2026-09-03 with the adept_speech and subculture_register exclusions, whose taxonomy
    comments claim exactly this property. A comment asserting an untested invariant is how the
    invariant stops being true, so the claim and the assertion arrive together.
    """
    import re

    offenders = []
    exercised = []
    for lens_id, tax in sorted(LENSES.items()):
        for marker in tax.markers:
            for det in marker.detections:
                if not getattr(det, "excludes", None):
                    continue
                for gold in getattr(det, "gold", None) or []:
                    text = getattr(gold, "text", None) or (
                        gold.get("text") if isinstance(gold, dict) else None)
                    if not text:
                        continue
                    matches = []
                    for cue in det.cues:
                        for m in re.finditer(re.escape(cue), text, re.IGNORECASE):
                            matches.append((m.start(), m.end()))
                    if not matches:
                        continue  # cue absent: gold_check's problem, not an exclusion's
                    exercised.append("%s/%s" % (lens_id, det.id))
                    if all(_suppressed(det, text, span) for span in matches):
                        offenders.append("%s/%s: %r" % (lens_id, det.id, text[:70]))

    # Non-vacuity, asserted rather than assumed. Gold is a list of DICTS, and the first draft
    # of this test read `gold.text`, exercised nothing, and passed -- a green check over an
    # empty loop, which is the same failure shape as a floor harness that has stopped
    # perturbing. If a schema change empties this loop again, this line fails instead of
    # quietly blessing every exclusion in the repository.
    assert len(exercised) >= 4, (
        "invariant exercised only %d gold example(s) -- it is not actually checking anything; "
        "covered: %s" % (len(exercised), sorted(set(exercised))))
    assert not offenders, (
        "exclusion(s) suppress their own detection's gold example -- the exclusion is too "
        "broad, or the gold needs replacing: %s" % offenders)


if __name__ == "__main__":
    import traceback
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("ok    %s" % name)
            except Exception:
                failures += 1
                print("FAIL  %s" % name)
                traceback.print_exc()
    raise SystemExit(1 if failures else 0)
