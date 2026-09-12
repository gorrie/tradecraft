# The cue repair, measured against its pre-registration

**Pre-registration:** `PREREG-2026-09-07-cue-repair.md` + `CUE-REPAIR-2026-09-07.json`, committed at
`eb58a7b8` before any number was looked at. **Tool:** `eval/cue_repair_eval.py` (measurement in
`CUE-REPAIR-2026-09-07-measured.json`, blast radius in `CUE-REPAIR-2026-09-07-boundary.json`).
**Corpora:** PTC 371 articles (chance 0.1325), unannotated PTC background 1,808,987 chars,
general-prose pool 171 docs / 885.3 kwords, 97 fixtures, the record's collateral (328 texts).

## The one-line result

The rule selected **4 of 17** changes — three cuts (`you haven`, `inevitability`, `in an attempt
to`) and one match-local exclusion (`existential` ← *existential risk* / *existential crisis*) — plus
the contraction guard on both engines. Applied, they removed **12 of the 51 read collateral spans,
every one of them cue-only or quoted by both readers**, at a cost of **zero** construct-present
spans, zero fixtures, zero demonstrated detections, and zero PTC lift on any lens that had lift.
Thirteen candidates were **kept** — twelve because the rule's benign-ubiquity gate is measured on
the PTC and general-prose backgrounds, and `training pipeline`, `diffuse`, `arithmetic`, `high
score`, `disruptive`, `proprietary model`, `a few hundred` **never occur there at all**. That is the
finding under the headline: these cues are invisible to every calibration corpus the detector has
and fire only on AI-safety prose, so no evidence the detector is calibrated against can cut them,
and cutting them on one collateral read would be the tuning the pre-registration forbade.

## Verdicts, by the rule

