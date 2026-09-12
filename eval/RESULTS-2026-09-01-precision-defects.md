# The harvest was meant to find gold. It found a precision problem instead.

> **RESOLVED, and one verdict below is WRONG. See
> `RESULTS-2026-09-01-precision-resolution.md`.** Three of the four defects were genuine and
> are fixed. **`pejorative-actor-label` was not a defect** — the cue fired correctly on
> "Cardinal Kevin Farrell and his Vatican cronies", and the verdict here was reached by reading
> an excerpt that did not contain the match, because the harvester recorded `sent[:400]`
> regardless of where the cue sat. The structural finding at the end of this file stands.

**2026-09-01.** `tools/harvest_gold.py` scans real documents already in the corpus and reports
every sentence a lens fires on, as a candidate for gold. 68 candidates across 145 documents.

Reading them, roughly a quarter are genuine specimens. Four were promoted to gold with their
source documents. **The rest are the finding**, because each false candidate is a cue firing on
something it should not, and nothing in this repository was measuring that.

## What the gold check cannot see

`eval/gold_check.py` asks whether a lens finds what it should. It went 84 → 138 of 161 tonight
and that number is worth exactly what it says: internal consistency. It cannot ask whether a
lens finds things it should *not*, because it never shows the lens anything that isn't gold.

Every real defect found tonight came from outside text:

| defect | found by |
|---|---|
| `registered with the` fired on a regatta | control corpus |
| `everyone knows` fired on a churchgoing aside | control corpus |
| `made permanent` fired on a conditional in a DEA notice | control corpus |
| the four below | this harvest |

Four for four. The gold check found none of them.

## The precision defects

**`institutional_permeation` / `hidden-or-deferred-cost` fires on a table separator.**
The candidate text is `--------------------------------------------------------------------------- National E-Commerce`.
A cue is matching inside document formatting. Whatever the cue is, it is not detecting a
deferred cost, and it will fire on every table in every Federal Register document.

**`legibility` / `erase-local-knowledge` fires on Executive Order boilerplate.**
*"Executive Order 12988 (Civil Justice Reform): This rulemaking meets applicable standards to
minimise litigation..."* — this exact paragraph appears in a large fraction of US rulemakings.
A cue that matches it produces a lens that scores nearly every federal rule.

**`institutional_permeation` / `attribution-gap` fires on a routine privacy provision.**
*"CBP is required to promulgate regulations that protect the privacy of business
proprietary..."* — an ordinary statutory obligation, not a gap between decision and
accountability.

**`sourcing_asymmetry` / `pejorative-actor-label` fires with no pejorative present.**
*"LGBT Catholics have stayed a part of the church, despite statements and actions which have
offended..."* — a descriptive clause. No label is being applied to an actor.

## Why these are not fixed in this commit

Each needs a judgement the harvest cannot make: whether the cue is salvageable by narrowing, or
whether it is the wrong kind of cue for the marker. Two of tonight's three control-corpus
defects were fixed by narrowing (`made permanent` → `are made permanent`) and one by outright
removal (`registered with the`). Which applies here depends on reading the cue lists against
the markers, and doing it hastily is how the 34-cue cut deleted `ongoing`, `movement` and
`national security` — the cues that actually fire on rulemaking.

## The larger finding, and it is structural

38 new Federal Register documents were fetched specifically to widen the harvest — registration
schemes, data collection, standards setting, comment processes, chosen because those are the
subjects `legibility` and `institutional_permeation` exist for. **They produced one additional
candidate.**

The lenses are near-blind in administrative register. Their cue lists are written for prose
that argues — advocacy, analysis, speeches, opinion — and administrative prose does not argue,
it administers. This is the same finding `rollback_asymmetry` produced when it scored 0.0 on
"Fourth Temporary Extension of COVID-19 Telemedicine Flexibilities", and it generalises across
the taxonomy.

It matters because institutional capture happens substantially in administrative text. A
detector for it that only reads argument will see the campaign for a measure and miss the
measure.

Two responses, and they are not alternatives:

1. **Source advocacy prose**, which is where these cue lists actually work, and stop expecting
   the Federal Register to exercise them.
2. **Accept that some markers are structural**, as `revolving_door`, `network_brokerage` and now
   `ratchet_series` already are. The administrative ratchet had to be counted rather than read;
   administrative permeation and legibility may need the same treatment.

## What this does not say

That the lenses are wrong. A lens that fires precisely on argumentative text and rarely on
administrative text is a valid instrument with a stated domain. The defect is that its domain
was never stated, and the leaderboard would have applied it to both.
