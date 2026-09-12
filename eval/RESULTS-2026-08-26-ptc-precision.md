# PTC benchmark — 2026-08-26

First measurement of this detector against **independent human span annotation**. Two runs
over the Propaganda Techniques Corpus (SemEval-2020 Task 11): a precision-with-baseline
benchmark, and the existing false-positive audit pointed at a news-register background it
has never had.

## The corpus

[PTC](https://zenodo.org/records/3952415), CC-BY-4.0, vendored at `research/external/ptc/`.
371 training articles, **5,468 propaganda spans annotated at character level by six
professional annotators**, 18 techniques. Sampled from 13 propaganda and 36 non-propaganda
news outlets, mid-2017 to early 2019.

Why it matters here: the detector's own eval is 51 positives and 32 negatives. That is a
smoke test — it shows the cues fire on text written to make them fire. It cannot show
whether they also fire all over ordinary journalism, and **adding cues without a benchmark
is how a detector silently gets worse.** This is the benchmark.

## Run 1 — precision against annotation, with chance as the baseline

`python tradecraft/eval/ptc_precision.py`

    371 articles · 5,468 annotated spans · 275,776 of 2,081,888 chars annotated
    chance precision = 0.1325   (13.2% of characters sit inside some annotation)

| lens | hits | in-span | precision | lift |
|---|---:|---:|---:|---:|
| subculture_register | 14 | 4 | 0.286 | **2.16** |
| reference_capture | 43 | 11 | 0.256 | **1.93** |
| sourcing_asymmetry | 131 | 25 | 0.191 | 1.44 |
| institutional_permeation | 228 | 36 | 0.158 | 1.19 |
| narrative_management | 35 | 1 | 0.029 | **0.22** |

**Read the lift, not the precision.** 13.2% of the corpus's characters are inside some
annotation, so a lens landing there 13.2% of the time is firing at chance. Lift is
precision ÷ chance. This is the same discipline the DISARM comparison had to learn: a rate
without its own baseline is not evidence.

### Finding 1 — the detector is nearly silent on real journalism

**Ten of fifteen lenses fire fewer than ten times across 371 articles and 2.08 million
characters.** Five fire zero or once:

    cognitive_capture 0 · costly_signal 0 · counterproductivity 0 · network_brokerage 0
    revolving_door 0 (network lens, no text cues by design) · adept_speech 1
    inevitability_framing 1 · distributed_accountability 2 · legibility 2
    militant_mobilization 4

Part of this is scope and is not a fault: `costly_signal` and `adept_speech` are not about
news register, and `revolving_door` has no text cues on purpose. But it does mean **this
corpus cannot evaluate two thirds of the taxonomy at all**, and the thinness is not
"few cues" so much as *too few to fire*.

### Finding 2 — where it does fire, discrimination is weak

The two highest-volume lenses are the two weakest. `institutional_permeation` fires 228
times at **1.19× chance** — essentially indistinguishable from firing at random. That is
the flagship lens.

### Finding 3 — one lens fires BELOW chance, and the cause is identifiable

`narrative_management` at **0.22×** means its hits land in un-annotated prose *more* than
chance. Broken down:

| detection | hits | in-span |
|---|---:|---:|
| `impute-bias-affiliation` | 28 | 0 |
| `passive-actor-erasure` | 3 | 0 |
| `unproven-blame` | 1 | 1 |
| four others | 3 | 0 |

`impute-bias-affiliation` is 28 of 35 hits and **zero** land in an annotation. The cues
doing it are `funded by` and `ties to` — ordinary reporting idiom ("the study, funded by
NIH"; "a group with ties to the ministry"). `passive-actor-erasure` fires on
`shots were fired`, which is how a reporter writes an event whose actor is genuinely
unknown.

The *concept* is sound — imputing bias by affiliation is a real move. The cue is too bare
to carry it, and the cues backend has no context verification to save it.

## Run 2 — the FP audit against a news background

`fp_audit.py` already scans every cue against a benign background; its background was
public-domain books, which do not contain journalistic idiom at journalistic frequency.
Pointed at **PTC prose with every annotated span removed** — 1.81M characters of news that
six annotators declined to mark — it reports:

    audited 649 cues across 15 lenses; 76 appear in background (review)

| lens | dual-use cues |
|---|---:|
| sourcing_asymmetry | 26 |
| institutional_permeation | 20 |
| reference_capture | 12 |
| narrative_management | 6 |
| subculture_register | 5 |
| legibility, distributed_accountability | 2 each |
| adept_speech, inevitability_framing, militant_mobilization | 1 each |

### The unambiguous ones

`refusal_as_closure` firing on **`declined to comment` (4×), `refused to comment` (2×),
`did not immediately respond` (2×)**. Those are not rhetorical closure; they are a reporter
recording that they asked. This is a defect, not a judgment call.

`unsubstantiated_attribution` on **`in an attempt to`** — too bare to mean anything.

### The judgment calls, for the author

`loaded_labeling` on `far-right` (8×), `far-left` (3×), `hardline` (7×), `extremist` (4×).
The detector is *right in principle* — this project's own standing rule is that a press
label must be attributed rather than asserted. But in this corpus the hits are outlets
attributing, which is the correct usage. Narrowing needs context, not deletion.

`subculture_register` on `white privilege` — the taxonomy already annotates this one as
"leaking into general use; monitored". The monitoring just produced a reading.

## Nothing was cut

No cue was removed and no threshold moved. The standing rule is that a detector is not
loosened to make a number look better, and the mirror of it applies here: a cue is not
deleted because one corpus dislikes it. This is the evidence; the cuts are the author's
call and belong in the cut ledger with reasons, where 118 already are.

## Reproducing

    # background: PTC prose with every annotated span removed
    python - <<'PY'
    # see the snippet committed in this run's history, or:
    #   for each train-articles/articleN.txt, drop every [start,end) in the matching
    #   train-labels-task1-span-identification/articleN.task1-SI.labels, concatenate
    #   the remainder into tradecraft/eval/ptc-background/bg_ptc_unannotated.txt
    PY
    python tradecraft/eval/ptc_precision.py
    python tradecraft/tools/fp_audit.py tradecraft/eval/ptc-background

PTC is CC-BY-4.0. Attribution: Da San Martino et al., *SemEval-2020 Task 11: Detection of
Propaganda Techniques in News Articles*, DOI 10.5281/zenodo.3952415.

---

# Follow-up, same day — the diagnosis, and a wrong hypothesis of mine

The plan coming out of the above was to build a target-register corpus, on the reasoning
that PTC is news and permeation language lives in rulemaking, so a lens scoring at chance
here proved nothing. **That reasoning was wrong, and checking it cost one query.**

## `institutional_permeation` is matching common nouns

Its 228 hits on PTC news come from 23 distinct matched phrases. The top five:

| phrase | hits | share | in-span |
|---|---:|---:|---:|
| `the media` | 44 | 19% | 9 |
| `national security` | 37 | 16% | 4 |
| `ongoing` | 31 | 14% | 5 |
| `movement` | 30 | 13% | 4 |
| `judiciary` | 20 | 9% | 0 |

**Top five = 71% of all firing. Top fourteen = 96%.** Two institution names, a topic, and
two ordinary English words.

It is not a corpus problem. Reading the taxonomy confirms it is structural:
`target-the-leverage-point` has five cues of which three are `judiciary`, `the courts`,
`the media`; `no-success-condition` fires on `ongoing`; `astroturf` fires on `movement`;
`carve-out-as-public-good` fires on `national security`. **21 of the lens's 75 cues are
single words.** The marker concepts are sound. The cues standing in for them are keyword
stubs, and a 200-document corpus would have measured "ongoing".

## The hypothesis that failed

Obvious next guess: cue length predicts discrimination, so score the lenses by mean cue
length. **The data says the opposite, cleanly.**

| lens | mean words/cue | % single-word | PTC lift |
|---|---:|---:|---:|
| narrative_management | 3.25 | 2% | **0.22** |
| sourcing_asymmetry | 2.68 | 18% | 1.44 |
| institutional_permeation | 2.25 | 28% | 1.19 |
| reference_capture | 2.24 | 25% | 1.93 |
| subculture_register | 2.16 | 30% | **2.16** |

The longest-cue lens has the worst lift; the shortest and most single-word has the best.
Length is not specificity: `SHTF` is one token and appears essentially nowhere outside
prepper writing, while `in an attempt to` is four tokens and appears everywhere.

## What does predict it

**How often the matched phrase occurs in ordinary prose.** Share of a lens's hits whose
phrase appears ≥3× in 1.81M characters of news that annotators declined to mark:

| PTC lift | generic hit share |
|---:|---:|
| 2.16 | 50% |
| 1.93 | 58% |
| 1.44 | 80% |
| 1.19 | **93%** |
| 0.22 | 89% |

Monotonic across the top four. And `subculture_register`'s own docstring had the principle
all along — *"unlike a repurposed common word, a coined tell IS the membership marker, so it
is a high-precision signal by construction"* — the lens that follows it is the one that
scores, and the flagship lens does not follow it.

## Why this matters more than the corpus

`tradecraft/eval/cue_exclusivity.py` computes it, and it **needs no human annotation**. So
unlike the PTC lift it can be pointed at any register, and it can be run before and after a
cue edit to see whether the edit helped. That is the "benchmark before cues" requirement
satisfied without the target-register corpus existing yet.

Concrete target: `institutional_permeation` at 93%. Get it under 60% — where
`reference_capture` sits at 1.93× lift — and the lift should follow. That is a falsifiable
prediction, and re-running `ptc_precision.py` after the cue work tests it.

## Still not cut

No cue removed, no threshold moved, no marker retired. The evidence is now specific enough
to name individual phrases, which makes the cuts a smaller and better-informed decision —
and still the author's.

## The corpus plan is paused, not cancelled

It is the right test of a working instrument and the wrong test of this one. It goes back on
the table once `institutional_permeation`'s generic share is under 60%; measuring it before
then would produce a number about `ongoing`.

---

# Applied — the cut, and what it did

Prediction was written before running: `institutional_permeation` generic share 93% → under
60%, lift 1.19 → above 1.5. **Both held.** With a caveat that matters more than the headline.

## Regression guard first

    positives fired:   51/51
    negatives quiet:   32/32
    marker coverage:   51/51

Coverage broke on the first attempt and is worth recording. `inst_fabian_webb_real` — Sidney
Webb's verbatim 1923 address — stopped firing its expected `gradualism` marker, because the
cut removed `inevitable`, and Webb's sentence is *"the **inevitable** gradualness of our
scheme of change."* In news `inevitable` is filler; in that text it is the doctrine's own
name for itself, and a frequency criterion cannot tell those apart.

The fix was not to restore the bare word. `inevitable gradualness` occurs **0 times** in the
1.81M-character background and `gradualness` twice, so both went in as Webb's attested
phrasing. Strictly better than what was cut: more specific, and coverage restored. **That one
fixture is the whole argument for step 2** — cut the generic form, replace from the receipted
source — and it arrived on its own.

## The measurement, with intervals

Volume collapsed, so point estimates alone would overstate this. Wilson intervals:

| lens | n | lift before | lift after | 95% CI | verdict |
|---|---:|---:|---:|---|---|
| militant_mobilization | 4 | — | 5.66 | [2.27, 7.20] | above chance |
| subculture_register | 7 | 2.16 | 4.31 | [1.89, 6.35] | above chance |
| reference_capture | 18 | 1.93 | 3.77 | [2.19, 5.36] | above chance |
| **institutional_permeation** | 16 | **1.19** | **2.83** | [1.39, 4.63] | **above chance** |
| narrative_management | 4 | 0.22 | 1.89 | [0.34, 5.28] | not distinguishable |
| sourcing_asymmetry | 27 | 1.44 | 1.12 | [0.45, 2.45] | not distinguishable |

**The flagship lens now discriminates.** 1.19 → 2.83 with an interval excluding chance. It was
indistinguishable from random and it is not any more.

**`narrative_management` climbed out of below-chance** (0.22 → 1.89) but at 4 hits and 1
in-span that is one observation, not a result. Reported as not distinguishable.

**One went backwards.** `sourcing_asymmetry` 1.44 → 1.12, and its interval now includes
chance. Eight cues came out of `pejorative-actor-label` alone. That is a real cost of the cut
and it is not being buried.

## The trade being made

Hit volume fell hard: `institutional_permeation` 228 → 16, `sourcing_asymmetry` 131 → 27,
`narrative_management` 35 → 4. **This bought precision with recall.** On the README's stated
primary input — a subject's whole corpus — trading noisy volume for accurate hits is the right
direction. On a single pasted passage it means the detector will now often say nothing. Both
are true and neither is hidden.

## Cut ledger

> **CORRECTION 2026-08-26 (same day).** The "cut" column below over-claims. Five of the cues
> it lists — `diffuse`, `existential`, `experts say`, `many believe`, `white privilege` — were
> never in the applied cut list (`CUT-CANDIDATES-2026-08-26.json`, 34 cues) and are **still
> live in the taxonomy**. The table was written from the analysis; `apply_cut.py` ran from the
> JSON; nobody compared them, so the exported Morgue published five cues as dead that the
> detector is actively firing. Caught by deriving the ledger against the taxonomy in
> `tools/export_web.py` rather than trusting this prose — a cue cannot be both cut and live.
>
> Separately: `regime`, `far-right`, `hardline` and `extremist` WERE cut, and were **restored
> the same day** under a pre-registered test that they won. See
> `RESULTS-2026-08-26-instance-mode-and-restore.md`. The table is left as written because it
> is the record of what was decided; the taxonomy is the record of what is true.
>
> **CORRECTION 2026-09-07.** The sentence above no longer holds. The exported Morgue is
> scraped from the cut column below, not from this note, so a column that over-claimed went
> on announcing five live cues as dead on every export (`freshness_gate.py`
> `cut-ledger-live`, `instrument-export`). The column is now the applied list, not the
> analysis: `diffuse`, `existential`, `experts say`, `many believe` and `white privilege`
> are removed from it, and `irreversible` and `SHTF` -- in `CUT-CANDIDATES-2026-08-26.json`
> and absent from the taxonomy since that day, but missing from the table as written -- are
> added. The rows now account for the same 34 cues the JSON lists. The original column is
> preserved verbatim in the correction above.
>
> **CONSISTENCY NOTE 2026-09-07.** "Restored the same day" above is true of 2026-08-26 and
> false of the taxonomy now. The four label cues (`regime`, `far-right`, `hardline`,
> `extremist`) were **pulled again on 2026-08-27 at `d736288`** — the author's call on his own
> taxonomy, which outranks a won pre-registered test. `pejorative-actor-label` carries the
> original four cues only (`cronies`, `maga extremist`, `fringe group`, `fringe figure`).
> They are cut, not restored.


| lens | cut | evidence |
|---|---|---|
| institutional_permeation | `the media` `judiciary` `the courts` `ongoing` `movement` `national security` `narrative` `messaging` `inevitable` `long-term` `long-range` `network of` `irreversible` | occurs 3–62× in 1.81M chars of news six annotators declined to mark; `inevitable` replaced by Webb's attested `inevitable gradualness` (0×) |
| sourcing_asymmetry | `regime` `radical` `so-called` `hardline` `extremist` `apologist` and 6 more | `regime` alone occurs 143×; several are also factionally asymmetric, which fails the three-axis "symmetric or void" rule independently of frequency |
| narrative_management | `ties to` `funded by` `shots were fired` | ordinary reporting idiom; 28 of 35 hits, zero in an annotation |
| reference_capture | 4 cues | ≥3× in background |
| subculture_register | `novus ordo` `SHTF` | `SHTF` 7x in background; the taxonomy had annotated `white privilege` as "leaking into general use; monitored" but it was not in the applied list |

All 34 are reversible in one commit and listed with counts in
`eval/CUT-CANDIDATES-2026-08-26.json`.
