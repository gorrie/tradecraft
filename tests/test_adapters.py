"""Tests for the input adapters (the intake surface).

Cover the offline, dependency-free adapters that broaden where material can come from: single file,
a directory of files, a JSONL texts store, and an X/Twitter export. (from_url needs network and
from_pdf needs an optional dep; both are exercised only for their clear-error / signature contract.)

Run with `pytest` or directly: `python tests/test_adapters.py`.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

from tradecraft import adapters as A  # noqa: E402


def test_from_text_shape():
    d = A.from_text("hello world", doc_id="x", subject="S", url="http://e", date="2020-01-01")
    assert d == {"doc_id": "x", "text": "hello world", "subject": "S",
                 "url": "http://e", "date": "2020-01-01"}


def test_token_estimate_monotonic():
    assert A.token_estimate("one two three") >= 1
    assert A.token_estimate("a " * 100) > A.token_estimate("a " * 10)


def test_from_file(tmp_path):
    p = tmp_path / "speech.txt"
    p.write_text("there is no alternative", encoding="utf-8")
    d = A.from_file(str(p), subject="Thatcher")
    assert d["text"] == "there is no alternative"
    assert d["doc_id"] == "speech.txt" and d["subject"] == "Thatcher"


def test_from_dir(tmp_path):
    (tmp_path / "a.txt").write_text("alpha", encoding="utf-8")
    (tmp_path / "b.txt").write_text("beta", encoding="utf-8")
    (tmp_path / "skip.md").write_text("not matched", encoding="utf-8")
    docs = A.from_dir(str(tmp_path), pattern="*.txt")
    assert [d["doc_id"] for d in docs] == ["a.txt", "b.txt"]  # sorted, .md excluded


def test_from_jsonl_store_and_filter(tmp_path):
    p = tmp_path / "texts.jsonl"
    p.write_text(
        json.dumps({"person_id": "Rubin", "id": "r1", "text": "one", "date": "2008-01-01"}) + "\n"
        + json.dumps({"subject": "Rubin", "text": "two", "url": "http://e"}) + "\n"
        + json.dumps({"person_id": "Other", "text": "three"}) + "\n"
        + json.dumps({"person_id": "Rubin", "text": "   "}) + "\n",  # blank dropped
        encoding="utf-8")
    alld = A.from_jsonl(str(p))
    assert len(alld) == 3  # blank-text record dropped
    rubin = A.from_jsonl(str(p), subject="Rubin")
    assert [d["text"] for d in rubin] == ["one", "two"]
    assert rubin[0]["doc_id"] == "r1" and rubin[0]["date"] == "2008-01-01"


def test_from_x_export(tmp_path):
    p = tmp_path / "x.jsonl"
    p.write_text(
        json.dumps({"id": 1, "handle": "gorrie", "created_at": "2024-05-01T12:00:00+00:00",
                    "text": "a post", "url": "https://x.com/gorrie/status/1"}) + "\n"
        + json.dumps({"id": 2, "handle": "someone", "created_at": "2024-05-02T00:00:00+00:00",
                      "text": "other handle"}) + "\n",
        encoding="utf-8")
    docs = A.from_x_export(str(p), subject="@gorrie")  # leading @ tolerated
    assert len(docs) == 1
    d = docs[0]
    assert d["text"] == "a post" and d["date"] == "2024-05-01" and d["subject"] == "gorrie"
    assert d["url"] == "https://x.com/gorrie/status/1"


def test_group_timeline_orders_dated_first(tmp_path):
    docs = [A.from_text("c", date="2022-01-01"), A.from_text("a"), A.from_text("b", date="2020-01-01")]
    out = A.group_timeline(docs)
    assert [d["date"] for d in out] == ["2020-01-01", "2022-01-01", None]


def test_from_pdf_missing_dep_is_clear(tmp_path, monkeypatch):
    # If neither pypdf nor pdfminer is importable, the error must name the fix, not crash opaquely.
    import builtins
    real = builtins.__import__

    def block(name, *a, **k):
        if name.startswith("pypdf") or name.startswith("pdfminer"):
            raise ImportError("blocked for test")
        return real(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", block)
    f = tmp_path / "x.pdf"
    f.write_bytes(b"%PDF-1.4")
    with pytest.raises(ImportError, match="pypdf"):
        A.from_pdf(str(f))


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
