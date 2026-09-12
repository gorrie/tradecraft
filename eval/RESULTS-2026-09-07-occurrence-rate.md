# Issue #7 closed: the unit is occurrences per 1,000 words, and the residual is genre

**Measured** 2026-09-07 over 171 background documents, 885.3 kwords.
**Reproduce:** `python eval/length_components.py` then `python eval/occurrence_rate.py --check`.

## What the issue asked

Every background rate was fired-documents over n-documents, with no length normalisation, on a
pool spanning 140 to 57,458 words. Five of sixteen lenses swung 13–31 points between the
shortest and longest length quartile. Two candidate units were offered, both needing
measurement first: **firings per 1,000 words**, or a **fixed-window scan**. The window scan was
measured on 2026-09-06 and refuted. A third option — stratify the null by length — was costed.

## First: the mechanism, and it refuted two hypotheses including mine

`eval/length_components.py` decomposes the index. A lens fires when `index > 0`, and

    index = 100 * (w_breadth * breadth + w_intensity * intensity + w_density * density)

Only `density` is length-normalised. So the obvious hypothesis is that `breadth` and
`intensity` — both *presence* terms, both monotone in length because a longer document contains
more distinct markers — carry the drift. **Measured, they do not.** All three components
correlate with length at the same magnitude:

| component | mean \|rho\| with length | worst lens |
|---|---:|---|
| breadth | 0.202 | institutional_permeation +0.415 |
| intensity | 0.202 | institutional_permeation +0.414 |
| density | 0.194 | institutional_permeation +0.378 |

And the decisive column: the `index>0` and `density>0` firing rates are **identical on every
lens**. So the drift is not saturation of the presence terms. It is the **extensive margin**:

> A lens fires when the document contains at least one cue, and `P(at least one)` rises with
> length for any nonzero underlying rate. Every component goes from zero to nonzero at the same
> moment. Normalising one cannot help — density is 0 when nothing occurs, and when a single cue
> occurs in 50,000 words density is tiny but still greater than zero.

That also explains, structurally, **why candidate 2 failed**: "fires if any window fires" is the
same extensive margin, over windows instead of documents. The 2026-09-06 note observed it
changed essentially nothing; this is the reason.

And it makes **candidate 1 correct**. Under a Poisson null at rate λ per 1,000 words:

    documents-fired / documents   = 1 - exp(-λ·words/1000)    rises with length
    occurrences / (words/1000)    = λ                          does not

## What was built

`eval/occurrence_rate.py`. Cue **occurrences** — raw, not the grader's confidence-weighted sum,
because a rate needs a count a reader can check by reading the document — over exposure in
thousands of words.

- **Exact Poisson (Garwood) intervals** replace Wilson, from chi-square quantiles computed in
  the file (this repo has no scipy). Validated against published values: χ²(0.975, 2) = 7.3778,
  χ²(0.025, 2) = 0.0506, χ²(0.975, 20) = 34.1696, all exact to four decimals.
- **A count of zero keeps a lower bound of exactly zero.** "We saw none" is the finding for four
  lenses and rounding it up would erase it.
- **MDR in words, not documents.** Once the unit is a rate, "100 documents" is not a size — the
  pool's own documents run 140 to 57,458 words.
- **Overdispersion is measured, not assumed.** Clustered occurrences would make the Poisson
  interval too narrow, and a too-narrow background makes detection *easier* to claim — the
  wrong direction to be wrong in. Variance-to-mean is reported per lens with a quasi-Poisson
  interval beside the exact one. **No lens exceeds the tolerance** (max VMR 1.11), so the exact
  interval stands.

## The rates

