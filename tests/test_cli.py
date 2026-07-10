"""Tests for the CLI surface (cli.py). Offline: cues backend + a monkeypatched detector for grade."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

from tradecraft import cli  # noqa: E402


def _run(capsys, *argv):
    cli.main(list(argv))
    return capsys.readouterr().out


def test_lenses(capsys):
    out = _run(capsys, "lenses")
    data = json.loads(out)
    assert "inevitability_framing" in data and "network_brokerage" in data


def test_demo(capsys):
    out = _run(capsys, "demo")
    assert "institutional_permeation" in out and "receipts" in out


def test_grade_file_monkeypatched(capsys, tmp_path, monkeypatch):
    from tradecraft import detect as D
    monkeypatch.setattr(D, "detect", lambda text, tax, **k: [])  # no API call
    f = tmp_path / "s.txt"
    f.write_text("there is no alternative", encoding="utf-8")
    out = _run(capsys, "grade", "--lens", "inevitability_framing", "--file", str(f))
    assert "inevitability_framing" in out


def test_grade_url_monkeypatched(capsys, monkeypatch):
    from tradecraft import detect as Dmod
    monkeypatch.setattr(Dmod, "detect", lambda text, tax, **k: [])
    monkeypatch.setattr(cli.adapters, "from_url",
                        lambda url, **k: {"doc_id": url, "text": "there is no alternative",
                                          "subject": None, "url": url, "date": None})
    out = _run(capsys, "grade", "--lens", "inevitability_framing", "--url", "http://e/x")
    assert "inevitability_framing" in out


def test_grade_unknown_lens(tmp_path):
    f = tmp_path / "s.txt"
    f.write_text("x", encoding="utf-8")
    with pytest.raises(SystemExit, match="unknown lens"):
        cli.main(["grade", "--lens", "nope", "--file", str(f)])


def test_grade_requires_file_or_url():
    with pytest.raises(SystemExit, match="provide --file or --url"):
        cli.main(["grade", "--lens", "inevitability_framing"])


def test_subject_cues(capsys, tmp_path):
    p = tmp_path / "t.jsonl"
    p.write_text("\n" + json.dumps({"person_id": "S", "text": "there is no alternative; adapt or die."}) + "\n",
                 encoding="utf-8")  # leading blank line exercises the skip branch
    out = _run(capsys, "subject", "--id", "S", "--texts", str(p))
    assert "inevitability_framing" in out and "Never blended" in out


def test_subject_no_texts_for_id(tmp_path):
    p = tmp_path / "t.jsonl"
    p.write_text(json.dumps({"person_id": "Other", "text": "x"}) + "\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="no texts for subject"):
        cli.main(["subject", "--id", "Missing", "--texts", str(p)])


def test_profile_ratchet_dir(capsys, tmp_path):
    d = tmp_path / "data"
    d.mkdir()
    (d / "people.jsonl").write_text(
        json.dumps({"id": "Hub", "label": "Hub", "sector": "fin", "kind": "person"}) + "\n",
        encoding="utf-8")
    (d / "institutions.jsonl").write_text(
        "\n".join(json.dumps({"id": i, "label": i, "sector": s, "kind": "institution"})
                  for i, s in [("Bank", "fin"), ("Gov", "gov"), ("Tank", "tank")]) + "\n",
        encoding="utf-8")
    (d / "edges.jsonl").write_text(
        "\n".join(json.dumps({"source": "Hub", "target": t}) for t in ["Bank", "Gov", "Tank"]) + "\n",
        encoding="utf-8")
    texts = tmp_path / "t.jsonl"
    texts.write_text(json.dumps({"person_id": "Hub", "text": "there is no alternative."}) + "\n",
                     encoding="utf-8")
    out = _run(capsys, "profile", "--id", "Hub", "--ratchet-dir", str(d), "--texts", str(texts))
    body = out[out.index("{"):]
    o = json.loads(body)
    assert "network_brokerage" in o["graph"] and o["text"] is not None


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
