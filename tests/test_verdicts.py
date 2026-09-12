"""The verdict cache's safety properties, which are all about REFUSING stale answers.

The cache exists so a nondeterministic model pass can sit behind a determinism gate. That
only works if it invalidates correctly. A cache that quietly serves a verdict taken under a
different prompt, or a different context window, is worse than no cache: it launders an
answer to one question into evidence for another, and nothing downstream can tell.
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tradecraft import verdicts as vc  # noqa: E402


def test_key_depends_on_every_input():
    base = ("lens_a", "det_a", "span", "window text")
    k = vc.key_for(*base)
    assert k != vc.key_for("lens_b", "det_a", "span", "window text")
    assert k != vc.key_for("lens_a", "det_b", "span", "window text")
    assert k != vc.key_for("lens_a", "det_a", "spun", "window text")
    # The window is the point: an edit to the surrounding paragraph changes the text the
    # model read, so the old verdict no longer describes anything that exists.
    assert k != vc.key_for("lens_a", "det_a", "span", "window text, edited")


def test_key_is_stable_across_runs():
    a = vc.key_for("l", "d", "s", "w")
    b = vc.key_for("l", "d", "s", "w")
    assert a == b and len(a) == 20


def test_window_is_paragraph_snapped_and_bounded():
    text = "alpha para.\n\nbeta HIT gamma.\n\ndelta para."
    start = text.index("HIT")
    win = vc.context_window(text, start, "HIT")
    assert "HIT" in win
    # snapped outward to paragraph edges, not opened mid-sentence
    assert win.startswith("beta") and win.endswith("gamma.")


def test_window_handles_a_hit_with_no_offset():
    # detect() can return char_start=None; the window must still be deterministic
    # rather than raising inside a 40-minute batch run.
    text = "x" * 9000
    assert vc.context_window(text, None, "x") == text[:vc.WINDOW_CHARS * 2]


def test_roundtrip(tmp_path):
    p = tmp_path / "v.json"
    vc.save(p, {"k1": {"verdict": "genuine"}})
    assert vc.load(p) == {"k1": {"verdict": "genuine"}}


def test_missing_file_is_an_empty_cache(tmp_path):
    assert vc.load(tmp_path / "nope.json") == {}


@pytest.mark.parametrize("field,bad", [("schema", 999), ("window_chars", 12)])
def test_cache_refuses_itself_when_a_global_input_changed(tmp_path, field, bad):
    """Schema and window size change the meaning of EVERY entry, so the whole file goes."""
    p = tmp_path / "v.json"
    vc.save(p, {"k1": {"verdict": "genuine"}})
    blob = json.loads(p.read_text(encoding="utf-8"))
    assert blob[field] != bad
    blob[field] = bad
    p.write_text(json.dumps(blob), encoding="utf-8")
    assert vc.load(p) == {}


def test_mode_changes_the_key():
    """"Is the author doing this" and "is this an instance of the technique" are different
    questions and get different answers on the same span -- so they must not collide. They
    did not, but only because nothing had two modes until now."""
    assert vc.key_for("l", "d", "s", "w", "author") != vc.key_for("l", "d", "s", "w", "instance")


def test_prompt_version_is_inside_the_key(monkeypatch):
    """Stronger than the old whole-file check it replaces: a prompt bump must miss that
    mode's entries specifically. Whole-file invalidation would also throw away the OTHER
    mode's verdicts, which are correct and cost tens of minutes -- and the pressure to
    avoid paying that twice is exactly how a stale-prompt cache gets kept."""
    before = vc.key_for("l", "d", "s", "w", "author")
    bumped = dict(vc.VERIFY_PROMPT_VERSION)
    bumped["author"] += 1
    monkeypatch.setattr(vc, "VERIFY_PROMPT_VERSION", bumped)
    assert vc.key_for("l", "d", "s", "w", "author") != before
    # ...and the untouched mode keeps its keys, so its cache survives.
    monkeypatch.undo()
    unchanged = vc.key_for("l", "d", "s", "w", "instance")
    monkeypatch.setattr(vc, "VERIFY_PROMPT_VERSION", bumped)
    assert vc.key_for("l", "d", "s", "w", "instance") == unchanged


def test_every_declared_mode_is_keyable():
    from tradecraft.detect import VERIFY_MODES
    keys = {m: vc.key_for("l", "d", "s", "w", m) for m in VERIFY_MODES}
    assert len(set(keys.values())) == len(VERIFY_MODES), keys


def test_saved_cache_records_what_produced_it(tmp_path):
    p = tmp_path / "v.json"
    vc.save(p, {})
    blob = json.loads(p.read_text(encoding="utf-8"))
    for k in ("schema", "prompt_versions", "window_chars", "note"):
        assert k in blob, f"cache must record {k} so a human can see what produced it"
    # prompt_versions is a RECORD, not the enforcement point -- the key enforces it. Assert
    # it covers every mode, or a new mode could ship with nothing tracking its prompt.
    from tradecraft.detect import VERIFY_MODES
    assert set(blob["prompt_versions"]) == set(VERIFY_MODES)


def test_saved_verdicts_are_sorted(tmp_path):
    """Committed file: unstable key order would show up as a diff on every run and make
    a real change impossible to review."""
    p = tmp_path / "v.json"
    vc.save(p, {"zz": {"verdict": "genuine"}, "aa": {"verdict": "incidental"}})
    keys = list(json.loads(p.read_text(encoding="utf-8"))["verdicts"])
    assert keys == sorted(keys)
