# Target-register corpus — plan v2

> **SUPERSEDED** — by `PLAN-2026-09-02-barometer-realization.md`, and its central premise is DISPROVEN rather than merely stale. This file plans a corpus acquisition on the theory that the silent lenses need a different register. Measured 2026-09-02/03: congressional hearings produced almost nothing, public rulemaking comments produced nothing, and across all 600,458 words held the silent lenses' cue phrases are ABSENT rather than blocked -- with "counterproductive" appearing once in 600k words and its concept-synonyms zero times. The missing material is a different GENRE of authorship and the blocker is licensing. Do not re-queue a register-acquisition item from here.


Supersedes the v1 plan (`~/.claude/plans/delightful-hugging-kite.md`) on sequence and
statistics. v1's **guards are kept verbatim** — selection by organisation never by text,
matched extraction, commit before reveal — because they are the part that was right.

v2 exists because v1 was written before four things were measured, and each of them
changes what the corpus can answer.

---

## What v1 did not know

**1. The control class is nearly silent, and that was measured, not assumed.**
20 Federal Register RULE documents, 153,159 words, fetched paced and public-domain
(`calibrate_register.py`, set committed in `calibration-set.json` and excluded from the
labelled corpus). The **entire 15-lens taxonomy fires twice.** Cue liveness: **2 of 621**.
For comparison, PTC news liveness is 58 of 621.

**2. The vocabulary is present in the text; the cues that would catch it were deleted.**
The words are there — `compliance` 128×, `standards` 110×, `expert` 34×, `ongoing` 29×,
`consultation` 27×, `stakeholder` 12×. Of the 34 cues cut on 2026-08-26, **12 appear in
this corpus and would have matched 75 times**:

| occurrences | cue | lens |
|---:|---|---|
| 29 | `ongoing` | institutional_permeation |
| 16 | `ties to` | narrative_management |
| 14 | `movement` | institutional_permeation |
| 5 | `national security` | institutional_permeation |
| 4 | `long-term` | institutional_permeation |
| 1 each | `regime`, `narrative`, `so-called`, `on behalf of`, `the courts`, `irreversible`, `overruled` | various |

The cut judged cues aimed at **rulemaking** against a **news** background. `ongoing` was
removed for appearing 34× in 1.8M characters of news; it appears 29× in 153k words of
rulemaking, a substantially higher density in the register it was written for.

**3. The matcher has no word boundaries, and 11.8% of its real fires are mid-word.**
`re.escape` substring matching means `regime` fires inside "regimen" and `diffuse` inside
"diffuser" — both verified directly. Across PTC, **16 of 136 cue fires (11.8%) have an
alphanumeric character abutting the match.** That is a floor on the false-positive rate that
no amount of corpus work will fix.

**4. The verifier has modes now, and v1 never says which question it asks.**
`author` (is the document's author employing the method) versus `instance` (is the span the
technique as it appears, whoever produced it). v1 predates the distinction entirely and
would have silently inherited whichever was the default.

---

## The statistics, corrected

An earlier draft of this revision set a floor of "≥10 hits in the control cell". **That is
wrong and would have killed the study for the wrong reason.** A quiet control class is what
a control class is *for*: if `method` fires 20 times and `control` fires 0, that is the
strongest possible discrimination, not a failure. The rate ratio is undefined, so use a
Poisson exact test on counts with token exposure — 0 versus 20 is decisive.

**The binding unknown is λ_method, and it is the one number nobody has.** Everything
measured so far — PTC news, Federal Register controls — bears on the control side. Whether
the design works turns entirely on whether documents *written by organisations that ran the
method* fire meaningfully more than routine rulemaking does.

So the pilot's job changes. It is no longer a miniature of the confirmatory test. **It is a
rate-estimation exercise whose single deliverable is λ_method**, and the confirmatory corpus
is sized from that rather than from the round number 200.

Two consequences:

- **Statistic:** verified hit counts against token exposure (Poisson), not
  `grade_document_for_lens`'s index. The index's breadth/intensity/density weighting and
  tier cutoffs are calibrated for grading a manuscript; running a two-class contrast through
  a bounded nonlinear score destroys the count arithmetic and makes power uncomputable.
- **Window: 1,500–2,000 words, not 400.** v1's stated reason for 400 was that
  density-per-1k inflates on short snippets — but that is an argument for *equal* lengths,
  and small-denominator noise is *worst* at 400. With exposure in the model the inflation
  worry disappears. Identical procedure across classes, fixed before the labelled fetch.

