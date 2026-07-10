"""Targeted tests closing the remaining coverage gaps across modules.

Each test names the branch it exercises. Network/PDF paths are mocked; graph paths use small
synthetic fixtures written to tmp files.
"""
import json
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

from tradecraft import adapters as A, detect as D, network as N, structural as S, profile as P  # noqa: E402
from tradecraft.schema import Taxonomy, Marker, Detection  # noqa: E402
from tradecraft.local_llm import Refusal  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DETECTORS = os.path.join(REPO, "detectors")


# ---- schema.marker_of miss -------------------------------------------------------------------

def test_marker_of_unknown_is_none():
    tax = Taxonomy(id="x", name="X", description="", markers=[
        Marker(id="m", name="M", base_weight=1.0,
               detections=[Detection(id="d", weight=1.0, definition="def")])])
    assert tax.marker_of("nope") is None
    assert tax.detection("nope") is None


# ---- detect.py gaps --------------------------------------------------------------------------

def test_few_shot_empty_when_no_gold():
    tax = Taxonomy(id="x", name="X", description="", markers=[
        Marker(id="m", name="M", base_weight=1.0,
               detections=[Detection(id="d", weight=1.0, definition="def")])])
    assert D._few_shot(tax) == ""


def test_strip_fences():
    assert D._strip_fences("```json\n{\"a\":1}\n```") == '{"a":1}'
    assert D._strip_fences("```\nplain\n```") == "plain"


def test_detect_cloud_non_json_is_refusal(monkeypatch):
    from tradecraft import local_llm
    monkeypatch.setattr(local_llm, "cloud", lambda *a, **k: "not json at all")
    tax = _load_one()
    with pytest.raises(Refusal):
        D.detect("text", tax, backend="cloud")


def test_detect_auto_falls_back_to_local(monkeypatch):
    from tradecraft import local_llm
    def refuse(*a, **k):
        raise Refusal("no")
    monkeypatch.setattr(local_llm, "cloud", refuse)
    monkeypatch.setattr(local_llm, "local", lambda *a, **k: '{"hits":[]}')
    tax = _load_one()
    assert D.detect("text", tax, backend="auto") == []


def test_detect_unknown_backend():
    with pytest.raises(ValueError, match="unknown backend"):
        D.detect("t", _load_one(), backend="bogus")


def _load_one():
    from tradecraft.loader import load_lenses
    return load_lenses(DETECTORS)["inevitability_framing"]


# ---- network.py edge cases -------------------------------------------------------------------

def test_network_unknown_subject(tmp_path):
    g = tmp_path / "g.json"
    g.write_text(json.dumps({"entities": [{"id": "A", "sector": "fin"}], "edges": []}),
                 encoding="utf-8")
    assert N.subject_network_hits(str(g), "Nobody") == []


def test_network_skips_self_and_missing_edges(tmp_path):
    g = tmp_path / "g.json"
    g.write_text(json.dumps({"entities": [{"id": "A", "sector": "fin"}],
                             "edges": [{"source": "A", "target": "A"},
                                       {"source": "A"}]}), encoding="utf-8")
    graph = N.build_graph(str(g))
    assert "A" not in graph.adj or "A" not in graph.adj.get("A", set())


def test_decile_and_percentile_empty():
    assert N._decile_threshold([], 0.1) == float("inf")
    assert N._percentile_rank([], 1.0) == 0.0


def test_brokerage_skips_sectorless_node(tmp_path):
    # B has no sector -> the gb-is-None continue branch fires.
    g = tmp_path / "g.json"
    g.write_text(json.dumps({"entities": [{"id": "A", "sector": "fin"}, {"id": "C", "sector": "gov"}],
                             "edges": [{"source": "A", "target": "B"}, {"source": "B", "target": "C"}]}),
                 encoding="utf-8")
    roles = N.brokerage_roles(N.build_graph(str(g)))
    assert "B" in roles  # B present but contributes nothing (no sector)


# ---- structural.py gaps ----------------------------------------------------------------------

