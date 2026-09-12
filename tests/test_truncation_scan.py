"""The truncation scanner must catch the four real cases and stay quiet on correct data.

Truncation is the most-repeated defect class in this project -- a fixed-size background pool,
a hardcoded 800-token generation budget, a regex that truncated its own match, hearings sliced
at ~5,000 words -- and every instance was found by accident. The scanner generalises the
signature instead of patching the cases.

Half of these tests are FALSE-POSITIVE guards, and they matter as much as the detections. The
first run against run records reported 27 of 32 forced-choice answer sheets as truncated: they
end `62. Strongly Disagree`, which is a complete sheet. A scanner that flags correct data is a
scanner someone turns off, and then it catches nothing.

Run with `pytest` or directly: `python tests/test_truncation_scan.py`.
"""
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import truncation_scan as T  # noqa: E402


# ---------------------------------------------------------------- cap spike

def test_a_wall_at_the_maximum_is_a_cap():
    """94 of 95 documents at exactly 3,200 words: the real _news-control shape."""
    vals = [3200] * 94 + [1090]
    got = T.cap_spike(vals)
    assert got is not None
    share, top = got
    assert top == 3200
    assert share > 0.9


def test_a_real_length_distribution_is_not_a_cap():
    vals = [120, 180, 210, 240, 303, 340, 410, 520, 700, 1100, 12500]
    assert T.cap_spike(vals) is None


def test_too_few_values_to_judge():
    assert T.cap_spike([100, 100, 100]) is None


# ---------------------------------------------------------------- soft cap

def test_values_crowding_under_the_maximum_are_a_soft_cap():
    """The advocacy-specimens shape: hearings sliced at ~5,000 words, trimmed to a boundary."""
    vals = [4700, 4750, 4789, 4800, 4850, 4900, 4950, 5000, 5100, 5202, 3000, 2000]
    got = T.soft_cap(vals)
    assert got is not None
    share, top = got
    assert top == 5202
    assert share >= T.SOFT_CAP_SHARE


def test_a_long_tail_is_not_a_soft_cap():
    """A genuinely spread distribution must not read as a cutter.

    REWRITTEN 2026-09-04. This test used method-specimens' WORD counts and its docstring said
    "38% within 10% of max is a real distribution, not a cutter" -- asserting that a corpus
    which IS truncated passes clean, which is the detector-loosening this project forbids,
    written into the test suite. That corpus is cut at 6,000 CHARACTERS: 54% sit exactly on
    the maximum and 86% within 10% of it. The fixture below is now a synthetic spread, and
    the real corpus is asserted to FAIL in test_the_character_cap_is_caught below.
    """
    vals = [120, 200, 340, 480, 610, 900, 1400, 2200, 3600, 5000, 9000, 14000]
    assert T.soft_cap(vals) is None
    assert T.cap_spike(vals) is None


def test_the_character_cap_is_caught():
    """The scanner missed its own headline case because it only counted words."""
    chars = [6000] * 84 + list(range(1200, 5900, 60))[:71]
    got = T.cap_spike(chars)
    assert got is not None, "84 of 155 at exactly 6000 must read as a cap"
    share, top = got
    assert top == 6000
    assert share >= T.CAP_SHARE
    assert T.round_ceiling(6000) == "a round multiple of 1000"


