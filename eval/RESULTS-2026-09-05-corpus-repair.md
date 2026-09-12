# The specimen corpora were 3% of themselves, and every word count included HTML

2026-09-05

Two defects, found by `tools/truncation_scan.py` and by pointing it at one bucket at a time.
Both are now repaired in the data and closed at the fetcher, and the gate that found them is
green for the first time.

## 1. The corpora were cut at their fetcher's default and never said so

| corpus | before | after |
|---|---:|---:|
| `method-specimens.jsonl` | 84 of 155 at **exactly 6,000 characters** | median **31,433** |
| | 889,498 characters total | **29,882,953** |
| `advocacy-specimens.jsonl` | 15 of 18 at **exactly 30,000 characters** | median **133,861** |
| | 450,000 characters total | **2,496,561** |

The corpus held **3.0%** of the prose it claimed to hold. One hearing went from 30,000 to
255,991 characters — the stored document was the first eleven percent of it.

### Refetched by id, not by re-running the fetchers

`fetch_federal_register.py` and `fetch_govinfo.py` retrieve **by search term**. Re-running them
would have returned whatever those searches return today, so corpus membership would have moved
at the same time as the truncation and no measurement could have been attributed to either.
`corpus/refetch_full_text.py` refetches the documents **already in the corpus, addressed by
their own identifiers** — same documents, same order, one factor different. It writes to
`*.full.jsonl` and refuses to promote unless every id came back.

**Three could not be refetched, and they now say so.** `gi_CREC-2024-07-11`,
`gi_CREC-2022-09-28` and `gi_CREC-2006-09-28` are Congressional *Record* issues. The corpus
stored a granule's title (`Text of Senate Amendment 2594`) against the *package's* id, and the
package exposes no granules through the API (`count: 0`) — so no identifier addresses the text
actually held. They keep their truncated text with `truncated: true`, `truncated_at_chars`, and
a `refetch_blocked` reason. A fragment that declares itself is data; a fragment that doesn't is
a number waiting to be misread.

## 2. Every fetcher stored markup as words

| corpus | records carrying HTML tags | carrying entities |
|---|---:|---:|
| `method-specimens.jsonl` | **155 of 155** | 106 |
| `advocacy-comments.jsonl` | 28 of 38 | **36 of 38** |

`fetch_regulations.py` did `" ".join(comment.split())` and nothing else, so `<br/>` and
`&rsquo;` sat in the prose verbatim. The Federal Register's raw text carries its own markup —
`<bullet>` (3,614), `<INF>`/`<SUP>` (2,612), `</a>` (4,092), Cloudflare email-obfuscation spans
(306), `&#160;` (309) — and nothing touched it.

Each of those is a token in `text.split()`. Background rates here are fired-documents over
n-documents with word counts deciding the buckets, a cue cannot match across a `<br/>`, and
`&rsquo;` defeats every pattern written with a real apostrophe.

**Three implementations of this already existed** — in `fetch_manifest.py`, `mediawiki.plain()`
and `refile_method_specimens.de_html()` — and none of the three had ever been applied to the
specimen corpora. There is now one, `corpus/textnorm.py`, used by all three fetchers, with
`de_html` kept as a delegating wrapper.

### Inline and block are not the same tag

`de_html` mapped every tag to a space, which turns `H<INF>2</INF>O` into three tokens. Mapping
every tag to nothing welds `one<br/>two`. So inline formatting closes up and everything else
opens a gap. That is the only judgement in the file and the reason to have one copy of it.

### The cleaner ate a sentence before it was allowed near the data

The first pattern was `<[^>]{0,400}>` — any `<...>` span. In a corpus of environmental
rulemakings that is **prose**: `precipitation <20 inches/year) for disposal years prior to 2010`
was deleted whole from `fr_2024-07413`. It surfaced only because the repair pass was not
idempotent on that one record. A tag name is now required after the `<`, the case is pinned in
`tests/test_textnorm.py`, and the repair refuses to write when any record loses more than 25%
of its words.

## 3. `_news-control` declares its chunking instead of being permanently red

95 vendored files, 94 of them **exactly 3,200 words**, every one ending mid-sentence: fixed-size
slices of concatenated wire copy, not articles. That is real and deliberate — there is no
fetcher in this repo that could produce it differently — and it was already written up in
`eval/background_rate.ROLES`, where a reader of the *rates* would find it and a scanner of the
*files* would not.

A directory may now declare itself in `.truncation.json`. **The declaration is re-measured, not
believed.** Declare a cap the data does not have and the scan reports `declaration-mismatch` at
HIGH and leaves every record undeclared, so the underlying cut is still found. The only way a
declaration quietens anything is by being true. `test_a_FALSE_declaration_suppresses_nothing`
is the guard.

