# The claim, measured: 7 of 17 methods are attested under opposed flags

The series' load-bearing claim is *method not ideology* — that the same institutional
manoeuvre recurs across actors who agree about nothing else. This measures it directly,
from receipted data already on disk, with **no model, no benchmark, and no score.**

It is the first measurement in this project that tests the actual claim rather than a proxy.

## Why the previous measurements did not

Everything before this scored the keyword detector against the Propaganda Techniques Corpus.
`ptc_precision.py`'s own docstring says why that was the wrong instrument:

> PTC annotates *propaganda techniques in news articles*. This taxonomy names *institutional
> and rhetorical method*, which is a different and broader thing. A lens scoring at chance
> here is not thereby worthless. **Read it as a floor, not a verdict.**

It was read as a verdict for two days. Worse, the 34-cue cut used a PTC-derived background
as its criterion, which is how `ongoing`, `movement` and `national security` — the cues that
actually fire on rulemaking — came to be deleted. An external corpus measuring a different
construct did not merely fail to help; it drove a change that damaged the instrument on its
own target register.

## The measurement

`tradecraft/leaderboard/cross_faction.py`, over the capture ledger's **150 receipted
records** — each a marker, an actor family, an institution, a verbatim span, and source URLs.
12 actor families are grouped into 6 broad ideological blocs, and four bloc pairs are
**declared** antagonistic:

    marxist_leninist vs religious_traditionalist
    marxist_leninist vs corporate
    progressive vs religious_traditionalist
    progressive vs corporate

The grouping is a judgement call, so it lives in the open at the top of the script where it
can be argued with. Change it and the headline changes — which is why the pairs print
alongside the result. `unaligned` is deliberately in no pair: counting a residual bucket as
anybody's opponent would manufacture the answer.

| | marker | records | blocs | opposed pairs spanned |
|---|---|---:|---:|---:|
| ** | `permeation` | 20 | 6 | **all 4** |
| ** | `gradualism` | 15 | 6 | **all 4** |
| ** | `discretionary_rule_elasticity` | 12 | 5 | 2 |
| ** | `authority_override_ratchet` | 11 | 5 | 2 |
| ** | `front_costume` | 8 | 4 | 1 |
| ** | `manufactured_consent` | 13 | 3 | 1 |
| ** | `deniability_architecture` | 10 | 3 | 1 |
| | `captured_neutral` | 19 | 2 | – |
| | `state_moderation_coordination` | 11 | 2 | – |
| | `gov_industry_crossing` | 7 | 2 | – |
| | `crisis_no_exit` | 5 | 2 | – |
| !! | `concentrated_benefit_diffuse_cost` | 9 | **1** (corporate) | – |
| !! | `offwiki_coordination` | 4 | **1** (unaligned) | – |
| !! | `pseudonymous_enforcement` | 3 | **1** (unaligned) | – |
| !! | `paid_covert_editing` | 1 | **1** (corporate) | – |
| !! | `institutional_ip_editing` | 1 | **1** (administrative) | – |
| !! | `asymmetric_enforcement` | 1 | **1** (progressive) | – |

**7 of 17 markers are attested on both sides of a declared opposed pair. 6 sit in a single
bloc and the claim is not demonstrated for those** — they are named individually rather than
averaged into a headline. Every one of the four opposed pairs shares at least one marker, so
there are no empty pairs to report.

## What `permeation` looks like — the strongest case, with receipts

The same move, *enter existing institutions rather than confront them*, attested across
five mutually hostile traditions:

| actor | institution | verbatim span |
|---|---|---|
| progressive_left | **Fabian Society** | "a policy of 'permeation', infiltrating existing institutions, parties and Parliament rather than confronting them" |
| state_leninist | **CCP United Front Work Dept** | "co-opting and mobilizing non-Party elites at home and abroad to advance Party aims" |
| religious_right | **Seven Mountains Mandate** | seven "mountains" — family, religion, education, media, arts, business, government — "spheres to be taken top-down" |
| hindu_nationalist | **RSS** | "~83,000 shakhas by 2025 — daily local branches for ideological formation" |
| commercial_pr | **Gates Foundation / WHO** | "~90% of WHO income is voluntary and almost all of it is earmarked to donor-defined projects" |
| progressive_left | **New Left** | Dutschke's "der lange Marsch durch die Institutionen" (~1967) |

Every row carries source URLs and a FACT/ATTRIBUTED tier. A hostile reader checking them
makes the exhibit stronger, which is the property none of the scoring work had.

## The circularity, and why the receipts are the answer

The ledger was assembled by the author of the thesis it supports. Records selected to show
cross-faction recurrence would show cross-faction recurrence. That is not fixable by
argument, so it is handled structurally:

1. **The evidence is checkable.** Every record has source URLs. This is the only defence
   that actually works against curation bias.
2. **The gaps are as loud as the hits.** Six markers are printed as NOT demonstrated. An
   opposed pair sharing nothing would be printed by name.
3. **No prevalence claim is made or possible.** 150 curated records have no denominator.
   This says the claim is *attested here*, never *this is how often it happens*.

**Receipt coverage is complete, and that is the strongest thing here:** all **150 of 150**
records carry both a source URL and a verbatim span, and every actor family maps to a
declared bloc. There are no unsourced rows and no unclassified actors.

**But the blocs are badly uneven, and the bold marks above oversell the thin ones:**

| bloc | records |
|---|---:|
| administrative | 51 |
| corporate | 45 |
| marxist_leninist | 24 |
| unaligned | 17 |
| **progressive** | **7** |
| **religious_traditionalist** | **6** |

Every opposed pair involves `progressive` or `religious_traditionalist`, so all four
pair-spanning results rest on one of two blocs holding 6–7 records. `permeation` spanning
"all 4 pairs" is carried by roughly four documents on the thin side. The finding is real and
the receipts are real; the *weight* behind it is much lighter than 150 records implies, and
filling those two blocs is the single highest-value curation job.

Worth noting in the other direction: the two largest blocs are `administrative` and
`corporate`, not either wing. Whatever else the ledger is, it is not a partisan hit list —
which is the opposite of what the detector's cue vocabulary turned out to be.

## A false alarm, checked before reporting

`move` and `marker` disagree on 132 of 150 records, which looked like a data defect. It is
not: `move` has three values (`language`, `ratchet`, `permeation`) and `marker` has
seventeen, so `move` is a coarse grouping rather than a duplicate. Recorded because
"restated counts were wrong and got applied" is a documented failure mode here.

## Why this is the instrument to build on

* It measures the claim the books make, not a proxy for it.
* It requires no model, so nothing to refuse, drift, or cost money.
* It cannot be Goodharted by tuning, because there is no threshold and no score.
* It is symmetric by construction: the unit of evidence is a receipt against a named actor,
  and an absent faction shows as an absent row rather than as a silent zero.
* It is demo-ready: the reader picks a method and sees the same manoeuvre under opposed
  flags, with sources. No paste box, no verdict, nothing for a hostile critic to screenshot
  except the receipts.

## Reproduce

```bash
python tradecraft/leaderboard/cross_faction.py
python tradecraft/leaderboard/cross_faction.py --marker permeation --receipts
python tradecraft/leaderboard/cross_faction.py --json
```
