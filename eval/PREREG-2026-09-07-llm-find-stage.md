# Pre-registration: does the LLM find stage grow the detector past three detections?

Written and committed **before** the first full-lens run. Committed at the hash recorded in
`RESULTS-2026-09-07-llm-find-stage.md` when the results are written; the results file will
name it. A rule that can be adjusted after seeing the number is not a rule.

## The question

Three of 140 detections are demonstrated above chance on PTC by the cue stage
(`RESULTS-2026-09-03-detection-census.md`); 102 never fire; the cue vocabulary is at a
measured ceiling (97% of one lens's cues never appear in the corpus,
`RESULTS-2026-09-03-cue-enumeration-ceiling.md`). The embedding find stage measured at chance
(`RESULTS-2026-08-27-embedding-find-stage.md`). The barometer plan names the remaining
measurement: **the LLM find stage, run at scale on PTC on the local 14B** — the one find stage
never put on this benchmark for more than a handful of articles.

The rig is `eval/llm_find_stage.py`, which reuses the census's statistic and machinery
(`ptc_precision.load_corpus` / `covered`, `compare_find_stages.chance_for`,
`detection_census.wilson` / `load_techniques` / `JUDGEABLE_HITS`) and adds a per-article cache
so the run resumes and the results recompute from the cache. Smoke-tested on 3 articles before
this file was written (rig runs, spans locate, 9.5 s/article); nothing else has been run.

## What is fixed

| parameter | value | why |
|---|---|---|
| corpus | PTC train split, all **371** articles, 5,468 task-1 spans, task-2 technique labels for attribution | the census's corpus; no subsampling except by lens |
| model | `huihui_ai/qwen2.5-abliterate:14b` (`tradecraft.local_llm.LOCAL_MODEL`, Q4_K_M, local ollama) | the detector's shipped default local backend; the plan's "local 14B" |
| prompt | `detect.build_user_prompt` + `detect._system`, **unchanged**; cache keyed on their hash | a prompt change invalidates the cache for that lens rather than mixing answers |
| decoding | `local_llm.local` defaults: temperature 0.2, `num_predict` 1500, JSON mode | the shipped defaults. Not deterministic — a fresh run varies. The RESULTS file reproduces from the committed cache; a replication is a second run reported beside it, not a substitute |
| offsets | `detect._parse_hits`: `text.find(span)`; a quoted span not present in the text is **counted as unlocatable**, never dropped silently | the model's fabrication rate is a result, not noise |
| null | the length-matched permutation null (`chance_for`, 200 draws, seed 20260907) | a 300-char LLM span overlaps an annotation by luck far more often than a 10-char cue; the character-rate null flattered the embedding arm 5x on 2026-08-27 |
| interval | Wilson 95% on in-span precision, divided by the mean length-matched chance -> lift CI | the census's interval, so rows are comparable |
| judgeable | `JUDGEABLE_HITS = 5` locatable firings | the census's threshold, unchanged |
| baseline | the **cue arm on the same articles**, same statistic | lift is read against the floor that exists |
| lens order | model-only first (`inevitability_framing`, `distributed_accountability`, `cognitive_capture`, `counterproductivity`, `legibility`), then receipts-only cue lenses (`narrative_management`, `militant_mobilization`, `rollback_asymmetry`, `adept_speech`, `costly_signal`, `network_brokerage`), then the index-bearing five (`institutional_permeation`, `sourcing_asymmetry`, `reference_capture`, `subculture_register`) | the LLM find stage is the ONLY find stage the model-only lenses can have, so they decide most; the index-bearing lenses already have a working cue floor |
| excluded | `revolving_door` | graph lens; no text markers |
| runtime | ~1 h/lens; run in lens order until stopped; **partial coverage is reported as partial** | 15 lenses is ~15 h of GPU time. A lens not yet run is "not run", never "no result" |

Nothing is re-tuned. No cue, weight, threshold, prompt or taxonomy changes between this file
and the results. If the run surfaces a rig defect (a crash, a parse failure rate), the defect is
fixed and named in the results, and the affected lens is re-run from an empty cache.

## The rule — what would count as the detector growing

Three levels, each with its own bar. All three are computed by the script; none is applied by it.

### A detection is demonstrated by the LLM arm iff

1. it has **≥ 5 locatable LLM firings** on the 371 articles (judgeable), and
2. the **lower bound of its Wilson-95% lift interval exceeds 1.0** (above chance, interval
   excludes it).

