# Truncation is the recurring defect, and it sets the background rates

2026-09-04

Chasing the last non-recomputable input to the background firing rates turned up something
bigger than the licensing question it was meant to close. **Every corpus bucket in this
repository is truncated, and the truncation of the largest one sets every background rate in
the study.**

The prompt was an observation rather than a measurement: truncation kept coming up. It does,
and it has one signature — *something stopped at a limit, the artifact stayed well-formed, and
the number derived from it went on being used.* Nothing errors, so nothing is noticed.

## The instances

| when | what | how it was found |
|---|---|---|
| 2026-09-04 | `corpus/_news-control/`: 94 of 95 background documents are **exactly 3,200 words**, every one ending mid-sentence. Fixed-size chunks of concatenated wire copy, not documents. | accident, while replacing the bucket |
| 2026-09-04 | `corpus/advocacy-specimens.jsonl`: 18 congressional hearings, median 4,789 words, max 5,202, **78% within 10% of the maximum** — a 30,000-character window. | the scanner below, on its first run |
| 2026-09-04 | `call_ollama` hardcoded `num_predict: 800` after a fork was resolved by taking the narrower side. A 62-item answer sheet does not fit in 800 tokens. | a TypeError, not the truncation itself |
| 2026-09-04 | The Wikinews media regex stopped at the first `]]`, truncating its own match and leaving `thumb\|left\|A file photo of…` in 6 of 95 documents. | reading sample output |
| 2026-08-30 | `max_tokens` was never recorded, so truncation was being classified as **refusal** (fixed in `96e5fa5`). | the same defect one layer up |
| ongoing | `truncated` is a live failure class in the run classifier. | it is the standing acknowledgement that this recurs |

## The one that changes a number

`_news-control` is 95 of the 171 documents behind every background firing rate, and
`rate_block` computes `fired / n_docs` — a per-document proportion with no length
normalisation. So the chunk size is a free parameter of every rate.

Measured three ways, using `background_rate`'s own `index_of` rather than a reimplementation:

| lens | A: old pool, 3,200-word chunks | B: real articles, median 303 | C: same prose as B, re-chunked to 3,200 |
|---|---:|---:|---:|
| `sourcing_asymmetry` | 25.3% (24/95) | 2.1% (2/94) | 12.5% (2/16) |
| `institutional_permeation` | 7.4% (7/95) | 1.1% (1/94) | 12.5% (2/16) |
| `reference_capture` | 8.4% (8/95) | 0% | 0% |
| `subculture_register` | 6.3% (6/95) | 0% | 0% |
| `narrative_management` | 3.2% (3/95) | 0% | 0% |
| `rollback_asymmetry` | 2.1% (2/95) | 1.1% (1/94) | 6.2% (1/16) |

**Column C is the decomposition.** Same prose as B, same packaging as A. On
`sourcing_asymmetry`, repackaging identical text into 3,200-word chunks moves the rate from
2.1% to 12.5% — so roughly half the gap between the pools is chunk size and nothing else.
`institutional_permeation` goes the other way: C exceeds A, so the new prose is *more*
permeation-like per 3,200 words than the old.

C rests on 16 documents, so it is directional, not decisive. But the direction is not in doubt:
a per-document rate over fixed-size chunks measures the chunk size.

## What this does and does not license

**It does not license swapping the pool.** `reference_capture` fires 8.4% in the old pool and
0% in the new at *either* packaging, so the two differ in content as well as in unit, and the
new pool is 49k words against 302k. A swap would move every background rate and confound two
causes at once. That is the mistake this study convicts other people of.

**It does license the Wikinews pool as an additional, recomputable bucket**, and it makes the
old pool's construction a stated fact rather than a hidden one. `corpus/fetch_wikinews.py`
builds it: a committed manifest pinning **revision ids** (not titles — a wiki page changes
under you), CC-BY 2.5, articles drawn from dated archive categories and never from a topic
search, with `--allow-topical` required and recorded if anyone ever selects on topic. 101
records, 94 fetched, one `--verify` away from proof that a reader gets the same text.

**And it says the honest next step is more words, not a substitution.** Matching 302k words at
Wikinews' ~300 words/article needs roughly 1,000 articles; the 2006–2008 archive runs ~350
articles/month, so three peak months would do it. `fetch_raw_by_revids` batches 40 revisions
per request, so that is ~25 requests rather than 1,000.

## The tooling the pattern actually needed

`tools/truncation_scan.py`. Four signatures, because a per-case patch does not generalise:

1. **cap-spike** — the maximum of a distribution is also its mode. A real length distribution
   has a tail; a capped one has a wall. Catches `_news-control` instantly (94 of 95 at 3,200).
