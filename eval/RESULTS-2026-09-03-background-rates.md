# RESULTS 2026-09-03 — background firing rates, and why twelve lenses are silent

Harness: `eval/background_rate.py` (new). Regenerate everything below with

    python eval/background_rate.py              # rates + eval/background-rates.json
    python eval/background_rate.py --crosstab   # the lens x bucket table
    python eval/background_rate.py --markdown   # the rate table

Deterministic cues backend, no API key, 331 corpus documents of ≥60 words. This file records
measurements, not intentions; every number in it is emitted by that script.

---

## 1. What was built, and the bind it dissolves

`eval/lens_floor.py` can only measure a lens that fires: it needs `MIN_LIVE_DOCS = 8` live
documents before a floor means anything, and twelve of sixteen lenses cannot meet that on any
corpus held. The standing read of that was a corpus problem — get more prose, or widen the
cues. Both were tested in the preceding days and both failed (congressional hearings, then
rulemaking comments; then a concept-absence probe showing the phrases are absent rather than
blocked).

An index is simply the wrong statistic for a rare phenomenon, and there is a second resolution
object that needs no positives at all:

> A rare lens's resolvable claim is not an index GAP between subjects. It is a subject's firing
> RATE against a measured background rate. The general corpus measures that background
> *precisely because* the phenomenon is absent from it. Zero firings in 171 documents is not a
> failure to detect. It is the ruler.

**This is the headline, and it is better news than the plan it came from assumed.** A lens with
a `0/171` background has a 95% Wilson upper bound of 0.022, and at that background a subject
corpus of 100 documents can resolve any true firing rate at or above **0.082**. The silent
lenses do not need a licensed corpus to become honest instruments. They need the statistic that
matches their rarity, and they can have it today.

## 2. Background rates

`fires` = lens index > 0, the same definition `lens_floor.py` uses to call a document live.
`95% up` is the Wilson upper bound — a subject must clear the bound, not the point estimate.
`MDR` is the smallest true firing rate a subject corpus of that size can distinguish from the
background, exact binomial, one-sided, alpha 0.05, power 0.80.

**This table is generated.** It was hand-typed until 2026-09-05, and by then it was wrong in
two independent ways at once: it carried the pre-refetch rates, and it called `legibility`
receipts-only long after it had become index-bearing. Regenerate with
`python eval/background_rate.py --sync-doc`; `--check` fails when it is stale.

<!-- GENERATED:background-rate-table -- edit background_rate.py, not this -->
| lens | state | background fired | rate | 95% upper | MDR n=50 | MDR n=100 | occ/1k words | length-invariant? |
|---|---|---:|---:|---:|---:|---:|---:|---|
| `adept_speech` | receipts-only | 1/217 | 0.005 | 0.026 | 0.14 | 0.09 | 0.0010 | no evidence, and **no power** (<50x undetectable) |
| `cognitive_capture` | receipts-only | 1/217 | 0.005 | 0.026 | 0.15 | 0.12 | 0.0029 | no evidence, and **no power** (<50x undetectable) |
| `costly_signal` | receipts-only | 0/217 | 0.000 | 0.017 | 0.14 | 0.09 | 0.0000 | no occurrences |
| `counterproductivity` | receipts-only | 0/217 | 0.000 | 0.017 | 0.14 | 0.09 | 0.0000 | no occurrences |
| `distributed_accountability` | index-bearing | 5/217 | 0.023 | 0.053 | 0.20 | 0.15 | 0.0049 | no evidence, and **no power** (<50x undetectable) |
| `inevitability_framing` | receipts-only | 4/217 | 0.018 | 0.046 | 0.20 | 0.15 | 0.0059 | yes (could detect 26.3x) |
| `institutional_permeation` | index-bearing | 35/217 | 0.161 | 0.216 | 0.49 | 0.44 | 0.0734 | yes (could detect 2.0x) |
| `legibility` | index-bearing | 13/217 | 0.060 | 0.100 | 0.31 | 0.26 | 0.0186 | yes (could detect 5.0x) |
| `militant_mobilization` | receipts-only | 4/217 | 0.018 | 0.046 | 0.20 | 0.15 | 0.0039 | no evidence, and **no power** (<50x undetectable) |
| `narrative_management` | receipts-only | 3/217 | 0.014 | 0.040 | 0.14 | 0.09 | 0.0029 | no evidence, and **no power** (<50x undetectable) |
| `network_brokerage` | receipts-only | 0/217 | 0.000 | 0.017 | 0.14 | 0.09 | 0.0000 | no occurrences |
| `reference_capture` | index-bearing | 20/217 | 0.092 | 0.138 | 0.33 | 0.27 | 0.0313 | yes (could detect 3.4x) |
| `revolving_door` | receipts-only | 0/217 | 0.000 | 0.017 | 0.14 | 0.09 | 0.0000 | no occurrences |
| `rollback_asymmetry` | index-bearing | 3/217 | 0.014 | 0.040 | 0.15 | 0.12 | 0.0029 | no evidence, and **no power** (<50x undetectable) |
| `sourcing_asymmetry` | index-bearing | 35/217 | 0.161 | 0.216 | 0.33 | 0.27 | 0.0528 | **no -- 3 of 5 buckets, quote per bucket** |
| `subculture_register` | index-bearing | 15/217 | 0.069 | 0.111 | 0.28 | 0.23 | 0.0235 | yes (could detect 3.9x) |
<!-- /GENERATED:background-rate-table -->

