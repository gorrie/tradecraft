# The unlocatable spans: half are invention, and the other half are recoverable

**The owed measurement.** `RESULTS-2026-09-07-llm-find-stage.md` closed on one open item: the LLM
find stage quotes 8,789 spans across 15 lenses and **3,210 of them (36.5%) cannot be located** in
the article they were attributed to. Its ruling was that this number decides whether a fuzzy
locator is a fix or a laundering step, and that the classification had to happen **before** any
locator was written — otherwise the locator gets tuned against the number that is supposed to
judge it.

Done here. Two independent measurements, one machine-decidable and one a hand-read, and they
agree.

**Rig:** `eval/unlocatable_sample.py`. Corpus and caches as in the 2026-09-07/11 run
(`huihui_ai/qwen2.5-abliterate:14b`, 371 PTC articles, 15 lenses at the current taxonomy).
Cache selection is by `prompt_hash`, not by set size — four lenses hold two complete 371-record
runs and picking the larger is a coin flip that reads the superseded one. The first draft of the
sampler did exactly that and collected 3,234 spans against the payload's 3,210; the 24-span gap
is what exposed it.

---

## 1. The machine-decidable half: a span quoted from 102 different articles is not a quote

No reader, no judgement, no threshold. A span genuinely quoted from a document cannot also be
quoted verbatim from a different document. So: how many unlocatable span *texts* appear against
more than one article id?

| | spans | distinct texts | texts used on >1 article | occurrences that are such a span |
|---|---:|---:|---:|---|
| **unlocatable** | 3,210 | 1,736 | 152 | **1,361 — 42.4% [40.7, 44.1]** |
| **locatable (control)** | 5,579 | 3,701 | 72 | **228 — 4.1% [3.6, 4.6]** |

The control is what honest repetition looks like: site boilerplate that really does appear in many
articles (*"take our poll - story continues below"*, *"completing this poll grants you access to
freedom outpost updates"*), plus a handful of widely-syndicated quotes. 4.1%.

The unlocatable side is not that.

| span text | articles it was "quoted" from |
|---|---:|
| `malinformation` | 102 |
| `there is no alternative.` | 101 |
| `propaganda of the deed` | 53 |
| `no one may post, pay, or travel without an authenticated, verified digital identity` | 44 |
| `organizations utilizing this method of command and control are easy prey for government infiltration … leaderless resistance` | 43 |
| `a rationally designed system, administered by experts, will allocate far better than the spontaneous muddle it replaces` | 35 |
| `these protections are now the floor, not the ceiling, for any future framework.` | 33 |
| `stakeholder capitalism` | 33 |
| `the science is settled and the debate is over; further questions are not legitimate` | 30 |
| `the patchwork of local arrangements is simply too messy to administer and must be simplified` | 30 |
| `only the designated authoritative sources may define what counts as accurate` | 27 |
| `heighten the contradictions` | 26 |

**Read what those are.** They are not misquotes of anything. Several are the detection's own
definition returned as if it were a sentence in the article — `no one may post, pay, or travel
without an authenticated, verified digital identity` is `legibility/id-as-precondition` restated;
`the science is settled and the debate is over` is `distributed_accountability/settled-beyond-question`
restated. The rest are the canonical *term of art* for the concept — `malinformation`,
`propaganda of the deed`, `stakeholder capitalism`, `heighten the contradictions`, and the Louis
Beam "leaderless resistance" passage, which the model knows from training and reproduced against
43 unrelated articles.

**So 42.4% of unlocatable spans are provably not quotes, by arithmetic alone.** That is a floor,
not an estimate: it counts only spans caught repeating. A fabrication emitted against exactly one
article is invisible to this test.

## 2. The hand-read: 120 spans, seeded, classified against the article

`--n 120`, seed `20260911`, drawn and written to disk before any span was read. Classes assigned
one per span against the article's nearest passage.

| class | n | share | recoverable by a locator? |
|---|---:|---:|---|
| **INVENTION** — no corresponding passage | **60** | **50.0% [41.2, 58.8]** | **no** |
| PUNCT — verbatim but for quote glyphs, casing, added quote marks | 50 | 41.7% | yes |
| BOUNDARY — verbatim, span merges or trims at a sentence edge | 7 | 5.8% | yes |
| PARAPHRASE — substance present, wording the model's | 3 | 2.5% | judgement |

**Recoverable: 57 of 120 = 47.5% [38.8, 56.4]. Invented: 60 of 120 = 50.0% [41.2, 58.8].**

Grading was automatic only where it is provable — 34 spans whose normalised form is present
verbatim (PUNCT), and 54 caught by the cross-article test above (INVENTION). The remaining 32 were
read individually against their article and are recorded with the reader's note in
`SAMPLE-2026-09-11-unlocatable.jsonl`. A pre-classifier that guessed PARAPHRASE versus INVENTION
would have been the laundering this exercise exists to prevent, so it does not exist.

The two measurements agree: 42.4% machine-provable, 50.0% [41.2, 58.8] on the read. The read is
higher because it also catches single-article fabrications, which is exactly the gap the floor
leaves open.

## 3. What this means for the locator, which is the question that was asked

**Projected over the corpus:** ~1,605 invented spans [1,322–1,887], which is **18.3%
[15.0, 21.5] of all 8,789 quoted spans.** Close to one span in five that the find stage emits is
text that is not in the document.

**A fuzzy locator is justified, and it is also dangerous, for the same reason.** Half the
unlocatable spans are real text the model re-punctuated, wrapped in quote marks the article did
not have, or trimmed at the wrong boundary. Recovering those is correct: they are quotes, and the
only thing wrong with them is `str.find`'s literalism. That would take the unlocatable rate from
36.5% to roughly 18%, and CP2 bar (3) asks for under 20%.

**And that is precisely the trap.** A locator loose enough to recover a curly-quote mismatch is
also loose enough to match `the science is settled and the debate is over` onto whichever
paragraph of a climate article scores highest — and the result is a false receipt with a character
offset attached, which is worse than an unlocatable span, because an unlocatable span is visibly
unlocatable and a wrong offset is not. **Clearing bar (3) by fuzzy matching alone would be
laundering.** The bar would be met and the artifact would be worse.

### The one thing that must go in before any locator

The cross-article repetition test is cheap, deterministic and needs no threshold: **a span text
emitted against more than one article is not a quote and must never receive an offset.** It
removes 1,361 of the 3,210 with no judgement call, and it is a guard the locator cannot tune its
way around. Any fuzzy locator lands *after* that filter or not at all.

**Not done here, deliberately:** the locator is not written, no threshold is proposed, and nothing
in `floors.json`, the taxonomy or any lens state changes. This file measures; the routing decision
it informs is a reviewed edit citing it, and CP2 remains the author's call.

## Reproduce

```bash
python tradecraft/eval/unlocatable_sample.py --n 120 --out SAMPLE-2026-09-11-unlocatable.jsonl
python tradecraft/eval/unlocatable_sample.py --grade SAMPLE-2026-09-11-unlocatable.jsonl
```

The sample file carries every span, its lens, its detection, its article, its class and the note
for each — including which were graded automatically and on what evidence.
