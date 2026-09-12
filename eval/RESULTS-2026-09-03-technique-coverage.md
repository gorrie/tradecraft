# RESULTS 2026-09-03 — what the detector catches, in someone else's vocabulary

PTC's task-2 technique-classification labels are now read by `eval/detection_census.py`. They
were vendored and unused: 6,129 spans typed with one of fourteen human-named propaganda
techniques, against task-1's 5,468 untyped spans (task-1 merges spans carrying overlapping
techniques, so the typed count is higher).

    python eval/detection_census.py --techniques    # per-technique coverage
    python eval/detection_census.py                 # the per-detection census, unchanged

This turns "our detection landed in some annotated span" into "our detection catches *this*
technique six professional annotators named." Both directions are measured, because they
answer different questions and only one of them was previously askable.

---

## 1. Which techniques the detector reaches

Counted over **spans**, not hits: two detections landing on one annotated span is one technique
instance caught, not two. Counting hits would let a heavily-cued technique report coverage above
100%.

| technique | spans | caught | coverage | best detection |
|---|---:|---:|---:|---|
| `Loaded_Language` | 2123 | 8 | 0.4% | `militant_mobilization/reframe-target-as-vermin-or-nazi` (2) |
| `Name_Calling,Labeling` | 1058 | 8 | 0.8% | `reference_capture/penalty-without-adjudication` (3) |
| `Repetition` | 621 | 4 | 0.6% | `inevitability_framing/no-alternative` (3) |
| `Doubt` | 493 | 4 | 0.8% | `adept_speech/candidate-sorting` (1) |
| `Exaggeration,Minimisation` | 466 | 1 | 0.2% | `reference_capture/elastic-charge` (1) |
| `Appeal_to_fear-prejudice` | 294 | 6 | 2.0% | `subculture_register/maganr-tells` (2) |
| `Flag-Waving` | 229 | 0 | **0.0%** | — |
| `Causal_Oversimplification` | 209 | 1 | 0.5% | `sourcing_asymmetry/unsourced-assertion` (1) |
| `Appeal_to_Authority` | 144 | 0 | **0.0%** | — |
| `Slogans` | 129 | 5 | 3.9% | `subculture_register/maganr-tells` (5) |
| `Whataboutism,Straw_Men,Red_Herring` | 108 | 0 | **0.0%** | — |
| `Black-and-White_Fallacy` | 107 | 1 | 0.9% | `institutional_permeation/irreversibility-framing` (1) |
| `Thought-terminating_Cliches` | 76 | 1 | 1.3% | `institutional_permeation/irreversibility-framing` (1) |
| `Bandwagon,Reductio_ad_hitlerum` | 72 | 1 | 1.4% | `reference_capture/penalty-without-adjudication` (1) |

Coverage runs from 0.0% to 3.9%. Across 140 detections the whole taxonomy reaches roughly forty
of 6,129 typed spans, and **only 19 of the 140 detections ever land on a typed span at all.**

That number should be read with the construct difference in front of it, not behind it: PTC
annotates *rhetorical propaganda technique in news articles*, and this taxonomy detects
*institutional tradecraft* — a stated strategy of entering institutions, a penalty imposed
without a hearing, an asymmetric sourcing pattern. Low coverage of `Loaded_Language` is mostly
the two constructs failing to be the same construct, and a detector that scored highly on
loaded language would arguably be mis-specified for this project's stated purpose. The census
is a measurement against an external gold standard, not a scoreboard this taxonomy was built
to win.

## 2. The three gaps that are inside our own declared domain

Three techniques have zero coverage. One is plausibly outside scope; **two are not, and they
are the concrete build targets this measurement produces:**

- **`Appeal_to_Authority`, 144 annotated spans, zero caught.** This sits squarely inside what
  `reference_capture` and `sourcing_asymmetry` claim to detect — who is permitted to settle a
  question by being cited. A capture detector that catches none of 144 human-annotated appeals
  to authority has a documented hole, in the one place it should be strongest.
- **`Whataboutism,Straw_Men,Red_Herring`, 108 spans, zero caught.** This is
  `narrative_management` territory — redirecting a charge rather than answering it.
- `Flag-Waving`, 229 spans, zero caught. Nationalist appeal is adjacent to
  `militant_mobilization` but is not itself an institutional move; leaving this uncovered is
  defensible, and should be a stated scope decision rather than an accident.

The value of a zero here is that it is a *documented* gap rather than an unknown, with 144
externally annotated positives to build against and to measure both directions of any cue
change. That is the check the plan's risk 5 asked for and did not have.

### ADDENDUM, same day — both "build targets" were probed, and both are DISPROVEN for the cue engine

The paragraph above called those two gaps buildable. **Measured hours later, they are not** — not
with a literal-cue detector — and the claim is corrected here rather than left standing. Method:
candidate cues written from the **even**-numbered article ids only and evaluated on the
**odd**-numbered held-out half (189 articles, 79 `Appeal_to_Authority` spans), plus a
false-positive count over the untouched `_news-control` and `_calibration-cache` corpora.

**`Appeal_to_Authority` — 18 candidate credential-attribution cues** (*the political scientist*,
*according to church expert*, *professor of*, *the author of*, *is said to be*, *to quote*, …):

