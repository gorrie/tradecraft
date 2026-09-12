# The key arrived, and the corpus it unlocked was invisible to the tools that needed it

**2026-09-01, later.** `GOVINFO_API_KEY` was obtained, which was backlog item A1 — the block on
C6 (a positive corpus per lens), which blocks C7 (a measured floor per lens), which is launch
gate #24. The fetch succeeded on the first try. Three defects sat between it and a measurement.

## 1. Nothing read the file the fetcher wrote

`corpus/fetch_govinfo.py` wrote 18 congressional hearings to `corpus/advocacy-specimens.jsonl`.
`eval/lens_floor.py` globbed `corpus/**/*.txt`. `tools/harvest_gold.py` globbed the same plus
one hardcoded filename, `method-specimens.jsonl`. Neither could see the new corpus, and the
floor tool had never been able to see `method-specimens.jsonl` either — 68 documents invisible
to the tool reporting that most lenses had no material to measure a floor over, since the day
it was written.

Enumeration now lives once, in `tradecraft/corpus_docs.py`. No consumer knows what the corpus
files are called. Inventory: **206 documents across 118 files** — 115 text, 91 JSONL records.

## 2. The cap was a head-slice, and path order put every JSONL record past it

`lens_floor.py --docs 40` took the first 40 of 206 in path order, which is all Federal Register
cache. The cap silently decided the floor would be measured over regulatory prose alone — the
one register these lenses are known not to fire on. `spread()` now takes a cap round-robin
across origin files instead of off the front.

## 3. The hearings were masthead

The first fetch produced 18 documents averaging 950 words, uniformly, several truncated
mid-sentence. `--chars 8000` was a head-slice of the whole document, and a GPO hearing opens
with 1,500–2,500 words of committee roster, printing-office boilerplate and serial numbers
before anyone makes an argument. Every document was front matter, cut at the point the chair
began speaking.

`body_window()` now skips to the first of seven structural markers (`The Committee met`,
`OPENING STATEMENT OF`, `STATEMENT OF HON.`, …) and takes the window from there, and records
`front_matter_chars_skipped` per record so the corpus says which of its documents are windows
and which are whole. **17,052 words → 74,923 words**, with 3,000–6,900 chars of masthead
skipped on 15 of 18. The three Congressional Record items find no marker and are kept as heads,
flagged with a skip of 0.

## The floors

| | before tonight | after |
|---|---:|---:|
| lenses with a measured floor | 0 of 16 | **4 of 16** |

`institutional_permeation`, `reference_capture`, `sourcing_asymmetry`, `subculture_register`, all
at MDE 0.5 index points. `legibility` fires on 7 of 206 and needs 8 — one document short.

**One defect the harness caught on its own terms.** `institutional_permeation` moves a maximum
of **6.7 index points under duplication** — the same text repeated twice — against 0.0 for
sentence-order, chunk-boundary and whitespace. Density is supposed to be per-token, so a
correctly normalised lens does not move when the document is doubled. This is precisely the
failure the perturbation was written to expose, and it is now the widest ruler in the set.
Recorded, not fixed: it is a grader question, not a cue question.

## The finding that matters: hearings are the wrong corpus for half the lenses

Twelve lenses still cannot state a floor. The tempting reading is that the cues are too
literal. It is worth writing down that this was checked and the tempting reading is wrong.

`inevitability_framing` fires on 1 of 206 documents. Its cues are literal phrases — *there is
no alternative*, *right side of history*, *adapt or die*. Searching the 75,000 words of hearing
text for the move in ANY phrasing returns: `inevitab` twice, `only option` once, `only way`
once, `too late` twice. **The move is not there in other words. It is not there.**

A congressional hearing is procedural: a chair asks, a witness answers with qualifications, and
both argue in institutional voice. The lenses that fired are the institutional ones. The ones
that did not are the movement-rhetoric ones, and they were authored for material this corpus
does not contain.

So no cue is being widened. Corpus item 28 already named what those lenses need — "op-eds,
speeches, consultation responses, campaign material arguing that a measure must not be
reversed." The nearest such material that is public record and freely retrievable is **public
comments filed on federal rulemakings**: written to persuade, filed by movements, industry
associations and individuals, and served by regulations.gov on the *same api.data.gov key*
(verified tonight: 165,258 comments match `surveillance` alone). That is the next fetcher, and
it is the remaining path to gate #24 for the other twelve.

## Standing

`eval/lens-floors.json` regenerated. 129 tests pass. Four floors are real and measured over
206 documents; twelve lenses remain unresolvable and are reported as unresolvable, which is
the same answer as this morning stated more precisely and over four times the corpus.
