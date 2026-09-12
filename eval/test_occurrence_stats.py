#!/usr/bin/env python3
"""Validate the hand-rolled statistics in occurrence_rate.py against published values.

WHY THIS FILE EXISTS
--------------------
`occurrence_rate.py` implements six statistical routines from scratch, because this repository
has no scipy and adding one for a handful of quantiles would be the heaviest import in the
tree: a chi-square quantile, the regularised lower incomplete gamma, an exact (Garwood) Poisson
interval, an exact conditional binomial test for two Poisson rates, a power search for the
minimum detectable rate ratio, and an exposure solver.

Those numbers are load-bearing. Every background rate's interval, every detection limit and the
whole "no power below 50x" claim about seven lenses come out of them. When they were written
the chi-square quantiles and the exact test were checked against hand-computable cases and the
rest were spot-checked -- which I said out loud was the weakest part of the day's work. This
closes that.

The Poisson interval is checked against the standard published table rather than against
another implementation of my own, because two copies of the same mistake agree.
"""
from __future__ import annotations

import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import occurrence_rate as O  # noqa: E402


# ----------------------------------------------------------------- chi-square quantiles

@pytest.mark.parametrize("p,k,want", [
    (0.975, 1, 5.0239), (0.025, 1, 0.000982),
    (0.975, 2, 7.3778), (0.025, 2, 0.0506),
    (0.950, 3, 7.8147), (0.990, 3, 11.3449),
    (0.975, 10, 20.4832), (0.975, 20, 34.1696),
    (0.500, 1, 0.4549), (0.500, 4, 3.3567),
])
def test_chi2_quantiles_match_published_tables(p, k, want):
    got = O._chi2_ppf(p, k)
    assert got == pytest.approx(want, rel=1e-3), "chi2(%s, %d) = %.6f, table says %s" % (
        p, k, got, want)


# ------------------------------------------------------- exact (Garwood) Poisson interval

#: The standard published two-sided 95% exact Poisson interval, per unit exposure. These are the
#: values in every textbook table, and they are the ones a reader would check against.
GARWOOD_95 = {
    0: (0.000, 3.689),
    1: (0.0253, 5.572),
    2: (0.242, 7.225),
    3: (0.619, 8.767),
    4: (1.090, 10.242),
    5: (1.623, 11.668),
    10: (4.795, 18.390),
    20: (12.217, 30.888),
}


@pytest.mark.parametrize("count", sorted(GARWOOD_95))
def test_poisson_interval_matches_the_published_table(count):
    lo, hi = O.poisson_ci(count, 1.0)
    want_lo, want_hi = GARWOOD_95[count]
    assert lo == pytest.approx(want_lo, abs=5e-3), "lower for %d: %.4f vs %s" % (
        count, lo, want_lo)
    assert hi == pytest.approx(want_hi, abs=5e-3), "upper for %d: %.4f vs %s" % (
        count, hi, want_hi)


def test_zero_count_keeps_an_exact_zero_lower_bound():
    """"We saw none" is the finding for four lenses; rounding it up would erase it."""
    lo, _hi = O.poisson_ci(0, 885.3)
    assert lo == 0.0


def test_interval_scales_with_exposure():
    """A rate is per unit exposure, so ten times the exposure gives a tenth of the rate."""
    lo1, hi1 = O.poisson_ci(20, 1.0)
    lo10, hi10 = O.poisson_ci(20, 10.0)
    assert lo10 == pytest.approx(lo1 / 10.0, rel=1e-9)
    assert hi10 == pytest.approx(hi1 / 10.0, rel=1e-9)


def test_interval_covers_the_point_estimate():
    for count in (1, 3, 10, 53):
        lo, hi = O.poisson_ci(count, 885.3)
        rate = count / 885.3
        assert lo <= rate <= hi, count


# ------------------------------------------------------------- exact conditional rate test

def test_exact_test_against_hand_computable_cases():
    # Equal exposure, all counts on one side: two-sided p = 2 * 0.5**n.
    assert O.exact_rate_split_test(10, 0, 100, 100) == pytest.approx(2 * 0.5 ** 10, rel=1e-9)
    assert O.exact_rate_split_test(0, 4, 50, 50) == pytest.approx(2 * 0.5 ** 4, rel=1e-9)
    # A split matching the exposure ratio exactly is the most probable outcome: p = 1.
    assert O.exact_rate_split_test(5, 5, 100, 100) == pytest.approx(1.0)
    assert O.exact_rate_split_test(2, 1, 200, 100) == pytest.approx(1.0)
    # Zero total is not testable.
    assert O.exact_rate_split_test(0, 0, 100, 100) is None


