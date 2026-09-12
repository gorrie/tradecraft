# The verify stage, measured — and why it is not a drop-in precision layer

Measured on PTC (371 external news articles, human character-span annotation, CC-BY-4.0).
Nothing in this file is measured on the author's manuscripts.

## The setup

`detect.py` has described a two-stage pipeline since it was written — cue matching is "the
high-recall half of a `find(cues) -> verify(model)` pipeline" — and the verify half had no
caller outside a unit test and `eval/verify_eval.py`. So **every precision number this
project has published measured the find stage alone**: `ptc_precision.py`,
`cue_exclusivity.py`, and the 34-cue repair all call `detect(..., backend="cues")`.

That mattered for a live question. `CUE-REPAIR-PLAN.md` step 3 wrote off `far-right`,
`extremist` and `regime` as unfixable at the cue layer, because separating an *attributed*
label from an *asserted* one "requires knowing whether the label is quoted or asserted,
which is context, and `detect_cues` has no proximity, no co-occurrence, no negation." That
paragraph describes the verifier. So the obvious hypothesis was that the cut was aimed at
the wrong stage: a cue that fires often is the find stage doing its job, and precision is
verify's problem.

`eval/verified_precision.py` tests that. It reports three numbers together, because
precision alone is trivially maximised by rejecting everything:

* cues-only precision and lift over chance
* the same, keeping only `verdict == "genuine"`
* **recall cost** — how many hits that landed inside a human annotation were rejected

## The result

Chance precision 0.1325. Every hit sampled (no subsampling was needed at these pool sizes).

| lens | hits | cues-only lift | + verify lift | kept | annotated hits retained |
|---|---:|---:|---:|---:|---:|
| `institutional_permeation` | 16 | 2.83 | 7.55 | 1 (6%) | 1 of 6 (17%) |
| `sourcing_asymmetry` | 27 | 1.12 | — | 0 (0%) | 0 of 4 (0%) |

`sourcing_asymmetry` rejected **every** sampled hit. `institutional_permeation`'s lift more
than doubled by keeping a single hit out of sixteen.

**The hypothesis is not supported. Verify is not a precision layer that can be dropped in
front of a high-recall cue set on this register — it removes the instrument.**

## Why, and it is not a bug in the model

The verifier asks: *is the AUTHOR employing this method?* In a news article the author is a
reporter, and the method — where it is present at all — belongs to a quoted politician. The
correct answer to the question as asked is `opposite`, "attributes it to someone else," and
that is what the model returned.

PTC's annotators marked a propaganda span **wherever it occurred**, without caring whether
the journalist or the quoted subject produced it. So the two are not measuring the same
thing, and the mismatch is in the question, not the answer.

The pipeline is missing a **subject**. These are different tools:

* *is the author of this document employing the method?* — the self-audit question
* *is this span an instance of the technique, whoever produced it?* — the detection question

Only the first is implemented, and it is silently applied to corpora where the second is
what anyone wants. A subject-aware verify is the fix, and it is not a prompt tweak.

## Consequences, including one for a claim made earlier today

1. **The cut stands.** Restoring `far-right` / `extremist` / `regime` on the theory that
   verify would own their precision is unsupported: verify as built rejects them too. The
   earlier claim in this session that the cut was "probably wrong" was reasoning from the
   pipeline's docstring rather than from a measurement, and the measurement disagrees.
   `CUE-REPAIR-PLAN.md` step 3's conclusion — leave them cut — turns out to be right for a
   different reason than it gave.
2. **The cut's falsifiable prediction was met, expensively.** `institutional_permeation`
   cues-only lift went 1.19 → **2.83**, clearing the predicted 1.5. But its PTC firing fell
   from 228 hits to **16**, a 93% drop. Precision bought with recall, at a ratio the plan
   did not predict and should have.
3. **Read both tables with the sample sizes in front of you.** 16 hits with 6 in-span, and
   27 with 4. These lifts are noisy and a single reclassification moves them a lot. They are
   strong enough to reject the "verify is a drop-in precision layer" hypothesis and too thin
   to rank lenses by.

## Two defects found and fixed on the way

* **`verify_hit` returned a confident rejection when the backend was unreachable.** Every
  exception — connection refused, unparseable JSON, no model — became
  `{"verdict": "incidental"}`, indistinguishable from a considered rejection. A dead
  verifier read as a clean bill of health, which is the exact shape of detector-loosening
  the project forbids. It now returns `ok: False` with the error, and callers must refuse
  to record it.
* **The verifier could not tell use from mention.** Asked about a text that *documents* a
  method, it answered `genuine` and said so in its rationale: *"The author quotes Walter
  Lippmann … indicating that the author is employing."* Analysts name methods constantly
  without using them. `VERIFY_PROMPT_VERSION = 2` puts the distinction at the head of the
  prompt; `eval/verify_eval.py` still passes 8/8 on its eight documented real-world cases,
  so it is not simply rejecting more.

  Note the interaction with the finding above: v2 sharpened "attributed to another party →
  `opposite`", which is right for a self-audit and is part of why news hits are rejected
  wholesale. The prompt is correct for the question it asks. The question is the problem.

## Reproduce

```bash
python tradecraft/eval/verified_precision.py --lens institutional_permeation \
                                             --lens sourcing_asymmetry -n 110
```

Sampling is every k-th hit in corpus order — no seed, no shuffle, and it cannot be re-rolled
until the answer improves.
