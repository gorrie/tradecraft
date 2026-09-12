
# A census of the detections that actually work: three of 140

**2026-09-03.** The author asked for a census of actually effective detections, "so that we can
start somewhere." Here it is, and the honest headline is that **three detections out of 140 are
demonstrated above chance.** That is a starting point rather than an indictment — but it has to
be the real number.

## Method

`eval/detection_census.py`, against the **Propaganda Techniques Corpus** (SemEval-2020 Task 11,
CC-BY-4.0, vendored at `research/external/ptc/`): 371 articles, **5,468 spans annotated at
character level by six professional annotators**, 18 techniques, drawn from 13 propaganda and 36
non-propaganda outlets.

For every cue firing, does it land inside a span a human independently marked? **Read the lift,
not the precision** — 13.25% of the corpus's characters sit inside some annotation, so a
detection landing there 13.25% of the time is firing at chance.

`ptc_precision.py` already did this at LENS level in August. This is at DETECTION level, because
a lens is not the unit you keep or cut: a lens at 1.19× chance is not uniformly mediocre, it is
some detections carrying signal and others firing on ordinary journalism. Judging the whole lens
on the aggregate is the same net-aggregate error this project keeps catching elsewhere.

## The census

| lens | detection | hits | in-span | lift | 95% CI |
|---|---|---:|---:|---:|---|
| `reference_capture` | `penalty-without-adjudication` | 6 | 5 | **6.29** | [3.30, 7.32] |
| `subculture_register` | `maganr-tells` | 11 | 8 | **5.49** | [3.28, 6.81] |
| `institutional_permeation` | `infiltrate-existing-institutions` | 5 | 3 | **4.53** | [1.74, 6.66] |
| `sourcing_asymmetry` | `unsourced-assertion` | 5 | 1 | 1.51 | [0.27, 4.71] |
| `sourcing_asymmetry` | `declined-to-comment` | 11 | 0 | 0.00 | [0.00, 1.95] |
| `sourcing_asymmetry` | `honorific-framing` | 6 | 0 | 0.00 | [0.00, 2.95] |

|  | count |
|---|---:|
| **above chance, interval excludes it** | **3** |
| below chance, interval excludes it | 0 |
| fired enough to judge, interval spans chance | 3 |
| fired 1–4 times, too thin to judge | 32 |
| never fired | 102 |

**The CI rule applies here as everywhere else in this project.** A lift of 6.29 from six firings
is not a finding on its own, and neither is a 0.00 from eleven. So `unsourced-assertion` at 1.51
is **undecided**, not working — and `declined-to-comment` and `honorific-framing`, which land in
an annotated span **zero times out of 11 and 6**, are *suspicious but not established*. I will
not cut them on an interval that spans chance, having spent this week arguing nobody else should
either.

## What the three winners have in common

They name a **concrete, checkable act**, not a rhetorical mood:

- `penalty-without-adjudication` — a sanction imposed without a hearing
- `maganr-tells` — a specific subcultural register with distinctive vocabulary
- `infiltrate-existing-institutions` — an explicitly stated strategy of entering rather than confronting

The undecided and silent ones are mostly **moods and framings** — inevitability, counterproductivity,
costly signalling. That is a pattern worth building on: this detector is good at naming a move
somebody made and bad at detecting an attitude somebody holds.

## Why 102 never fired, stated precisely

Not a fault in itself. PTC annotates *propaganda techniques in news articles*; this taxonomy
names *institutional tradecraft*. They overlap without being the same construct, and
`costly_signal` and `adept_speech` are not about news register at all.

But it is now the third independent corpus to say the same thing. Measured this week:
congressional hearings (74,923 words) produced almost nothing; public rulemaking comments
(16,450 words) produced nothing; and across all 244 documents we hold — 600,458 words — the
silent lenses' cue phrases are **absent, not blocked**: `costly_signal` 0 of 18 cues present,
`counterproductivity` 0 of 37. Probing concept-level synonyms rather than authored cues,
"counterproductive" appears **once** in 600k words and "unintended consequence", "backfire" and
"diminishing return" appear zero times each.

So the missing material is not a register within institutional writing. It is a different genre
of authorship — Illich and his successors, critical essays, dissident memoir, movement
manifestos — and that material is largely copyrighted. **The blocker is licensing, not
sourcing**, and it should be named that way.

## What this changes

1. **There is a defensible core.** Three detections, and a fourth lens-level result from August
   (`subculture_register` 2.16×, `reference_capture` 1.93× at lens level). A barometer built on
   *those* can state a resolution and show receipts today.
2. **The 102 do not ship with an index.** They can flag and show receipts against material the
   author supplies; they cannot carry a number, because nothing has ever established that they
   detect anything in text nobody chose for them.
3. **PTC is the benchmark from now on.** It is externally authored, character-annotated, and
   CC-BY — so it cannot be selected-on-outcome the way our own corpora can. Every cue change
   gets measured against it, both directions, before it lands.
4. **Two anti-predictive candidates need more firings, not a verdict.** `declined-to-comment` is
   standard journalism boilerplate and almost certainly a false-positive generator; the way to
   retire it honestly is a larger sample, not this one.

## Reproduce

```bash
python eval/detection_census.py            # ranked, with intervals
python eval/detection_census.py --markdown # the table above
python eval/ptc_precision.py               # the August lens-level run
```

Writes `eval/detection-census.json` — every detection with hits, in-span, lift and interval,
including the 102 zeros, so the next run can be diffed against this one.
