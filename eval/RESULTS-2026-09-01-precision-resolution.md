# Resolution of the four precision defects — and one was a false accusation

**2026-09-01, later.** Resolves `RESULTS-2026-09-01-precision-defects.md`. Three of the four
were genuine and are fixed. The fourth was not a cue defect at all, and finding out why
produced the most consequential fix of the four.

## `pejorative-actor-label` was RIGHT. The receipt was wrong.

That file wrote it up as *"fires with no pejorative present"* over the passage *"LGBT Catholics
have stayed a part of the church, despite statements and actions which have offended..."* — a
descriptive clause with no label in it.

The document says **"the efforts of Cardinal Kevin Farrell and his Vatican cronies to promote
the LGBT agenda."** The cue `cronies` fired on "Vatican cronies", which is exactly what the
marker is for. The verdict was reached by reading a passage that did not contain the match.

**Cause: `harvest_gold.py` recorded `sent[:400]`** — the first 400 characters of the sentence,
regardless of where in it the cue sat. When the cue fell past that boundary the candidate
carried no trace of what fired, and a reviewer saw prose with nothing wrong in it.

In an instrument whose first rule is *flag-and-show-the-receipts, never a verdict*, a receipt
that omits its own evidence is the worst available failure. It does not merely fail to help; it
misleads, and here it convicted a working cue.

Fixed two ways. The excerpt is now **centred on the match**, and the harvester **asserts that
every candidate's text contains the cue that fired**, exiting 1 with the offending rows named
if any does not — and printing "every candidate's excerpt contains the cue that fired" when
clean, so the property is stated rather than assumed. Re-harvested: 84 candidates, up from 68
now the advocacy corpus is visible, all aligned.

## The three real ones, each with the judgement it needed

**`attribution-gap` / `proprietary` — NARROWED.** A bare word matching the routine legal term
*"business proprietary information"* in three separate rulemakings, plus an acronym glossary
defining PROPIN. The marker's own definition says *proprietary criteria*, so the cue now has to
reach the decision machinery: `proprietary criteria | algorithm | model | score | formula |
methodology | system`.

**`hidden-or-deferred-cost` / `spread across` — NARROWED.** A geographic idiom, not a cost one:
a scheduled drug that *"rapidly spread across the United States"*, a criminal gang that *"has
already spread across Denmark"*. The marker is a DIFFUSE COST, so the cue names one now:
`cost is/are spread across | spread across taxpayers | spread across everyone | spread thinly
across`.

**`erase-local-knowledge` / `eliminate ambiguity` — EXCLUDED, not narrowed.** The cue is a real
marker of the standardisation grid in argumentative prose. It is also three words of Executive
Order 12988's mandatory paragraph, which appears in a large share of US rulemakings. Neither
keeping it nor dropping it was right, so the schema gained the capability it was missing.

## `excludes`: the one mechanism here that can make a lens fire less

`Detection.excludes` is a list of phrases that suppress a firing when they appear near the
match. Design points, because this is the mechanism whose misuse is hardest to see — a lens
that has quietly stopped detecting looks exactly like a lens with good precision:

- **Match-local, not document-level.** A rulemaking carries the boilerplate as a matter of
  course; a genuine standardisation argument in its fifth paragraph must survive the
  boilerplate in its first. Window is 200 characters either side.
- **Applied as a rejection INSIDE the cue search**, so a suppressed occurrence advances to the
  next occurrence of the same cue rather than abandoning the cue. The first implementation
  filtered after the fact, which made the exclusion document-level by accident —
  `test_exclusion_is_match_local_not_document_level` caught that, which is why the test was
  written before the feature was trusted.
- **One-directional.** An exclusion can only suppress. It cannot invent a firing, so it cannot
  make a lens over-fire. The only risk it carries is lost recall, and `gold_check` measures
  that.

## Measured, both directions

| | before | after |
|---|---:|---:|
| gold recall | 138 of 161 | **138 of 161** (no loss) |
| tests | 129 | **138** (9 new, both directions per cue) |
| documents firing `institutional_permeation` | 24 | **16** |
| documents firing `legibility` | 7 | **6** |
| `institutional_permeation` length↔index Spearman | −0.673 | **−0.505** |

All four false fires stop. All three moves the cues exist for still fire, each with its own
test. Eight documents stopped scoring on `institutional_permeation` and not one gold example
was lost — which is what a precision fix is supposed to look like.

## What is still open from the original file

Its **structural** finding stands and is untouched by any of this: the lenses are near-blind in
administrative register, because their cue lists were written for prose that argues and
administrative prose administers. Narrowing three cues does not change that. The two responses
it named — source advocacy prose, and accept that some markers are structural rather than
textual — are corpus items 6 and 33, not cue items.
