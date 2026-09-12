# Instance mode, and the cut criterion was measuring the wrong thing

Two results, both on PTC (371 external news articles, human character-span annotation).
Neither is measured on any manuscript.

## 1. The verifier needed a subject, and with one it works

`eval/RESULTS-2026-08-26-verify-stage.md` established that running verify in **author
mode** — *is the document's author employing this method?* — rejected almost everything on
news, because a news author is a reporter quoting someone else, so "attributed to a third
party" is the honest answer and the hit dies. PTC's annotators marked spans wherever they
occurred, without regard to speaker.

`VERIFY_MODES` now carries a second question. **instance** mode asks: is this span an
instance of the technique as it appears, whoever produced it? Same corpus, same cues, same
model, one question changed:

| lens | cues only | author-mode verify | instance-mode verify |
|---|---:|---|---|
| `institutional_permeation` | 2.83 | 7.55 — kept 1 (6%), **1 of 6** spans | 4.53 — kept 5 (31%), **3 of 6** spans |
| `reference_capture` | 3.77 | not run | 4.31 — kept 7 (39%), 4 of 9 spans |
| `sourcing_asymmetry` | 1.12 | rejected all 27, **0 of 4** | 0.42 — kept 18 (67%), 1 of 4 |

For the two lenses PTC can judge, instance mode is a working precision layer: lift up over
the cues-only baseline while roughly half the human-annotated spans survive. Author mode
was not a broken verifier, it was the wrong question, and reading its output as a verdict
on the verifier would have retired a working component.

### `sourcing_asymmetry`'s 0.42 is a corpus mismatch, not a broken verifier

Worth stating because the first reading of this table got it wrong. The spans this lens
keeps as `genuine` are `did not immediately respond`, `refused to comment`, `esteemed`,
`acclaimed`, `highly respected` — sourcing boilerplate and honorifics. That is exactly what
the lens is built to catch and largely **not** among PTC's 18 propaganda techniques.
`ptc_precision.py`'s own docstring says a low lift here "is a floor, not a verdict", and
this is the case it was written for. PTC cannot evaluate this lens; the number measures the
mismatch.

## 2. The pre-registered restoration test — prediction wrong, cut criterion wrong

Pre-registration: `eval/PREREG-2026-08-26-label-cue-restore.md`, committed at `23948b3`
**before** the run. Four cues restored to `sourcing_asymmetry/pejorative-actor-label`:
`regime` (bg 143×), `far-right` (8×), `hardline` (7×), `extremist` (4×).

| | before restore | after restore |
|---|---:|---:|
| hits on 371 articles | 27 | **81** |
| cues-only lift | 1.12 | **1.77** |
| instance-verified lift | 0.42 | **1.68** |
| human-annotated spans retained | **1 of 4** | **12 of 19** |

Both pre-registered conditions hold — verified lift is far above the pre-restore value, and
absolute retention rose from 1 to 12, not merely as a better ratio of a smaller pool. **The
ruling is restore, and the cues stay in.**

**Prediction 2 was wrong, and that is the finding.** It said cues-only lift would FALL,
because these cues were cut for occurring freely in ordinary prose. It rose, 1.12 → 1.77.
Per-cue, on `pejorative-actor-label`:

| | cue | genuine / fired |
|---|---|---:|
| RESTORED | `far-right` | 5 / 5 |
| RESTORED | `hardline` | 4 / 4 |
| RESTORED | `extremist` | 4 / 5 |
| RESTORED | `regime` | 23 / 40 |
| survivor | `cronies` | 1 / 1 |
| survivor | `maga extremist` | **never fires** |
| survivor | `fringe group` | **never fires** |
| survivor | `fringe figure` | **never fires** |

The cut removed the only cues on this detection that work and kept three that are inert.

### Why the criterion fails

The cut ranked cues by **how often the phrase occurs in neutral background prose**. That
measures how common a phrase is. It does not measure whether, *when the phrase does appear*,
it is doing the method. `regime` is common AND frequently pejorative labelling when it
shows up; `fringe figure` is rare and never shows up at all. Frequency was standing in for
precision and, on the one detection where it has been tested directly, it is anti-correlated
with it.

### The scale of it

Counting every cue in the taxonomy against the same 371 articles:

* **621 cues** in the taxonomy
* **58 fire at least once** (9%)
* **563 never fire** (91%)
* the 34 cues the cut removed **all fired ≥3× in PTC prose by construction** — the criterion
  selected them *for* firing

So before the cut roughly 92 cues were live, and the cut deleted 34 of them: about **37% of
the working vocabulary**, while leaving 563 inert ones untouched. The instrument's problem
was never that its live cues fire too much. It is that nine cues in ten are dead, and the
repair removed a third of the ones that were not.

**Caveat, and it is a real one:** PTC is news. Many of these cues are aimed at rulemaking,
foundation reports and party programmes, where they may well fire. A cue that is silent on
news is not thereby dead — it is unmeasured. That is an argument for the target-register
corpus, not an argument that 563 cues are fine.

## What follows

1. **The four cues stay restored.** Pre-registered, both conditions met.
2. **The other 30 cuts need the same test before they are trusted**, one detection at a
   time with the same absolute-retention bar. Not a bulk restore — that would repeat the
   original error in the opposite direction, changing 30 cues on one detection's evidence.
3. **`cue_exclusivity.py`'s generic-hit-share is now uninformative on PTC and must not be
   quoted.** It reports 0% for every lens, because the cut deleted exactly the set it calls
   generic, using the same threshold (3) and the same background file. That is Goodhart, not
   improvement, and the same arithmetic means the standing gate for unpausing the
   target-register corpus ("returns when generic share is under 60%") is now satisfied
   vacuously. Treat that gate as void rather than met.
4. **The target-register corpus is the unblocked next step**, and now for a sharper reason
   than before: 91% of the vocabulary has never been measured against anything, and PTC
   cannot measure it.

## Reproduce

```bash
python tradecraft/eval/verified_precision.py --lens sourcing_asymmetry --mode instance -n 0
python tradecraft/eval/verified_precision.py --lens institutional_permeation --mode instance -n 0
```

Verdicts are cached per (lens, detection, span, window, mode, prompt version), so a re-run
after a cue edit only pays for what changed.

---

## STATUS NOTE 2026-09-07 — "the cues stay in" no longer holds

Section 2 and "What follows" item 1 describe 2026-08-26. On 2026-08-27, commit `d736288`, the
author pulled the four restored cues (`regime`, `far-right`, `hardline`, `extremist`) from
`pejorative-actor-label`, on the ground that the restore took a 4-0 right-directed cue list to
8-0 and a won test on PTC precision does not outrank the author on his own taxonomy. The
detection is back to `cronies`, `maga extremist`, `fringe group`, `fringe figure`. **The four
label cues are cut.** The measurements in this file are unchanged and still true of the run;
the ruling they produced was reversed the next day and this note is where that is recorded.
