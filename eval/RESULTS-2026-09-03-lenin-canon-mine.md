# RESULTS 2026-09-03 — the method on a second camp, and the confounds a second run finds

`tankie_mlm` (Marxist-Leninist / Maoist), run the same way as `georgist` earlier the same day.
Second run of `BACKLOG-shibboleth-corpus-study.md`'s per-camp method, chosen because both the
camp's canon **and** its discipline-matched control are public domain and obtainable.

**Yield: three cues from fourteen surviving candidates.** Better than georgist's 1-from-22, and
the reason is entirely that the second run had the first run's guards already in place.

---

## 1. Corpora

| role | source | words |
|---|---|---:|
| camp canon | Lenin, *Imperialism, the Last Stage of Capitalism* (1926 edn) + *Left-Wing Communism: an Infantile Disorder* (1920), 29 pages | 73,130 |
| **discipline control** | Marx & Engels, *Manifesto of the Communist Party*, *Wage-Labor and Capital*, *The Poverty of Philosophy*, 17 pages | 74,628 |
| benign controls | `_news-control` + `_calibration-cache` | 115 documents |

Size-matched within 2%, which matters because the field-vocabulary test is a rate comparison.

**Why Marx is the right control here, and it is the sharpest one this study has had.** The
benign controls cannot distinguish Marxism-Leninism from Marxism — neither is socialist theory.
Marx and Engels can, and they are also the camp's own ancestor, which makes this the strictest
possible form of the study's rule that *a shibboleth must identify ITS discourse, not
activist-speak generally*.

## 2. Two new confounds, both invisible to the previous run's guards

### Work titles and author names read as strong idiom

The first pass put these at the top of the candidate list, each clearing every control:
`infantile disorder`, `left-wing communism`, `communism an infantile disorder`,
`vladimir ilyich lenin`, `ilyich lenin`, `last stage of capitalism`, `imperialism the last
stage`. All of them are the **titles of the two books and the author's name**.

The saturation guard added during the georgist run could not catch them. It drops grams present
in more than 80% of canon documents, and with a two-book canon each title appears in only its
own book's chapters — 13 and 16 of 29 files, about half. **A guard tuned for one work fails on
two**, and it fails in the direction that looks like a finding.

Source: rendered Wikisource pages open with a navigation block carrying the work title, the
year, the author and prev/next links. It is wrapped in a div whose class is literally
`ws-noexport` — Wikisource's own marker for "not part of the text". Two fixes, deliberately
overlapping:

- `corpus/fetch_wikisource.py` now strips `ws-noexport` / `wst-header` elements by depth-counted
  div matching, at the source.
- `corpus/mine_camp_idiom.py` builds a stoplist from the canon's **own document titles** plus an
  optional `--author`, because titles are known metadata and should not be re-discovered
  statistically. This one is source-agnostic and catches whatever any other archive leaks.

### Scholarly apparatus

`op cit` — 16 occurrences across 6 files, absent from both controls. That is precisely the
statistical profile of a shibboleth and it is a footnote convention. A heavily-cited primary
work carries its citation machinery at the frequency of real idiom. Now filtered alongside
navigation (`APPARATUS` in the miner).

### Still unfiltered, and honestly so

`die bank`, `deutsche bank`, `million marks`, `lloyd george`, `hendersons and snowdens` — proper
nouns and quantities from the sources Lenin cites. They share a signature: high count,
concentrated in **2–4 files** where he discusses German banking, against 7–10 files for real
theory vocabulary. Dispersion is therefore informative but not decisive — `division of the
world` is genuine and sits in 5 — so it is reported in the `files` column and left to the human
rather than wired into a filter.

## 3. The ruling, and the basis that survives an incomplete control

Fourteen candidates cleared both controls. **Three were taken.**

| cue | canon | files | benign | in Marx | basis |
|---|---:|---:|---:|---:|---|
| `finance capital` | 14 | 7 | 0 | 0 | Hilferding's term, coined **1910** |
| `second international` | 15 | 7 | 0 | 0 | organisation founded **1889** |
| `left communists` | 18 | 8 | 0 | 0 | faction named **1918** |

**They are kept on CHRONOLOGY, not on the control's silence.** Marx died in 1883. None of these
three could appear in his corpus however much of it is missing from a control — and Lenin's own
text dates one of them: *"the period of the Second International — that is, of the twenty-five
years between 1889 and 1914"*.

That distinction did real work, because it is what excluded the most tempting candidate:

> **`dictatorship of the proletariat` — 22 occurrences, 10 files, 0 in the control — was NOT
> taken.** Marx used the phrase, in *Critique of the Gotha Programme* (1875), which is not in
> the fetched control set. Its zero is an artifact of **control incompleteness**, exactly like
> `margin of cultivation` passing the Smith control because Smith predates Ricardo. A control
> is always missing something; a cue justified only by its silence inherits every gap.

`proletarian dictatorship` (20 / 7) was declined for the same reason — a phrasing variant of a
Marx term. `division of the world`, `concentration of production`, `colonial policy` and
`capitalist countries` are descriptive rather than coined, and were declined as such.

## 4. A gap in the fixture format, found by needing it

The cross-camp negative for this camp is the *Communist Manifesto*: it must **not** fire
`tankie_mlm`. Written as an ordinary lens-level negative it **failed** — and it failed
correctly. The passage fires `revolutionary_left`, and that is a **true positive**: Marx is that
camp's canon. The fixture was wrong, not the detector.

The format had no way to say *"the lens may fire, but this marker must stay quiet"* — which is
the exact assertion the study's step 3 requires for every camp. So `run_eval.py` gained
**`forbid_markers`**, with its own counter (`cross-camp quiet: 1/1`) folded into the strict gate.
This is the mechanism every remaining camp's cross-camp negative will use, and it did not exist
until a real cross-camp negative was attempted.

## 5. Measured effect

| | before | after |
|---|---|---|
| strict eval | 53/53 pos, 34/34 neg | **55/55, 34/34**, plus cross-camp quiet 1/1 |
| gold recall | 139 of 162 | **141 of 165** (all three new gold fire) |
| `subculture_register` background | 8/171 | 8/171 — **unchanged**, so the three cues add no measurable FP load |
| camps ready to validate | 15 of 27 | **16 of 27** |
| `tankie_mlm` | 4 cues, 1 gold, THIN | 7 cues, 4 gold, ready |

## 6. What the second run says about the cost of the ninth

georgist took a full cycle for one cue; this one produced three, and the difference is not
skill. It is that the guards from the first run — saturation, orthographic folding, nested
templates — were already in place, so the candidate list arrived cleaner. Each run pays for the
next.

Against that, both runs found **new** confounds that the previous run's guards could not see, and
both were of the same shape: *structural artifacts of the transcription presenting with the
statistical signature of idiom*. Expect the third camp to find a third one. The guards now
cover navigation, templates, saturation, titles, authors, apparatus and orthography, which is
seven classes of noise that all looked like findings.

The human ruling remains the bottleneck, and this run sharpens what that ruling actually is:
**not "is this phrase distinctive?" but "is there a reason beyond my control's silence to
believe it?"** Chronology supplied that reason three times here. Where nothing does, the honest
answer is to decline, as `dictatorship of the proletariat` was declined.
