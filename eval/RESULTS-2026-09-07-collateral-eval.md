# The working detectors on the record's collateral — first evaluation, against the pre-registration

**Pre-registration:** `PREREG-2026-09-07-collateral-eval.md`, committed at `7b8cdaa6` before the run.
**Rig:** `eval/collateral_eval.py` (deterministic; `--check` exits 0 against the committed
`collateral-eval.json`). **Collateral:** `research/ratchet-mcp/server/data/texts.jsonl` — 328 verbatim
public statements by 20 dataset persons, 114,615 words, median 39 words, 2017-11-26 to 2026-06-29,
sha256 `685322306849adc5`. **Taxonomy:** `7a9fe27e075fb5fb`, unchanged. Not the author's books, not PTC.
**Hand-read:** `collateral-eval-hand-read.json`, 51 spans, four pre-registered classes.

Run time 11 s. Nothing was tuned between the pre-registration and this file.

## What ran, what did not

| detector | status |
|---|---|
| tradecraft `cues` backend, 14 text lenses | **ran** |
| capture scanner — the shipped `scanner.js` + `capture-cats.js`, through node | **ran** |
| `/tech/instrument/` engine.js | same taxonomy and grader, parity-gated — the cues run is its result, not a second measurement |
| tradecraft LLM find / verify stage (local 14B) | **not run** — GPU held by the detached Phase-1.2 measurement; 37% span fabrication (`RESULTS-2026-09-07-llm-find-stage.md`) unresolved |
| bias study | not applicable — measures models, reads no third-party text |
| `ratchet_series.py` | not applicable — reads a series of administrative actions |

## The one-line result

**56 cue occurrences in 114,615 words.** Two lenses sit above their general-prose background on the
length-invariant unit; twelve are indistinguishable from it, six of those at zero. The hand-read puts
the construct behind **10 of 51** fired spans (20%). The one index-bearing lens that is "above
background" (`institutional_permeation`) is above it because AI-safety people say *existential risk*:
2 of its 23 sampled hits carry the construct. The only board institution with collateral (SIO, 38 texts
by DiResta and Stamos) fired nothing. The detectors did not do well on this material, and the
pre-registration's "doing badly" bar was crossed on the hand-read.

## Lens table

Two units, both rulers, interval verdicts only. *bg* = the general-prose background pool (171
documents / 885.3 kwords). *detectable at* = the smallest multiple of the background rate this
corpus's exposure could have shown as "above background".

| lens | state | docs fired | docs rate [W95] | bg docs | occ | per 1k [P95] | bg per 1k [95] | verdict | top detection (share) | one cue | detectable at |
|---|---|---:|---|---:|---:|---|---|---|---|---|---|
| `adept_speech` | receipts-only | 2 | .006 [.002, .022] | .012 | 2 | .017 [.002, .063] | .002 [.000, .008] | indistinguishable | candidate-sorting (1.0) | no | 15.2× |
| `cognitive_capture` | receipts-only | 0 | 0 [0, .012] | .006 | 0 | 0 [0, .032] | .003 [.001, .010] | indistinguishable | — | no | 12.8× |
| `costly_signal` | receipts-only | 0 | 0 [0, .012] | 0 | 0 | 0 [0, .032] | 0 [0, .004] | indistinguishable | — | no | undefined (bg = 0) |
| `counterproductivity` | receipts-only | 0 | 0 [0, .012] | 0 | 0 | 0 [0, .032] | 0 [0, .004] | indistinguishable | — | no | undefined (bg = 0) |
| `distributed_accountability` | receipts-only | 0 | 0 [0, .012] | .023 | 0 | 0 [0, .032] | .005 [.001, .012] | indistinguishable | — | no | 9.7× |
| `inevitability_framing` | receipts-only | 2 | .006 [.002, .022] | .018 | 2 | .017 [.002, .063] | .006 [.002, .014] | indistinguishable | no-alternative (1.0) | no | 7.8× |
| **`institutional_permeation`** | index | 20 | .061 [.040, .092] | .129 | 25 | **.218 [.141, .322]** | .051 [.037, .069] | **above background** | define-crisis-claim-authority (.48) | no | 2.6× |
| `legibility` | index | 0 | 0 [0, .012] | .047 | 0 | 0 [0, .032] | .014 [.007, .024] | indistinguishable | — | no | 4.5× |
| `militant_mobilization` | receipts-only | 3 | .009 [.003, .027] | .023 | 3 | .026 [.005, .077] | .005 [.001, .012] | indistinguishable | sainthood-and-heroes (.67) | no | 9.7× |
| `narrative_management` | receipts-only | 0 | 0 [0, .012] | .018 | 0 | 0 [0, .032] | .003 [.001, .010] | indistinguishable | — | no | 12.8× |
| `reference_capture` | index | 5 | .015 [.007, .035] | .105 | 7 | .061 [.025, .126] | .023 [.014, .035] | indistinguishable | elastic-charge (.43) | no | 3.5× |
| `rollback_asymmetry` | receipts-only | 1 | .003 [.001, .017] | .018 | 1 | .009 [.000, .049] | .003 [.001, .010] | indistinguishable | new-normal-floor (1.0) | no | 12.8× |
| `sourcing_asymmetry` | index | 3 | .009 [.003, .027] | .187 | 3 | .026 [.005, .077] | .060 [.045, .078] | indistinguishable | mind-reading (1.0) | no | 2.3× |
| **`subculture_register`** | index | 7 | .021 [.010, .043] | .064 | 13 | **.113 [.060, .194]** | .019 [.011, .031] | **above background** | rationalist-tells (.85) | **YES** | 4.1× |

