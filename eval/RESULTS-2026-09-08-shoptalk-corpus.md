# The shop-talk corpus, measured against the pre-registration -- a bounded null, narrowly

**Pre-registration:** `PREREG-2026-09-08-shoptalk-corpus.md`, committed before any document was
fetched. **Corpus:** `corpus/ai-governance-shoptalk.jsonl`, built by
`corpus/fetch_ai_governance_shoptalk.py`. **Recheck plan:** `CUE-REPAIR-2026-09-08-shoptalk-recheck.json`
(the same 13 candidates, the same rule, as `CUE-REPAIR-2026-09-07.json`). **Measured:**
`CUE-REPAIR-2026-09-08-shoptalk-recheck-measured.json`.

## The one-line result

**The corpus is real, sourced, and it moved the needle -- just not past the pre-registered bar.**
Of the 13 cues the 2026-09-07 repair could not touch for lack of evidence, this corpus supplied
new occurrences for 5 and pushed **2 over the cut threshold** (`diffuse`, `disruptive`) against a
pre-registered bar of "at least 3 flip." That is a **narrow, honest null on P5** -- but the two
cuts that did clear the bar were not free: applying them, together with the corpus's own effect on
the background rate, **demoted `institutional_permeation`'s flagship claim on real people's own
collateral statements from "above background" to "indistinguishable from background"** (occ 17 ->
15, per-1k 0.148 -> 0.131, against a background that itself rose and became visibly overdispersed
once AI-governance prose was in the pool). Collateral precision on the frozen 51-span sample rose
from 25.6%/23.1% (readers A/B, post-2026-09-07) to **29.4%/26.5%** (post-this-repair), losing zero
construct-present spans. The seven cues named as "never occurs anywhere" in the 2026-09-07 finding
-- `training pipeline`, `arithmetic`, `proprietary model`, `high score`, `in a bid to`, plus
`level playing field` and `canvassing` short of the threshold -- **still do not occur** in 137
kwords of real frontier-lab safety blogs, governance think-tank papers, standards text, and AI
oversight hearings. That is now a measured fact about this register, not an absence of evidence.

## The corpus

46 documents, 136,989 words, four source classes, every record carrying a `source_url` and a
fetch date:

| source_class | docs | words | orgs |
|---|---:|---:|---|
| `lab-safety-blog` | 24 | 85,222 | Anthropic, Google DeepMind, Frontier Model Forum, METR, Apollo Research, Redwood Research |
| `congressional-testimony` | 9 | 43,324 | U.S. Congress (govinfo CHRG hearings) |
| `standards-framework` | 7 | 4,685 | NIST, UK AI Safety Institute, UK Government (Bletchley, Seoul), European Commission (Hiroshima Process), Federal Register (EO 14110) |
| `think-tank` | 6 | 3,758 | Centre for the Governance of AI (GovAI) |

Every URL was verified to resolve (HTTP 200, real content) before being written to the fetch
plan, and again at fetch time. **A defect found and fixed during the run:** 6 of 21 govinfo `CREC`
search hits (Congressional Record items, as opposed to `CHRG` hearings) returned govinfo's "Page
Not Found" error shell through the content path that works for `CHRG` -- a real HTTP 200 with real
page content, but not the document. Caught by inspecting the fetched text rather than trusting the
word count (one of the six was a fentanyl-detection bill picked up by a loose full-text match on
"artificial intelligence" somewhere in the record), dropped, and the fetcher now skips this shape
by content rather than guessing a corrected path (`fetch_ai_governance_shoptalk.py`, the
"Search Page Not Found" guard). All 9 `CHRG` hearings and all 37 direct-URL pages verified as real,
substantive text.

Declared in `eval/background_rate.py`'s `ROLES` as `background` / `recomputable: True` -- gathered
by topic (a named institution's AI-safety/governance publication, or a govinfo search term scoped
to AI oversight), never by cue, matching the discipline the file's own docstring requires.

## The 13 candidates, rechecked with the identical rule

`CUE-REPAIR-2026-09-08-shoptalk-recheck.json` carries the same `ptc_bg_min: 3`,
`bg_min_occurrences: 3`, `exclude_min_read: 3` as the 2026-09-07 plan. Nothing about the rule
changed; only the general-prose pool grew (171 -> 217 docs, 885.3 -> 1,022.3 kwords).

