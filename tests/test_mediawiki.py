"""The MediaWiki stripper has ONE implementation, and it must keep the behaviour it had.

`corpus/mediawiki.py` was extracted from `corpus/fetch_wikisource.py` on 2026-09-04, when the
reader-recomputable background pool needed a second wiki. An extraction that changes behaviour
is not an extraction: the georgist, lenin and revleft canon corpora were mined with the old
code and their idiom counts are already written into results files, so a "tidier" stripper
silently invalidates published numbers while the code goes on looking correct.

Two drafts of the extraction did exactly that before these tests existed:

  - external links: `[http://x.com label]` became `label` instead of `http://x.com label`
  - headings: `== Heading ==` lines were dropped instead of kept
  - _DROP_CLASSES gained navbox/reflist/catlinks and LOST `ws-noinclude`

Each looks like an improvement and each rewrites the corpus. The fixtures below are the
measured behaviour, not the desirable behaviour, and that distinction is the point.

Run with `pytest` or directly: `python tests/test_mediawiki.py`.
"""
import io
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "corpus"))

import fetch_wikisource as FW  # noqa: E402
import mediawiki as MW  # noqa: E402

#: Behaviour as it stood before the extraction. Each entry is (input, expected output).
FIXTURES = [
    ("{{header|title=X}}Real prose here.", "Real prose here."),
    ("Nested {{a|{{b|c}}}} gone.", "Nested gone."),
    # The URL is KEPT alongside the label. A draft dropped it; that is a corpus change.
    ("[http://x.com label].", "http://x.com label ."),
    # Headings are kept INCLUDING their `==` markers -- the stripper is documented as
    # "deliberately blunt: this feeds an n-gram count", and `==` is not a word character so it
    # never becomes an n-gram. A draft removed heading lines entirely, which deletes the
    # heading's WORDS from the corpus too. Written here as what it does, not what is tidy.
    ("== Heading ==\nPara.", "== Heading == Para."),
    ("<div class=\"ws-noexport\">drop</div>Keep.", "Keep."),
    ("<div class=\"wst-header\">h<div>nest</div></div>Keep2.", "Keep2."),
    # ws-noinclude must stay in the drop set. A draft removed it.
    ("<div class=\"ws-noinclude\">ni</div>Keep3.", "Keep3."),
    ("<ref>note</ref>Body end.", "Body end."),
    ("<table><tr><td>t</td></tr></table>After.", "After."),
    ("<sup>1</sup>Text.", "Text."),
    ("Plain sentence with no markup at all.", "Plain sentence with no markup at all."),
]


@pytest.mark.parametrize("raw,expected", FIXTURES)
def test_plain_keeps_its_measured_behaviour(raw, expected):
    assert MW.plain(raw) == expected


def test_unbalanced_braces_do_not_swallow_the_page():
    """The documented fallback: wrong in a small way rather than catastrophic in a large one."""
    out = MW.plain("Unbalanced {{a|b Rest of page survives.")
    assert "Rest of page survives." in out


def test_drop_classes_are_exactly_the_three_the_corpora_were_built_with():
    assert MW._DROP_CLASSES == ("ws-noexport", "wst-header", "ws-noinclude")


# ------------------------------------------------- EOF truncation, the two the review found
#
# Both repairs are confined to inputs the OLD code truncated. Measured rather than asserted
# (2026-09-04), pre- vs post-repair on identical inputs: 101 raw Wikinews revisions (0
# divergences; the 94 hash-pinned in news-control.manifest.jsonl reproduce through both), 116
# raw + 91 rendered Wikisource pages re-fetched for the georgist / lenin / revleft canon and
# their Smith and Marx controls (0), the stored 28-page georgist raw wikitext (0), the 331
# in-repo corpus documents (0); the 29 stored lenin pages are reproduced exactly by the new
# code. Only the two synthetic reproductions below diverge, which is the intended outcome.
# The re-fetch lives outside the repo, as the canon does; these tests pin the synthetic cases.

def test_a_self_closing_ref_does_not_swallow_the_prose_up_to_the_next_ref():
    """`<ref name=a/>` has no `</ref>`, so `<ref.*?</ref>` ran to the NEXT one: 105 chars to 16."""
    raw = ("Intro text. <ref name=a/> Here is a long stretch of prose that should survive "
           "intact.<ref>note</ref> End.")
    out = MW.plain(raw)
    assert out == "Intro text. Here is a long stretch of prose that should survive intact. End."
    assert "note" not in out, "the paired <ref>note</ref> must still be removed"


@pytest.mark.parametrize("raw,expected", [
    # A lone self-closing ref was already dropped to a single space by the generic tag strip;
    # dropping it earlier must land on the same text, or this is a corpus change.
    ("A <ref name=a/> B.", "A B."),
    ("A <references/> B.", "A B."),
    ("A <ref name=\"x\" /> B.", "A B."),
    # A paired ref carrying attributes is still removed whole.
    ("A <ref name=x>n</ref> B.", "A B."),
    # An attribute value containing a slash is not a self-closing tag.
    ("<table style=\"a/b\"><tr><td>t</td></tr></table>After.", "After."),
])
def test_self_closing_forms_land_on_the_pre_repair_text(raw, expected):
    assert MW.plain(raw) == expected


def test_an_unclosed_drop_div_does_not_delete_to_eof():
    """The depth counter ran off the end and the old code deleted to EOF: 98 chars to 13."""
    raw = ('Lead prose. <div class="messagebox">unclosed and the rest of the article body '
           'runs on here and on.')
    out = MW.strip_elements(raw, MW.SITE_DROP_CLASSES["wikinews"])
    assert "the rest of the article body runs on here and on." in out, out
    assert "Lead prose." in out
    assert '<div class="messagebox">' not in out, "the opener itself must go, or the loop spins"