**Documents-fired is below background on 12 of 14 lenses; per-1k is indistinguishable or above on all
12.** That is the extensive margin on 39-word texts (issue #7) showing up on real collateral exactly
as predicted: the documents unit says "these people use the moves less than newspapers do", the rate
unit says "no, the texts are short". Only the rate unit is read.

## The hand-read — 51 spans, 20% construct present

40 spans sampled with seed 20260907 from the 45 hits of lenses with more than three hits; all 11 hits
of the six rarer lenses read in full. Verdicts and one-line reasons for every span:
`collateral-eval-hand-read.json`; contexts: `collateral-eval.json` `precision_sample.rows`.

| | construct present | cue-only | quoted / attributed | unreadable | precision |
|---|---:|---:|---:|---:|---:|
| sampled 40 | 8 | 25 | 7 | 0 | **20%** |
| rare-lens 11 | 2 | 8 | 1 | 0 | 18% |
| **all 51** | **10** | **33** | **8** | **0** | **20%** |

By lens (all 51):

| lens | read | CP | CO | QA | what fired |
|---|---:|---:|---:|---:|---|
| `institutional_permeation` | 23 | **2** | 19 | 2 | *existential* 12× (a field's name for a research area, a chatbot's "existential crisis", a book title); *training pipeline* (ML jargon); *diffuse* (the verb); *from within* (a fiction dateline); *arithmetic*; *grassroots*; *proprietary models*; *level playing field*. The two CP: Bengio's case for a multilateral network of labs; a post licensing its own RSI programme by "existential importance". |
| `subculture_register` | 10 | **6** | 1 | 3 | *the alignment problem*, *coordination problem*, *instrumental convergence* used natively by alignment researchers — the lens measures what it says. The 3 QA are a cited paper title (*Clarifying AI X-risk*, twice) and *e/acc* named as an opponent's word. |
| `reference_capture` | 7 | **0** | 5 | 2 | *disruptive* ×3 (an adjective); *a few hundred* ×2 (a count); *canvassing* ×2 (a study's fundraising firm). |
| `sourcing_asymmetry` | 3 | 0 | 3 | 0 | *in an attempt to* / *in a bid to* — the speaker's own motive once, a fiction narrator twice. Mind-reading needs a real third party. |
| `militant_mobilization` | 3 | 0 | 2 | 1 | *high score* ×2 (benchmarks); *exterminate* in a quoted passage. |
| `adept_speech` | 2 | 0 | 2 | 0 | the cue **`you haven`** firing inside *you haven't* — twice. A substring, not initiatory address. |
| `inevitability_framing` | 2 | **1** | 1 | 0 | Summers 1998, *it is inevitable that if barriers continue to fall* — the construct. Clark announcing a lecture titled "Change is inevitable. Autonomy is not" — a title, not a move. |
| `rollback_asymmetry` | 1 | **1** | 0 | 0 | Clark: *I expect this is the new normal* — a change framed as a permanent floor. |

### Second reader, blind (added 2026-09-07, same day)

The same 51 spans were read a second time by a separate agent on a different model (Reader B:
Claude Opus 5, `collateral-eval-hand-read-B.json`), given only the contexts, the detection
definitions and the pre-registered codebook — not Reader A's verdicts, not this file. Reader A is
the agent that ran the rig (Claude Fable 5.1).

| | CP | CO | QA | UR | precision |
|---|---:|---:|---:|---:|---:|
| Reader A | 10 | 33 | 8 | 0 | 19.6% |
| Reader B | 9 | 34 | 8 | 0 | 17.6% |
| CP by **both** | 8 | | | | 15.7% |

Agreement **44 of 51 (86%)**, Cohen's κ = **0.73** on the four classes, **0.81** on the binary
construct-present / not. The seven disagreements: #23 (`human capital` — B reads the managerial
register as present, A as textbook economics), #24 and #40 (the two `existential` spans A called
CP — B holds `define-crisis-claim-authority` to a stricter bar: stakes named, but no exclusive
authority claimed), #26/#27 (B: cue-only rather than quoted — the fundraising firm is the study's
subject, not a quotation), #29 and #39 (B: quoted/title rather than cue-only). None of the seven
moves a lens's verdict; the eight both-CP spans are the six `subculture_register` register uses,
Summers's `is inevitable` and Clark's `the new normal`. **The 20% holds: 18–20% by either reader,
16% by both.**