### The numbers moved on 2026-09-05, and every one of them moved up

The corpus these rates are measured over was **3% of itself**: `method-specimens.jsonl` was cut
at 6,000 characters and `advocacy-specimens.jsonl` at 30,000, by their fetchers' defaults, and
every fetcher stored HTML markup as words. Both are repaired — refetched by id at full length,
markup normalised. See `RESULTS-2026-09-05-corpus-repair.md`.

Nine of sixteen background rates rose; none fell. Cues in the discarded 97% of each document
could not fire, so the old background was measured against a fraction of the prose.

| lens | before | after | 95% upper | MDR n=100 |
|---|---:|---:|---|---|
| `reference_capture` | 10/171 | **18/171** | 0.104 → 0.160 | 0.199 → 0.265 |
| `institutional_permeation` | 15/171 | **22/171** | 0.140 → 0.187 | 0.245 → 0.297 |
| `subculture_register` | 8/171 | **11/171** | 0.090 → 0.112 | 0.180 → 0.212 |
| `sourcing_asymmetry` | 29/171 | **32/171** | 0.233 → 0.252 | 0.348 → 0.367 |
| `legibility` | 6/171 | **8/171** | 0.074 → 0.090 | 0.159 → 0.180 |
| `distributed_accountability` | 2/171 | **4/171** | 0.042 → 0.059 | 0.117 → 0.139 |
| `inevitability_framing` | 1/171 | **3/171** | 0.032 → 0.050 | 0.092 → 0.125 |
| `militant_mobilization` | 3/171 | **4/171** | 0.050 → 0.059 | 0.125 → 0.139 |
| `rollback_asymmetry` | 2/171 | **3/171** | 0.042 → 0.050 | 0.117 → 0.125 |

Every one of these makes a detection claim **harder**, not easier: the null a subject has to
clear is higher and the minimum detectable rate is larger. That is the direction a correction
should move when the defect was under-measurement, and it is the direction this project will
not accept a correction moving in by accident — see `feedback_never_loosen_the_detector`. The
seven unchanged lenses fire on nothing in the background either way.

`eligible state` is what the *measurement* permits — "index-bearing" means only that
`lens-floors.json` holds an index floor for that lens. The actual per-lens ruling is a
genre-and-sourcing decision and is the author's; this script does not make it.

Note the ordering it produces, which is the opposite of the intuition: **the five lenses that
work are the five with the WORST resolution.** `sourcing_asymmetry` fires on 32 of 171
background documents, so a subject needs a true rate above 0.30 at n=100 before anything is
resolvable — it is a noisy instrument precisely because it is a productive one. The `0/171`
lenses have the sharpest rulers and nothing yet to point them at. `sourcing_asymmetry`'s
background is also concentrated in `_news-control` (24 of 95): "declined to comment" is
journalism boilerplate, which is the same conclusion the 2026-09-03 census reached from the
other direction when that detection landed in an annotated span zero times out of eleven.

