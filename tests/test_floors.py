"""The floor harnesses: their estimators, and whether they still perturb anything.

WHY THIS MATTERS MORE THAN IT LOOKS
-----------------------------------
As of 2026-09-02 every lens with a measured floor moves 0.0 index points under all four
perturbations. That is the expected result of repairing density into a real rate -- and it is
also exactly what a harness that had quietly stopped perturbing anything would print. A clean
sweep is indistinguishable from a broken instrument unless something asserts the perturbations
are real.

So the first block below asserts the perturbations actually alter the text, independently of
any lens. The rest covers the two estimator defects found the same day:

  mde() returned 0.5 for an exactly-zero null -- the search STEP, printed where a resolution
  belongs, reading as "resolves half an index point" and earned by nothing.

  pctile() puts int(0.90*n) at n-1 for every n <= 10, so p90 IS the maximum on any small arm
  and the two columns print one number while looking like two.

Run with `pytest` or directly: `python tests/test_floors.py`.
"""
import os
import random
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "eval"))

import graph_floor as GF  # noqa: E402
import lens_floor as LF  # noqa: E402

from tradecraft.corpus_docs import documents  # noqa: E402


# ------------------------------------------------- the perturbations must be real

SAMPLE = (
    "The council argued the local patchwork was indefensible. "
    "A single standard would be centrally recorded and monitored. "
    "Officials said the messy reality had to be simplified. "
    "The cost is spread across every future taxpayer."
)


def test_perturb_returns_all_four_kinds():
    got = LF.perturb(SAMPLE, random.Random(1))
    assert set(got) == {"sentence-order", "chunk-boundary", "whitespace", "duplication"}


def test_every_perturbation_actually_changes_the_text():
    """A zero floor is only meaningful if something was done to the document."""
    for name, variant in LF.perturb(SAMPLE, random.Random(1)).items():
        if name == "whitespace":
            continue                       # SAMPLE is already single-spaced; see below
        assert variant != SAMPLE, "%s returned the input unchanged" % name


def test_whitespace_perturbation_changes_text_that_has_whitespace_to_normalise():
    messy = SAMPLE.replace(". ", ".\n\n   ")
    assert LF.perturb(messy, random.Random(1))["whitespace"] != messy


def test_perturbations_preserve_the_words():
    """Not a reword: the same tokens, rearranged or repeated. Otherwise it is not a null."""
    variants = LF.perturb(SAMPLE, random.Random(7))
    base = sorted(SAMPLE.split())
    assert sorted(variants["sentence-order"].split()) == base
    assert sorted(variants["chunk-boundary"].split()) == base
    assert sorted(variants["whitespace"].split()) == base
    assert sorted(variants["duplication"].split()) == sorted(base + base)


def test_duplication_really_doubles():
    dup = LF.perturb(SAMPLE, random.Random(1))["duplication"]
    assert len(dup.split()) == 2 * len(SAMPLE.split())


def test_corpus_docs_returns_documents_over_the_word_floor():
    docs = LF.corpus_docs(12)
    assert docs, "no corpus documents selected"
    assert len(docs) <= 12
    for d in docs:
        assert len(d.text.split()) >= 60


def test_corpus_docs_cap_spans_more_than_one_source_file():
    """The cap used to be a head-slice, which took Federal Register cache and nothing else."""
    origins = {d.origin for d in LF.corpus_docs(40)}
    assert len(origins) > 1, origins


# -------------------------------------------------------------- the MDE estimator

def test_mde_returns_none_for_a_degenerate_null():
    """The defect: this returned 0.5, which is MDE_STEP and not a measurement."""
    assert LF.mde([0.0] * 20, 0.0) is None
    assert LF.mde([0, 0, 0, 0, 0, 0, 0, 0], 0.0) is None


def test_mde_label_names_a_degenerate_null_instead_of_printing_a_digit():
    assert LF.mde_label(None) == "none measured"
    assert LF.mde_label(float("nan")) == "n/a"
    assert LF.mde_label(2.5) == "2.5"


def test_mde_is_a_multiple_of_its_own_step():
    """Whatever it returns has to be reachable by the search, or it is not what was searched."""
    vals = [0.0, 1.0, 2.0, 3.0, 4.0, 12.0]
    got = LF.mde(vals, LF.pctile([abs(v) for v in vals], 0.95))
    assert got is not None
    assert abs((got / LF.MDE_STEP) - round(got / LF.MDE_STEP)) < 1e-9, got