Same two conditions as the cue census. A detection with 4 firings at 100% precision is not
demonstrated; it is too thin to judge, exactly as it would be for the cue stage.

### The detector has grown iff

the set of detections demonstrated by the LLM arm contains **at least one detection the cue
census did not demonstrate** (i.e. outside `penalty-without-adjudication`, `maganr-tells`,
`infiltrate-existing-institutions`). Count reported as "detections demonstrated, new to the
LLM arm". Re-demonstrating the same three is confirmation, not growth.

### A lens is a candidate for the index track (CP2) only iff ALL of

1. its lens-level LLM lift interval excludes 1.0 on PTC (lower bound > 1);
2. **absolute annotated-span recovery does not fall**: distinct annotated spans overlapped by
   the LLM arm ≥ those overlapped by the cue arm on the same articles. A higher precision on a
   smaller pool is the 2026-08-26 trap and does not qualify;
3. its unlocatable-span rate is **below 20%** — a find stage that quotes text not in the
   document one time in five is manufacturing receipts, and no lift statistic on the locatable
   four-fifths repairs that;
4. it already holds an index floor from `eval/lens_floor.py` (the `index` state in
   `floors.json`), or acquires one by the existing procedure.

This measurement can supply (1)–(3). It changes **nothing** in `floors.json`,
`floors_contract.py` or the instrument export: a lens moving from receipts-only to
index-bearing is a separate reviewed edit citing the RESULTS file, and **which lenses may ever
print a public index is CP2 — the author's call**, not this script's.

### What each outcome means

| outcome | ruling |
|---|---|
| ≥ 1 new detection demonstrated, on a lens meeting (1)–(3) | The find stage is the bottleneck, not the taxonomy. Route that lens through the LLM find stage in the pipeline; propose it under CP2. |
| ≥ 1 new detection demonstrated, lens fails (2) or (3) | The LLM finds new things and loses or fabricates others. Report both; no routing change; the fabrication or recall loss is the next defect to fix. |
| lenses judgeable, no new detection demonstrated | The three are the detector's ceiling **on news**. The register argument (PTC is news; the taxonomy targets rulemaking, foundation reports, party programmes) stands as the open question and the target-register corpus is the next measurement, not another find stage. |
| a model-only lens has < 5 locatable hits on 371 articles | **Untestable on PTC**, not failed. The corpus contains too little of what the lens detects to judge it; stated as such. |
| lens-level lift interval upper bound < 1.0 | Anti-predictive on news: the LLM arm fires where humans did not mark. That is evidence against the lens's construct on this register, or against the prompt; either way it does not enter the pipeline. |

## Predictions (falsifiable, written before the run)

1. The LLM arm fires **more often than the cue arm on every lens** run (the 3-article smoke
   showed 7 LLM hits to 0 cue hits on `institutional_permeation`; I expect that shape to hold).
2. **At least three of the five model-only lenses produce ≥ 5 locatable hits** and are
   therefore judgeable on PTC for the first time.
3. **The detector grows by at most two detections.** I expect a modest positive — one or two
   detections new to the LLM arm demonstrated, most likely on `institutional_permeation` and
   `sourcing_asymmetry` — and not a transformation. If the LLM arm demonstrates five or more
   new detections, I was wrong in the useful direction and the register argument weakens.
4. The **unlocatable-span rate is between 5% and 20%** on a 14B at temperature 0.2. Below 5%
   would be better than I expect of quoted spans from a small model; above 20% fails bar (3).
5. `sourcing_asymmetry` will show the **highest LLM lift** of the cue lenses, because its
   construct (attributed vs asserted labels, honorifics, "declined to comment") is contextual
   and exactly what the cue floor could not separate — the same reasoning that motivated
   instance-mode verify on 2026-08-26.

## Constraints on the report

- Every lens run is reported, including nulls and untestables, in one table, with the cue arm
  beside it. A lens not reached is listed as **not run**.
- The per-detection table lists every judgeable detection, not only the demonstrated ones.
- Technique attribution (PTC task-2) is reported for in-span hits so "landed in an annotation"
  can be read as "caught *this* named technique" or "landed on something else".
- `eval/run_eval.py cues --strict` and `tools/test_engine_parity.py` are unaffected by design
  (no taxonomy change) and are re-run to prove it.
- If the result is a null, **this file stays** and the null is written up. A negative result
  that gets deleted gets re-attempted every six months.
