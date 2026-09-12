"""The background-rate harness: its estimators, and its refusal to guess a corpus role.

WHY THIS MATTERS
----------------
A background firing rate is the resolution object for a lens too rare to hold an index floor,
and twelve of sixteen lenses depend on it. Two things about it fail silently.

The first is the zero case. Twelve lenses fire on zero background documents, and the normal
approximation to a proportion gives [0, 0] there -- which claims a background rate is known to
be exactly zero from 171 documents. It is not; the honest upper bound is about 2%, and every
rare-lens claim is measured against that bound rather than the point estimate. A regression to
the normal approximation would make every one of those lenses look infinitely sensitive.

The second is corpus classification. `corpus/method-specimens.jsonl` was retrieved per-lens by
cue term: it is selected on the phenomenon, so averaging it into a background would inflate the
background and make real firings look ordinary. Three tools in this repo have already been
bitten by a glob blind to one input. So a corpus file with no declared role must STOP the
measurement, and this file asserts that the manifest actually covers the corpus on disk -- the
assertion that fires when someone adds a seventh bucket and nothing else notices.

Run with `pytest` or directly: `python tests/test_background_rate.py`.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "eval"))

import background_rate as BR  # noqa: E402

from tradecraft.corpus_docs import documents  # noqa: E402


# ------------------------------------------------- the zero case is the load-bearing case

def test_wilson_upper_bound_is_positive_at_zero_successes():
    """0/171 must not read as "rate is zero". It reads as "rate is below about 2%"."""
    lo, hi = BR.wilson(0, 171)
    assert lo == 0.0
    assert 0.0 < hi < 0.05, hi


def test_wilson_upper_bound_tightens_with_more_documents():
    small = BR.wilson(0, 20)[1]
    large = BR.wilson(0, 400)[1]
    assert large < small, (small, large)


def test_wilson_brackets_the_point_estimate():
    lo, hi = BR.wilson(29, 171)
    assert lo < 29 / 171 < hi


# ------------------------------------------------- the exact binomial

def test_binom_sf_known_values():
    # P(X >= 1) for n=1 is just p.
    assert BR.binom_sf(1, 1, 0.25) == pytest.approx(0.25)
    # P(X >= 0) is 1 by definition, and P(X > n) is 0.
    assert BR.binom_sf(0, 10, 0.3) == 1.0
    assert BR.binom_sf(11, 10, 0.3) == 0.0
    # Symmetric case: P(X >= 1) for n=2, p=0.5 is 3/4.
    assert BR.binom_sf(1, 2, 0.5) == pytest.approx(0.75)


def test_binom_sf_is_monotone_in_p():
    a = BR.binom_sf(5, 50, 0.05)
    b = BR.binom_sf(5, 50, 0.20)
    assert a < b


# ------------------------------------------------- the resolution statistic

def test_critical_count_rises_with_background():
    """A noisier background demands more firings before a subject is distinguishable."""
    quiet = BR.critical_count(100, 0.02)
    noisy = BR.critical_count(100, 0.23)
    assert quiet < noisy, (quiet, noisy)


def test_mdr_improves_with_corpus_size():
    """More subject documents resolve a smaller true rate, at a fixed background."""
    small = BR.minimum_detectable_rate(20, 0.022)
    large = BR.minimum_detectable_rate(200, 0.022)
    assert small is not None and large is not None
    assert large < small, (small, large)


def test_mdr_worsens_with_a_noisier_background():
    quiet = BR.minimum_detectable_rate(100, 0.022)
    noisy = BR.minimum_detectable_rate(100, 0.233)
    assert quiet is not None and noisy is not None
    assert quiet < noisy, (quiet, noisy)


def test_mdr_never_claims_to_resolve_below_its_background():
    for p0 in (0.02, 0.10, 0.23):
        got = BR.minimum_detectable_rate(100, p0)
        assert got is None or got >= p0, (p0, got)


def test_mdr_is_none_when_the_corpus_is_too_small_to_ever_reject():
    """At n=1 against a 23% background no observation can reach significance.

    Returning a number here would be the same defect `mde()` had: printing the search step
    where a measurement belongs. None is the honest answer -- this corpus size resolves
    nothing, however common the move is.
    """
    assert BR.minimum_detectable_rate(1, 0.233) is None


# ------------------------------------------------- the manifest must cover the corpus

def test_every_corpus_file_on_disk_has_a_declared_role():
    """The assertion that fires when a seventh corpus bucket lands and nothing notices."""
    undeclared = sorted({d.origin for d in documents(min_words=BR.MIN_WORDS)
                         if BR.role_of(d.origin) is None})
    assert not undeclared, (
        "corpus file(s) with no declared role in background_rate.ROLES: %s -- classify each as "
        "'background' (not gathered for any lens) or 'recall-fixture' (gathered because the "
        "move is in it) before any background rate is trusted" % undeclared)


def test_roles_are_one_of_the_two_declared_kinds():
    for key, rec in BR.ROLES.items():
        assert rec["role"] in ("background", "recall-fixture"), (key, rec["role"])
        assert isinstance(rec["recomputable"], bool), key
        assert rec.get("why"), "every role needs its reason recorded: %s" % key


def test_outcome_selected_buckets_are_not_backgrounds():
    """The specific trap: a corpus retrieved per-lens can never measure accidental firing."""
    for name in ("corpus/method-specimens.jsonl", "corpus/specimens.jsonl"):
        assert BR.ROLES[name]["role"] == "recall-fixture", name


def test_bucket_of_groups_text_files_under_their_directory():
    """Grouping by raw origin gave 115 single-document columns; buckets are the unit."""
    assert BR.bucket_of("corpus\\_news-control\\news001.txt") == "corpus/_news-control"
    assert BR.bucket_of("corpus/_calibration-cache/2026-17238.txt") == "corpus/_calibration-cache"
    assert BR.bucket_of("corpus/advocacy-comments.jsonl") == "corpus/advocacy-comments.jsonl"
    assert BR.bucket_of("corpus/not-a-real-file.jsonl") is None


# ------------------------------------------------- gate 24: a floor OR a rate, never neither

def _write(path, lens_ids):
    import json
    path.write_text(json.dumps({"lenses": {k: {} for k in lens_ids}}), encoding="utf-8")


def test_gate_passes_when_a_lens_holds_only_a_background_rate(tmp_path, monkeypatch, capsys):
    """The case that made the old check unsatisfiable: a rare lens with no index floor."""
    import lens_floor as LF

    floors, rates = tmp_path / "floors.json", tmp_path / "rates.json"
    _write(floors, ["institutional_permeation"])
    _write(rates, ["costly_signal"])
    monkeypatch.setattr(LF, "FLOOR_FILE", str(floors))
    monkeypatch.setattr(LF, "RATE_FILE", str(rates))

    rc = LF.main(["--check", "--lens", "institutional_permeation", "--lens", "costly_signal"])
    out = capsys.readouterr().out
    assert rc == 0, out
    assert "index-bearing" in out and "receipts-only" in out


def test_gate_fails_when_a_lens_holds_neither_object(tmp_path, monkeypatch, capsys):
    """The strictness that must never rot: no ruler at all is still a hard failure."""
    import lens_floor as LF

    floors, rates = tmp_path / "floors.json", tmp_path / "rates.json"
    _write(floors, ["institutional_permeation"])
    _write(rates, ["costly_signal"])
    monkeypatch.setattr(LF, "FLOOR_FILE", str(floors))
    monkeypatch.setattr(LF, "RATE_FILE", str(rates))

    rc = LF.main(["--check", "--lens", "legibility"])
    out = capsys.readouterr().out
    assert rc == 1, out
    assert "NO RESOLUTION OBJECT" in out
    assert "legibility" in out


def test_gate_fails_when_the_rate_file_is_missing_entirely(tmp_path, monkeypatch, capsys):
    """A deleted background-rates.json must not silently pass the twelve rare lenses."""
    import lens_floor as LF

    floors = tmp_path / "floors.json"
    _write(floors, ["institutional_permeation"])
    monkeypatch.setattr(LF, "FLOOR_FILE", str(floors))
    monkeypatch.setattr(LF, "RATE_FILE", str(tmp_path / "does-not-exist.json"))

    rc = LF.main(["--check", "--lens", "costly_signal"])
    assert rc == 1
    assert "NO RESOLUTION OBJECT" in capsys.readouterr().out


def test_a_directory_holding_only_a_declaration_is_absent_not_empty(tmp_path):
    """A gitignored bucket with one committed sidecar is NOT CHECKED OUT, not empty.

    `--check` classified by `os.path.exists`, so force-adding `.truncation.json` into the
    gitignored `corpus/_news-control/` made CI see a directory that exists, holds none of its
    95 .txt files, and fails as "declared bucket with zero documents". The gate exists for a
    bucket whose data IS here and measures nothing; it fired on one that is simply not here.
    """
    bucket = tmp_path / "_news-control"
    bucket.mkdir()
    (bucket / ".truncation.json").write_text('{"unit":"words","cap":3200}', encoding="utf-8")
    from eval.background_rate import has_candidates
    assert has_candidates(str(bucket)) is False


def test_a_manifest_that_yields_nothing_is_still_empty_and_still_fails(tmp_path):
    """The teeth the test above must not remove.

    `news-control.manifest.jsonl` is a file of revision ids with no `text` field. It exists, it
    is readable, and it contributes zero documents -- a RECIPE for a corpus declared as the
    corpus. That is the vacuous pass this gate was written for, and it must keep failing.
    """
    manifest = tmp_path / "news-control.manifest.jsonl"
    manifest.write_text('{"revid": 1}\n{"revid": 2}\n', encoding="utf-8")
    from eval.background_rate import has_candidates
    assert has_candidates(str(manifest)) is True


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
