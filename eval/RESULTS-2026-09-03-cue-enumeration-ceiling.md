# RESULTS 2026-09-03 — hand-curated cues have a measurable ceiling, and it is below detectability

Asked for real detections rather than a green build. Tried to add some, measured properly, and
they do not exist to be added this way. This file is the number behind that, because "add more
cues" is the default next move and it needs to stop being proposed.

---

## 1. The experiment: add coined slogans, validated on held-out data

`Slogans` is the technique a literal-cue engine should be *best* at — 129 externally annotated
spans, and `subculture_register/maganr-tells` is already the best detection in the taxonomy for
it (5 of its 8 in-span landings). So slogans are the fair test of enumeration.

Method, with the split fixed in advance: candidate cues read from **even**-numbered PTC article
ids only, evaluated on the **odd**-numbered held-out half (189 articles), plus a false-positive
count over `_news-control` and `_calibration-cache` (115 documents that carry no annotated
propaganda). Eight candidates, chosen to be *coined and exclusive* rather than generic, and
spread across registers the lens already covers so nothing drifts one-sided: `smash the state`
(revolutionary left), `no king but king jesus` and `rebellion/resistance to tyrants is obedience
to god` (Christian nationalist), `stopthesynod` (tradcath), `we are hamas` (jihadist militant),
`free iran`, `hungary first`.

| | result |
|---|---|
| held-out hits, all eight cues | **2** across 189 articles |
| of those, inside a `Slogans` span | **1** |
| false positives on the control corpora | **3** (`we are hamas`, `free iran`, `stopthesynod`) |

**False positives outnumber true positives.** Not one of the eight is worth adding, and the
candidate list was not weak — every one is a real slogan taken from human-annotated gold.

## 2. Why, and it is structural rather than bad luck

The existing cue set, measured against the same 371 articles:

| `subculture_register` | count |
|---|---:|
| cues in the lens | 171 |
| **cues that never appear in 371 articles** | **166 (97%)** |
| cues appearing in exactly 1 document | 3 |
| **cues appearing in ≥5 documents** | **1** |

The whole distribution is `drain the swamp` (6 documents), `make america great again` (4), then
three cues at 1 and a 97% tail of zeros. **The taxonomy's best detection — lift 5.49, the one
result worth building on — rests on two cues.** The other 169 contribute nothing measurable
here.

Now put that next to the resolution object measured the same day
(`RESULTS-2026-09-03-background-rates.md`). A lens needs a firing rate of roughly **0.08 to
0.12** at a 100-document subject corpus before anything it says is resolvable against its own
background. A cue appearing in 1 of 371 documents fires at **0.003**. That is two orders of
magnitude below detectability, and no amount of curation changes the exponent: coined idioms are
Zipf-distributed, so each additional cue buys an ever-smaller slice of an already-thin tail
while carrying its own false-positive risk. The two measurements are the same statement from
opposite ends — one says what resolution requires, the other says what enumeration delivers.

This is the quantitative form of an argument `embed_find.py`'s own docstring already made in
prose: *"a keyword list can only ever contain what its author thought to type. It is a property
of the representation."* It was right, and now it has a number.

## 3. One caveat that makes the ceiling firmer, not softer

`eval/compare_find_stages.py` records that **PTC is exhausted as a tuning corpus for the cue
stage** — the 2026-08-26 cut was made against a PTC-derived background, so cue numbers measured
on PTC are partly self-fulfilling. The three above-chance detections were therefore selected, in
part, against the corpus that now scores them. That does not void them (the lift intervals
exclude chance, and `drain the swamp` is plainly a real slogan), but it means **3 of 140 is
closer to a ceiling than to a floor**, and a fresh externally-annotated corpus would more likely
lower it than raise it.

## 4. What this leaves, stated as options rather than a recommendation

The find stage is where the detector is failing, and there are exactly three candidates. Two are
now measured:

| find stage | status |
|---|---|
| hand-curated cues | **ceiling reached.** 3 of 140 detections above chance; 97% of cues never fire; additions fail on held-out data |
| embeddings (`embed_find.py`) | **measured at chance**, 2026-08-27, and the metric that first said 5× better was measuring span length |
| **LLM find stage** (`detect.py`'s anthropic / local backend) | **NEVER MEASURED against PTC.** `compare_find_stages.py` compares cues vs embeddings only |

So the honest position is that the detector has one untested lever left, and it is the one the
Appeal_to_Authority and Whataboutism disproofs independently pointed at: relational and
content-borrowing moves need something that reads the passage, not something that matches a
string. `detect.py` already has the backend and the local abliterated model runs on the 4090 at
no API cost, so the experiment is cheap; extending `compare_find_stages.py` to a third arm is
the shape of it.

The alternative, which is not a failure, is to ship what is measured: three detections that
work, twelve lenses with honest background rates, and receipts rather than an index. CP4b made
that a real option — but it should be chosen knowingly rather than arrived at by adding cues
until the backlog runs out.
