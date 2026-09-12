# The `sourcing_asymmetry` arm effect is concentrated in one cue

2026-09-04

The largest cross-instrument result this project has produced was `sourcing_asymmetry` firing
on 0.332 of no-directive model responses and 0.155 of directive ones — a halving, across
~2,000 documents per arm, that **survived length control in all four strata** and so was
reported as a real effect rather than an artifact of response length.

It is real, and two of its six detections move the same way with non-overlapping intervals. But
**one of them carries 89% of the magnitude**, and a reader told only "sourcing asymmetry halves"
would picture something more evenly distributed than what is there.

## Per detection, whole corpus, document rate within each arm

| detection | A (no directive) | B (directive) | gap |
|---|---:|---:|---:|
| **unanswered-accusation** | **0.306** (626) | **0.139** (281) | **0.168** |
| manufactured-parity | 0.014 (29) | 0.003 (6) | 0.011 |
| honorific-framing | 0.014 (29) | 0.019 (38) | **−0.005** |
| single-source-consensus | 0.014 (28) | 0.009 (19) | 0.004 |
| pejorative-actor-label | 0.000 (1) | 0.000 (0) | 0.000 |
| mind-reading | 0.000 (0) | 0.000 (1) | −0.000 |

`unanswered-accusation` is 0.168 of a summed gap of 0.189. One of the other five moves in the
*wrong* direction. `manufactured-parity` is the only other one that moves the same way with any
magnitude, and it is fifteen times smaller — though its interval **is** disjoint from its
counterpart's, so it is a real second witness rather than noise (see below).

**So "sourcing asymmetry halves when a model is told to commit" is true and misleadingly
shaped.** Two of six detections move in the same direction with non-overlapping intervals, so
the concept-level statement is supported; but 89% of the magnitude is one phrasing pattern, and
a lens-level number invites a reader to picture a rhetorical posture shifting broadly when what
shifted is mostly one construction. The scope belongs in the sentence.

This matters more here than it would elsewhere because of the enumeration ceiling measured on
2026-09-03: 97% of `subculture_register`'s cues never fire in 371 articles, and the strongest
detections in this repository rest on very few cues. A lens whose signal is carried by one cue
is a lens that reports its cue's wording, which is why the per-detection view is now printed
alongside the per-lens one rather than being available on request.

## Why per-lens reporting hid it

`arm_rate_control.py` compared arms on `grade_document_for_lens(...).index > 0` — "did anything
in this lens fire". That is the right statistic for the length control it was built for, and it
cannot distinguish a concept moving from a phrase moving. The tool now reports both, sorted by
gap so the driver is the first row, and prints a warning when one detection holds 60% or more
of the summed gap.

Counting is **once per document per detection**, matching the per-lens statistic. Counting hits
would let one verbose document set a detection's rate.

## The control that agrees, as a contrast

`institutional_permeation` was withdrawn on 2026-09-03 because its A/B difference collapsed
inside every length stratum. Its per-detection view says the same thing from the other side:
the largest single gap is `intermediary-laundering` at 0.007, **21%** of the summed gap, spread
across thirteen detections that barely move.

So the two controls can agree (permeation: no length survival, no dominant cue — nothing there)
or disagree informatively (sourcing: survives length, one cue dominates — real but narrow).
Neither control substitutes for the other, which is the argument for running both.

## What changes

- `RESULTS-2026-09-03-detector-on-model-output.md` reports the sourcing halving at the lens
  level. That number is unchanged and correctly computed; its **scope** is narrower than the
  lens name implies, and the per-detection table belongs beside it.
- No withdrawal. The effect survives its length control and its direction is consistent across
  four strata; nothing here says it is not real.
- **`manufactured-parity` IS a second witness**, and a first draft of this file said it was
  only the beginning of one — "a Wilson interval on 35 documents will be wide" — which was an
  assumption instead of a computation. Computed: 29/2044 gives [0.0099, 0.0203] and 6/2026
  gives [0.0014, 0.0064]. **Disjoint.** The denominators are two thousand per arm, so a rate
  of one percent is separable even though the count is small. It is a real second detection
  moving the same way, fifteen times smaller.

  That strengthens the concept-level reading rather than the cue-level one, and the honest
  summary is therefore two-part: **two of six detections move in the same direction with
  non-overlapping intervals, and one of them carries 89% of the magnitude.** The effect is not
  a single-cue artifact. It is also not evenly distributed across the concept, and a reader
  told only "sourcing asymmetry halves" would picture the second thing.