## 3. Corpus roles, and the trap the harness refuses

A background rate computed over documents gathered *because* the phenomenon is in them is
selection on the outcome wearing a statistic's clothes — it would inflate the background and
make real firings look ordinary. So every corpus file declares a role in `ROLES`, and an
undeclared file is a hard error rather than a silent default. Three tools in this repo have
already been bitten by a glob that was blind to one input and therefore to others.

| bucket | docs | role | reader-recomputable |
|---|---:|---|---|
| `_news-control` | 95 | background | **no** — vendored third-party news text, no manifest, no fetcher |
| `advocacy-comments.jsonl` | 38 | background | yes — regulations.gov ids + `fetch_regulations.py` |
| `_calibration-cache` | 20 | background | yes — Federal Register ids + `fetch_federal_register.py` |
| `advocacy-specimens.jsonl` | 18 | background | yes — govinfo package ids + `fetch_govinfo.py` |
| `method-specimens.jsonl` | 155 | recall-fixture | yes, but see §5 |
| `specimens.jsonl` | 5 | recall-fixture | yes |

**95 of the 171 background documents are not reader-recomputable**, so rates are reported twice
— over the full pool and over the recomputable 76 alone — and only the second may carry a public
MDR. A single pooled number with a hopeful flag on it is exactly the defect this project indicts
in the ten studies it critiques. The recomputable-only column is in
`eval/background-rates.json`; it is wider, as a quarter of the pool should be.

## 4. The cross-tab, and the mechanism behind the silence

<!-- GENERATED:background-crosstab -- edit background_rate.py, not this -->
| lens | calibration-cache (bg) | news-control (bg) | advocacy-comments (bg) | advocacy-specimens (bg) | ai-governance-shoptalk (bg) | method-specimens (recall) | specimens (recall) |
|---|---:|---:|---:|---:|---:|---:|---:|
| `adept_speech` | 0/20 | 1/95 | 0/38 | 0/18 | 0/46 | 1/155 | 0/5 |
| `cognitive_capture` | 0/20 | 0/95 | 0/38 | 1/18 | 0/46 | 2/155 | 0/5 |
| `costly_signal` | 0/20 | 0/95 | 0/38 | 0/18 | 0/46 | 0/155 | 0/5 |
| `counterproductivity` | 0/20 | 0/95 | 0/38 | 0/18 | 0/46 | 2/155 | 0/5 |
| `distributed_accountability` | 0/20 | 2/95 | 0/38 | 2/18 | 1/46 | 3/155 | 1/5 |
| `inevitability_framing` | 0/20 | 1/95 | 0/38 | 2/18 | 1/46 | 2/155 | 0/5 |
| `institutional_permeation` | 1/20 | 7/95 | 1/38 | 12/18 | 14/46 | 19/155 | 1/5 |
| `legibility` | 3/20 | 2/95 | 0/38 | 3/18 | 5/46 | 24/155 | 0/5 |
| `militant_mobilization` | 1/20 | 1/95 | 0/38 | 2/18 | 0/46 | 3/155 | 0/5 |
| `narrative_management` | 0/20 | 3/95 | 0/38 | 0/18 | 0/46 | 0/155 | 0/5 |
| `network_brokerage` | 0/20 | 0/95 | 0/38 | 0/18 | 0/46 | 0/155 | 0/5 |
| `reference_capture` | 1/20 | 8/95 | 0/38 | 8/18 | 3/46 | 18/155 | 0/5 |
| `revolving_door` | 0/20 | 0/95 | 0/38 | 0/18 | 0/46 | 0/155 | 0/5 |
| `rollback_asymmetry` | 0/20 | 2/95 | 0/38 | 1/18 | 0/46 | 10/155 | 0/5 |
| `sourcing_asymmetry` | 0/20 | 23/95 | 0/38 | 8/18 | 4/46 | 3/155 | 0/5 |
| `subculture_register` | 0/20 | 6/95 | 0/38 | 5/18 | 4/46 | 7/155 | 0/5 |
<!-- /GENERATED:background-crosstab -->

