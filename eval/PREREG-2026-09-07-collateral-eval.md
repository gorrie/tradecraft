# Pre-registration: the working detectors on the record's real-world collateral

Written and committed **before** the first full run. The results file
(`RESULTS-2026-09-07-collateral-eval.md`) names the commit this file landed in. A rule that can
be adjusted after seeing the number is not a rule.

## The question

The detectors have been measured on their calibration corpora — PTC (`detection_census.py`,
`ptc_precision.py`), the general-prose background pool (`background_rate.py`,
`occurrence_rate.py`), the bias study's model output (`RESULTS-2026-09-03-detector-on-model-
output.md`) — and on the author's own books (`/tech/instrument/`, the one deliberate exception
to *books are not the corpus*). They have **never been run, as a measurement, on the material
THE RECORD actually tracks about its own entities.** This is that run.

## What "collateral" means here, and what it does not

**Used:** `research/ratchet-mcp/server/data/texts.jsonl` — verbatim public statements
attributed to dataset persons (speeches, op-eds, posts, testimony), each with a source URL.
At this writing: **328 texts, 20 persons, 114,615 words, median 39 words, 2017-11-26 to
2026-06-29**, sha256 `685322306849adc5`. This is the store the texts-by-person lane
(`tradecraft.subject`, the MCP `grade_person_texts` tool) was built to read, and it is the
only collateral already on hand for the record's entities.

**Rolled up to a board institution** only where `edges.jsonl` affiliates a person-with-texts
to a `capture_leaderboard.json` institution (exact-label match to a graph institution — the
same rule `tools/build_record.py` uses). Measured before writing this file: **one** of 36
board institutions has any — Stanford Internet Observatory, via DiResta (26 texts) and Stamos
(12). The other 35 will print *no collateral on hand*. That is the honest shape of the
inventory, not a gap to paper over.

**Not used:** the author's manuscripts (never a detector corpus; the instrument page is the
exception and it is not this measurement); the PTC benchmark; the bias study's model output.

**Alternatives named, not taken this pass** (flagged for the author): (a) the 150 ledger
records' receipt URLs — institutional documents, cheaply fetchable serially through the
existing `corpus/` fetchers, but each needs an own-output-vs-third-party-reporting ruling
before it can be called the institution's collateral; (b) fresh collection of each board
institution's own statements/filings. Either would be a second pre-registration.

## What is fixed

| parameter | value | why |
|---|---|---|
| rig | `eval/collateral_eval.py`; smoke-tested on the first 3 texts only before this file was written | nothing else has been run |
| detector 1 | tradecraft `cues` backend, every **text** lens (14; `revolving_door` and `network_brokerage` excluded as graph lenses, per `subject.py`), shipped taxonomy **unchanged** (sha256 `7a9fe27e075fb5fb`, recorded in the output) | deterministic, offline, the same engine the browser runs (`test_engine_parity.py`) |
| detector 2 | the capture scanner — the **shipped** `scanner.js` + `capture-cats.js`, driven through node by `eval/scanner_harness.js`; `scanner.js` gained a `measure()` export in the same commit so no formula is copied | a Python re-implementation would be a third copy of a wordlist that already drifted once |
| not run | the tradecraft LLM find/verify stage (local 14B is held by the detached Phase-1.2 measurement; its 37% span-fabrication rate is an open defect); the bias study (measures models, reads no third-party text); `ratchet_series.py` (reads administrative action series) | recorded as *not run* / *not applicable*, never as null |
| unit 1 | documents fired / n, Wilson 95% | the `background-rates.json` unit, for comparability — and predicted to mislead here (P5) |
| unit 2 | cue occurrences per 1,000 words, exact Poisson 95% (`occurrence_rate.poisson_ci`) | the length-invariant unit (issue #7); the one a verdict is read from |
| rulers | `background-rates.json` `background_full_pool` (171 docs) and `occurrence-rates.json` (885.3 kwords); the **wider** of exact / quasi-Poisson per that file's rule | the rulers `/tech/instrument/` and `/tech/tradecraft/` already print |
| verdict rule | interval comparison only: *above background* iff the collateral per-1k lower bound exceeds the background upper bound; *below* iff the upper is under the background lower; otherwise *indistinguishable* | never a point comparison |
| power statement | for every lens: the smallest per-1k rate whose Poisson lower bound at this corpus's exposure clears the background upper bound, printed as a multiple of background | "no evidence, and no power" is a different sentence from "absent" |
| one-cue flag | a lens with ≥ 5 occurrences whose top detection carries ≥ 80% of them | the 2026-09-04 finding: an "arm effect" that was one cue |
| hand-read | 40 fired spans sampled without replacement, `random.Random(20260907)`, from all cue hits of lenses with > 3 hits; **every** hit of a lens with ≤ 3 hits read in full; ±120 chars context; spans written into the JSON | the read is checkable span by span |
| hand-read classes | **construct present** (the text does the thing the detection names) · **cue-only** (literal phrase, construct absent) · **quoted / attributed** (the speaker is citing or criticising the phrase, not deploying it) · **unreadable** (span too short / mis-located) | the third class is the failure the cue matcher cannot see by design |
| receipts comparison | the 24 records of `receipts.jsonl` (earlier model-read detections on these texts): does the cue arm fire the same lens on the same text; does any cue land inside the receipt's span | the model arm and the cue arm on the same collateral |
| word count | `background_rate.tokens` (whitespace split) | the same denominator as the rulers |
| seed | 20260907 | |

Nothing is re-tuned. No cue, weight, threshold or taxonomy changes between this file and the
results. A rig defect found during the run is fixed, named in the results, and the run
repeated from scratch (the rig is deterministic, so "repeated" is exact).

## Predictions — scored in the results, wrong ones kept

| # | prediction | falsified if |
|---|---|---|
| P1 | `sourcing_asymmetry` has the highest documents-fired rate of the 14 lenses | any other lens fires on more documents |
| P2 | `institutional_permeation` is **above background** on the per-1k unit (the 2.1× on model output; these are AI-governance actors talking about institutions) | verdict is *indistinguishable* or *below* |
| P3 | `inevitability_framing` records ≤ 2 cue occurrences in 328 texts (its cue arm fired 5 times on 371 PTC articles) | ≥ 3 |
| P4 | at least 6 of 14 lenses record **zero** occurrences and print a detectable-multiple ≥ 2× background | fewer than 6 zeros, or a zero lens whose exposure could have detected < 2× |
| P5 | documents-fired is **below** the background documents-fired rate for ≥ 8 of 14 lenses, while the per-1k unit is *indistinguishable or above* for at least half of those same lenses — the extensive margin on 39-word texts, which is why per-1k is the unit read | fewer than 8 below on docs-fired, or per-1k agrees with docs-fired on most of them |
| P6 | at least one lens is flagged **one cue** | none flagged |
| P7 | hand-read precision (construct present / readable spans) lands **between 40% and 60%** | ≥ 60% (doing well) or < 40% (doing badly) — both are reported as such |
| P8 | the cue arm fires the same lens on the same text for **≤ 25%** of the 24 receipts (most receipt lenses are model-only or thin-cued) | > 25% |
| P9 | scanner: ≥ 90% of texts land in the **Low** band; DiResta and Stamos have the two highest *asserted per 1,000 words* — because `misinformation` / `disinformation` / `conspiracy theorist` are their field's vocabulary and the 110-char attribution window is the only thing standing between "subject matter" and "smuggle" | < 90% Low, or either of them outside the top two |
| P10 | exactly **1 of 36** board institutions has collateral on hand (SIO) | any other count |

## What counts as doing well vs badly

**Doing well** = the rulers apply (every rate carries an interval and a comparable
background); the per-1k unit and docs-fired disagree in the predicted direction on short texts
(the length-invariance argument holds on real collateral); hand-read precision ≥ 60%; no lens
dominated by one cue; the cue arm recovers a meaningful share of the model-read receipts.

**Doing badly** = hand-read precision < 40%; one-cue dominance on a lens that would print a
rate; a lens "above background" whose hits are the speaker's professional vocabulary or
quoted material rather than the construct; scanner "High" bands driven by field terms. Each
of these is reported as the failure it is, on the page that surfaces the result, next to the
number it qualifies. Nothing is smoothed.

**Neither** = a lens with zero occurrences at an exposure that could not have detected a
plausible elevation. That is *no evidence, and no power*, printed with the multiple.

## Known limits, stated before the run

- **Selection.** `texts.jsonl` was assembled by hand for the receipts lane; it is not a random
  sample of anyone's output. Rates describe *the store*, not the person.
- **Attribution blindness.** The cue matcher cannot tell a speaker deploying a phrase from a
  speaker quoting it to criticise it. The hand-read's third class measures how often that
  bites; the scanner's ATTRIB window is the only automated defense either detector has.
- **Short texts.** Median 39 words against a background pool of ≥ 140-word documents. This is
  the whole reason two units are printed.
- **Named people.** Every number is *what the text exhibits*, attributed to the text with its
  URL — the store's own rule (`texts.README.md`). Not a finding about anyone's character or
  motives, and the surface says so beside every reading.

## Where the result goes

`eval/collateral-eval.json` (the artifact, recomputed by `--check`), the RESULTS file, and —
if the measurement holds up to its own rulers — a `collateral` block in THE RECORD's store so
the board row for any institution with collateral on hand, and the dossier of any person with
texts, can print the reading beside its ruler. Institutions without collateral print that.
