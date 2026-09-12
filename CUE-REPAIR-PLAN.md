# Cue repair — the plan

> **CORRECTION 2026-08-26, same day, measured.** The criterion this plan is built on —
> *cut a cue if its phrase occurs ≥3× in neutral background prose* — **is not a precision
> criterion and should not be applied further without a per-detection test.** Restoring four
> of the cut cues to `sourcing_asymmetry/pejorative-actor-label` under a pre-registered test
> raised cues-only lift 1.12 → 1.77 and human-annotated retention 1-of-4 → 12-of-19; the
> removed `far-right` scores 5/5 genuine and `hardline` 4/4, while three of the four cues the
> cut KEPT never fire at all. Frequency measures how common a phrase is, not whether it is
> doing the method when it appears. Wider context: only 58 of 621 cues fire on 371 PTC
> articles, and this cut deleted 34 that did. See
> `eval/RESULTS-2026-08-26-instance-mode-and-restore.md` and
> `eval/PREREG-2026-08-26-label-cue-restore.md`. Step 1 below is left as written, because the
> reasoning that produced it is the point.


The detector's marker concepts are sound and its cue set is not. This is what to do about
it, in the order that keeps each step measurable and reversible.

Evidence: `eval/RESULTS-2026-08-26-ptc-precision.md`. Everything below is measured, and the
two numbers that make step 1 safe were computed *before* proposing it.

## The diagnosis in one paragraph

`institutional_permeation` — the flagship lens, the one the Ratchet's argument leans on —
fires 228 times across 371 news articles at **1.19× chance**. Its top five matched phrases
are `the media` (44), `national security` (37), `ongoing` (31), `movement` (30) and
`judiciary` (20): **71% of all its firing**, from two institution names, a topic and two
ordinary English words. The predictor of a lens's discriminative power is not cue length —
that was tested and is wrong, the longest-cue lens has the worst lift — but how often the
matched phrase occurs in ordinary prose. Measured against PTC lift, monotonic across the top
four lenses: 50% generic → 2.16, 58% → 1.93, 80% → 1.44, 93% → **1.19**.

## Why removing cues should *raise* the score

`detect_cues` fires **once per detection and breaks on the first match**
(`tradecraft/detect.py:196-210`). So a high-frequency cue does not merely add noise — it
**shadows** the specific cues behind it in the same list. `no-success-condition` carries
`ongoing`, `never been more important`, `more must be done`, `cannot be complacent`. Three of
those are real formulations, and `ongoing` matches first in almost any document, so the
detection is almost never recorded on the good ones.

That is why this is a repair and not a retreat: the specific cues are already written. They
are being suppressed by the generic ones sitting next to them.

---

## Step 1 — the measured cut. Ready to run, and de-risked.

**Criterion, disclosed and reproducible:** a cue goes if its phrase occurs **≥3 times** in
1,808,987 characters of PTC news prose with every human-annotated propaganda span removed —
i.e. text six professional annotators declined to mark. Not taste, not length, not my
opinion about the phrase.

**34 cues, 5.2% of the set, across 19 detections.** The list is generated at
`eval/CUT-CANDIDATES-2026-08-26.json`, each row carrying its background count *and the
surviving cues in its detection* so the consequence of each removal is visible.

Two safety numbers, both computed by simulating the cut before proposing it:

| check | result |
|---|---|
| detections left with **no** cues | **0** — every affected detection retains at least one |
| positive fixtures that fire today and would stop | **0 of 56** |

The worst offenders, with what survives them:

| bg | lens / detection | cut | survives |
|---:|---|---|---|
| 143× | sourcing_asymmetry / pejorative-actor-label | `regime` | `cronies`, `maga extremist`, `fringe group`, `fringe figure` |
| 62× | institutional_permeation / carve-out-as-public-good | `national security` | `level playing field`, `remains insufficient`, … |
| 55× | institutional_permeation / target-the-leverage-point | `the media` | `the universities`, `most important instrument` |
| 34× | institutional_permeation / no-success-condition | `ongoing` | `never been more important`, `more must be done`, `cannot be complacent` |
| 24× | institutional_permeation / belief-as-engineerable | `narrative` | `manufacture of consent`, `shape opinion`, `the public must be` |

Each removal is written to the **cut ledger** with its background count as the stated reason,
joining the 118 already there. Nothing is deleted silently and every cut is one line to
revert.

