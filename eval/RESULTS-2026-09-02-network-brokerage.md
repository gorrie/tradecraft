# The lens with no code, and the gold that turned out to be right

**2026-09-02.** Backlog item 12 said the structural lenses had never been run: *"`revolving_door`
and `network_brokerage` read a graph via `structural.py`; no graph has been built or tested
against. Their correctness is entirely unverified."*

Half of that is wrong and the other half was worse than stated.

## `revolving_door` was already run and tested

`data/research-entities.json` exists — **182 entities, 183 edges, no dangling references** —
and `tests/test_structural.py` carries eight passing tests that exercise all eight
`revolving_door` detections against it by name. It is not unverified.

## `network_brokerage` had no implementation at all

`structural.py` does not mention the lens. Checked detection by detection:

| lens | detections | emitted by structural.py |
|---|---|---|
| `revolving_door` | 8 | all 8 |
| `network_brokerage` | `high-betweenness`, `hub-degree`, `cross-group-broker` | **none** |

So the lens declared `reads: graph`, carried six gold entries quoting specific computed figures
marked `[FACT: computed by Brandes' algorithm over the shipped graph]`, and **nothing in the
repository could fire it.** The numbers had been computed outside the tree and never committed
as a detector. That is a worse state than "unverified": it is a lens that looks finished, cites
arithmetic nobody can re-run, and would have gone to a leaderboard as a scoring axis.

`tradecraft/brokerage.py` is the missing half — exact Brandes betweenness, degree, and a
Gould-Fernandez (1989) triad census, stdlib only, receipts carrying the bridging triads.
`score_subject` now dispatches on the lens id.

## The gold was computed correctly. My first implementation was not.

Two defects in the new code, both caught by checking against the gold rather than by reading it.

**The Gould-Fernandez census was half.** I counted each unordered neighbour pair once and got
Anthropic `coordinator:42, gatekeeper:19, representative:10, liaison:3` against the gold's
`84 / 29 / 29 / 6`. The tell that settled it: **gold reports gatekeeper and representative as
equal, and they are equal by construction under the ordered-pair convention** — a triad
`a—B—c` with `a` outside B's group and `c` inside is a gatekeeper role read one way and a
representative role read the other. Ordered pairs are canonical GF. The gold was right; the
code was wrong.

**The betweenness scale was four times too large**, `2/((n-1)(n-2))` where the normalisation is
`1/((n-1)(n-2))`. Caught by a three-node unit test: in `A—B—C`, B sits on the only path between
the other two, so its normalised betweenness is 1.0 by definition and the code said 2.0.

Worth recording *how invisible that was on the real graph*: every node was inflated by the same
constant, so **every rank was correct and the entire ordering looked right.** A ranking that
reproduces is not evidence that a level is right. That is the same lesson the bias study learned
about effect sizes, arriving from graph arithmetic.

## What the corrected code says, against gold computed on an older graph

| | gold (172 nodes) | computed (182 nodes) |
|---|---:|---:|
| Frontier Model Forum, betweenness | 0.087 | 0.1078 |
| Frontier Model Forum, degree | 10 | **11** |
| OpenAI, betweenness | 0.065 | 0.0734 |
| OpenAI, degree | 17 | **18** |
| Anthropic, degree | 13 | **13** |
| Anthropic, GF census | 84 / 29 / 29 / 6 | **84 / 29 / 29 / 6** |
| OpenAI, liaison | 30 | 46 |

**Everything that should have moved moved, and the one thing that should not did not.** Anthropic
is the only gold node whose degree is unchanged, and its Gould-Fernandez census reproduces to
the digit — an independent reproduction of a figure computed by other means, which is as good a
validation as this code can get. FMF and OpenAI each gained a tie as the graph grew by ten
nodes, and their betweenness rose accordingly. Rank order reproduces exactly: FMF the top
bridge, OpenAI the top hub, Anthropic second.

## The gold should quote rank and structure, not decimals

The betweenness and degree figures in this lens's gold were correct when computed and are stale
now, and they will be stale again after the next dossier lands, because **they are levels
measured against a graph that grows.** The census figures drifted for exactly the nodes that
gained an edge.

Recommend rewriting those gold entries to what survives graph growth — *"the highest-betweenness
bridge in the graph, sitting between the frontier labs and the governance bodies"* — and letting
the numbers live in a regenerated report. Same ruling the bias study reached about citing the
arc rather than the level, and the same reason.

`test_brokerage.py` pins the Anthropic census as a regression test precisely because that node's
neighbourhood is stable; if it ever moves, either the graph changed around Anthropic or the
census implementation did, and both are worth being told about.

## Still open

- **Thresholds are top-decile, per the taxonomy's own wording**, and relative on purpose: an
  absolute cut means something different on 182 nodes than on 10,000. Not calibrated against
  labelled data, because there is none — same standing gap as everywhere else in this repo.
- ~~**No floor for a graph detector.**~~ **BUILT: `eval/graph_floor.py`** — and its answer is
  more interesting than a number.

  Four perturbations. Two are invariance assertions: relabel every node id, flip every edge's
  direction. Both must move nothing, and both do move nothing — adjacency is undirected and a
  rename is a rename. Two are the floor: drop a degree-1 node *not* adjacent to the subject
  (a dossier that had not landed yet), and attach a new one elsewhere (the next dossier landing
  somewhere else). That is the right null for this instrument, because **an entity graph built
  from dossiers is permanently incomplete, and a subject's position must not swing on whether
  some unrelated peripheral node happens to have been entered yet.**

  The index moved **0.000 on every trial**, and that is not a clean floor. The metric underneath
  it moved on 145 of 160 trials, by up to 0.0039 betweenness. **The index is quantised**: three
  markers firing at a fixed confidence, so across every subject and perturbation it takes only
  **four distinct values — 32.86, 61.09, 65.71, 93.94.** A leaderboard gap on this lens is not
  resolvable below that step, and unrelated corpus growth is not what limits it.

  The harness says so itself and `--check` exits 1 rather than certifying it, because reporting
  0.000 as a floor would be the most flattering possible reading of no resolution. The metric
  floor — median 0.0004, p90 0.0012 betweenness — is the number to quote if this lens ever
  reports centrality instead of a tier.

  `ratchet_series` still needs its own (corpus item 30); a counting detector's nuisance factors
  are docket-matching and coverage, not edges.
- **Position is not action.** Every receipt says so and the taxonomy says so three times, and
  it needs saying again before any of this reaches a public board: a node positioned to broker
  is not a node shown to broker.