| cue | detection | occurrences in THIS corpus alone | pooled background (all buckets) | verdict |
|---|---|---:|---:|---|
| `diffuse` | institutional_permeation/hidden-or-deferred-cost | **4** | 4 | **CUT** |
| `disruptive` | reference_capture/elastic-charge | **5** | 6 | **CUT** |
| `a few hundred` | reference_capture/anonymous-authority | 2 | 2 | KEEP (< 3) |
| `grassroots` | institutional_permeation/astroturf | 1 | 1 | KEEP (protected: own PTC lift clears 1) |
| `human capital` | subculture_register/managerial-tells | 1 | 1 | KEEP (protected: reader B found the construct present) |
| `level playing field` | institutional_permeation/carve-out-as-public-good | 0 | 2 | KEEP (< 3) |
| `training pipeline` | institutional_permeation/build-parallel-institutions | 0 | 0 | KEEP (still zero everywhere) |
| `arithmetic` | institutional_permeation/value-as-science | 0 | 0 | KEEP (still zero everywhere) |
| `proprietary model` | institutional_permeation/attribution-gap | 0 | 0 | KEEP (still zero everywhere) |
| `high score` | militant_mobilization/sainthood-and-heroes | 0 | 0 | KEEP (still zero everywhere) |
| `in a bid to` | sourcing_asymmetry/mind-reading | 0 | 0 | KEEP (still zero everywhere) |
| `from within` | institutional_permeation/infiltrate-existing-institutions | 0 | 4 (pre-existing) | KEEP (protected: demotes a demonstrated detection + breaks a fixture + own lift) |
| `canvassing` | reference_capture/canvassing-mobilization | 0 | 2 (pre-existing) | KEEP (< 3; unchanged by this corpus) |

**Five of seven "zero-everywhere" cues from 2026-09-07 are STILL zero-everywhere** even in 137
kwords of the exact register they were suspected to be ordinary vocabulary in:
`training pipeline`, `arithmetic`, `proprietary model`, `high score`, `in a bid to`. That is a
substantive negative finding in its own right -- these phrases are not, in fact, common trade
vocabulary in frontier-lab safety writing, think-tank papers, or AI-oversight hearings at this
sample size. Whatever register produces them (if any) is not the one this corpus sampled.

## Predictions, scored

| # | prediction | result | holds? |
|---|---|---|---|
| P1 | >= 8 of 13 show >= 1 occurrence in the new corpus alone | **5 of 13** (`diffuse`, `grassroots`, `disruptive`, `a few hundred`, `human capital`) | **wrong** |
| P2 | >= 3 of 13 clear `bg_min_occurrences >= 3` from this corpus alone | **2** (`diffuse` 4, `disruptive` 5) | **wrong, narrowly** |
| P3 | `human capital` stays KEPT regardless (reader-CP guard) | kept, guard fired exactly as predicted | **holds** |
| P4 | `from within` stays KEPT regardless (detection-demotion guard) | kept, guard fired exactly as predicted (also broke a fixture, also had its own lift) | **holds** |
| P5 | >= 3 of 13 flip from KEEP to CUT/REPLACE | **2** (`diffuse`, `disruptive`) | **wrong, narrowly** |
| P6 | `institutional_permeation`'s general-prose per-1k rate rises | 0.0508 -> 0.0773 (pre-cut) -> **0.0734** (post-cut), still above the 2026-09-07 baseline | **holds** |
| P7 | applying whatever the rule selects drops no CP collateral span, demotes no PTC-demonstrated detection | verified on the frozen 51-span sample: the 5 newly-dropped spans (n=9,10,12,15,16) are **CO by both readers on every one**; `detection_census.py`'s 3 demonstrated detections **unchanged** | **holds** |
| P8 | collateral precision rises measurably (a few points, not a step change) if anything is cut | Reader A 25.6% -> **29.4%**, Reader B 23.1% -> **26.5%**, both 20.5% -> **23.5%** (39 -> 34 surviving spans) | **holds** |

**The decision rule from the pre-registration:** "the corpus lets the detector distinguish
shop-talk from tradecraft" required P5 (>= 3 flips) **and** P7. P7 holds; P5 does not (2, one short
of the pre-registered bar). **By my own stated rule, this is the null side of the line** -- stated
plainly rather than rounded up because two is close to three.

## What moved anyway, on real material

The abstract cue-count bar is a proxy. The thing that actually matters -- whether a flagship
"above background" claim on real people's real words survives contact with a register-matched
control -- did move, and it moved on the lens the whole exercise was about:

