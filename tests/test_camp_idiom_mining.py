"""The canon-mining tools: three confounds that each pass silently and flatter the result.

WHY THIS FILE EXISTS
--------------------
`corpus/mine_camp_idiom.py` proposes cues for a human to rule on. Every defect it can have
produces a plausible candidate list rather than an error, so each of the three found on
2026-09-03 while mining `georgist` is pinned here.

  1. NESTED TEMPLATES. A non-greedy `{{.*?}}` stops at the first `}}`, so a Wikisource header
     leaves its own field names in the prose. `header title`, `author henry george`,
     `notes smalltoc` and `title chapters` all reached the top of a candidate list, each in 27
     of 28 canon files.

  2. SATURATION. Structural boilerplate appears in nearly every document of a canon; real idiom
     concentrates in a minority of them. `natural opportunities` sat in 9 of 28 files while every
     piece of scaffolding sat in 27 or 28.

  3. ORTHOGRAPHY. The Wikisource *Wealth of Nations* is an American edition (`labor` 1,324,
     `labour` 56); George is British (`labour` 576). So `produce of labour` measured ZERO in the
     discipline control and passed as a Georgist shibboleth, while `produce of labor` occurs 8
     times in that same text. Every -our/-ise gram in a British canon clears an American control
     for free, and nothing about the output looks wrong.

Run with `pytest` or directly: `python tests/test_camp_idiom_mining.py`.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "corpus"))

import fetch_wikisource as FW  # noqa: E402
import mine_camp_idiom as MC  # noqa: E402


# ------------------------------------------------- confound 1: nested templates

def test_strip_templates_handles_nesting():
    got = FW.strip_templates(
        "{{header|title=Progress and Poverty|author=Henry George|notes={{smalltoc}}}}"
        "Real prose begins here.")
    assert got.strip() == "Real prose begins here."
    assert "header" not in got and "smalltoc" not in got


def test_strip_templates_leaves_prose_between_templates():
    got = FW.strip_templates("{{a}}one{{b|x={{c}}}}two{{d}}")
    assert got == "onetwo"


def test_strip_templates_tolerates_unbalanced_braces():
    """A malformed transcription must not swallow the whole page."""
    assert "prose" in FW.strip_templates("{{broken|x=1 prose continues")


def test_plain_drops_header_field_names():
    text = FW.plain("{{header|title=T|author=Henry George|notes={{smalltoc}}}}"
                    "The term land includes all natural opportunities and forces.")
    assert "natural opportunities" in text
    for leak in ("header", "author henry george", "smalltoc", "title"):
        assert leak not in text.lower()


# ------------------------------------------------- confound 3: orthography

def test_normalise_folds_british_to_american():
    assert MC.normalise("the produce of labour") == "the produce of labor"
    assert MC.normalise("Labour and Capital") == "Labor and Capital"
    assert MC.normalise("neighbourhood") == "neighbourhood"      # not in the map, left alone


def test_normalise_makes_the_two_editions_comparable():
    """The actual defect: a British gram must be findable in an American control."""
    george = MC.normalise("the produce of labour is divided")
    smith = MC.normalise("the produce of labor makes a third component part")
    assert "produce of labor" in george
    assert "produce of labor" in smith


# ------------------------------------------------- T3.2: the same defect in other languages

def test_arabic_alef_variants_fold_together():
    """Hamza-carrying alefs are written inconsistently and often bare. Unnormalised, an Arabic
    cue misses most of its own occurrences -- the labour/labor defect with a bigger blast
    radius."""
    assert MC.normalise("أحمد") == MC.normalise("احمد")
    assert MC.normalise("إسلام") == MC.normalise("اسلام")
    assert MC.normalise("آخر") == MC.normalise("اخر")


def test_arabic_ta_marbuta_and_alef_maqsura_fold():
    assert MC.normalise("مدرسة") == MC.normalise("مدرسه")
    assert MC.normalise("على") == MC.normalise("علي")


def test_arabic_harakat_and_tatweel_are_stripped():
    """Short-vowel marks and the elongation character are optional decoration."""
    assert MC.normalise("كِتَاب") == MC.normalise("كتاب")
    assert MC.normalise("كــتاب") == MC.normalise("كتاب")


def test_hebrew_niqqud_is_stripped_and_finals_fold():
    """Niqqud is usually absent, and the five final forms are the same letters positionally."""
    assert MC.normalise("שָׁלוֹם") == MC.normalise("שלום")
    assert MC.normalise("שלום") == MC.normalise("שלומ")


def test_german_eszett_folds_to_ss():
    assert MC.normalise("Straße") == "Strasse"


def test_script_folding_leaves_latin_and_cyrillic_alone():
    """A fold that reached into unrelated scripts would silently merge distinct words."""
    assert MC.normalise("the productive forces") == "the productive forces"
    assert MC.normalise("русский мир") == "русский мир"


def test_normalise_does_not_mangle_ordinary_words():
    for word in ("our", "four", "hour", "flour", "tour", "pour", "sour", "your"):
        assert MC.normalise(word) == word


def test_normalise_is_idempotent():
    once = MC.normalise("labour and the neighbour's colour")
    assert MC.normalise(once) == once


# ------------------------------------------------- confound 2: saturation, and the nav list

def test_nav_pattern_rejects_transcription_navigation():
    for gram in ("chapter x", "book ii", "part iii", "section v", "contents index"):
        assert MC.NAV.search(gram), gram


def test_nav_pattern_keeps_real_idiom():
    for gram in ("natural opportunities", "labor and capital", "margin of cultivation",
                 "unearned increment", "land value tax"):
        assert not MC.NAV.search(gram), gram


# ------------------------------------------------- confound 4: scholarly apparatus

def test_apparatus_pattern_rejects_citation_machinery():
    """`op cit` cleared both controls 16 times across 6 files -- a footnote, not a shibboleth."""
    for gram in ("op cit", "loc cit", "ibid", "et al", "quoted in", "translated by"):
        assert MC.APPARATUS.search(gram), gram


def test_apparatus_pattern_keeps_real_idiom():
    for gram in ("finance capital", "second international", "left communists",
                 "natural opportunities", "dictatorship of the proletariat"):
        assert not MC.APPARATUS.search(gram), gram


# ------------------------------------------------- confound 5: header/title leakage at source

def test_strip_elements_removes_the_wikisource_header_block():
    """The block carrying work title, year and author -- class `ws-noexport` by Wikisource's
    own admission that it is not part of the text. Left in, it put book titles and the author
    name at the top of a candidate list."""
    html = ('<div class="mw-parser-output"><div class="ws-noexport">'
            '<div class="wst-header-mainblock">Imperialism, the Last Stage of Capitalism '
            '(1926) by N. Lenin</div></div>APPENDIX begins here.</div>')
    got = FW.plain(html)
    assert "APPENDIX begins here." in got
    for leak in ("Lenin", "1926", "Imperialism"):
        assert leak not in got, leak


def test_strip_elements_handles_nested_divs_without_eating_the_body():
    html = ('<div class="ws-noexport"><div><div>nav</div></div></div>'
            'the real argument follows')
    assert FW.plain(html).strip() == "the real argument follows"


def test_strip_elements_leaves_ordinary_divs_alone():
    assert "kept" in FW.plain('<div class="prose">kept</div>')


# ------------------------------------------------- confound 8: the polemical target's terms

def test_quoted_share_separates_an_opponents_term_from_the_camps_own():
    """The case it was built for: Proudhon's `constituted value` inside Marx's canon.

    A camp quotes its opponents at length in order to attack them, and the opponent is not in
    the discipline control either -- so frequency, dispersion and both controls all agree the
    term is idiom. Only the quotation context separates them.
    """
    own = ("The bourgeoisie has created more colossal productive forces than all preceding "
           "generations. These productive forces are the basis of modern industry, and the "
           "productive forces develop further still.")
    borrowed = ('M. Proudhon says that "constituted value" is the solution. According to '
                'M. Proudhon, "constituted value" explains everything. He calls it '
                '"constituted value" throughout.')
    assert MC.quoted_share("productive forces", own) < 0.5
    assert MC.quoted_share("constituted value", borrowed) >= 0.5


def test_quoted_share_is_zero_when_the_gram_is_absent():
    assert MC.quoted_share("nothing here", "an unrelated sentence entirely.") == 0.0


def test_quoted_share_counts_attribution_without_quote_marks():
    """Attribution alone is enough -- reported speech often carries no quotation marks."""
    assert MC.quoted_share("constituted value", "according to Proudhon constituted value is "
                                                "the answer") == 1.0


def test_attribution_pattern_does_not_fire_on_ordinary_prose():
    for text in ("the productive forces of society", "the means of production were seized"):
        assert not MC.ATTRIBUTION.search(text), text


def test_ngrams_skip_navigation_and_stopword_edges():
    grams = set(MC.ngrams("chapter x the margin of cultivation is fixed by natural "
                          "opportunities", 2, 3))
    assert "margin of cultivation" in grams
    assert "natural opportunities" in grams
    assert not any("chapter" in g for g in grams)
    assert not any(g.startswith("the ") or g.endswith(" the") for g in grams)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
