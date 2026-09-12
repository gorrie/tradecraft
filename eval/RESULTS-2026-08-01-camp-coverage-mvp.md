# Subculture-register MVP — all-camp coverage pass (2026-08-01)

Goal: a decent-coverage MVP for EVERY camp before wiring into the ratchet toolset, then improve.
Method: fetch each camp's own canonical work(s) by curl, confirm which tells actually appear (recall),
widen cues from real text, FP-screen every addition, add real-primary recall fixtures. Same discipline
as the FP sweep: keep coined near-exclusive idiom, cut anything dual-use — even with strong recall.

## Per-camp findings

| camp | real primary fetched | tells added (validated) | FP cuts this pass | recall fixture |
|---|---|---|---|---|
| revolutionary_left | Marx/Engels *Manifesto* (bourgeoisie 52×, proletariat 28×, class struggle 3×); Debord *Spectacle* (society of the spectacle 7×); Bonanno *Armed Joy* | bourgeoisie, proletariat, means of production, class consciousness, surplus value, commodity fetishism | **ruling class** — fires on ordinary history ("the ruling class of ancient Rome") | Manifesto + Bonanno (2 works ✓) |
| radical_feminist | Hanisch *The Personal Is Political* (personal is political 17×, pro-woman line 11×, male supremacy 3×) | male supremacy, pro-woman line, rape culture | — | Hanisch (1) |
| critical_social_justice | McIntosh *Invisible Knapsack* (white privilege 17×, invisible knapsack 13×, unearned 22×) | white privilege, invisible knapsack, intersectionality, white fragility, microaggression | — | McIntosh (1) |
| rationalist_ai_safety | Bostrom *Existential Risks* (existential risk 70×) | the alignment problem, instrumental convergence, orthogonality thesis, paperclip maximizer, longtermism | **existential risk** — leaked into business English ("existential risk to the company"); **singleton** (Bostrom's term but collides with programming/pregnancy); **Moloch** (biblical) | probe (real primary deferred — Bostrom 2002 predates the x-risk/LessWrong shibboleths) |
| disinformation_apparatus | — (documented coinages; Info Disorder report already cited) | influence operations, firehose of falsehood | — | probe |
| managerial_technocratic | — (Friedman 1970 404'd; coinages documented) | ESG, public-private partnership, social license, human capital, smart city | — | probe |
| accelerationist_right | — (DOCTRINE-only by policy; NO extremist-host fetch) | the great replacement, white genocide, helicopter rides (DEFAMATION NOTE in-lens: opposite-speaker possible) | — | probe |

## Cross-camp separation (the precision proof)

Every fetched primary fires ONLY its own camp, EXCEPT Hanisch, which fires BOTH `radical_feminist`
(pro-woman line, male supremacy) AND `revolutionary_left` (verbatim "class struggle") — correct, not a
bug: it is a socialist-feminist text that genuinely speaks both registers. Multi-register texts get
multiple fingerprints; that is the intended behaviour. de Cleyre's nonviolent *Direct Action* stays
silent (no camp), as it should.

## FP discipline held

Three strong-recall cues were CUT because they are dual-use: `ruling class`, `existential risk`,
`singleton`. This is the same rule that drove the main sweep — a coined near-exclusive tell survives; a
word the whole language uses does not, however well it recalls. Two biblical/programming collisions
(`Moloch`, `singleton`) screened out before landing.

## Suite state

- `python eval/run_eval.py cues` → positives **29/29**, negatives quiet **16/16**, coverage **29/29**,
  8 skipped (verify layer).
- `python -m pytest -q` → **113 passed**.

## EXPANSION — 7 → 14 camps (same day)

Fleshing out was cut short at 7; expanded to 14 with the same real-source-or-documented-coinage rigor,
symmetric. **Accelerationists were NOT hidden** — the earlier "documented-only" framing was an
inconsistent over-correction; they now carry §3i-parity sourcing (Turner Diaries / SIEGE, the same
gate-verified record the militant lens uses) plus added tells (siege-pilled, RaHoWa).

New camps added: `jihadist_militant` (§3i / al-Suri, parity with accelerationist), `ethnonationalist`,
`manosphere_mra`, `gender_critical`, `qanon_conspiracist`, `neoreactionary`, `effective_altruism`.

Real-primary recall extended (grep counts on fetched text): Moldbug *Formalist Manifesto* — formalism
13× (→ neoreactionary); 80,000 Hours *Earning to Give* — earning to give 63× (→ effective_altruism).

FP discipline held on the new cues — CUT 4 dual-use/opposite-speaker cues: `the red pill` (The Matrix),
`the near enemy`/`the far enemy` (Buddhist "near enemy of compassion"; ordinary military), `gender
ideology` (used by the religious right, GC advocates, AND their critics), `bednets` (any malaria
article). Cross-camp clean; every new camp exemplar fires only its own camp; all 4 lookalikes quiet.

Suite after expansion: positives **36/36**, negatives quiet **20/20**, 113 pytest.

## BREADTH — 14 → 21 camps (same day)

Added 7 more for coverage: `tankie_mlm`, `tradcath_integralist`, `crypto_sovereign_libertarian`,
`eco_radical_primitivist`, `transhumanist_eacc`, `degrowth`, `christian_nationalist`. Every new camp
fires only its own register. FP discipline held again — CUT 4 more dual-use cues: `the singularity`
(physics — black-hole singularity), `planetary boundaries` (neutral Earth-system science, Rockström),
`read theory` (a professor's imperative), `christian nation` (historians debate the phrase). Running
FP-cut total across the register lens: 8 dual-use/opposite-speaker cues (red pill, near/far enemy,
gender ideology, bednets, singularity, planetary boundaries, read theory, christian nation) plus the
3 from the first pass (ruling class, existential risk, singleton). Suite: positives **43/43**,
negatives quiet **24/24**, 113 pytest. Roadmap (modern materials / more camps / true-believers / OSINT
tracking / effectiveness metrics / scoring wiring) in BACKLOG.

## BREADTH — 21 → 27 camps + the FP-audit tool (same day)

Added 6 more: `georgist`, `mmt_monetary`, `sovereign_citizen`, `antinatalist`, `prepper_survivalist`,
`maga_new_right`. FP gate cut 4 dual-use cues at validation (job guarantee → labor contract; grid-down
→ power outage; RINO → **the rhinoceros**; drain the swamp → literal wetland) — the gutted maga/mmt/
prepper camps were ENRICHED with exclusive slogans (stop the steal, let's go brandon; taxes don't fund
spending; when the balloon goes up) rather than left thin.

**New tool `tools/fp_audit.py`** — scans EVERY cue in the whole detector against a 3.18M-char general-
English background (Austen + Melville + Federalist + benign fixtures). "Test it on everything and see
how we do":

- `subculture_register`: **0 / 172 cues** appear in the background. The shibboleth approach is
  FP-clean by construction — validated at scale, not by hand-probes.
- It also caught two OUTRIGHT BUGS the small-probe sweep missed in the older MOVE lenses: `found`
  (525× — matches "find" past-tense) and `TINA` (30× — matches the name *Tina*). Both fixed
  (institutional_permeation, inevitability_framing).
- The move lenses still show ~44 flagged cues (judiciary, the courts, civility, direct action, …).
  Those are **context-dependent move cues by design** — the move lenses detect rhetorical moves via
  breadth × density + the verify layer, not per-cue exclusivity, and several carry gold/fixture/
  leaderboard dependencies. They get a dedicated fp_audit-driven review pass (BACKLOG), not a blind cut.

Suite: positives **49/49**, negatives quiet **28/28**, 113 pytest. 27 camps.

## Not done yet (improve-from-here)

- Real-primary recall for disinfo / managerial / accelerationist / rationalist(post-2002) — deferred to
  the corpus study (accelerationist stays documented-only by defamation policy).
- **Ratchet-toolset integration + scoring update** — once coverage is satisfactory, wire
  `subculture_register` into the ratchet scoring so register fingerprints feed the composite. Not done
  in this pass (the author gated it on "satisfactory improvements").