This supersedes the ad-hoc 2026-09-02 cross-tab as the *record* of it — same conclusion, now
emitted by a script instead of typed into a plan. It also puts a mechanism under the silence,
which the earlier read did not have.

**The silent lenses hold cues for the wrong STANCE.** Take `rollback_asymmetry`, whose 62 cues
across 5 markers are phrases like *the new normal*, *reckless to unwind*, *turning back the
clock*, *a one-way street*, *only ever moves in one direction*. Every one of those is something
a commentator says **about** a ratchet. A Federal Register notice **performing** a ratchet says
no such thing; it says the sunset provision is removed and the temporary authority is extended.

Re-measured 2026-09-05 against the **155 full-length** register-matched Federal Register
candidates (the figures below were originally taken against 68 documents cut at 6,000
characters; see `RESULTS-2026-09-05-corpus-repair.md`):

- the lens's 62 existing cues fire on **10 of 155** documents, up from 1 of 133 on the cut
  corpus — the cues were there all along, in the 97% of each notice that was being discarded;
- the candidate **performative** phrases do better on more prose but not enough to change the
  verdict — *indefinitely* 15/155, *sunset provision* 8/155, *made permanent* 7/155,
  *extension of temporary* 2/155, *once designated* 2/155;
- and they still hit the Federal Register control (*made permanent* 1/20, *indefinitely*
  1/20), so a self-stance rewrite remains an FP-audit question, not a free win.

The conclusion is unchanged and now rests on 2.3× the documents and 33× the prose: a notice
**performing** a ratchet does not describe one. What the fuller corpus adds is that the
performative phrases are real but *rare* — 9.7% for the best of them — which is a resolution
problem rather than an absence.

The repo already carries the vocabulary for this distinction: `specimens.jsonl` records a
`stance: self | about` per document, and the corpus backlog's W1.7 asks for a self-vs-about
fire-rate check. This is that check arriving from the corpus side, and it agrees with the
2026-09-03 census from the taxonomy side: **the detector is good at naming acts and bad at
detecting moods.** Acts have a performative form in primary documents. Moods only exist in
commentary about them.

### CORRECTION, same day — for `rollback_asymmetry` this was already settled, and the fix is NOT a cue rewrite

The paragraphs above use `rollback_asymmetry` as the worked example and imply the remedy is a
self-stance detection set: teach the lens the performative language an FR notice uses while
executing a ratchet. **That is wrong, and it was already answered in this repository before this
measurement was taken.** `detectors/ratchet_series/README.md` records the same result from the
same kind of evidence:

> `rollback_asymmetry` was built to read irreversibility off prose, and it works on prose that
> argues. Tested against 30 Federal Register rules it fired on 4, and the misses settle the
> question: **"ALP Express Pilot to Permanent Status" scores 0.0. "Fourth Temporary Extension
> of COVID-19 Telemedicine Flexibilities" scores 0.0.** Both are ratchets. Neither document
> says anything ratcheting. … The pattern is not in the document. No amount of cue-matching
> recovers something that was never written down.

So the 1-hit-in-68 figure above — 10 of 155 on the repaired corpus — is a **reproduction** of a
documented finding, not a new one,
and the lens is not defective: it is correctly scoped to *argumentative* prose, and
irreversibility performed by an administrative series is a different object living in a
different instrument. `ratchet_series` exists precisely for it, reads a *series* rather than a
document, and counts one-way movement — because the fourth extension of a temporary measure
reads exactly like the first and is a ratchet only because three came before it.

Two consequences, and the second is a corpus defect:

