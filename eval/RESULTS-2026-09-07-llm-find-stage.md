# The LLM find stage on PTC — lens by lens, against the pre-registration

**Pre-registration:** `PREREG-2026-09-07-llm-find-stage.md`, committed at `76a98d1` before the first
full-lens run. **Rig:** `eval/llm_find_stage.py`; model `huihui_ai/qwen2.5-abliterate:14b` (local,
Q4_K_M), the shipped find prompt unchanged (hash in each cache record), 371 PTC articles, the
length-matched permutation null, Wilson 95%, judgeable at ≥ 5 locatable hits. Every number below
recomputes from `eval/cache/llm-find__*.jsonl` with `python eval/llm_find_stage.py --report`.

**Coverage: 15 of 15 lenses, all at 371/371 articles, 0 errors, all at the current taxonomy.**
Eleven ran 2026-09-07. The other four (`adept_speech`, `institutional_permeation`,
`sourcing_asymmetry`, `reference_capture`) had their taxonomies edited by the 2026-09-08 cue
repair *after* they ran — which changes the find prompt and so invalidated their caches — and
were **re-run 2026-09-11**, 3h13m on the local 14B at a measured 7.9 s/article. The earlier
estimates were both wrong in the same direction: ~45 min/lens from a partial lens, then 9.9
s/article from a five-article smoke test; the real figure over four full lenses is 7.9.

*Section 1 below is lens 1 as written on 2026-09-07 — kept verbatim, because two of its five
predictions were already scored wrong there and a prediction is only worth anything if it stays
where it was written. The completed-run analysis follows it.*

## Lens 1 — `inevitability_framing` (model-only). 371/371 articles, 0 errors.

| arm | hits | in-span | precision | length-matched chance | lift [95% CI] | mean hit chars | annotated spans recovered |
|---|---:|---:|---:|---:|---|---:|---:|
| LLM | 422 locatable (+247 unlocatable) | 211 | 0.500 | 0.354 | **1.41 [1.28, 1.55]** | 125 | **238** |
| cues | 5 | 3 | 0.600 | 0.301 | 1.99 [0.77, 2.93] | 16 | 3 |

Spans only the LLM arm recovered: 237. Articles with ≥ 1 LLM hit: 329 of 371 (89%).

| detection | hits | in-span | lift | 95% CI | verdict | PTC techniques the in-span hits landed on |
|---|---:|---:|---:|---|---|---|
| `historys-side` | 150 | 85 | 1.53 | [1.31, 1.74] | above chance, interval excludes it | Loaded_Language 37, Exaggeration/Minimisation 11, Flag-Waving 11 |
| `adapt-or-perish` | 92 | 47 | 1.38 | [1.11, 1.64] | above chance, interval excludes it | Loaded_Language 20, Appeal_to_fear-prejudice 7, Doubt 6 |
| `no-alternative` | 180 | 79 | 1.36 | [1.14, 1.59] | above chance, interval excludes it | Loaded_Language 28, Doubt 14, Exaggeration/Minimisation 10 |

### The rule, applied

**Detections demonstrated by the LLM arm: 3** (`historys-side`, `adapt-or-perish`, `no-alternative`),
each ≥ 5 firings with a lift interval whose lower bound clears 1.0. None of the three is among
the cue census's three (`penalty-without-adjudication`, `maganr-tells`,
`infiltrate-existing-institutions`). **By the pre-registered definition the detector has grown** —
and on a lens the cue stage could never judge at all: its cue arm fired 5 times on 371 articles.

**Index-track candidacy (CP2), all four bars required:**

| bar | result | holds? |
|---|---|---|
| (1) lens-level lift interval excludes 1.0 | 1.41 [1.28, 1.55] | yes |
| (2) absolute annotated-span recovery does not fall | 238 vs 3 | yes |
| (3) unlocatable-span rate below 20% | **247 of 669 = 37%** | **no** |
| (4) holds an index floor | none — model-only lenses have no cue-based floor | no |

**Ruling for this lens: the second row of the pre-registered outcome table.** *The LLM finds new
things and fabricates or misquotes others.* No routing change; the 37% is the next defect. It is
not a rounding problem: more than one quoted span in three is text the model claims to have found
in the article and that `str.find` cannot locate. Some of that will be paraphrase and whitespace
(the parse is a literal substring match); the rest is invention. Which, and in what proportion, is
the measurement that decides whether a fuzzy locator is a fix or a laundering step — and it is not
this measurement. Until it is made, an LLM hit on this lens is a lead for a human, not a receipt.

### What the numbers say beyond the rule