2. **soft-cap** — values crowd *under* the maximum without landing on it, because the cutter
   trimmed to a word boundary after slicing. This is the commoner shape, and `cap-spike`
   cannot see it. Catches the hearings at 78% within 10% of 5,202.
3. **broken-tail** — text ending mid-word or without terminal punctuation.
4. **at-cap** — a measured value within a hair of its own declared limit (`tokens_out` vs
   `max_tokens`). Exact when both fields exist, which is the argument for recording the limit
   beside the measurement in every producer.

`round_ceiling` raises severity when the maximum is a power of two or a round multiple of 100:
caps are chosen by humans, and humans choose round numbers.

### Half the tests are false-positive guards, and that is the point

The first run against run records reported **27 of 32 forced-choice answer sheets as truncated**.
They end `62. Strongly Disagree` — a complete and correct sheet. A scanner that flags correct
data is a scanner someone switches off, and then it catches nothing at all. `looks_structured`
suppresses the tail test when the final line is an enumerated or bulleted item, and
`test_an_answer_sheet_is_not_truncated` pins it.

Likewise `soft_cap` deliberately declines `method-specimens.jsonl` (38% within 10% of max —
a real distribution of similar-length Federal Register measures, not a cutter). Thresholds
tuned until nothing fires would have been the other failure.

24 tests, and the suite is 389 green.

## Follow-up, same day: two of my own claims here were wrong

**The hearings are not head-sliced, and I said they were.** `fetch_govinfo.py` already has
`body_window`, which finds the first `The Committee met` / `OPENING STATEMENT OF` marker,
skips the masthead, and windows from there — added 2026-09-01 for exactly this reason, with a
measured note saying that all 18 documents in the *first* fetch were front matter. The
standing rule is already honoured. The soft-cap signature correctly detected a cut; the cut is
deliberate, documented in the fetcher, and correct. My "violates a standing rule" was an
inference from a length distribution, which is the same move as reading a rate off a chunk
size.

**And truncation does not explain the missing retrieval terms.** `method-specimens.jsonl`
records the `found_by_term` that retrieved each document, and the term is absent from 124 of
155 stored texts — which looked like the truncation cutting the term away. It is not: the
term-present and term-missing documents have *identical* length distributions (median 789
against 790, max 892 against 890). The real cause is that the term is a **search query**, not a
quotation: `fr_2026-17576` was retrieved by "extension of temporary provisions" and the
document says "extension of temporary modification". federalregister.gov's search does not
require the exact phrase. The ROLES note's conclusion — that these cannot demonstrate recall —
stands, for a different reason than the one I proposed.

## The real defect, and the three fixes

`method-specimens.jsonl` **is** truncated, and by a worse mechanism than the hearings:
`fetch_federal_register.py` did `" ".join(text.split())[:args.chars]` with `--chars` defaulting
to 6,000. A raw **character** cut, so one specimen ends mid-URL-token
(`…%20DEA%20SAMHSA%20buprenorphine%20telemedi`). A severed token can match a cue by accident
and can never match one it would have matched whole.

| fix | what changed |
|---|---|
| scanner false positive | Federal Register notices end `BILLING CODE 4810-AL-P`, which is the document's real terminator. 18 of 20 `_calibration-cache` files were flagged; now 0. `_KNOWN_TERMINATORS` handles the filing line and billing code — and the first pattern was too narrow (`[\d-]+[A-Z]?` cannot match `4810-AL-P`), so it left one file flagged, which reads as a genuine finding. |
| character cut → word boundary | both fetchers now cut on `rsplit(" ", 1)` when the tail is being dropped anyway. |
| records self-describe | both now carry `truncated`, `truncated_at_chars` and `full_words`. `fetch_govinfo` already recorded `front_matter_chars_skipped` — what was skipped at the *front* — and said nothing about what was cut at the *end*. A corpus should not need a statistical test to reveal how it was built. |

The scanner now treats a declared cut as an `info` disclosure that suppresses cap-spike,
soft-cap and broken-tail alike, and `info` does not fail `--check`. Otherwise the honest
fetcher earns a warning and the silent one passes — a perverse incentive, and the third
false-positive class this tool produced. All three were found by reading what it flagged
rather than trusting the count.

**The fixes are to the producers, not the data.** The existing 155 Federal Register specimens
and 18 hearings still lack the markers and still carry character-boundary cuts; they gain both
only on a refetch, which is a deliberate act because refetching changes the corpus every
measured number rests on.

396 tests green.

## Standing consequence

A cap spike is not automatically a defect — a deliberately chunked corpus has one by
construction. It **is** automatically undocumented until someone writes down that the chunking
is deliberate and what it does to every rate computed per document. That sentence is the
scanner's own closing output, and `corpus/_news-control`'s ROLES entry now has to carry it.