**The falsifiable prediction.** After the cut: `institutional_permeation`'s generic hit share
drops from 93% to under 60%, and its PTC lift rises from 1.19 above 1.5.
**Result (2026-08-26): met, and more expensively than predicted — lift 1.19 -> 2.83, but PTC
firing fell from 228 hits to 16, a 93% drop. The prediction named a precision target and
said nothing about the recall it would cost, which is a defect in the prediction.** Verified by re-running
`eval/cue_exclusivity.py` and `eval/ptc_precision.py`. **If lift does not move, the exclusivity
theory is wrong and that gets written up as a failed prediction, not quietly dropped.**

Regression guard is the existing eval: `eval/run_eval.py cues` must still show 51/51 positives
firing and 32/32 negatives quiet. If cutting breaks a positive, too much came out.

## Step 2 — replenish from receipts, not from imagination

The stubs got there because someone needed a cue and wrote the first word that came to mind.
Replacing them the same way repeats the mistake.

The source is already in the repo: the capture ledger holds **33 FACT-tier records** carrying
verbatim `span` evidence of `permeation` and `gradualism` from documented cases — Webb's
"compelled to make each particular change", the Comintern's "replace them with reliable
communists", the 1921 unity resolution. Those are real formulations from real sources, and
each arrives with a receipt.

Non-circular by construction: those spans were selected as *evidence of the method* by a
sourcing process, never by matching against the cue list they would feed.

`target-the-leverage-point` needs this most — after step 1 it drops to two cues.

**This is authoring on the flagship lens and it changes what the Ratchet's instrument
detects, so it is the author's call, not mine to execute.** I can propose the extracted
formulations with their receipts.

## Step 3 — the engine limit, named so it stops being retried

Some false positives **cannot** be fixed at this layer, and it is worth writing down which.
`loaded_labeling` fires on `far-right` (8×), `extremist` (4×), `hardline` (7×). The detector
is right in principle — this project's own standing rule is that a press label must be
attributed rather than asserted — but in PTC the hits are outlets attributing correctly.
Telling those apart requires knowing whether the label is *quoted* or *asserted*, which is
context, and `detect_cues` has no proximity, no co-occurrence, no negation, and no regex
(cues are `re.escape`d).

So: do not keep trying to narrow those cues. They need an engine change, which touches the
JS/Python parity gate and every lens. Not now, and not as part of this repair.

**Updated 2026-08-26 — measured, and the conclusion holds for a different reason.** The
"engine change" this step asks for already exists: `verify_hit` context-reads a span and
was never wired to anything shipping, so the obvious next move was to restore these cues
and let verify own their precision. That was tested through the full find->verify pipeline
against PTC (`eval/verified_precision.py`, write-up in
`eval/RESULTS-2026-08-26-verify-stage.md`) and **it does not work**: on news prose the
verifier rejects 94% of `institutional_permeation` hits and 100% of `sourcing_asymmetry`
hits, retaining 1 of 6 and 0 of 4 human-annotated spans respectively. It asks whether the
AUTHOR employs the method, and in a news article the author is a reporter quoting someone
else — so the honest answer is `opposite` and the hit dies. The pipeline has no notion of a
SUBJECT distinct from the author, and that, not cue narrowing, is the real missing piece.
**Superseded the same day** — see the correction at the top. The four label cues were restored under a pre-registered test and both success conditions were met. What step 3 got right is that this is not fixable by narrowing cues; what it got wrong is the conclusion that the cues had to go. The missing piece was a verify MODE that asks whether the span is an instance of the technique whoever produced it, rather than whether the document's author is performing it.

## Step 4 — the target-register corpus, when it is worth measuring

Paused, not cancelled. It is the right test of a working instrument and the wrong test of
this one: 200 curated documents would currently measure `ongoing`. It returns when
`institutional_permeation`'s generic share is under 60%. Source probes are already done —
Federal Register API is public-domain, reachable, and gives full plain text; the
`method`-class candidate list is at `corpus/METHOD-CLASS-PROPOSAL.md` awaiting a ruling.

---

## What is being asked

Step 1 is mechanical, disclosed, reversible, and verified not to break anything — say go and
it runs, with the before/after numbers reported either way.

Step 2 is authoring and yours. Step 3 is a decision to *stop* doing something. Step 4 waits
on step 1's result.
