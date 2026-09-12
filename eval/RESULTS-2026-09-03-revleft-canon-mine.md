# RESULTS 2026-09-03 — camp 3, and the eighth confound was predicted and duly arrived

`revolutionary_left`, mined from Marx & Engels against Adam Smith. Third run of
`BACKLOG-shibboleth-corpus-study.md`'s per-camp method, and the first that needed **no new
fetching** — both corpora were already in hand from the two earlier runs, which is the
compounding the georgist write-up predicted.

**Yield: two cues from nine surviving candidates, plus one new guard.**

---

## 1. Corpora

| role | source | words |
|---|---|---:|
| camp canon | Marx & Engels — *Manifesto of the Communist Party*, *Wage-Labor and Capital*, *The Poverty of Philosophy* | 74,628 |
| discipline control | Adam Smith, *The Wealth of Nations* | 418,125 |
| benign controls | `_news-control` + `_calibration-cache` | 115 documents |

Smith is the right control twice over: same discipline, and he is the tradition Marx is arguing
*against*, so a phrase common to both is political economy rather than Marxism.

## 2. THE EIGHTH CONFOUND — the polemical target's vocabulary

The `tankie_mlm` write-up ended by predicting a third camp would surface a confound the existing
seven guards could not see. It did, and it is a distinct class:

> **`constituted value` — 21 occurrences, 7 files, zero in both controls.** That is a textbook
> shibboleth profile. It is **Proudhon's** term. Marx quotes it relentlessly throughout *The
> Poverty of Philosophy* in the course of demolishing it.

Why no existing guard catches it: a camp's canon quotes its opponents at length, and the
opponent is not in the discipline control either — Proudhon is not Adam Smith. Frequency,
dispersion and both controls all agree it is idiom. Shipping it would have made the Marxist lens
fire on **Proudhonists**, which is the precise opposite of the intended reading.

**The separation is sharp and needs no external knowledge.** An opponent's term arrives wrapped
in quotation marks and attribution; a camp's own term does not. Measured over the same canon:

| candidate | occurrences | in quotes / near attribution | reading |
|---|---:|---:|---|
| `constituted value` | 20 | **90%** | Proudhon's, quoted to be attacked |
| `labor time` | 54 | **54%** | mixed — Marx discusses Ricardo's and Proudhon's labour-time as well as his own |
| `bourgeois production` | 18 | 44% | borderline |
| `existing society` | 16 | 25% | the camp's own |
| `modern industry` | 21 | 19% | the camp's own |
| `means of production` | 23 | 14% | the camp's own |
| `productive forces` | 40 | **8%** | the camp's own |
| `petty bourgeois` | 16 | **6%** | the camp's own |

`quoted_share()` now reports this per candidate and flags anything at or above 50% as *"the
polemical target's term?"*. **Reported, not filtered** — a camp does sometimes adopt a term it
first quoted, and `labor time` sits at 54% for exactly that reason. Same treatment as
dispersion: it informs the human, who remains the bottleneck.

## 3. The ruling

Nine candidates cleared both controls. **Two taken**, both zero in 418,000 words of Smith:

| cue | canon | files | quoted | why |
|---|---:|---:|---:|---|
| `productive forces` | 40 | 11 | 8% | *Produktivkräfte* — a Marxist term of art, not a Smithian one |
| `petty bourgeois` | 16 | 5 | 6% | a Marxist class category; Smith has no `bourgeois` at all |

Declined: `constituted value` and `labor time` (quoted — see above); `bourgeois society`,
`bourgeois production`, `modern industry`, `social relations`, `existing society`,
`instruments of production` — compositional description rather than coinage, and mostly
`bourgeois` plus a noun, where `bourgeoisie` is already a cue.

**A small validation worth recording:** the same run independently re-surfaced
`means of production`, which is **already** a cue in this camp. A method that only ever produces
novel phrases might be finding noise; one that rediscovers a hand-picked cue on its own evidence
is measuring something real.

## 4. Measured effect

| | before | after |
|---|---|---|
| strict eval | 55/55 pos, 34/34 neg, cross-camp 1/1 | unchanged and green |
| gold recall | 141 of 165 | **143 of 167** (both new gold fire) |
| `subculture_register` background | 8/171 | 8/171 — unchanged |

## 5. Three runs in, what the cost curve actually looks like

| camp | new fetching | candidates | cues | new confound found |
|---|---|---:|---:|---|
| `georgist` | full (3 works) | 22 | 1 | discipline control required; orthography; saturation; nested templates |
| `tankie_mlm` | full (6 works) | 14 | 3 | work titles + author names; scholarly apparatus |
| `revolutionary_left` | **none** | 9 | 2 | **the polemical target's vocabulary** |

The candidate lists get shorter and cleaner because each run's guards carry forward — 22 → 14 →
9 — while the yield holds. Eight noise classes are now guarded, every one of which first
presented as a finding.

The prediction that a fourth camp will surface a ninth class should be treated as live. The
shape has been consistent across all three: **an artifact of how the text was transcribed,
published or argued, wearing the statistics of idiom.** Nothing about frequency, dispersion or
control-silence distinguishes any of them, which is why the guards had to be found one corpus at
a time rather than reasoned out in advance.