| measure | result |
|---|---|
| held-out precision (landings inside an AtA span) | **16.0%** — 4 of 25 hits, against a 13.25% chance rate |
| held-out recall | **4 of 79 spans (5.1%)** |
| false positives on news control | **23 of 95 documents, 30 hits** — a 0.24 background rate |

That is a non-detection with a background worse than `sourcing_asymmetry`, our noisiest lens.
It would have degraded whichever lens received it. It is not proposed and must not be added.

**Why it cannot work, and this is the mechanically useful part:** PTC annotates the *borrowed
claim*, not the attribution. The spans read *"the epidemic could still worsen"*, *"the crisis in
Madagascar had yet to peak"* — the content asserted on someone's authority. The detectable
signal, the attribution, sits **outside** the span, so a character-overlap census cannot credit
it even given a perfect attribution detector. A proximity rule does not rescue this either: an
attribution verb (*according to*, *said*, *told*, *explains*, *argues*, *recommends*) appears
inside the span for 16% of spans and within 300 characters before it for only 27% — and a
300-character window is itself near chance.

**`Whataboutism,Straw_Men,Red_Herring`** fails for a different reason, found by inspection of
its derive-half spans: the class is heterogeneous and several spans are single words (*"white"*,
*"a Democrat"*, *"Democratic"*), artifacts of three techniques merged into one label. The move
itself is discourse-relational — raising a different matter to deflect the one at hand — so
identifying it requires knowing what argument is being deflected. No literal phrase carries that.

**The corrected conclusion.** These two are not cue-engine gaps to be closed with better cues;
they are **limits of literal-substring matching against relational and content-borrowing
techniques**. `detect.py` already has the backend that could reach them — the anthropic/local
LLM path — and that, not a cue list, is the honest route if either is ever wanted. Recorded at
this length so nobody spends a second attempt on the cue route, which is what this project does
with a disproof.

`Flag-Waving` remains unprobed and is still the scope decision described above.

## 3. What the working detections actually are

The three detections whose lift interval excludes chance, now named in PTC's vocabulary.
`concentration` is the share of a detection's typed landings sitting on its single commonest
technique — near 1.0 means the detection is really a detector for that one technique, whatever
its marker calls it.

| detection | hits | in-span | lift | techniques landed on | conc. |
|---|---:|---:|---:|---|---:|
| `reference_capture/penalty-without-adjudication` | 6 | 5 | 6.29 | Name_Calling,Labeling ×3 · Bandwagon ×1 · Loaded_Language ×1 | 0.60 |
| `subculture_register/maganr-tells` | 11 | 8 | 5.49 | **Slogans ×5** · Appeal_to_fear-prejudice ×2 · Name_Calling ×1 · Doubt ×1 · Repetition ×1 | 0.50 |
| `institutional_permeation/infiltrate-existing-institutions` | 5 | 3 | 4.53 | Appeal_to_fear-prejudice ×1 · Loaded_Language ×1 · Doubt ×1 | 0.33 |

Three readings worth keeping:

**`maganr-tells` is, in external terms, a slogan detector.** Five of its eight in-span landings
are `Slogans`, and it is the single best detection for that technique in the whole taxonomy —
3.9% coverage, the highest figure in the table. That is a coherent thing for a subcultural
register lens to be, and it is a more precise description than "subculture register" was.

**`penalty-without-adjudication` catches labeling.** Name_Calling,Labeling ×3 of 5. Also
coherent: the move it names is a sanction applied by designation, and designation is what
annotators mark as labeling. The construct survives contact with an outside vocabulary.

**`infiltrate-existing-institutions` concentrates on nothing** — 0.33, one landing each across
three techniques. Its lift is real, and PTC has no technique for "stated strategy of entering
institutions," so the spread is what a genuinely non-rhetorical detection looks like when
scored against a rhetorical taxonomy. This is the one of the three whose value the census can
confirm but cannot characterise, and that is a fact about PTC rather than about the detection.

## 4. One inconsistency fixed while wiring this

The census table flagged `<== works` on any lift ≥ 1.5 while the summary three lines below
applied the project's actual CI rule. So `sourcing_asymmetry/unsourced-assertion` printed
"works" on a lift of 1.51 whose interval is [0.27, 4.71], and the summary simultaneously and
correctly counted it undecided. One fact, two copies, disagreeing inside a single output. The
rule now has one implementation that both readers call, and the table shows exactly the three
`works` the summary counts.

## 5. What this does not claim

Nothing here retires a detection. A zero on a detection that never fired is a statement about
this corpus; a low lift on a detection that fires is evidence about the detection. The 102
never-fired detections remain unjudged rather than condemned — `costly_signal` and `adept_speech`
are not about news register at all, which the background-rate measurement of the same date
covers from the other side.

What has changed is that PTC is now the benchmark it was vendored to be: every cue change can be
measured against 6,129 externally typed spans in both directions before it lands. The first two
things measured through it were the two gaps this file initially called buildable, and the
benchmark refused them both within the hour — 16% precision and a 0.24 background on the one,
an unstateable construct on the other. A benchmark whose first act is to kill the proposal its
own author wrote from it is a benchmark doing its job.
