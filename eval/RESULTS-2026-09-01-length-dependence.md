# The density term is measuring document length, and it does it in every lens

**2026-09-01.** `eval/lens_floor.py` reported that `institutional_permeation` moved up to 6.7
index points under DUPLICATION — the same text twice — against 0.0 for reordering, re-chunking
and whitespace. That was logged as a grader question worth returning to. Returning to it found
something larger than duplication sensitivity.

## Duplication is a null, and 12 of 12 firing lenses fail it

| lens | docs firing | dup median | dup max | length↔index Spearman |
|---|---:|---:|---:|---:|
| institutional_permeation | 24 | 0.19 | **6.74** | **−0.673** |
| distributed_accountability | 3 | 0.22 | **7.28** | n/a |
| rollback_asymmetry | 3 | 0.22 | 0.83 | n/a |
| reference_capture | 10 | 0.19 | 0.38 | **−0.498** |
| sourcing_asymmetry | 29 | 0.19 | 0.37 | +0.055 |
| subculture_register | 8 | 0.22 | 0.22 | **−1.000** |
| legibility | 7 | 0.14 | 0.22 | −0.200 |
| adept_speech, cognitive_capture, inevitability_framing, militant_mobilization, narrative_management | 1–3 | 0.12–0.21 | 0.12–0.25 | n/a |

Duplication is the one perturbation where the answer is not arguable. A document concatenated
with itself has exactly the same *rate* of method-marking. Any measure claiming to be a rate
must return the same number. Every lens that fires moves.

`subculture_register` at **−1.000** is the clearest statement of the defect: across the eight
documents it fires on, its index is a perfectly monotone inverse function of document length.
Not correlated with length — determined by it.

## The cause is the join of two reasonable decisions

Neither component is wrong by itself. Together they are incoherent.

**`detect_cues` fires once per detection**, by design and with a comment saying so: *"one
firing per detection is enough; move to the next detection."* Defensible for a
breadth-oriented grader — it is asking which markers are present, not how loud they are.

**`grade_document_for_lens` divides by token count**: `density = weighted_hits / (tokens/1000)`,
capped, and the grader's own docstring calls it *"weighted hits per 1k tokens."*

With one hit per detection, that quotient is not a rate. Its numerator is bounded by how many
distinct detections matched — typically **1** — so the expression reduces to `k / length`.
Measured:

| document | words | hits | density | index |
|---|---:|---:|---:|---:|
| *The Labour Party on the Threshold* (Fabian Tract) | 102 | 1 | **0.8987** | **22.56** |
| Zero-Based Regulating (Federal Register) | 739 | 1 | 0.1116 | 10.53 |
| 2026-17238 (Federal Register) | 28,677 | 1 | 0.0029 | 8.60 |

`w_density` is 0.15 for `institutional_permeation`, so **roughly 13 of the Fabian tract's 22
index points come from its being 102 words long.** The highest-scoring document in the corpus
scores highest substantially because it is the shortest.

## Why this matters more than a floor

The floor harness asks whether an index difference between two subjects exceeds the noise. This
is not noise. It is a systematic term, and it points one way: **shorter documents score higher.**

The leaderboard grades institutions across document sets whose lengths differ by two orders of
magnitude — a Fabian tract against a Federal Register rulemaking. An institution that writes
briefly outscores one that writes at length, holding rhetoric exactly constant. That is the
"measured by actions, not by style" rule failing in the arithmetic rather than in the taxonomy.

It also inverts the intuition the index invites. A reader seeing 22.56 against 8.60 reads the
first document as three times as method-marked. On these two documents the first is 280 times
shorter and both fired exactly one detection.

## Not fixed here, and why

Two repairs are available and both move every grade the engine has produced:

1. **Count occurrences.** `detect_cues` returns all firings rather than the first, making
   density a genuine rate. Changes the receipts as well as the scores, and multiplies receipt
   volume on long documents.
2. **Stop dividing by total length.** Density becomes something length-robust — the share of
   document segments carrying a marker, say — which keeps a bounded [0,1] meaning without
   rewarding brevity.

Choosing between them is an author's decision about what the index is *for*, not a repair to
apply while nobody is looking, and the honest position is that the engine currently has no
published grades to protect: the leaderboard is internal and the public `/tech/` render is
parked. Fixing it now costs nothing but the choice.

## The instrument

`eval/length_dependence.py`, and it is a standing check rather than a one-off:

- **duplication invariance** per lens, with the failing component named — breadth, intensity
  or density — so a failure reports its own cause instead of a number to go tracing.
- **length↔index Spearman** across every document a lens fires on.
- `--check` exits 1 on any lens that moves under duplication. Tolerance is 0.05 index points,
  set because a rate is a rate — not set to whatever the current code happens to produce, which
  is how a gate becomes a rubber stamp.

Proposed as **launch gate #31**: no lens ships while its score is a function of how long the
document is.
