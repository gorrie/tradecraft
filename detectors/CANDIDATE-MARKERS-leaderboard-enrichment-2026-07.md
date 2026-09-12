# Candidate markers + shoehorn audit — from the 2026-07 capture-leaderboard enrichment

**Status: CANDIDATE + AUDIT. NOT WIRED.** Menu for a taxonomy PR, plus a re-tag list for the
evilrobots `capture_leaderboard.json`. No `detectors/` YAML changed by this file.

## The honest finding (why "no new markers" was hollow)

The 2026-07 enrichment added **~88 records across 22 institutions** to the capture-leaderboard. It
reported **zero new markers on every batch** — but that was an *artifact of the constraint*, not
evidence the taxonomy is complete. The leaderboard scores only **3 of the detector's 12 lenses**
(`reference_capture`, `institutional_permeation`, `revolving_door`), and the enrichment agents were
told to prefer the existing 16 markers. So capture-moves that genuinely belong in the **other 9
lenses** got crammed into the 3 available. The review that matters is *fit*, not *count*.

## A. Shoehorned into 3 lenses; true home is an UNUSED lens

| Records (leaderboard) | Filed as | Belongs in (unused lens) | Why |
|---|---|---|---|
| Frontier Model Forum "frontier models *as defined by the Forum*"; US AI Safety Institute voluntary-commitment framing; "adapt or be left behind" | `front_costume` / `discretionary_rule_elasticity` | **inevitability_framing** | The move is *pre-empting resistance / defining the terms before binding rules arrive* — the resistance-is-futile pointed forward, not a fake-grassroots costume. |
| CCP "discourse and narrative system" / mandated `tifa` formulations; Soviet Glavlit single-approved-register | `discretionary_rule_elasticity` / `state_moderation_coordination` | **legibility** (Scott) | A *centrally-mandated, standardized, readable vocabulary officials must use* is the legibility move (render discourse into a form the center can manage) — not merely "elastic rules." |
| WHO industry-funded guidance; FDA user-fee-funded review; US AISI "safety body dependent on the labs it grades" | `captured_neutral` / `front_costume` | **counterproductivity** (Illich) | The signature is *the institution producing the harm it was built to prevent / captured by those it regulates* — iatrogenic, not just a neutrality claim. |
| Behavioural Insights Team "arms-length deniable private service"; nudge as governance-by-default | `deniability_architecture` | **distributed_accountability** | "No one decides" — responsibility dissolves into the choice-architecture so no actor is answerable. Overlaps deniability_architecture; the *no-answerable-actor* half is distributed_accountability. |

**Implication:** the leaderboard is *structurally blind* to 4 capture-moves it repeatedly
encountered. Either expand it to score `inevitability_framing`, `legibility`, `counterproductivity`,
and `distributed_accountability`, or stop claiming the 3-lens board is a complete capture read.

## B. Genuine NEW marker / detection candidates (not covered by any of the 12)

1. **`asymmetric_enforcement`** — new marker under `reference_capture`. *Symmetric rules, applied
   asymmetrically by faction* — distinct from `discretionary_rule_elasticity` (vague/elastic
   charges). Gold: Marcuse, *Repressive Tolerance* (1965): "Liberating tolerance ... would mean
   intolerance against movements from the Right and toleration of movements from the Left." Also
   fires on KDE/Arch "CoC for thee" enforcement in the troll.fan governance record.
2. **`sequential-elimination`** — new detection under `gradualism` (institutional_permeation).
   *Salami tactics: slice off rivals/coalition partners one at a time via engineered charges.*
   Gold: Rákosi's szalámitaktika (Béla Kovács seized on conspiracy charges 1947; SDP forced-merged
   1948) — currently filed flat as `gradualism`.
3. **`self_regulation_preemption`** — new marker under `institutional_permeation`. *The regulated
   author/define the binding standard before external regulation arrives.* Gold: FMF "the Forum
   reserves to itself the threat models, evaluations, thresholds and mitigations its own members
   are measured against." Currently split awkwardly across `front_costume`/`discretionary_rule_elasticity`.
4. **`mandated-vocabulary`** — new detection under **legibility** (if wired) or a new language
   marker. *A centrally-approved formulation set that officials/media must use; deviation is a
   discipline matter.* Gold: CCP `tifa`; Klemperer's LTI single-vocabulary saturation.

## C. Marker overlap to tighten (definitions blur in the corpus)

`front_costume` (fake grassroots / third-party front) and `captured_neutral` (the apparatus's own
neutrality claim) were used near-interchangeably across the enrichment (Bernays, ExxonMobil GCC, the
AI bodies). They are distinct moves — astroturf vs. neutrality-claim — and the `gold`/`cues` should
be sharpened so the grader separates them. Re-tag candidates: several ExxonMobil/AI-body records.

## Recommendation / next step

1. **Wire B1–B3** as low-risk YAML additions (new detections + gold lifted from the records above);
   `mandated-vocabulary` waits on a `legibility` usage decision.
2. **Leaderboard reconciliation:** re-tag the section-A records to their true lens once the leaderboard
   scores those lenses; until then, annotate them as under-scored rather than mis-scored.
3. Regrade + eval after wiring (the language lenses still lack a real validation corpus — see the
   SemEval note in `CANDIDATE-MARKERS-disarm-semeval.md`).
