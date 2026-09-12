# Eval results — 2026-08-02: institutional_permeation cue sweep + two detector bugs

Two defects found while designing the public self-audit ("The Mirror"), which would have
published a score about the author's own books. Both are fixed; the score changed by more
than 2x as a result, which is why the fix had to land first.

## Bug 1 — `detect_cues` produced misaligned receipt spans (FIXED)

`tradecraft/detect.py` matched cues against `text.lower()` but sliced spans out of `text`.
`str.lower()` is **not length-preserving** — `"İstanbul"` is 8 characters and lowers to 9 —
so every span after the first such character drifted. Observed symptom: the span `'reedom '`
recorded for the cue `'patient'`.

Compounding it, the span ended at `idx + len(cue)` using the **unstripped** cue, overrunning
by whatever whitespace `cue.strip()` had removed.

Fix: search the original string case-insensitively (`re.search(re.escape(c), text, re.I)`).
Offsets are then correct by construction and the span is exact. Verified with a regression
case carrying length-changing characters ahead of every cue: 0 misaligned spans.

This corrupted receipt **output**, not just display — any span recorded before this date in
`receipts.jsonl` or a leaderboard record should be treated as unreliable and re-derived.

## Bug 2 — `institutional_permeation` had never been cue-swept (FIXED)

The 2026-07-31 / 2026-08-01 sweeps cut benign-ubiquitous cues from eight lenses.
`institutional_permeation` was not among them and still carried seven single generic words.

Measured against benign control sentences, before the cut:

| Control sentence | Fired |
|---|---|
| "The patient was discharged on Tuesday in good condition." | `patient` |
| "She is a permanent member of the faculty and a patient teacher." | `permanent`, `patient` |
| "He works as a software engineer at the institute." | `institute`, `engineer` |
| "The default setting is neutral; change it in preferences." | `default`, `neutral` |
| "Call the emergency number if the smoke alarm sounds." | `emergency` |

**5 of 7 benign sentences tripped the lens.** Same verdict as the earlier sweeps: CUT.

Cues removed (7): `patient`, `permanent`, `institute`, `engineer`, `default`, `neutral`,
`emergency`.

Nothing was lost. Every one sat beside discriminating multi-word cues that survive —
`irreversibility-framing` keeps `inevitable` / `inevitability` / `irreversible` /
`no going back` / `settled forever`; `build-parallel-institutions` keeps `think tank` /
`training pipeline` / `litter the world with`; `neutrality-claim` keeps `no particular party`
/ `we take no position`.

### After the cut

- benign false positives: **0 of 5** (was 5 of 5)
- `eval/run_eval.py cues`: **49/49 positives · 28/28 negatives quiet · 49/49 marker coverage**
- Webb 1923 primary still fires correctly on `inevitable` + `permeation`

### A process note worth keeping

Two intermediate attempts at this edit were reverted before landing:

1. A `re.sub` with `DOTALL` over `cues: \[(.*?)\]` ran past the list terminator into the
   `gold:` blocks (they contain `[FACT]`) and ate cues silently.
2. A line-scoped version used `re.findall(r'"([^"]*)"')`, which captures only **quoted**
   scalars. These lists mix quoted and bare YAML scalars
   (`cues: [inevitable, "no going back"]`), so every bare cue was dropped — `inevitable`
   and `permeation` among them, which cost the Webb fixture its expected marker.

Both were caught by `marker coverage` falling 49/49 → 48/49. **The coverage metric is the
thing that caught a bad edit twice; do not let it regress silently.** Cue lists are now
emitted uniformly quoted so the mixed-quoting trap is gone.

## Effect on the book self-audit

Re-measured after both fixes (offline `cues` backend, `institutional_permeation` only):

| | before fixes | after fixes |
|---|---|---|
| *The Ratchet* (26 chapters) | 199 hits | **93** |
| *The Secret Life of Evil Robots* (18 chapters) | 69 hits | **20** |

The pre-fix figure was inflated **2.1x / 3.5x** by the generic cues. The earlier reading
that four Ratchet chapters graded "dense tradecraft" on permeation was substantially an
artifact of un-swept cues and must not be published in that form.

Densest remaining, and these look like genuine topical density rather than false positives —
a book about institutional permeation quoting Fabian and Powell-memo language will and should
fire this lens:

- `01-the-flagging-machine.md` — 11 (`inevitable`, `period of years`, `permeation`, `think tank`)
- `07-the-priest.md` — 9 (`inevitable`, `Long-Term`, `permeation`, `think tank`)
- `19-the-model.md` — 8 (`from within`, `think tank`, `judiciary`, `narrative`)

Which is the point the self-audit is for: the instrument fires on the author's own prose, the
dispositions are shown (QUOTE / TOPIC / FALSE POSITIVE / OWN VOICE), and the reader judges.
It just has to fire for real reasons.
