# Density is a rate now, and the duplication null is exactly satisfied

**2026-09-02.** Author's call on backlog item 33: **count occurrences.** The matcher returns
every firing instead of the first, so `density` becomes what its docstring always claimed —
weighted hits per 1k tokens.

## What was wrong

`detect_cues` fired once per detection by design (*"one firing per detection is enough"*) while
the grader divided by token count. With the numerator bounded at roughly the number of
detections that matched — typically 1 — the expression reduced to `k / document_length`. It was
an inverse-length term wearing the docstring of a rate, and it carried 15% of every index.

## The result

| | before | after |
|---|---:|---:|
| **duplication, max index movement** (all 12 firing lenses) | up to **7.28** | **0.00** |
| `institutional_permeation` text floor, max | 6.7 | **0.0** |
| lenses failing the duplication null | **12 of 12** | **0 of 12** |
| gold recall | 138 of 161 | **138 of 161** |
| tests | 156 | **156** |

Duplication is the one perturbation where any movement is definitionally a defect: the same
document twice has the same rate of method-marking. **Every lens now returns exactly the same
index.** `lens_floor.py` reports 0.0 median, p90 and max across all four perturbations —
sentence-order, chunk-boundary, whitespace and duplication.

## One thing the decision did not ask for, and why it was necessary anyway

Occurrences must NOT flow into `breadth` and `intensity`. Those answer *which markers are
present* and *how strongly*, and marker scores accumulate to a cap — so a document repeating
one cue forty times would max its marker score and read as broad and intense on the strength of
a single phrase. Letting repetition drive intensity would have made intensity a second, worse
copy of density.

So the grader keeps two sums: **every occurrence feeds `total_weighted`** (the rate), and
**each detection contributes once, at its strongest hit, to marker scoring** (the presence).
`engine.js` mirrors both, because diverging there breaks parity on every long document.

## The residual length correlation is now a real property, not arithmetic

Index still correlates with length for some lenses. Decomposed, it is no longer an artifact:

| lens | length↔index | length↔hits | length↔density | reading |
|---|---:|---:|---:|---|
| `institutional_permeation` | −0.504 | **−0.002** | −0.668 | hit count is FLAT with length, so a falling rate is a true statement: long administrative documents genuinely carry fewer permeation markers per 1k tokens |
| `reference_capture` | −0.423 | +0.311 | −0.725 | sublinear growth — a real, lower rate in longer documents |
| `subculture_register` | **+0.959** | **+0.990** | +0.959 | superlinear on **eight documents**; too few to read as anything |

Before this change, `subculture_register` correlated **−1.000** with length — its index *was*
the length. It now correlates positively, driven by hits growing faster than the document, on a
sample of eight. That is a corpus observation awaiting more material, not a finding.

The important line: `institutional_permeation`'s hit count is uncorrelated with length
(−0.002), which is exactly the shape that lets a per-token denominator mean something. The rate
falls in long documents because the rate really is lower there.

## What this does NOT fix

The precision-defects file's structural finding stands untouched: **these lenses are near-blind
in administrative register**, because their cue lists were written for prose that argues.
A long Federal Register document will score lower than a short advocacy tract, and after this
change that is a true statement about marker rate rather than an artifact of division. It is
still a bias in a leaderboard that grades institutions across both registers — the difference
is that it is now a bias with a defensible reading, and the fix for it is corpus and domain
scoping (items 6 and 28), not arithmetic.

## Gates

`lens_floor` 0.0 on every perturbation. `gold_check` 138/161 unchanged. 156 tests. Engine
parity green on both fixture classes, with two new mechanism fixtures that assert occurrence
counts — proved to have teeth: reverting the JS to first-match-only fails
`mech_counts_every_occurrence` with *"got [plain] want [plain,plain,plain]"*.
