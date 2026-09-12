# The background null is length-dependent, and the proposed fix does not fix it

**Issue:** [#7 — Background firing rates need a length-invariant unit](https://github.com/gorrie/tradecraft/-/issues/7)
**Measured:** 2026-09-06, `tradecraft/eval/window_rate.py`
**Status:** the defect is confirmed and larger than the issue estimated; **candidate 2 is
refuted**; a third option is proposed.

## 1. The bias is real, and it is large

Firing rate per length quartile across the 171-document background pool (140 to 57,458 words):

| lens | Q1 (505w) | Q2 (3200w) | Q3 (3200w) | Q4 (4728w) | Q4−Q1 |
|---|---:|---:|---:|---:|---:|
| `reference_capture` | 0.000 | 0.071 | 0.024 | **0.311** | **+0.311** |
| `institutional_permeation` | 0.024 | 0.071 | 0.095 | **0.333** | **+0.309** |
| `sourcing_asymmetry` | 0.000 | 0.238 | 0.214 | **0.289** | **+0.289** |
| `subculture_register` | 0.000 | 0.048 | 0.048 | 0.156 | +0.156 |
| `legibility` | 0.000 | 0.000 | 0.048 | 0.133 | +0.133 |
| the other 11 | — | — | — | — | ≤ +0.067 |

**Five of sixteen lenses swing 13 to 31 points from the shortest quartile to the longest.**
`reference_capture` and `legibility` never fire at all on short documents and fire on a third
and an eighth of long ones. That is not a property of the phenomenon; it is a property of how
much text the detector was handed.

The issue called this "not urgent, and still real". The first half is too generous to us. A
null that moves 31 points with document length is not a null — it is a length meter, and the
three lenses at the top of that table are among the ones carrying published findings.

**The direction is still conservative**, which is the only reason nothing needs withdrawing:
long documents inflate the background, an inflated background makes detection harder to claim,
and no published claim gets easier under any of this.

## 2. Candidate 2 — the fixed-window scan — does not work

The issue proposed scoring overlapping N-word windows and calling a document fired if any
window fires. Its appeal is that it keeps the binomial machinery and the "document fires"
idiom, unlike firings-per-1,000-words, which needs Poisson replacements for the Wilson bound
and the whole MDR apparatus.

**Measured at N=500 with 50% overlap, it changes essentially nothing:**

- Against the per-document unit, **1 of 16 lenses moves at all**, by 1.8 points.
- Per length quartile, the spreads are **identical**: `reference_capture` +0.311 both ways,
  `institutional_permeation` +0.309 both ways, `sourcing_asymmetry` +0.289 both ways.

The reason is structural rather than a matter of tuning N. These detectors already grade
against a per-1,000-word density, so a window is scored the same way the document is; and
"fires if ANY window fires" gives a long document *more* chances to fire, which pushes in the
same direction as the bias rather than against it. Windowing renames the unit. It does not make
it length-invariant.

**Do not implement candidate 2.** That is the useful half of this result.

## 3. A third option the issue did not name

**Stratify the null by length instead of re-scaling it.** Compare a subject against the
background rate *within its own length band* rather than against the pooled rate.

- It is length-invariant by construction — a 400-word subject is scored against 400-word
  background, and the 410x spread stops mattering because it is never crossed.
- It keeps the binomial machinery entirely: Wilson, `critical_count` and the MDR apparatus all
  work unchanged inside a stratum.
- It costs statistical power, and that cost is the honest argument against it: the pool is 171
  documents, so four strata leave roughly 42 apiece and every MDR widens accordingly.

Candidate 1 (firings per 1,000 words) remains open and is the one that needs the Poisson
rewrite. Between the two, stratification is cheaper to build and more expensive to run; the
rate change is the reverse. Neither is adopted here.

## 4. What this does not do

`background_rate.py` still owns every published rate and none of them moved. `window_rate.py`
measures and prints; it adopts nothing. The issue stays open with candidate 2 struck off, the
magnitude measured, and a third option costed.

And the thing the issue forbids is still forbidden: **re-truncating the corpora to make the
rates comparable.** That chooses a measurement that flatters the instrument over the data that
exists, which is the move this project spent two days indicting in other people's work.

## Reproduce

```bash
python tradecraft/eval/window_rate.py               # both units, N=500
python tradecraft/eval/window_rate.py --by-length   # the quartile table above
python tradecraft/eval/window_rate.py --by-length --windowed   # the refutation
python tradecraft/eval/window_rate.py --sweep       # N = 250 / 500 / 1000 / 2000
```

Needs `corpus/_news-control` and `corpus/_calibration-cache`, which are gitignored, so this
runs on the author's machine and not in CI. That is a real limit on the result and the reason
it is a RESULTS document rather than a gate.