def _rich_graph(tmp_path):
    """A subject with 5 multi-sector career moves + funds an industry node AND a tank node."""
    ents = [{"id": "S", "name": "Subj", "sector": "gov"},
            {"id": "Aca", "name": "Aca", "sector": "academia"},
            {"id": "Tk", "name": "Tk", "sector": "tank"},
            {"id": "Tc", "name": "Tc", "sector": "tech"},
            {"id": "Fn", "name": "Fn", "sector": "fin"},
            {"id": "Gv", "name": "Gv", "sector": "gov"},
            {"id": "Proj", "name": "Proj", "sector": "tech"},
            {"id": "Eval", "name": "Eval", "sector": "tank"}]
    edges = [{"source": "S", "target": t, "rel": "employed-by"} for t in ["Aca", "Tk", "Tc", "Fn", "Gv"]]
    edges += [{"source": "Proj", "target": "S", "rel": "funded-by"},
              {"source": "Eval", "target": "S", "rel": "funded-by"}]
    p = tmp_path / "rg.json"
    p.write_text(json.dumps({"entities": ents, "edges": edges}), encoding="utf-8")
    return str(p)


def test_structural_unknown_subject(tmp_path):
    g = tmp_path / "g.json"
    g.write_text(json.dumps({"entities": [{"id": "A", "sector": "fin"}], "edges": []}), encoding="utf-8")
    assert S.detect_subject(str(g), "Nobody") == []


def test_structural_four_sectors_five_moves_and_funder_evaluator(tmp_path):
    hits = S.detect_subject(_rich_graph(tmp_path), "S")
    ids = {h.detection_id for h in hits}
    assert "spans-four-plus-sectors" in ids
    assert "five-plus-moves" in ids
    assert "funds-recipient-and-evaluator" in ids
    # typed graph -> NO affiliation-mode annotation
    assert all("affiliation graph" not in h.rationale for h in hits)


def test_structural_affiliation_mode_on_untyped_graph(tmp_path):
    # Untyped edges (the ratchet shape): revolving_door reads cross-sector affiliation breadth,
    # and every receipt is annotated that this is breadth, not a proven trajectory.
    ents = [{"id": "S", "sector": "gov", "name": "S"}, {"id": "A", "sector": "fin", "name": "A"},
            {"id": "B", "sector": "tank", "name": "B"}, {"id": "C", "sector": "tech", "name": "C"}]
    edges = [{"source": "S", "target": t} for t in ["A", "B", "C"]]  # no rel
    p = tmp_path / "u.json"
    p.write_text(json.dumps({"entities": ents, "edges": edges}), encoding="utf-8")
    hits = S.detect_subject(str(p), "S")
    ids = {h.detection_id for h in hits}
    # targets span fin/tank/tech -> 3 sectors + monitor(tank)->industry(fin,tech)
    assert "spans-three-sectors" in ids and "watchdog-then-join" in ids
    assert hits and all("affiliation graph" in h.rationale for h in hits)


# ---- profile.py: unknown graph lens skipped --------------------------------------------------

def test_profile_unknown_graph_lens_skipped(tmp_path):
    g = tmp_path / "g.json"
    g.write_text(json.dumps({"entities": [{"id": "A", "sector": "fin"}], "edges": []}), encoding="utf-8")
    out = P.profile_subject("A", detectors_dir=DETECTORS, graph_path=str(g),
                            graph_lenses=("not_a_lens",))
    assert out["graph"] == {}


# ---- adapters.py gaps ------------------------------------------------------------------------

def test_from_url(monkeypatch):
    import requests

    class R:
        text = "<html><head><style>x{}</style></head><body><p>Hello  world</p><script>z()</script></body></html>"
        def raise_for_status(self):
            return None

    monkeypatch.setattr(requests, "get", lambda *a, **k: R())
    d = A.from_url("http://example.org/x", subject="Sub")
    assert "Hello world" in d["text"] and "z()" not in d["text"]
    assert d["url"] == "http://example.org/x" and d["subject"] == "Sub"


def test_from_subject_found_and_missing(tmp_path):
    p = tmp_path / "ents.json"
    p.write_text(json.dumps({"people": [
        {"id": "Sub", "label": "Subject", "sources": [{"url": "https://e/1"}, "not-a-url", "https://e/2"]}]}),
        encoding="utf-8")
    got = A.from_subject("Sub", str(p))
    assert got["sources"] == ["https://e/1", "https://e/2"]
    with pytest.raises(KeyError):
        A.from_subject("Ghost", str(p))