**Reading of the reading.** The register lens works on this material because the material *is*
the register (60% CP, and the quoted cases are the ones a human would also set aside). Every other
text lens is mostly firing on words that mean something else in the speaker's trade. That was the
PTC finding too (`RESULTS-2026-08-26-ptc-precision.md`, precision 0.16–0.29 against annotation); on
the record's own collateral it is worse, because the collateral is denser in the exact vocabulary the
cues borrowed from it.

## Predictions, scored

| # | prediction | result | holds? |
|---|---|---|---|
| P1 | `sourcing_asymmetry` fires on the most documents | `institutional_permeation` 20 docs; `sourcing_asymmetry` **3** | **wrong** |
| P2 | `institutional_permeation` above background on per-1k | .218 [.141, .322] vs .051 [.037, .069] | holds — **for the wrong reason**: 2 of 23 read spans carry the construct; the elevation is *existential (risk)* |
| P3 | `inevitability_framing` ≤ 2 occurrences | 2 | holds |
| P4 | ≥ 6 lenses at zero, each with a detectable multiple ≥ 2× | 6 zeros; multiples 4.5×–12.8×; two undefined because the background is itself zero (`costly_signal`, `counterproductivity`) | holds, with the undefined pair noted |
| P5 | docs-fired below background on ≥ 8 lenses while per-1k is indistinguishable-or-above on at least half of them | 12 below (9 by interval); per-1k indistinguishable-or-above on all 12 | holds |
| P6 | at least one one-cue lens | `subculture_register` — rationalist-tells carries 85% (four distinct cues inside that detection) | holds |
| P7 | hand-read precision between 40% and 60% | **20%** | **wrong — below the "doing badly" bar** |
| P8 | cue arm fires the same lens on the same text for ≤ 25% of the 24 receipts | 3 of 24 (12.5%); a cue lands inside the receipt's span **0** of 24 | holds |
| P9 | ≥ 90% Low band; DiResta and Stamos top two on asserted-per-1k | 318/328 Low (97%) — holds. DiResta and Stamos: **0 loaded terms in 1,683 words**; the top two are Bengio (4.6/1k) and Hendrycks (1.2/1k) | **half wrong** |
| P10 | exactly 1 of 36 board institutions has collateral | 1 (SIO) | holds |

Seven hold, two wrong, one half. P2 holding is the least informative row in the table: the number
came out where predicted and the read says the number is not measuring the construct.

### After the cue repair (added 2026-09-07, same day)

The pre-registered repair (`PREREG-2026-09-07-cue-repair.md`, results in
`RESULTS-2026-09-07-cue-repair.md`) cut three cues, added one exclusion and closed the contraction
hole. Re-run on the **same frozen 51 spans**: 12 no longer fire — 11 cue-only and 1 quoted by both
readers, **no construct-present span lost**. Survivors 39; precision **25.6%** (A) / **23.1%** (B) /
20.5% by both. `institutional_permeation` is still above background (17 occurrences, 0.148 per 1k
against 0.047), because the rule kept the cues the calibration corpora never see. The 20% became
25%; it did not become good.

