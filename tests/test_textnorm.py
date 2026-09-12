"""`textnorm.clean` must remove markup and NOT remove prose."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "corpus"))

from textnorm import clean, has_markup  # noqa: E402


def test_inline_formatting_closes_up():
    """`H<INF>2</INF>O` is ONE token, not three. Mapping every tag to a space split it."""
    assert clean("H<INF>2</INF>O") == "H2O"
    assert clean("a <b>bold</b> word") == "a bold word"


def test_block_markup_opens_a_gap():
    """`one<br/>two` is two words. Mapping every tag to nothing welded them."""
    assert clean("one<br/>two") == "one two"
    assert clean("statute.<br/>Thank you.") == "statute. Thank you."


def test_entities_are_decoded():
    assert clean("a &rsquo;s &amp; b") == "a ’s & b"
    assert clean("a&#160;b") == "a b"


def test_cloudflare_email_element_goes_whole():
    """The visible content is a placeholder; unwrapping it puts it in the word stream."""
    src = '<span class="__cf_email__" data-cfemail="ab">[email protected]</span> ok'
    assert clean(src) == "ok"


def test_less_than_in_prose_survives():
    """THE REGRESSION THIS FILE EXISTS FOR.

    `<[^>]{0,400}>` matched any `<...>` span, so a rulemaking that says
    `precipitation <20 inches/year) for disposal years prior to 2010` lost the whole clause --
    from a real record, fr_2024-07413. A tag name is required after the `<`.
    """
    t = "precipitation <20 inches/year) for disposal years prior to 2010."
    assert clean(t) == t
    assert clean("5 < 7 and 9 > 3") == "5 < 7 and 9 > 3"


def test_idempotent():
    """A second pass must be a no-op, or the repair script can never report itself finished."""
    for t in ("H<INF>2</INF>O", "one<br/>two", "precipitation <20 inches/year)", "plain"):
        assert clean(clean(t)) == clean(t)


def test_has_markup_agrees_with_clean():
    for t in ("plain text", "5 < 7", "one<br/>two", "a&#160;b"):
        assert has_markup(t) == (clean(t) != t)


def test_empty_and_none_safe():
    assert clean("") == ""
    assert clean(None) == ""
    assert has_markup("") is False