| lens | occ | per 1k | 95% CI (exact) | VMR |
|---|---:|---:|---|---:|
| sourcing_asymmetry | 53 | 0.0599 | [0.0448, 0.0783] | 0.37 |
| institutional_permeation | 45 | 0.0508 | [0.0371, 0.0680] | 1.07 |
| reference_capture | 20 | 0.0226 | [0.0138, 0.0349] | 0.32 |
| subculture_register | 17 | 0.0192 | [0.0112, 0.0307] | 0.26 |
| legibility | 12 | 0.0136 | [0.0070, 0.0237] | 0.23 |
| inevitability_framing | 5 | 0.0056 | [0.0018, 0.0132] | 1.11 |
| distributed_accountability, militant_mobilization | 4 | 0.0045 | [0.0012, 0.0116] | ~0.28 |
| cognitive_capture, narrative_management, rollback_asymmetry | 3 | 0.0034 | [0.0007, 0.0099] | ~0.30 |
| adept_speech | 2 | 0.0023 | [0.0003, 0.0082] | 0.31 |
| costly_signal, counterproductivity, network_brokerage, revolving_door | 0 | 0.0000 | [0.0000, 0.0042] | — |

## The acceptance test, and two ways it was wrong first

The unit's whole claim is length-invariance, so it is tested rather than asserted: recompute the
rate within length bands and ask whether one rate describes them all, by exposure-weighted
Poisson chi-square.

**Getting that test right took three tries, and each wrong version failed in a way this project
has a name for.**

1. **A raw swing across quartiles** failed 7 lenses — including three whose bands are not
   monotone in length at all (`inevitability_framing` is *highest* in the shortest band). Bands
   held equal document counts and wildly unequal word exposure, so the statistic measured the
   exposure imbalance.
2. **A Spearman correlation on per-document rates** failed 5 lenses at rho +0.24 to +0.38. That
   statistic is invalid here: per-document rates are mostly tied at zero and their variance
   scales as 1/length, so a rank correlation over them re-measures the extensive margin — the
   exact symptom the pooled rate exists to route around. It is still reported, and not gated.
3. **Equal-document-count bands** made every lens's expected count fall below 5, so the
   chi-square was invalid everywhere and the gate **passed having evaluated zero lenses**. A
   vacuous green, in code written to catch vacuous greens. Bands now hold equal word exposure,
   the gate tests halves (the coarsest split with power), and **zero evaluations is now a
   failure** rather than a pass.

Result: 5 of 12 live lenses had enough exposure for the chi-square. Four were homogeneous, and
**seven were reported UNTESTABLE** — honest, and useless to anyone.

## "Too rare to test" was the chi-square's limitation, not the data's

The chi-square needs expected counts above ~5. That is an asymptotic requirement, and there is
an **exact** test with no such condition. Conditioning on the total, if
`X1 ~ Poisson(λ1·e1)` and `X2 ~ Poisson(λ2·e2)` then

    X1 | X1 + X2 = N   ~   Binomial(N, λ1·e1 / (λ1·e1 + λ2·e2))

and under the null that parameter is `e1/(e1+e2)` — known exactly. So **every live lens now has
a valid p-value, including `adept_speech` with two occurrences.** Validated against
hand-computable cases: 10 vs 0 at equal exposure gives p = 0.0020 = 2·0.5¹⁰; 0 vs 2 gives 0.5;
2 vs 1 at 2:1 exposure gives 1.0.

**And the exact test agrees with the chi-square on all five lenses where both are valid** —
same reject/accept decision every time (`sourcing_asymmetry` 0.0089 against 0.0087,
`institutional_permeation` 0.0727 against 0.0597). Two independent computations agreeing is how
a hand-rolled statistic earns trust in a repo with no scipy.

What the rare lenses lack is **power**, and power is a number rather than a category:

