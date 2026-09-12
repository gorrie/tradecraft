# The embedding find stage does not work, and the metric that said it did was broken

Built the replacement find stage the architecture review recommended, measured it against
the cue stage on PTC, and it is at chance. Reported as a negative result because it is one.

The more useful finding is the second one: **the first version of the measurement said the
embedding stage was 5× better, and that number was an artifact of span length.**

## What was built

`tradecraft/embed_find.py`. A find stage with no vocabulary at all:

* **287 anchors** — every one of the taxonomy's 130 detection `definition` strings plus its
  157 sourced `gold` exemplars (Webb's actual words, Lippmann's actual phrase), embedded
  once with `intfloat/multilingual-e5-small` and committed.
* Documents are cut into overlapping sentence windows; a detection fires when a window's
  cosine similarity to one of its anchors clears that detection's threshold.
* **Thresholds are calibrated, never authored** — the 99.5th percentile of the similarity
  distribution over a neutral control corpus. Nobody types a number, and the control corpus
  carries no labels, so there is nothing to optimise toward.
* Returns `DetectionHit` objects, so it drops into the existing grader and verifier
  unchanged. The point was to replace the find stage, not the pipeline.

Multilingual on purpose: a substring list cannot go multilingual without being re-authored
per language, by someone fluent, with the same bias exposure each time.

## The metric was wrong first, and it flattered the new thing

`ptc_precision.py` computes chance as *the fraction of corpus characters inside some human
annotation* — 11.3%. That is correct when every hit is a literal cue eight characters wide,
which was true of every stage it had ever scored.

It is badly wrong for a stage whose hits are 350-character windows. A long span overlaps an
annotation by luck far more often than a short one, so scoring both against one
character-level rate hands the window-based stage a large free lift.

`compare_find_stages.py` replaces it with a **length-matched permutation null**: drop a span
of the *same length* at a random offset in the *same document*, 200 draws, and measure how
often that hits an annotation. Same corpus, same ground truth, honest denominator.

| | naive lift | length-matched lift |
|---|---:|---:|
| `reference_capture` (embed, 349 chars) | **5.28** | **1.16** |
| `institutional_permeation` (embed, 315 chars) | **5.13** | **1.22** |
| `sourcing_asymmetry` (embed, 305 chars) | **5.12** | **1.21** |
| `sourcing_asymmetry` (cues, 8 chars) | 3.92 | **2.86** |

The entire apparent advantage was span length. Under a fair null the embedding stage is at
chance and the cue stage still discriminates.

## Four configurations, all at chance

The obvious diagnoses were window size, then register mismatch, then anchor type. All three
were tested rather than assumed. None rescued it.

| configuration | mean hit chars | lift range |
|---|---:|---|
| 3-sentence windows, rulemaking-calibrated | ~320 | 1.16 – 1.22 |
| 1-sentence windows, rulemaking-calibrated | ~80 | 0.94 – 1.22 |
| 1-sentence windows, **news**-calibrated (register-matched) | ~70 | 0.83 – 1.38 |
| 1-sentence windows, news-calibrated, **gold-only anchors** | ~79 | 0.91 – 1.39 |

Cue stage on `sourcing_asymmetry`, for comparison, across the same runs: **2.79 – 2.95**.

A bug found on the way, and worth recording because it nearly produced a fake result: the
first "1-sentence" recalibration returned **byte-identical thresholds** to the 3-sentence
run. `windows(text, n=WINDOW_SENTENCES)` binds its default at definition time, so setting
`embed_find.WINDOW_SENTENCES = 1` from outside did nothing. Only comparing the two threshold
sets caught it. Window size is now an explicit argument.

## Why it fails — hypotheses, ranked; one tested, the rest priced

1. **A definition describes a method; text performing the method does not resemble a
   description of it.** "Change framed as inevitable, permanent, or not-to-be-reversed" and
   "the inevitable gradualness of our scheme of change" are semantically distant despite
   being about the same thing. Definition anchors may be actively harmful here.
2. ~~**Gold-only anchors were never tested separately.**~~ **TESTED AND DISCONFIRMED.**
   Dropping all 130 definitions and anchoring on the 157 sourced gold exemplars alone --
   which ARE instances of the method rather than descriptions of it -- moved lift from
   0.83–1.38 to 0.91–1.39. Unchanged. The definitions were not diluting anything, and the
   most plausible remaining explanation is hypothesis 3 or 4, neither of which is cheap.
3. **`multilingual-e5-small` is 384-dim and general-purpose retrieval.** A larger or
   domain-adapted encoder may separate what this one cannot.
4. **A control-quantile threshold selects "unusual sentences", not "sentences doing the
   method".** Being unlike routine prose is necessary and nowhere near sufficient.

**Nothing further is being chased**, and that is deliberate. Hypothesis 2 was the one cheap
test and it came back negative, so four configurations now sit at chance. Every additional
configuration tried against PTC spends the corpus, and tuning an architecture until it beats
the benchmark it is measured on is precisely how the cue stage was Goodharted in the first
place. The remaining hypotheses need a bigger encoder or a different scoring rule, and both
should be tested against a corpus that has not already been spent.

## On the mirror suite, and a defect in my own test

The embedding stage was also run against `eval/mirror-pairs.json` and came out worse than
the cues — 5 symmetric-and-firing, 3 asymmetric, 8 vacuous, versus 10 / 2 / 1.

**That comparison is not fair and should not be quoted.** The pairs are single sentences and
the thresholds were calibrated on 3-sentence windows in 3,000-word documents; a noise floor
does not transfer across text-length regimes.

It did expose a real defect in the suite: `CONTROL-nonpolitical-02` used "left-hand
proposal" versus "right-hand proposal". A substring matcher cannot see that, but a semantic
backend reads *left-hand* and *right-hand* as political direction, and duly broke the
control. **A control that leaks the signal it exists to exclude is a defect in the test, not
a finding about the detector.** Fixed to ordinals, and `mirror-pairs.json` now carries a
`control_rule` saying that a control must carry no political signal under *any* backend.

## What stands

* **The cue stage remains the only find stage measured above chance.** It is also 91% dead
  vocabulary, one-directional on the detection tested, and useless on the target register.
  Both things are true and neither cancels the other.
* **The length-matched null is the most valuable thing built here** and it is
  architecture-independent. It should be used for every future find-stage comparison, and
  `ptc_precision.py` now carries a warning that its own chance rate is only valid for short
  hits.
* The anchor set, the calibration machinery and the comparison harness all remain and are
  encoder-agnostic. Swapping in a larger model (hypothesis 3) is a one-line change against
  infrastructure that is already built and already measured — which is the only reason this
  negative result was cheap.

## Reproduce

```bash
python -c "import sys;sys.path.insert(0,'tradecraft');from tradecraft.embed_find import build_anchors;build_anchors()"
python -c "import sys;sys.path.insert(0,'tradecraft');from tradecraft.embed_find import calibrate;calibrate(n_sent=1)"
python tradecraft/eval/compare_find_stages.py --lens sourcing_asymmetry --limit 60 --window 1
```