| lens / detection | cue (action) | PTC hits / in-span | own lift [95%] | PTC-bg | general-bg | detection: demonstrated before → after | fixtures broken | collateral occ · read (A / B) | verdict — the deciding reason |
|---|---|---:|---|---:|---:|---|---:|---|---|
| `adept_speech` / candidate-sorting | `you haven` (cut) | 2 / 1 | 3.77 [0.71, 6.84] | 1 | 1 | no → no | 0 | 2 · CO 2 / CO 2 | **CUT** — defective (prefix of *haven't*; gold carried by `passed through the degrees`) |
| `institutional_permeation` / define-crisis-claim-authority | `existential` (exclude `existential risk`, `existential crisis`) | 0 / 0 | — | 0 | 2 | no → no | 0 | 12 · CO 8 QA 2 **CP 2** / CO 9 QA 3 | **APPLY** — pattern attested in 10 read spans; silences neither CP span |
| `institutional_permeation` / build-parallel-institutions | `training pipeline` (cut) | 0 / 0 | — | 0 | 0 | no → no | 0 | 2 · CO 2 / CO 1 QA 1 | KEEP — not benign-ubiquitous (0 / 0) |
| `institutional_permeation` / hidden-or-deferred-cost | `diffuse` (cut) | 0 / 0 | — | 0 | 0 | no → no | 0 | 2 · CO 2 / CO 2 | KEEP — not benign-ubiquitous (0 / 0) |
| `institutional_permeation` / value-as-science | `arithmetic` (cut) | 0 / 0 | — | 0 | 0 | no → no | 0 | 2 · CO 1 / CO 1 | KEEP — not benign-ubiquitous (0 / 0) |
| `institutional_permeation` / astroturf | `grassroots` (replace → `independent grassroots`) | 1 / 1 | 7.55 [1.56, 7.55] | 0 | 0 | no → no | 0 | 1 · CO 1 / CO 1 | KEEP — own lift interval clears 1 on **one** hit; not ubiquitous |
| `institutional_permeation` / attribution-gap | `proprietary model` (cut) | 0 / 0 | — | 0 | 0 | no → no | 0 | 1 · CO 1 / CO 1 | KEEP — not benign-ubiquitous (0 / 0) |
| `institutional_permeation` / carve-out-as-public-good | `level playing field` (cut) | 0 / 0 | — | 0 | 2 | no → no | 0 | 1 · CO 1 / CO 1 | KEEP — not benign-ubiquitous (0 / 2) |
| `institutional_permeation` / infiltrate-existing-institutions | `from within` (cut) | 5 / 3 | 4.53 [1.74, 6.66] | 2 | 4 | **yes → no** | **1** (`inst_permeation_probe`) | 2 · CO 2 / CO 2 | KEEP — demotes a demonstrated detection, breaks a fixture, own lift clears 1 |
| `institutional_permeation` / irreversibility-framing | `inevitability` (cut) | 0 / 0 | — | 0 | 3 | no → no | 0 | 1 · CO 1 / CO 1 | **CUT** — 3 in the general pool; no PTC hit; read cue-only |
| `reference_capture` / elastic-charge | `disruptive` (cut) | 0 / 0 | — | 0 | 1 | no → no | 0 | 3 · CO 3 / CO 3 | KEEP — not benign-ubiquitous (0 / 1) |
| `reference_capture` / anonymous-authority | `a few hundred` (replace → `a few hundred anonymous`) | 0 / 0 | — | 0 | 0 | no → no | 0 | 2 · CO 2 / CO 2 | KEEP — not benign-ubiquitous (0 / 0) |
| `reference_capture` / canvassing-mobilization | `canvassing` (cut) | 2 / 0 | 0.0 [0.0, 4.96] | 2 | 2 | no → no | 0 | 2 · QA 2 / CO 2 | KEEP — not benign-ubiquitous (2 / 2) |
| `militant_mobilization` / sainthood-and-heroes | `high score` (cut) | 0 / 0 | — | 0 | 0 | no → no | 0 | 2 · CO 2 / CO 2 | KEEP — not benign-ubiquitous (0 / 0) |
| `sourcing_asymmetry` / mind-reading | `in an attempt to` (cut) | 3 / 1 | 2.52 [0.46, 5.98] | 2 | 5 | no → no | 0 | 2 · CO 2 / CO 2 | **CUT** — 5 in the general pool; own lift interval spans 1 |
| `sourcing_asymmetry` / mind-reading | `in a bid to` (cut) | 0 / 0 | — | 0 | 0 | no → no | 0 | 1 · CO 1 / CO 1 | KEEP — not benign-ubiquitous (0 / 0) |
| `subculture_register` / managerial-tells | `human capital` (cut) | 0 / 0 | — | 0 | 0 | no → no | 0 | 1 · CO 1 / **CP 1** | KEEP — Reader B found the construct |

**A weakness in the rule, found by applying it.** "Own PTC lift interval clears 1" fired for
`grassroots` on a single hit (Wilson at k = n = 1 gives a lower bound of 0.21, over chance 0.13). The
census requires 5 locatable hits before it judges a detection; the cut rule should have carried the
same floor. It did not change the outcome (`grassroots` was kept by the ubiquity gate as well), and
the rule stands as pre-registered for this run; a future plan should add the floor.

## The contraction guard

Implemented identically in `detect.py` (`_inside_contraction`, behind `CONTRACTION_GUARD`) and
`engine.js` (`insideContraction`); a mechanism fixture (`mech_contraction_is_not_a_boundary`) puts
it under the parity gate; `tests/test_contraction_guard.py` pins possessives and closing quotes.
**Blast radius, measured with the rule on against off across every live cue: 0 rejected matches on
PTC (99 matches), the general pool (163), the fixtures (242) and the collateral (51).** The only
match the guard would ever have rejected was `you haven` inside *haven't*, and the rule had already
cut that cue. The guard costs nothing and closes the hole the next such cue would fall through.

## Lens-level before → after

| measure | lens | before | after |
|---|---|---|---|
| PTC hits · precision · lift | `sourcing_asymmetry` | 34 · 0.118 · 0.89 | 31 · 0.097 · **0.73** |
| | `adept_speech` | 3 (too few to judge) | 1 (too few to judge) |
| | every other lens | — | **unchanged** |
| census: demonstrated detections | | `infiltrate-existing-institutions`, `penalty-without-adjudication`, `maganr-tells` | **the same three, same numbers** |
| detections that fire at all on PTC | | 38 | 37 (`candidate-sorting` 2 → 0; `mind-reading` 4 → 1) |
| fixtures (`run_eval cues --strict`) | | 55 positive fire · 34 negative quiet · 55 markers · 1 cross-camp | **identical** |
| general pool, occurrences per 1k | `institutional_permeation` | 45 · 0.0508 [0.0371, 0.0680] | 42 · 0.0474 [0.0342, 0.0641] |
| | `sourcing_asymmetry` | 53 · 0.0599 [0.0448, 0.0783] | 48 · 0.0542 [0.0400, 0.0719] |
| | `adept_speech` | 2 · 0.0023 | 1 · 0.0011 |
| general pool, documents fired | `institutional_permeation` / `sourcing_asymmetry` / `adept_speech` | 22 / 32 / 2 of 171 | 21 / 31 / 1 |
| lens eligibility (`background-rates.json`) | all 16 | — | **unchanged** |

`sourcing_asymmetry`'s PTC lift **fell** (0.89 → 0.73). It was below chance before and after — the
lens fires on news at the rate news is annotated — so nothing demonstrated was lost, but a
pre-registered prediction said no lift would fall and it did.

## On the record's collateral — the same 51 spans, re-run

| | before | after |
|---|---|---|
| fired spans in the frozen sample | 51 | **39** (12 dropped: 7 `existential` inside *existential risk* / *existential crisis*, 2 `you haven`, 2 `in an attempt to`, 1 `inevitability`) |
| dropped spans' read classes (A / B) | — | **CO 11, QA 1 / CO 11, QA 1 — no construct-present span dropped by either reader** |
| precision on the surviving spans, Reader A | 19.6% (10/51) | **25.6%** (10/39) |
| precision, Reader B | 17.6% (9/51) | 23.1% (9/39) |
| construct-present by both | 8/51 (15.7%) | 8/39 (20.5%) |
| cue occurrences, all lenses | 56 | 44 |
| `institutional_permeation` per 1k | 0.218 [0.141, 0.322], above background | 0.148 [0.086, 0.238], **still above background** (bg now 0.047 [0.034, 0.065]) |
| its top detection | `define-crisis-claim-authority` 48% | `define-crisis-claim-authority` 29% |
| lenses above background | 2 | 2 (`institutional_permeation`, `subculture_register`) |
| spans inside quotation marks (new annotation) | — | **4 of 44 (9%)**: `subculture_register` 2, `institutional_permeation` 1, `inevitability_framing` 1 |

Every gain is on spans both readers called false; nothing a reader called real was lost. The
`institutional_permeation` elevation stands because its remaining 17 occurrences are `from within`,
`training pipeline`, `diffuse`, `level playing field`, `proprietary model`, `arithmetic`, the
surviving `existential`s — all kept by the rule — with 2 construct-present among the 16 read
survivors (12.5%). The record's `#/collateral` flag for that lens still reads *vocabulary artifact*,
correctly.

## Predictions, scored

| # | prediction | result | holds? |
|---|---|---|---|
| R1 | `you haven` CUT; guard removes exactly its 2 collateral matches; blast radius ≤ 5, 0 fixtures | cut; the **cut** removed the 2 matches and the guard then rejects 0 anywhere; radius 0 / 0 fixtures | holds on the numbers; the "exactly its 2" was carried by the cut, not the guard |
| R2 | `from within` KEPT because cutting it demotes `infiltrate-existing-institutions` | kept: demotes the detection **and** breaks `inst_permeation_probe` **and** has own lift | holds |
| R3 | `canvassing` KEPT as not benign-ubiquitous | kept, 2 / 2 | holds |
| R4 | `existential` exclusion APPLIED; removes ≥ 8 of 12 collateral occurrences; silences neither CP span; ≤ 2 PTC hits change | applied; removes **7** of 12 (#39 *Existential kink*, #28 quoted *existential conflict*, #20 and the two CP spans survive); PTC hits unchanged | **three of four; the ≥ 8 is wrong (7)** |
| R5 | ≥ 6 of 17 CUT or APPLIED, ≥ 3 KEPT | **4** applied, 13 kept | **wrong** — the ubiquity gate kept far more than expected |
| R6 | fixtures unchanged; census demonstrated set unchanged; no lens's PTC lift falls; `institutional_permeation`'s rises | first two hold; `sourcing_asymmetry` **fell** 0.89 → 0.73 (below chance either way); `institutional_permeation` **unchanged** | **half wrong** |
| R7 | general-pool per-1k falls ≥ 15% for `institutional_permeation`; no lens rises | falls **6.7%** (45 → 42); nothing rose | **wrong on the size** |
| R8 | ≥ 20 frozen spans stop firing; ≤ 1 dropped span CP; surviving precision > 30%; `institutional_permeation` to *indistinguishable* | **12** stop; **0** CP dropped; **25.6%**; **still above** | **one of four** |
| R9 | ≥ 10% of surviving fired spans in quotes | 9% (4 of 44) | **wrong, narrowly** |

Three hold, one mostly, five wrong or half-wrong. The direction of every miss is the same: the
repair did less than predicted, because the pre-registered rule — correctly — would not cut on the
collateral's say-so alone.

## Rig defects found during the run, fixed and named

- `collateral_eval.py` shipped the quotation annotation without `import re` (a smoke test that never
  reached the function); the first post-repair run crashed before writing. Fixed; the run repeated
  from scratch (deterministic, so exactly).
- `detection_census.py` writes `by_detection` maps in Counter order, so two runs on identical input
  differ by key order. Cosmetic, but it made a pre-measurement look like drift. Not fixed here; noted.
- `lens_floor.py` takes longer than ten minutes on the full pool; re-measured in the background rather
  than skipped, because a floor measured on the old taxonomy is a stale artifact even if no number moved.

## Cut ledger

The instrument page's morgue (`tools/export_web.py` `cut_ledger`) scrapes this table.

| lens | cut | evidence |
|---|---|---|
| adept_speech | `you haven` | defective — a prefix of the contraction *haven't*; fired inside "you haven't been keeping up" and "you haven't read the Model Spec"; the gold phrase is carried by `passed through the degrees`; PTC 2 hits / 1 in-span |
| institutional_permeation | `inevitability` | 3 occurrences in the general-prose pool, 0 PTC hits; its one read span was a story-inspiration list; `inevitable gradualness` and `gradualness` carry the gold |
| sourcing_asymmetry | `in an attempt to` | 5 occurrences in the general pool, PTC lift interval spans 1 [0.46, 5.98]; both read spans were the speaker's own motive or a fiction narrator's |

Not a cut, recorded here so the exclusion is public: `institutional_permeation` /
`define-crisis-claim-authority` keeps `existential` and now carries `excludes: [existential risk,
existential crisis]` — a match within 200 characters of either phrase is suppressed. Attested by 10 of
12 read spans; the two construct-present spans (`existential importance`, `existential threats`)
still fire.

## What this changes, and what it does not

- Taxonomy: three cues gone, one exclusion added. Every derived artifact regenerated
  (`background-rates.json`, `occurrence-rates.json`, `lens-floors.json`, `floors.json`,
  `detection-census.json`, `instrument.json`, the demo split, `collateral-eval.json`); no lens changed
  eligibility state; `floors.json` records no state change.
- Nothing loosened: every action removed or narrowed a firing condition; the guard only rejects.
- **Not done, deliberately:** the thirteen kept cues. The rule that kept them is the right rule for a
  detector that must not be tuned to its last complaint, and it is also why the detector stays wrong
  on this material. The way through is not a looser rule but a **calibration corpus that contains the
  register the collateral is written in** — AI-governance prose — so that "benign-ubiquitous" can be
  measured where these cues actually live. That is a corpus-building task and an author's call.
- Fiction is not handled (no marker in the store); quotation is annotated, never filtered.

## Reproduce

```bash
python tradecraft/eval/cue_repair_eval.py --plan tradecraft/eval/CUE-REPAIR-2026-09-07.json   # verdicts (idempotent after apply: the cut cues are gone, so their rows read 0)
python tradecraft/eval/cue_repair_eval.py --boundary                                          # the guard's blast radius
python tradecraft/eval/run_eval.py cues --strict; python tradecraft/tools/test_engine_parity.py
python tradecraft/eval/collateral_eval.py --check
```