- **The lift is real and modest.** 1.41 with an interval that excludes 1 is a working detector;
  it is not the 4–6× the three cue detections show on their much smaller pools. The LLM arm fires
  on 89% of news articles for "inevitability framing", and half of those firings land where six
  annotators marked propaganda. The other half do not.
- **What it lands on is Loaded_Language, mostly.** PTC has no "inevitability" technique; the
  in-span hits distribute over Loaded_Language (85 of 211), Doubt, Exaggeration/Minimisation,
  Flag-Waving, Repetition, Appeal to fear. So "found something a human marked" here means
  "found rhetoric a human marked as loaded" more than "found the construct". That is consistent
  with the lens's definition — inevitability framing *is* a loaded move — and it is also the
  construct-mismatch caveat the census carries: a lens built for rulemaking and foundation
  reports, measured on news.
- **The chance rate is high because the spans are long.** Mean LLM hit 125 characters against 16
  for a cue; the length-matched null (0.354) is what keeps a 0.500 precision from reading as a
  3.8× naive lift. This is the 2026-08-27 embedding-arm lesson applied, and it is why the row
  says 1.41 and not 3.77.

### Predictions, scored so far

| # | prediction | status after lens 1 |
|---|---|---|
| 1 | LLM arm fires more often than cues on every lens | holds (422 vs 5) |
| 2 | ≥ 3 of 5 model-only lenses reach ≥ 5 locatable hits | 1 of 1 so far |
| 3 | the detector grows by **at most two** detections | **wrong already** — three on the first lens |
| 4 | unlocatable-span rate between 5% and 20% | **wrong** — 37%, above the bar |
| 5 | `sourcing_asymmetry` shows the highest LLM lift of the cue lenses | not yet run |

Two predictions wrong in opposite directions after one lens: the arm finds more than I expected
and fabricates more than I expected. Both are the finding.

## The completed run — 15 of 15, and the cache invalidation that made it two runs

All 15 pre-registered lenses now stand at 371/371 articles, 0 errors, at the current taxonomy.
Getting there took two sittings, and the reason is worth keeping.

`llm_find_stage.py` keys its cache on `prompt_hash` — a SHA of the system prompt plus the user
prompt built from the lens taxonomy. `build_user_prompt` (`detect.py:108`) writes each detection's
**cue list into the prompt the model sees**. So editing a lens's cues edits the find prompt, and
the rig then refuses to read that lens's cached answers, because they were produced by a different
instrument.

