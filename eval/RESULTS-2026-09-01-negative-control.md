# The negative control was never a series, and its forward movements were the agency's own clock

**2026-09-01, later.** Backlog item E17: re-measure "continued dumping duty" under docket
identity. It was the negative pole of the discrimination claim — 10 back, p = 0.002 — and the
only part of that claim not re-run after title matching was replaced by `docket_ids`. Three
things came out of running it.

## 1. It was never one series. It was ninety-five.

Under docket identity the measure collapses to **2 documents**. The reason is in the seeds:

> 100 seed documents, **95 distinct dockets**, most common appearing twice.

Every antidumping case is its own rulemaking — one per product per country. `A-549-502` is Thai
circular welded carbon steel pipe; `A-570-016` is a Chinese case; and so on for ninety-three
others. "Continued dumping duty" is not a measure, it is a **program** under which hundreds of
unrelated series each publish. The original 83-document count was title matching lumping
strangers together, and *10 back, p = 0.002* was computed across them.

**The discrimination claim does not survive this and is not restored below.** Its positive pole
(telemedicine, DEA-407) remains 4 forward, 0 back, p = 0.125 — unresolvable. A negative pole
that now resolves does not rescue a claim whose positive pole does not.

## 2. The seed window is volume-dependent, which is a coverage gap at the recent end

5,760 documents match "continued dumping duty" since 2010. With `order=newest` and
`per_page=100` the seeds spanned **2026-06-25 to 2026-09-01** — ten weeks — despite `--since
2010`. Newest-ordering was introduced to fix a coverage gap at the *old* end, where the first
live run fetched 1996–1999 documents for a measure whose movements were all in 2021–2025. It
creates the mirror of that gap for any term common enough to fill a page.

`--docket` now bypasses term search entirely: membership is the published identifier, ordering
is oldest-first, and a series is read from its beginning. `A-549-502` returns **92 documents
spanning 1994 to 2026** — an order of magnitude more than any series this detector had measured.

## 3. Every forward movement in that series was a filing deadline

First run on the real docket: 19 forward, 14 back, +0.152, p = 0.487.

All nineteen forward movements were **"Notice of Extension of Time Limit for Antidumping Duty
Administrative Review"** — the deadline for Commerce to finish its own review, extended because
the agency needed longer. Not one changed the measure's scope, duration or effective date. The
`forward` pattern `extension of` matched every one.

`movements.yaml` now has a **`procedural`** bucket, checked before everything else and counted
as neither: the agency's clock is not the measure's. Six patterns — time-limit extensions and
comment-period extensions and reopenings.

| A-549-502 | forward | back | asymmetry | p |
|---|---:|---:|---:|---:|
| before | 19 | 14 | +0.152 | 0.487 |
| **after** | **0** | **14** | **−1.000** | **0.0001** |

### Say plainly what this change did

It moved a result hard toward what this project wanted: a negative control that runs backward,
resolving at p = 0.0001. **That is exactly when a rule change deserves the most suspicion.**
Three things were done about it, and they are the reason it is being reported rather than
quietly banked:

1. The change was made on the reading of the documents, not on the p-value. A time-limit
   extension is procedural by definition, and would be excluded if it had moved the number the
   other way.
2. **The whole sweep was re-run, not only the measure that benefits.** All thirteen measures,
   under the corrected spec: nothing changed anywhere else. Telemedicine is still 4f/0b at
   p = 0.125; the sweep still resolves zero of thirteen. The rule is narrow and it did not
   quietly reshape the rest.
3. It needs an independent check before it carries any claim. One reader, one docket.

## What this leaves

- **A real negative control exists** and is measurable: an administrative series that moves one
  way, backward, over 32 years, with 14 receipts.
- **The discrimination claim stays retracted.** One pole is not a discrimination.
- **The sweep's term seeding is the next repair.** Every measure in it returns 1–10 documents
  because term search finds recent documents and docket filtering then keeps the few that share
  the dominant docket. `MEASURES` should carry a docket per measure, looked up once by hand,
  the way A-549-502 and DEA-407 were. Backlog E18's "the sweep saves no corpus" and this are
  the same repair: identify the series, then save it.
- **Item 30 still stands.** No floor for a counting detector. `p = 0.0001` is an exact binomial
  against a fair-coin null; it is not a statement about docket-matching error or coverage.
