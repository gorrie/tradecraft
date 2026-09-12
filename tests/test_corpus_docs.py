"""Corpus enumeration: the loader every measurement in this repo reads its documents through.

WHY IT MATTERS OUT OF PROPORTION TO ITS SIZE
--------------------------------------------
`tradecraft/corpus_docs.py` exists because three tools were each blind to a different corpus
file: `lens_floor.py` globbed only `*.txt` and measured floors over the Federal Register alone,
reporting "no floor measurable" for lenses whose material sat in a JSONL beside it;
`harvest_gold.py` globbed the same plus one hardcoded filename. Enumeration was centralised so a
new corpus file becomes visible to every consumer at once.

That makes this module the single point where a silent corpus loss would affect **every** number
the project publishes -- floors, background rates, cross-tabs, camp readiness. Its failure modes
are all quiet: a skipped file, a swallowed record, a head-slice that never reaches the JSONL.

The `spread()` behaviour is the one with a measured history. A plain head-slice is
path-ordered, so `--docs 40` never reached a single JSONL record and silently decided that
floors would be measured over regulatory prose alone -- the register those lenses are known NOT
to fire on.

Run with `pytest` or directly: `python tests/test_corpus_docs.py`.
"""
import io
import glob
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tradecraft import corpus_docs as CD  # noqa: E402


# ------------------------------------------------- Doc

def test_doc_unpacks_as_name_and_text():
    """Existing call sites do `for name, text in docs`; that must keep working."""
    name, text = CD.Doc("a.txt", "some words here")
    assert (name, text) == ("a.txt", "some words here")


def test_doc_repr_reports_the_word_count():
    r = repr(CD.Doc("a.txt", "one two three"))
    assert "a.txt" in r and "3 words" in r


# ------------------------------------------------- enumeration over the real corpus

def test_documents_finds_jsonl_records():
    docs = CD.documents(min_words=60)
    origins = {d.origin.replace("\\", "/") for d in docs}
    assert any(o.endswith(".jsonl") for o in origins), "no JSONL corpus enumerated"
    assert len(docs) >= 100, "only %d documents enumerated" % len(docs)


def test_documents_finds_plain_text_files_when_any_are_present():
    """The .txt half of the enumeration, which CI cannot see.

    SPLIT FROM the JSONL assertion on 2026-09-04. It was one test asserting both halves, and
    it failed the first pipeline that ever ran this suite: the only .txt corpus in the tree is
    `corpus/_news-control/`, which is gitignored, so a clean checkout enumerates zero text
    files and the assertion fired on an environment difference rather than a defect.

    Skipping is right here and weakening would not be: the precondition genuinely is not met
    in CI, and a test that cannot run should say so rather than fail or quietly pass. The JSONL
    half above still runs everywhere, and it now asserts a document COUNT as well, so this
    split cannot turn into "the enumeration is untested in CI".
    """
    txt = glob.glob(os.path.join(ROOT, "corpus", "**", "*.txt"), recursive=True)
    if not txt:
        pytest.skip("no .txt corpus in this checkout (corpus/_news-control is gitignored)")
    origins = {d.origin.replace("\\", "/") for d in CD.documents(min_words=60)}
    assert any(o.endswith(".txt") for o in origins), (
        "%d .txt file(s) on disk but none enumerated" % len(txt))


def test_min_words_drops_fragments():
    everything = CD.documents()
    longer = CD.documents(min_words=60)
    assert len(longer) <= len(everything)
    assert all(len(d.text.split()) >= 60 for d in longer)


def test_limit_caps_the_result():
    assert len(CD.documents(limit=5)) == 5


def test_inventory_counts_every_document_by_origin():
    inv = CD.inventory()
    assert inv
    assert sum(inv.values()) == len(CD.documents())


# ------------------------------------------------- spread(): the measured defect

def test_spread_reaches_every_origin_rather_than_head_slicing():
    """The bug this function exists for: a head-slice never reached the JSONL corpora."""
    docs = CD.documents(min_words=60)
    origins = {d.origin for d in docs}
    assert len(origins) > 1, "fixture assumes a multi-file corpus"
    picked = CD.spread(docs, 12)
    assert len(picked) == 12
    # Round-robin across origins, so a small cap costs depth everywhere instead of the
    # existence of most corpora.
    assert len({d.origin for d in picked}) > 1


def test_spread_returns_everything_when_the_limit_exceeds_the_corpus():
    docs = CD.documents(limit=3)
    assert CD.spread(docs, 99) == docs
    assert CD.spread(docs, None) == docs


def test_spread_stops_when_origins_are_exhausted():
    """Asking for more than exists must terminate, not spin."""
    docs = [CD.Doc("a", "x", None, "one"), CD.Doc("b", "y", None, "two")]
    assert len(CD.spread(docs, 10)) == 2


# ------------------------------------------------- the quiet failure modes

def test_malformed_jsonl_line_is_skipped_not_fatal(tmp_path, monkeypatch):
    """A corpus defect must show up as a missing document, not crash every consumer."""
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    with io.open(corpus / "x.jsonl", "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"title": "good", "text": "a real document body"}) + "\n")
        fh.write("{not json at all\n")
        fh.write("\n")
        fh.write(json.dumps({"title": "empty", "text": "   "}) + "\n")
        fh.write(json.dumps({"id": "by-id", "text": "another body"}) + "\n")
    monkeypatch.setattr(CD, "CORPUS", str(corpus))
    monkeypatch.setattr(CD, "ROOT", str(tmp_path))

    names = [d.name for d in CD.documents()]
    assert "good" in names
    assert "by-id" in names          # falls back to id when title is absent
    assert "empty" not in names      # whitespace-only text yields no document
    assert len(names) == 2


def test_text_files_are_read_with_their_relative_path_as_origin(tmp_path, monkeypatch):
    corpus = tmp_path / "corpus"
    (corpus / "sub").mkdir(parents=True)
    io.open(corpus / "sub" / "a.txt", "w", encoding="utf-8").write("body text here")
    monkeypatch.setattr(CD, "CORPUS", str(corpus))
    monkeypatch.setattr(CD, "ROOT", str(tmp_path))
    docs = CD.documents()
    assert len(docs) == 1
    assert docs[0].origin.replace("\\", "/").endswith("corpus/sub/a.txt")


def test_unreadable_files_are_skipped(tmp_path, monkeypatch):
    """An OSError on one file must not abort enumeration for the rest."""
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    io.open(corpus / "ok.txt", "w", encoding="utf-8").write("readable body")
    io.open(corpus / "ok.jsonl", "w", encoding="utf-8").write(
        json.dumps({"title": "t", "text": "jsonl body"}) + "\n")
    monkeypatch.setattr(CD, "CORPUS", str(corpus))
    monkeypatch.setattr(CD, "ROOT", str(tmp_path))

    real_open = io.open

    def flaky(path, *a, **kw):
        if str(path).endswith(("ok.txt", "ok.jsonl")):
            raise OSError("permission denied")
        return real_open(path, *a, **kw)

    monkeypatch.setattr(CD.io, "open", flaky)
    assert CD.documents() == []


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
