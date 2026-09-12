# Hostile read of the assembled instrument

**2026-09-11.** Plan item 1.4, Gate 27. Two hostile reads have run on the bias study
(`RESULTS-2026-09-01-hostile-read.md`, `REVIEW-2026-08-30-conviction-hostile.md`); none had run
on the **detector as assembled** — the three public surfaces a reader meets, rather than on
individual lenses.

This is that read. **Every claim on `/tech/instrument`, `/tech/tradecraft` and the leaderboard
gets a row: survives, narrowed, or withdrawn.** Each verdict is verified against the shipped
payload or the code, not against the document that asserts it. Where a check needed a negative
control, the control was run.

**Result: 7 survive, 3 narrowed, 0 withdrawn.** The narrowings are all on `/tech/instrument`, and
the first of them is the one worth the author's attention.

---

## NARROWED 1 — "fires identically" asserts a rate the site does not measure

`/tech/instrument`, first section:

> "It fires identically on left-gradualist and corporate-right prose; that symmetry is the
> design, not a disclaimer."

The site's evidence for this is the method/actor cross-tab, and the cross-tab is scrupulous where
the page is not. Its own headline: *"12 of 17 markers fire across more than one actor family, and
the two commonest fire across 8 families that agree on nothing."* Its own `limit` field:

> *"A hand-assembled ledger, not a random sample of institutions. A marker firing across families
> here shows the marker CAN travel; it does not measure how often it does in the world."*

Measured against the shipped payload:

| | |
|---|---:|
| markers in the shipped taxonomy | **107** |
| markers appearing in the cross-tab | **17** (16%) |
| markers the cross-tab shows firing across >1 family | 12 |
| markers appearing against a single family | 5 |
| actor families | 12 |

So the evidence covers a sixth of the markers, is a hand-assembled ledger rather than a sample,
and **explicitly declines to measure frequency** — while the page says the detector fires
*identically*, which is a claim about frequency. "Identically" is not a stronger phrasing of what
the cross-tab found; it is a different and unmeasured claim.

This is the same class the 2026-09-01 read withdrew *"no house political position detectable at
the median"* for: an asymmetry claim resting on a median that had pooled five vendors into one.

**Narrowed to what the cross-tab supports**, in the page prose. The design intent is kept — it is
true and it is the point — but separated from the empirical claim, which is now stated at the
cross-tab's own strength and links to it so a reader can check the 17.

## NARROWED 2 — "ports exactly two functions" is thirteen

> "`engine.js` ports exactly two functions — cue matching and per-lens grading"

`engine.js` defines **13**: `detectCues`, `gradeDocumentForLens`, `escapeRe`, `findAllBounded`,
`findBounded`, `insideContraction`, `mechanismTest`, `runAll`, `selfTest`, `suppressed`,
`tierFor`, `tokenCount`, `unspaced`.

Two of those are the ported graders and the sentence is right about *which*; the other eleven are
string helpers and the parity harness. No hardcoded vocabulary was found — the two cue-looking
literals in the file (`"class struggles"`, `"eliminate ambiguity"`) are both inside comments
explaining the suffix list and the Executive Order 12988 exclusion. `tierFor` reads its tiers
from the payload argument and hardcodes no thresholds.

So the claim is imprecise rather than wrong, and the imprecision is in the direction that
flatters. Reworded to "ports two graders … the rest is string helpers and the parity harness."

## NARROWED 3 — "reads every cue, weight and threshold from a payload" — two constants are a second copy

> "reads every cue, weight and threshold from a payload emitted by the same taxonomy loader the
> Python detector uses. There is one definition of each marker, in YAML, and both runtimes read
> it."

True of the vocabulary. **Not true of two structural constants**: `EXCLUDE_WINDOW = 200` is
hardcoded at `engine.js:103` and again at `detect.py:351`, and the suffix list is duplicated by
the file's own admission (*"Closed suffix list, identical to Python's `_SUFFIXES`"*).

**Verified guarded, in both directions.** Setting the JS window to 3 and running
`tools/test_engine_parity.py` fails at **71/73**, naming `neg_adept_mission` and
`sub_neg_literal_drain_swamp` — both negative fixtures that depend on an exclusion firing at
distance. Restored, parity returns 73/73 and the file is byte-identical to the committed one.

So the duplication cannot drift silently, which is why this is a narrowing and not a withdrawal.
But the sentence as written would let a future editor move a threshold into JS believing the
payload governs it. Reworded to say the vocabulary comes from the payload and the two structural
constants are duplicated and parity-gated.

---

## SURVIVES

| # | claim | surface | verified by |
|---|---|---|---|
| 1 | "The Mirror tab points the same instrument at the author's own books" | instrument | payload carries **4** mirror entries (18 / 26 / 30 / 20 chapters). The 2026-08 audit's "covers 2 of 4 books" is closed. |
| 2 | "This browser re-runs all of them on load and compares" | instrument | `ui.js:296` `DOMContentLoaded` → `boot()` → `Instrument.selfTest(P)` at line 236. |
| 3 | "If it ever reads **ENGINE DRIFT**, the scores are hidden" | instrument | `ui.js:238-248` sets the drift banner, `el('ins-panels').style.display = 'none'`, and returns before any score renders. |
| 4 | "no vocabulary of its own" | instrument | the only cue-shaped literals in `engine.js` are in comments; all 140 detections carry their cues in the payload. |
| 5 | "16 lenses ship in the payload: 10 carry text cues … 5 need a model … 1 (`revolving_door`) is a network lens with no text cues at all" | tradecraft | payload has exactly 16; the 10/5/1 split matches the declared routing. |
| 6 | "every marker cites the gold example that defines it" | tradecraft | `gold` present on **140 of 140** detections — finer-grained than the claim, which says markers. |
| 7 | "the grader is deterministic" | tradecraft | parity harness reproduces all 73 fixtures in a second runtime; two independent `--check` runs of the exporter are byte-identical. |

## Not in scope, and why

The **leaderboard** page carries no numeric claim of its own — its numbers come from
`capture_leaderboard.json` through the `leaderboard-sync` and `record-store` gates, and the
standalone page is parked behind an alias. Its content claims were read in the 2026-08-23 capstone
review (item 26, closed 2026-08-26 when the 12 actor families were declared in
`actors.json` and enforced on load). Nothing here re-litigates that.

**What this read did NOT check**, stated so a later reader does not mistake silence for coverage:
whether the markers are *good* — that is the PTC and collateral work
(`RESULTS-2026-09-07-collateral-eval.md`, `RESULTS-2026-09-07-llm-find-stage.md`,
`RESULTS-2026-09-11-unlocatable-spans.md`), and it is unflattering there already. This read asks
only whether the assembled pages describe the artifact they ship.

## Nothing was loosened

No threshold, no lens state, no entry in `floors.json`, no gate. Three sentences of page prose
were narrowed to match measurements that already existed. `freshness_gate.py` 0 FAIL,
`endpoint_audit.py` 0 findings across 741 pages, `test_engine_parity.py` 73/73.