1. **No performative cues are added to `rollback_asymmetry`, here or later.** Doing so would
   import the administrative ratchet into a rhetorical lens, blend two deliberately separate
   objects, and chase a pattern that is provably absent from any single document. The crude
   probe in §5's neighbourhood agreed in advance — candidate performative phrases reached 3/68
   at best and also hit the FR control. **Re-measured at full length 2026-09-05** they reach
   15/155 (*indefinitely*) and 8/155 (*sunset provision*), and still hit the FR control at
   1/20 apiece. More prose makes them more common without making them more discriminating,
   which is the same ruling on 2.3× the documents.
2. **The 155 `method-specimens.jsonl` records are filed under `lens: rollback_asymmetry` and
   should not be.** They are Federal Register measures — `ratchet_series` material. Filing them
   against a prose lens is what made a settled scoping decision look like a live capability gap.

**What survives of the stance finding** is the general claim, which the census supports
independently and which does not rest on this lens: the taxonomy detects *acts* stated in text
and misses *moods*, and a lens whose object only exists in commentary cannot be fed by primary
documents. Which lenses that implicates is CP2's ruling; `rollback_asymmetry` is not among them,
because its object is neither a mood nor a single-document act.

## 5. Two corpus defects found while measuring

**`method-specimens.jsonl` does not demonstrate recall, and should stop being described as if
it might** — and per the correction in §4 it is also filed against the wrong instrument.
All 155 records carry `arm: null` and `labeled_by: null` — unadjudicated candidates, not
confirmed positives. They have since been refiled from `lens: rollback_asymmetry` to
`instrument: ratchet_series`, which is consequence 2 of §4 above, done.

The retrieval finding is weakened by the refetch and not overturned: the `found_by_term` that
retrieved each record is literally present in **64 of the 155 texts** — up from 13 of 68, since
a term absent from the first 6,000 characters is often present later, but still a minority.
**59% of these documents do not contain the phrase that retrieved them**, so the retrieval was
substantially matching Federal Register metadata rather than body prose.

Across both recall buckets, 160 documents now produce 106 lens-document firings, against 7 on
the cut corpus. A bucket that proves a lens *can* fire is a real and necessary object; this is
still not one, because firing is not adjudication and none of these records is labelled. The
honest label remains `unadjudicated candidates`, and it is still correctly excluded from every
background.

**All 155 of those records were stored as raw markup** — `<bullet>`, `<INF>`/`<SUP>`, `</a>`,
Cloudflare email spans, `&#160;` — while the other buckets were clean. Fixed at all three
fetchers on 2026-09-05 (`corpus/textnorm.py`) and repaired in the stored data.

**The "cosmetic rather than load-bearing" verdict was re-measured at full length and holds.**
It had been measured on 6,000-character slices, so it could not simply be carried over; the
markup-bearing full text was refetched specifically to separate the two repairs. Same 155
documents, markup in and markup out:

- median document 4,577 → 4,553 words (0.5%);
- **every lens fires on exactly the same documents** — `legibility` 24/155 either way,
  `reference_capture` 25/155, `rollback_asymmetry` 10/155, and so on down the list.

So the movement in §2 is the **refetch**, not the normalisation. That distinction cost a
second 155-request refetch, because the first one's intermediate had been deleted after
promoting it — the pair was thrown away and the comparison had to be rebuilt to make it. Worth
recording: a paired measurement is only paired while both sides still exist.

The normalisation is still right, because a token count inflated by markup feeds the density
term and the next lens pointed at this bucket may not be so lucky.

## 6. What this unblocks, and what it does not

**Unblocked, no decision required:** every lens now has a resolution object. Four hold an index
floor; the other twelve hold a measured background rate with a stated minimum detectable rate.
`gate 24` can be restated in its intended form — *no INDEX ships without a floor computed on a
recomputable corpus; no receipts-only lens ships without a background rate* — and both halves
are now computable. `--check` is wired for CI.

**Not resolved by this file:** whether a given lens should ever carry a public index remains a
genre-and-sourcing ruling, and the licensing question for commentary-genre material is
unchanged. What has changed is that the ruling no longer blocks the barometer from having
honest resolution on all sixteen lenses — it only decides which of them may print an index.
The lenses can ship as flag-and-show-receipts against a measured background in the meantime,
which is what the framework said it was for.