## Failure modes, named

1. **Trade vocabulary reads as tradecraft.** `existential` is 12 of `institutional_permeation`'s 25
   occurrences and 0 of its 12 read instances is the move. `training pipeline`, `diffuse`,
   `disruptive`, `high score`, `a few hundred`, `human capital`: each is a cue written for one
   register firing in another. This is the `RESULTS-2026-09-03-cue-enumeration-ceiling.md` problem
   from the other side — the cues that *do* appear in real prose mostly appear meaning something else.
2. **`you haven`** fires inside *you haven't*, twice, and is the whole of `adept_speech`'s showing.
   A cue that is a prefix of a contraction is a defect in the cue, not in the corpus.
3. **Quotation blindness.** 8 of 51 spans are the speaker quoting, citing or naming someone else's
   words. The cue matcher has no attribution read; the scanner's 110-character ATTRIB window is the
   only automated defense in either detector and it is not in this lane.
4. **Fiction.** Three `sourcing_asymmetry` and two `institutional_permeation` hits are inside Jack
   Clark's short fiction (Import AI's closing stories). A narrator on a character is not mind-reading a
   real actor. The store does not mark fiction; the lane cannot know.
5. **The scanner explodes on short texts.** All six "High" texts are 15–76 words: one *harmful* in
   24 words scores 100/100; four italicised nouns in a 38-word tweet score 100/100; and
   **`@A_v_i__S` scores 89/100 because the underscores in a Twitter handle parse as `_v_` markdown
   emphasis.** The degree formula divides by words/100 with no floor; below ~100 words it is noise.
6. **Selection, not sampling.** `texts.jsonl` is hand-assembled for the receipts lane. Rates describe
   the store, not the person. 48,760 of the 114,615 words are one person's newsletters.
7. **The model arm and the cue arm do not see the same things.** 0 of 24 model-read receipts has a cue
   inside its span; the three "same lens, same text" matches are different sentences in the same
   long newsletter. The receipts are on `distributed_accountability`, `counterproductivity`,
   `cognitive_capture`, `legibility`, `inevitability_framing`, `adept_speech`,
   `institutional_permeation` — five of those are model-only or fired zero cues here.

## Board institutions

- **Stanford Internet Observatory** (`SIO`): 38 texts / 1,683 words by Renee DiResta (26) and Alex
  Stamos (12). **Nothing fired** on any lens; the scanner found **zero loaded terms**. At this
  exposure the tradecraft lenses could only have shown a rate ≥ 2.6×–15× background, so this is
  *no evidence, and no power* — and the texts are short posts, not the SIO's reports.
- **35 of 36** board institutions: **no collateral on hand.** The board prints that per row.

## What this changes, and what it does not

- **Nothing in `floors.json`, `floors_contract.py`, the taxonomy or any threshold changes.** A cue
  repair (`you haven`; the trade-vocabulary cues above) is a reviewed, pre-registered edit against
  the PTC and background pools, in the pattern of `PREREG-2026-08-26-label-cue-restore.md` — not a
  reaction to one collateral read. Listed here as the next defect, not fixed here.
- **The result is surfaced, not smoothed.** THE RECORD gets a `collateral` block: `#/collateral`
  prints this table with its rulers and the hand-read tallies; the board row for SIO prints its null
  and the other 35 print "no collateral on hand"; each person-with-texts dossier prints the lenses that
  fired on their words beside the background, with the precision the read found for that lens. Every
  reading is *what the text exhibits*, attributed to the text with its URL.
- **The scanner's short-text behaviour** is reported on the collateral page; the page itself is
  unchanged (its `measure()` export is a refactor with identical output). A words floor is a design
  change for the author.

## Alternatives flagged, not taken

The 150 ledger records' receipt URLs (institutional documents; fetchable serially through `corpus/`;
each needs an own-output-vs-third-party ruling) and fresh collection of each board institution's own
statements/filings would both give the *institutions* collateral. Either is a second pre-registration.

## Reproduce

```bash
python tradecraft/eval/collateral_eval.py --check      # exit 0: the committed JSON is a fresh run
python tradecraft/eval/collateral_eval.py --markdown   # the tables above, recomputed
python tools/build_record.py --check                   # the store's collateral block matches
```