| lens | occ | per 1k | detects now | background needed for 4× |
|---|---:|---:|---:|---|
| sourcing_asymmetry | 53 | 0.0599 | **2.3×** | 384 kw (0.4× current pool) |
| institutional_permeation | 45 | 0.0508 | **2.6×** | 452 kw (0.5×) |
| reference_capture | 20 | 0.0226 | **3.7×** | 1,018 kw (1.2×) |
| subculture_register | 17 | 0.0192 | **6.1×** | 1,198 kw (1.4×) |
| legibility | 12 | 0.0136 | **6.4×** | 1,697 kw (1.9×) |
| inevitability_framing | 5 | 0.0056 | none ≤50× | 4,072 kw (4.6×) |
| distributed_accountability, militant_mobilization | 4 | 0.0045 | none ≤50× | 5,090 kw (5.7×) |
| cognitive_capture, narrative_management, rollback_asymmetry | 3 | 0.0034 | none ≤50× | 6,787 kw (7.7×) |
| adept_speech | 2 | 0.0023 | none ≤50× | 10,181 kw (11.5×) |

So the seven former "untestable" lenses now read **"no evidence of a length effect, and no
power to have found one — this corpus could not detect 50×, and would need 4.6× to 11.5× more
background words to detect 4×."** That is a decision a reader can act on: grow the pool, or ship
the lens with a stated blind spot. "Too rare to test" was neither.

**Doubling the background pool would bring three more lenses to 4× detectability.** The rarest
four need an order of magnitude, which is a real answer about where corpus effort pays.

This is the sibling bias study's own doctrine applied here: an underpowered null is **undecided
with a stated limit**, not unmeasurable. `power.py` there says three of five published nulls sit
below their own detection limit; this says seven of twelve background rates do.

## The residual is genre, not length

`sourcing_asymmetry` rejects length homogeneity, χ² 6.88 on 1 dof, **p = 0.0087** — with rates
*falling* as documents get longer, the opposite direction from the old unit. Per bucket:

| bucket | n | kwords | occ | per 1k |
|---|---:|---:|---:|---:|
| `_news-control` | 95 | 301.9 | 30 | **0.0994** |
| `advocacy-specimens.jsonl` | 18 | 413.5 | 23 | **0.0556** |
| `_calibration-cache` (Federal Register) | 20 | 153.2 | 0 | **0.0000** |
| `advocacy-comments.jsonl` | 38 | 16.7 | 0 | **0.0000** |

It fires in news prose and advocacy tracts and **not once** in rulemaking notices or public
comments. Attribution language is a property of news writing. In this pool **length and genre
are the same variable** — the short documents are comments, the long ones are hearings and
notices — so the pooled length test cannot separate them, and the bucket test can.

`ROLES` already forbids pooling buckets of different length for exactly this reason. The pool
had become internally what it was forbidden to be across buckets, and the length unit was never
going to fix that: **`sourcing_asymmetry`'s pooled rate is a composition average over four
genres and must be quoted per bucket.** The gate says so by name and does not treat it as a
pass — reattributed is not exonerated.

## What this does not do

- **It does not replace `background_rate.py`.** Every published rate still comes from there, and
  none of them moved today. This is a second resolution object, measured and gated, ready to be
  adopted deliberately rather than by a script quietly changing its unit.
- **It does not rescue the twelve rare lenses.** Seven have too few background occurrences to
  test for length invariance and four have none at all. Their intervals are honest and wide;
  that is the finding, not a gap.
- **It does not settle candidate 3.** Stratifying the null by length is still available and is
  now less attractive: the bucket analysis shows the stratum that matters is source type, not
  length, and stratifying by the collinear variable would spend power on the wrong axis.
- **The two largest background buckets are gitignored**, so this runs on the author's machine.
  It is a RESULTS document plus a gate, not a public statistic.

## Direction of the error, restated

The old unit inflated the background on long documents, and an inflated background makes
detection **harder** to claim, so nothing published gets easier and nothing needs withdrawing.
The new unit is not systematically more permissive either: `sourcing_asymmetry`'s news-bucket
rate (0.0994) is *higher* than its pooled rate (0.0599), so quoting per bucket raises the bar
for a news-heavy subject rather than lowering it.