def test_from_jsonl_subject_key_and_text_key(tmp_path):
    p = tmp_path / "t.jsonl"
    p.write_text("\n" + json.dumps({"subject": "X", "body": "hello"}) + "\n", encoding="utf-8")  # leading blank line
    docs = A.from_jsonl(str(p), subject="X", text_key="body")
    assert docs and docs[0]["text"] == "hello" and docs[0]["subject"] == "X"


def test_from_pdf_pdfminer_fallback(tmp_path, monkeypatch):
    # pypdf unavailable -> pdfminer.six path runs.
    monkeypatch.setitem(sys.modules, "pypdf", None)  # makes `import pypdf` raise ImportError
    fake = types.ModuleType("pdfminer")
    fake_high = types.ModuleType("pdfminer.high_level")
    fake_high.extract_text = lambda path: "miner extracted   \nlines"
    fake.high_level = fake_high
    monkeypatch.setitem(sys.modules, "pdfminer", fake)
    monkeypatch.setitem(sys.modules, "pdfminer.high_level", fake_high)
    f = tmp_path / "x.pdf"
    f.write_bytes(b"%PDF-1.4")
    assert "miner extracted" in A.from_pdf(str(f))["text"]


def test_detect_cues_skips_empty_cue():
    tax = Taxonomy(id="x", name="X", description="", markers=[
        Marker(id="m", name="M", base_weight=1.0, detections=[
            Detection(id="d", weight=1.0, definition="def", cues=["   ", "findme"])])])
    hits = D.detect_cues("please findme here", tax)
    assert len(hits) == 1 and hits[0].span == "findme"


def test_from_pdf_success_with_fake_pypdf(tmp_path, monkeypatch):
    # Inject a fake pypdf so the success path runs without a real PDF library.
    fake = types.ModuleType("pypdf")
    class _Page:
        def extract_text(self):
            return "page text  \nmore"
    class _Reader:
        def __init__(self, path):
            self.pages = [_Page()]
    fake.PdfReader = _Reader
    monkeypatch.setitem(sys.modules, "pypdf", fake)
    f = tmp_path / "x.pdf"
    f.write_bytes(b"%PDF-1.4")
    d = A.from_pdf(str(f), subject="Z")
    assert "page text" in d["text"] and d["subject"] == "Z"


def test_from_x_export_full_text_fallback_and_skip_empty(tmp_path):
    p = tmp_path / "x.jsonl"
    p.write_text(
        "\n"  # blank line -> skipped
        + json.dumps({"id": 1, "handle": "h", "full_text": "via full_text", "created_at": "2024-01-02T00:00:00Z"}) + "\n"
        + json.dumps({"id": 2, "handle": "h", "text": "  "}) + "\n",  # empty -> skipped
        encoding="utf-8")
    docs = A.from_x_export(str(p))
    assert len(docs) == 1 and docs[0]["text"] == "via full_text" and docs[0]["date"] == "2024-01-02"


def test_write_ratchet_graph_list_edges_and_endpoint_guard(tmp_path):
    d = tmp_path / "data"
    d.mkdir()
    (d / "people.jsonl").write_text("\n" + json.dumps({"id": "P", "sector": "fin", "label": "P"}) + "\n",
                                    encoding="utf-8")  # leading blank line skipped
    (d / "institutions.jsonl").write_text(json.dumps({"id": "I", "sector": "gov", "label": "I"}) + "\n",
                                          encoding="utf-8")
    # one list-form edge (valid) and one with a missing endpoint (dropped)
    (d / "edges.jsonl").write_text('\n["P", "I"]\n' + json.dumps({"source": "P"}) + "\n", encoding="utf-8")  # blank line skipped
    out = tmp_path / "g.json"
    n = A.write_ratchet_graph(str(d), str(out))
    g = json.loads(out.read_text(encoding="utf-8"))
    assert n == 2 and len(g["edges"]) == 1 and g["edges"][0] == {"source": "P", "target": "I"}


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
