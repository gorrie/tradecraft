# `ratchet_series` — the administrative ratchet, counted

**Not a text lens.** Every other detector here reads a document and scores the rhetoric in it.
This one reads a *series* of documents about one measure and counts which direction they move.

## Why it has to exist

`rollback_asymmetry` was built to read irreversibility off prose, and it works on prose that
argues. Tested against 30 Federal Register rules it fired on 4, and the misses settle the
question: **"ALP Express Pilot to Permanent Status" scores 0.0. "Fourth Temporary Extension of
COVID-19 Telemedicine Flexibilities" scores 0.0.**

Both are ratchets. Neither document says anything ratcheting. The fourth extension of a
temporary measure reads exactly like the first — a modest, reasoned, time-limited step — and it
is only a ratchet because three came before it. The pattern is not in the document. No amount
of cue-matching recovers something that was never written down.

This is the same shape as two results in the sibling bias study: version-over-version drift
scored against a same-version null, and refusal one-way doors where the unanswerable set only
grows. In all three the signal lives in the sequence and is invisible in any single member of
it.

It is also the reason Axis 3 needs this at all. The three-axis model defines REVERSIBILITY
behaviourally — *"You don't get to self-report. It's read off what you do."* A text lens reads
what a document says. This reads what a series did.

## What it counts

For one measure, over its document series, each transition is classified as movement in one of
two directions or as neither:

| direction | examples |
|---|---|
| **forward** (the click) | effective date extended, sunset renewed, scope widened, temporary provision made permanent, pilot converted to permanent status, threshold raised, exemption removed |
| **back** (the un-click) | rule rescinded, authorisation revoked, regulations removed, sunset allowed to expire, scope narrowed, measure permitted to lapse |
| neither | technical correction, renumbering, cost-of-living adjustment, address change |

Output per measure: forward count, back count, the asymmetry ratio, the elapsed span, and every
document number and date as receipts. Never a single blended number, never a verdict — same
discipline as the lenses.

A measure with six forward movements and no back movements over nine years is a ratchet whether
or not any of its six documents contains a single argumentative sentence. That is the claim, and
it is checkable by anyone with the document numbers.

## What it is not

- **Not a claim that the measure is bad.** A programme may be extended six times because it
  works. The asymmetry is a fact about reversibility, not about merit, and the tool says so.
- **Not a claim about intent or coordination.** Same rule as every lens here.
- **Not a substitute for `rollback_asymmetry`.** Rhetorical and administrative ratchets are
  different objects and both are real. A campaign arguing a measure must never be repealed is
  the first. A measure quietly extended for a decade is the second.

## Floor

Item 30 of the backlog: this detector's nuisance factors are not sentence order and whitespace.
They are **docket-matching errors** (is this document about the same measure?), **coverage gaps**
(did the search see every document in the series?), and **ambiguous movements** (does a raised
threshold widen or narrow?). `eval/lens_floor.py` does not transfer and a second harness is
needed before any ratio is published.

`eval/series_floor.py` now measures two of the three by perturbing the QUERY rather than the
text: word subsets, word order, singular and plural, page caps, date floors. Same measure,
differently asked.

**Measured 2026-09-01 on telemedicine flexibilities** (9 variants):

| | result |
|---|---|
| sign stable across variants | YES |
| asymmetry spread | **0.000** — every variant that locates the series returns +1.000 |
| every variant resolvable | no — `per_page=40` finds 5 movements, p = 0.0625 |

Sign and magnitude are query-invariant. **Significance is not**, and the cause is a coverage
gap rather than instability: a truncated search sees fewer movements than the series contains,
and fewer movements cannot reach the same p. So the honest form of the finding is *eight
one-way movements, zero reversals, p = 0.0078, at a search depth of 100 or more documents* —
the depth is part of the claim, not a detail.

Ambiguous movements are bounded separately: every result reports the asymmetry recomputed with
all ambiguous documents forced forward and forced back. Telemedicine survives (+1.0 against
+0.333, sign intact); conservation-and-landscape-health does not (+0.333 against -1.0), so its
sign is a classification decision rather than a measurement, and the tool says so.

Still unquantified: docket matching where a measure is titled inconsistently across its series.
The title filter is crude and biases toward UNDERSTATING ratchets, which is the safer direction
but still a bias. `provisional: true` stays until that is measured.