def _cut_corpus(tmp_path, n_cut=84, n_free=71, cap=6000):
    """A JSONL with the shape method-specimens.jsonl HAD: `n_cut` documents at exactly `cap`
    characters, the rest genuinely varied and longer.

    THIS IS SYNTHETIC ON PURPOSE, and the change is worth stating. These assertions used to run
    against the live `corpus/method-specimens.jsonl`, which pinned the detector's proof of
    power to a corpus defect -- so REPAIRING the corpus broke the tests that prove the detector
    works, and the cheap way out is to weaken them. The detector's capability and the corpus's
    condition are two different claims and now have two different tests: capability here,
    condition in `test_the_repaired_corpora_are_clean`.
    """
    import random
    rng = random.Random(7)
    p = tmp_path / "cut.jsonl"
    rows = []
    for i in range(n_cut):
        rows.append({"id": "cut%03d" % i, "text": ("word%04d " % i * 2000)[:cap]})
    for i in range(n_free):
        rows.append({"id": "free%03d" % i,
                     "text": "w " * rng.randint(cap // 2 + 500, 4 * cap)})
    p.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    return str(p)


def test_scan_measures_characters_as_well_as_words(tmp_path):
    """A CHARACTER cut must be found. This tool once looked only at word counts, and the cut
    it was written for was `[:6000]` on a joined string, so it reported no signature."""
    rep = T.scan(_cut_corpus(tmp_path))
    assert rep["n"] >= 100, rep
    kinds = {f["kind"] for f in rep["findings"]}
    assert kinds & {"cap-spike", "soft-cap", "wall"}, (
        "the 6,000-character cut must be detected, got %r" % rep["findings"])
    assert any("character" in f["detail"] for f in rep["findings"]), rep["findings"]


def test_the_repaired_corpora_are_clean():
    """CONDITION, not capability: the specimen corpora carry no undeclared cap any more.

    Both were refetched BY ID at full length on 2026-09-05 -- same documents, same order, one
    factor different -- and this is the assertion that notices if a later fetch reintroduces a
    cut. `method-specimens` went from 84 of 155 at exactly 6,000 characters to a median of
    31,433; `advocacy-specimens` from 15 of 18 at exactly 30,000 to a median of 133,861.
    """
    for name in ("method-specimens.jsonl", "advocacy-specimens.jsonl"):
        path = os.path.join(ROOT, "corpus", name)
        rep = T.scan(path) if os.path.exists(path) else None
        if rep is None:
            pytest.skip("corpus/%s holds no documents in this checkout" % name)
        kinds = {f["kind"] for f in rep["findings"]}
        assert not kinds & {"cap-spike", "soft-cap", "wall"}, (name, rep["findings"])


# ---------------------------------------------------------------- interior wall
#
# cap_spike and soft_cap test only the MAXIMUM. The fetchers append and skip ids they already
# hold, so raising --chars once buries the old wall under a new maximum and the corpus reads
# as clean. All numbers below were run, not chosen.

def _live_shape():
    """84 at exactly 6,000 characters plus 90 uncapped longer documents, 6,100..20,000."""
    import random
    rng = random.Random(1)
    return [6000] * 84 + sorted(rng.randint(6100, 20000) for _ in range(90))


def test_the_old_detectors_are_blind_to_a_buried_wall():
    """The premise, asserted so a later change to cap_spike cannot make this suite vacuous."""
    vals = _live_shape()
    assert T.cap_spike(vals) is None, "48% at the max is under CAP_SHARE by construction"
    assert T.soft_cap(vals) is None


def test_a_wall_below_the_maximum_is_found():
    got = T.walls(_live_shape())
    assert got, "84 identical multi-thousand-character lengths are not chance"
    count, value, share = got[0]
    assert (count, value) == (84, 6000)
    assert share >= T.CAP_SHARE
    assert T.round_ceiling(value) == "a round multiple of 1000"


def test_a_wall_at_the_maximum_under_cap_share_is_still_a_wall():
    """84 at 6,000 with 90 SHORTER varied documents: cap_spike misses it at 48%, walls does not."""
    import random
    rng = random.Random(2)
    vals = [6000] * 84 + [rng.randint(1200, 5300) for _ in range(90)]
    assert T.cap_spike(vals) is None
    assert [(c, v) for c, v, _ in T.walls(vals)] == [(84, 6000)]


def test_dense_discreteness_is_not_a_wall():
    """1,000 word counts over 500..900 tie 9 deep at the mode; the mode is a sliver of its band."""
    import random
    import collections
    rng = random.Random(1)
    vals = [rng.randint(500, 900) for _ in range(1000)]
    assert max(collections.Counter(vals).values()) >= T.MIN_N, "the fixture must actually tie"
    assert T.walls(vals) == []


def test_a_chance_tie_under_min_n_is_not_a_wall():
    """method-specimens' largest chance tie is 5 documents at 802 words. Below MIN_N, ignored."""
    vals = [802] * 5 + list(range(415, 892, 4))
    assert T.walls(vals) == []


def test_a_value_whose_band_reaches_zero_is_not_judged():
    """52 one-character responses in the run records would otherwise be a 'wall' at 1."""
    vals = [1] * 52 + list(range(325, 3000, 50))
    assert T.walls(vals) == []
    # But the same count at a real length IS judged.
    assert [(c, v) for c, v, _ in T.walls([1500] * 52 + list(range(325, 3000, 50)))] == \
        [(52, 1500)]


def test_too_few_values_for_a_wall():
    assert T.walls([6000] * 7) == []


def test_scan_reports_a_buried_wall_end_to_end():
    """The live path: a 6,000-character cut appended to by a later, larger fetch."""
    import json
    import random
    import tempfile
    rng = random.Random(3)

    def prose(n_chars):
        words = []
        while sum(len(w) + 1 for w in words) < n_chars + 20:
            words.append(rng.choice(["notice", "the", "agency", "proposes", "rule",
                                     "comment", "period", "section", "federal", "of"]))
        return " ".join(words)[:n_chars]

    recs = [{"id": "old%d" % i, "text": prose(6000)} for i in range(84)]
    recs += [{"id": "new%d" % i, "text": prose(rng.randint(6100, 20000)) + "."}
             for i in range(90)]
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        for r in recs:
            fh.write(json.dumps(r) + "\n")
    try:
        rep = T.scan(path)
        kinds = {f["kind"]: f for f in rep["findings"]}
        assert "cap-spike" not in kinds, "the premise: the wall is no longer the maximum"
        assert "wall" in kinds, rep["findings"]
        assert "84 of 174" in kinds["wall"]["detail"] and "6000 characters" in kinds["wall"]["detail"]
        assert "below the maximum" in kinds["wall"]["detail"]
        assert kinds["wall"]["severity"] == "high", "6,000 is a round multiple of 1000"
        assert T.main([path, "--check"]) == 1
    finally:
        os.unlink(path)


def test_a_wall_of_answer_sheets_is_structured_output_not_a_cut():
    """runs/calibration: 20 gemma2 sheets, 10 at exactly 125 words, all 10 structured."""
    import json
    import tempfile
    sheet = "\n".join("%d. Agree" % i for i in range(1, 63))
    recs = [{"id": "s%d" % i, "text": sheet} for i in range(10)]
    recs += [{"id": "v%d" % i, "text": sheet + "\n" + "\n".join(
        "%d. Strongly Disagree" % j for j in range(63, 63 + i + 1))} for i in range(10)]
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        for r in recs:
            fh.write(json.dumps(r) + "\n")
    try:
        vals = [len(r["text"].split()) for r in recs]
        assert T.walls(vals), "the fixture must be a wall by the numbers alone"
        rep = T.scan(path)
        assert "wall" not in {f["kind"] for f in rep["findings"]}, rep["findings"]
    finally:
        os.unlink(path)


def test_the_wall_is_not_double_counted_with_cap_spike(tmp_path):
    """When the cut IS the maximum, cap_spike owns it and `wall` stays quiet -- one finding for
    one defect, or a single cut reads as two and inflates every count in the report."""
    rep = T.scan(_cut_corpus(tmp_path, n_cut=84, n_free=0))
    kinds = [f["kind"] for f in rep["findings"]]
    assert "cap-spike" in kinds, rep["findings"]
    assert "wall" not in kinds, rep["findings"]


# ------------------------------------- the real corpora keep their verdicts (measured 2026-09-04)

def test_the_calibration_cache_stays_clean():
    """20 Federal Register notices, genuinely varied: 413..49,491 words, no two the same length."""
    path = os.path.join(ROOT, "corpus", "_calibration-cache")
    # Same guard as the news-control test below, and for the same reason: this bucket is
    # gitignored too, so the day anything is committed into it the directory materialises
    # empty in CI and `scan` returns None. One input showing a blind spot means the others
    # have it too -- three tools in this repo have already been bitten by exactly that.
    rep = T.scan(path) if os.path.isdir(path) else None
    if rep is None:
        pytest.skip("corpus/_calibration-cache holds no documents in this checkout")
    assert rep["n"] >= 20, rep
    assert rep["findings"] == [], rep["findings"]


def test_advocacy_comments_gain_no_cap_finding():
    """38 comments, median 478 words: a MEDIUM broken tail today and nothing else."""
    path = os.path.join(ROOT, "corpus", "advocacy-comments.jsonl")
    if not os.path.exists(path):
        pytest.skip("corpus/advocacy-comments.jsonl not present")
    rep = T.scan(path)
    assert rep["n"] >= 30, rep
    kinds = {f["kind"] for f in rep["findings"]}
    assert not kinds & {"cap-spike", "soft-cap", "wall"}, rep["findings"]


def test_advocacy_specimens_pass_after_the_refetch():
    """Was `test_advocacy_specimens_still_fail`, and the rename is the point.

    A test whose name asserts an artifact STILL FAILS is a test that has to be edited the day
    the artifact is fixed, which is the day nobody wants to be arguing about a test. 15 of 18
    hearings were cut at exactly 30,000 characters; the by-id refetch on 2026-09-05 restored
    them (median 30,000 -> 133,861 characters). The remaining 3 are Congressional RECORD issues
    whose stored id addresses an issue rather than the granule whose title is recorded, so no
    identifier addresses the text held; they now DECLARE their truncation instead of hiding it,
    which is what makes this exit 0.
    """
    path = os.path.join(ROOT, "corpus", "advocacy-specimens.jsonl")
    if not os.path.exists(path):
        pytest.skip("corpus/advocacy-specimens.jsonl not present")
    assert T.main([path, "--check"]) == 0
    rep = T.scan(path)
    declared = [f for f in rep["findings"] if f["kind"] == "declared-truncation"]
    assert declared, "the 3 unrefetchable records must still declare themselves"


# ------------------------------------------- one declared record must not blind the input

def test_one_declared_record_does_not_suppress_the_rest():
    """A gate a single row can disable is not a gate.

    Suppression was per INPUT: one record with `truncated: true` switched cap-spike and
    soft-cap off for every other record. Both fetchers append and skip ids they already hold,
    so the next fetch would have written a few declared records beside 155 undeclared ones and
    blinded the scanner to all 155.
    """
    import json
    import tempfile
    recs = [{"id": "u%d" % i, "text": "word " * 3200} for i in range(60)]
    recs.append({"id": "declared", "text": "short text that was cut",
                 "truncated": True, "truncated_at_chars": 6000, "full_words": 9000})
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        for r in recs:
            fh.write(json.dumps(r) + "\n")
    try:
        rep = T.scan(path)
        kinds = {f["kind"] for f in rep["findings"]}
        assert "declared-truncation" in kinds, rep["findings"]
        assert "cap-spike" in kinds, (
            "60 undeclared records at one length must still be caught: %r" % rep["findings"])
        assert T.main([path, "--check"]) == 1
    finally:
        os.unlink(path)


# ---------------------------------------------------------------- at-cap fields


# ---------------------------------------------------------------- round ceilings

@pytest.mark.parametrize("n,expect", [
    (8192, "a power of two"), (1024, "a power of two"), (800, "a round multiple of 100"),
    (3200, "a round multiple of 100"), (1500, "a round multiple of 500"),
    (5202, None), (4789, None), (137, None),
])
def test_round_ceiling_names_human_chosen_caps(n, expect):
    assert T.round_ceiling(n) == expect


# ---------------------------------------------------------------- broken tail

def test_text_cut_mid_sentence_is_caught():
    got = T.broken_tail("to them. We don't know to what extent Kavanaugh was Trump's choice and")
    assert got and "mid-sentence" in got


def test_finished_prose_is_not_flagged():
    assert T.broken_tail("The vote was 51 to 49.") is None
    assert T.broken_tail('He called it "an organized attack."') is None


def test_an_answer_sheet_is_not_truncated():
    """THE false positive that mattered: 27 of 32 valid compass sheets were flagged."""
    sheet = "\n".join("%d. Strongly Disagree" % i for i in range(1, 63))
    assert T.broken_tail(sheet) is None
    assert T.looks_structured(sheet)


def test_a_bulleted_list_is_not_truncated():
    assert T.broken_tail("Findings:\n- one thing\n- another thing") is None


def test_a_key_value_tail_is_not_truncated():
    assert T.broken_tail("Header\n\nmodel: claude-sonnet-5") is None


def test_empty_text_is_not_a_finding():
    assert T.broken_tail("") is None
    assert T.broken_tail("   ") is None


# ------------------------------------------------- known terminators (false positive #2)

@pytest.mark.parametrize("code", ["7710-12-P", "4810-AL-P", "6325-39-P", "4910-13-P"])
def test_a_federal_register_billing_code_is_the_real_end(code):
    """18 of 20 calibration-cache notices were flagged. They are complete documents.

    The letter segments run to two characters and appear mid-code, so a first pattern of
    `[\\d-]+[A-Z]?` matched 19 of 20 and left one file looking like a genuine finding.
    """
    text = "of Foreign Assets Control, Department of the Treasury.\nBILLING CODE " + code
    assert T.known_terminator(text)
    assert T.broken_tail(text) is None


def test_an_fr_doc_line_is_the_real_end():
    assert T.known_terminator("text.\n[FR Doc. 2026-17426 Filed 8-24-26; 4:15 pm]")


def test_a_billing_code_does_not_excuse_a_cut_elsewhere():
    """Non-suppression guard: the terminator must be at the END, not merely present."""
    assert T.broken_tail("BILLING CODE 7710-12-P and then more prose that stops abruptly and")


# ------------------------------------------------- declared truncation is a disclosure

def test_a_record_that_declares_truncation_is_info_not_a_defect():
    """The producers now record `truncated`; the scanner must credit that, not re-flag it.

    A scanner that keeps warning about a documented, deliberate cut trains its reader to
    ignore it -- and then the undocumented one goes past too.
    """
    import json
    import tempfile
    recs = [{"id": "a", "text": "A sentence that was cut off mid",
             "truncated": True, "truncated_at_chars": 6000, "full_words": 9000}] * 10
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        for r in recs:
            fh.write(json.dumps(r) + "\n")
    try:
        rep = T.scan(path)
        kinds = {f["kind"]: f["severity"] for f in rep["findings"]}
        assert kinds.get("declared-truncation") == "info", rep["findings"]
        assert "soft-cap" not in kinds, "a declared cut must not also be reported as a soft cap"
        assert T.main([path, "--check"]) == 0, "an info-only report must not fail --check"
    finally:
        os.unlink(path)



def test_a_generation_on_its_own_budget_is_caught():
    msgs = T.at_cap({"tokens_out": 8190, "max_tokens": 8192})
    assert msgs and "at its" in msgs[0]


def test_a_generation_well_under_budget_is_not():
    assert T.at_cap({"tokens_out": 305, "max_tokens": 8192}) == []


def test_a_record_missing_the_limit_cannot_be_judged():
    """Which is the argument for recording the limit beside the measurement."""
    assert T.at_cap({"tokens_out": 8190}) == []


# ---------------------------------------------------------------- end to end

def test_it_reads_the_real_news_control_pool():
    """Non-vacuity: this must read the actual corpus, not pass on a missing directory.

    Its 3,200-word chunking is real and deliberate -- vendored wire copy, no fetcher in this
    repo could produce it differently -- so as of 2026-09-05 it DECLARES itself in
    `.truncation.json` and the finding is INFO rather than HIGH. The declaration is
    re-measured, not believed; see the mismatch test below.
    """
    path = os.path.join(ROOT, "corpus", "_news-control")
    rep = T.scan(path) if os.path.isdir(path) else None
    if rep is None:
        # ABSENT IS NOT EMPTY, AND THE DIRECTORY NOW EXISTS IN CI WHILE THE DATA DOES NOT.
        #
        # `corpus/_news-control/` is gitignored, so this used to be a clean "directory missing,
        # skip". Then `.truncation.json` was force-added into it on 2026-09-05 -- correctly,
        # the declaration is documentation and belongs in the repo -- and the directory started
        # existing in CI with none of its 95 .txt files in it. `os.path.isdir` passed,
        # `load_texts` found nothing it reads, `scan` returned None, and this line raised
        # TypeError. Committing one file into an ignored directory materialises the directory.
        pytest.skip("corpus/_news-control holds no documents in this checkout "
                    "(gitignored; only its .truncation.json is committed)")
    assert rep["n"] >= 90, rep
    decl = [f for f in rep["findings"] if f["kind"] == "declared-truncation"]
    assert decl, rep["findings"]
    assert "3200 words" in decl[0]["detail"], decl
    assert not {f["kind"] for f in rep["findings"]} & {"cap-spike", "wall", "soft-cap"}


def _declared_dir(tmp_path, cap_words, declared_cap):
    d = tmp_path / "bucket"
    d.mkdir()
    for i in range(30):
        (d / ("doc%02d.txt" % i)).write_text("w " * cap_words, encoding="utf-8")
    (d / ".truncation.json").write_text(
        json.dumps({"unit": "words", "cap": declared_cap, "why": "test"}), encoding="utf-8")
    return str(d)


def test_a_true_declaration_downgrades_the_finding(tmp_path):
    rep = T.scan(_declared_dir(tmp_path, 500, 500))
    kinds = {f["kind"] for f in rep["findings"]}
    assert "declared-truncation" in kinds, rep["findings"]
    assert not kinds & {"cap-spike", "wall", "soft-cap"}, rep["findings"]


def test_a_FALSE_declaration_suppresses_nothing_and_is_itself_a_finding(tmp_path):
    """THE GUARD THAT KEEPS THE SIDECAR FROM BEING AN OFF SWITCH.

    Declare a cap the data does not have and the scan re-measures, reports
    `declaration-mismatch` at HIGH, and leaves every record undeclared -- so the underlying cut
    is still found. The only way a declaration quietens anything is by being true, which is the
    difference between documenting a corpus and loosening a detector.
    """
    rep = T.scan(_declared_dir(tmp_path, 500, 1234))
    kinds = {f["kind"] for f in rep["findings"]}
    assert "declaration-mismatch" in kinds, rep["findings"]
    assert kinds & {"cap-spike", "wall", "soft-cap"}, (
        "the real cut must still be reported", rep["findings"])
    assert any(f["severity"] == "high" for f in rep["findings"]), rep["findings"]


def test_a_sidecar_one_level_down_is_honoured(tmp_path):
    """CI points the scan at `corpus/`, and the bucket that declares itself is a subdirectory.

    Resolving only the top directory's sidecar looked right and ignored the declaration in
    exactly the invocation that matters.
    """
    _declared_dir(tmp_path, 500, 500)
    rep = T.scan(str(tmp_path))
    assert "declared-truncation" in {f["kind"] for f in rep["findings"]}, rep["findings"]


def test_a_truncated_corpus_still_fails_the_default_check(tmp_path):
    """THE TEST THAT SETTLES WHETHER --check WAS NARROWED OR RETREATED.

    On 2026-09-05 `--check` was scoped to HIGH findings, because `broken-tail` (MEDIUM) has a
    genuine population: 14 of 38 public comments "end mid-sentence" and every one ends on a
    signature. If that scoping had also stopped the tool failing on the 6,000-character cut it
    was written to find, it would be a loosened detector wearing a policy argument. It does not:
    a cap signature is HIGH and fails --check either way.
    """
    path = _cut_corpus(tmp_path)
    assert T.main([path, "--check"]) == 1
    assert T.main([path, "--check", "--strict"]) == 1
    assert T.main([path]) == 0, "without --check it reports and exits 0"


def test_a_broken_tail_alone_reports_but_does_not_gate(tmp_path):
    """Prose that ends on a name is not a cut. It is still printed, at MEDIUM.

    14 of 38 -- 37% -- is the real proportion in `advocacy-comments.jsonl`, and it is under the
    tool's own 50% escalation, above which broken tails ARE a cap signature and go HIGH. That
    escalation is what keeps this scoping from blinding the tool to a cut made at a paragraph
    boundary rather than a character count: such a corpus ends mid-sentence nearly everywhere,
    and 100% broken tails still fails --check with no --strict.
    """
    import random
    rng = random.Random(3)
    p = tmp_path / "sigs.jsonl"
    rows = []
    for i in range(38):
        body = "w " * rng.randint(200, 900)
        rows.append({"id": "c%02d" % i,
                     "text": body + ("Sincerely, Ms. Barbara Green" if i < 14
                                     else "and that is the end of it.")})
    p.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    rep = T.scan(str(p))
    assert "broken-tail" in {f["kind"] for f in rep["findings"]}, rep["findings"]
    assert T.main([str(p), "--check"]) == 0
    assert T.main([str(p), "--check", "--strict"]) == 1, "--strict must still gate on it"


def test_broken_tails_everywhere_are_a_cap_signature_and_gate(tmp_path):
    """Above 50% the tool escalates broken-tail to HIGH, so a cut made at a paragraph boundary
    -- which leaves no round-number cap for cap_spike or wall to find -- still fails --check."""
    p = tmp_path / "allcut.jsonl"
    rows = [{"id": "c%02d" % i, "text": ("w " * (300 + i * 7)) + "and then it stops abruptly on"}
            for i in range(40)]
    p.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    rep = T.scan(str(p))
    assert not {f["kind"] for f in rep["findings"]} & {"cap-spike", "wall", "soft-cap"}, (
        "no round cap here -- broken-tail must carry this alone", rep["findings"])
    assert T.main([str(p), "--check"]) == 1


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
