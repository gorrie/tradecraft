"""A boundary inside a contraction is not a boundary (PREREG-2026-09-07-cue-repair.md).

`you haven` matched inside "you haven't" because the apostrophe is not a word character. The
guard rejects a match followed by an apostrophe and a letter, keeps the possessive, keeps a
closing quote, and leaves every ordinary boundary alone.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tradecraft import detect as D  # noqa: E402


def spans(cue, text):
    return [text[a:b] for a, b in D._find_all_bounded(cue, text)]


def test_contraction_is_not_a_boundary():
    assert spans("you haven", "If you haven't been keeping up, you haven't.") == []
    assert spans("we", "we're here; we’ll stay") == []


def test_possessive_and_closing_quote_still_match():
    assert spans("class struggle", "the class struggle's history") == ["class struggle"]
    assert spans("needle", "he said 'needle' twice") == ["needle"]
    assert spans("needle", "the ‘needle’ again") == ["needle"]


def test_ordinary_boundaries_unchanged():
    assert spans("class struggle", "class struggles everywhere; class struggle.") == ["class struggles", "class struggle"]
    assert spans("regime", "the regimen") == []


def test_guard_flag_is_the_only_difference():
    text = "you haven't"
    D.CONTRACTION_GUARD = False
    try:
        off = spans("you haven", text)
    finally:
        D.CONTRACTION_GUARD = True
    assert off == ["you haven"] and spans("you haven", text) == []