**Verify mode: `author`, for this test.** A `method` document is written *by* the
organisation running the method, so "is the author employing this?" is exactly what the
class labels encode. `instance` would fire on control documents that quote or summarise
method language — rulemaking citing comment letters — diluting the contrast. Same mode for
both classes or mode becomes a confound. Report `instance` alongside: verdicts are cached
per mode so it is nearly free, and the author-vs-instance delta is itself diagnostic.
Report cues-only counts as a separate line always, so a verifier failure cannot be mistaken
for a corpus finding.

---

## Sequence

**Stage 0 — fix the matcher. Before any labelled fetch.**
Word-boundary matching by default, per-cue opt-out for affixes that should match inside a
word. It touches the JS/Python parity gate, so it ships as its own change with the gate
green. Doing it after the corpus exists means re-running everything.

**Stage 1 — liveness census on the target register. No labels, no rulings, no model.**
Extend the calibration set beyond rulemaking to the registers the lenses actually target:
foundation reports, standards bodies, party programmes. Report, per lens, how many cues fire
and at what rate. This is cheap and it gates the rest:

> If liveness on the lens's own register stays near the 0.3% measured on rulemaking, the
> vocabulary is **inert rather than off-register**, and taxonomy repair precedes any corpus
> verdict about whether a lens works. That is a real finding, and it costs 25 documents
> rather than 200.

**Stage 2 — replenish the vocabulary from receipts.** The source is
`tradecraft/leaderboard/data/leaderboard.jsonl`: filtering to `assurance: FACT`, lens
`institutional_permeation`, markers `permeation`/`gradualism` yields **exactly 33 records**,
each carrying a verbatim `span` (47–455 chars, median 245) and receipt URLs. Procedure:

- **Enumerate, do not choose.** Script emits every contiguous 2–6-word n-gram from each
  span, excluding ones that start or end on a stopword or consist wholly of the record's
  proper nouns. A human picking *which fragment* to lift is where circularity re-enters —
  someone who knows `far-right` works will lift things shaped like it.
- **Validate by fire-and-verify, not by frequency.** Frequency was discredited today. Free
  offline fire count first; then instance-mode verification on a sample; accept on a
  pre-registered threshold with an **absolute** genuine floor, not a ratio.
- **Never validate a cue against its own source document** — match `receipts` URLs against
  the corpus manifest and exclude.
- Each accepted cue carries a `gold` entry citing its ledger record, so provenance travels
  with the cue.

**This stage is authoring on the flagship lens and is the author's call, not mine to
execute.** I can produce the ranked candidate list with its numbers and receipts.

**Stage 3 — the pilot, re-scoped to estimate λ_method.** Needs the
`METHOD-CLASS-PROPOSAL.md` ruling: naming an organisation as having run a capture method is
a defamation-exposed claim about real bodies and it is the axis the whole test turns on.

**Stage 4 — confirmatory corpus, sized from λ_method.** Not before.

---

## Interpreting a null — three findings, three instruments

Pre-registered, because "the lens does not work" is only one of three:

| observation | verdict |
|---|---|
| cue liveness on the lens's own register ≈ rulemaking's 0.3% | **cues inert** — repair the taxonomy first |
| liveness healthy, total hits below the power floor | **UNDERPOWERED** — report as such, never as a null |
| hits sufficient, rate-ratio CI includes 1 | **the lens does not discriminate** — the real null, and it ships |

Two controls v1 lacks:

- **Positive control.** Run the 91 `fixtures.json` sentences through the identical pipeline.
  If it cannot separate written-to-fire text from `control`, the pipeline is broken and no
  corpus result means anything.
- **Negative-control lens.** Pre-register one lens with no theoretical link to permeation
  and require it *not* to separate the classes. If it does, the classes differ by register
  rather than by method — the confound the whole design exists to exclude.

---

## Also worth fixing, found on the way

- **First-match-then-break makes cue order load-bearing and nothing owns it.**
  `detect_cues` records one hit per detection and stops, so the verifier judges whichever
  cue happens to sit earliest in the list — possibly the weakest instance in the document.
  Order cues by measured precision, generate the order, gate it with `--check`.
- **`sourcing_asymmetry`'s gold entries are marked "(illustrative)"** — imagined, one level
  up from the cues. The leaderboard ledger carries no `sourcing_asymmetry` material, but
  PTC's own human-annotated `loaded_language` / `name_calling` spans are an equally
  non-circular receipt source, on a train/holdout split.
- **Stop reporting "621 cues" as instrument size.** Report live-cue count and verified
  precision. 621 is the number that let this hide.
