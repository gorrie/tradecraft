# Pre-registration: should the cut label cues come back under instance-mode verify?

Written and committed **before** the restoration is run. The point of writing it down is
that a prediction which can be adjusted after seeing the number is not a prediction.

## The question

The 2026-08-26 cue repair cut four cues from
`sourcing_asymmetry/pejorative-actor-label` for firing too often in neutral news prose:

| cue | background count |
|---|---:|
| `regime` | 143× |
| `far-right` | 8× |
| `hardline` | 7× |
| `extremist` | 4× |

`CUE-REPAIR-PLAN.md` step 3 said these could not be fixed at the cue layer, because telling
an *attributed* label from an *asserted* one needs context. That is the verifier's job. But
the verifier was then measured in **author mode** — "is the document's author employing this
method?" — and in a news article the author is a reporter, so every attributed label came
back `opposite` and the whole lens was rejected 27 of 27.

**Instance mode** asks a different question: is the span an instance of the technique as it
appears, whoever produced it? That is the question PTC's annotators answered. So the cut
deserves one re-test under the right question, and this is it.

## The prediction

Restoring the four cues to `pejorative-actor-label` and re-running
`eval/verified_precision.py --lens sourcing_asymmetry --mode instance -n 0`:

1. **Hit count rises substantially** — `regime` alone appeared 143× in the neutral
   background, so the find stage will fire far more often than the current 27.
2. **Cues-only lift FALLS** below its current value. These cues were cut precisely because
   they occur freely in ordinary reporting; nothing about the verifier changes what the cue
   matcher does.
3. **The real test is what verify does with the extra hits.** The restoration is justified
   if, after instance-mode verification, BOTH hold:
   - verified lift is **at least as high** as the pre-restore verified lift, and
   - **in-span retention improves in absolute terms** — more human-annotated spans
     retained than the pre-restore run retained, not merely a better percentage of a
     smaller pool.

   Percentage alone is not enough and is the trap: rejecting almost everything produces a
   flattering ratio. The count of true positives kept has to go UP.

## What each outcome means

| outcome | ruling |
|---|---|
| both conditions hold | The cut was aimed at the wrong stage. Restore the cues, and re-examine the other 30 on the same basis. |
| verified lift holds but absolute retention does not | No gain. The verifier is filtering the new hits out again; leave them cut. |
| verified lift falls | The verifier cannot separate these at all. Step 3's conclusion stands on its own terms and this line of attack is closed. |

## Constraints on the run

- Same corpus, same threshold, same background as the original cut. Nothing is re-tuned.
- Every hit verified, no subsampling (`-n 0`), so the comparison is not a sampling artefact.
- `eval/run_eval.py cues` must still pass 51/51 and 32/32 afterwards either way.
- If the restoration loses, **the cues go back out and this file stays** as the record that
  it was tried and failed. A negative result that gets deleted is a negative result that
  gets re-attempted every six months.

---

## OUTCOME (run 2026-08-26, after this file was committed at `23948b3`)

**Both conditions met. Cues restored and kept.** Full write-up:
`RESULTS-2026-08-26-instance-mode-and-restore.md`.

| | before | after |
|---|---:|---:|
| hits | 27 | 81 |
| cues-only lift | 1.12 | 1.77 |
| verified lift (instance) | 0.42 | 1.68 |
| annotated spans retained | 1 of 4 | 12 of 19 |

**Prediction 2 was wrong** — it said cues-only lift would fall, and it rose. That is the
result worth keeping: the cut criterion ranked cues by how common the phrase is in ordinary
prose, which is not the same as whether the phrase is doing the method when it appears. Of
the four cues left on this detection after the cut, three (`maga extremist`, `fringe group`,
`fringe figure`) never fire at all, while the removed `far-right` scored 5/5 genuine and
`hardline` 4/4.

---

## STATUS NOTE 2026-09-07 — the restore did not survive

The OUTCOME above stands as the record of the test and its result. It does not describe the
taxonomy. On 2026-08-27, commit `d736288`, the author pulled the four restored cues (`regime`,
`far-right`, `hardline`, `extremist`) from `sourcing_asymmetry/pejorative-actor-label`: a won
pre-registered test does not outrank the author on his own vocabulary, and the restore took a
4-0 right-directed list to 8-0. The detection carries the original four cues only. **The four
are cut, not restored.** This file stays as the record that it was tried, won, and was pulled.