| | before (2026-09-07 state) | after (this corpus + repair) |
|---|---|---|
| `institutional_permeation` on collateral (person statements, `collateral_eval.py`) | occ 17, 0.148/1k, **above background** | occ 15, 0.131/1k, **indistinguishable from background** |
| its background (`occurrence_rate.py`) | 0.0508/1k [0.0371, 0.0680], not overdispersed | 0.0734/1k [0.0577, 0.0920], **overdispersed (VMR 2.40)**, quasi-upper 0.1022 |
| `reference_capture` on collateral | occ 7, 0.061/1k, indistinguishable | occ 4, 0.035/1k, indistinguishable (unchanged verdict, tighter reading) |
| `institutional_permeation` on THE RECORD's board institutions' own output (`collateral_pass2.py`, unrelated 34-document store) | occ 34, above background | occ 34, above background -- **unchanged** (`diffuse` never occurred in that store) |
| `reference_capture` on the same pass-2 store | occ 18, above background | occ 13, above background -- **unchanged verdict, on a higher bar** (background per-1k rose 0.023 -> 0.031 too) |

The `institutional_permeation` flip is not attributable to the cue cut alone. Two things moved
together: cutting `diffuse` removed 2 of the collateral's 17 occurrences directly, and the corpus
addition made the lens **visibly overdispersed for the first time** (VMR crossed 1.5), which
widens the background interval `collateral_eval.py`'s own ruler discipline requires it to quote.
Both effects point the same direction -- toward a more honest, harder-to-clear background -- and
neither loosens anything: the background got WIDER, not narrower, which is the conservative
direction to move in.

## What did not move

- The census's 3 demonstrated detections (`infiltrate-existing-institutions`,
  `penalty-without-adjudication`, `maganr-tells`) are byte-for-byte unchanged.
- `run_eval.py cues --strict`: 55/55 positive, 34/34 negative, 55/55 marker coverage, 1/1
  cross-camp -- identical to 2026-09-07.
- `tools/test_engine_parity.py`: OK, both engines, identical.
- THE RECORD's board institutions' own-output pass (`collateral_pass2.py`) changed only in
  `reference_capture`'s raw count (18 -> 13, both cuts hit real occurrences there too) and neither
  verdict flipped.
- `canvassing`, `level playing field`, `a few hundred`, `grassroots`, `human capital`, `from
  within` -- all KEPT, all for the same reasons as 2026-09-07, none touched by this corpus's
  content in a way that changed the outcome.

## A side effect found, diagnosed, and NOT silently fixed

Adding the corpus pushed `eval/occurrence_rate.py --check` from passing to **FAILING** on its
length-homogeneity acceptance test, for two different and separable reasons:

1. **`reference_capture`** (VMR 4.10, overdispersed): band Q3's exact-Poisson interval
   `[0.0381, 0.1015]` excludes the pooled rate `0.0313`. But the OVERALL homogeneity test on this
   lens says **p = 0.161 -- not significant** (homogeneous). The band-exclusion sub-check compares
   a band's narrow EXACT interval against the pooled rate even when the lens is known to be
   overdispersed; the file's own documented rule for the POOLED interval is to quote the WIDER
   quasi-Poisson bound in that case (`ci95_quasi`), and the per-band exclusion check does not do
   the same widening. Hand-checked: widening Q3's interval by the same VMR-derived factor the file
   already applies to the pooled interval removes the exclusion entirely. This reads as a
   **pre-existing gap in the band-exclusion check**, exposed for the first time because no lens
   was both overdispersed AND had a band-exclusion hit before this corpus existed.
2. **`sourcing_asymmetry`** (VMR 0.36, not overdispersed): band Q3 excludes the pooled rate too,
   but this lens's own tool output **already attributes it to composition, not length**
   (`bucket_p = 0.0005`; it fires at 0.093/1k in news, 0.048/1k in advocacy hearings, and now
   0.044/1k in this corpus -- three different genres at three different rates, exactly the
   "quote per bucket" finding the 2026-09-07 RESULTS already made about this lens). The
   homogeneity check has a composition escape valve (`bucket_explains()`); the band-exclusion
   check does not.

