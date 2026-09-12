"""The scriptio-continua range table is hand-copied into two runtimes. Hold them identical.

WHY THIS EXISTS
---------------
`detect.py::_NO_WORD_BOUNDARY` and `engine.js`'s `NO_WORD_BOUNDARY` are the same ten codepoint
ranges written out twice. That duplication is deliberate and correct -- the JS comment gives the
reason, and it is a good one:

    "Literal codepoint ranges, identical to detect.py's _NO_WORD_BOUNDARY, rather than
     \\p{Script=...} -- a range table cannot drift between two runtimes' Unicode databases."

A range table cannot drift between Unicode *databases*. It can absolutely drift between two
files, and nothing was checking that it had not.

WHY THE EXISTING GUARDS DO NOT COVER IT
---------------------------------------
This is the same shape as the `EXCLUDE_WINDOW` duplication that the 2026-09-11 hostile read
looked at -- except that one is caught by the parity fixtures (diverging it fails
`test_engine_parity.py` at 71/73), and **this one is not, because it cannot be.** The parity
harness compares the two engines on the shipped eval fixtures, and measured 2026-09-11:

    total cues in all taxonomies : 803
    cues containing a scriptio-continua character : 0

Zero. So no fixture exercises any of these ranges, every fixture passes under either table, and
a wrong range would ship silently until the first CJK/Thai/Khmer cue arrived -- which is T3.2,
blocked on corpora, and could be months. The gap is exactly the interval in which nobody would
find out.

WHAT THIS DOES NOT DO
---------------------
It does not test segmentation. Exempting a boundary makes a CJK cue *fire*; it does not stop it
firing on a substring of a longer compound, which is the deferred half of T3.4. That half guards
0 of 803 cues today and is left deferred rather than built speculatively -- see
`BACKLOG-shibboleth-corpus-study.md` T3.4 and the 2026-09-11 note there.
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)

JS = os.path.join(os.path.dirname(REPO), "website", "static", "tech", "instrument", "engine.js")


def _js_ranges(src: str):
    """The NO_WORD_BOUNDARY literal from engine.js, as a list of (lo, hi)."""
    m = re.search(r"var\s+NO_WORD_BOUNDARY\s*=\s*\[(.*?)\];", src, re.S)
    assert m, "NO_WORD_BOUNDARY array not found in engine.js"
    pairs = re.findall(r"\[\s*(0x[0-9A-Fa-f]+)\s*,\s*(0x[0-9A-Fa-f]+)\s*\]", m.group(1))
    return [(int(a, 16), int(b, 16)) for a, b in pairs]


def test_range_tables_are_identical():
    from tradecraft.detect import _NO_WORD_BOUNDARY as PY

    js = _js_ranges(io.open(JS, encoding="utf-8").read())
    py = [tuple(r) for r in PY]
    assert js == py, (
        "scriptio-continua tables diverged.\n"
        "  engine.js : %r\n  detect.py : %r\n"
        "Both must list the same ranges in the same order." % (js, py)
    )


def test_hangul_is_absent_from_both():
    """Korean uses spaces, so Hangul must NOT be exempted from the boundary rule.

    Asserted rather than assumed because it is the one range a reader adds by reflex when the
    comment says 'CJK' -- and adding it would turn every Korean cue into a prefix match.
    """
    from tradecraft.detect import _NO_WORD_BOUNDARY as PY

    hangul = 0xAC00          # HANGUL SYLLABLE GA
    for lo, hi in list(PY) + _js_ranges(io.open(JS, encoding="utf-8").read()):
        assert not (lo <= hangul <= hi), "Hangul (U+AC00) is inside range (0x%X, 0x%X)" % (lo, hi)


def test_both_runtimes_agree_character_by_character():
    """Walk one representative codepoint per range, plus Latin and Hangul controls.

    Range-table equality above is the strong check; this is the behavioural one, and it fails
    loudly if someone reimplements `_unspaced` in terms of something other than the table.
    """
    from tradecraft.detect import _unspaced

    js = _js_ranges(io.open(JS, encoding="utf-8").read())

    def js_unspaced(cp):
        return any(lo <= cp <= hi for lo, hi in js)

    probes = [lo for lo, _ in js] + [hi for _, hi in js] + [
        ord("a"), ord("Z"), ord("0"), 0xAC00, 0x0627, 0x05D0, 0x0400,
    ]
    for cp in probes:
        assert _unspaced(chr(cp)) == js_unspaced(cp), (
            "runtimes disagree on U+%04X: python=%s js=%s"
            % (cp, _unspaced(chr(cp)), js_unspaced(cp))
        )


def test_no_cjk_cue_ships_without_this_guard():
    """Documents the reason this file exists, and self-retires when it stops being true.

    While zero shipped cues contain a scriptio-continua character, the parity fixtures cannot
    catch a table divergence and this test is the only thing that can. Once T3.2 lands cues in
    these scripts the fixtures start covering it too -- at which point this assertion fails and
    whoever sees it should read the docstring above and relax it, not delete the file.
    """
    import glob

    import yaml

    from tradecraft.detect import _unspaced

    n_cues = n_cjk = 0
    for path in sorted(glob.glob(os.path.join(REPO, "detectors", "*", "taxonomy.yaml"))):
        tax = yaml.safe_load(io.open(path, encoding="utf-8"))
        for marker in tax.get("markers", []):
            for det in marker.get("detections", []):
                for cue in (det.get("cues") or []):
                    n_cues += 1
                    if any(_unspaced(ch) for ch in cue):
                        n_cjk += 1
    assert n_cues > 100, "taxonomies did not load (%d cues)" % n_cues
    assert n_cjk == 0, (
        "%d of %d cues now contain a scriptio-continua character. The parity fixtures should "
        "now cover the range tables directly -- re-read this file's docstring and widen the "
        "guard rather than dropping it." % (n_cjk, n_cues)
    )
