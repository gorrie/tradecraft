# RESULTS 2026-09-03 — the detector reads the bias study's model output

First run of the interaction the plan calls the deep one (§2b): the tradecraft detector grading
the corpus the bias study generates. Adapter: `corpus/to_bias_study.py` (W4.3).

**4,322 responses, 44 models, 8 conditions**, drawn from 13 run directories. Refusals (34),
sub-25-word stubs (94) and failed calls (561) dropped and counted — a refusal is a real finding
for the bias study, which has a table for it, and is not a specimen of any method a lens detects.

Firing rates are compared against each lens's measured general-prose background
(`eval/background-rates.json`), which is what makes "more than usual" a statement rather than an
impression.

---

## 1. Model output against general prose

| lens | model output | general prose | ratio |
|---|---:|---:|---:|
| `institutional_permeation` | 0.185 | 0.088 | **2.1×** |
| `sourcing_asymmetry` | 0.230 | 0.170 | 1.4× |
| `subculture_register` | 0.041 | 0.047 | 0.9× |
| `narrative_management` | 0.012 | 0.018 | 0.7× |
| `reference_capture` | 0.036 | 0.058 | 0.6× |
| `inevitability_framing` | 0.003 | 0.006 | 0.5× |
| **`cognitive_capture`** | **0.002** | **0.006** | **0.4×** |
| `legibility` | 0.011 | 0.035 | 0.3× |
| `rollback_asymmetry` | 0.003 | 0.012 | 0.2× |
| `distributed_accountability` | 0.001 | 0.012 | 0.1× |
| `militant_mobilization`, `adept_speech` | 0.000 | 0.012–0.018 | 0.0× |
| `costly_signal` | 0.000 | 0.000 | — |

**The plan's `cognitive_capture` hypothesis is DISCONFIRMED.** §1's provisional table reasoned
that this lens's home genre "is arguably **model output**, the one corpus this project generates
itself, unencumbered and unlimited", and marked it index-possible on that basis. Measured over
4,322 responses it fires at **0.002 — lower than on general prose, and three times lower.** The
one lens that was supposed to be rescued by having an unlimited corpus is not helped by it.
That row should be revised rather than carried forward.

**`institutional_permeation` at 2.1× is the finding worth keeping.** It is also the only lens
here whose elevation rests on a large count rather than a handful: 0.185 of 4,322 is roughly 800
documents. Model prose talks about entering, staffing and working through institutions more than
general prose does — which is a barometer reading in its own right, and exactly the "a move rare
in public prose may be common in RLHF prose" asymmetry §2b predicted.

## 2. By arm — and one result that is not small

The study's own arms: **A** = no directive in the prompt, **B** = a directive. n ≈ 2,000 each.

| lens | A (no directive) | B (directive) | B/A |
|---|---:|---:|---:|
| **`sourcing_asymmetry`** | **0.332** | **0.155** | **0.47×** |
| `rollback_asymmetry` | 0.001 | 0.004 | 2.7× |
| `reference_capture` | 0.030 | 0.041 | 1.35× |
| `subculture_register` | 0.040 | 0.043 | 1.07× |
| `institutional_permeation` | 0.197 | 0.177 | 0.90× |
| `legibility` | 0.014 | 0.010 | 0.72× |
| `inevitability_framing` | 0.001 | 0.005 | 5.0× |
| `cognitive_capture` | 0.000 | 0.004 | 8.1× |

**`sourcing_asymmetry` halves under a directive**, on ~2,000 documents per arm. That is the only
row here with both a large effect and the counts to support it: unprompted, models produce
attribution-hedging language at 0.332; told to commit, at 0.155.

> **Scope, added 2026-09-04.** Broken out per detection, **89% of that gap is one cue** —
> `unanswered-accusation`, 0.306 against 0.139. Of the other five, one moves the wrong way, and
> only `manufactured-parity` moves the same way with any magnitude (0.014 vs 0.003, intervals
> disjoint, so a real second witness fifteen times smaller). The number above is correct and
> the concept-level reading is supported by two detections; "models produce attribution-hedging
> language" nonetheless invites a broader picture than the data shows. See
> `RESULTS-2026-09-04-arm-effect-is-one-cue.md`.

It also lines up with something the bias study already measured from the other side — the
refusal result, where **not one** of the 32 models measured under both arms declines even once
under a directive prompt, and what abolishes refusal is the presence of a firm instruction
rather than its content. Hedged attribution and outright refusal may be the same reflex read by
two instruments.

**Do not promote this to a finding yet, for two stated reasons.** First,
`sourcing_asymmetry` is the noisiest lens in the taxonomy — background 0.170, the worst
resolution of the four index-bearing ones — and its `declined-to-comment` detection landed in an
annotated PTC span **zero times out of eleven**, which is journalism boilerplate rather than
method. Second, the arms differ in prompt length and structure, and no length-matched null has
been run here; `eval/compare_find_stages.py` exists for exactly that and was not used. The
number is a lead, and the next step on it is the length-matched null, not a write-up.

### THE LENGTH CONTROL, run the same day — `eval/arm_rate_control.py`

The second objection is now answered, and it disposed of one of the two rows above. The arms
**do** differ in length: median 421 words unprompted against 343 instructed. Equal-count strata
over the pooled corpus, each arm's rate compared within bin:

**`sourcing_asymmetry` SURVIVES, in all four strata, every interval disjoint:**

| stratum (words) | A (no directive) | B (directive) |
|---|---:|---:|
| 0–267 | 0.117 (47/403) | 0.040 (24/605) |
| 267–379 | 0.237 (101/426) | 0.133 (79/595) |
| 379–511 | 0.403 (229/568) | 0.207 (92/444) |
| 511–1117 | 0.465 (301/647) | 0.312 (119/382) |

The halving is not length. It holds at every response length, and it is large at every response
length. **This clears the blocker this file set for it.** What remains before it is quotable is
the lens's own noisiness — the `declined-to-comment` problem is unaddressed and is a reason to
report the finding *per detection* rather than at lens level.

**`institutional_permeation`'s A/B difference COLLAPSES inside every bin: it was length.** Its
pooled 0.90× rests on nothing — the lens's firing rate rises monotonically with document length
(0.117 → 0.169 → 0.215 → 0.250) and the unprompted arm is simply longer. Withdrawn.

Note what this does **not** touch: the 2.1× in §1 is model output against *general prose*, a
different comparison. And it runs the other way — the general-prose corpus is the longer of the
two, so a length effect there would *depress* the model-output rate, not inflate it. If
anything 2.1× is understated.

The lesson is the one this repo keeps relearning, and it cost one of two headline rows: a rate
difference between two populations is not a finding until length is held constant, because
`subculture_register`'s index once correlated **-1.000** with document length and the score
simply *was* the length.

The 5.0× and 8.1× rows are noted and should not be quoted: both move between counts near zero
(0.001 → 0.005, 0.000 → 0.004), which is a ratio computed on single-digit document counts.

## 3. What this says about the corpus itself

Twelve lenses fire on model output at or below their general-prose rate, and four of them fire
on nothing at all. The corpus that is unlimited and unencumbered is **not** the corpus that
rescues the silent lenses — it is one more register in which they are silent. The enumeration
ceiling measured earlier the same day is not a fact about news; it survives contact with a
completely different population.

What model output does supply is scale for the two lenses that already work on it, and a
register comparison that costs nothing to regenerate. That is worth having, and it is less than
§1 hoped for.
