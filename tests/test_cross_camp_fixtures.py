"""`forbid_markers`: the cross-camp assertion the fixture format could not previously make.

WHY IT EXISTS
-------------
The shibboleth study requires, for every camp, that its cues stay quiet on the OTHER camps'
primary works -- "a shibboleth must identify ITS discourse, not activist-speak generally".

That assertion was unmakeable. Fixtures carried a lens-level `should_fire`, so the cross-camp
negative for the Marxist-Leninist camp -- the *Communist Manifesto*, which must not fire
`tankie_mlm` -- had to claim the whole `subculture_register` lens stays quiet on it. It does
not, and should not: the passage fires `revolutionary_left`, and Marx is that camp's canon. The
fixture failed, correctly, and the fixture was the thing that was wrong.

`forbid_markers` says "the lens may fire, but these markers must not", counts separately
(`cross-camp quiet: n/n`) and is folded into the strict gate.

Run with `pytest` or directly: `python tests/test_cross_camp_fixtures.py`.
"""
import io
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tradecraft.detect import detect  # noqa: E402
from tradecraft.grader import grade_document_for_lens  # noqa: E402
from tradecraft.loader import load_lenses  # noqa: E402
from tradecraft import adapters  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES = os.path.join(REPO_ROOT, "eval", "fixtures.json")


def _fixtures():
    return json.load(io.open(FIXTURES, encoding="utf-8"))


def _markers(fx, lenses):
    tax = lenses[fx["lens"]]
    hits = detect(fx["text"], tax, backend="cues")
    mr = grade_document_for_lens(tax, hits, adapters.token_estimate(fx["text"]))
    return set(mr.markers_present)


def test_the_mechanism_is_actually_used():
    """Non-vacuity: a feature nothing exercises is a feature that silently rots."""
    using = [f for f in _fixtures() if f.get("forbid_markers")]
    assert using, "no fixture uses forbid_markers -- the cross-camp gate asserts nothing"


def test_every_forbidden_marker_stays_quiet():
    lenses = load_lenses(os.path.join(REPO_ROOT, "detectors"))
    for fx in _fixtures():
        forbidden = fx.get("forbid_markers") or []
        if not forbidden:
            continue
        present = _markers(fx, lenses)
        leaked = [m for m in forbidden if m in present]
        assert not leaked, "%s leaked %s (present: %s)" % (fx["id"], leaked, sorted(present))


def test_forbidden_markers_name_real_markers():
    """A typo in a forbid list is a gate that passes because it forbids nothing."""
    lenses = load_lenses(os.path.join(REPO_ROOT, "detectors"))
    for fx in _fixtures():
        tax = lenses[fx["lens"]]
        known = {m.id for m in tax.markers}
        for m in fx.get("forbid_markers") or []:
            assert m in known, "%s forbids unknown marker %r on lens %s" % (
                fx["id"], m, fx["lens"])


def test_the_classical_marxism_fixture_asserts_both_halves():
    """The case the mechanism was built for, pinned explicitly.

    Marx must fire revolutionary_left (he is its canon) and must NOT fire tankie_mlm (whose
    cues are all post-1883). Asserting only one half would miss the point of the fixture.
    """
    lenses = load_lenses(os.path.join(REPO_ROOT, "detectors"))
    fx = next(f for f in _fixtures() if f["id"] == "sub_neg_classical_marxism")
    present = _markers(fx, lenses)
    assert "revolutionary_left" in present, present
    assert "tankie_mlm" not in present, present


def test_the_leninist_cues_are_chronologically_impossible_in_marx():
    """The basis the three new cues were kept on, asserted against the real control text.

    Not "absent from our control" -- that is what excluded `dictatorship of the proletariat`.
    These three name things that postdate Marx's death in 1883, so no gap in a Marx corpus can
    put them there.
    """
    lenses = load_lenses(os.path.join(REPO_ROOT, "detectors"))
    tankie = next(m for m in lenses["subculture_register"].markers if m.id == "tankie_mlm")
    cues = {c.lower() for d in tankie.detections for c in d.cues}
    for cue in ("finance capital", "second international", "left communists"):
        assert cue in cues, cue

    fx = next(f for f in _fixtures() if f["id"] == "sub_neg_classical_marxism")
    marx = fx["text"].lower()
    for cue in ("finance capital", "second international", "left communists"):
        assert cue not in marx, cue


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
