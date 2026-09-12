#!/usr/bin/env python3
"""A LENGTH-INVARIANT background rate: cue occurrences per 1,000 words, with its own interval.

WHY THIS EXISTS
---------------
Issue #7. Every rate in `background_rate.py` is fired-documents over n-documents, and the
background pool spans 140 to 57,458 words -- a 410x range. Five of sixteen lenses swing 13 to 31
points between the shortest and longest length quartile, and `reference_capture` and
`legibility` never fire on short documents at all. A null that moves 31 points with document
length is a length meter.

THE MECHANISM, measured in `length_components.py` rather than assumed:

    Firing is the EXTENSIVE MARGIN. A lens fires when `index > 0`, which happens when the
    document contains at least ONE cue -- and `P(at least one)` rises with length for any
    nonzero underlying rate. The `index>0` and `density>0` firing columns are IDENTICAL on
    every lens, and all three index components drift with length by the same amount
    (breadth 0.202, intensity 0.202, density 0.194 mean |rho|).

That refuted two hypotheses at once. It is not breadth/intensity saturation -- density is
length-normalised by construction and drifts just as much, because density is zero when nothing
occurs and tiny-but-positive when one cue occurs in 50,000 words. And it is why the fixed-window
scan (issue candidate 2) failed: "fires if ANY window fires" is the same extensive margin, over
windows instead of documents.

Under a Poisson null at rate L per 1,000 words:

    documents-fired / documents   = 1 - exp(-L * words / 1000)   rises with length
    occurrences / (words / 1000)  = L                            does not

So candidate 1 is structurally correct and this implements it.

WHAT REPLACES THE BINOMIAL MACHINERY
------------------------------------
The Wilson interval is for a proportion and this is a rate, so it is replaced by the EXACT
POISSON interval (Garwood, from the chi-square quantiles). The minimum detectable rate is
recomputed against a subject corpus measured in WORDS rather than documents, which is the
honest denominator once the unit is a rate -- "100 documents" means nothing when documents run
140 to 57,458 words.

OVERDISPERSION IS TESTED, NOT ASSUMED
-------------------------------------
Cue occurrences may cluster: a document that mentions a move once tends to mention it again. If
they do, the Poisson interval is too NARROW, and a too-narrow background interval makes every
detection claim EASIER to sustain -- the opposite of the conservative direction the current
defect happens to have. So the variance-to-mean ratio is measured per lens and a
quasi-Poisson (VMR-inflated) interval is reported beside the exact one. **The wider of the two
is the one a public surface may quote**, and `--check` fails if a caller would have taken the
narrower one on an overdispersed lens.

LENGTH INVARIANCE IS AN ACCEPTANCE TEST, NOT A CLAIM
----------------------------------------------------
The whole point is that the new unit does not move with length. So the rate is recomputed
within each length quartile and the swing is reported. If it still swings, this unit failed and
the report says so rather than shipping it.

    python eval/occurrence_rate.py                # measure and report
    python eval/occurrence_rate.py --json
    python eval/occurrence_rate.py --check        # exit 1 if a lens is overdispersed and
                                                  # the narrow interval is what gets quoted
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

from tradecraft.corpus_docs import documents               # noqa: E402
from tradecraft.detect import detect                       # noqa: E402
from tradecraft.loader import load_lenses                  # noqa: E402

import background_rate as B                                # noqa: E402

RATE_FILE = os.path.join(HERE, "occurrence-rates.json")

ALPHA = 0.05

#: Subject corpus sizes in WORDS, not documents. Once the unit is a rate, "100 documents" is
#: not a size -- the background pool's own documents run 140 to 57,458 words, so a
#: hundred-document subject could be 14,000 words or 5.7 million.
SUBJECT_WORDS = (50_000, 200_000, 1_000_000)

#: A lens whose occurrences are more clustered than this must not be quoted from the exact
#: Poisson interval. 1.0 is the Poisson expectation; anything above it is overdispersion.
VMR_TOLERANCE = 1.5

#: Minimum EXPECTED count per length band for the chi-square homogeneity test to be valid.
#: Below this the asymptotic approximation does not hold and the statistic inflates -- see the
#: note in measure(). A lens under it is reported UNTESTABLE, never passed.
MIN_EXPECTED = 5.0

#: Target power for the detectable-rate-ratio figure, and the ceiling the search gives up at.
#: A lens that needs more than a 50x length effect to be detectable is reported as undetectable
#: rather than with a number nobody would act on.
POWER_TARGET = 0.80
RATIO_CEILING = 50.0


def _chi2_ppf(p, k):
    """Chi-square quantile by bisection on the regularised gamma CDF.

    Written out rather than imported because this repository has no scipy dependency and
    adding one for two quantiles would be the heaviest import in the tree. Bisection is exact
    enough here: the interval bounds are reported to four decimals and the search runs to 1e-10.
    """
    if k <= 0:
        return 0.0
    lo, hi = 0.0, max(10.0, 4.0 * k)
    while _gammainc_lower(k / 2.0, hi / 2.0) < p:
        hi *= 2.0
        if hi > 1e9:
            break
    for _ in range(200):
        mid = (lo + hi) / 2.0
        if _gammainc_lower(k / 2.0, mid / 2.0) < p:
            lo = mid
        else:
            hi = mid
        if hi - lo < 1e-10:
            break
    return (lo + hi) / 2.0


def _gammainc_lower(a, x):
    """Regularised lower incomplete gamma P(a, x), series and continued fraction."""
    if x <= 0:
        return 0.0
    if x < a + 1.0:
        term = 1.0 / a
        total = term
        n = 1
        while n < 500:
            term *= x / (a + n)
            total += term
            if abs(term) < abs(total) * 1e-14:
                break
            n += 1
        return total * math.exp(-x + a * math.log(x) - math.lgamma(a))
    # Lentz continued fraction for Q(a, x), then complement.
    tiny = 1e-300
    b = x + 1.0 - a
    c = 1.0 / tiny
    d = 1.0 / b
    h = d
    for i in range(1, 500):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < tiny:
            d = tiny
        c = b + an / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-14:
            break
    q = math.exp(-x + a * math.log(x) - math.lgamma(a)) * h
    return 1.0 - q


def _binom_pmf(k, n, p):
    if k < 0 or k > n:
        return 0.0
    if p <= 0.0:
        return 1.0 if k == 0 else 0.0
    if p >= 1.0:
        return 1.0 if k == n else 0.0
    return math.exp(math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)
                    + k * math.log(p) + (n - k) * math.log1p(-p))


def exact_rate_split_test(c1, c2, e1, e2):
    """EXACT two-sided test that two Poisson rates are equal, valid at ANY count.

    THIS IS WHAT REPLACES "TOO RARE TO TEST", and the replacement is not a weaker test -- it
    is the correct one. The chi-square homogeneity statistic needs every expected count above
    about 5, which on a background pool where the phenomenon is absent excludes seven of twelve
    live lenses: `adept_speech` has TWO occurrences in 885 kwords. Those lenses were reported
    UNTESTABLE, which is honest and useless.

    The exact test conditions on the total. If X1 ~ Poisson(L1*e1) and X2 ~ Poisson(L2*e2),
    then

        X1 | X1 + X2 = N   ~   Binomial(N, L1*e1 / (L1*e1 + L2*e2))

    and under the null L1 = L2 that parameter is just e1 / (e1 + e2) -- known exactly, with no
    asymptotics and no expected-count condition. So every lens with at least one occurrence
    gets a valid p-value, including the ones with two.

    What those lenses lack is POWER, not validity, and that is a number rather than a category
    -- see `detectable_rate_ratio()`. Reporting "underpowered, and here is by how much" instead
    of "untestable" is the same move this project's sibling study makes with its detection
    limits: an underpowered null is undecided, not unmeasurable.

    Two-sided by summing every split at most as probable as the observed one, which is the
    standard exact construction and does not assume symmetry.
    """
    n = c1 + c2
    if n == 0 or e1 <= 0 or e2 <= 0:
        return None
    p0 = e1 / (e1 + e2)
    obs = _binom_pmf(c1, n, p0)
    # A tolerance, because two splits that are equally probable in exact arithmetic can differ
    # in the last bit and drop one tail.
    tol = obs * (1.0 + 1e-9)
    return min(1.0, sum(_binom_pmf(k, n, p0) for k in range(n + 1)
                        if _binom_pmf(k, n, p0) <= tol))


def detectable_rate_ratio(n, e1, e2, alpha=ALPHA, power=POWER_TARGET):
    """Smallest rate RATIO between the two bands this test could detect at `power`.

    The honest replacement for "too rare to test". At `n` total occurrences split across
    exposures `e1` and `e2`, this walks the ratio up until the exact test rejects the null with
    probability at least `power`, and returns it. A lens with two occurrences comes back with a
    huge number or None -- which says "this corpus could not have detected a tenfold length
    effect on this lens", and that is a measurement.

    Returns None when no ratio up to RATIO_CEILING reaches the target power.
    """
    if n <= 0 or e1 <= 0 or e2 <= 0:
        return None
    p0 = e1 / (e1 + e2)
    # Which observed splits would reject at alpha? Precompute once.
    reject = [k for k in range(n + 1)
              if (exact_rate_split_test(k, n - k, e1, e2) or 1.0) < alpha]
    if not reject:
        return None                      # no split of n counts can reject; power is 0 for all
    r = 1.0
    while r <= RATIO_CEILING:
        r *= 1.05
        # Under the alternative, the conditional parameter shifts.
        p1 = (r * e1) / (r * e1 + e2)
        got = sum(_binom_pmf(k, n, p1) for k in reject)
        if got >= power:
            return round(r, 2)
    return None


def kwords_for_ratio(rate, target_ratio, alpha=ALPHA, power=POWER_TARGET):
    """How much background exposure a lens needs before a `target_ratio` becomes detectable.

    "NO POWER" IS ONLY HALF AN ANSWER. Saying a lens cannot detect a 50x length effect is
    honest and leaves the reader with nothing to do. This says what to do: the total kilowords
    of background at which the exact test would catch a `target_ratio` difference between the
    short and long halves at `power`.

    Walks the occurrence count up, since the count is what the test consumes, and converts back
    through the lens's measured rate. A lens firing twice in 885 kwords needs an enormous pool;
    printing that number is the argument for either growing the corpus or accepting that the
    lens ships with a stated blind spot -- both of which are decisions, which "too rare to
    test" was not.
    """
    if not rate or rate <= 0:
        return None
    for n in range(1, 2001):
        # Split the hypothetical exposure in half, as the test does.
        kw = n / rate
        r = detectable_rate_ratio(n, kw / 2.0, kw / 2.0, alpha=alpha, power=power)
        if r is not None and r <= target_ratio:
            return round(kw, 1)
    return None


def poisson_ci(count, exposure, alpha=ALPHA):
    """Exact (Garwood) Poisson interval for a rate, per unit exposure.

    exposure is in units of 1,000 words. A count of zero has a lower bound of exactly zero --
    reported as such rather than as a small positive number, because "we saw none" is the
    finding for twelve of these lenses and rounding it up would erase it.
    """
    if exposure <= 0:
        return (None, None)
    lo = 0.0 if count == 0 else _chi2_ppf(alpha / 2.0, 2 * count) / 2.0 / exposure
    hi = _chi2_ppf(1.0 - alpha / 2.0, 2 * (count + 1)) / 2.0 / exposure
    return (lo, hi)


def background_docs():
    out = []
    for d in documents(min_words=B.MIN_WORDS):
        rec = B.role_of(d.origin)
        if rec and rec.get("role") == "background":
            out.append((d, rec))
    return out


def occurrences(text, taxonomy):
    """How many cue occurrences this document holds for this lens.

    RAW OCCURRENCES, not the grader's weighted sum. The weighting exists to build an INDEX --
    a bounded 0-100 score combining breadth, intensity and density -- and a rate needs a
    count. Weighted occurrences would make the rate's unit "confidence-weighted cue-equivalents
    per 1,000 words", which is not a quantity anybody can check against a document by reading
    it. The receipts are the occurrences.
    """
    return len(list(detect(text, taxonomy, backend="cues")))


def measure():
    lenses = load_lenses(os.path.join(ROOT, "detectors"))
    docs = background_docs()
    lengths = [B.tokens(d.text) for d, _ in docs]
    total_kwords = sum(lengths) / 1000.0

    # BANDS OF EQUAL WORD EXPOSURE, NOT EQUAL DOCUMENT COUNT.
    #
    # Ordered by length either way, but the split point matters enormously. Equal document
    # counts give the shortest quartile ~42 documents and about 19 kwords, against ~600 kwords
    # in the longest -- so the expected count in Q1 is under 5 for EVERY lens in this pool and
    # the homogeneity test is invalid everywhere. The first version did that and the gate
    # passed having evaluated zero lenses, which is the vacuous green this file's own docstring
    # complains about elsewhere.
    #
    # Equal exposure gives every band the same expected count under H0, which is the condition
    # the chi-square wants and the arrangement with the most power available from this corpus.
    # The bands still span the length range because the ordering is by length; what changes is
    # that the short band now holds many small documents instead of a handful.
    order = sorted(range(len(docs)), key=lambda i: lengths[i])
    total_words = sum(lengths)
    bands, cur, cur_w, target = [], [], 0, total_words / 4.0
    for i in order:
        cur.append(i)
        cur_w += lengths[i]
        if cur_w >= target and len(bands) < 3:
            bands.append(cur)
            cur, cur_w = [], 0
    bands.append(cur)
    bands = [b for b in bands if b]

    # THE GATE SPLITS IN HALF, not in quarters. Four bands quarter the exposure and quarter
    # the expected count with it, and this pool is small enough that quartering costs the test
    # its validity on all but the two busiest lenses. Halves are the coarsest split that still
    # answers the question actually asked -- does the rate differ between short and long
    # documents -- and they double the expected count. Both are reported.
    half_target = total_words / 2.0
    halves, cur, cur_w = [], [], 0
    for i in order:
        cur.append(i)
        cur_w += lengths[i]
        if cur_w >= half_target and not halves:
            halves.append(cur)
            cur, cur_w = [], 0
    halves.append(cur)
    halves = [b for b in halves if b]

    rows = []
    for lens_id, taxonomy in sorted(lenses.items()):
        counts = [occurrences(d.text, taxonomy) for d, _ in docs]
        total = sum(counts)
        rate = total / total_kwords if total_kwords else None
        lo, hi = poisson_ci(total, total_kwords)

        # Per-document rates, for the dispersion test. A document with no words cannot
        # contribute; MIN_WORDS already excludes fragments.
        per_doc = [c / (n / 1000.0) for c, n in zip(counts, lengths) if n > 0]
        mean = sum(per_doc) / len(per_doc) if per_doc else 0.0
        var = (sum((x - mean) ** 2 for x in per_doc) / (len(per_doc) - 1)
               if len(per_doc) > 1 else 0.0)
        vmr = (var / mean) if mean > 0 else None

        # Quasi-Poisson: widen the interval by sqrt(VMR) when occurrences cluster.
        qlo, qhi = lo, hi
        if vmr and vmr > 1.0 and rate is not None:
            infl = math.sqrt(vmr)
            qlo = max(0.0, rate - (rate - lo) * infl)
            qhi = hi + (hi - rate) * (infl - 1.0)

        # PER-BAND RATES WITH THEIR OWN EXPOSURE AND INTERVAL.
        #
        # Bands hold equal DOCUMENT counts and wildly unequal WORD counts -- the shortest
        # quartile of this pool is ~42 documents and a few thousand words total, so one
        # occurrence there is a large rate and zero is a zero. Comparing raw band rates
        # therefore compares four numbers of very different precision, and a swing statistic
        # over them measures the exposure imbalance rather than any length bias. The first
        # version of the acceptance test did exactly that and failed seven lenses whose bands
        # were not even monotone in length.
        band_rates, band_detail = [], []
        for band in bands:
            kw = sum(lengths[i] for i in band) / 1000.0
            c = sum(counts[i] for i in band)
            r_band = (c / kw) if kw else None
            blo, bhi = poisson_ci(c, kw)
            band_rates.append(round(r_band, 4) if r_band is not None else None)
            band_detail.append({"kwords": round(kw, 1), "occ": c,
                                "rate": round(r_band, 4) if r_band is not None else None,
                                "ci95": [None if blo is None else round(blo, 4),
                                         None if bhi is None else round(bhi, 4)]})
        live = [r for r in band_rates if r is not None]
        swing = (max(live) - min(live)) if live else None

        # THE TEST THAT MEANS SOMETHING: does any band's interval EXCLUDE the pooled rate?
        # If the underlying rate were constant, each band's exact interval should cover it.
        # A band whose interval misses the pooled rate is a real deviation; a band that merely
        # sits far away with a huge interval is small exposure, not bias.
        excludes = []
        for name, det in zip(("Q1", "Q2", "Q3", "Q4"), band_detail):
            c = det["ci95"]
            if rate is None or c[0] is None:
                continue
            if rate < c[0] or rate > c[1]:
                excludes.append(name)

        # THE HOMOGENEITY TEST. Is one rate enough to describe all four bands?
        #
        # Under H0 the underlying rate is constant, so band i expects `rate * exposure_i`
        # occurrences and the Poisson chi-square statistic sum((c_i - E_i)^2 / E_i) has k-1
        # degrees of freedom. This is the right test because it weights each band BY ITS
        # EXPOSURE, which is the thing that differs 30-fold between the shortest and longest
        # quartile of this pool.
        # AND IT HAS A VALIDITY CONDITION, which the first version of this gate ignored.
        #
        # The chi-square approximation needs every expected count above ~5. On a background
        # pool where the phenomenon is absent, most lenses are nowhere near that:
        # `adept_speech` has TWO occurrences in 885 kwords, so its expected band counts run
        # 0.1 to 1.4 and the statistic is meaningless. Applied anyway, it rejected homogeneity
        # for `adept_speech` (p 0.011) and `inevitability_framing` (5 occurrences, p 0.029) --
        # failing the fix on the two lenses least able to say anything about it.
        #
        # So the test runs only where it is valid, and where it is not the lens is reported as
        # UNTESTABLE BY NAME rather than counted as passing. Absent is not zero and it is not
        # a pass; a gate that silently passes what it could not evaluate is the vacuous green
        # this project keeps finding elsewhere.
        # Run it on the HALVES, which is where the exposure is large enough to be valid.
        half_detail = []
        for band in halves:
            kw = sum(lengths[i] for i in band) / 1000.0
            c = sum(counts[i] for i in band)
            half_detail.append({"kwords": round(kw, 1), "occ": c,
                                "rate": round(c / kw, 4) if kw else None})
        # THE EXACT TEST IS THE TEST. Valid at any count, so nothing is "untestable".
        #
        # The chi-square is kept alongside it as a CROSS-CHECK where both are valid, because
        # two independent computations agreeing is how a hand-rolled statistic earns trust in a
        # repo with no scipy. Where they disagree, the exact one is right.
        p_exact = None
        mdrr = None
        if len(half_detail) == 2:
            a, b_ = half_detail[0], half_detail[1]
            p_exact = exact_rate_split_test(a["occ"], b_["occ"], a["kwords"], b_["kwords"])
            mdrr = detectable_rate_ratio(a["occ"] + b_["occ"], a["kwords"], b_["kwords"])

        expected = [(rate or 0.0) * det["kwords"] for det in half_detail]
        chi2_valid = bool(expected) and min(expected) >= MIN_EXPECTED
        chi2 = None
        dof = 0
        if chi2_valid:
            for det, e in zip(half_detail, expected):
                if e > 0:
                    chi2 = (chi2 or 0.0) + (det["occ"] - e) ** 2 / e
                    dof += 1
            dof = max(0, dof - 1)
        p_chi2 = (1.0 - _gammainc_lower(dof / 2.0, chi2 / 2.0)) if (chi2 and dof) else None
        # `homogeneity_p` is the key every caller reads, and it now carries the EXACT p-value.
        # The chi-square keeps its own key so the cross-check is visible rather than folded in.
        p_homog = p_exact

        # WITHIN-BUCKET RATES, because in this pool LENGTH AND SOURCE TYPE ARE THE SAME
        # VARIABLE. The short documents are public comments (median 459 words) and the long
        # ones are hearings and Federal Register notices (median 3,200 to 19,301). So a rate
        # that differs between short and long documents may be a length artifact OR a real
        # difference between comment prose and hearing prose, and the pooled test cannot tell
        # them apart. `ROLES` already forbids pooling buckets of different length for exactly
        # this reason; the pool became internally what it was forbidden to be across buckets.
        #
        # If a lens's rate is homogeneous WITHIN each bucket and differs BETWEEN buckets, the
        # residual is composition rather than length, and no choice of unit can fix it -- the
        # fix is to report per bucket.
        per_bucket = {}
        for (d, _rec), c, n in zip(docs, counts, lengths):
            b = B.bucket_of(d.origin) or "?"
            agg = per_bucket.setdefault(b, {"occ": 0, "words": 0, "n": 0})
            agg["occ"] += c
            agg["words"] += n
            agg["n"] += 1
        bucket_rates = {b: {"n": v["n"], "kwords": round(v["words"] / 1000.0, 1),
                            "occ": v["occ"],
                            "rate": round(v["occ"] / (v["words"] / 1000.0), 4)
                                    if v["words"] else None}
                        for b, v in sorted(per_bucket.items())}

        # BETWEEN-BUCKET HOMOGENEITY, the test that says whether a length failure is really a
        # genre failure. Same Poisson chi-square, exposure-weighted, over buckets instead of
        # length bands. If a lens rejects here, its rate is a property of the SOURCE TYPE and
        # the pooled figure is a composition average of four different genres -- so the fix is
        # to report per bucket, and no choice of unit can substitute for that.
        b_exp = [(rate or 0.0) * v["kwords"] for v in bucket_rates.values()]
        b_chi2, b_dof = None, 0
        if b_exp and min(b_exp) >= MIN_EXPECTED:
            for v, e in zip(bucket_rates.values(), b_exp):
                if e > 0:
                    b_chi2 = (b_chi2 or 0.0) + (v["occ"] - e) ** 2 / e
                    b_dof += 1
            b_dof = max(0, b_dof - 1)
        b_p = ((1.0 - _gammainc_lower(b_dof / 2.0, b_chi2 / 2.0))
               if (b_chi2 and b_dof) else None)
        # Reported even when the strict validity condition fails, because a lens that fires in
        # exactly one bucket and nowhere else is the clearest possible composition finding and
        # it should not be silenced by an expected-count rule. `bucket_concentration` is the
        # share of occurrences in the single busiest bucket.
        occ_by_bucket = sorted((v["occ"] for v in bucket_rates.values()), reverse=True)
        concentration = (occ_by_bucket[0] / total) if total else None
        zero_buckets = sum(1 for v in bucket_rates.values() if v["occ"] == 0)

        # THE SPEARMAN ON PER-DOCUMENT RATES IS REPORTED AND NOT GATED, and the reason is the
        # useful half of this measurement. It reads +0.24 to +0.38 on the five busiest lenses
        # even though every band's interval covers the pooled rate -- because per-document
        # rates are mostly TIED AT ZERO and their variance scales as 1/length, so a rank
        # correlation over them is dominated by the zero/nonzero split. That split IS the
        # extensive margin, which is the defect the pooled rate exists to route around. Gating
        # on this statistic would fail the fix for reproducing the symptom it was built to
        # avoid measuring; a first version of the gate did exactly that.
        rho_rate = _spearman(lengths, [c / (n / 1000.0) if n else 0.0
                                       for c, n in zip(counts, lengths)])

        rows.append({
            "lens": lens_id,
            "occurrences": total,
            "kwords": round(total_kwords, 1),
            "rate_per_1k": round(rate, 4) if rate is not None else None,
            "ci95": [round(lo, 4), round(hi, 4)],
            "vmr": round(vmr, 2) if vmr is not None else None,
            "overdispersed": bool(vmr and vmr > VMR_TOLERANCE),
            "ci95_quasi": [round(qlo, 4), round(qhi, 4)],
            "band_rates": band_rates,
            "band_detail": band_detail,
            "band_swing": round(swing, 4) if swing is not None else None,
            "bands_excluding_pooled": excludes,
            "half_detail": half_detail,
            "bucket_rates": bucket_rates,
            "bucket_chi2": None if b_chi2 is None else round(b_chi2, 3),
            "bucket_p": None if b_p is None else round(b_p, 4),
            "bucket_concentration": None if concentration is None else round(concentration, 3),
            "zero_buckets": zero_buckets,
            "homogeneity_p_exact": None if p_exact is None else round(p_exact, 4),
            "detectable_rate_ratio": mdrr,
            "kwords_for_4x": kwords_for_ratio(rate, 4.0),
            "homogeneity_chi2": None if chi2 is None else round(chi2, 3),
            "homogeneity_p_chi2": None if p_chi2 is None else round(p_chi2, 4),
            "homogeneity_dof": dof,
            "homogeneity_p": None if p_homog is None else round(p_homog, 4),
            "rho_rate_vs_length": None if rho_rate is None else round(rho_rate, 3),
            "mdr_per_1k": {str(w): round(_mdr(w / 1000.0, hi), 4)
                           for w in SUBJECT_WORDS},
        })
    return {"n_docs": len(docs), "kwords": round(total_kwords, 1),
            "alpha": ALPHA, "vmr_tolerance": VMR_TOLERANCE, "lenses": rows}


def _mdr(exposure_kwords, background_hi):
    """Smallest subject rate whose exact lower bound clears the background's upper bound.

    Solved by walking the count up rather than inverting the interval analytically: the
    quantity is discrete in the count anyway, so a search returns the achievable answer rather
    than one that rounds to a count nobody can observe.
    """
    if exposure_kwords <= 0:
        return float("nan")
    k = 0
    while k < 100000:
        lo, _hi = poisson_ci(k, exposure_kwords)
        if lo is not None and lo > background_hi:
            return k / exposure_kwords
        k += 1
    return float("nan")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)

    data = measure()
    if args.write:
        with open(RATE_FILE, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(data, fh, indent=2)
            fh.write("\n")
        print("wrote %s" % os.path.relpath(RATE_FILE, ROOT))
    if args.json:
        print(json.dumps(data, indent=2))
        return 0

    print("OCCURRENCE RATE PER 1,000 WORDS -- %d background document(s), %s kwords"
          % (data["n_docs"], data["kwords"]))
    print("exact Poisson interval; quasi-Poisson beside it where occurrences cluster")
    print("")
    print("  %-26s %6s %9s %-18s %6s %-18s"
          % ("lens", "occ", "per 1k", "95% CI (exact)", "VMR", "95% CI (quasi)"))
    for r in data["lenses"]:
        print("  %-26s %6d %9s [%.4f, %.4f] %6s %s"
              % (r["lens"][:26], r["occurrences"],
                 "-" if r["rate_per_1k"] is None else "%.4f" % r["rate_per_1k"],
                 r["ci95"][0], r["ci95"][1],
                 "-" if r["vmr"] is None else "%.2f" % r["vmr"],
                 ("[%.4f, %.4f]%s" % (r["ci95_quasi"][0], r["ci95_quasi"][1],
                                      "  OVERDISPERSED" if r["overdispersed"] else "")
                  if r["vmr"] else "-")))

    print("")
    print("ACCEPTANCE TEST -- does the new unit still move with length?")
    print("  rate per 1k within each length quartile, shortest to longest")
    print("  %-26s %9s %9s %9s %9s %9s" % ("lens", "Q1", "Q2", "Q3", "Q4", "swing"))
    for r in data["lenses"]:
        b = r["band_rates"]
        print("  %-26s %9s %9s %9s %9s %9s"
              % (r["lens"][:26], *[("-" if x is None else "%.4f" % x) for x in b],
                 "-" if r["band_swing"] is None else "%.4f" % r["band_swing"]))

    # THE MDR WAS COMPUTED AND NEVER PRINTED, and it is the number the whole object exists to
    # produce. A background rate is only useful as something a subject either clears or does
    # not, so "what rate would a subject of this size need" is the answer a reader came for --
    # and it was sitting in the JSON, invisible to anyone running the script. Computed and
    # unsurfaced is the same defect as unsurfaced and uncomputed, one step less excusable.
    #
    # The ZERO-OCCURRENCE lenses are the most useful rows here, not the emptiest: a background
    # of [0, 0.0042] is the tightest ruler in the table, so a receipts-only claim on those four
    # clears its background at a lower subject rate than any other lens measured.
    print("")
    print("MINIMUM DETECTABLE RATE -- what a SUBJECT must show to clear this background")
    print("  occurrences per 1,000 words, by subject corpus size in WORDS")
    print("  %-26s %10s %11s %10s %13s"
          % ("lens", "50k words", "200k words", "1M words", "bg 95% upper"))
    for r in data["lenses"]:
        m = r["mdr_per_1k"]

        def _m(key):
            v = m.get(key)
            return "--" if v is None or v != v else "%.3f" % v

        print("  %-26s %10s %11s %10s %13.4f"
              % (r["lens"][:26], _m("50000"), _m("200000"), _m("1000000"), r["ci95"][1]))

    live = [r for r in data["lenses"] if r["occurrences"] > 0]
    od = [r for r in live if r["overdispersed"]]
    print("")
    print("%d of %d lenses have any occurrence in the background at all."
          % (len(live), len(data["lenses"])))
    if od:
        print("%d ARE OVERDISPERSED (VMR > %.1f): %s"
              % (len(od), data["vmr_tolerance"], ", ".join(r["lens"] for r in od)))
        print("For those, the exact Poisson interval is TOO NARROW and a public surface must")
        print("quote the quasi-Poisson bound. A narrow background makes detection easier to")
        print("claim, which is the wrong direction to be wrong in.")
    else:
        print("No lens exceeds the dispersion tolerance, so the exact interval stands.")

    if args.check:
        # THE GATE IS ON THE ACCEPTANCE TEST, NOT ON DISPERSION.
        #
        # Overdispersion is a fact about the corpus and a requirement on which interval gets
        # quoted -- not a defect in the unit. Failing on it would make this gate unfixable and
        # therefore switched off. What must fail is the unit not doing its job.
        #
        # AND THE TEST IS NOT A RAW SWING. A first version compared band rates directly and
        # failed seven lenses, including three whose bands are not monotone in length at all
        # -- `inevitability_framing` is HIGHEST in the shortest band. Bands hold equal
        # document counts and unequal word exposure, so a raw swing measures that imbalance.
        # Two tests that do mean something:
        #
        #   1. does any band's exact interval EXCLUDE the pooled rate? Under a constant
        #      underlying rate each band's interval should cover it.
        #   2. is the per-document rate still correlated with length? The index was, at rho
        #      up to +0.415, and a length-invariant unit should not be.
        live = [r for r in data["lenses"] if r["occurrences"] > 0]
        excl = [r for r in live if r["bands_excluding_pooled"]]
        het = [r for r in live if r["homogeneity_p"] is not None
               and r["homogeneity_p"] < ALPHA]
        # NOTHING IS "UNTESTABLE" ANY MORE, AND THAT WAS THE POINT OF THE EXACT TEST.
        #
        # The chi-square needed expected counts above 5 and therefore excluded seven of twelve
        # live lenses -- `adept_speech` has two occurrences in 885 kwords. They were printed as
        # UNTESTABLE, which is honest and tells a reader nothing they can act on.
        #
        # The exact conditional test is valid at any count, so every live lens now has a real
        # p-value. What the rare ones lack is POWER, and power is a NUMBER: the smallest rate
        # ratio between short and long documents this corpus could have detected at 80%. For a
        # lens with two occurrences that number does not exist below 50x, which is a
        # measurement of the corpus rather than a category the lens falls into.
        #
        # This is the sibling study's own doctrine applied here: an underpowered null is
        # UNDECIDED with a stated limit, not unmeasurable.
        blind = [r for r in live if r["detectable_rate_ratio"] is None]
        print("")
        if blind:
            print("NO POWER -- %d lens(es) where this corpus could not have detected even a"
                  % len(blind))
            print("%.0fx length effect at %d%% power. A pass here means nothing was seen, not"
                  % (RATIO_CEILING, int(POWER_TARGET * 100)))
            print("that nothing is there:")
            for r in blind:
                print("      %-26s %2d occurrence(s) in %s kwords, exact p %.4f"
                      % (r["lens"], r["occurrences"], data["kwords"],
                         r["homogeneity_p"] if r["homogeneity_p"] is not None else float("nan")))
            print("")
        # A LENGTH FAILURE THAT THE BUCKETS EXPLAIN IS A COMPOSITION FINDING, NOT A UNIT
        # FAILURE -- and telling them apart is the whole reason the bucket rates are computed.
        #
        # In this pool LENGTH AND GENRE ARE THE SAME VARIABLE: the short documents are public
        # comments and the long ones are hearings and Federal Register notices. So a lens whose
        # rate differs between short and long documents may be length-sensitive, or it may
        # simply fire in news prose and not in rulemaking prose. `sourcing_asymmetry` is the
        # second: 0.0994 per 1k in `_news-control`, 0.0556 in advocacy specimens, and EXACTLY
        # ZERO in both the Federal Register cache and the public comments. Attribution language
        # is a property of news writing.
        #
        # Calling that a failure of the unit would be wrong, and calling it a pass would be
        # worse. It is reported as what it is: the pooled rate for that lens is a composition
        # average over four genres and must be quoted per bucket.
        def bucket_explains(r):
            if r["bucket_p"] is not None and r["bucket_p"] < ALPHA:
                return True
            # Fires in one bucket and nowhere else: the clearest composition case there is,
            # and an expected-count rule should not silence it.
            return bool(r["zero_buckets"] >= 2 and (r["bucket_concentration"] or 0) >= 0.5)

        composition = [r for r in het if bucket_explains(r)]
        real_length = [r for r in het if not bucket_explains(r)]

        if composition:
            print("COMPOSITION, NOT LENGTH -- %d lens(es) whose rate differs across length"
                  % len(composition))
            print("bands because it differs across SOURCE TYPE, and the two are collinear here:")
            for r in composition:
                nz = [(b, v) for b, v in r["bucket_rates"].items() if v["occ"]]
                print("      %-26s length p %.4f; fires in %d of %d bucket(s):"
                      % (r["lens"], r["homogeneity_p"], len(nz), len(r["bucket_rates"])))
                for b, v in nz:
                    print("          %-34s %.4f per 1k (%d occ in %s kw)"
                          % (b, v["rate"], v["occ"], v["kwords"]))
            print("      -> quote these PER BUCKET. The pooled rate is a genre average.")
            print("")

        if excl or real_length:
            print("--check FAILED: the unit has not removed the length dependence.")
            for r in excl:
                print("      %-26s band(s) %s exclude the pooled rate %.4f"
                      % (r["lens"], ",".join(r["bands_excluding_pooled"]), r["rate_per_1k"]))
            for r in real_length:
                print("      %-26s rate NOT homogeneous across length bands, and the buckets "
                      "do NOT explain it: chi2 %.2f on %d dof, p %.4f"
                      % (r["lens"], r["homogeneity_chi2"], r["homogeneity_dof"],
                         r["homogeneity_p"]))
            return 1
        tested = [r for r in live if r["homogeneity_p"] is not None]
        # A GATE THAT EVALUATED NOTHING HAS NOT PASSED.
        #
        # With equal-document-count bands and the chi-square, every lens was untestable and
        # this returned 0 -- the vacuous green this project keeps convicting. The exact test
        # removed that failure mode by construction, and the guard stays because a future
        # change to the bands could bring it back.
        if not tested:
            print("--check FAILED: the homogeneity test could evaluate NO lens.")
            print("That is a fact about the pool, not a pass. Widen the bands, or say the unit")
            print("is unverified on this corpus.")
            return 1
        powered = [r for r in tested if r["detectable_rate_ratio"] is not None]
        print("--check passed on %d live lens(es), every one with a valid exact p-value:"
              % len(tested))
        print("  %d show homogeneous rates across length bands at alpha %.2f."
              % (len(tested) - len(composition), ALPHA))
        if powered:
            worst = max(r["detectable_rate_ratio"] for r in powered)
            print("  %d of those have the power to detect a length effect at all, the weakest"
                  % len(powered))
            print("  needing a %.2fx rate ratio; %d could not detect %.0fx and are named above."
                  % (worst, len(tested) - len(powered), RATIO_CEILING))
        if composition:
            # SAID PRECISELY. A first version of this line read "no lens rejects rate
            # homogeneity" while one lens had rejected it at p 0.0087 and been reattributed to
            # composition. Reattributed is not exonerated, and a summary that rounds it to
            # "none" is the kind of sentence this project keeps having to retract.
            print("  %d REJECTED length homogeneity and is attributed to source type above,"
                  % len(composition))
            print("  not to length: %s. That is a live constraint on how it may be quoted,"
                  % ", ".join(r["lens"] for r in composition))
            print("  not a clean bill of health.")
        return 0
    return 0


def _spearman(xs, ys):
    """Spearman rho, with the project's own tie handling. Imported at call time from
    length_dependence when available so the two scripts cannot disagree about the statistic."""
    try:
        from length_dependence import spearman as _s
        return _s(xs, ys)
    except Exception:                                  # noqa: BLE001
        return None


if __name__ == "__main__":
    raise SystemExit(main())