The consequence the sidecar records is the one that matters: rates over this bucket are
fired/n_docs with no length normalisation, so **the chunk size is a free parameter of every rate
computed here** — repackaging identical prose from 300-word articles into 3,200-word chunks
moved `sourcing_asymmetry` from 2.1% to 12.5%, and this bucket is 95 of 171 background
documents.

## 4. Pooling buckets hid a 37% signal at 2.8%

Scanning `corpus/` as one input reported "14 of 508 documents end mid-sentence" — 2.8%, ignorable.
All 14 were in `advocacy-comments.jsonl`: **14 of 38, 37% of that bucket**. A bad bucket hides in
a good denominator.

They turned out to be genuine — public comments end with a signature (`Sincerely, Ms. Barbara
Green`), which has no terminal punctuation, and that fetcher has no length cap and no wall in its
length distribution. But the finding was only *checkable* per bucket, and it was the per-bucket
scan that exposed defect 2 above.

## 5. What the repair COST, and it is not nothing

Truncation had accidentally been homogenising the background pool. Cutting every hearing at
30,000 characters made a 250,000-character hearing the same size as a 30,000-character one, and
a per-document firing rate over documents of equal length is at least comparable across
buckets. The repair removed that accident along with the defect:

| bucket | role | n | median words | min | max |
|---|---|---:|---:|---:|---:|
| `advocacy-specimens.jsonl` | background | 18 | **19,301** | 684 | 57,458 |
| `_news-control` | background | 95 | 3,200 | 1,090 | 3,200 |
| `_calibration-cache` | background | 20 | 2,898 | 413 | 49,491 |
| `advocacy-comments.jsonl` | background | 38 | **459** | 140 | 750 |

The background pool now runs **140 to 57,458 words — a 410× range**, p10 413 and p90 14,187.
A hearing fires more often than a public comment for no reason except that there is 42× more of
it, and every rate here is fired-documents over n-documents with no length normalisation.

**The direction is conservative**, which is why this is a note and not a retraction: the long
documents inflate the background, and an inflated background makes every detection claim
*harder* to sustain. Nothing published gets easier because of it. But it is the same defect the
`_news-control` chunking note has carried since 2026-09-04, now larger and no longer confined to
one bucket, and the fix is the one that note already names: **a length-invariant unit** — firings
per 1,000 words, or a fixed-window scan — not a ROLES entry and not a re-truncation. Pooling
buckets of different length was already forbidden here for exactly this reason; the pool has now
become internally what it was forbidden to be across buckets.

Open, and logged as such. Re-truncating to make the rates comparable would be choosing a
measurement that flatters the instrument over the data that exists, which is the move this
project spent two days indicting in other people's work.

## Where the gate stands

`python tools/truncation_scan.py corpus --check` now exits **0**, and is wired into CI as of this
commit. It exited 1 on every previous day this tool has existed, which is why it was
deliberately left unwired: a gate that cannot go green is a gate that gets switched off
wholesale.

**One finding still prints, at MEDIUM, and is deliberately not gated:** `16 of 338 documents end
mid-sentence`. Fourteen of those are the `advocacy-comments` signatures above — genuine prose,
in a bucket with no length cap and no wall. So `--check` was scoped on 2026-09-05 to fail on
**HIGH** (the cap signatures), with `--strict` retaining the old behaviour for an audit pass.

That scoping is the kind of change this project treats as guilty until proven otherwise, so it
is settled by test rather than by argument. `test_a_truncated_corpus_still_fails_the_default_check`
asserts the 6,000-character cut this tool was written to find still fails `--check` without
`--strict`; `test_broken_tails_everywhere_are_a_cap_signature_and_gate` asserts that a cut made
at a *paragraph* boundary — which leaves no round-number cap for `cap_spike` or `wall` to find —
also still fails, because the tool escalates broken-tail to HIGH above 50%. A narrower gate that
still catches what it was built for is a gate. One that stops catching it is a retreat, and
these two tests are what tells them apart.

## Files

- `corpus/textnorm.py` — the one normaliser (new)
- `corpus/repair_markup.py` — applies it to data already on disk; backs up, refuses on >25% word loss (new)
- `corpus/refetch_full_text.py` — by-id full-length refetch (new)
- `corpus/_news-control/.truncation.json` — verified self-declaration (new)
- `tools/truncation_scan.py` — directory-level declarations, verified
- `corpus/fetch_federal_register.py`, `fetch_govinfo.py`, `fetch_regulations.py` — normalise on the way in
- `corpus/refile_method_specimens.py` — `de_html` delegates
- `tests/test_textnorm.py` (new), `tests/test_truncation_scan.py`

One test rename worth noting: `test_advocacy_specimens_still_fail` became
`test_advocacy_specimens_pass_after_the_refetch`. A test whose name asserts an artifact still
fails has to be edited on the day the artifact is fixed, which is the worst day to be arguing
about a test.
