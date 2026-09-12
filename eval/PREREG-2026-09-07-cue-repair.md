# Pre-registration: the cue repair after the collateral read

Written and committed **before** the measurement runs and before any taxonomy file changes. The
results file (`RESULTS-2026-09-07-cue-repair.md`) names the commit. The candidate list and the
rule are in `CUE-REPAIR-2026-09-07.json`; the tool is `eval/cue_repair_eval.py`, smoke-tested only
on `--help` and on loading its corpora before this file was written — no candidate was measured
and no verdict was looked at.

## What is being repaired, and why a rule

The collateral evaluation (`RESULTS-2026-09-07-collateral-eval.md`) read 51 fired spans; two
readers put the construct behind 10 and 9 of them. The rest were mostly one shape: a cue written
for one register firing in another — `existential` (a research field's name), `training
pipeline` (ML jargon), `high score` (a benchmark), `you haven` (a prefix of *haven't*). The
detector-tuning failure mode is to delete what one corpus disliked. So a cue leaves only through
a rule fixed here and measured on the corpora the detector is calibrated against — PTC (371
annotated articles), the unannotated PTC background (1.81M chars), the general-prose pool
(171 documents), the 97 fixtures — with the cost of each change stated before it is made.

**Tightening precision, never loosening the detector.** Every action removes or narrows a firing
condition. A change that would break a positive fixture, demote a detection the census has
demonstrated, or remove a cue a reader found the construct behind, is **kept** and reported as
kept with the number that kept it.

## Actions and the rule (fixed; the tool applies it mechanically)

| action | what it does | applied iff |
|---|---|---|
| **cut** | remove the cue | no positive fixture breaks; no demonstrated detection is demoted; the cue's own PTC lift interval does not clear 1.0; no read span carried the construct by **either** reader; and the cue is benign-ubiquitous (≥ 3 occurrences in the unannotated PTC background, or ≥ 3 in the general-prose pool) or marked defective |
| **replace** | remove the cue, add the narrower phrasing **from the detection's own gold text** (the 2026-08-26 precedent: `inevitable` → `inevitable gradualness`) | the cut rule holds for the generic form, every added cue is in the gold text, and no added cue is itself benign-ubiquitous |
| **exclude** | keep the cue, add match-local `excludes` phrases (the taxonomy's existing mechanism, used for EO 12988 boilerplate) | ≥ 3 read spans (cue-only or quoted) attest the false-fire pattern; the exclusion silences no span either reader marked construct-present; no fixture breaks; no demonstrated detection is demoted |

"Either reader" is the recall-protecting direction: a cue one reader saw working stays.

## The matcher rule

`you haven` matched inside *you haven't* because the apostrophe is not a word character, so the
bounded matcher saw a boundary. **A boundary inside a contraction is not a boundary.** The
repair is a rule, not a cue edit: a match whose end is followed by an apostrophe (`'` or `’`)
and a letter is rejected unless the tail is an accepted suffix (`'s`). Implemented identically in
`tradecraft/detect.py` (`_find_bounded`, behind `CONTRACTION_GUARD`) and
`website/static/tech/instrument/engine.js` (`findBounded`), parity-gated. Its blast radius —
every match it rejects, on every corpus, across **all** cues — is measured with `--boundary`
and printed, so the rule's cost is a number.

## Candidates (17)

From the read: every cue whose read spans were cue-only or quoted, plus the defective one.
`from within` and `canvassing` are included **expecting the rule to keep them** — the first
carries the demonstrated `infiltrate-existing-institutions` detection, the second is rare in
general prose and is the exact Wikipedia enforcement term the lens was built around. `existential`
and `human capital` had a construct-present read by at least one reader, so they cannot be cut;
`existential` gets the exclusion test for its dominant false-fire pattern, *existential risk*
(9 of its 12 read spans) and the idiom *existential crisis*.

## Predictions — scored in the results, wrong ones kept

| # | prediction | falsified if |
|---|---|---|
| R1 | `you haven` is CUT; the contraction guard removes exactly its 2 collateral matches; the guard's blast radius on PTC + background + fixtures is **≤ 5 matches** across all cues and **0 fixtures** change | more than 5, or any fixture |
| R2 | `from within` is KEPT because cutting it demotes `infiltrate-existing-institutions` | it is cut, or it is kept for a different reason only |
| R3 | `canvassing` is KEPT as not benign-ubiquitous (< 3 in both backgrounds) | it is cut |
| R4 | the `existential` exclusion is APPLIED, removes ≥ 8 of its 12 collateral occurrences, silences neither reader-A construct-present span, and changes ≤ 2 PTC hits | any of the four |
| R5 | at least **6** of the 17 candidates are CUT or APPLIED, at least **3** KEPT | fewer than 6, or fewer than 3 |
| R6 | after apply: `run_eval cues --strict` unchanged (every positive fires, every negative quiet, marker coverage held); the census's demonstrated set is unchanged; no lens's PTC lift **falls**; `institutional_permeation`'s PTC lift **rises** | any regression |
| R7 | background per-1k rate falls by ≥ 15% for `institutional_permeation` and does not rise for any lens | it falls less, or any lens rises |
| R8 | collateral re-run on the frozen 51: ≥ 20 spans no longer fire; **≤ 1** dropped span was construct-present by either reader; precision on the surviving spans rises above 30%; `institutional_permeation` drops from *above background* to *indistinguishable* | any of the four |
| R9 | quotation annotation (new in the rig: a span sitting between paired quotation marks within 600 chars is marked `in_quotes`): ≥ 10% of surviving fired spans are in quotes | < 10% |

## What is measured, in order

1. `cue_repair_eval.py --plan` — every candidate against every corpus; verdicts by the rule.
   Written to `CUE-REPAIR-2026-09-07-measured.json`.
2. Lens-level **before**: `ptc_precision.py --json`, `occurrence_rate.py --json`, the
   detection census's demonstrated set, `run_eval.py cues --strict`.
3. `--apply`; the matcher rule; `--boundary`.
4. Lens-level **after**: the same four, plus `background_rate.py`, `occurrence_rate.py --write`,
   `lens_floor.py`, `floors_contract.py`, `detection_census.py`, `export_web.py`, the demo
   split — every derived artifact regenerated, every gate re-run.
5. Collateral re-run on the frozen 51 (`collateral_eval.py`); the dropped spans and their read
   classes are the repair's cost and benefit on the same spans.

## What must not happen

No cue the rule keeps is touched. No threshold, weight or floor changes. No cue is added from
the collateral (an added cue must be in the detection's gold). If `--apply` and the reload
disagree, nothing is written. Fiction is **not** handled: the store carries no fiction marker and
inventing one from a reading would be tuning; it is flagged. The quotation annotation is a
measurement, not a filter — nothing is suppressed because it sits in quotes.