**I did not touch `occurrence_rate.py` to make either of these pass.** Fixing #1 would be
mechanical and consistent with the file's own already-stated overdispersion philosophy; fixing #2
would mean deciding that the band-exclusion check should carry the same composition escape valve
the homogeneity check has, which changes what the gate considers a pass and is a design call, not
a bug fix. The hard rule for this task is fix artifacts, never loosen gates -- so `--check` is left
**failing, honestly, on disk**, with this diagnosis attached. See the "left for Ian" list.

## What must not happen, and didn't

No cue was cut that the rule kept. No cue was added because the corpus happened to contain it. No
document was selected because it contained a candidate phrase -- every URL was chosen by topic
before any occurrence was counted (see the pre-registration). No book manuscript was used as
corpus or source. Every fetched URL resolved to real, attributed content; the 6 that didn't
(the CREC 404 shells) were caught and dropped, not silently kept or guessed-around. Internet
discipline: serial requests only, 1.5s between direct-URL fetches, 3.0s between govinfo calls, one
host at a time, a descriptive User-Agent naming this research and a contact URL, a local
on-disk cache so a re-run never re-fetches, and the run stopped cleanly on the one HTTP error
encountered (a 429 during the earlier, unrelated pass-2 own-output fetch, not this corpus).

## Gates, before handing this off

- `run_eval.py cues --strict`: PASS (55/55, 34/34, 55/55, 1/1)
- `tools/test_engine_parity.py`: PASS
- `pytest` (tradecraft): **496 passed**
- `tools/freshness_gate.py` (repo root): **0 FAIL**, 2 pre-existing WARN (bibliography coverage,
  unrelated authoring backlog)
- `tools/endpoint_audit.py`: **0 findings** across 741 pages
- `eval/background_rate.py --check`: PASS
- `eval/collateral_eval.py --check`: PASS
- `eval/occurrence_rate.py --check`: **FAIL** -- diagnosed above, left failing, not loosened
- Regenerated as a consequence of the taxonomy edit: `instrument.json` (`export_web.py`),
  THE RECORD store (`build_record.py`), `rosetta.json` (`gen-rosetta.py`), the tradecraft demo
  split (`web/build-demo.py`), `collateral-eval.json`, `collateral-pass2.json`. All verified fresh.
- A defect found and fixed along the way, unrelated to the corpus content: a `git stash`/`pop`
  used to compare against the pre-corpus baseline round-tripped `detectors/institutional_permeation/taxonomy.yaml`
  and `detectors/reference_capture/taxonomy.yaml` through `core.autocrlf`, flipping them from the
  repo's committed LF to local CRLF and changing every downstream export's taxonomy hash without
  changing a single line of content. Caught by a hash mismatch between two consecutive runs of the
  same tool, fixed with `dos2unix`, and every downstream artifact regenerated a second time against
  the corrected files. Named here because a byte-identical-content, hash-different file is exactly
  the kind of drift this project's own gates exist to catch, and it very nearly shipped.
- `git commit`: the source repository only, under the identity that owns it, explicit paths (no `gh`, no push to
  `github.com/gorrie`, per the hard rules for this task). The still-running Phase-1.2 measurement's
  own output (`eval/llm-find-stage.json`, `eval/cache/`) was left untouched and excluded from the
  commit; the concurrent `research/bias-study/` tree was not touched.

## Left for Ian

1. **`occurrence_rate.py`'s band-exclusion check does not account for overdispersion or
   composition the way its own homogeneity check does.** Two live lenses now fail it for two
   different, already-diagnosed reasons. Either fix #1 (widen the per-band comparison by the same
   VMR factor the pooled interval already uses when overdispersed -- mechanical, consistent with
   the file's stated design) and separately decide whether #2 (`sourcing_asymmetry`'s genre
   composition) should also get an escape valve, or leave `--check` red with this file as the
   standing explanation.
2. **A second, larger corpus pass is available if the seven still-zero cues matter enough to
   settle.** `training pipeline`, `arithmetic`, `proprietary model`, `high score`, and `in a bid
   to` are now measured absent from 137 kwords of exactly the register they were suspected of
   living in. A future pass could widen the source classes (more labs: OpenAI blocks bots at the
   HTTP layer and would need a different fetch approach; RAND, CSET, and OECD returned 403/404 on
   the URLs tried and were not pursued further under this task's bounded-first-pass scope) or
   accept that these five are not, in fact, common AI-governance vocabulary and consider them
   candidates for a defective-cue review on different grounds than register-ubiquity.
3. **`level playing field` and `canvassing`** sit at 2 of the 3 needed; one more real document
   containing either, from any register, would resolve them either way.