def test_exact_test_is_symmetric_under_swapping_the_arms():
    for c1, c2, e1, e2 in ((7, 2, 100, 100), (12, 3, 300, 100), (1, 9, 50, 200)):
        a = O.exact_rate_split_test(c1, c2, e1, e2)
        b = O.exact_rate_split_test(c2, c1, e2, e1)
        assert a == pytest.approx(b, rel=1e-9)


def test_exact_test_p_values_are_probabilities():
    for c1 in range(0, 8):
        for c2 in range(0, 8):
            p = O.exact_rate_split_test(c1, c2, 442.0, 442.0)
            if p is not None:
                assert 0.0 <= p <= 1.0, (c1, c2, p)


def test_unequal_exposure_shifts_the_null():
    """With twice the exposure on one side, the null expects twice the counts there.

    9 vs 1 at 2:1 exposure is unremarkable in the direction the exposure predicts; 1 vs 9 is
    not. A test that returned the same p for both would be ignoring exposure entirely.
    """
    with_grain = O.exact_rate_split_test(6, 3, 200, 100)
    against = O.exact_rate_split_test(1, 9, 200, 100)
    assert with_grain > against
    assert with_grain == pytest.approx(1.0)


# --------------------------------------------------------------------- the power search

def test_detectable_ratio_is_monotone_in_sample_size():
    """More occurrences must never make the detectable effect LARGER."""
    seen = []
    for n in (5, 10, 20, 40, 80, 160):
        r = O.detectable_rate_ratio(n, 442.0, 442.0)
        seen.append((n, r))
    live = [(n, r) for n, r in seen if r is not None]
    assert len(live) >= 3, seen
    for (n1, r1), (n2, r2) in zip(live, live[1:]):
        assert r2 <= r1, "n=%d needs %.2fx but n=%d needs %.2fx" % (n1, r1, n2, r2)


def test_no_power_at_tiny_counts_is_reported_as_none():
    """The seven rare lenses' verdict. At n=2 no ratio up to the ceiling reaches 80% power."""
    assert O.detectable_rate_ratio(2, 442.0, 442.0) is None
    assert O.detectable_rate_ratio(5, 442.0, 442.0) is None


def test_the_returned_ratio_actually_reaches_the_target_power():
    """Independently re-derive the power at the returned ratio rather than trusting the search.

    The search walks the ratio up until power crosses the target; this recomputes the power at
    the answer from the exact test's own rejection set. A search that returned a ratio below
    its own target would pass every monotonicity check and still be wrong.
    """
    for n in (20, 40, 53, 100):
        r = O.detectable_rate_ratio(n, 442.0, 442.0)
        if r is None:
            continue
        p0_reject = [k for k in range(n + 1)
                     if (O.exact_rate_split_test(k, n - k, 442.0, 442.0) or 1.0) < O.ALPHA]
        p1 = (r * 442.0) / (r * 442.0 + 442.0)
        power = sum(O._binom_pmf(k, n, p1) for k in p0_reject)
        assert power >= O.POWER_TARGET - 1e-9, (
            "n=%d returned %.2fx but its power is %.3f, target %.2f"
            % (n, r, power, O.POWER_TARGET))


def test_exposure_solver_agrees_with_the_ratio_search():
    """`kwords_for_ratio` must return an exposure at which the ratio IS detectable."""
    for rate in (0.0599, 0.0226, 0.0056):
        kw = O.kwords_for_ratio(rate, 4.0)
        if kw is None:
            continue
        n = int(round(rate * kw))
        r = O.detectable_rate_ratio(n, kw / 2.0, kw / 2.0)
        assert r is not None and r <= 4.0 + 1e-9, (
            "rate %.4f: solver says %.0f kwords (n=%d) but the detectable ratio there is %s"
            % (rate, kw, n, r))


def test_exposure_solver_is_monotone_in_the_rate():
    """A rarer lens must need MORE background, never less."""
    a = O.kwords_for_ratio(0.0599, 4.0)
    b = O.kwords_for_ratio(0.0226, 4.0)
    c = O.kwords_for_ratio(0.0023, 4.0)
    live = [x for x in (a, b, c) if x is not None]
    assert live == sorted(live), (a, b, c)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
