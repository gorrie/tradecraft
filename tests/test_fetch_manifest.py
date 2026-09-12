"""The fetcher-manifest pattern: extraction, hashing, and the lock that proves recomputability.

WHY THE HASH MATTERS MORE THAN THE FETCH
----------------------------------------
A floor measured over a corpus a reader cannot rebuild is internal calibration, not a public
statistic -- `eval/floors_contract.py` carries a `recomputable` flag and public surfaces print
an MDE only when it is true. This tool is what lets that flag be true: a committed manifest of
public URLs plus a per-item content hash, so a reader can prove they hold the same text this
project measured.

Which means the hash has to behave. If it changed on every markup reflow the lock would be
noise and everyone would stop reading it; if it ignored a prose edit the lock would be a lie.
The trade made here is normalised-text hashing, and these tests pin both halves of it.

No network. Extraction and hashing are pure; the fetch discipline is exercised by hand.

Run with `pytest` or directly: `python tests/test_fetch_manifest.py`.
"""
import io
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "corpus"))

import fetch_manifest as FM  # noqa: E402


# ------------------------------------------------- extraction

def test_html_is_stripped_to_prose():
    got = FM.normalise_text(
        "<html><head><style>p{color:red}</style></head><body>"
        "<nav>menu items here</nav><p>The council must eliminate ambiguity.</p>"
        "<footer>copyright</footer></body></html>", "text/html")
    assert "The council must eliminate ambiguity." in got
    for junk in ("menu items", "color:red", "copyright"):
        assert junk not in got, junk


def test_html_entities_are_unescaped():
    assert "don't & won't" in FM.normalise_text(
        "<p>don&#39;t &amp; won&#39;t</p>", "text/html")


def test_plain_text_passes_through_whitespace_normalised():
    got = FM.normalise_text("line one\n\n  line   two\t", "text/plain")
    assert got == "line one line two"


def test_html_is_detected_without_a_content_type():
    """A server that mislabels its content type must not leak markup into the corpus."""
    got = FM.normalise_text("<div><p>real prose here</p></div>", "")
    assert got == "real prose here"


# ------------------------------------------------- the hash contract, both halves

def test_markup_reflow_does_not_change_the_hash():
    """A site reindenting its HTML must not invalidate a measured corpus."""
    a = FM.normalise_text("<p>The same words exactly.</p>", "text/html")
    b = FM.normalise_text("<div>\n  <p>\n    The same words exactly.\n  </p>\n</div>",
                          "text/html")
    assert FM.content_hash(a) == FM.content_hash(b)


def test_a_prose_edit_does_change_the_hash():
    """The other half. A lock that ignored content changes would be a lie."""
    a = FM.normalise_text("<p>The same words exactly.</p>", "text/html")
    b = FM.normalise_text("<p>The same words, nearly.</p>", "text/html")
    assert FM.content_hash(a) != FM.content_hash(b)


def test_hash_is_stable_across_calls():
    text = "a corpus document"
    assert FM.content_hash(text) == FM.content_hash(text)
    assert len(FM.content_hash(text)) == 64


# ------------------------------------------------- manifest and lock plumbing

def test_manifest_skips_comments_and_blank_lines(tmp_path):
    p = tmp_path / "m.jsonl"
    p.write_text("# a comment\n"
                 + json.dumps({"id": "a", "url": "https://example.org/a"}) + "\n"
                 + "\n"
                 + json.dumps({"id": "b", "url": "https://example.org/b"}) + "\n",
                 encoding="utf-8")
    items = FM.load_manifest(str(p))
    assert [i["id"] for i in items] == ["a", "b"]


def test_lock_sits_beside_its_manifest():
    assert FM.lock_path("/x/y/advocacy.jsonl") == "/x/y/advocacy.lock.json"


def test_init_writes_a_usable_template(tmp_path, capsys):
    p = tmp_path / "new.jsonl"
    assert FM.main(["--init", str(p)]) == 0
    items = FM.load_manifest(str(p))
    assert items and "url" in items[0] and "note" in items[0]
    # The template must say what gets committed, or the pattern gets used backwards.
    head = io.open(p, encoding="utf-8").read()
    assert "never commit the fetched text" in head.lower()


def test_fetch_refuses_without_an_out_path(tmp_path, capsys):
    """The corpus must not default into the repo: that is the whole point of the pattern."""
    p = tmp_path / "m.jsonl"
    p.write_text(json.dumps({"id": "a", "url": "https://example.org/a"}) + "\n",
                 encoding="utf-8")
    assert FM.main(["--manifest", str(p)]) == 1
    assert "OUTSIDE the repo" in capsys.readouterr().out


def test_verify_without_a_lock_is_refused(tmp_path, capsys):
    p = tmp_path / "m.jsonl"
    p.write_text(json.dumps({"id": "a", "url": "https://example.org/a"}) + "\n",
                 encoding="utf-8")
    assert FM.main(["--manifest", str(p), "--verify"]) == 1
    assert "no lock file" in capsys.readouterr().out


def test_an_oversized_manifest_is_refused_rather_than_fetched(tmp_path, capsys):
    """The cap exists so a thousand-URL manifest is a decision, not an accident."""
    p = tmp_path / "m.jsonl"
    p.write_text("".join(
        json.dumps({"id": "i%d" % i, "url": "https://example.org/%d" % i}) + "\n"
        for i in range(5)), encoding="utf-8")
    assert FM.main(["--manifest", str(p), "--out", str(tmp_path / "o.jsonl"),
                    "--cap", "3"]) == 1
    assert "over the 3 cap" in capsys.readouterr().out


def test_fetch_discipline_constants_are_not_hot():
    """Serial with a real delay, a cap, and a contactable UA. Changing these is a decision."""
    assert FM.DELAY >= 1.0
    assert FM.CAP <= 500
    assert "contact" in FM.UA and "tradecraft" in FM.UA


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
