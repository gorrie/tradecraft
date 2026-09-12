# RESULTS 2026-09-03 — the shibboleth method run end to end on one camp, and what it cost per cue

First full execution of `BACKLOG-shibboleth-corpus-study.md`'s per-camp method: assemble the
camp's canon, mine coined idiom recurring across ≥2 of its own works, validate recall on the
canon and precision against controls, verdict per candidate.

Camp: **`georgist`** — chosen because its canon is public domain, so nothing is licensing-blocked
and every number here is reader-recomputable from stable public URLs.

**Yield: one cue from twenty-two candidates.** That ratio is the useful finding.

---

## 1. The canon, and how it was obtained

| source | words | provenance |
|---|---:|---|
| *Progress and Poverty* (1879) | 69,759 | en.wikisource.org, "Progress and Poverty (George, unsourced)/Chapter *" — 28 pages, one batched API call |
| North American Review essay | 4,093 | en.wikisource.org, via redirect from a title on `Author:Henry George` |
| **negative control:** *The Wealth of Nations* (1776) | 418,125 | en.wikisource.org, 39 pages rendered via `action=parse` |

Fetching notes, because the next camp will hit the same walls. Project Gutenberg's own pages say
not to scrape them and point at a catalog dump, so Wikisource's MediaWiki API was used instead —
it is built for programmatic access and takes up to 50 titles per request, turning a 28-chapter
book into one call. Two traps: Wikisource's proofread books keep their text in the `Page:`
namespace and transclude it, so `prop=revisions` returns a **stub** (27 chapters came back as 189
words total) and `action=parse` is required to render it; and `titles=` does not follow redirects
without `redirects=1`, which silently returned 1 of 8 requested works.

## 2. The discipline-matched negative is the arm that did the work

The study's step 3 asks for precision against "the benign control corpus AND the OTHER camps'
primary works." For this camp the benign controls — 95 news documents and 20 Federal Register
notices — **cannot do the job**, because neither is economics. They cannot distinguish *Georgist*
from *classical political economy*.

Adam Smith can. Of the 22 candidates that recurred across both George works and were absent from
all 115 benign control documents, Smith rejected four outright as field vocabulary: `adam smith`
(69 occurrences in Smith), `taxes upon` (82), `wealth of nations` (51), `effect upon` (14). Those
four would have shipped on the benign controls alone.

**Generalisation for every remaining camp: a benign control is not sufficient. Each camp needs a
control matched to its DISCIPLINE** — classical economics for `georgist` and `mmt_monetary`,
academic sociology for `critical_social_justice`, mainstream theology for
`christian_nationalist` and `tradcath_integralist`, security-studies writing for
`jihadist_militant`. Without it, a camp's cue set fills up with the vocabulary of its field.

## 3. Why 21 of 22 candidates still failed

Nine candidates survived both controls. Only one is defensible:

| candidate | P&P | essay | verdict |
|---|---:|---:|---|
| **`natural opportunities`** | 15 | 1 | **KEEP** — George's coined term of art |
| `distribution of wealth` | 31 | 3 | CUT — field vocabulary; Smith phrases it differently, which is not the same as not sharing it |
| `food clothing`, `clothing and shelter`, `great masses`, `least exertion`, `thrown open`, `desires with the least` | 5–6 | 1–2 | CUT — Victorian prose habits. These would fire on Mill, Ricardo or Spencer |
| `wages depend` | 4 | 1 | CUT — George's wage-fund argument, but the phrase is a sentence fragment, not an idiom |

**The methodological finding, and it should change step 2 of the method.** Keyness mining against
a single-author negative control cannot separate *camp idiom* from *authorial style*. Everything
distinctive about *Progress and Poverty* relative to *The Wealth of Nations* is partly Georgism
and partly George-the-Victorian-essayist, and n-gram frequency cannot tell those apart — which is
why the survivor list is full of phrases like `thrown open`.

The fix is structural: **a camp's canon needs ≥2 DIFFERENT AUTHORS**, so that what survives is
what the camp shares rather than what one writer repeats. For `georgist` that means a later
land-value-tax advocate alongside George himself. Recorded against the method rather than
discovered again per camp.

## 4. The one cue, fully validated

`natural opportunities`, added to `subculture_register/georgist`.

| arm | result |
|---|---|
| recall, own canon | 15 occurrences in *Progress and Poverty* (chs. II, VII, VIII, IX) + 1 in the essay — recurs across two works, as the method requires |
| precision, benign controls | 0 of 115 documents |
| precision, discipline-matched | **0 in 418,125 words of Adam Smith** |
| cross-camp collision | none — the cue belongs to no other camp (`eval/camp_readiness.py --collisions`) |
| background firing rate | `subculture_register` unchanged at 8/171, so the cue adds no measurable false-positive load |

It is a term of art rather than a slogan, and George stops to define it — *"the term land includes
all natural opportunities and forces"* — which is what a camp's term of art looks like from the
inside, and is now the detection's second gold example.

Two fixtures landed with it. The positive is that definitional passage. **The negative is the one
worth keeping:** Smith on the rent of land — landlords who "love to reap where they never sowed",
the price of produce, rent as a component of price — the camp's exact subject matter with none of
its coined idiom. It stays quiet at index 0.0. That fixture is what stops a future contributor
from "improving" this camp with `rent of land` or `the landlord`.

## 5. What it did to the measured state

| | before | after |
|---|---|---|
| strict eval | 52/52 positives, 33/33 negatives | **53/53, 34/34** |
| gold recall | 138 of 161 | **139 of 162** (the new gold fires) |
| `subculture_register` background | 8/171 | 8/171 — unchanged |
| camps ready to validate | 14 of 27 | **15 of 27** |
| `georgist` | 4 cues, 1 gold, THIN | 5 cues, 2 gold, ready |

## 6. The honest cost, and it is the reason to record this

One camp took a full session's fetch-mine-validate cycle and yielded **one cue**. Nine camps
remain thin. At this rate the per-camp deepening is not a sprint, and the numbers say why: the
cheap part (fetch a public-domain canon, count n-grams) produces mostly authorial style, and the
expensive part is a human deciding which surviving phrase is a term of art rather than a Victorian
tic.

Two things make the next camp cheaper rather than merely later:

1. **The fetch path is known** — Wikisource API, `redirects=1`, `action=parse` for proofread
   books, batched titles. The two traps above cost most of the fetching time and will not recur.
2. **The discipline-matched control is now a required arm**, named per camp in §2. Building it
   once per discipline serves several camps — classical economics covers `georgist` and
   `mmt_monetary`; mainstream theology covers two more.

Neither of those makes the human judgement cheaper, and that judgement is the actual bottleneck.
That is worth knowing before nine more camps are scheduled.
