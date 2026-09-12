"""Script/charset profiling: the OSINT layer that needs no vocabulary.

The point of this profiler is that it works in languages nobody here reads, which means nobody
here will notice if it quietly stops working. So the assertions are concrete and per-script, and
the most important one is the LAST: plain English must produce no findings, because a profiler
that flags everything is a profiler that gets ignored.

Run with `pytest` or directly: `python tests/test_script_profile.py`.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tradecraft import script_profile as SP  # noqa: E402
from tradecraft.grader import _script_summary, grade_document  # noqa: E402
from tradecraft.loader import load_lenses  # noqa: E402
from tradecraft.subject import grade_person  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CLEAN = "An ordinary paragraph of plain English prose with nothing unusual about it."


# ------------------------------------------------- script identification

def test_script_of_names_the_writing_system():
    assert SP.script_of("a") == "LATIN"
    assert SP.script_of("а") == "CYRILLIC"
    assert SP.script_of("د") == "ARABIC"
    assert SP.script_of("א") == "HEBREW"
    assert SP.script_of("下") == "CJK"
    assert SP.script_of("ह") == "DEVANAGARI"
    assert SP.script_of("α") == "GREEK"
    assert SP.script_of("1") is None          # not a letter
    assert SP.script_of(" ") is None


def test_alphabetic_characters_with_no_unicode_name_are_bucketed_not_dropped():
    """U+17000 (Tangut) is category Lo but has no UCD name, so name() raises.

    A real character rather than a mocked one. Dropping it would silently shrink the letter
    count that every share in this profile is divided by, so it is bucketed as UNNAMED and
    stays visible.
    """
    tangut = "\U00017000"
    assert tangut.isalpha()
    assert SP.script_of(tangut) == "UNNAMED"
    p = SP.profile(tangut + tangut + "ab")
    assert p["letters"] == 4
    assert p["scripts"]["UNNAMED"] == 0.5


def test_shares_are_reported_per_script():
    p = SP.profile("hello добро")
    assert set(p["scripts"]) == {"LATIN", "CYRILLIC"}
    assert abs(sum(p["scripts"].values()) - 1.0) < 1e-6
    assert p["script_count"] == 2


def test_dominant_script_is_the_largest_share():
    p = SP.profile("mostly english with one д cyrillic letter")
    assert p["dominant_script"] == "LATIN"


def test_a_diaspora_style_mix_is_profiled_without_false_flags():
    """Two scripts in separate words is bilingual prose, not evasion."""
    p = SP.profile("wrote دار الحرب and also "
                   "dar al-harb in transliteration")
    assert set(p["scripts"]) == {"LATIN", "ARABIC"}
    assert p["mixed_script_total"] == 0, p["mixed_script_words"]


# ------------------------------------------------- the operationally useful part

def test_mixed_script_inside_one_word_is_flagged_with_a_receipt():
    p = SP.profile("the Кiev regime")
    assert p["mixed_script_total"] == 1
    entry = p["mixed_script_words"][0]
    assert entry["word"] == "Кiev"
    assert entry["scripts"] == ["CYRILLIC", "LATIN"]
    # A receipt is only a receipt if it locates the thing.
    assert "the Кiev regime"[entry["offset"]:].startswith("Кiev")


def test_latin_lookalikes_are_called_out_specifically():
    """The deliberate subset: a word that reads as Latin but will not match a Latin cue."""
    p = SP.profile("ruѕѕian world")
    assert p["confusable_total"] == 1
    assert "ѕ->s" in p["confusable_words"][0]["latin_lookalikes"]


def test_a_confusable_word_defeats_a_plain_substring_search():
    """Why this matters at all, asserted rather than described."""
    text = "ruѕѕian world"
    assert "russian" not in text.lower()
    assert SP.profile(text)["confusable_total"] == 1


def test_invisible_and_bidi_characters_are_counted():
    p = SP.profile("hidden​zero width and ‮an override")
    assert p["invisibles"]["ZERO WIDTH SPACE"] == 1
    assert p["invisibles"]["RIGHT-TO-LEFT OVERRIDE"] == 1


def test_diacritic_rate_separates_native_from_stripped_transliteration():
    native = SP.profile("résumé naı̈ve")     # combining marks
    stripped = SP.profile("resume naive")
    assert native["diacritic_rate"] > 0
    assert stripped["diacritic_rate"] == 0


# ------------------------------------------------- the anti-noise assertion

def test_plain_english_produces_no_findings():
    p = SP.profile(CLEAN)
    assert p["script_count"] == 1
    assert p["mixed_script_total"] == 0
    assert p["confusable_total"] == 0
    assert p["invisibles"] == {}
    assert p["diacritic_rate"] == 0


def test_empty_text_does_not_divide_by_zero():
    p = SP.profile("")
    assert p["letters"] == 0
    assert p["dominant_script"] is None


def test_profiler_makes_no_verdict_claim():
    """Flag with receipts, never a verdict -- so no field here scores or ranks anything."""
    p = SP.profile("the Кiev regime")
    for banned in ("index", "score", "verdict", "rank", "grade"):
        assert banned not in p, banned


# ------------------------------------------------- T3.5: wired into the scoring path

def test_grade_document_attaches_a_script_profile_when_given_text():
    lenses = load_lenses(os.path.join(REPO_ROOT, "detectors"))
    tax = {"legibility": lenses["legibility"]}
    with_text = grade_document(tax, {}, token_count=10, text="the Кiev regime")
    assert with_text.script is not None
    assert with_text.script["confusable_total"] >= 0
    assert with_text.script["mixed_script_total"] == 1


def test_grade_document_without_text_carries_no_script_profile():
    """None means NOT MEASURED, which is a different statement from "nothing found"."""
    lenses = load_lenses(os.path.join(REPO_ROOT, "detectors"))
    tax = {"legibility": lenses["legibility"]}
    assert grade_document(tax, {}, token_count=10).script is None


def test_the_script_profile_cannot_change_any_index():
    """It is context, not a lens. Same hits must give the same scores either way."""
    lenses = load_lenses(os.path.join(REPO_ROOT, "detectors"))
    tax = {"legibility": lenses["legibility"]}
    a = grade_document(tax, {}, token_count=10)
    b = grade_document(tax, {}, token_count=10, text="the Кiev regime and ruѕѕian world")
    assert a.lenses["legibility"].index == b.lenses["legibility"].index
    assert a.lenses["legibility"].tier == b.lenses["legibility"].tier


def test_subject_summary_counts_documents_not_words():
    """One document full of substitutions differs from a whole corpus of them."""
    lenses = load_lenses(os.path.join(REPO_ROOT, "detectors"))
    texts = [
        {"id": "d1", "date": "2024-01-01", "text": "Ordinary English prose about councils."},
        {"id": "d2", "date": "2024-02-01",
         "text": "دار الحرب and also dar al-harb transliterated."},
        {"id": "d3", "date": "2024-03-01", "text": "The ruѕѕian world, with a hidden​char."},
    ]
    sp, docs = grade_person(lenses, "subj", texts)
    s = sp.script
    assert s["documents_profiled"] == 3
    assert s["scripts_seen"]["LATIN"] == 3
    assert set(s["scripts_seen"]) == {"LATIN", "ARABIC", "CYRILLIC"}
    # d2 and d3 are multiscript; only d3 mixes scripts INSIDE a word.
    assert s["documents_multiscript"] == 2
    assert s["documents_with_mixed_script_words"] == 1
    assert s["documents_with_confusables"] == 1
    assert s["documents_with_invisibles"] == 1


def test_bilingual_prose_is_not_reported_as_mixed_script():
    """The distinction that makes this useful rather than alarmist."""
    lenses = load_lenses(os.path.join(REPO_ROOT, "detectors"))
    sp, _ = grade_person(lenses, "subj", [
        {"id": "d1", "text": "ארץ ישראל and the same idea in English."}])
    assert sp.script["documents_multiscript"] == 1
    assert sp.script["documents_with_mixed_script_words"] == 0


def test_script_summary_is_none_when_nothing_was_profiled():
    assert _script_summary([]) is None


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
