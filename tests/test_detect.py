"""Offline tests for the curated gold examples and the shared local_llm transport.

No network: the cloud/local transport is monkeypatched, so this asserts the dispatch logic
(auto -> cloud, fall back to local on refusal) and the curated adept_speech gold without an
API key or a running Ollama. Pure loader + dispatch.

Run with `pytest` or directly: `python tests/test_detect.py`.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tradecraft.loader import load_lenses, load_taxonomy  # noqa: E402
from tradecraft import detect as detect_mod, local_llm  # noqa: E402
from tradecraft.detect import detect, build_user_prompt, _few_shot  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DETECTORS = os.path.join(REPO_ROOT, "detectors")
ADEPT = os.path.join(DETECTORS, "adept_speech", "taxonomy.yaml")

ADEPT_MARKERS = {
    "apophatic_framing", "secret_knowledge", "teleological_work", "esoteric_metaphor",
    "unnamed_authority", "experience_as_proof", "deliberate_incompleteness", "initiatory_address",
}

# A placeholder gold example is one still pointing at the un-curated corpus stub.
_PLACEHOLDER_MARK = "curate verbatim"


# ---- gold curation (the deliverable) ----

def test_adept_speech_loads_with_eight_marker_families():
    tax = load_taxonomy(ADEPT)
    assert tax.id == "adept_speech"
    assert {m.id for m in tax.markers} == ADEPT_MARKERS


def test_every_detection_has_curated_gold():
    """Each detection carries >=1 gold example, none of them the placeholder stub."""
    tax = load_taxonomy(ADEPT)
    for m in tax.markers:
        for d in m.detections:
            assert d.gold, f"{d.id} has no gold examples"
            for g in d.gold:
                text = (g.get("text") or "").strip()
                src = (g.get("source") or "").strip()
                assert text, f"{d.id} gold has empty text"
                assert src, f"{d.id} gold has empty source"
                assert _PLACEHOLDER_MARK not in src, f"{d.id} still has a placeholder gold source"
                # every curated example is sourced to a Hidden Fire chapter, tagged VERBATIM/BOOK
                assert "the-hidden-fire" in src, f"{d.id} gold not sourced to the corpus: {src!r}"
                assert ("[VERBATIM]" in src or "[BOOK]" in src), f"{d.id} gold untagged: {src!r}"


def test_all_eight_families_represented_in_gold():
    tax = load_taxonomy(ADEPT)
    families_with_gold = {m.id for m in tax.markers if any(d.gold for d in m.detections)}
    assert families_with_gold == ADEPT_MARKERS


def test_gold_feeds_the_few_shot_prompt():
    """The curated spans surface as worked examples in the LLM prompt (anti-under-firing)."""
    tax = load_taxonomy(ADEPT)
    fs = _few_shot(tax)
    assert "EXAMPLES" in fs
    # a known verbatim span and its detection id both appear
    assert "the dharma cannot be taught" in fs
    assert "ineffability-claim" in fs
    prompt = build_user_prompt(tax, "some document text")
    assert "EXAMPLES" in prompt


def test_other_text_lenses_also_carry_gold():
    """Sibling text lenses load and carry sourced gold (regression guard on the loader)."""
    lenses = load_lenses(DETECTORS)
    for lid in ("institutional_permeation", "cognitive_capture"):
        assert lid in lenses
        tax = lenses[lid]
        assert any(d.gold for m in tax.markers for d in m.detections)


# ---- shared local_llm transport (helper extraction) ----

def test_detect_reexports_refusal_and_models():
    assert detect_mod.RefusalError is local_llm.Refusal
    assert detect_mod.CLOUD_MODEL == local_llm.CLOUD_MODEL
    assert detect_mod.LOCAL_MODEL == local_llm.LOCAL_MODEL


def _hit_json(detection_id):
    return ('{"hits":[{"detection_id":"%s","confidence":0.9,"span":"x","rationale":"r"}]}'
            % detection_id)


def test_cloud_backend_routes_through_helper(monkeypatch):
    tax = load_taxonomy(ADEPT)
    calls = {}

    def fake_cloud(prompt, system, *, model, json_mode):
        calls["cloud"] = model
        return _hit_json("ineffability-claim")

    def fail_local(*a, **k):
        raise AssertionError("local must not be called for backend='cloud'")

    monkeypatch.setattr(local_llm, "cloud", fake_cloud)
    monkeypatch.setattr(local_llm, "local", fail_local)
    hits = detect("text with x", tax, backend="cloud")
    assert calls["cloud"] == local_llm.CLOUD_MODEL
    assert [h.detection_id for h in hits] == ["ineffability-claim"]


def test_auto_falls_back_to_local_on_refusal(monkeypatch):
    tax = load_taxonomy(ADEPT)
    seq = []

    def refusing_cloud(prompt, system, *, model, json_mode):
        seq.append("cloud")
        raise local_llm.Refusal("nope")

    def ok_local(prompt, system, *, model, json_mode):
        seq.append("local")
        return _hit_json("the-seeing")  # invalid id -> dropped, but proves local ran

    monkeypatch.setattr(local_llm, "cloud", refusing_cloud)
    monkeypatch.setattr(local_llm, "local", ok_local)
    hits = detect("text", tax, backend="auto")
    assert seq == ["cloud", "local"]            # tried cloud first, then fell back
    assert hits == []                            # unknown detection id is dropped, not fatal


def test_local_invalid_json_is_not_fatal(monkeypatch):
    tax = load_taxonomy(ADEPT)
    monkeypatch.setattr(local_llm, "local", lambda *a, **k: "I refuse to answer.")
    assert detect("text", tax, backend="local") == []


def test_unknown_backend_raises():
    tax = load_taxonomy(ADEPT)
    try:
        detect("text", tax, backend="telepathy")
        assert False, "expected ValueError"
    except ValueError:
        pass


if __name__ == "__main__":
    import types
    # tiny monkeypatch shim so the file also runs without pytest
    class MP:
        def __init__(self): self._undo = []
        def setattr(self, obj, name, val):
            self._undo.append((obj, name, getattr(obj, name)))
            setattr(obj, name, val)
        def undo(self):
            for obj, name, val in reversed(self._undo): setattr(obj, name, val)
            self._undo = []
    fns = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for name, fn in fns:
        n = fn.__code__.co_argcount
        if n and "monkeypatch" in fn.__code__.co_varnames[:n]:
            mp = MP()
            try:
                fn(mp)
            finally:
                mp.undo()
        else:
            fn()
        print(f"ok  {name}")
    print(f"\n{len(fns)} passed")
