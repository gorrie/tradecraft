"""Edge paths in the engine and adapters that no other fixture reaches.

Not coverage-chasing: each of these is a branch that decides whether a hit is real, whether a
cached verdict answers the question that was asked, or whether a graph lens can see a
trajectory. All three fail quietly.

Run with `pytest` or directly: `python tests/test_engine_edges.py`.
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tradecraft import adapters  # noqa: E402
from tradecraft.detect import (  # noqa: E402
    VERIFY_MODES, _find_all_bounded, build_verify_prompt, verify_hit,
)
from tradecraft.loader import load_lenses  # noqa: E402
from tradecraft.schema import DetectionHit  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _lens():
    return load_lenses(os.path.join(REPO_ROOT, "detectors"))["subculture_register"]


# ------------------------------------------------- suffix absorption has a limit

def test_an_absorbed_suffix_may_not_run_into_more_word():
    """`class struggles` counts; `class strugglesx` does not.

    The closed suffix list lets a match absorb a plural and still count, PROVIDED a non-word
    character follows. Without that second check the suffix rule would reopen the mid-word
    matching it exists alongside -- `regime` inside `regimen` is the defect the boundary rule
    was added for, and an unchecked suffix would walk straight back into it.
    """
    assert _find_all_bounded("class struggle", "the class struggles continue")
    assert not _find_all_bounded("class struggle", "the class strugglesx continue")


# ------------------------------------------------- verify modes

@pytest.mark.parametrize("mode", VERIFY_MODES)
def test_every_declared_verify_mode_builds_a_prompt(mode):
    tax = _lens()
    hit = DetectionHit(detection_id="maganr-tells", confidence=0.55,
                       span="drain the swamp", char_start=0, char_end=15,
                       rationale="fixture")
    prompt = build_verify_prompt(tax, "drain the swamp, they said", hit, mode=mode)
    assert "FLAGGED SPAN" in prompt
    assert tax.name in prompt


def test_instance_mode_asks_about_use_not_speaker():
    """The branch that exists because the verifier once rejected every hit in reported speech.

    Author mode asks whose words they are; instance mode asks whether the method is present.
    Conflating them made a corpus of quotations score zero.
    """
    tax = _lens()
    hit = DetectionHit(detection_id="maganr-tells", confidence=0.55,
                       span="drain the swamp", char_start=0, char_end=15,
                       rationale="fixture")
    instance = build_verify_prompt(tax, "He said: drain the swamp.", hit, mode="instance")
    author = build_verify_prompt(tax, "He said: drain the swamp.", hit, mode="author")
    # Both modes turn on use-vs-mention; only instance mode declares the speaker irrelevant.
    assert "USE vs MENTION" in instance and "USE vs MENTION" in author
    assert "NOT WHO IS SPEAKING" in instance
    assert "attribution is not your question here" in instance
    assert "NOT WHO IS SPEAKING" not in author


def test_an_unknown_verify_mode_is_refused_by_the_prompt_builder():
    """A typo must not silently fall through to the author prompt: verdicts get cached under
    a mode, and a cached verdict then answers a question nobody asked."""
    tax = _lens()
    hit = DetectionHit(detection_id="maganr-tells", confidence=0.55,
                       span="drain the swamp", char_start=0, char_end=15,
                       rationale="fixture")
    with pytest.raises(ValueError, match="unknown verify mode"):
        build_verify_prompt(tax, "text", hit, mode="autheur")


def test_an_unknown_verify_mode_is_refused_before_any_backend_call():
    """Same guard on the calling path, so no request is spent discovering the typo."""
    tax = _lens()
    hit = DetectionHit(detection_id="maganr-tells", confidence=0.55,
                       span="drain the swamp", char_start=0, char_end=15,
                       rationale="fixture")
    with pytest.raises(ValueError, match="unknown verify mode"):
        verify_hit("text", tax, hit, mode="autheur", backend="cues")


# ------------------------------------------------- typed relations survive the graph export

def test_write_ratchet_graph_carries_typed_relations_through(tmp_path):
    """`revolving_door` reads trajectory off typed edges. An untyped export downgrades it to
    breadth, which the lens's own receipts have to disclaim -- so the rel must survive."""
    data = tmp_path / "data"
    data.mkdir()
    (data / "people.jsonl").write_text(
        json.dumps({"id": "a", "label": "A", "sector": "gov"}) + "\n", encoding="utf-8")
    (data / "institutions.jsonl").write_text(
        json.dumps({"id": "b", "label": "B", "sector": "industry"}) + "\n", encoding="utf-8")
    (data / "edges.jsonl").write_text(
        json.dumps({"source": "a", "target": "b", "rel": "employed-by"}) + "\n"
        + json.dumps({"source": "b", "target": "a"}) + "\n"
        + json.dumps(["a", "b"]) + "\n"          # legacy bare-pair form
        + json.dumps({"source": "", "target": "b"}) + "\n"   # incomplete: dropped
        + "\n",
        encoding="utf-8")

    out = tmp_path / "graph.json"
    n = adapters.write_ratchet_graph(str(data), str(out))
    assert n == 2
    written = json.load(open(out, encoding="utf-8"))
    edges = written["edges"]
    assert {"source": "a", "target": "b", "rel": "employed-by"} in edges
    # An edge with no relation stays untyped rather than acquiring a fabricated one, and the
    # legacy bare-pair form still ports as plain adjacency.
    assert {"source": "b", "target": "a"} in edges
    assert edges.count({"source": "a", "target": "b"}) == 1
    assert len(edges) == 3           # the incomplete edge is dropped
    assert {"id": "a", "sector": "gov", "name": "A"} in written["entities"]


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
