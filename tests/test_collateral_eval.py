"""The collateral rig's arithmetic and its honesty rules, on synthetic documents.

The full run is 11 s and gated by tools/freshness_gate.py (`collateral-eval`); these tests
pin the pieces a future edit could quietly bend: the verdict is an interval comparison, a zero
count prints a power statement rather than "absent", the one-cue flag needs both a share and a
floor, the hand-read sample is reproducible from its seed, and a rare lens is read in full.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "eval"))

import collateral_eval as ce  # noqa: E402


def _doc(pid, tid, words, occ_by_lens):
    lenses = {}
    for lid, n in occ_by_lens.items():
        lenses[lid] = {"occurrences": n, "detections": {"d1": n} if n else {},
                       "spans": [{"detection": "d1", "start": i * 10, "end": i * 10 + 4,
                                  "span": "cue!", "cue": "'cue'"} for i in range(n)]}
    return {"id": tid, "person_id": pid, "url": None, "date": None, "words": words, "lenses": lenses}


RULER = {"L": {"eligible_state": "index", "docs_rate": 0.1, "per_1k": 0.05, "per_1k_ci95": [0.03, 0.07]}}


def test_verdict_is_an_interval_comparison_not_a_point():
    # 2 occurrences in 100 kwords -> 0.02 per 1k, upper bound well above the background's
    # lower bound: indistinguishable, even though the point sits below the background point.
    docs = [_doc("p", "t", 100_000, {"L": 2})]
    row = ce.lens_table(docs, {"L": None}, RULER)["L"]
    assert row["verdict"] == "indistinguishable from background"
    # 200 in 100 kwords -> 2.0 per 1k, lower bound far above 0.07: above.
    docs = [_doc("p", "t", 100_000, {"L": 200})]
    assert ce.lens_table(docs, {"L": None}, RULER)["L"]["verdict"] == "above background"


def test_zero_count_prints_power_not_absence():
    docs = [_doc("p", "t", 20_000, {"L": 0})]
    row = ce.lens_table(docs, {"L": None}, RULER)["L"]
    assert row["occurrences"] == 0
    assert row["per_1k_ci95"][0] == 0.0 and row["per_1k_ci95"][1] > 0
    assert row["min_detectable_per_1k"] is not None and row["min_detectable_ratio"] > 1


def test_min_detectable_falls_with_exposure():
    small = ce.min_detectable_per_1k(20.0, 0.07)
    large = ce.min_detectable_per_1k(2000.0, 0.07)
    assert small > large > 0.07


def test_one_cue_needs_share_and_floor():
    docs = [_doc("p", "t", 10_000, {"L": 3})]           # 100% share but only 3 occurrences
    assert ce.lens_table(docs, {"L": None}, RULER)["L"]["one_cue"] is False
    docs = [_doc("p", "t", 10_000, {"L": ce.ONE_CUE_MIN})]
    assert ce.lens_table(docs, {"L": None}, RULER)["L"]["one_cue"] is True


def test_precision_sample_is_seeded_and_reads_rare_lenses_in_full():
    docs = [_doc("p", f"t{i}", 1000, {"common": 3, "rare": 0}) for i in range(20)]
    docs.append(_doc("q", "t99", 1000, {"common": 0, "rare": 2}))
    texts = {d["id"]: {"text": "x" * 400} for d in docs}
    a = ce.precision_sample(docs, texts, frozen=None)      # a fresh draw; never touch the real frozen set
    b = ce.precision_sample(docs, texts, frozen=None)
    assert a == b
    assert a["sample_n"] == ce.SAMPLE_N and len([r for r in a["rows"] if r["how"] == "sampled"]) == ce.SAMPLE_N
    rare = [r for r in a["rows"] if r["how"] != "sampled"]
    assert len(rare) == 2 and all(r["lens"] == "rare" for r in rare)
    assert a["rows"][-1]["n"] == len(a["rows"])          # numbering is contiguous


def test_frozen_sample_reports_survivors_and_dropped(tmp_path):
    docs = [_doc("p", f"t{i}", 1000, {"common": 3}) for i in range(20)]
    texts = {d["id"]: {"text": "x" * 400} for d in docs}
    frozen = str(tmp_path / "frozen.json")
    first = ce.precision_sample(docs, texts, frozen=frozen)
    assert first["surviving"] == len(first["rows"]) and os.path.exists(frozen)
    # a "cue repair" removes every hit on one text: its sampled spans must be reported dropped,
    # the rest keep their numbers, and nothing new is drawn
    docs2 = [d for d in docs if d["id"] != first["rows"][0]["text_id"]]
    second = ce.precision_sample(docs2, texts, frozen=frozen)
    assert second["frozen_n"] == first["frozen_n"]
    assert second["surviving"] + len(second["dropped"]) == first["frozen_n"]
    assert all(not d["fires_now"] for d in second["dropped"])
    kept = {r["n"] for r in second["rows"]}
    assert kept <= {r["n"] for r in first["rows"]}


def test_quoted_ranges_pair_marks_and_ignore_orphans():
    t = 'He said “existential risk” and then "a few hundred" more. Unpaired “ here.'
    r = ce.quoted_ranges(t)
    assert len(r) == 2
    a = t.find("existential")
    assert ce.in_quotes(r, a, a + len("existential")) is True
    b = t.find("more")
    assert ce.in_quotes(r, b, b + 4) is False


def test_rulers_quote_the_wider_interval():
    r = ce.rulers()
    for lid, ru in r.items():
        if ru.get("per_1k_ci95") is None:
            continue
        lo, hi = ru["per_1k_ci95"]
        assert lo <= (ru["per_1k"] or 0) <= hi or ru["per_1k"] == 0