def test_an_unclosed_drop_div_falls_back_to_the_first_closer():
    """strip_templates' precedent: the conservative reading, not the destructive one.

    The nested `<div>inner</div>` closes once; the outer never does. Cutting at the first
    `</div>` loses `inner` (wrong in a small way) and keeps the tail (not catastrophic)."""
    raw = ('Lead. <div class="messagebox">box <div>inner</div> tail runs on with no closer '
           'at all.')
    out = MW.plain(raw, MW.SITE_DROP_CLASSES["wikinews"])
    assert out == "Lead. tail runs on with no closer at all."


def test_balanced_drop_divs_are_still_removed_whole():
    """The fallback must be unreachable for a well-formed document."""
    raw = ('Lead. <div class="messagebox">box <div>inner</div> more box</div> Body. '
           '<div class="infobox">i</div> End.')
    out = MW.plain(raw, MW.SITE_DROP_CLASSES["wikinews"])
    assert out == "Lead. Body. End."


def test_fetch_wikisource_holds_no_second_copy():
    """The whole point of the extraction. A re-added local def is the regression."""
    src = io.open(os.path.join(ROOT, "corpus", "fetch_wikisource.py"),
                  encoding="utf-8").read()
    for fn in ("strip_templates", "strip_elements", "plain", "_get",
               "fetch_batched", "fetch_rendered", "list_subpages"):
        assert ("def %s(" % fn) not in src, (
            "fetch_wikisource.py defines %s again; it must import it from mediawiki" % fn)
    assert "from mediawiki import" in src


def test_the_shim_re_exports_what_callers_use():
    """tests/test_camp_idiom_mining.py imports these off fetch_wikisource. Keep them reachable."""
    for fn in ("plain", "strip_templates", "strip_elements"):
        assert getattr(FW, fn) is getattr(MW, fn), fn


def test_real_corpus_documents_round_trip_identically():
    """Non-vacuity guard: this must actually read documents, not pass on an empty glob.

    A test that iterates nothing and asserts nothing about it reports success, which is how
    three vacuous tests got written in this project before being caught.
    """
    import glob
    import json
    seen = 0
    for path in glob.glob(os.path.join(ROOT, "corpus", "*.jsonl")):
        for line in io.open(path, encoding="utf-8"):
            if not line.strip():
                continue
            text = (json.loads(line).get("text") or "")
            if not text:
                continue
            seen += 1
            assert FW.plain(text) == MW.plain(text)
    assert seen >= 20, "only %d corpus documents exercised -- glob is not finding them" % seen


# ------------------------------------------- Wikinews cleaning must never eat the article

def _wikinews():
    sys.path.insert(0, os.path.join(ROOT, "corpus"))
    import fetch_wikinews
    return fetch_wikinews


def test_unbalanced_media_markup_does_not_swallow_the_body():
    """The EOF truncation the balanced-bracket rewrite reintroduced.

    A depth counter with no fallback runs to end-of-string when the closing `]]` never
    arrives, so one typo'd caption deleted every word after it: 112 characters to 14.
    strip_templates already had the answer -- fall back to the conservative reading -- and
    drop_media did not.
    """
    F = _wikinews()
    text = ("Intro prose. [[File:x.jpg|thumb|a caption with [[a link] typo]] "
            "and then the real body continues here at length.")
    out = F.drop_media(text)
    assert "the real body continues here at length." in out, out
    assert "Intro prose." in out


def test_media_that_never_closes_drops_nothing():
    """Leaving markup visible beats deleting prose nobody can see is missing."""
    F = _wikinews()
    text = "Intro. [[File:x.jpg|thumb|no close at all and the body runs on and on."
    assert F.drop_media(text) == text


def test_well_formed_media_is_still_removed_caption_and_all():
    F = _wikinews()
    F_out = F.drop_media("Intro. [[File:x.jpg|thumb|left|A caption.]] Body follows.")
    assert "caption" not in F_out and "File" not in F_out
    assert "Intro." in F_out and "Body follows." in F_out
    # A caption containing its own wikilink must go with it, brackets balanced.
    nested = F.drop_media("Intro. [[File:x.jpg|thumb|A photo of [[Ardlui station]], t.]] Body.")
    assert "Ardlui" not in nested and "Body." in nested


def test_boilerplate_patterns_are_gone_not_merely_narrowed():
    """_BOILER ran after plain() flattened the text, so `.*` reached EOF. Measured zero
    matches across 94 fetched articles, so the patterns were deleted rather than tuned."""
    F = _wikinews()
    assert F._BOILER == ()
    kept = F.clean("First para. A spokesman said this article has been archived by the "
                   "museum, and the rest of the story continues.")
    assert "the rest of the story continues" in kept


def test_mid_article_notes_section_survives():
    """`notes?` was in _TAIL with DOTALL, so a mid-article == Notes == cut the body."""
    F = _wikinews()
    out = F.clean("Body text.\n== Notes ==\na footnote. More body prose here.\n"
                  "== Sources ==\n* link")
    assert "More body prose here." in out
    assert "link" not in out, "the terminal Sources section should still go"


def test_site_switching_is_explicit_and_validated():
    before = MW.API
    try:
        assert MW.use_site("wikinews").endswith("en.wikinews.org/w/api.php")
        assert MW.use_site("wikisource").endswith("en.wikisource.org/w/api.php")
        with pytest.raises(ValueError):
            MW.use_site("wikipedia")
    finally:
        MW.API = before


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
