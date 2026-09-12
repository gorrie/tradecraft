"""Unicode word boundaries: the two failure modes, and why both had to be measured.

WHAT LANDED (2026-09-03, T3.1 of BACKLOG-shibboleth-corpus-study.md)
--------------------------------------------------------------------
The boundary rule was `[A-Za-z0-9_]` on both sides, so **every non-Latin cue was a PREFIX
match**: an Arabic cue fired inside its own adjectival form, a Cyrillic cue inside a longer
adjective. Recall worked in every script and precision worked in none, which is the worst
arrangement because the output looks fine.

FAILURE MODE ONE: pairing the two runtimes wrongly. Python `\\w` and JS `/[\\p{L}\\p{N}_]/u`
are equivalent -- 0 divergences over 47 characters spanning nine scripts, four digit systems,
combining marks and ZWJ -- but two plausible alternatives are NOT, and only measuring found
them: JS `\\w` is ASCII-only EVEN WITH the `u` flag (29 divergences), and adding `\\p{M}`
diverges on every Arabic harakat and Devanagari vowel sign. Parity is a CI gate, so a wrong
pairing would have broken the browser engine against Python on exactly the text nobody checks.

FAILURE MODE TWO, which the fix itself introduced: scripts written without spaces. In CJK every
occurrence is flanked by letters, so a Unicode boundary rule refuses **everything**. The cue
天下为公 stopped matching 他们说天下为公很重要 at all -- from "fires but leaks" to "never
fires", a strictly worse outcome that would have shipped as a Unicode improvement. Each cue edge
is now exempted independently when it sits in a scriptio-continua range.

Run with `pytest` or directly: `python tests/test_multilingual_boundaries.py`.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tradecraft.detect import _find_all_bounded, _unspaced, _WORDCHAR  # noqa: E402

# (label, cue, text where the cue stands alone, text where it is embedded)
BOUNDED = [
    ("cyrillic", "русский мир",
     "идея русский мир жива",
     "русский мировой"),
    ("arabic", "دار الحرب",
     "في دار الحرب اليوم",
     "دار الحربية"),
    ("hebrew", "ארץ ישראל",
     "בתוך ארץ ישראל היום",
     "ארץ ישראלי"),
    ("devanagari", "हिन्दू राष्ट्र",
     "यह हिन्दू राष्ट्र है",
     "हिन्दू राष्ट्रवाद"),
    ("greek", "μεγάλη ιδέα",
     "η μεγάλη ιδέα ήταν",
     "μεγάλη ιδέας"),
    ("latin_diacritic", "regime", "the regime fell", "Regimeänderung was the goal"),
]

UNSPACED = [
    ("cjk", "天下为公", "他们说天下为公很重要"),
    ("kana", "あの世", "それはあの世です"),
]


@pytest.mark.parametrize("label,cue,positive,embedded", BOUNDED,
                         ids=[c[0] for c in BOUNDED])
def test_cue_fires_on_a_real_instance(label, cue, positive, embedded):
    assert _find_all_bounded(cue, positive), "%s cue does not fire at all" % label


@pytest.mark.parametrize("label,cue,positive,embedded", BOUNDED,
                         ids=[c[0] for c in BOUNDED])
def test_cue_refuses_to_match_inside_a_longer_word(label, cue, positive, embedded):
    """The defect this fix closed. Every one of these leaked under the ASCII rule."""
    assert not _find_all_bounded(cue, embedded), (
        "%s cue matched inside a longer word -- it is behaving as a prefix match" % label)


@pytest.mark.parametrize("label,cue,positive", UNSPACED, ids=[c[0] for c in UNSPACED])
def test_scripts_without_spaces_still_fire(label, cue, positive):
    """The regression the Unicode fix introduced: a boundary rule refuses all of CJK."""
    assert _find_all_bounded(cue, positive), (
        "%s cue does not fire; a script with no spaces has every occurrence flanked by "
        "letters, so the boundary rule must be exempted there" % label)


def test_english_behaviour_is_unchanged():
    """The rule got stricter for non-ASCII neighbours only. English must not move."""
    assert _find_all_bounded("regime change", "they demanded regime change now")
    assert not _find_all_bounded("regime", "the regimen was strict")
    assert not _find_all_bounded("needle", "the needlework was fine")
    # Suffix absorption still works, which is a separate rule that shares this code path.
    assert _find_all_bounded("class struggle", "the class struggles continue")


def test_wordchar_is_unicode_aware():
    for ch in "aZ5_éüаدאह下α":
        assert _WORDCHAR.match(ch), ch
    for ch in " -.'":
        assert not _WORDCHAR.match(ch), ch


def test_combining_marks_are_not_word_characters():
    """A deliberate, documented limit -- identical on both sides, so parity holds.

    A cue followed by a combining mark still matches. Fixing that needs grapheme-cluster
    awareness. Pinned so the behaviour is a decision rather than a surprise.
    """
    assert not _WORDCHAR.match("َ")     # ARABIC FATHA
    assert not _WORDCHAR.match("ְ")     # HEBREW POINT SHEVA
    assert not _WORDCHAR.match("्")     # DEVANAGARI SIGN VIRAMA


def test_unspaced_covers_the_scriptio_continua_ranges():
    for ch in "下ア あ๑ຫཀကក":
        if ch == " ":
            continue
        assert _unspaced(ch), repr(ch)


def test_unspaced_excludes_scripts_that_use_spaces():
    """Hangul is the trap here: Korean is not scriptio continua."""
    for ch in "aЯدאहα한":
        assert not _unspaced(ch), repr(ch)
    assert not _unspaced("")


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
