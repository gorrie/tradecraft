# Marker validation pass — 2026-07-31 (real-corpus cue test + false-positive audit)

**Method.** For each marker, run the deterministic `detect_cues` floor on (a) the marker's REAL
source primary [recall] and (b) benign control + adversarial/critic text that contains the marker's
generic cues [false-positive]. A marker is KEPT only if it fires on genuine hostile-actor language
AND stays quiet on benign/critic text. A cue that fires on innocent prose is disqualifying — this
tool names infiltrators/traitors, so a false positive smears an innocent. Ideology-blind throughout.

## Verdicts — the three markers added earlier on 2026-07-31 (validate-or-CUT)

| lens / marker | verdict | evidence |
|---|---|---|
| institutional_permeation / gradualism → `sequential-elimination` | **CUT** | cues "one at a time" / "piece by piece" fired on benign *"the admissions committee reviewed the applications one at a time"* and *"we shipped the fixes piece by piece"* — generic false-positive machines. "salami tactics" is a historian's label, not the actor's own language. |
| institutional_permeation / `self_regulation_preemption` | **CUT** | cues "best practices" / "voluntary commitments" fired on benign *"our vendor follows industry best practices and publishes voluntary commitments"* — benign-ubiquitous. The real Frontier Model Forum corpus uses soft language ("develop resources", "emerging practice documents"); the "reserves to itself" gold was my paraphrase, not the Forum's words. Cannot separate capture from ordinary standards work by substring. |
| reference_capture / `asymmetric_enforcement` | **FIXED (narrow, kept)** | old cues "rules for thee" / "selectively enforced" fired on CRITIC language (wrong speaker — it would flag the critic, not the infiltrator). Pruned to Marcuse's actual doctrine phrasing ("liberating tolerance", "intolerance against movements from the right", "toleration of movements from the left"). Now fires on the Marcuse primary (*Repressive Tolerance*, 1965) and is quiet on the critic control. Narrow — catches the explicit articulation of asymmetric-tolerance doctrine, which is a real but specialized tell. |

## Pre-existing false-positive found + fixed

| lens / marker / detection | fix | evidence |
|---|---|---|
| institutional_permeation / captured_neutral / `value-as-science` | pruned cues "best practices" and "evidence-based" | fired on benign *"our team takes an evidence-based approach and follows industry best practices"*. The diagnostic cues ("sound science", "the science is settled", "just the data") still fire on the real move; the two generic phrases were false-positive bait. Eval unchanged (18/18, 6/6) — no fixture depended on them. |

## Honest limitations surfaced

- Several "capture-move" markers are **behavioral, not linguistic** — actors *do* salami-slicing or
  asymmetric enforcement without ever *saying* it. A substring cue-floor can only catch the ones who
  articulate the doctrine (Marcuse) or a critic/historian's label. Those markers are narrow by nature
  and should lean on the find→verify LLM layer, not the cue floor, for anything published about a
  named person.
- The next pass must FP-audit the remaining existing markers in the three capture lenses the same way
  (benign + adversarial probes), then extend to `militant_mobilization` (the terrorist lens).

## Suite state after this pass
- `python -m pytest -q` → **113 passed**.
- `python eval/run_eval.py cues` → positives **18/18**, negatives quiet **6/6**, marker coverage
  **18/18**, 8 skipped (need a model for the verify layer).
