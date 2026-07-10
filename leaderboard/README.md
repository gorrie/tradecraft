# Capture Leaderboard

A **receipts scoreboard** over documented capture *actions* — the flagship output view of the
Tradecraft detector. It ranks institutions by how much of the capture playbook they can be caught
running, with every cell backed by a clickable receipt. **Not a verdict — an evidence-density map.**
Design rationale: `memory/project_capture_leaderboard.md`. Seed evidence:
`research/research-wikipedia-capture.md` + `research/capture-mechanism-universal.md`.

## Why it can't be a single "evil score"
Capture is measured by *actions*, and institutions are captured *incompletely by several factions at
once*. So each institution is a **set of records**, not a number, and the board is segmented by actor
and credits self-correction. A naive one-number ranking is exactly the partisan-hit-list failure mode
the whole framework exists to avoid.

## Record schema (`data/leaderboard.jsonl`, one JSON object per line)
| field | meaning |
|-------|---------|
| `institution` | the subject being scored |
| `lens` | which Tradecraft lens the marker belongs to (validated on load) |
| `marker` | a marker id from that lens (the documented ACTION) |
| `move` | `permeation` \| `language` \| `ratchet` (the three-move mechanism) |
| `actor` | WHO ran the action (faction) — drives the segmented bar; capture is never blamed on the institution wholesale |
| `assurance` | `FACT` (1.0) \| `ATTRIBUTED` (0.6) \| `RUMOR` (0.25) |
| `severity` | 0–1 marker severity |
| `self_correction` | 0–1 credit — did the institution's own machinery resist/reverse it? |
| `span` | the exact quoted evidence |
| `receipts` | list of source URLs (**required — the defamation gate; a record with none is a build error**) |
| `note` | context |

## Scoring
`record_score = severity × assurance_weight × (1 − self_correction)`
Institution **rank = Σ of FACT-tier record_scores only.** Attributed + rumor are summed into a separate
`unverified` band that is shown but never drives the rank. `by_actor` sums all tiers per faction for the
segmented bar. Self-correction is subtracted per-record (Wikipedia's ArbCom banning both sides is the
model case — its coordinated-editing score drops sharply).

## Discipline (enforced or checked)
- **Receipt-gate:** every record must carry ≥1 receipt (`score.py` exits nonzero on a NO-RECEIPT record).
- **Marker coherence:** every `marker` must exist in its declared `lens` (validated against all detectors).
- **Assurance honesty:** rumor is postable but labeled; attributed never ranks; only FACT drives position.
- **Spectrum balance:** the roster MUST span the political map — an all-one-direction board is broken,
  not done. Current seed: Wikipedia (reference-institution) + Fabians (left) + CCP United Front
  (Leninist-state) + Seven Mountains (religious-right) + RSS (Hindu-nationalist).

## Usage
```
python leaderboard/score.py                    # build OUTPUT.md + leaderboard.json from the data
python leaderboard/snapshot.py 2026-07-08      # observatory: archive the cut + emit DELTA.md (drift)
```
`leaderboard.json` is also copied to `website/data/capture_leaderboard.json` for the parked
`/tech/capture-leaderboard/` render (server-side Hugo, amusing framing over the receipts; graduates to
live on Ian's go).

## Observatory
The leaderboard is a standing longitudinal instrument, same shape as the AI-bias study: re-measure on a
cadence, `snapshot.py` archives each cut under `snapshots/` and diffs it against the prior into
`DELTA.md` — the drift report *is* the mailing-list digest payload. Intended to run under a shared
observatory runner alongside the bias-study cut and ratchet-mcp drift (see the design memo).
