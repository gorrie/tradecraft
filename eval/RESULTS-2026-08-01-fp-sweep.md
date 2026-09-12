# Full-lens false-positive sweep — 2026-08-01

**Scope.** Every LINGUISTIC lens (the eight cue-driven ones plus the two capture lenses hardened on
2026-07-31). Goal: run each marker's cues against benign controls + opposite-meaning/critic text and
cut anything that fires on innocent prose, because this tool names infiltrators/traitors and a false
positive smears an innocent. Ideology-blind throughout.

## Method

A one-off sweep script (session scratch, never committed and no longer present) ran the deterministic `detect_cues` floor over a battery of benign controls
(sports, church, corporate, ops/devops, management, product marketing, poetry, mission statements,
science reporting, political debate) and opposite-speaker adversarials (a journalist DESCRIBING
militants; a critic quoting the censor's own phrase) for each lens. Any cue that fires on a benign
control is a candidate cut. Retained cues were then re-checked for recall (they still fire on the real
primary / gold) and the whole eval suite re-run.

## Headline result — the shibboleth/generic split

The sweep sorted every cue cleanly:

- **Coined subculture idiom survived** — `leaderless resistance`, `propaganda of the deed`, `heighten
  the contradictions`, `as above so below`, `there is no alternative`, `radical monopoly`. Near-zero
  benign use.
- **Repurposed common words failed** — every one fired on innocent prose and was cut: `based`,
  `a hero`, `saint `, `did nothing wrong`, `the martyr`, `rest in power`, `escalate`, `lone wolf`
  (opposite-speaker), `consensus`, `stakeholders`, `the committee`, `per policy`, `misinformation`
  (opposite-speaker), `dangerous`, `settled science`, `standardize`, `observability`, `evidence-based`,
  `best practices`, `data-driven`, `the light`, `the fire`, `illumination`, `the Work`, `personalized`,
  `autocomplete`, `diminishing returns`, `mandatory`, `inevitable`, `obsolete`, `I would die for`.

This is the empirical basis for the pivot recorded in `BACKLOG-shibboleth-corpus-study.md`: grow the
tool by mining each camp's coined idiom, not by inventing more generic move-cues.

## Per-lens actions

| lens | cut (FP bait) | kept (shibboleth core) | notes |
|---|---|---|---|
| militant_mobilization | `saint `, `a hero`, `based`, `the martyr`, `rest in power`, `did nothing wrong`, `escalate`, `lone wolf`, `act alone`, `independent action`, `the time for talk is over`, `now is the time`, `no more waiting`, `find them` | `leaderless resistance`, `propaganda of the deed`, `by any means necessary`, `diversity of tactics`, `heighten the contradictions`, `we know where they live`, `hunt them`, `high score`, `gigachad` | DEFAMATION-CRITICAL; zero tolerance for cues firing on devotional/sports prose. Name-anchored "Saint <perpetrator>" is verify-only. |
| distributed_accountability | `consensus`, `stakeholders`, `the committee`, `per policy`, `automatically`, `standard procedure`, `everyone agrees`, `misinformation`, `disinformation`, `fact-check`, `trust the science`, `dangerous`, `irresponsible`, `complicit`, `causing harm`, `settled science`, `the experts agree`, `consensus is clear` | `nobody decided`, `out of our hands`, `the algorithm decided`, `the community decided`, `harmful falsehood`, `we decide what is`, `on the wrong side of history`, `denialist`, `the debate is over`, `not up for debate` | Opposite-speaker was the big failure: `misinformation`/`fact-check` are used identically by the apparatus and its critics. |
| legibility | `legible`, `legibility`, `observability`, `single pane of glass`, `register`, `on the record`, `unique identifier`, `standardize`, `standardization`, `interoperable`, `normalize`, `harmonize`, `rationalize`, `evidence-based`, `best practices`, `data-driven`, `verified identity`, `know your customer`, `credential`, `full visibility`, `registry`, `central database`, `hit the target`, `risk score` | `make visible`, `see the whole`, `must be registered`, `no anonymity`, `authenticated to participate`, `engineer society`, `centrally planned`, `we know better`, `optimize the number` | Legibility is an ANALYTIC concept (Scott), not a shibboleth vocabulary — flagged near-inert on the floor; `impose-uniformity` made inert (`cues: []`). Leans on verify. |
| adept_speech | `cannot be put into words`, `words fail`, `the tradition holds`, `the Work`, `the mission`, `the light`, `illumination`, `the fire`, `ascent`, `descent`, `awakening`, `the veil`, `the masters`, `the elders`, `it is said`, `I have seen`, `direct experience`, `candidates`, `seekers`, `if you are called` | `ineffable`, `as above so below`, `gnosis`, `solve et coagula` (NEW), `egregore` (NEW), `secret chiefs` (NEW), `those with eyes to see`, `hidden in plain sight` | `the Great Work` is a real shibboleth cut only for lack of case-sensitive matching (see capability gap). |
| cognitive_capture | `personalized`, `tailored to you`, `based on your`, `autocomplete`, `smart reply`, `default phrasing`, `agreeable`, `affirming`, `validate`, `watch time`, `amplify`, `companion`, `relationship`, `offload` | `microtargeted`, `psychographic`, `maximize engagement`, `RLHF preference`, `loves you`, `never leaves` | `opinion-shaping-suggestions` made inert — latent autocomplete-persuasion is a behavioral tell the operator never names (opposite-speaker). |
| counterproductivity | `made it worse`, `backfired`, `the fix created`, `the only option`, `mandatory`, `compulsory`, `no alternative`, `diminishing returns`, `past the point`, `you are not qualified`, `needs assessment` | `radical monopoly`, `disables self-provision`, `second watershed`, `counterproductive beyond`, `disabling profession`, `iatrogenic` | Illich coinages are strong shibboleths. |
| inevitability_framing | `inevitable`, `unavoidable`, `no choice but`, `the future is`, `progress is coming`, `obsolete`, `fall behind`, `left in the dust` | `there is no alternative`, `TINA`, `adapt or die`, `right side of history`, `the arc of history` | Mostly VALIDATED — the surviving cues are genuine slogans; the lens is ideology-blind so a vendor deploying them is the move firing correctly. |
| costly_signal | `I would die for`, `cost me everything`, `was fired for`, `lost my job over` | `willing to go to prison`, `obey God rather than you`, `going to prison for`, `served my sentence` (gold-anchored: Plato, Auernheimer) | Hyperbolic-affection FPs cut; the concrete/dated price references kept. |

> **CORRECTION 2026-09-07.** `beyond words` and `the Great Work` are removed from
> `adept_speech`'s cut column above because both are live again. `beyond words` was restored
> in the 2026-09-01 gold-recall repair (`6557a9f`), which re-read the repaired lens against 40
> control documents; `the Great Work` returned as the lowercase cue `the great work` with a
> match-local exclusion of the corporate mission-speak register (`6557a9f`, `4367cb9`), which
> is how the case-sensitivity gap the notes column names was closed. The exported Morgue is
> scraped from this column, so as written it kept announcing two live cues as dead
> (`freshness_gate.py` `cut-ledger-live`). The other twenty in that cell stand.

## Two behavioral detections made inert (not deleted)

`legibility/impose-uniformity` and `cognitive_capture/opinion-shaping-suggestions` had NO non-generic
cue — the move is real but the actor never announces it in words a critic doesn't also use. Both set
to `cues: []` with an explanatory comment (the same pattern as the already-structural `revolving_door`
/ `network_brokerage` lenses), preserving their definition + gold for a future structured/verify
backend. Nothing deleted.

## Structural / non-floor lenses (documented, unchanged)

`network_brokerage` (graph-property descriptions, not substrings) and `revolving_door` (empty cues by
design) are NOT linguistic cue lenses and are out of scope for the substring floor — they need graph /
structured input. Recorded here so a future reader does not mistake their non-firing for a bug.

## Easy wins landed (actor's-own-idiom shibboleths, symmetric)

- `distributed_accountability/authority-to-define-true`: `malinformation`, `cognitive infrastructure`
  (the disinfo apparatus's OWN coinages — verified fire on an exemplar, quiet on "core infrastructure"
  / "false information").
- `adept_speech/light-ascent-veil`: `solve et coagula`, `egregore` (esoteric practitioner idiom —
  verified fire, quiet on "dissolve and coagulate in the lab").
- `adept_speech/the-masters`: `secret chiefs` (Golden Dawn / Thelema shibboleth).

## Suite state

- `python -m pytest -q` → **113 passed**.
- `python eval/run_eval.py cues` → positives **18/18**, negatives quiet **14/14** (up from 6/6 — 8 new
  benign-control regression negatives locked in across militant / distributed / legibility / adept),
  marker coverage **18/18**, 8 skipped (need a model for the verify layer).
- FP sweep: the four smear-risk lenses (militant, distributed, legibility, adept) are QUIET on every
  benign control. Residual fires are all true-positives on probes that literally deployed the move
  (TINA/adapt-or-die slogans; the counterproductivity thesis; the "it was satire" deniability move).

## Next (see BACKLOG-shibboleth-corpus-study.md)

Comprehensive per-camp corpus mining (feminist / marxist / CSJ / accelerationist / jihadist /
managerial / disinfo / occult / AI-safety — symmetric), plus a motte-and-bailey structural marker in
the verify layer. Capability gaps to close: case-sensitive cues, verify-layer independent finding,
two-part proximity cues.
