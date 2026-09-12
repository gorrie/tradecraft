# Tradecraft testing corpus — primary sources by pawl

A labeled corpus of **real primary-source text**, organized by the five pawls of *The Ratchet*
(traditionalist / progressive / utilitarian / technocratic / green — see `factions.yaml`). Its job is
the one the synthetic fixtures in `eval/fixtures.json` cannot do: prove each lens fires on the
**method present**, not on a faction's political coding. It is the substrate for the sample→grade→tune
loop ("sample and train for a while").

## Files
- `factions.yaml` — the canonical 5-pawl roster (definitions, orgs/actors, rhetoric-tells, coding, sources).
- `specimens.jsonl` — one JSON object per line: `{id, pawl, stance, source_url, date, author, title, note, text}`.
- Run with `python eval/run_corpus.py [backend] [--md eval/corpus-report.md]`.

## Stances
- `self` — the pawl's OWN words (doctrine, manifesto, official statement). Tests register/method lenses.
- `about` — coverage OF the pawl. Tests the coverage lenses (`narrative_management`, `sourcing_asymmetry`).

## Discipline (hard rules)
- **Provenance on every specimen.** `source_url` must resolve and support the text; verify before adding.
- **Fair-use snippets only** — a few representative sentences, never a full copyrighted work; provenance
  fields carry the receipt, the corpus does not republish the source.
- **Specimens are labeled TEST MATERIAL, never cited as fact.** Raw faction text is a specimen with a
  label, not a claim we adopt. No terrorist/propaganda source as load-bearing.
- **Symmetric, flag-not-verdict.** The `coding` tag exists ONLY to structure the symmetry test. A
  `CONCENTRATED` flag from the runner is a prompt to investigate (text vs lens), never a verdict, never a
  left/right label on a document.
- **Do not confabulate a quote or a URL.** If the exact primary text can't be verified from this box
  (IP-blocked origin), queue it to M5/archive.org (see `BACKLOG.md`) rather than paraphrase-and-attribute.

## What the seed run already showed (2026-08, cues backend)
- **The cues floor is high-precision / low-recall on authentic prose.** Literal cue strings rarely
  appear verbatim in real primary text, so 0/5 seed specimens fire at the "notable" threshold on the
  offline cues backend. This is the empirical case for the **model-panel backend** doing recall while
  cues stay the deterministic floor — i.e. the "train" ladder, not a bug.
- **The corpus caught a real false positive** the synthetic fixtures missed: `sourcing_asymmetry`'s
  `fringe` cue fired on GFANZ's "from the fringes to the forefront." Fixed (→ `fringe group`/`fringe
  figure`). This is the loop working: real text surfaces cue collisions synthetic probes never contain.

## The sample→train loop
1. **Sample** — add verified primary specimens (both stances, several per pawl) via `research-dossier`.
2. **Grade** — `run_corpus.py` (cues floor, then a model backend for recall).
3. **Read the symmetry report** — for each lens, is firing spread across pawls or concentrated?
4. **Tune** — a concentration that lives in the LENS (a register-bound cue) gets fixed; one that lives
   in the TEXT (that pawl really uses the method more) gets documented, not "corrected."
5. **Guard** — re-run `eval/run_eval.py` (no fixture regressions) and `tools/fp_audit.py`.
6. Repeat. Breadth (≥N specimens/pawl) is what turns the symmetry report from anecdote into a statistic.