def test_mde_grows_with_a_noisier_null():
    quiet = [0.0, 0.0, 1.0, 1.0, 1.0, 2.0]
    loud = [0.0, 5.0, 9.0, 11.0, 14.0, 20.0]
    q = LF.mde(quiet, LF.pctile([abs(v) for v in quiet], 0.95))
    l = LF.mde(loud, LF.pctile([abs(v) for v in loud], 0.95))  # noqa: E741
    assert q is not None and l is not None
    assert l > q, (q, l)


def test_mde_of_an_empty_null_is_nan():
    got = LF.mde([], 0.0)
    assert got != got


# ------------------------------------------------------------ the percentile convention

def test_pctile_is_nearest_rank_and_documented_as_such():
    assert LF.pctile([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 0.5) == 6
    assert LF.pctile([5], 0.9) == 5
    got = LF.pctile([], 0.9)
    assert got != got


def test_p90_collapses_onto_max_for_small_samples():
    """Not a bug to fix silently -- a property to KNOW, because the paper prints both columns.

    Nearest-rank puts int(0.90*n) at n-1 whenever n <= 10, so on a 4-pair or 7-pair arm the
    p90 and the max are the same number by construction. The bias study's requantisation row
    (n=4) and its prompt-condition row (n=7) both print p90 == max for exactly this reason.
    """
    for n in range(2, 11):
        vals = list(range(1, n + 1))
        assert LF.pctile(vals, 0.90) == max(vals), n
    # And from 11 up they separate.
    vals = list(range(1, 12))
    assert LF.pctile(vals, 0.90) < max(vals)


def test_results_flag_small_samples(tmp_path):
    """lens_floor records the flag so a reader is not left to notice it."""
    import json
    floors = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "eval", "lens-floors.json")
    if not os.path.exists(floors):
        pytest.skip("no recorded floors yet")
    payload = json.load(open(floors, encoding="utf-8"))
    rows = payload.get("lenses") or payload
    for name, row in rows.items():
        if isinstance(row, dict) and "p90_is_max" in row:
            assert isinstance(row["p90_is_max"], bool), name


# ------------------------------------------------------------------ the graph floor

def test_graph_floor_invariance_perturbations_are_declared_invariant():
    names = {name: inv for name, _, inv in GF.PERTURBATIONS}
    assert names["relabel"] is True
    assert names["flip-edges"] is True
    assert names["drop-far-leaf"] is False
    assert names["add-far-leaf"] is False


def test_relabel_preserves_structure_and_renames_the_subject():
    graph = GF.json.load(GF.io.open(GF.GRAPH, encoding="utf-8"))
    subject = graph["entities"][0]["id"]
    out, new_subject = GF.relabel(graph, subject, random.Random(3))
    assert new_subject != subject, "relabel did not rename the subject"
    assert len(out["entities"]) == len(graph["entities"])
    assert len(out["edges"]) == len(graph["edges"])
    assert all(e["id"].startswith("n") for e in out["entities"])


def test_flip_edges_reverses_every_edge():
    graph = GF.json.load(GF.io.open(GF.GRAPH, encoding="utf-8"))
    out, _ = GF.flip_edges(graph, graph["entities"][0]["id"], random.Random(3))
    for before, after in zip(graph["edges"], out["edges"]):
        assert after["source"] == before["target"]
        assert after["target"] == before["source"]


def test_drop_far_leaf_removes_exactly_one_node_not_adjacent_to_the_subject():
    graph = GF.json.load(GF.io.open(GF.GRAPH, encoding="utf-8"))
    report = GF.B.graph_report(GF.GRAPH, top=1)
    subject = report["top"][0]["id"]
    out, _ = GF.drop_far_leaf(graph, subject, random.Random(5))
    assert out is not None
    assert len(out["entities"]) == len(graph["entities"]) - 1
    removed = ({e["id"] for e in graph["entities"]}
               - {e["id"] for e in out["entities"]})
    assert len(removed) == 1
    assert removed.isdisjoint(GF._neighbours(graph, subject) | {subject})


def test_add_far_leaf_adds_one_node_and_one_edge_away_from_the_subject():
    graph = GF.json.load(GF.io.open(GF.GRAPH, encoding="utf-8"))
    report = GF.B.graph_report(GF.GRAPH, top=1)
    subject = report["top"][0]["id"]
    out, _ = GF.add_far_leaf(graph, subject, random.Random(5))
    assert out is not None
    assert len(out["entities"]) == len(graph["entities"]) + 1
    assert len(out["edges"]) == len(graph["edges"]) + 1
    assert subject not in (out["edges"][-1]["source"], out["edges"][-1]["target"])


if __name__ == "__main__":
    raise SystemExit(pytest.main([os.path.abspath(__file__), "-q"]))