On 2026-09-08 the pre-registered cue repair (`5ea88afa`) and the shoptalk-corpus recheck
(`a013b548`) did exactly that, correctly, to four lenses: `adept_speech` (cut `you haven`, a prefix
of *haven't*), `institutional_permeation` (excluded `existential risk` / `existential crisis`),
`sourcing_asymmetry` and `reference_capture`. Their 2026-09-07 results were orphaned by a repair to
the instrument that produced them. That is the cache doing its job, and the invalidation was not
worked around: a lift computed against one cue list is not comparable to one computed against
another. The four were **re-run from scratch on 2026-09-11**.

### Per-lens, from the committed caches

| lens | model-only | articles | LLM hits | in-span | LLM lift [95% CI] | cues hits | cues lift [95% CI] | spans recovered LLM / cues / LLM-only | unlocatable | detections demonstrated (LLM) | LLM verdict |
|---|---|---:|---:|---:|---|---:|---|---|---:|---:|---|
| `inevitability_framing` | yes | 371/371 | 422 | 211 | 1.41 [1.28, 1.55] | 5 | 1.99 [0.77, 2.93] | 238 / 3 / 237 | 247 (37%) | 3 | above chance, interval excludes it |
| `distributed_accountability` | yes | 371/371 | 455 | 166 | 0.98 [0.86, 1.10] | 2 | 0.00 [0.00, 2.09] | 203 / 0 / 203 | 237 (34%) | 1 | interval spans chance |
| `cognitive_capture` | yes | 371/371 | 356 | 153 | 1.29 [1.14, 1.45] | 0 | – | 193 / 0 / 193 | 119 (25%) | 2 | above chance, interval excludes it |
| `counterproductivity` | yes | 371/371 | 427 | 197 | 1.24 [1.11, 1.37] | 0 | – | 240 / 0 / 240 | 166 (28%) | 3 | above chance, interval excludes it |
| `legibility` | yes | 371/371 | 656 | 233 | 1.01 [0.91, 1.12] | 2 | 0.00 [0.00, 13.15] | 288 / 0 / 288 | 293 (31%) | 1 | interval spans chance |
| `narrative_management` | no | 371/371 | 518 | 199 | 1.16 [1.03, 1.28] | 4 | 1.68 [0.31, 4.70] | 243 / 1 / 242 | 225 (30%) | 2 | above chance, interval excludes it |
| `militant_mobilization` | no | 371/371 | 632 | 336 | 1.55 [1.44, 1.67] | 4 | 2.40 [0.96, 3.05] | 367 / 3 / 367 | 593 (48%) | 6 | above chance, interval excludes it |
| `rollback_asymmetry` | no | 371/371 | 85 | 27 | 1.28 [0.92, 1.70] | 3 | 3.17 [0.59, 7.55] | 33 / 1 / 32 | 92 (52%) | 1 | interval spans chance |
| **`adept_speech`** | no | 371/371 | 230 | 116 | **1.46 [1.27, 1.64]** | 1 | 0.00 [0.00, 39.67] | 127 / 0 / 127 | 149 (39%) | 1 | above chance, interval excludes it |
| `costly_signal` | no | 371/371 | 545 | 206 | 1.13 [1.01, 1.25] | 0 | – | 251 / 0 / 251 | 252 (32%) | 1 | above chance, interval excludes it |
| `network_brokerage` | no | 371/371 | 0 | 0 | – | 0 | – | 0 / 0 / 0 | 0 (–) | 0 | untestable on PTC (fewer than 5 locatable hits) |
| **`institutional_permeation`** | no | 371/371 | 585 | 197 | **0.94 [0.84, 1.05]** | 15 | **2.04 [1.08, 3.05]** | 233 / 6 / 231 | 243 (29%) | 2 | interval spans chance |
| **`sourcing_asymmetry`** | no | 371/371 | 203 | 77 | **1.02 [0.85, 1.21]** | 31 | 0.58 [0.20, 1.50] | 92 / 3 / 92 | 89 (30%) | 0 | interval spans chance |
| **`reference_capture`** | no | 371/371 | 325 | 124 | **1.11 [0.96, 1.27]** | 18 | **3.59 [2.09, 5.10]** | 147 / 9 / 144 | 173 (35%) | 2 | interval spans chance |
| `subculture_register` | no | 371/371 | 140 | 64 | 1.77 [1.46, 2.09] | 14 | 3.06 [1.75, 4.22] | 62 / 8 / 59 | 332 (70%) | 3 | above chance, interval excludes it |

Bold rows are the four re-run on 2026-09-11. Regenerate with
`python tradecraft/eval/llm_find_stage.py --report --markdown`; the per-detection table (75 rows)
prints below it and is not duplicated here.

## The rule, applied to the whole run

**Detections demonstrated by the LLM arm: 28**, against the cue census's 3. Eight of the fifteen
lenses clear chance with an interval that excludes it, six span it, one is untestable.

**By the pre-registered definition the detector has grown, and not marginally.** Five lenses are
**model-only** — the cue stage could never judge them at all — and four of those five now carry at
least one demonstrated detection. `cognitive_capture` and `counterproductivity` fired **zero cues
on 371 articles** and demonstrate 2 and 3 respectively. That is the whole case for the LLM find
stage, measured rather than argued.

And it arrives with the same defect it arrived with on lens 1, corpus-wide:

**The unlocatable-span rate is 36.5%** — 3,210 of 8,789 quoted spans are text the model says it
found in the article and that `str.find` cannot locate. Every measured lens fails CP2 bar (3)
(<20%). It is not concentrated in the weak lenses, which would have been the comfortable result:
`subculture_register` has the **highest lift in the run (1.77) and the worst fabrication rate
(70%)**, and `militant_mobilization` pairs the second-highest lift (1.55) with 48%. The lenses the
model is surest about are the ones it most often quotes text that is not there. `cognitive_capture`
(1.29 at 25%) is the counter-example that keeps it from being a law.

### What the four repaired lenses added, which was not more of the same

The re-run did not simply extend the pattern. **Three of the four have a WEAK LLM arm** — 0.94,
1.02, 1.11, all spanning chance — where the 2026-09-07 eleven averaged well clear of it. Only
`adept_speech` (1.46) joins the above-chance set.

And on two of them the arms **invert**: the cue arm beats the LLM arm and clears chance, which
happens exactly once in the other eleven.

| lens | LLM lift | cues lift | reading |
|---|---|---|---|
| `reference_capture` | 1.11 [0.96, 1.27] | **3.59 [2.09, 5.10]** | highest cue lift in the run; 18 cue hits recover 9 annotated spans |
| `institutional_permeation` | 0.94 [0.84, 1.05] | **2.04 [1.08, 3.05]** | 585 LLM firings produce no signal at all |
| `sourcing_asymmetry` | 1.02 [0.85, 1.21] | 0.58 [0.20, 1.50] | neither arm works; 0 detections |
| `adept_speech` | **1.46 [1.27, 1.64]** | 0.00 [0.00, 39.67] | cue arm collapsed to a single hit |

Cue arms clearing chance: **2 of these 4, against 1 of the other 11.** The obvious story is that
the cue repair worked — cut the false-positive cues and what remains is precise. **Do not publish
that as a finding.** These four are not a sample; they were selected for repair *because* their
cues were suspect, so a post-repair precision gain on exactly them is what selection alone
predicts. It is a hypothesis the next pre-registration can test on lenses that were not repaired,
and nothing more.

`adept_speech` is the cleanest single result of the re-run and it cuts the other way. Its entire
cue showing before the repair was the cue `you haven` firing inside *haven't* — the collateral
evaluation caught that, the repair cut it, and the cue arm now fires **once in 371 articles with
zero in-span**. The lens survives on the LLM arm alone. A cue that fires on a contraction was never
detecting the construct; removing it did not weaken the detector, it stopped the detector lying
about what it had found.

### The ruling, unchanged

Second row of the pre-registered outcome table: *the LLM finds new things and fabricates or
misquotes others.* **No routing change. No lens state changed. Nothing in `floors.json`, the
taxonomy or any threshold is touched by this file.** An LLM hit remains a lead for a human, not a
receipt.

The next measurement is the one lens 1 named and the completed run makes unavoidable: classify the
3,210 unlocatable spans as whitespace/paraphrase versus invention, on a seeded hand-read,
**before** any fuzzy locator is written. A locator that turns 36.5% into 5% by loosening the match
is laundering, not a fix, and the lift/fabrication correlation above is the reason to expect it
would flatter the highest-lift lenses most.

### Predictions, scored — four of five wrong

| # | prediction | result |
|---|---|---|
| 1 | LLM arm fires more often than cues on every lens | **holds** on 14 of 15; `network_brokerage` fires 0 in both arms (a network lens with no text cues — the tie is the correct outcome, not a miss) |
| 2 | ≥ 3 of 5 model-only lenses reach ≥ 5 locatable hits | **holds** — all 5 did |
| 3 | the detector grows by **at most two** detections | **wrong, by an order of magnitude** — 28 |
| 4 | unlocatable-span rate between 5% and 20% | **wrong** — 36.5% corpus-wide, and every lens is above the bar |
| 5 | `sourcing_asymmetry` shows the highest LLM lift of the cue lenses | **wrong** — 1.02, near the bottom. The highest cue-lens LLM lifts are `subculture_register` 1.77, `militant_mobilization` 1.55, `adept_speech` 1.46. This was recorded as *unscorable* while the lens sat invalidated; the re-run made it scorable, and it fails. |

Four of five wrong, in both directions: the arm finds far more than expected, fabricates far more
than expected, and the lens predicted to lead the cue-lens field is last but one. Prediction 5 is
the one worth sitting with — it was an expert guess about which construct a language model would
find easiest, made by someone who had read every lens, and it was not close. That is the argument
for pre-registering rather than reporting impressions after the fact.

## What this changes, and what it does not

- **Nothing in `floors.json`, `floors_contract.py` or the instrument export changes.** A state
  change is a reviewed edit citing this file; CP2 (which lenses may ever print a public index) is
  the author's call, and bar (3) fails here regardless.
- `eval/run_eval.py cues --strict` and `tools/test_engine_parity.py` are unaffected by design (no
  taxonomy change made here) — re-run after the run completed: unchanged.
- The pipeline's LLM find stage stays where it was: available, not routed. The next measurement
  is the unlocatable spans: classify the **2,556** as whitespace/paraphrase vs invention, on a
  seeded hand-read, before any locator is loosened to "fix" them.
- **Owed, and not done here:** the four invalidated lenses, ~4.1 h on the local 14B. Until they
  run, any corpus-level figure in this file is over 11 lenses and says so; none of them is a
  15-lens number.

## Reproduce

The per-lens cache under `eval/cache/` is the artifact this file recomputes from.
`eval/cache/` is gitignored (the verify-stage cache `ptc-verdicts.json` there is NOT tracked),
so each completed lens's `llm-find__*.jsonl` is force-added as it completes — the commit for
lens 1 described that as following a precedent; there was none, this is the first.

```bash
python tradecraft/eval/llm_find_stage.py --report --markdown      # from the committed cache
python tradecraft/eval/llm_find_stage.py --lens inevitability_framing   # re-run (temperature 0.2: a replication, not a repeat)
```
