"""Tests for the combined two-lane profile (profile.py) and the ratchet-graph converter.

Offline (cues backend). Asserts: the converter produces the graph-lens schema; a text-only profile
runs without a graph; a combined profile carries BOTH a graph-lane result and a text-lane result on
separate axes; and nothing is ever blended into a single score.

Run with `pytest` or directly: `python tests/test_profile.py`.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tradecraft import adapters as A  # noqa: E402
from tradecraft.profile import profile_subject  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DETECTORS = os.path.join(REPO_ROOT, "detectors")

INEV = ("There is no alternative; this is the only way forward and it cannot be stopped. "
        "You can be on the right side of history or be left behind — adapt or die.")


def _tiny_ratchet_dir(root):
    """A small but valid ratchet data dir: a hub person tied to several sectored institutions."""
    d = root / "data"
    d.mkdir()
    (d / "people.jsonl").write_text(
        json.dumps({"id": "Hub", "label": "Hub Person", "sector": "fin", "kind": "person"}) + "\n"
        + json.dumps({"id": "Side", "label": "Side Person", "sector": "gov", "kind": "person"}) + "\n",
        encoding="utf-8")
    (d / "institutions.jsonl").write_text(
        "\n".join(json.dumps({"id": i, "label": i, "sector": s, "kind": "institution"})
                  for i, s in [("Bank", "fin"), ("Gov", "gov"), ("Tank", "tank"), ("Media", "media")])
        + "\n", encoding="utf-8")
    (d / "edges.jsonl").write_text(
        "\n".join(json.dumps({"source": s, "target": t}) for s, t in
                  [("Hub", "Bank"), ("Hub", "Gov"), ("Hub", "Tank"), ("Hub", "Media"),
                   ("Side", "Gov")]) + "\n", encoding="utf-8")
    return d


def test_write_ratchet_graph(tmp_path):
    d = _tiny_ratchet_dir(tmp_path)
    out = tmp_path / "graph.json"
    n = A.write_ratchet_graph(str(d), str(out))
    g = json.loads(out.read_text(encoding="utf-8"))
    assert n == 6  # 2 people + 4 institutions
    assert len(g["entities"]) == 6 and len(g["edges"]) == 5
    assert {e["id"] for e in g["entities"]} >= {"Hub", "Bank", "Tank"}
    assert all("sector" in e for e in g["entities"])


def test_profile_text_only():
    out = profile_subject("S", detectors_dir=DETECTORS,
                          texts=[{"id": "t1", "text": INEV}], backend="cues")
    assert out["graph"] == {}                 # no graph_path -> graph lane empty
    assert out["text"] is not None
    per_lens = out["text"]["subject"]["per_lens"]
    assert per_lens["inevitability_framing"]["max"] > 0.0
    assert "score" not in out and "index" not in out   # never a single blended number


def test_profile_combined_two_lanes(tmp_path):
    d = _tiny_ratchet_dir(tmp_path)
    graph = tmp_path / "graph.json"
    A.write_ratchet_graph(str(d), str(graph))
    out = profile_subject("Hub", detectors_dir=DETECTORS, graph_path=str(graph),
                          texts=[{"id": "t1", "text": INEV}], backend="cues")
    # graph lane present and on its own axis
    assert "network_brokerage" in out["graph"]
    nb = out["graph"]["network_brokerage"]
    assert nb["lens_id"] == "network_brokerage" and "index" in nb
    assert nb["markers_present"]  # the hub spans fin/gov/tank/media -> brokerage fires
    # text lane present and on its own axis
    assert out["text"]["subject"]["per_lens"]["inevitability_framing"]["max"] > 0.0
    # two distinct axes, never merged
    assert set(out.keys()) >= {"subject", "graph", "text"} and "score" not in out


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
